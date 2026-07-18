//! SSH reverse-tunnel management for secure device/agent connectivity.
//!
//! Tunnels are configured with a [`TunnelConfig`], registered with a unique id
//! and a lifecycle tracked by [`TunnelStatus`]. Heartbeats keep a tunnel
//! alive; staleness is computed from the last-seen timestamp. The SSH handshake
//! records host key fingerprints for integrity verification.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use thiserror::Error;
use tracing::{debug, info, warn};
use uuid::Uuid;

/// A tenant-scoped unique identifier for a tunnel.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct TunnelId(pub Uuid);

impl TunnelId {
    pub fn new() -> Self {
        Self(Uuid::new_v4())
    }
}

impl Default for TunnelId {
    fn default() -> Self {
        Self::new()
    }
}

impl std::fmt::Display for TunnelId {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.0)
    }
}

/// Lifecycle status of a tunnel.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum TunnelStatus {
    Provisioned,
    Connected,
    Closed,
}

/// Configuration for a managed SSH reverse tunnel.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TunnelConfig {
    pub tenant_id: crate::tenant::TenantId,
    pub device_id: String,
    pub local_port: u16,
    pub remote_port: u16,
    pub ssh_host: String,
    pub ssh_user: String,
}

impl TunnelConfig {
    pub fn new(
        tenant_id: crate::tenant::TenantId,
        device_id: &str,
        local_port: u16,
        remote_port: u16,
    ) -> Self {
        Self {
            tenant_id,
            device_id: device_id.to_string(),
            local_port,
            remote_port,
            ssh_host: "tunnel.p2.cloud".to_string(),
            ssh_user: "tunnel".to_string(),
        }
    }
}

/// A managed SSH reverse tunnel.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Tunnel {
    pub id: TunnelId,
    pub config: TunnelConfig,
    pub status: TunnelStatus,
    pub host_key_fingerprint: Option<String>,
    pub last_heartbeat: chrono::DateTime<chrono::Utc>,
}

impl Tunnel {
    /// Heartbeat timeout window before a tunnel is considered stale.
    pub const HEARTBEAT_TIMEOUT: chrono::Duration = chrono::Duration::seconds(60);

    /// Record a heartbeat, marking the tunnel connected.
    pub fn heartbeat(&mut self) {
        self.last_heartbeat = chrono::Utc::now();
        if self.status == TunnelStatus::Provisioned {
            self.status = TunnelStatus::Connected;
        }
    }

    /// Whether the tunnel has not sent a heartbeat within the timeout window.
    pub fn is_stale(&self) -> bool {
        chrono::Utc::now() - self.last_heartbeat > Self::HEARTBEAT_TIMEOUT
    }
}

/// Errors arising during tunnel management.
#[derive(Debug, Error)]
pub enum TunnelError {
    #[error("tunnel {0} not found")]
    NotFound(String),
    #[error("port {0} already allocated")]
    PortAlreadyAllocated(u16),
    #[error("handshake failed: {0}")]
    Handshake(String),
}

/// Manager for the lifecycle of tunnels.
#[derive(Debug, Default)]
pub struct TunnelManager {
    tunnels: HashMap<TunnelId, Tunnel>,
    allocated_ports: HashMap<u16, TunnelId>,
}

impl TunnelManager {
    pub fn new() -> Self {
        Self::default()
    }

    /// Provision a new tunnel from a config.
    pub fn provision(&mut self, config: TunnelConfig) -> Result<TunnelId, TunnelError> {
        if self.allocated_ports.contains_key(&config.remote_port) {
            return Err(TunnelError::PortAlreadyAllocated(config.remote_port));
        }
        let tunnel = Tunnel {
            id: TunnelId::new(),
            config,
            status: TunnelStatus::Provisioned,
            host_key_fingerprint: None,
            last_heartbeat: chrono::Utc::now(),
        };
        info!(tunnel = %tunnel.id, device = %tunnel.config.device_id, "tunnel provisioned");
        self.allocated_ports
            .insert(tunnel.config.remote_port, tunnel.id);
        let id = tunnel.id;
        self.tunnels.insert(id, tunnel);
        Ok(id)
    }

    /// Complete the SSH handshake, storing the host key fingerprint.
    pub fn complete_handshake(&mut self, id: TunnelId, host_key_fingerprint: &str) -> Result<(), TunnelError> {
        let tunnel = self
            .tunnels
            .get_mut(&id)
            .ok_or_else(|| TunnelError::NotFound(id.to_string()))?;
        tunnel.host_key_fingerprint = Some(host_key_fingerprint.to_string());
        tunnel.heartbeat();
        debug!(tunnel = %id, "handshake completed");
        Ok(())
    }

    pub fn heartbeat(&mut self, id: TunnelId) -> Result<(), TunnelError> {
        let tunnel = self
            .tunnels
            .get_mut(&id)
            .ok_or_else(|| TunnelError::NotFound(id.to_string()))?;
        tunnel.heartbeat();
        Ok(())
    }

