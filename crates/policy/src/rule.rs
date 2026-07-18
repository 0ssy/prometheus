//! Policy rules and conditions.

use crate::PolicyError;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use tracing::debug;
use uuid::Uuid;

/// The subject making a request.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Subject {
    pub id: Uuid,
    pub roles: Vec<String>,
    pub tenant: Uuid,
}

/// The resource a request targets.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ResourceRef {
    pub kind: String,
    pub id: Uuid,
    pub owner: Uuid,
}

/// A request presented to the policy engine for evaluation.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Request {
    pub subject: Subject,
    pub action: String,
    pub resource: ResourceRef,
    pub attributes: HashMap<String, String>,
}

impl Request {
    pub fn attr(&self, key: &str) -> Option<&str> {
        self.attributes.get(key).map(|s| s.as_str())
    }
}

/// Comparison operators usable in conditions.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum Op {
    Equals,
    NotEquals,
    In,
    GreaterThan,
    LessThan,
}

/// A condition compares a field of the request against a value.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Condition {
    pub field: String,
    pub op: Op,
    pub value: String,
}

impl Condition {
    /// Evaluate the condition against a request.
    pub fn eval(&self, req: &Request) -> crate::Result<bool> {
        let actual = self.lookup(req)?;
        let result = match self.op {
            Op::Equals => actual == self.value,
            Op::NotEquals => actual != self.value,
            Op::In => actual.split(',').any(|v| v.trim() == self.value),
            Op::GreaterThan => actual
                .parse::<i64>()
                .map(|a| self.value.parse::<i64>().map(|b| a > b).unwrap_or(false))
                .unwrap_or(false),
            Op::LessThan => actual
                .parse::<i64>()
                .map(|a| self.value.parse::<i64>().map(|b| a < b).unwrap_or(false))
                .unwrap_or(false),
        };
        debug!(field = %self.field, op = ?self.op, result, "condition eval");
        Ok(result)
    }

    fn lookup(&self, req: &Request) -> crate::Result<String> {
        match self.field.as_str() {
            "subject.id" => Ok(req.subject.id.to_string()),
            "subject.tenant" => Ok(req.subject.tenant.to_string()),
            "subject.role" => Ok(req.subject.roles.join(",")),
            "action" => Ok(req.action.clone()),
            "resource.kind" => Ok(req.resource.kind.clone()),
            "resource.owner" => Ok(req.resource.owner.to_string()),
            other => req
                .attr(other)
                .map(|s| s.to_string())
                .ok_or_else(|| PolicyError::InvalidCondition(other.to_string())),
        }
    }
}

/// Effect a rule produces when its conditions match.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum Effect {
    Allow,
    Deny,
}

/// A policy rule: conditions combined with AND, producing an effect.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Rule {
    pub id: Uuid,
    pub name: String,
    pub effect: Effect,
    pub priority: i32,
    pub conditions: Vec<Condition>,
}

impl Rule {
    pub fn new(name: &str, effect: Effect, conditions: Vec<Condition>) -> Self {
        Self {
            id: Uuid::new_v4(),
            name: name.to_string(),
            effect,
            priority: 0,
            conditions,
        }
    }

    pub fn with_priority(mut self, priority: i32) -> Self {
        self.priority = priority;
        self
    }

    /// A rule matches if all its conditions are true.
    pub fn matches(&self, req: &Request) -> crate::Result<bool> {
        for c in &self.conditions {
            if !c.eval(req)? {
                return Ok(false);
            }
        }
        Ok(true)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn subject() -> Subject {
        Subject {
            id: Uuid::from_bytes([1; 16]),
            roles: vec!["admin".into()],
            tenant: Uuid::from_bytes([2; 16]),
        }
    }

    fn request() -> Request {
        Request {
            subject: subject(),
            action: "delete".into(),
            resource: ResourceRef {
                kind: "model".into(),
                id: Uuid::from_bytes([3; 16]),
                owner: Uuid::from_bytes([2; 16]),
            },
            attributes: [("region".to_string(), "us".to_string())].into(),
        }
    }

    #[test]
    fn condition_equals() {
        let c = Condition {
            field: "action".into(),
            op: Op::Equals,
            value: "delete".into(),
        };
        assert!(c.eval(&request()).unwrap());
    }

    #[test]
    fn condition_in_role() {
        let c = Condition {
            field: "subject.role".into(),
            op: Op::In,
            value: "admin".into(),
        };
        assert!(c.eval(&request()).unwrap());
    }

    #[test]
    fn condition_greater_than() {
        let mut attrs = HashMap::new();
        attrs.insert("size".to_string(), "100".to_string());
        let mut req = request();
        req.attributes = attrs;
        let c = Condition {
            field: "size".into(),
            op: Op::GreaterThan,
            value: "50".into(),
        };
        assert!(c.eval(&req).unwrap());
    }

    #[test]
    fn rule_matches_all_conditions() {
        let rule = Rule::new(
            "owner-only",
            Effect::Allow,
            vec![
                Condition { field: "subject.tenant".into(), op: Op::Equals, value: Uuid::from_bytes([2;16]).to_string() },
                Condition { field: "action".into(), op: Op::Equals, value: "delete".into() },
            ],
        );
        assert!(rule.matches(&request()).unwrap());
    }

    #[test]
    fn rule_fails_when_one_condition_false() {
        let rule = Rule::new(
            "owner-only",
            Effect::Allow,
            vec![
                Condition { field: "action".into(), op: Op::Equals, value: "delete".into() },
                Condition { field: "resource.kind".into(), op: Op::Equals, value: "tensor".into() },
            ],
        );
        assert!(!rule.matches(&request()).unwrap());
    }
}
