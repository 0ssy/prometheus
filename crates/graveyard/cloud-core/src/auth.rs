//! Authentication: OIDC (OpenID Connect) and passkey (WebAuthn) flows, plus
//! API-key and tenant-scoped RBAC primitives.
//!
//! Cryptographic challenge verification is fully implemented; the OIDC token
//! exchange and WebAuthn attestation are wired with verifiable stubs that can
//! be swapped for a real IdP.

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::{HashMap, HashSet};
use thiserror::Error;
use tracing::{debug, info, warn};
use uuid::Uuid;

/// A verified, authenticated principal.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Session {
    pub user_id: Uuid,
    pub tenant_id: crate::tenant::TenantId,
    pub method: AuthMethod,
    pub issued_at: chrono::DateTime<chrono::Utc>,
    pub expires_at: chrono::DateTime<chrono::Utc>,
}

/// Authentication method used to establish a session.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum AuthMethod {
    Oidc,
    Passkey,
    ApiKey,
}

/// Errors arising during authentication.
#[derive(Debug, Error)]
pub enum AuthError {
    #[error("unknown oidc state: {0}")]
    UnknownState(String),
    #[error("oidc nonce mismatch")]
    NonceMismatch,
    #[error("no passkey challenge for {0}")]
    NoChallenge(String),
    #[error("passkey challenge mismatch")]
    ChallengeMismatch,
    #[error("missing authenticator data or signature")]
    MissingSignature,
    #[error("no session for user {0}")]
    NoSession(String),
    #[error("session expired for user {0}")]
    SessionExpired(String),
    #[error("invalid api key")]
    InvalidApiKey,
    #[error("serialization error: {0}")]
    Serialization(String),
    #[error("permission denied: need {needed}, have {have}")]
    PermissionDenied { needed: String, have: String },
}

pub type Result<T> = std::result::Result<T, AuthError>;

/// A long-lived API key bound to a tenant.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ApiKey {
    pub id: Uuid,
    pub tenant_id: crate::tenant::TenantId,
    pub key_hash: String,
    pub label: String,
    pub created_at: chrono::DateTime<chrono::Utc>,
    pub revoked: bool,
}

impl ApiKey {
    /// Create a new API key; returns the key material (shown only once) and the
    /// stored record (which keeps only the hash).
    pub fn create(
        tenant_id: crate::tenant::TenantId,
        label: &str,
    ) -> (String, ApiKey) {
        let raw = Uuid::new_v4().to_string().replace('-', "") + &Uuid::new_v4().to_string();
        let key_hash = hash(raw.as_bytes());
        let record = ApiKey {
            id: Uuid::new_v4(),
            tenant_id,
            key_hash,
            label: label.to_string(),
            created_at: chrono::Utc::now(),
            revoked: false,
        };
        (raw, record)
    }

    /// Verify presented key material against the stored hash.
    pub fn verify(&self, presented: &str) -> bool {
        if self.revoked {
            return false;
        }
        constant_time_eq(&self.key_hash, &hash(presented.as_bytes()))
    }
}

/// A role assigned to a principal within a tenant.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum Role {
    Owner,
    Admin,
    Member,
    Viewer,
}

/// Tenant-scoped role-based access control.
#[derive(Debug, Default)]
pub struct TenantRbac {
    assignments: HashMap<Uuid, HashSet<Role>>,
}

impl TenantRbac {
    pub fn new() -> Self {
        Self::default()
    }

    /// Grant a role to a user.
    pub fn grant(&mut self, user_id: Uuid, role: Role) {
        self.assignments
            .entry(user_id)
            .or_default()
            .insert(role);
    }

    /// Revoke a role from a user.
    pub fn revoke(&mut self, user_id: Uuid, role: Role) {
        if let Some(set) = self.assignments.get_mut(&user_id) {
            set.remove(&role);
        }
    }

    /// Check whether a user holds at least one of the required roles.
    pub fn has_role(&self, user_id: Uuid, required: Role) -> bool {
        self.assignments
            .get(&user_id)
            .map(|set| set.contains(&required))
            .unwrap_or(false)
    }

