//! Convergent Replicated Data Types (CRDTs).
//!
//! All types here implement [`Crdt`] which guarantees that merging any two
//! replicas in any order yields the same result. Each type is serializable so
//! replicas can be shipped across the wire.

use crate::DistributedError;
use serde::{Deserialize, Serialize};
use std::cmp::Ordering;
use std::collections::{BTreeMap, BTreeSet, HashMap};
use tracing::debug;
use uuid::Uuid;

/// Behaviour shared by all CRDTs in this module.
pub trait Crdt: Clone + PartialEq {
    /// Merge `other` into `self`, producing a value that converges.
    fn merge(&mut self, other: &Self);

    /// Compute the merge without mutating `self`.
    fn merged(&self, other: &Self) -> Self {
        let mut clone = self.clone();
        clone.merge(other);
        clone
    }
}

/// Grow-only counter. Sum of per-node increments.
#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
pub struct GCounter {
    counts: HashMap<Uuid, u64>,
}

impl GCounter {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn increment(&mut self, node: Uuid, by: u64) {
        *self.counts.entry(node).or_insert(0) += by;
        debug!(node = %node, by, total = self.value(), "gcounter increment");
    }

    pub fn value(&self) -> u64 {
        self.counts.values().sum()
    }
}

impl Crdt for GCounter {
    fn merge(&mut self, other: &Self) {
        for (node, count) in &other.counts {
            let entry = self.counts.entry(*node).or_insert(0);
            if *count > *entry {
                *entry = *count;
            }
        }
    }
}

/// Positive-negative counter (two grow-only counters).
#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
pub struct PNCounter {
    increments: GCounter,
    decrements: GCounter,
}

impl PNCounter {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn increment(&mut self, node: Uuid, by: u64) {
        self.increments.increment(node, by);
    }

    pub fn decrement(&mut self, node: Uuid, by: u64) {
        self.decrements.increment(node, by);
    }

    pub fn value(&self) -> i64 {
        self.increments.value() as i64 - self.decrements.value() as i64
    }
}

impl Crdt for PNCounter {
    fn merge(&mut self, other: &Self) {
        self.increments.merge(&other.increments);
        self.decrements.merge(&other.decrements);
    }
}

/// Grow-only set.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct GSet<T: Ord + Clone> {
    elements: BTreeSet<T>,
}

impl<T: Ord + Clone> GSet<T> {
    pub fn new() -> Self {
        Self {
            elements: BTreeSet::new(),
        }
    }

    pub fn insert(&mut self, value: T) {
        self.elements.insert(value);
    }

    pub fn contains(&self, value: &T) -> bool {
        self.elements.contains(value)
    }

    pub fn iter(&self) -> impl Iterator<Item = &T> {
        self.elements.iter()
    }
}

impl<T: Ord + Clone> Crdt for GSet<T> {
    fn merge(&mut self, other: &Self) {
        self.elements.extend(other.elements.iter().cloned());
    }
}

/// Observed-Remove Set with unique tags per element.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ORSet<T: Ord + Clone> {
    added: BTreeSet<(T, Uuid)>,
    removed: BTreeSet<(T, Uuid)>,
}

impl<T: Ord + Clone> ORSet<T> {
    pub fn new() -> Self {
        Self {
            added: BTreeSet::new(),
            removed: BTreeSet::new(),
        }
    }

    pub fn add(&mut self, value: T, tag: Uuid) {
        self.added.insert((value, tag));
    }

    pub fn remove(&mut self, value: &T) {
        // Remove only tags currently observed as added.
        let tags: Vec<(T, Uuid)> = self
            .added
            .iter()
            .filter(|(v, _)| v == value)
            .cloned()
            .collect();
        for t in tags {
            self.added.remove(&t);
            self.removed.insert(t);
        }
    }

    pub fn contains(&self, value: &T) -> bool {
        self.added.iter().any(|(v, _)| v == value)
    }

    pub fn elements(&self) -> Vec<T> {
        let mut out: Vec<T> = self.added.iter().map(|(v, _)| v.clone()).collect();
        out.sort();
        out.dedup();
        out
    }
}

