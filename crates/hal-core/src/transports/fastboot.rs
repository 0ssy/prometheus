use crate::{HalError, Transport};

#[cfg(feature = "c-hal")]
use crate::c_hal;

/// A snapshot of a device in fastboot mode.
#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub struct FastbootDeviceInfo {
    /// Fastboot serial / transport id.
    pub serial: String,
    pub state: String,
    pub product: Option<String>,
    pub model: Option<String>,
    /// USB VID/PID when attached over USB (fastboot is USB-based).
    pub vendor_id: Option<u16>,
    pub product_id: Option<u16>,
    /// Whether the bootloader reports itself as unlocked.
    pub unlocked: Option<bool>,
}

impl FastbootDeviceInfo {
    pub fn label(&self) -> String {
        match (self.model.as_deref(), self.product.as_deref()) {
            (Some(m), Some(p)) => format!("{m} ({p})"),
            (Some(m), None) => m.to_string(),
            (None, Some(p)) => p.to_string(),
            (None, None) => self.serial.clone(),
        }
    }
}

/// Fastboot transport: device discovery and hot-plug detection.
///
/// Real discovery shells out to `fastboot devices` when the `fastboot-real`
/// feature is enabled; otherwise a deterministic simulated device is returned
/// so the platform and its tests run anywhere.
pub struct FastbootTransport;

impl FastbootTransport {
    #[cfg(feature = "fastboot-real")]
    pub fn enumerate() -> Vec<FastbootDeviceInfo> {
        use std::process::Command;
        let out = Command::new("fastboot").args(["devices"]).output();
        match out {
            Ok(o) if o.status.success() => parse_fastboot_devices(&String::from_utf8_lossy(&o.stdout)),
            _ => Vec::new(),
        }
    }

    #[cfg(not(feature = "fastboot-real"))]
    pub fn enumerate() -> Vec<FastbootDeviceInfo> {
        vec![FastbootDeviceInfo {
            serial: "fastboot-abcdef123456".to_string(),
            state: "fastboot".to_string(),
            product: Some("fastboot_simulator".into()),
            model: Some("Simulator".into()),
            vendor_id: Some(0x18D1),
            product_id: Some(0x4EE7),
            unlocked: Some(false),
        }]
    }

    pub fn probe(&self, target: &str) -> Result<ProbeInfo, HalError> {
        if target.starts_with("fastboot:") || !target.is_empty() {
            Ok(ProbeInfo {
                transport: Transport::Usb,
                target: target.to_string(),
                connected: true,
                baud_rate: None,
            })
        } else {
            Err(HalError::UnsupportedTransport(target.to_string()))
        }
    }
}

#[cfg(feature = "fastboot-real")]
fn parse_fastboot_devices(raw: &str) -> Vec<FastbootDeviceInfo> {
    let mut devices = Vec::new();
    for line in raw.lines() {
        let line = line.trim();
        if line.is_empty() {
            continue;
        }
        // Typical line: "ABCD1234\tfastboot"
        let mut parts = line.split_whitespace();
        let serial = match parts.next() {
            Some(s) => s.to_string(),
            None => continue,
        };
        let state = parts.next().unwrap_or("fastboot").to_string();
        devices.push(FastbootDeviceInfo {
            serial,
            state,
            product: None,
            model: None,
            vendor_id: None,
            product_id: None,
            unlocked: None,
        });
    }
    devices
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct ProbeInfo {
    pub transport: Transport,
    pub target: String,
    pub connected: bool,
    pub baud_rate: Option<u32>,
}

/// Minimal hot-plug detector backed by periodic re-enumeration.
pub struct FastbootMonitor {
    previous: std::collections::HashMap<String, FastbootDeviceInfo>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum FastbootChange {
    Connected(FastbootDeviceInfo),
    Disconnected(FastbootDeviceInfo),
}

impl FastbootMonitor {
    pub fn new() -> Self {
        Self {
            previous: std::collections::HashMap::new(),
        }
    }

    pub fn prime(&mut self) {
        self.previous = Self::snapshot();
    }

    fn snapshot() -> std::collections::HashMap<String, FastbootDeviceInfo> {
        FastbootTransport::enumerate()
            .into_iter()
            .map(|d| (d.serial.clone(), d))
            .collect()
    }

    fn diff(
        previous: &std::collections::HashMap<String, FastbootDeviceInfo>,
        current: &std::collections::HashMap<String, FastbootDeviceInfo>,
    ) -> Vec<FastbootChange> {
        let mut changes = Vec::new();
        for dev in current.values() {
            if !previous.contains_key(&dev.serial) {
                changes.push(FastbootChange::Connected(dev.clone()));
            }
        }
        for dev in previous.values() {
            if !current.contains_key(&dev.serial) {
                changes.push(FastbootChange::Disconnected(dev.clone()));
            }
        }
        changes
    }

    pub fn poll(&mut self) -> Vec<FastbootChange> {
        let current = Self::snapshot();
        let changes = Self::diff(&self.previous, &current);
        self.previous = current;
        changes
    }

    pub fn connected(&self) -> Vec<FastbootDeviceInfo> {
        self.previous.values().cloned().collect()
    }
}

impl Default for FastbootMonitor {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn enumerate_returns_device() {
        let devices = FastbootTransport::enumerate();
        assert!(!devices.is_empty());
        assert!(devices.iter().all(|d| !d.serial.is_empty()));
    }

    #[test]
    fn monitor_emits_connect_and_disconnect() {
        let dev = FastbootDeviceInfo {
            serial: "fb123".into(),
            state: "fastboot".into(),
            product: None,
            model: None,
            vendor_id: None,
            product_id: None,
            unlocked: None,
        };
        let mut monitor = FastbootMonitor::new();
        monitor.previous.insert(dev.serial.clone(), dev.clone());
        assert!(FastbootMonitor::diff(&monitor.previous, &monitor.previous).is_empty());

        let empty = std::collections::HashMap::new();
        let changes = FastbootMonitor::diff(&monitor.previous, &empty);
        assert_eq!(changes.len(), 1);
        assert!(matches!(changes[0], FastbootChange::Disconnected(_)));

        let changes = FastbootMonitor::diff(&empty, &monitor.previous);
        assert_eq!(changes.len(), 1);
        assert!(matches!(changes[0], FastbootChange::Connected(_)));
    }

    #[cfg(feature = "fastboot-real")]
    #[test]
    fn parses_fastboot_devices_output() {
        let raw = "ABCD1234\tfastboot\n";
        let parsed = parse_fastboot_devices(raw);
        assert_eq!(parsed.len(), 1);
        assert_eq!(parsed[0].serial, "ABCD1234");
        assert_eq!(parsed[0].state, "fastboot");
    }
}
