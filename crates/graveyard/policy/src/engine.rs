//! Policy evaluation engine.

use crate::audit::{AuditLog, DecisionRecord};
use crate::rule::{Effect, Request, Rule};
use crate::{PolicyError, Result};
use std::sync::Arc;
use tokio::sync::RwLock;
use tracing::info;
use uuid::Uuid;

/// Evaluates ordered rules against requests, recording decisions.
#[derive(Clone)]
pub struct PolicyEngine {
    rules: Arc<RwLock<Vec<Rule>>>,
    audit: Arc<RwLock<AuditLog>>,
    /// Default effect when no rule matches.
    default: Effect,
}

impl PolicyEngine {
    pub fn new() -> Self {
        Self {
            rules: Arc::new(RwLock::new(Vec::new())),
            audit: Arc::new(RwLock::new(AuditLog::new())),
            default: Effect::Deny,
        }
    }

    pub fn with_default(default: Effect) -> Self {
        Self {
            default,
            ..Self::new()
        }
    }

    /// Add a rule; rules are kept sorted by descending priority.
    pub async fn add_rule(&self, rule: Rule) {
        let mut guard = self.rules.write().await;
        guard.push(rule);
        guard.sort_by(|a, b| b.priority.cmp(&a.priority));
    }

    pub async fn list_rules(&self) -> Vec<Rule> {
        self.rules.read().await.clone()
    }

    pub async fn remove_rule(&self, id: &Uuid) -> Result<()> {
        let mut guard = self.rules.write().await;
        let before = guard.len();
        guard.retain(|r| &r.id != id);
        if guard.len() == before {
            return Err(PolicyError::RuleNotFound(id.to_string()));
        }
        Ok(())
    }

    /// Evaluate a request and return the decision plus the matching rule id.
    pub async fn evaluate(&self, req: &Request) -> Result<DecisionRecord> {
        let rules = self.rules.read().await;
        let mut matched: Option<&Rule> = None;
        for rule in rules.iter() {
            if rule.matches(req)? {
                matched = Some(rule);
                break;
            }
        }
        let decision = match matched {
            Some(r) => r.effect,
            None => self.default,
        };
        let record = DecisionRecord::new(
            req,
            decision,
            matched.map(|r| r.id),
            matched.map(|r| r.name.clone()),
        );
        info!(decision = ?decision, rule = ?matched.map(|r| &r.name), "policy evaluated");
        self.audit.write().await.append(record.clone());
        Ok(record)
    }

    /// Convenience: returns true only when the decision is Allow.
    pub async fn is_allowed(&self, req: &Request) -> bool {
        matches!(self.evaluate(req).await, Ok(r) if r.decision == Effect::Allow)
    }

    pub async fn audit_log(&self) -> AuditLog {
        self.audit.read().await.clone()
    }
}

impl Default for PolicyEngine {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::rule::{Condition, Op, Rule};
    use std::collections::HashMap;

    fn req(role: &str, action: &str) -> Request {
        Request {
            subject: crate::rule::Subject {
                id: Uuid::from_bytes([1; 16]),
                roles: vec![role.into()],
                tenant: Uuid::from_bytes([2; 16]),
            },
            action: action.into(),
            resource: crate::rule::ResourceRef {
                kind: "model".into(),
                id: Uuid::from_bytes([3; 16]),
                owner: Uuid::from_bytes([2; 16]),
            },
            attributes: HashMap::new(),
        }
    }

    #[tokio::test]
    async fn allow_when_rule_matches() {
        let engine = PolicyEngine::new();
        engine
            .add_rule(Rule::new(
                "admins-write",
                Effect::Allow,
                vec![Condition {
                    field: "subject.role".into(),
                    op: Op::In,
                    value: "admin".into(),
                }],
            ))
            .await;
        let d = engine.evaluate(&req("admin", "write")).await.unwrap();
        assert_eq!(d.decision, Effect::Allow);
    }

    #[tokio::test]
    async fn deny_by_default() {
        let engine = PolicyEngine::new();
        let d = engine.evaluate(&req("guest", "write")).await.unwrap();
        assert_eq!(d.decision, Effect::Deny);
    }

    #[tokio::test]
    async fn explicit_deny_rule() {
        let engine = PolicyEngine::with_default(Effect::Allow);
        engine
            .add_rule(Rule::new(
                "block-delete",
                Effect::Deny,
                vec![Condition {
                    field: "action".into(),
                    op: Op::Equals,
                    value: "delete".into(),
                }],
            ))
            .await;
        let d = engine.evaluate(&req("admin", "delete")).await.unwrap();
        assert_eq!(d.decision, Effect::Deny);
    }

    #[tokio::test]
    async fn priority_ordering() {
        let engine = PolicyEngine::new();
        engine
            .add_rule(Rule::new("wide-allow", Effect::Allow, vec![]).with_priority(10))
            .await;
        engine
            .add_rule(
                Rule::new(
                    "specific-deny",
                    Effect::Deny,
                    vec![Condition { field: "action".into(), op: Op::Equals, value: "delete".into() }],
                )
                .with_priority(100),
            )
            .await;
        // higher priority deny wins even though allow matches all
        let d = engine.evaluate(&req("x", "delete")).await.unwrap();
        assert_eq!(d.decision, Effect::Deny);
    }

    #[tokio::test]
    async fn audit_records_decisions() {
        let engine = PolicyEngine::new();
        engine
            .add_rule(Rule::new("allow-all", Effect::Allow, vec![]))
            .await;
        engine.evaluate(&req("a", "read")).await.unwrap();
        engine.evaluate(&req("a", "write")).await.unwrap();
        let log = engine.audit_log().await;
        assert_eq!(log.entries.len(), 2);
    }

    #[tokio::test]
    async fn remove_rule() {
        let engine = PolicyEngine::new();
        let rule = Rule::new("r", Effect::Allow, vec![]);
        engine.add_rule(rule.clone()).await;
        assert_eq!(engine.list_rules().await.len(), 1);
        engine.remove_rule(&rule.id).await.unwrap();
        assert_eq!(engine.list_rules().await.len(), 0);
    }
}
