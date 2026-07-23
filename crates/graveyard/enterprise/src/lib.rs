//! Enterprise features: multi-tenant isolation, RBAC and billing.
//!
//! - [`tenant`] — organizations, teams and resource isolation.
//! - [`rbac`] — role-based access control and permissions.
//! - [`billing`] — usage metering and invoice generation.

pub mod billing;
pub mod rbac;
pub mod tenant;

use thiserror::Error;

#[derive(Debug, Error)]
pub enum EnterpriseError {
    #[error("tenant {0} not found")]
    TenantNotFound(String),
    #[error("duplicate tenant {0}")]
    DuplicateTenant(String),
    #[error("member {0} not found in tenant {1}")]
    MemberNotFound(String, String),
    #[error("permission denied: {0} on {1}")]
    PermissionDenied(String, String),
    #[error("role {0} not found")]
    RoleNotFound(String),
    #[error("billing record error: {0}")]
    Billing(String),
    #[error("database error: {0}")]
    Database(String),
}

pub type Result<T> = std::result::Result<T, EnterpriseError>;
