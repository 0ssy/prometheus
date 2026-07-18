//! Multi-tenant isolation with organization/team hierarchy.

use crate::{EnterpriseError, Result};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::RwLock;
use tracing::{debug, info};
use uuid::Uuid;

/// A tenant is an isolated organization.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Tenant {
    pub id: Uuid,
    pub name: String,
    pub plan: Plan,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum Plan {
    Free,
    Pro,
    Enterprise,
}

impl Plan {
    pub fn max_members(&self) -> usize {
        match self {
            Plan::Free => 5,
            Plan::Pro => 50,
            Plan::Enterprise => usize::MAX,
        }
    }

    pub fn label(&self) -> &'static str {
        match self {
            Plan::Free => "free",
            Plan::Pro => "pro",
            Plan::Enterprise => "enterprise",
        }
    }
}

/// A team within a tenant, used to group members and scope resources.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Team {
    pub id: Uuid,
    pub tenant_id: Uuid,
    pub name: String,
}

/// A member belongs to a tenant and optionally a set of teams.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Member {
    pub id: Uuid,
    pub tenant_id: Uuid,
    pub name: String,
    pub team_ids: Vec<Uuid>,
}

/// A tenancy manager isolating resources per tenant.
#[derive(Debug, Clone, Default)]
pub struct TenantManager {
    tenants: Arc<RwLock<HashMap<Uuid, Tenant>>>,
    teams: Arc<RwLock<HashMap<Uuid, Team>>>,
    members: Arc<RwLock<HashMap<Uuid, Member>>>,
}

impl TenantManager {
    pub fn new() -> Self {
        Self::default()
    }

    /// Create a new tenant with the given name and plan.
    pub async fn create_tenant(&self, name: &str, plan: Plan) -> Result<Tenant> {
        let mut guard = self.tenants.write().await;
        if guard.values().any(|t| t.name == name) {
            return Err(EnterpriseError::DuplicateTenant(name.to_string()));
        }
        let tenant = Tenant {
            id: Uuid::new_v4(),
            name: name.to_string(),
            plan,
        };
        info!(tenant = %tenant.id, name, plan = plan.label(), "tenant created");
        guard.insert(tenant.id, tenant.clone());
        Ok(tenant)
    }

    pub async fn get_tenant(&self, id: &Uuid) -> Result<Tenant> {
        self.tenants
            .read()
            .await
            .get(id)
            .cloned()
            .ok_or_else(|| EnterpriseError::TenantNotFound(id.to_string()))
    }

    pub async fn set_plan(&self, id: &Uuid, plan: Plan) -> Result<()> {
        let mut guard = self.tenants.write().await;
        let t = guard
            .get_mut(id)
            .ok_or_else(|| EnterpriseError::TenantNotFound(id.to_string()))?;
        t.plan = plan;
        Ok(())
    }

    pub async fn create_team(&self, tenant_id: &Uuid, name: &str) -> Result<Team> {
        self.get_tenant(tenant_id).await?;
        let team = Team {
            id: Uuid::new_v4(),
            tenant_id: *tenant_id,
            name: name.to_string(),
        };
        self.teams.write().await.insert(team.id, team.clone());
        Ok(team)
    }

    /// Add a member to a tenant, enforcing the plan's member cap.
    pub async fn add_member(&self, tenant_id: &Uuid, name: &str) -> Result<Member> {
        let tenant = self.get_tenant(tenant_id).await?;
        let guard = self.members.read().await;
        let current = guard.values().filter(|m| &m.tenant_id == tenant_id).count();
        drop(guard);
        if current >= tenant.plan.max_members() {
            return Err(EnterpriseError::Billing(format!(
                "tenant {} reached member limit {}",
                tenant.name,
                tenant.plan.max_members()
            )));
        }
        let member = Member {
            id: Uuid::new_v4(),
            tenant_id: *tenant_id,
            name: name.to_string(),
            team_ids: Vec::new(),
        };
        self.members
            .write()
            .await
            .insert(member.id, member.clone());
        info!(member = %member.id, tenant = %tenant_id, "member added");
        Ok(member)
    }

