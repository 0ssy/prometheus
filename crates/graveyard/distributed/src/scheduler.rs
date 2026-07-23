//! Distributed task scheduling with work-stealing.
//!
//! A [`Scheduler`] owns a set of [`Worker`]s, each with its own local queue.
//! Producers push tasks to the scheduler; the scheduler assigns them to the
//! least-loaded worker. Idle workers [`steal`](Worker::try_steal) from busy
//! peers to keep the cluster balanced.

use crate::{DistributedError, Result};
use serde::{Deserialize, Serialize};
use std::collections::VecDeque;
use std::sync::Arc;
use tokio::sync::{mpsc, Mutex, Notify};
use tracing::{debug, info, warn};
use uuid::Uuid;

/// A unit of scheduled work.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Task {
    pub id: Uuid,
    pub payload: String,
    pub priority: u8,
    pub affinity: Option<Uuid>,
}

impl Task {
    pub fn new(payload: String) -> Self {
        Self {
            id: Uuid::new_v4(),
            payload,
            priority: 128,
            affinity: None,
        }
    }

    pub fn with_priority(mut self, priority: u8) -> Self {
        self.priority = priority;
        self
    }

    pub fn with_affinity(mut self, node: Uuid) -> Self {
        self.affinity = Some(node);
        self
    }
}

/// A single worker with a local queue and a steal channel.
#[derive(Debug)]
pub struct Worker {
    pub id: Uuid,
    queue: Mutex<VecDeque<Task>>,
    stolen_tx: mpsc::UnboundedSender<Task>,
    ready: Notify,
}

impl Worker {
    pub fn new(id: Uuid) -> (Arc<Self>, mpsc::UnboundedReceiver<Task>) {
        let (stolen_tx, stolen_rx) = mpsc::unbounded_channel();
        let w = Arc::new(Self {
            id,
            queue: Mutex::new(VecDeque::new()),
            stolen_tx,
            ready: Notify::new(),
        });
        (w, stolen_rx)
    }

    async fn push_local(&self, task: Task) {
        let mut q = self.queue.lock().await;
        // higher priority first
        let pos = q
            .iter()
            .position(|t| t.priority < task.priority)
            .unwrap_or(q.len());
        q.insert(pos, task);
        self.ready.notify_one();
    }

    pub async fn local_len(&self) -> usize {
        self.queue.lock().await.len()
    }

    /// Pop the highest-priority task; returns None if idle.
    pub async fn pop(&self) -> Option<Task> {
        let mut q = self.queue.lock().await;
        q.pop_front()
    }

    /// Attempt to steal the highest-priority task from this worker.
    pub async fn try_steal(&self) -> Option<Task> {
        let mut q = self.queue.lock().await;
        if q.len() > 1 {
            // Keep at least one task for the owner.
            q.pop_back()
        } else {
            None
        }
    }

    /// Run the worker loop: execute local tasks, then steal from peers.
    pub async fn run(
        self: Arc<Self>,
        stolen_rx: mpsc::UnboundedReceiver<Task>,
        peers: Vec<Arc<Worker>>,
        mut shutdown: mpsc::Receiver<()>,
    ) {
        let mut stolen_rx = stolen_rx;
        loop {
            tokio::select! {
                Some(task) = stolen_rx.recv() => {
                    self.push_local(task).await;
                }
                _ = self.ready.notified() => {
                    if let Some(task) = self.pop().await {
                        info!(worker = %self.id, task = %task.id, "executing task");
                        debug!(payload = %task.payload, "task payload");
                    }
                }
                maybe = Self::steal_from_peers(&peers) => {
                    if let Some((from, task)) = maybe {
                        info!(worker = %self.id, from = %from, task = %task.id, "stole task");
                        self.push_local(task).await;
                    }
                }
                _ = shutdown.recv() => {
                    debug!(worker = %self.id, "shutting down");
                    break;
                }
            }
        }
    }

