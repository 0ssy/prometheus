//! Hardware Abstraction Layer (HAL) traits, driver manifests, and signed
//! driver packaging.

use crate::plugin::Permission;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::BTreeMap;
use thiserror::Error;

/// Errors produced while building or verifying driver packages.
#[derive(Debug, Error, PartialEq, Eq)]
pub enum DriverError {
    #[error("unsupported protocol: {0}")]
    UnknownProtocol(String),
    #[error("driver package integrity check failed")]
    IntegrityFailed,
    #[error("driver manifest is missing required field: {0}")]
    MissingField(String),
}

/// Transport/protocol families a driver can bind to.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "UPPERCASE")]
pub enum Protocol {
    Gpio,
    Serial,
    Usb,
    I2c,
    Spi,
    Can,
    Jtag,
    Bluetooth,
    Network,
}

impl Protocol {
    pub fn as_str(&self) -> &'static str {
        match self {
            Protocol::Gpio => "GPIO",
            Protocol::Serial => "SERIAL",
            Protocol::Usb => "USB",
            Protocol::I2c => "I2C",
            Protocol::Spi => "SPI",
            Protocol::Can => "CAN",
            Protocol::Jtag => "JTAG",
            Protocol::Bluetooth => "BLUETOOTH",
            Protocol::Network => "NETWORK",
        }
    }

    pub fn parse(s: &str) -> Result<Protocol, DriverError> {
        match s.to_ascii_uppercase().as_str() {
            "GPIO" => Ok(Protocol::Gpio),
            "SERIAL" => Ok(Protocol::Serial),
            "USB" => Ok(Protocol::Usb),
            "I2C" => Ok(Protocol::I2c),
            "SPI" => Ok(Protocol::Spi),
            "CAN" => Ok(Protocol::Can),
            "JTAG" => Ok(Protocol::Jtag),
            "BLUETOOTH" => Ok(Protocol::Bluetooth),
            "NETWORK" => Ok(Protocol::Network),
            other => Err(DriverError::UnknownProtocol(other.to_string())),
        }
    }
}

/// Safety classification of a driver's operations.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum SafetyLevel {
    Safe,
    Unsafe,
    Critical,
}

/// A single method declared on a HAL trait.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct HalTraitMethod {
    pub name: String,
    pub signature: String,
}

/// A named HAL trait a driver implements.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct HalTraitDefinition {
    pub name: String,
    pub methods: Vec<HalTraitMethod>,
    pub safety_level: SafetyLevel,
}

/// The driver's manifest, mirroring the on-disk `driver.json` contract.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct DriverManifest {
    pub id: String,
    pub name: String,
    pub version: String,
    pub description: String,
    pub author: String,
    pub protocols: Vec<Protocol>,
    pub hal_traits: Vec<HalTraitDefinition>,
    pub entrypoint: String,
}

impl DriverManifest {
    pub fn from_json(s: &str) -> Result<Self, serde_json::Error> {
        serde_json::from_str(s)
    }

    pub fn to_json(&self) -> Result<String, serde_json::Error> {
        serde_json::to_string_pretty(self)
    }
}

/// The unified Hardware Abstraction Layer contract a driver implements.
///
/// The SDK provides a default conformance probe; drivers override
/// [`Hal::probe`] to report device availability on a supported protocol.
pub trait Hal: Send + Sync {
    /// Probes `target` on `protocol`, returning whether the device answered.
    fn probe(&self, protocol: Protocol, target: &str) -> ProbeResult;
}

/// Result of a [`Hal::probe`] call.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ProbeResult {
    pub protocol: Protocol,
    pub target: String,
    pub handshake_success: bool,
    pub error: Option<String>,
}

/// A deterministic, testable HAL implementation used in conformance runs.
#[derive(Debug, Default)]
pub struct SimulatedHal;

impl Hal for SimulatedHal {
    fn probe(&self, protocol: Protocol, target: &str) -> ProbeResult {
        let ok = target.starts_with("dev-")
            && matches!(protocol, Protocol::Usb | Protocol::Serial | Protocol::Gpio);
        ProbeResult {
            protocol,
            target: target.to_string(),
            handshake_success: ok,
            error: if ok {
                None
            } else {
                Some(format!("no {} adapter for target {}", protocol.as_str(), target))
            },
        }
    }
}