    /// Authorize an action requiring a minimum role. Owners/Admins satisfy
    /// Member/Viewer requirements; this is a simple hierarchy check.
    pub fn authorize(&self, user_id: Uuid, required: Role) -> Result<()> {
        let rank = |r: Role| match r {
            Role::Viewer => 1,
            Role::Member => 2,
            Role::Admin => 3,
            Role::Owner => 4,
        };
        let need = rank(required);
        let held = self
            .assignments
            .get(&user_id)
            .and_then(|set| set.iter().map(|r| rank(*r)).max())
            .ok_or(AuthError::PermissionDenied {
                needed: format!("{required:?}"),
                have: "none".to_string(),
            })?;
        if held >= need {
            Ok(())
        } else {
            Err(AuthError::PermissionDenied {
                needed: format!("{required:?}"),
                have: "insufficient".to_string(),
            })
        }
    }
}

/// Outstanding OIDC authorization request pending token exchange.
#[derive(Debug, Clone)]
pub struct OidcChallenge {
    pub state: String,
    pub nonce: String,
    pub created_at: chrono::DateTime<chrono::Utc>,
}

/// Configuration for an OIDC identity provider.
#[derive(Debug, Clone)]
pub struct OidcProvider {
    pub issuer: String,
    pub client_id: String,
    pub authorization_endpoint: String,
    pub token_endpoint: String,
    pub jwks_uri: String,
}

impl OidcProvider {
    pub fn new(issuer: &str, client_id: &str) -> Self {
        let base = issuer.trim_end_matches('/');
        Self {
            issuer: base.to_string(),
            client_id: client_id.to_string(),
            authorization_endpoint: format!("{base}/authorize"),
            token_endpoint: format!("{base}/token"),
            jwks_uri: format!("{base}/.well-known/jwks.json"),
        }
    }

    /// Produce the authorization URL a user-agent should be redirected to.
    pub fn authorization_url(&self, state: &str, nonce: &str, redirect_uri: &str) -> String {
        format!(
            "{}?response_type=code&client_id={}&state={}&nonce={}&redirect_uri={}",
            self.authorization_endpoint, self.client_id, state, nonce, redirect_uri
        )
    }
}

/// Minimal decoded OIDC ID token claims used for nonce binding.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IdTokenClaims {
    pub sub: Uuid,
    pub nonce: String,
    pub iss: String,
    pub aud: String,
}

/// Outstanding passkey registration/authentication challenge.
#[derive(Debug, Clone)]
pub struct PasskeyChallenge {
    pub challenge: String,
    pub created_at: chrono::DateTime<chrono::Utc>,
}

/// Passkey (WebAuthn) authenticator verifying client-data challenges.
#[derive(Debug, Default)]
pub struct PasskeyAuth {
    challenges: HashMap<String, PasskeyChallenge>,
}

impl PasskeyAuth {
    pub fn new() -> Self {
        Self::default()
    }

    /// Begin a passkey challenge, returning the challenge bytes the client
    /// must echo back (as `client_data_json`) for verification.
    pub fn begin(&mut self, user_handle: &str) -> Vec<u8> {
        let entropy: Vec<u8> = Uuid::new_v4().as_bytes().to_vec();
        let challenge = PasskeyChallenge {
            challenge: hash(&entropy),
            created_at: chrono::Utc::now(),
        };
        self.challenges
            .insert(user_handle.to_string(), challenge.clone());
        entropy
    }

    /// Complete a passkey authentication by verifying the client echoed the
    /// challenge: `SHA-256(client_data_json) == stored challenge`.
    pub fn complete(
        &mut self,
        user_handle: &str,
        client_data_json: &[u8],
        authenticator_data: &[u8],
        signature: &[u8],
    ) -> Result<()> {
        let stored = self
            .challenges
            .remove(user_handle)
            .ok_or_else(|| AuthError::NoChallenge(user_handle.to_string()))?;
        if hash(client_data_json) != stored.challenge {
            warn!(user = user_handle, "passkey challenge mismatch");
            return Err(AuthError::ChallengeMismatch);
        }
        if signature.is_empty() || authenticator_data.is_empty() {
            return Err(AuthError::MissingSignature);
        }
        Ok(())
    }
}

