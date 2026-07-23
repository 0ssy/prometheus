//! Role-based access control with permissions.

use crate::{EnterpriseError, Result};
use serde::{Deserialize, Serialize};
use std::collections::{HashMap, HashSet};
use std::sync::Arc;
use tokio::sync::RwLock;
use tracing::debug;
use uuid::Uuid;

/// A protected resource category.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum Resource {
    Tensor,
    Model,
    Driver,
    KnowledgeGraph,
    Billing,
    Tenant,
}

/// Actions that can be performed on a resource.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum Action {
    Read,
    Write,
    Delete,
    Execute,
    Manage,
}

/// A permission pair of (resource, action).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct Permission {
    pub resource: Resource,
    pub action: Action,
}

impl Permission {
    pub fn new(resource: Resource, action: Action) -> Self {
        Self { resource, action }
    }
}

/// A role bundles a set of permissions.
#[derive(Debug, Clone)]
pub struct Role {
    pub id: Uuid,
    pub name: String,
    permissions: HashSet<Permission>,
}

impl Role {
    pub fn new(name: &str, permissions: &[Permission]) -> Self {
        Self {
            id: Uuid::new_v4(),
            name: name.to_string(),
            permissions: permissions.iter().copied().collect(),
        }
    }

    pub fn has(&self, perm: &Permission) -> bool {
        self.permissions.contains(perm)
    }

    pub fn grant(&mut self, perm: Permission) {
        self.permissions.insert(perm);
    }
}

/// A principal (member) and the roles assigned to them.
#[derive(Debug, Clone)]
pub struct Principal {
    pub id: Uuid,
    pub name: String,
    role_ids: HashSet<Uuid>,
}

impl Principal {
    pub fn new(name: &str) -> Self {
        Self {
            id: Uuid::new_v4(),
            name: name.to_string(),
            role_ids: HashSet::new(),
        }
    }
}

/// The RBAC engine: roles, principals and permission checks.
#[derive(Debug, Clone, Default)]
pub struct RbacEngine {
    roles: Arc<RwLock<HashMap<Uuid, Role>>>,
    principals: Arc<RwLock<HashMap<Uuid, Principal>>>,
}

impl RbacEngine {
    pub fn new() -> Self {
        Self::default()
    }

    /// Create the well-known built-in roles used by the platform.
    pub async fn with_builtins() -> Self {
        let engine = Self::new();
        let admin = Role::new(
            "admin",
            &[
                Permission::new(Resource::Tensor, Action::Manage),
                Permission::new(Resource::Model, Action::Manage),
                Permission::new(Resource::Driver, Action::Manage),
                Permission::new(Resource::KnowledgeGraph, Action::Manage),
                Permission::new(Resource::Billing, Action::Manage),
                Permission::new(Resource::Tenant, Action::Manage),
            ],
        );
        let viewer = Role::new(
            "viewer",
            &[
                Permission::new(Resource::Tensor, Action::Read),
                Permission::new(Resource::Model, Action::Read),
                Permission::new(Resource::KnowledgeGraph, Action::Read),
            ],
        );
        let operator = Role::new(
            "operator",
            &[
                Permission::new(Resource::Driver, Action::Manage),
                Permission::new(Resource::Tensor, Action::Execute),
                Permission::new(Resource::Model, Action::Write),
            ],
        );
        engine.roles.write().await.insert(admin.id, admin);
        engine.roles.write().await.insert(viewer.id, viewer);
        engine.roles.write().await.insert(operator.id, operator);
        engine
    }

    pub async fn create_role(&self, role: Role) {
        self.roles.write().await.insert(role.id, role);
    }

    pub async fn get_role(&self, id: &Uuid) -> Result<Role> {
        self.roles
            .read()
            .await
            .get(id)
            .cloned()
            .ok_or_else(|| EnterpriseError::RoleNotFound(id.to_string()))
    }

    pub async fn register_principal(&self, principal: Principal) {
        self.principals
            .write()
            .await
            .insert(principal.id, principal);
    }