/// Runs the conformance matrix against a HAL and returns per-target results.
pub fn run_conformance<H: Hal>(hal: &H, targets: &[(Protocol, String)]) -> Vec<ProbeResult> {
    targets
        .iter()
        .map(|(p, t)| hal.probe(*p, t))
        .collect()
}

/// A single file entry in a driver package with its SHA-256 digest.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct PackageFile {
    pub path: String,
    #[serde(with = "hex_digest")]
    pub sha256: [u8; 32],
}

/// A signed driver package descriptor. The `files` digests are covered by the
/// HMAC-SHA256 `signature` computed over the canonical JSON of `files`.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct DriverPackage {
    pub manifest: DriverManifest,
    pub files: Vec<PackageFile>,
    #[serde(with = "hex_digest")]
    pub signature: [u8; 32],
}

impl DriverPackage {
    /// Builds a package, signing the file manifest with `key` (HMAC-SHA256).
    pub fn sign(files: Vec<PackageFile>, manifest: DriverManifest, key: &[u8]) -> Self {
        let signature = Self::compute_signature(&files, key);
        DriverPackage {
            manifest,
            files,
            signature,
        }
    }

    /// Canonical serialization of the file list used as the HMAC input.
    pub fn canonical_files(files: &[PackageFile]) -> Vec<u8> {
        let mut map: BTreeMap<&str, String> = BTreeMap::new();
        for f in files {
            map.insert(f.path.as_str(), hex_digest::to_hex(&f.sha256));
        }
        serde_json::to_vec(&map).expect("file map serializes")
    }

    fn compute_signature(files: &[PackageFile], key: &[u8]) -> [u8; 32] {
        use hmac::{Hmac, Mac};
        type HmacSha256 = Hmac<Sha256>;
        let mut mac =
            HmacSha256::new_from_slice(key).expect("HMAC accepts any key length");
        mac.update(&Self::canonical_files(files));
        let out = mac.finalize().into_bytes();
        let mut arr = [0u8; 32];
        arr.copy_from_slice(&out);
        arr
    }

    /// Verifies the package signature against `key`.
    pub fn verify(&self, key: &[u8]) -> Result<(), DriverError> {
        let expected = Self::compute_signature(&self.files, key);
        if expected == self.signature {
            Ok(())
        } else {
            Err(DriverError::IntegrityFailed)
        }
    }

    /// Verifies that the in-memory file contents match the recorded digests.
    pub fn verify_file_integrity(&self, contents: &[(String, Vec<u8>)]) -> Result<(), DriverError> {
        for (path, bytes) in contents {
            let recorded = self.files.iter().find(|f| &f.path == path);
            let recorded = match recorded {
                Some(r) => r,
                None => return Err(DriverError::IntegrityFailed),
            };
            let mut hasher = Sha256::new();
            hasher.update(bytes);
            let digest = hasher.finalize();
            if digest.as_slice() != recorded.sha256 {
                return Err(DriverError::IntegrityFailed);
            }
        }
        Ok(())
    }
}

/// Computes the SHA-256 digest of arbitrary content.
pub fn sha256_of(bytes: &[u8]) -> [u8; 32] {
    let mut hasher = Sha256::new();
    hasher.update(bytes);
    let out = hasher.finalize();
    let mut arr = [0u8; 32];
    arr.copy_from_slice(&out);
    arr
}

/// Maps a driver's protocols to the SDK permissions it implicitly needs.
pub fn driver_permissions(protocols: &[Protocol]) -> Vec<Permission> {
    // Any driver that talks to real hardware needs device write + a process.
    if protocols.is_empty() {
        Vec::new()
    } else {
        vec![Permission::WriteDevice, Permission::SpawnProcess]
    }
}

mod hex_digest {
    use serde::{Deserialize, Deserializer, Serializer};

    pub fn to_hex(bytes: &[u8; 32]) -> String {
        bytes.iter().map(|b| format!("{b:02x}")).collect()
    }

