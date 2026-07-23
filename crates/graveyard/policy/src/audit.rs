//! Audit logging for policy decisions.

use crate::rule::{Effect, Request};
use serde::{Deserialize, Serialize};
use std::collections::VecDeque;
use uuid::Uuid;

/// A single recorded policy decision.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DecisionRecord {
    pub id: Uuid,
    pub subject: Uuid,
    pub action: String,
    pub resource_kind: String,
    pub decision: Effect,
    pub rule_id: Option<Uuid>,
    pub rule_name: Option<String>,
}

impl DecisionRecord {
    pub fn new(
        req: &Request,
        decision: Effect,
        rule_id: Option<Uuid>,
        rule_name: Option<String>,
    ) -> Self {
        Self {
            id: Uuid::new_v4(),
            subject: req.subject.id,
            action: req.action.clone(),
            resource_kind: req.resource.kind.clone(),
            decision,
            rule_id,
            rule_name,
        }
    }
}

/// Append-only audit log with bounded retention.
#[derive(Debug, Clone, Default)]
pub struct AuditLog {
    pub entries: VecDeque<DecisionRecord>,
    limit: usize,
}

impl AuditLog {
    pub fn new() -> Self {
        Self {
            entries: VecDeque::new(),
            limit: 10000,
        }
    }

    pub fn with_limit(limit: usize) -> Self {
        Self {
            entries: VecDeque::new(),
            limit,
        }
    }

    pub fn append(&mut self, record: DecisionRecord) {
        self.entries.push_back(record);
        while self.entries.len() > self.limit {
            self.entries.pop_front();
        }
    }

    /// All decisions for a subject.
    pub fn for_subject(&self, subject: &Uuid) -> Vec<DecisionRecord> {
        self.entries
            .iter()
            .filter(|r| &r.subject == subject)
            .cloned()
            .collect()
    }

    /// All deny decisions (useful for compliance review).
    pub fn denials(&self) -> Vec<DecisionRecord> {
        self.entries
            .iter()
            .filter(|r| r.decision == Effect::Deny)
            .cloned()
            .collect()
    }

    pub fn len(&self) -> usize {
        self.entries.len()
    }

    pub fn is_empty(&self) -> bool {
        self.entries.is_empty()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::rule::{Subject, ResourceRef};
    use std::collections::HashMap;

    fn record(action: &str, decision: Effect) -> DecisionRecord {
        let req = Request {
            subject: Subject { id: Uuid::from_bytes([1;16]), roles: vec![], tenant: Uuid::from_bytes([2;16]) },
            action: action.into(),
            resource: ResourceRef { kind: "model".into(), id: Uuid::from_bytes([3;16]), owner: Uuid::from_bytes([2;16]) },
            attributes: HashMap::new(),
        };
        DecisionRecord::new(&req, decision, None, None)
    }

    #[test]
    fn append_and_query() {
        let mut log = AuditLog::new();
        log.append(record("read", Effect::Allow));
        log.append(record("delete", Effect::Deny));
        assert_eq!(log.len(), 2);
        assert_eq!(log.denials().len(), 1);
    }

    #[test]
    fn for_subject_filter() {
        let mut log = AuditLog::new();
        let sub = Uuid::from_bytes([9;16]);
        let req = Request {
            subject: Subject { id: sub, roles: vec![], tenant: Uuid::from_bytes([2;16]) },
            action: "x".into(),
            resource: ResourceRef { kind: "model".into(), id: Uuid::from_bytes([3;16]), owner: Uuid::from_bytes([2;16]) },
            attributes: HashMap::new(),
        };
        log.append(DecisionRecord::new(&req, Effect::Allow, None, None));
        assert_eq!(log.for_subject(&sub).len(), 1);
        assert_eq!(log.for_subject(&Uuid::from_bytes([8;16])).len(), 0);
    }

    #[test]
    fn respects_limit() {
        let mut log = AuditLog::with_limit(2);
        log.append(record("a", Effect::Allow));
        log.append(record("b", Effect::Allow));
        log.append(record("c", Effect::Allow));
        assert_eq!(log.len(), 2);
        assert_eq!(log.entries.back().unwrap().action, "c");
    }
}
