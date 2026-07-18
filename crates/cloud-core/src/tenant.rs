use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use thiserror::Error;
use tracing::{debug, info, warn};
use uuid::Uuid;

pub type TenantId = Uuid;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Hash)]
pub struct Organization {
    pub id: Uuid,
    pub name: String,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

impl Organization {
    pub fn new(name: impl Into<String>) -> Self {
        let now = Utc::now();
        Self {
            id: Uuid::new_v4(),
            name: name.into(),
            created_at: now,
            updated_at: now,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Hash)]
pub struct Team {
    pub id: Uuid,
    pub org_id: Uuid,
    pub name: String,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

impl Team {
    pub fn new(org_id: Uuid, name: impl Into<String>) -> Self {
        let now = Utc::now();
        Self {
            id: Uuid::new_v4(),
            org_id,
            name: name.into(),
            created_at: now,
            updated_at: now,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Tenant {
    pub id: TenantId,
    pub name: String,
    pub org_id: Uuid,
    pub team_id: Option<Uuid>,
    pub metadata: HashMap<String, String>,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
    pub is_active: bool,
}

impl Tenant {
    pub fn new(name: impl Into<String>, org_id: Uuid, team_id: Option<Uuid>) -> Self {
        let now = Utc::now();
        let mut metadata = HashMap::new();
        metadata.insert("environment".to_string(), "default".to_string());
        Self {
            id: Uuid::new_v4(),
            name: name.into(),
            org_id,
            team_id,
            metadata,
            created_at: now,
            updated_at: now,
            is_active: true,
        }
    }

    pub fn with_metadata(mut self, key: impl Into<String>, value: impl Into<String>) -> Self {
        self.metadata.insert(key.into(), value.into());
        self.updated_at = Utc::now();
        self
    }

    pub fn deactivate(&mut self) {
        self.is_active = false;
        self.updated_at = Utc::now();
        warn!(tenant_id = %self.id, "tenant deactivated");
    }

    pub fn activate(&mut self) {
        self.is_active = true;
        self.updated_at = Utc::now();
        info!(tenant_id = %self.id, "tenant activated");
    }
}

#[derive(Debug, Error)]
pub enum TenantError {
    #[error("tenant not found: {tenant_id}")]
    NotFound { tenant_id: TenantId },

    #[error("organization not found: {org_id}")]
    OrgNotFound { org_id: Uuid },

    #[error("team not found: {team_id}")]
    TeamNotFound { team_id: Uuid },

    #[error("tenant already exists: {name}")]
    AlreadyExists { name: String },

    #[error("invalid tenant state transition")]
    InvalidStateTransition,

    #[error("serialization error: {0}")]
    Serialization(#[from] serde_json::Error),
}

pub struct TenantManager {
    tenants: HashMap<TenantId, Tenant>,
    orgs: HashMap<Uuid, Organization>,
    teams: HashMap<Uuid, Team>,
    org_tenants: HashMap<Uuid, Vec<TenantId>>,
    team_tenants: HashMap<Uuid, Vec<TenantId>>,
}

impl TenantManager {
    pub fn new() -> Self {
        info!("initializing tenant manager");
        Self {
            tenants: HashMap::new(),
            orgs: HashMap::new(),
            teams: HashMap::new(),
            org_tenants: HashMap::new(),
            team_tenants: HashMap::new(),
        }
    }

    pub fn create_org(&mut self, name: impl Into<String>) -> Organization {
        let org = Organization::new(name);
        info!(org_id = %org.id, org_name = %org.name, "created organization");
        self.orgs.insert(org.id, org.clone());
        org
    }

    pub fn get_org(&self, org_id: Uuid) -> Option<&Organization> {
        self.orgs.get(&org_id)
    }

    pub fn create_team(&mut self, org_id: Uuid, name: impl Into<String>) -> Result<Team, TenantError> {
        if !self.orgs.contains_key(&org_id) {
            return Err(TenantError::OrgNotFound { org_id });
        }
        let team = Team::new(org_id, name);
        info!(team_id = %team.id, org_id = %org_id, team_name = %team.name, "created team");
        self.teams.insert(team.id, team.clone());
        Ok(team)
    }

    pub fn get_team(&self, team_id: Uuid) -> Option<&Team> {
        self.teams.get(&team_id)
    }

    pub fn create_tenant(
        &mut self,
        name: impl Into<String>,
        org_id: Uuid,
        team_id: Option<Uuid>,
    ) -> Result<Tenant, TenantError> {
        let name = name.into();
        if !self.orgs.contains_key(&org_id) {
            return Err(TenantError::OrgNotFound { org_id });
        }
        if let Some(tid) = team_id {
            if !self.teams.contains_key(&tid) {
                return Err(TenantError::TeamNotFound { team_id: tid });
            }
        }

        if self.tenants.values().any(|t| t.name == name && t.org_id == org_id) {
            return Err(TenantError::AlreadyExists { name });
        }

        let tenant = Tenant::new(name, org_id, team_id);
        let tenant_id = tenant.id;
        debug!(tenant_id = %tenant_id, org_id = %org_id, "creating tenant");

        self.org_tenants
            .entry(org_id)
            .or_default()
            .push(tenant_id);
        if let Some(tid) = team_id {
            self.team_tenants.entry(tid).or_default().push(tenant_id);
        }

        self.tenants.insert(tenant_id, tenant.clone());
        info!(tenant_id = %tenant_id, name = %tenant.name, "tenant created");
        Ok(tenant)
    }

    pub fn get_tenant(&self, tenant_id: TenantId) -> Result<&Tenant, TenantError> {
        self.tenants
            .get(&tenant_id)
            .ok_or(TenantError::NotFound { tenant_id })
    }

    pub fn get_tenant_mut(&mut self, tenant_id: TenantId) -> Result<&mut Tenant, TenantError> {
        self.tenants
            .get_mut(&tenant_id)
            .ok_or(TenantError::NotFound { tenant_id })
    }

    pub fn update_tenant(
        &mut self,
        tenant_id: TenantId,
        name: impl Into<String>,
    ) -> Result<Tenant, TenantError> {
        let tenant = self.get_tenant_mut(tenant_id)?;
        tenant.name = name.into();
        tenant.updated_at = Utc::now();
        info!(tenant_id = %tenant_id, new_name = %tenant.name, "tenant updated");
        Ok(tenant.clone())
    }

    pub fn deactivate_tenant(&mut self, tenant_id: TenantId) -> Result<(), TenantError> {
        let tenant = self.get_tenant_mut(tenant_id)?;
        tenant.deactivate();
        Ok(())
    }

    pub fn activate_tenant(&mut self, tenant_id: TenantId) -> Result<(), TenantError> {
        let tenant = self.get_tenant_mut(tenant_id)?;
        tenant.activate();
        Ok(())
    }

    pub fn delete_tenant(&mut self, tenant_id: TenantId) -> Result<Tenant, TenantError> {
        let tenant = self
            .tenants
            .remove(&tenant_id)
            .ok_or(TenantError::NotFound { tenant_id })?;
        if let Some(list) = self.org_tenants.get_mut(&tenant.org_id) {
            list.retain(|&id| id != tenant_id);
        }
        if let Some(tid) = tenant.team_id {
            if let Some(list) = self.team_tenants.get_mut(&tid) {
                list.retain(|&id| id != tenant_id);
            }
        }
        info!(tenant_id = %tenant_id, "tenant deleted");
        Ok(tenant)
    }

    pub fn list_org_tenants(&self, org_id: Uuid) -> Vec<&Tenant> {
        self.org_tenants
            .get(&org_id)
            .into_iter()
            .flatten()
            .filter_map(|id| self.tenants.get(id))
            .collect()
    }

    pub fn list_team_tenants(&self, team_id: Uuid) -> Vec<&Tenant> {
        self.team_tenants
            .get(&team_id)
            .into_iter()
            .flatten()
            .filter_map(|id| self.tenants.get(id))
            .collect()
    }

    pub fn tenant_count(&self) -> usize {
        self.tenants.len()
    }

    pub fn org_count(&self) -> usize {
        self.orgs.len()
    }

    pub fn team_count(&self) -> usize {
        self.teams.len()
    }
}

impl Default for TenantManager {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn create_org_and_team() {
        let mut mgr = TenantManager::new();
        let org = mgr.create_org("acme");
        let team = mgr.create_team(org.id, "platform").unwrap();
        assert_eq!(mgr.org_count(), 1);
        assert_eq!(mgr.team_count(), 1);
        assert_eq!(team.org_id, org.id);
    }

    #[test]
    fn create_tenant_hierarchy() {
        let mut mgr = TenantManager::new();
        let org = mgr.create_org("acme");
        let team = mgr.create_team(org.id, "platform").unwrap();
        let tenant = mgr.create_tenant("proj-alpha", org.id, Some(team.id)).unwrap();
        assert_eq!(tenant.org_id, org.id);
        assert_eq!(tenant.team_id, Some(team.id));
        assert!(tenant.is_active);
    }

    #[test]
    fn tenant_not_found() {
        let mgr = TenantManager::new();
        let missing = Uuid::new_v4();
        assert!(matches!(
            mgr.get_tenant(missing),
            Err(TenantError::NotFound { .. })
        ));
    }

    #[test]
    fn deactivate_and_activate() {
        let mut mgr = TenantManager::new();
        let org = mgr.create_org("acme");
        let tenant = mgr.create_tenant("proj-alpha", org.id, None).unwrap();
        let id = tenant.id;
        mgr.deactivate_tenant(id).unwrap();
        assert!(mgr.get_tenant(id).unwrap().is_active == false);
        mgr.activate_tenant(id).unwrap();
        assert!(mgr.get_tenant(id).unwrap().is_active);
    }

    #[test]
    fn duplicate_tenant_name() {
        let mut mgr = TenantManager::new();
        let org = mgr.create_org("acme");
        mgr.create_tenant("proj-alpha", org.id, None).unwrap();
        let result = mgr.create_tenant("proj-alpha", org.id, None);
        assert!(matches!(result, Err(TenantError::AlreadyExists { .. })));
    }

    #[test]
    fn delete_tenant() {
        let mut mgr = TenantManager::new();
        let org = mgr.create_org("acme");
        let tenant = mgr.create_tenant("proj-alpha", org.id, None).unwrap();
        assert_eq!(mgr.tenant_count(), 1);
        mgr.delete_tenant(tenant.id).unwrap();
        assert_eq!(mgr.tenant_count(), 0);
    }

    #[test]
    fn list_org_tenants() {
        let mut mgr = TenantManager::new();
        let org = mgr.create_org("acme");
        mgr.create_tenant("proj-alpha", org.id, None).unwrap();
        mgr.create_tenant("proj-beta", org.id, None).unwrap();
        assert_eq!(mgr.list_org_tenants(org.id).len(), 2);
    }

    #[test]
    fn list_team_tenants() {
        let mut mgr = TenantManager::new();
        let org = mgr.create_org("acme");
        let team = mgr.create_team(org.id, "platform").unwrap();
        mgr.create_tenant("proj-alpha", org.id, Some(team.id)).unwrap();
        assert_eq!(mgr.list_team_tenants(team.id).len(), 1);
    }

    #[test]
    fn org_not_found_for_team() {
        let mut mgr = TenantManager::new();
        let missing = Uuid::new_v4();
        assert!(matches!(
            mgr.create_team(missing, "platform"),
            Err(TenantError::OrgNotFound { .. })
        ));
    }

    #[test]
    fn tenant_serialization() {
        let tenant = Tenant::new("proj-alpha", Uuid::new_v4(), None);
        let json = serde_json::to_string(&tenant).unwrap();
        let back: Tenant = serde_json::from_str(&json).unwrap();
        assert_eq!(tenant.name, back.name);
    }
}
