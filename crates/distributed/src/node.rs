//! Node registry, discovery and heartbeats.
//!
//! A [`NodeRegistry`] tracks the membership of a cluster. Nodes register, send
//! periodic [`Heartbeat`]s, and are considered dead once their heartbeat
//! timestamp passes the configured timeout. Discovery lists the currently live
//! nodes.

use crate::{DistributedError, Result};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::Arc;
use std::time::{Duration, Instant};
use tokio::sync::RwLock;
use tracing::{debug, info, warn};
use uuid::Uuid;

/// The kind of node participating in the cluster.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum NodeKind {
    Compute,
    Storage,
    Coordinator,
    Edge,
}

/// A logical address where a node can be reached.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct NodeAddress {
    pub host: String,
    pub port: u16,
}

/// A single node in the cluster.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Node {
    pub id: Uuid,
    pub kind: NodeKind,
    pub address: NodeAddress,
    pub region: String,
    #[serde(skip)]
    pub last_heartbeat: Option<Instant>,
    #[serde(skip)]
    pub seq: u64,
}

impl Node {
    pub fn new(kind: NodeKind, address: NodeAddress, region: String) -> Self {
        Self {
            id: Uuid::new_v4(),
            kind,
            address,
            region,
            last_heartbeat: Some(Instant::now()),
            seq: 0,
        }
    }

    pub fn is_alive(&self, timeout: Duration) -> bool {
        self.last_heartbeat
            .map(|t| t.elapsed() <= timeout)
            .unwrap_or(false)
    }
}

/// A heartbeat message exchanged between nodes.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Heartbeat {
    pub node_id: Uuid,
    pub seq: u64,
    pub timestamp_ms: u64,
}

/// Thread-safe node registry that manages cluster membership.
#[derive(Debug, Clone)]
pub struct NodeRegistry {
    nodes: Arc<RwLock<HashMap<Uuid, Node>>>,
    heartbeat_timeout: Duration,
}

impl NodeRegistry {
    pub fn new(heartbeat_timeout: Duration) -> Self {
        Self {
            nodes: Arc::new(RwLock::new(HashMap::new())),
            heartbeat_timeout,
        }
    }

    /// Register a new node and return its generated id.
    pub async fn register(&self, node: Node) -> Result<Uuid> {
        let mut guard = self.nodes.write().await;
        if guard.contains_key(&node.id) {
            return Err(DistributedError::DuplicateNode(node.id.to_string()));
        }
        info!(node_id = %node.id, kind = ?node.kind, "registering node");
        let id = node.id;
        guard.insert(id, node);
        Ok(id)
    }

    /// Remove a node from the registry.
    pub async fn deregister(&self, id: &Uuid) -> Result<()> {
        let mut guard = self.nodes.write().await;
        guard
            .remove(id)
            .map(|_| ())
            .ok_or_else(|| DistributedError::NodeNotFound(id.to_string()))
    }

    /// Record a heartbeat, bumping the node's sequence counter.
    pub async fn heartbeat(&self, hb: Heartbeat) -> Result<()> {
        let mut guard = self.nodes.write().await;
        let node = guard
            .get_mut(&hb.node_id)
            .ok_or_else(|| DistributedError::NodeNotFound(hb.node_id.to_string()))?;
        if hb.seq >= node.seq {
            node.seq = hb.seq + 1;
            node.last_heartbeat = Some(Instant::now());
            debug!(node_id = %hb.node_id, seq = node.seq, "heartbeat received");
        }
        Ok(())
    }

    /// Discover live nodes (those within the heartbeat timeout).
    pub async fn discover(&self) -> Vec<Node> {
        let guard = self.nodes.read().await;
        guard
            .values()
            .filter(|n| n.is_alive(self.heartbeat_timeout))
            .cloned()
            .collect()
    }

    /// Discover live nodes of a particular kind.
    pub async fn discover_by_kind(&self, kind: NodeKind) -> Vec<Node> {
        self.discover()
            .await
            .into_iter()
            .filter(|n| n.kind == kind)
            .collect()
    }

    /// Discover live nodes in a given region.
    pub async fn discover_by_region(&self, region: &str) -> Vec<Node> {
        self.discover()
            .await
            .into_iter()
            .filter(|n| n.region == region)
            .collect()
    }

    /// Nodes considered dead (heartbeat exceeded timeout).
    pub async fn dead_nodes(&self) -> Vec<Node> {
        let guard = self.nodes.read().await;
        guard
            .values()
            .filter(|n| !n.is_alive(self.heartbeat_timeout))
            .cloned()
            .collect()
    }