    pub async fn assign_role(&self, principal_id: &Uuid, role_id: &Uuid) -> Result<()> {
        // ensure role exists
        self.get_role(role_id).await?;
        let mut pg = self.principals.write().await;
        let p = pg
            .get_mut(principal_id)
            .ok_or_else(|| EnterpriseError::RoleNotFound(principal_id.to_string()))?;
        p.role_ids.insert(*role_id);
        debug!(principal = %principal_id, role = %role_id, "role assigned");
        Ok(())
    }

    /// Check whether a principal may perform `action` on `resource`.
    pub async fn authorize(
        &self,
        principal_id: &Uuid,
        resource: Resource,
        action: Action,
    ) -> Result<()> {
        let pg = self.principals.read().await;
        let p = pg
            .get(principal_id)
            .ok_or_else(|| EnterpriseError::RoleNotFound(principal_id.to_string()))?;
        let rg = self.roles.read().await;
        let perm = Permission::new(resource, action);
        for rid in &p.role_ids {
            if let Some(role) = rg.get(rid) {
                if role.has(&perm) {
                    return Ok(());
                }
            }
        }
        Err(EnterpriseError::PermissionDenied(
            format!("{:?}", action),
            format!("{:?}", resource),
        ))
    }

    pub async fn can(&self, principal_id: &Uuid, resource: Resource, action: Action) -> bool {
        self.authorize(principal_id, resource, action).await.is_ok()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn admin_can_manage_all() {
        let rbac = RbacEngine::with_builtins().await;
        let p = Principal::new("boss");
        let admin_role = {
            let rg = rbac.roles.read().await;
            rg.values().find(|r| r.name == "admin").unwrap().id
        };
        rbac.register_principal(p.clone()).await;
        rbac.assign_role(&p.id, &admin_role).await.unwrap();
        assert!(rbac
            .can(&p.id, Resource::Tensor, Action::Manage)
            .await);
        assert!(rbac
            .can(&p.id, Resource::Billing, Action::Manage)
            .await);
    }

    #[tokio::test]
    async fn viewer_cannot_write() {
        let rbac = RbacEngine::with_builtins().await;
        let p = Principal::new("peon");
        let viewer = {
            let rg = rbac.roles.read().await;
            rg.values().find(|r| r.name == "viewer").unwrap().id
        };
        rbac.register_principal(p.clone()).await;
        rbac.assign_role(&p.id, &viewer).await.unwrap();
        assert!(rbac.can(&p.id, Resource::Model, Action::Read).await);
        assert!(!rbac.can(&p.id, Resource::Model, Action::Write).await);
    }

    #[tokio::test]
    async fn operator_can_execute() {
        let rbac = RbacEngine::with_builtins().await;
        let p = Principal::new("ops");
        let op = {
            let rg = rbac.roles.read().await;
            rg.values().find(|r| r.name == "operator").unwrap().id
        };
        rbac.register_principal(p.clone()).await;
        rbac.assign_role(&p.id, &op).await.unwrap();
        assert!(rbac.can(&p.id, Resource::Tensor, Action::Execute).await);
        assert!(!rbac.can(&p.id, Resource::Billing, Action::Manage).await);
    }

    #[tokio::test]
    async fn unknown_principal_denied() {
        let rbac = RbacEngine::with_builtins().await;
        let pid = Uuid::new_v4();
        assert!(rbac
            .authorize(&pid, Resource::Tensor, Action::Read)
            .await
            .is_err());
    }

    #[tokio::test]
    async fn custom_role_grant() {
        let rbac = RbacEngine::new();
        let mut role = Role::new("custom", &[]);
        role.grant(Permission::new(Resource::Driver, Action::Write));
        rbac.create_role(role.clone()).await;
        let p = Principal::new("c");
        rbac.register_principal(p.clone()).await;
        rbac.assign_role(&p.id, &role.id).await.unwrap();
        assert!(rbac.can(&p.id, Resource::Driver, Action::Write).await);
    }
}