impl<T: Ord + Clone> Crdt for ORSet<T> {
    fn merge(&mut self, other: &Self) {
        self.added.extend(other.added.iter().cloned());
        self.removed.extend(other.removed.iter().cloned());
        // Recompute adds: drop any added entries explicitly removed.
        let removed: BTreeSet<(T, Uuid)> = self.removed.iter().cloned().collect();
        self.added.retain(|entry| !removed.contains(entry));
    }
}

/// Last-Writer-Wins register keyed by timestamp + node id tiebreak.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct LWWRegister<T: Clone> {
    pub value: T,
    pub timestamp: u64,
    pub node: Uuid,
}

impl<T: Clone> LWWRegister<T> {
    pub fn new(value: T, timestamp: u64, node: Uuid) -> Self {
        Self {
            value,
            timestamp,
            node,
        }
    }

    pub fn set(&mut self, value: T, timestamp: u64, node: Uuid) {
        self.value = value;
        self.timestamp = timestamp;
        self.node = node;
    }
}

impl<T: Clone + PartialEq> Crdt for LWWRegister<T> {
    fn merge(&mut self, other: &Self) {
        let wins = match other.timestamp.cmp(&self.timestamp) {
            Ordering::Greater => true,
            Ordering::Less => false,
            Ordering::Equal => other.node > self.node,
        };
        if wins {
            self.value = other.value.clone();
            self.timestamp = other.timestamp;
            self.node = other.node;
        }
    }
}

/// Per-node logical clock component.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct VectorClock {
    counters: BTreeMap<Uuid, u64>,
}

impl Default for VectorClock {
    fn default() -> Self {
        Self {
            counters: BTreeMap::new(),
        }
    }
}

impl VectorClock {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn increment(&mut self, node: Uuid) {
        *self.counters.entry(node).or_insert(0) += 1;
    }

    pub fn get(&self, node: &Uuid) -> u64 {
        self.counters.get(node).copied().unwrap_or(0)
    }

    /// Returns true if `self` happened-before `other` (strictly less).
    pub fn happens_before(&self, other: &VectorClock) -> bool {
        matches!(self.partial_cmp(other), Some(Ordering::Less))
    }

    /// Returns true if the two clocks are concurrent (incomparable).
    pub fn concurrent(&self, other: &VectorClock) -> bool {
        self.partial_cmp(other).is_none()
    }
}

impl PartialOrd for VectorClock {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        let mut less = false;
        let mut greater = false;
        let keys: BTreeSet<&Uuid> =
            self.counters.keys().chain(other.counters.keys()).collect();
        for k in keys {
            let a = self.counters.get(k).copied().unwrap_or(0);
            let b = other.counters.get(k).copied().unwrap_or(0);
            match a.cmp(&b) {
                Ordering::Less => less = true,
                Ordering::Greater => greater = true,
                Ordering::Equal => {}
            }
            if less && greater {
                return None; // concurrent
            }
        }
        match (less, greater) {
            (false, false) => Some(Ordering::Equal),
            (true, false) => Some(Ordering::Less),
            (false, true) => Some(Ordering::Greater),
            (true, true) => None,
        }
    }
}

impl Crdt for VectorClock {
    fn merge(&mut self, other: &Self) {
        for (node, counter) in &other.counters {
            let entry = self.counters.entry(*node).or_insert(0);
            if *counter > *entry {
                *entry = *counter;
            }
        }
    }
}

/// Serialize any CRDT to JSON bytes for transport.
pub fn to_json_bytes<T: Serialize>(value: &T) -> Result<Vec<u8>, DistributedError> {
    serde_json::to_vec(value).map_err(|e| DistributedError::Serialization(e.to_string()))
}

