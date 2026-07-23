//! Policy evaluation engine, rules and audit logging.
//!
//! - [`rule`] — policy rules, conditions and the context they evaluate.
//! - [`engine`] — evaluation engine applying ordered rules to a request.
//! - [`audit`] — append-only audit log of policy decisions.

pub mod audit;
pub mod engine;
pub mod rule;

use thiserror::Error;

#[derive(Debug, Error)]
pub enum PolicyError {
    #[error("rule {0} not found")]
    RuleNotFound(String),
    #[error("evaluation error: {0}")]
    Evaluation(String),
    #[error("invalid condition: {0}")]
    InvalidCondition(String),
    #[error("audit error: {0}")]
    Audit(String),
}

pub type Result<T> = std::result::Result<T, PolicyError>;
