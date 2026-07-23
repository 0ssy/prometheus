use crate::{HalError, Transport};

#[cfg(feature = "c-hal")]
use crate::c_hal;

/// A snapshot of an ADB-visible Android device.
#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub struct AdbDeviceInfo {
    /// ADB serial (transport id), e.g. `ABCD1234` or `192.168.1.5:5555`.
    pub serial: String,
    pub state: String,
    pub model: Option<String>,
    pub product: Option<String>,
    pub device: Option<String>,
    pub android_version: Option<String>,
    pub sdk: Option<String>,
    /// USB VID/PID when the device is attached over USB.
    pub vendor_id: Option<u16>,
    pub product_id: Option<u16>,
}

impl AdbDeviceInfo {
    pub fn label(&self) -> String {
        match (self.model.as_deref(), self.product.as_deref()) {
            (Some(m), Some(p)) => format!("{m} ({p})"),
            (Some(m), None) => m.to_string(),
            (None, Some(p)) => p.to_string(),
            (None, None) => self.serial.clone(),
        }
    }
}

/// ADB transport: device discovery and hot-plug detection.
///
/// Real discovery shells out to the `adb` CLI (`adb devices -l`) when the
/// `adb-real` feature is enabled; otherwise a deterministic simulated device
/// is returned so the platform and its tests run anywhere.
pub struct AdbTransport;

impl AdbTransport {
    #[cfg(feature = "adb-real")]
    pub fn enumerate() -> Vec<AdbDeviceInfo> {
        use std::process::Command;
        let out = Command::new("adb")
            .args(["devices", "-l"])
            .output();
        match out {
            Ok(o) if o.status.success() => parse_adb_devices(&String::from_utf8_lossy(&o.stdout)),
            _ => Vec::new(),
        }
    }

    #[cfg(not(feature = "adb-real"))]
    pub fn enumerate() -> Vec<AdbDeviceInfo> {
        vec![AdbDeviceInfo {
            serial: "adb-1234567890".to_string(),
            state: "device".to_string(),
            model: Some("Pixel Simulator".into()),
            product: Some("sdk_gphone64_x86_64".into()),
            device: Some("simulator".into()),
            android_version: Some("14".into()),
            sdk: Some("34".into()),
            vendor_id: Some(0x18D1),
            product_id: Some(0x4EE7),
        }]
    }

    pub fn probe(&self, target: &str) -> Result<ProbeInfo, HalError> {
        if target.starts_with("adb:") || target.contains(':') || !target.is_empty() {
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

#[cfg(feature = "adb-real")]
fn parse_adb_devices(raw: &str) -> Vec<AdbDeviceInfo> {
    let mut devices = Vec::new();
    for line in raw.lines().skip(1) {
        let line = line.trim();
        if line.is_empty() {
            continue;
        }
        let mut parts = line.split_whitespace();
        let serial = match parts.next() {
            Some(s) => s.to_string(),
            None => continue,
        };
        let state = parts.next().unwrap_or("unknown").to_string();
        if state != "device" {
            devices.push(AdbDeviceInfo {
                serial,
                state,
                model: None,
                product: None,
                device: None,
                android_version: None,
                sdk: None,
                vendor_id: None,
                product_id: None,
            });
            continue;
        }
        let mut model = None;
        let mut product = None;
        let mut device = None;
        for kv in parts {
            if let Some((k, v)) = kv.split_once(':') {
                match k {
                    "model" => model = Some(v.to_string()),
                    "product" => product = Some(v.to_string()),
                    "device" => device = Some(v.to_string()),
                    _ => {}
                }
            }
        }
        devices.push(AdbDeviceInfo {
            serial,
            state,
            model,
            product,
            device,
            android_version: None,
            sdk: None,
            vendor_id: None,
            product_id: None,
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
pub struct AdbMonitor {
    previous: std::collections::HashMap<String, AdbDeviceInfo>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum AdbChange {
    Connected(AdbDeviceInfo),
    Disconnected(AdbDeviceInfo),
}

impl AdbMonitor {
    pub fn new() -> Self {
        Self {
            previous: std::collections::HashMap::new(),
        }
    }

    pub fn prime(&mut self) {
        self.previous = Self::snapshot();
    }

    fn snapshot() -> std::collections::HashMap<String, AdbDeviceInfo> {
        AdbTransport::enumerate()
            .into_iter()
            .map(|d| (d.serial.clone(), d))
            .collect()
    }

    fn diff(
        previous: &std::collections::HashMap<String, AdbDeviceInfo>,
        current: &std::collections::HashMap<String, AdbDeviceInfo>,
    ) -> Vec<AdbChange> {
        let mut changes = Vec::new();
        for dev in current.values() {
            if !previous.contains_key(&dev.serial) {
                changes.push(AdbChange::Connected(dev.clone()));
            }
        }
        for dev in previous.values() {
            if !current.contains_key(&dev.serial) {
                changes.push(AdbChange::Disconnected(dev.clone()));
            }
        }
        changes
    }

    pub fn poll(&mut self) -> Vec<AdbChange> {
        let current = Self::snapshot();
        let changes = Self::diff(&self.previous, &current);
        self.previous = current;
        changes
    }

    pub fn connected(&self) -> Vec<AdbDeviceInfo> {
        self.previous.values().cloned().collect()
    }
}

impl Default for AdbMonitor {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn enumerate_returns_device() {
        let devices = AdbTransport::enumerate();
        assert!(!devices.is_empty());
        assert!(devices.iter().all(|d| !d.serial.is_empty()));
    }

    #[test]
    fn monitor_emits_connect_and_disconnect() {
        let dev = AdbDeviceInfo {
            serial: "abc123".into(),
            state: "device".into(),
            model: None,
            product: None,
            device: None,
            android_version: None,
            sdk: None,
            vendor_id: None,
            product_id: None,
        };
        let mut monitor = AdbMonitor::new();
        monitor.previous.insert(dev.serial.clone(), dev.clone());
        assert!(AdbMonitor::diff(&monitor.previous, &monitor.previous).is_empty());

        let empty = std::collections::HashMap::new();
        let changes = AdbMonitor::diff(&monitor.previous, &empty);
        assert_eq!(changes.len(), 1);
        assert!(matches!(changes[0], AdbChange::Disconnected(_)));

        let changes = AdbMonitor::diff(&empty, &monitor.previous);
        assert_eq!(changes.len(), 1);
        assert!(matches!(changes[0], AdbChange::Connected(_)));
    }

    #[cfg(feature = "adb-real")]
    #[test]
    fn parses_adb_devices_output() {
        let raw = "List of devices attached\nABCD1234\tdevice product:foo model:Bar device:baz\n";
        let parsed = parse_adb_devices(raw);
        assert_eq!(parsed.len(), 1);
        assert_eq!(parsed[0].serial, "ABCD1234");
        assert_eq!(parsed[0].product.as_deref(), Some("foo"));
        assert_eq!(parsed[0].model.as_deref(), Some("Bar"));
    }
}
