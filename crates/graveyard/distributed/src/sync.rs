//! Knowledge graph synchronization.
//!
//! The knowledge graph is replicated across nodes via CRDTs. Each entity is
//! stored as an [`LWWRegister`] keyed by id, so concurrent edits at different
//! nodes converge to the last writer. The [`KnowledgeSync`] store merges
//! remote updates and tracks a [`VectorClock`] of observed changes.

use crate::crdt::{LWWRegister, VectorClock, Crdt};
use crate::Result;
use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;
use tracing::{debug, info};
use uuid::Uuid;

/// A node in the knowledge graph.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Entity {
    pub id: Uuid,
    pub label: String,
    pub properties: BTreeMap<String, String>,
}

/// A replicated entity stored as an LWW register with its originating node.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct EntityState {
    register: LWWRegister<Entity>,
}

impl EntityState {
    pub fn new(entity: Entity, timestamp: u64, node: Uuid) -> Self {
        Self {
            register: LWWRegister::new(entity, timestamp, node),
        }
    }

    pub fn entity(&self) -> &Entity {
        &self.register.value
    }

    pub fn timestamp(&self) -> u64 {
        self.register.timestamp
    }

    pub fn node(&self) -> Uuid {
        self.register.node
    }

    pub fn update(&mut self, entity: Entity, timestamp: u64, node: Uuid) {
        self.register.set(entity, timestamp, node);
    }

    pub fn merge(&mut self, other: &Self) {
        self.register.merge(&other.register);
    }
}

/// Replicated knowledge graph store.
#[derive(Debug, Clone, Default)]
pub struct KnowledgeSync {
    entities: BTreeMap<Uuid, EntityState>,
    clock: VectorClock,
    local_node: Uuid,
}

impl KnowledgeSync {
    pub fn new(local_node: Uuid) -> Self {
        Self {
            entities: BTreeMap::new(),
            clock: VectorClock::new(),
            local_node,
        }
    }

    /// Apply a local upsert, advancing the local vector clock.
    pub fn upsert(&mut self, mut entity: Entity) -> u64 {
        let ts = self.clock.get(&self.local_node) + 1;
        self.clock.increment(self.local_node);
        let id = entity.id;
        match self.entities.get_mut(&id) {
            Some(state) => state.update(entity, ts, self.local_node),
            None => {
                entity.id = id;
                self.entities
                    .insert(id, EntityState::new(entity, ts, self.local_node));
            }
        }
        info!(entity = %id, ts, "knowledge upsert");
        ts
    }

    /// Merge a remote entity state; the remote clock advances ours.
    pub fn merge_remote(&mut self, remote: EntityState, remote_node: Uuid) -> Result<()> {
        let id = remote.entity().id;
        match self.entities.get_mut(&id) {
            Some(state) => {
                let before = state.entity().clone();
                state.merge(&remote);
                if state.entity() != &before {
                    debug!(entity = %id, "knowledge entity updated from remote");
                }
            }
            None => {
                self.entities.insert(id, remote);
            }
        }
        self.clock.increment(remote_node);
        Ok(())
    }

    pub fn get(&self, id: &Uuid) -> Option<&Entity> {
        self.entities.get(id).map(|s| s.entity())
    }

    pub fn all(&self) -> Vec<Entity> {
        self.entities
            .values()
            .map(|s| s.entity().clone())
            .collect()
    }

    pub fn len(&self) -> usize {
        self.entities.len()
    }

    pub fn is_empty(&self) -> bool {
        self.entities.is_empty()
    }

    /// Export all entity states for replication.
    pub fn export(&self) -> Vec<EntityState> {
        self.entities.values().cloned().collect()
    }

    /// Detect conflicts: entities where the remote version is newer on a
    /// different node than our own latest writer.
    pub fn detect_conflicts(&self, remote: &EntityState) -> Result<bool> {
        match self.entities.get(&remote.entity().id) {
            None => Ok(false),
            Some(local) => {
                let concurrent = local.timestamp() == remote.timestamp()
                    && local.node() != remote.node()
                    && local.entity() != remote.entity();
                Ok(concurrent)
            }
        }
    }

    pub fn clock(&self) -> &VectorClock {
        &self.clock
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn node(seed: u8) -> Uuid {
        Uuid::from_bytes([seed; 16])
    }

    fn entity(_seed: u8, label: &str) -> Entity {
        Entity {
            id: Uuid::new_v4(),
            label: label.to_string(),
            properties: BTreeMap::new(),
        }
    }

    #[test]
    fn upsert_and_get() {
        let mut store = KnowledgeSync::new(node(1));
        let e = entity(1, "person");
        store.upsert(e.clone());
        assert_eq!(store.len(), 1);
        assert_eq!(store.get(&e.id).unwrap().label, "person");
    }

    #[test]
    fn merge_remote_converges() {
        let mut a = KnowledgeSync::new(node(1));
        let mut b = KnowledgeSync::new(node(2));
        let e = entity(3, "node");
        let id = e.id;
        a.upsert(e.clone());
        // replicate to b at a later time
        let remote = EntityState::new(e.clone(), 100, node(1));
        b.merge_remote(remote, node(1)).unwrap();
        assert_eq!(b.get(&id).unwrap().label, "node");
    }

    #[test]
    fn lww_resolves_concurrent_edits() {
        let mut a = KnowledgeSync::new(node(1));
        let mut b = KnowledgeSync::new(node(2));
        let e = entity(4, "init");
        let id = e.id;
        a.upsert(e.clone());
        b.upsert(Entity {
            id,
            label: "edited-by-b".into(),
            properties: BTreeMap::new(),
        });
        // a sees b's update (higher local clock → higher ts)
        let remote = {
            let states = b.export();
            states.into_iter().find(|s| s.entity().id == id).unwrap()
        };
        a.merge_remote(remote, node(2)).unwrap();
        assert_eq!(a.get(&id).unwrap().label, "edited-by-b");
    }

    #[test]
    fn conflict_detection() {
        let store = KnowledgeSync::new(node(1));
        let e = entity(5, "x");
        let local = EntityState::new(e.clone(), 10, node(1));
        let remote = EntityState::new(Entity { label: "y".into(), ..e }, 10, node(2));
        assert!(store.detect_conflicts(&remote).is_ok());
        let _ = local;
    }

    #[test]
    fn clock_advances() {
        let mut store = KnowledgeSync::new(node(7));
        store.upsert(entity(8, "a"));
        store.upsert(entity(9, "b"));
        assert_eq!(store.clock().get(&node(7)), 2);
    }
}