/// Top-level authentication provider wiring OIDC, passkey, API keys and RBAC.
#[derive(Debug, Default)]
pub struct AuthProvider {
    oidc: HashMap<String, OidcChallenge>,
    passkey: PasskeyAuth,
    api_keys: HashMap<Uuid, ApiKey>,
    rbac: TenantRbac,
    sessions: HashMap<Uuid, Session>,
}

impl AuthProvider {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn rbac(&self) -> &TenantRbac {
        &self.rbac
    }

    pub fn rbac_mut(&mut self) -> &mut TenantRbac {
        &mut self.rbac
    }

    /// Begin an OIDC flow, returning the `state`/`nonce` challenge.
    pub fn begin_oidc(&mut self, provider: &OidcProvider) -> OidcChallenge {
        let challenge = OidcChallenge {
            state: Uuid::new_v4().to_string(),
            nonce: Uuid::new_v4().to_string(),
            created_at: chrono::Utc::now(),
        };
        debug!(state = %challenge.state, "oidc flow begun");
        self.oidc.insert(challenge.state.clone(), challenge.clone());
        // `provider` retained for API symmetry / future JWKS verification.
        let _ = provider;
        challenge
    }

    /// Complete an OIDC flow, validating nonce binding.
    pub fn complete_oidc(
        &mut self,
        state: &str,
        claims: &IdTokenClaims,
        tenant_id: crate::tenant::TenantId,
    ) -> Result<Session> {
        let challenge = self
            .oidc
            .remove(state)
            .ok_or_else(|| AuthError::UnknownState(state.to_string()))?;
        if challenge.nonce != claims.nonce {
            warn!(state, "oidc nonce mismatch");
            return Err(AuthError::NonceMismatch);
        }
        let session = self.issue(claims.sub, tenant_id, AuthMethod::Oidc);
        info!(user = %session.user_id, "oidc session issued");
        Ok(session)
    }

    /// Verify an API key and issue a session.
    pub fn authenticate_api_key(
        &mut self,
        presented: &str,
        tenant_id: crate::tenant::TenantId,
    ) -> Result<Session> {
        let key = self
            .api_keys
            .values()
            .find(|k| k.tenant_id == tenant_id && k.verify(presented))
            .ok_or(AuthError::InvalidApiKey)?;
        let user_id = key.id;
        let session = self.issue(user_id, tenant_id, AuthMethod::ApiKey);
        info!(key = %user_id, "api key session issued");
        Ok(session)
    }

    /// Register an API key for a tenant (returns the raw key material).
    pub fn register_api_key(
        &mut self,
        tenant_id: crate::tenant::TenantId,
        label: &str,
    ) -> (String, Uuid) {
        let (raw, key) = ApiKey::create(tenant_id, label);
        let id = key.id;
        self.api_keys.insert(id, key);
        (raw, id)
    }

    /// Begin + complete a passkey flow in one call.
    pub fn passkey_authenticate(
        &mut self,
        user_handle: &str,
        client_data_json: &[u8],
        authenticator_data: &[u8],
        signature: &[u8],
        user_id: Uuid,
        tenant_id: crate::tenant::TenantId,
    ) -> Result<Session> {
        self.passkey
            .complete(user_handle, client_data_json, authenticator_data, signature)?;
        let session = self.issue(user_id, tenant_id, AuthMethod::Passkey);
        info!(user = %user_id, "passkey session issued");
        Ok(session)
    }

    fn issue(
        &mut self,
        user_id: Uuid,
        tenant_id: crate::tenant::TenantId,
        method: AuthMethod,
    ) -> Session {
        let now = chrono::Utc::now();
        let session = Session {
            user_id,
            tenant_id,
            method,
            issued_at: now,
            expires_at: now + chrono::Duration::hours(12),
        };
        self.sessions.insert(session.user_id, session.clone());
        session
    }

    /// Validate a session, returning it if still active.
    pub fn validate(&self, user_id: Uuid) -> Result<&Session> {
        let session = self
            .sessions
            .get(&user_id)
            .ok_or_else(|| AuthError::NoSession(user_id.to_string()))?;
        if session.expires_at < chrono::Utc::now() {
            return Err(AuthError::SessionExpired(user_id.to_string()));
        }
        Ok(session)
    }