    async fn steal_from_peers(peers: &[Arc<Worker>]) -> Option<(Uuid, Task)> {
        for peer in peers {
            if let Some(task) = peer.try_steal().await {
                return Some((peer.id, task));
            }
        }
        None
    }
}

/// Distributes tasks across workers and supports work-stealing.
#[derive(Debug)]
pub struct Scheduler {
    workers: Vec<Arc<Worker>>,
    #[allow(dead_code)]
    handles: Vec<mpsc::UnboundedSender<Task>>,
}

impl Scheduler {
    pub async fn new(worker_count: usize) -> Self {
        let mut workers = Vec::new();
        let mut handles = Vec::new();
        for _ in 0..worker_count {
            let (w, rx) = Worker::new(Uuid::new_v4());
            let id = w.id;
            handles.push(w.stolen_tx.clone());
            workers.push(w.clone());
            let peers = workers.clone();
            let w_clone = w.clone();
            let (shutdown_tx, shutdown_rx) = mpsc::channel(1);
            std::mem::drop(shutdown_tx);
            tokio::spawn(w_clone.run(rx, peers, shutdown_rx));
            let _ = id;
        }
        Self { workers, handles }
    }

    /// Submit a task. Honors node affinity; otherwise picks the least-loaded worker.
    pub async fn submit(&self, task: Task) -> Result<()> {
        if self.workers.is_empty() {
            return Err(DistributedError::Scheduler("no workers".into()));
        }
        if let Some(target) = task.affinity {
            if let Some(w) = self.workers.iter().find(|w| w.id == target) {
                w.push_local(task).await;
                return Ok(());
            }
            warn!(target = %target, "affinity target not found, falling back");
        }
        // least-loaded worker
        let mut best = &self.workers[0];
        let mut best_len = best.local_len().await;
        for w in &self.workers[1..] {
            let len = w.local_len().await;
            if len < best_len {
                best = w;
                best_len = len;
            }
        }
        best.push_local(task).await;
        Ok(())
    }

    /// Number of tasks queued cluster-wide.
    pub async fn pending(&self) -> usize {
        let mut total = 0;
        for w in &self.workers {
            total += w.local_len().await;
        }
        total
    }

    pub fn worker_count(&self) -> usize {
        self.workers.len()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn submit_picks_worker() {
        let s = Scheduler::new(3).await;
        assert_eq!(s.worker_count(), 3);
        s.submit(Task::new("t1".into())).await.unwrap();
        assert_eq!(s.pending().await, 1);
    }

    #[tokio::test]
    async fn affinity_targets_worker() {
        let s = Scheduler::new(2).await;
        let target = s.workers[1].id;
        s.submit(Task::new("x".into()).with_affinity(target))
            .await
            .unwrap();
        assert_eq!(s.workers[1].local_len().await, 1);
        assert_eq!(s.workers[0].local_len().await, 0);
    }

    #[tokio::test]
    async fn priority_ordering() {
        let (w, _rx) = Worker::new(Uuid::new_v4());
        w.push_local(Task::new("low".into()).with_priority(1)).await;
        w.push_local(Task::new("high".into()).with_priority(255))
            .await;
        assert_eq!(w.pop().await.unwrap().payload, "high");
    }

    #[tokio::test]
    async fn steal_keeps_one() {
        let (w, _rx) = Worker::new(Uuid::new_v4());
        w.push_local(Task::new("a".into())).await;
        w.push_local(Task::new("b".into())).await;
        let stolen = w.try_steal().await.unwrap();
        assert_eq!(stolen.payload, "b");
        assert_eq!(w.local_len().await, 1);
    }

    #[tokio::test]
    async fn steal_nothing_when_single() {
        let (w, _rx) = Worker::new(Uuid::new_v4());
        w.push_local(Task::new("only".into())).await;
        assert!(w.try_steal().await.is_none());
    }

    #[test]
    fn task_builder() {
        let t = Task::new("p".into()).with_priority(200);
        assert_eq!(t.priority, 200);
        assert!(t.affinity.is_none());
    }
}