    pub async fn assign_to_team(&self, member_id: &Uuid, team_id: &Uuid) -> Result<()> {
        let mut mg = self.members.write().await;
        let m = mg
            .get_mut(member_id)
            .ok_or_else(|| EnterpriseError::MemberNotFound(member_id.to_string(), "".into()))?;
        let tg = self.teams.read().await;
        let team = tg
            .get(team_id)
            .ok_or_else(|| EnterpriseError::TenantNotFound(team_id.to_string()))?;
        if team.tenant_id != m.tenant_id {
            return Err(EnterpriseError::TenantNotFound(
                "team not in member's tenant".into(),
            ));
        }
        if !m.team_ids.contains(team_id) {
            m.team_ids.push(*team_id);
        }
        debug!(member = %member_id, team = %team_id, "assigned to team");
        Ok(())
    }

    pub async fn members_of(&self, tenant_id: &Uuid) -> Vec<Member> {
        self.members
            .read()
            .await
            .values()
            .filter(|m| &m.tenant_id == tenant_id)
            .cloned()
            .collect()
    }

    pub async fn teams_of(&self, tenant_id: &Uuid) -> Vec<Team> {
        self.teams
            .read()
            .await
            .values()
            .filter(|t| &t.tenant_id == tenant_id)
            .cloned()
            .collect()
    }

    /// Strong isolation check: ensure a resource owned by `owner_tenant`
    /// can be accessed by `requester_tenant`.
    pub async fn can_access(&self, requester: &Uuid, owner: &Uuid) -> bool {
        requester == owner
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn create_and_fetch_tenant() {
        let tm = TenantManager::new();
        let t = tm.create_tenant("acme", Plan::Pro).await.unwrap();
        assert_eq!(tm.get_tenant(&t.id).await.unwrap().name, "acme");
    }

    #[tokio::test]
    async fn duplicate_tenant_rejected() {
        let tm = TenantManager::new();
        tm.create_tenant("acme", Plan::Free).await.unwrap();
        assert!(tm.create_tenant("acme", Plan::Free).await.is_err());
    }

    #[tokio::test]
    async fn member_cap_enforced() {
        let tm = TenantManager::new();
        let t = tm.create_tenant("tiny", Plan::Free).await.unwrap();
        for i in 0..5 {
            tm.add_member(&t.id, &format!("m{i}")).await.unwrap();
        }
        assert!(tm.add_member(&t.id, "overflow").await.is_err());
    }

    #[tokio::test]
    async fn team_hierarchy() {
        let tm = TenantManager::new();
        let t = tm.create_tenant("acme", Plan::Pro).await.unwrap();
        let team = tm.create_team(&t.id, "eng").await.unwrap();
        let m = tm.add_member(&t.id, "alice").await.unwrap();
        tm.assign_to_team(&m.id, &team.id).await.unwrap();
        let member = tm.members_of(&t.id).await;
        assert_eq!(member[0].team_ids, vec![team.id]);
    }

    #[tokio::test]
    async fn cross_tenant_assignment_blocked() {
        let tm = TenantManager::new();
        let a = tm.create_tenant("a", Plan::Pro).await.unwrap();
        let b = tm.create_tenant("b", Plan::Pro).await.unwrap();
        let team_b = tm.create_team(&b.id, "t").await.unwrap();
        let m = tm.add_member(&a.id, "x").await.unwrap();
        assert!(tm.assign_to_team(&m.id, &team_b.id).await.is_err());
    }

    #[tokio::test]
    async fn isolation_check() {
        let tm = TenantManager::new();
        let a = tm.create_tenant("a", Plan::Pro).await.unwrap();
        let b = tm.create_tenant("b", Plan::Pro).await.unwrap();
        assert!(tm.can_access(&a.id, &a.id).await);
        assert!(!tm.can_access(&a.id, &b.id).await);
    }

    #[test]
    fn plan_limits() {
        assert_eq!(Plan::Free.max_members(), 5);
        assert_eq!(Plan::Enterprise.max_members(), usize::MAX);
    }
}