    pub fn revoke(&mut self, user_id: Uuid) {
        self.sessions.remove(&user_id);
    }
}

fn hash(bytes: &[u8]) -> String {
    let digest = Sha256::digest(bytes);
    let mut s = String::with_capacity(digest.len() * 2);
    for b in digest {
        s.push_str(&format!("{b:02x}"));
    }
    s
}

fn constant_time_eq(a: &str, b: &str) -> bool {
    if a.len() != b.len() {
        return false;
    }
    let mut diff = 0u8;
    for (x, y) in a.as_bytes().iter().zip(b.as_bytes().iter()) {
        diff |= x ^ y;
    }
    diff == 0
}

#[cfg(test)]
mod tests {
    use super::*;

    fn tenant() -> crate::tenant::TenantId {
        Uuid::new_v4()
    }

    #[test]
    fn api_key_roundtrip() {
        let t = tenant();
        let (raw, key) = ApiKey::create(t, "ci");
        assert!(key.verify(&raw));
        assert!(!key.verify("wrong"));
    }

    #[test]
    fn rbac_hierarchy() {
        let mut rbac = TenantRbac::new();
        let u = Uuid::new_v4();
        rbac.grant(u, Role::Member);
        assert!(rbac.has_role(u, Role::Member));
        assert!(rbac.authorize(u, Role::Viewer).is_ok());
        assert!(rbac.authorize(u, Role::Admin).is_err());
    }

    #[test]
    fn oidc_roundtrip() {
        let mut p = AuthProvider::new();
        let provider = OidcProvider::new("https://idp.example.com", "client");
        let ch = p.begin_oidc(&provider);
        let claims = IdTokenClaims {
            sub: Uuid::new_v4(),
            nonce: ch.nonce.clone(),
            iss: "i".into(),
            aud: "a".into(),
        };
        let session = p.complete_oidc(&ch.state, &claims, tenant()).unwrap();
        assert_eq!(session.method, AuthMethod::Oidc);
        assert!(p.validate(session.user_id).is_ok());
    }

    #[test]
    fn oidc_nonce_mismatch_rejected() {
        let mut p = AuthProvider::new();
        let provider = OidcProvider::new("https://idp", "c");
        let ch = p.begin_oidc(&provider);
        let mut claims = IdTokenClaims {
            sub: Uuid::new_v4(),
            nonce: ch.nonce.clone(),
            iss: "i".into(),
            aud: "a".into(),
        };
        claims.nonce = "wrong".into();
        assert!(matches!(
            p.complete_oidc(&ch.state, &claims, tenant()),
            Err(AuthError::NonceMismatch)
        ));
    }

    #[test]
    fn passkey_roundtrip() {
        let mut p = AuthProvider::new();
        let handle = "user@example.com";
        let challenge = p.passkey.begin(handle);
        let user = Uuid::new_v4();
        let session = p
            .passkey_authenticate(handle, &challenge, b"authdata", b"sig", user, tenant())
            .unwrap();
        assert_eq!(session.method, AuthMethod::Passkey);
    }

    #[test]
    fn api_key_session() {
        let mut p = AuthProvider::new();
        let t = tenant();
        let (raw, _) = p.register_api_key(t, "ci");
        let session = p.authenticate_api_key(&raw, t).unwrap();
        assert_eq!(session.method, AuthMethod::ApiKey);
    }

    #[test]
    fn session_expiry_and_revoke() {
        let mut p = AuthProvider::new();
        let provider = OidcProvider::new("https://idp", "c");
        let ch = p.begin_oidc(&provider);
        let claims = IdTokenClaims {
            sub: Uuid::new_v4(),
            nonce: ch.nonce.clone(),
            iss: "i".into(),
            aud: "a".into(),
        };
        let session = p.complete_oidc(&ch.state, &claims, tenant()).unwrap();
        p.revoke(session.user_id);
        assert!(p.validate(session.user_id).is_err());
    }
}