/// Deserialize CRDT from JSON bytes.
pub fn from_json_bytes<'a, T: serde::Deserialize<'a>>(
    bytes: &'a [u8],
) -> Result<T, DistributedError> {
    serde_json::from_slice(bytes).map_err(|e| DistributedError::Serialization(e.to_string()))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn nid(seed: u8) -> Uuid {
        Uuid::from_bytes([seed; 16])
    }

    #[test]
    fn gcounter_merge_converges() {
        let mut a = GCounter::new();
        let mut b = GCounter::new();
        a.increment(nid(1), 3);
        b.increment(nid(1), 5);
        b.increment(nid(2), 2);
        a.merge(&b);
        assert_eq!(a.value(), 7);
        // symmetric
        let mut b2 = b.clone();
        b2.merge(&GCounter { counts: [(nid(1), 3)].into() });
        assert_eq!(a, b2);
    }

    #[test]
    fn gcounter_commutative() {
        let mut a = GCounter::new();
        a.increment(nid(1), 4);
        let mut b = GCounter::new();
        b.increment(nid(2), 1);
        let ab = a.merged(&b);
        let ba = b.merged(&a);
        assert_eq!(ab, ba);
        assert_eq!(ab.value(), 5);
    }

    #[test]
    fn pncounter_negative() {
        let mut c = PNCounter::new();
        c.increment(nid(1), 10);
        c.decrement(nid(1), 4);
        assert_eq!(c.value(), 6);
        c.decrement(nid(2), 1);
        assert_eq!(c.value(), 5);
    }

    #[test]
    fn gset_union() {
        let mut a: GSet<u32> = GSet::new();
        let mut b: GSet<u32> = GSet::new();
        a.insert(1);
        b.insert(1);
        b.insert(2);
        a.merge(&b);
        assert!(a.contains(&1));
        assert!(a.contains(&2));
        assert_eq!(a.iter().count(), 2);
    }

    #[test]
    fn orset_add_remove_add() {
        let mut s: ORSet<String> = ORSet::new();
        s.add("a".into(), nid(1));
        assert!(s.contains(&"a".to_string()));
        s.remove(&"a".to_string());
        assert!(!s.contains(&"a".to_string()));
        s.add("a".into(), nid(2));
        assert!(s.contains(&"a".to_string()));
        assert_eq!(s.elements(), vec!["a".to_string()]);
    }

    #[test]
    fn orset_merge_respects_tombstones() {
        // Replica A removes after B adds the same tag -> stays removed on merge.
        let mut a: ORSet<String> = ORSet::new();
        let mut b: ORSet<String> = ORSet::new();
        a.add("x".into(), nid(9));
        b.merge(&a);
        b.remove(&"x".to_string());
        a.merge(&b);
        assert!(!a.contains(&"x".to_string()));
    }

    #[test]
    fn lww_register_wins_by_time() {
        let mut r = LWWRegister::new("old".to_string(), 1, nid(1));
        let other = LWWRegister::new("new".to_string(), 5, nid(2));
        r.merge(&other);
        assert_eq!(r.value, "new".to_string());
    }

    #[test]
    fn lww_register_tiebreak_by_node() {
        let mut r = LWWRegister::new("a".to_string(), 5, nid(1));
        let other = LWWRegister::new("b".to_string(), 5, nid(2));
        r.merge(&other);
        assert_eq!(r.value, "b".to_string());
    }

    #[test]
    fn vector_clock_ordering() {
        let mut a = VectorClock::new();
        let mut b = VectorClock::new();
        a.increment(nid(1));
        b.increment(nid(1));
        b.increment(nid(1));
        assert!(a.happens_before(&b));
        assert!(!b.happens_before(&a));
    }

    #[test]
    fn vector_clock_concurrent() {
        let mut a = VectorClock::new();
        let mut b = VectorClock::new();
        a.increment(nid(1));
        b.increment(nid(2));
        assert!(a.concurrent(&b));
        assert!(a.partial_cmp(&b).is_none());
    }

    #[test]
    fn vector_clock_merge() {
        let mut a = VectorClock::new();
        let mut b = VectorClock::new();
        a.increment(nid(1));
        b.increment(nid(2));
        b.increment(nid(2));
        a.merge(&b);
        assert_eq!(a.get(&nid(1)), 1);
        assert_eq!(a.get(&nid(2)), 2);
    }

    #[test]
    fn json_roundtrip_gcounter() {
        let mut c = GCounter::new();
        c.increment(nid(3), 7);
        let bytes = to_json_bytes(&c).unwrap();
        let back: GCounter = from_json_bytes(&bytes).unwrap();
        assert_eq!(c, back);
    }

    #[test]
    fn json_roundtrip_orset() {
        let mut s: ORSet<u32> = ORSet::new();
        s.add(1, nid(1));
        s.add(2, nid(2));
        let bytes = to_json_bytes(&s).unwrap();
        let back: ORSet<u32> = from_json_bytes(&bytes).unwrap();
        assert_eq!(s, back);
    }
}