    pub fn from_hex(s: &str) -> Result<[u8; 32], String> {
        let s = s.trim();
        if s.len() != 64 {
            return Err(format!("expected 64 hex chars, got {}", s.len()));
        }
        let mut out = [0u8; 32];
        for (i, chunk) in s.as_bytes().chunks(2).enumerate() {
            let pair = std::str::from_utf8(chunk).map_err(|e| e.to_string())?;
            out[i] = u8::from_str_radix(pair, 16).map_err(|e| e.to_string())?;
        }
        Ok(out)
    }

    pub fn serialize<S: Serializer>(bytes: &[u8; 32], ser: S) -> Result<S::Ok, S::Error> {
        ser.serialize_str(&to_hex(bytes))
    }

    pub fn deserialize<'de, D: Deserializer<'de>>(de: D) -> Result<[u8; 32], D::Error> {
        let s = String::deserialize(de)?;
        from_hex(&s).map_err(serde::de::Error::custom)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn sample_manifest() -> DriverManifest {
        DriverManifest {
            id: "drv-example".into(),
            name: "Example Driver".into(),
            version: "0.1.0".into(),
            description: "An example driver".into(),
            author: "prometheus".into(),
            protocols: vec![Protocol::Usb, Protocol::Serial],
            hal_traits: vec![HalTraitDefinition {
                name: "Probeable".into(),
                methods: vec![HalTraitMethod {
                    name: "probe".into(),
                    signature: "fn probe(&self, target: &str)".into(),
                }],
                safety_level: SafetyLevel::Safe,
            }],
            entrypoint: "libdriver.so".into(),
        }
    }

    #[test]
    fn protocol_parse_roundtrip() {
        assert_eq!(Protocol::parse("usb").unwrap(), Protocol::Usb);
        assert_eq!(Protocol::Usb.as_str(), "USB");
        assert!(Protocol::parse("firewire").is_err());
    }

    #[test]
    fn manifest_json_roundtrip() {
        let m = sample_manifest();
        let json = m.to_json().unwrap();
        let back = DriverManifest::from_json(&json).unwrap();
        assert_eq!(back, m);
    }

    #[test]
    fn conformance_marks_known_targets() {
        let hal = SimulatedHal;
        let results = run_conformance(
            &hal,
            &[
                (Protocol::Usb, "dev-1".into()),
                (Protocol::Gpio, "unknown".into()),
            ],
        );
        assert!(results[0].handshake_success);
        assert!(!results[1].handshake_success);
    }

    #[test]
    fn package_sign_verify() {
        let key = b"super-secret-key";
        let files = vec![PackageFile {
            path: "libdriver.so".into(),
            sha256: sha256_of(b"binary-bytes"),
        }];
        let pkg = DriverPackage::sign(files, sample_manifest(), key);
        assert!(pkg.verify(key).is_ok());
        assert!(pkg.verify(b"wrong-key").is_err());
    }

    #[test]
    fn package_file_integrity() {
        let key = b"k";
        let digest = sha256_of(b"hello");
        let pkg = DriverPackage::sign(
            vec![PackageFile {
                path: "a.txt".into(),
                sha256: digest,
            }],
            sample_manifest(),
            key,
        );
        assert!(pkg.verify_file_integrity(&[("a.txt".into(), b"hello".to_vec())]).is_ok());
        assert!(pkg.verify_file_integrity(&[("a.txt".into(), b"tampered".to_vec())]).is_err());
        assert!(pkg.verify_file_integrity(&[("missing".into(), b"x".to_vec())]).is_err());
    }

    #[test]
    fn driver_permissions_for_protocols() {
        assert!(driver_permissions(&[Protocol::Usb]).contains(&Permission::WriteDevice));
        assert!(driver_permissions(&[]).is_empty());
    }

    #[test]
    fn signature_hex_serde() {
        let digest = [0xabu8; 32];
        let json = serde_json::to_string(&digest).unwrap();
        let back: [u8; 32] = serde_json::from_str(&json).unwrap();
        assert_eq!(back, digest);
    }
}