    pub async fn count(&self) -> usize {
        self.nodes.read().await.len()
    }

    pub async fn live_count(&self) -> usize {
        self.discover().await.len()
    }
}

/// A background task that periodically expires dead nodes and warns about them.
pub async fn monitor_loop(registry: NodeRegistry, period: Duration) {
    loop {
        tokio::time::sleep(period).await;
        for node in registry.dead_nodes().await {
            warn!(node_id = %node.id, "node missed heartbeat window");
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn addr() -> NodeAddress {
        NodeAddress {
            host: "127.0.0.1".into(),
            port: 7000,
        }
    }

    #[tokio::test]
    async fn register_and_discover() {
        let reg = NodeRegistry::new(Duration::from_secs(30));
        let n = Node::new(NodeKind::Compute, addr(), "us-east".into());
        let id = reg.register(n).await.unwrap();
        assert_eq!(reg.count().await, 1);
        let live = reg.discover().await;
        assert_eq!(live.len(), 1);
        assert_eq!(live[0].id, id);
    }

    #[tokio::test]
    async fn duplicate_register_rejected() {
        let reg = NodeRegistry::new(Duration::from_secs(30));
        let n = Node::new(NodeKind::Compute, addr(), "us-east".into());
        reg.register(n.clone()).await.unwrap();
        assert!(reg.register(n).await.is_err());
    }

    #[tokio::test]
    async fn heartbeat_bumps_seq() {
        let reg = NodeRegistry::new(Duration::from_secs(30));
        let n = Node::new(NodeKind::Coordinator, addr(), "eu".into());
        let id = reg.register(n).await.unwrap();
        let start = reg.discover().await[0].seq;
        reg.heartbeat(Heartbeat {
            node_id: id,
            seq: start,
            timestamp_ms: 1,
        })
        .await
        .unwrap();
        assert_eq!(reg.discover().await[0].seq, start + 1);
    }

    #[tokio::test]
    async fn stale_heartbeat_ignored() {
        let reg = NodeRegistry::new(Duration::from_secs(30));
        let n = Node::new(NodeKind::Compute, addr(), "us-east".into());
        let id = reg.register(n).await.unwrap();
        let seq = reg.discover().await[0].seq;
        // bump the sequence so a later stale heartbeat (seq - 1) is rejected
        reg.heartbeat(Heartbeat {
            node_id: id,
            seq,
            timestamp_ms: 1,
        })
        .await
        .unwrap();
        let bumped = reg.discover().await[0].seq;
        // stale heartbeat (lower than current) must be ignored
        reg.heartbeat(Heartbeat {
            node_id: id,
            seq: bumped.saturating_sub(1),
            timestamp_ms: 0,
        })
        .await
        .unwrap();
        assert_eq!(reg.discover().await[0].seq, bumped);
    }

    #[tokio::test]
    async fn dead_node_not_discovered() {
        let reg = NodeRegistry::new(Duration::from_millis(10));
        let n = Node::new(NodeKind::Edge, addr(), "ap".into());
        let id = reg.register(n).await.unwrap();
        // manually age the heartbeat
        {
            let mut guard = reg.nodes.write().await;
            guard.get_mut(&id).unwrap().last_heartbeat =
                Some(Instant::now() - Duration::from_secs(100));
        }
        assert_eq!(reg.discover().await.len(), 0);
        assert_eq!(reg.dead_nodes().await.len(), 1);
    }

    #[tokio::test]
    async fn filter_by_kind_and_region() {
        let reg = NodeRegistry::new(Duration::from_secs(30));
        reg.register(Node::new(NodeKind::Compute, addr(), "us".into()))
            .await
            .unwrap();
        reg.register(Node::new(NodeKind::Storage, addr(), "eu".into()))
            .await
            .unwrap();
        assert_eq!(reg.discover_by_kind(NodeKind::Storage).await.len(), 1);
        assert_eq!(reg.discover_by_region("us").await.len(), 1);
    }

    #[test]
    fn node_serialization_roundtrip() {
        let n = Node::new(NodeKind::Edge, addr(), "ap".into());
        let json = serde_json::to_string(&n).unwrap();
        let back: Node = serde_json::from_str(&json).unwrap();
        assert_eq!(back.id, n.id);
        assert_eq!(back.kind, n.kind);
    }
}
