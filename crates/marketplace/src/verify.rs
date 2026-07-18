//! Package signature verification using HMAC-SHA256.

use crate::package::Manifest;
use crate::{MarketplaceError, Result};
use base64::Engine;
use hmac::{Hmac, Mac};
use sha2::{Digest, Sha256};
use tracing::debug;

type HmacSha256 = Hmac<Sha256>;

/// Verifies package integrity and authenticity.
pub struct Verifier {
    secret: Vec<u8>,
}

impl Verifier {
    /// Create a verifier with the shared HMAC secret.
    pub fn new(secret: &[u8]) -> Self {
        Self {
            secret: secret.to_vec(),
        }
    }

    /// Compute the HMAC-SHA256 over the canonical manifest JSON.
    pub fn sign(&self, manifest: &Manifest) -> String {
        let data = manifest.to_json().expect("manifest serializable");
        let mut mac = HmacSha256::new_from_slice(&self.secret)
            .expect("HMAC accepts key of any size");
        mac.update(data.as_bytes());
        let tag = mac.finalize().into_bytes();
        base64::engine::general_purpose::STANDARD.encode(tag)
    }

    /// Verify the manifest's recorded signature. The signature is stored in
    /// `manifest.license` field convention is avoided; we pass it explicitly.
    pub fn verify(&self, manifest: &Manifest, signature_b64: &str) -> Result<()> {
        let expected = self.sign(manifest);
        let ok = constant_time_eq(&expected, signature_b64);
        if ok {
            debug!(name = %manifest.name, "signature verified");
            Ok(())
        } else {
            Err(MarketplaceError::Verification(manifest.name.clone()))
        }
    }

    /// Verify the artifact bytes against the recorded SHA256 (hex).
    pub fn verify_artifact(&self, manifest: &Manifest, artifact: &[u8]) -> Result<()> {
        let digest = Sha256::digest(artifact);
        let hex = hex_encode(&digest);
        if hex.eq_ignore_ascii_case(&manifest.artifact_sha256) {
            Ok(())
        } else {
            Err(MarketplaceError::Verification(format!(
                "artifact sha mismatch for {}",
                manifest.name
            )))
        }
    }
}

/// Constant-time string comparison to avoid timing attacks.
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

fn hex_encode(bytes: &[u8]) -> String {
    let mut s = String::with_capacity(bytes.len() * 2);
    for b in bytes {
        s.push_str(&format!("{b:02x}"));
    }
    s
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::package::{PackageKind, Version};

    fn manifest() -> Manifest {
        Manifest::new("demo", Version::new(1, 0, 0), PackageKind::Plugin, "d".repeat(64).as_str())
    }

    #[test]
    fn sign_verify_roundtrip() {
        let v = Verifier::new(b"super-secret");
        let m = manifest();
        let sig = v.sign(&m);
        assert!(v.verify(&m, &sig).is_ok());
    }

    #[test]
    fn tampered_manifest_rejects() {
        let v = Verifier::new(b"secret");
        let mut m = manifest();
        let sig = v.sign(&m);
        m.description = "tampered".into();
        assert!(v.verify(&m, &sig).is_err());
    }

    #[test]
    fn wrong_secret_rejects() {
        let a = Verifier::new(b"secret-a");
        let b = Verifier::new(b"secret-b");
        let m = manifest();
        let sig = a.sign(&m);
        assert!(b.verify(&m, &sig).is_err());
    }

    #[test]
    fn artifact_sha_matches() {
        let v = Verifier::new(b"k");
        let payload = b"hello artifact";
        let digest = Sha256::digest(payload);
        let mut m = manifest();
        m.artifact_sha256 = hex_encode(&digest);
        assert!(v.verify_artifact(&m, payload).is_ok());
        assert!(v.verify_artifact(&m, b"other").is_err());
    }

    #[test]
    fn constant_time_eq_basics() {
        assert!(constant_time_eq("abc", "abc"));
        assert!(!constant_time_eq("abc", "abd"));
        assert!(!constant_time_eq("abc", "abcd"));
    }
}