    pub fn get(&self, id: TunnelId) -> Result<&Tunnel, TunnelError> {
        self.tunnels
            .get(&id)
            .ok_or_else(|| TunnelError::NotFound(id.to_string()))
    }

    /// Close a tunnel and release its port.
    pub fn close(&mut self, id: TunnelId) -> Result<(), TunnelError> {
        let tunnel = self
            .tunnels
            .get_mut(&id)
            .ok_or_else(|| TunnelError::NotFound(id.to_string()))?;
        tunnel.status = TunnelStatus::Closed;
        self.allocated_ports.remove(&tunnel.config.remote_port);
        info!(tunnel = %id, "tunnel closed");
        Ok(())
    }

    /// Return ids of tunnels that are connected but have not heartbeaten.
    pub fn stale_tunnels(&self) -> Vec<TunnelId> {
        self.tunnels
            .values()
            .filter(|t| t.status == TunnelStatus::Connected && t.is_stale())
            .map(|t| t.id)
            .collect()
    }

    /// Reconcile the tunnel registry: close all stale tunnels.
    pub fn reconcile(&mut self) -> Vec<TunnelId> {
        let stale = self.stale_tunnels();
        for id in &stale {
            if let Some(t) = self.tunnels.get_mut(id) {
                warn!(tunnel = %id, "reconciling stale tunnel");
                t.status = TunnelStatus::Closed;
            }
        }
        stale
    }

    /// All active (provisioned or connected) tunnels for a tenant.
    pub fn active_for_tenant(&self, tenant_id: crate::tenant::TenantId) -> Vec<&Tunnel> {
        self.tunnels
            .values()
            .filter(|t| t.config.tenant_id == tenant_id && t.status != TunnelStatus::Closed)
            .collect()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn provision_and_handshake() {
        let mut mgr = TunnelManager::new();
        let t = Uuid::new_v4();
        let id = mgr.provision(TunnelConfig::new(t, "dev-1", 8080, 9000)).unwrap();
        assert_eq!(mgr.get(id).unwrap().status, TunnelStatus::Provisioned);
        mgr.complete_handshake(id, "sha256:abcd").unwrap();
        assert_eq!(mgr.get(id).unwrap().status, TunnelStatus::Connected);
        assert_eq!(
            mgr.get(id).unwrap().host_key_fingerprint.as_deref(),
            Some("sha256:abcd")
        );
    }

    #[test]
    fn duplicate_port_rejected() {
        let mut mgr = TunnelManager::new();
        let t = Uuid::new_v4();
        mgr.provision(TunnelConfig::new(t, "d1", 1, 9000)).unwrap();
        let err = mgr.provision(TunnelConfig::new(t, "d2", 2, 9000));
        assert!(matches!(err, Err(TunnelError::PortAlreadyAllocated(9000))));
    }

    #[test]
    fn unknown_tunnel_errors() {
        let mut mgr = TunnelManager::new();
        assert!(matches!(
            mgr.complete_handshake(TunnelId::new(), "fp"),
            Err(TunnelError::NotFound(_))
        ));
    }

    #[test]
    fn stale_detection_and_reconcile() {
        let mut mgr = TunnelManager::new();
        let id = mgr
            .provision(TunnelConfig::new(Uuid::new_v4(), "d", 1, 2))
            .unwrap();
        mgr.complete_handshake(id, "fp").unwrap();
        mgr.tunnels.get_mut(&id).unwrap().last_heartbeat =
            chrono::Utc::now() - Tunnel::HEARTBEAT_TIMEOUT - chrono::Duration::seconds(5);
        assert!(mgr.get(id).unwrap().is_stale());
        let reconciled = mgr.reconcile();
        assert_eq!(reconciled, vec![id]);
        assert_eq!(mgr.get(id).unwrap().status, TunnelStatus::Closed);
    }

    #[test]
    fn close_releases_port() {
        let mut mgr = TunnelManager::new();
        let t = Uuid::new_v4();
        let id = mgr.provision(TunnelConfig::new(t, "d", 1, 2)).unwrap();
        mgr.close(id).unwrap();
        assert!(mgr.provision(TunnelConfig::new(t, "d2", 3, 2)).is_ok());
    }

    #[test]
    fn active_for_tenant_filtering() {
        let mut mgr = TunnelManager::new();
        let t1 = Uuid::new_v4();
        let t2 = Uuid::new_v4();
        let a = mgr.provision(TunnelConfig::new(t1, "d1", 1, 2)).unwrap();
        mgr.provision(TunnelConfig::new(t2, "d2", 3, 4)).unwrap();
        mgr.complete_handshake(a, "fp").unwrap();
        assert_eq!(mgr.active_for_tenant(t1).len(), 1);
        assert_eq!(mgr.active_for_tenant(t2).len(), 1);
    }
}
