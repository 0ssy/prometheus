//! Distributed computing primitives for the Prometheus platform.
//!
//! This crate provides the building blocks for running P2 across a cluster:
//!
//! - [`node`] — node registry, discovery and heartbeats.
//! - [`crdt`] — convergent replicated data types (GCounter, PNCounter, GSet,
//!   ORSet, LWWRegister, VectorClock) with merge and serialize support.
//! - [`scheduler`] — work-stealing distributed task scheduler.
//! - [`sync`] — knowledge graph synchronization over CRDTs.

pub mod crdt;
pub mod node;
pub mod scheduler;
pub mod sync;

use thiserror::Error;

/// Errors shared across the distributed crate.
#[derive(Debug, Error)]
pub enum DistributedError {
    #[error("node {0} not found in registry")]
    NodeNotFound(String),
    #[error("duplicate node id {0}")]
    DuplicateNode(String),
    #[error("CRDT type mismatch: expected {expected}, got {got}")]
    CrdtTypeMismatch { expected: String, got: String },
    #[error("vector clock concurrency violation between {a} and {b}")]
    ClockConcurrency { a: String, b: String },
    #[error("scheduler rejected task: {0}")]
    Scheduler(String),
    #[error("serialization error: {0}")]
    Serialization(String),
    #[error("sync conflict on entity {0}")]
    SyncConflict(String),
}

pub type Result<T> = std::result::Result<T, DistributedError>;
