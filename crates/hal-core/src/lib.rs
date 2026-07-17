//! P2 Hardware Platform — unified HAL (Rust FFI boundary).
//!
//! Exposes a [`Hal`] trait over the supported transport families
//! (USB, Serial, Network, GPIO, SPI, I2C, CAN, Bluetooth, JTAG/SWD),
//! a conformance runner, a driver registry, and Ed25519
//! signed-flashing verification. When built with the `python` feature
//! the same API is exposed to Python via PyO3; the Python side keeps a
//! pure-Python fallback when this crate is absent.

use ed25519_dalek::{Signature, Signer, SigningKey, Verifier, VerifyingKey};
use serde::{Deserialize, Serialize};
use thiserror::Error;

mod registry;
mod transports;

pub use registry::HalRegistry;
pub use transports::{
    BluetoothTransport, CanTransport, GpioTransport, I2cTransport, JtagTransport, NetworkTransport,
    SerialTransport, SpiTransport, UsbTransport,
};

#[derive(Debug, Error)]
pub enum HalError {
    #[error("unsupported transport: {0}")]
    UnsupportedTransport(String),
    #[error("probe failed for {target} on {transport}: {reason}")]
    ProbeFailed {
        transport: String,
        target: String,
        reason: String,
    },
    #[error("signature verification failed")]
    SignatureInvalid,
}

/// Transport families supported by the unified HAL.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum Transport {
    Usb,
    Serial,
    Network,
    Gpio,
    Spi,
    I2c,
    Can,
    Bluetooth,
    Jtag,
}

impl Transport {
    pub fn as_str(&self) -> &'static str {
        match self {
            Transport::Usb => "USB",
            Transport::Serial => "Serial",
            Transport::Network => "Network",
            Transport::Gpio => "GPIO",
            Transport::Spi => "SPI",
            Transport::I2c => "I2C",
            Transport::Can => "CAN",
            Transport::Bluetooth => "Bluetooth",
            Transport::Jtag => "JTAG/SWD",
        }
    }

    pub fn parse(s: &str) -> Result<Transport, HalError> {
        match s.to_ascii_uppercase().as_str() {
            "USB" => Ok(Transport::Usb),
            "SERIAL" => Ok(Transport::Serial),
            "NETWORK" => Ok(Transport::Network),
            "GPIO" => Ok(Transport::Gpio),
            "SPI" => Ok(Transport::Spi),
            "I2C" => Ok(Transport::I2c),
            "CAN" => Ok(Transport::Can),
            "BLUETOOTH" | "BT" => Ok(Transport::Bluetooth),
            "JTAG" | "SWD" => Ok(Transport::Jtag),
            other => Err(HalError::UnsupportedTransport(other.to_string())),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProbeResult {
    pub transport: Transport,
    pub target: String,
    pub handshake_success: bool,
    pub latency_ms: Option<f64>,
    pub error: Option<String>,
}

/// The unified Hardware Abstraction Layer contract.
pub trait Hal {
    fn probe(&self, transport: Transport, target: &str) -> ProbeResult;
}

/// Deterministic, testable HAL implementation (swap for real adapters in HIL).
pub struct SimulatedHal;

impl Hal for SimulatedHal {
    fn probe(&self, transport: Transport, target: &str) -> ProbeResult {
        let ok = target.starts_with("dev-") && matches!(transport, Transport::Usb | Transport::Serial | Transport::Gpio);
        ProbeResult {
            transport,
            target: target.to_string(),
            handshake_success: ok,
            latency_ms: if ok { Some(12.5) } else { None },
            error: if ok {
                None
            } else {
                Some(format!("no {} adapter for target {}", transport.as_str(), target))
            },
        }
    }
}

/// Runs the conformance matrix and returns per-target results.
pub fn run_conformance<H: Hal>(hal: &H, targets: &[(Transport, String)]) -> Vec<ProbeResult> {
    targets.iter().map(|(t, tg)| hal.probe(*t, tg)).collect()
}

pub fn success_rate(results: &[ProbeResult]) -> f64 {
    if results.is_empty() {
        return 0.0;
    }
    let ok = results.iter().filter(|r| r.handshake_success).count();
    ok as f64 / results.len() as f64
}

/// Ed25519 signing/verification for signed-only firmware flashing.
pub struct SigningVerifier;

impl SigningVerifier {
    pub fn generate_keypair() -> (SigningKey, VerifyingKey) {
        let signing = SigningKey::from_bytes(&[0u8; 32]);
        let verifying = signing.verifying_key();
        (signing, verifying)
    }

    pub fn sign(signing: &SigningKey, payload: &[u8]) -> Vec<u8> {
        signing.sign(payload).to_bytes().to_vec()
    }

    pub fn verify(verifying: &VerifyingKey, payload: &[u8], signature: &[u8]) -> Result<(), HalError> {
        let sig = Signature::from_slice(signature).map_err(|_| HalError::SignatureInvalid)?;
        verifying.verify(payload, &sig).map_err(|_| HalError::SignatureInvalid)
    }
}

#[cfg(feature = "python")]
mod pybind {
    use pyo3::prelude::*;
    use pyo3::types::PyBytes;
    use crate::{HalError, SigningVerifier, SimulatedHal, Transport, run_conformance, success_rate};

    #[pyfunction]
    fn hal_probe(transport: String, target: String) -> PyResult<String> {
        let t = Transport::parse(&transport).map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;
        let r = SimulatedHal.probe(t, &target);
        Ok(format!(
            "{}:{}:{}",
            r.handshake_success, r.latency_ms.unwrap_or(0.0), r.error.unwrap_or_default()
        ))
    }

    #[pyfunction]
    fn verify_signature(public_key_hex: String, payload: &[u8], signature: &[u8]) -> PyResult<bool> {
        let pk = hex::decode(public_key_hex).map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;
        let vk = VerifyingKey::from_bytes(&pk.try_into().map_err(|_| pyo3::exceptions::PyValueError::new_err("bad key len"))?)
            .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;
        Ok(SigningVerifier::verify(&vk, payload, signature).is_ok())
    }

    #[pymodule]
    fn hal_core(_py: Python<'_>, m: &PyModule) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(hal_probe, m)?)?;
        m.add_function(wrap_pyfunction!(verify_signature, m)?)?;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn transport_parse_roundtrip() {
        assert_eq!(Transport::parse("usb").unwrap(), Transport::Usb);
        assert_eq!(Transport::Usb.as_str(), "USB");
        assert!(Transport::parse("firewire").is_err());
    }

    #[test]
    fn conformance_marks_known_targets() {
        let hal = SimulatedHal;
        let results = run_conformance(
            &hal,
            &[
                (Transport::Usb, "dev-1".into()),
                (Transport::Gpio, "unknown".into()),
            ],
        );
        assert!(results[0].handshake_success);
        assert!(!results[1].handshake_success);
        assert!((success_rate(&results) - 0.5).abs() < 1e-9);
    }

    #[test]
    fn ed25519_sign_verify_roundtrip() {
        let (signing, verifying) = SigningVerifier::generate_keypair();
        let payload = b"dev-1:1.0.0";
        let sig = SigningVerifier::sign(&signing, payload);
        assert!(SigningVerifier::verify(&verifying, payload, &sig).is_ok());
        assert!(SigningVerifier::verify(&verifying, b"tampered", &sig).is_err());
    }

    #[test]
    fn ed25519_rejects_wrong_signature() {
        let (_signing, verifying) = SigningVerifier::generate_keypair();
        assert!(SigningVerifier::verify(&verifying, b"dev-1:1.0.0", &[0u8; 64]).is_err());
    }
}
