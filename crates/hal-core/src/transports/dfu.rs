use crate::{HalError, Transport};

/// A snapshot of a device in DFU mode.
#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub struct DfuDeviceInfo {
    /// Platform path, e.g. `/dev/bus/usb/001/002`.
    pub path: String,
    /// Vendor/product when exposed through USB.
    pub vendor_id: Option<u16>,
    pub product_id: Option<u16>,
    /// DFU state as reported by the device, e.g. `appIDLE`, `dfuDNLOAD-IDLE`.
    pub state: String,
    /// Firmware version reported by the device.
    pub firmware_version: Option<u16>,
    /// Whether the device reports as detach-capable.
    pub can_detach: Option<bool>,
}

impl DfuDeviceInfo {
    pub fn vid_pid(&self) -> String {
        match (self.vendor_id, self.product_id) {
            (Some(v), Some(p)) => format!("{:04x}:{:04x}", v, p),
            _ => "unknown".to_string(),
        }
    }

    pub fn label(&self) -> String {
        format!("DFU ({})", self.vid_pid())
    }
}

/// DFU transport: device discovery and monitor.

/// Real discovery shells out to a Platform DFU utility when the `dfu-real`
/// feature is enabled; otherwise a deterministic simulated device is returned.
pub struct DfuTransport;

impl DfuTransport {
    pub fn enumerate() -> Vec<DfuDeviceInfo> {
        #[cfg(feature = "dfu-real")]
        {
            enumerate_real()
        }
        #[cfg(not(feature = "dfu-real"))]
        {
            vec![
                DfuDeviceInfo {
                    path: "/dev/bus/usb/001/002".to_string(),
                    vendor_id: Some(0x05AC),
                    product_id: Some(0x1227),
                    state: "appIDLE".to_string(),
                    firmware_version: Some(1),
                    can_detach: Some(true),
                },
                DfuDeviceInfo {
                    path: "/dev/bus/usb/002/004".to_string(),
                    vendor_id: Some(0x0483),
                    product_id: Some(0xDF11),
                    state: "dfuIDLE".to_string(),
                    firmware_version: Some(2),
                    can_detach: Some(false),
                },
            ]
        }
    }

    pub fn probe(&self, target: &str) -> Result<ProbeInfo, HalError> {
        if target.starts_with("dfu:") || target.contains("dfu") {
            Ok(ProbeInfo {
                transport: Transport::Dfu,
                target: target.to_string(),
                connected: true,
            })
        } else {
            Err(HalError::UnsupportedTransport(target.to_string()))
        }
    }
}

#[cfg(feature = "dfu-real")]
fn enumerate_real() -> Vec<DfuDeviceInfo> {
    use std::process::Command;
    let out = Command::new("dfu-util").args(["-l"]).output();
    match out {
        Ok(o) if o.status.success() => parse_dfu_list(&String::from_utf8_lossy(&o.stdout)),
        _ => Vec::new(),
    }
}

#[cfg(feature = "dfu-real")]
fn parse_dfu_list(raw: &str) -> Vec<DfuDeviceInfo> {
    let mut devices = Vec::new();
    let mut current = DfuDeviceInfo {
        path: String::new(),
        vendor_id: None,
        product_id: None,
        state: String::new(),
        firmware_version: None,
        can_detach: None,
    };
    for line in raw.lines() {
        let line = line.trim();
        if line.is_empty() {
            if !current.path.is_empty() {
                devices.push(current.clone());
                current = DfuDeviceInfo {
                    path: String::new(),
                    vendor_id: None,
                    product_id: None,
                    state: String::new(),
                    firmware_version: None,
                    can_detach: None,
                };
            }
            continue;
        }
        if let Some(rest) = line.strip_prefix("manufacturer=\"") {
            current.path = rest.trim_end_matches("\"").to_string();
        }
        if line.starts_with("idVendor=") {
            if let Some(v) = line.split('=').nth(1) {
                current.vendor_id = u16::from_str_radix(v.trim(), 16).ok();
            }
        }
        if line.starts_with("idProduct=") {
            if let Some(v) = line.split('=').nth(1) {
                current.product_id = u16::from_str_radix(v.trim(), 16).ok();
            }
        }
        if line.starts_with("bcdDevice=") {
            if let Some(v) = line.split('=').nth(1) {
                current.firmware_version =
                    u16::from_str_radix(v.trim().trim_start_matches("0x"), 16).ok();
            }
        }
        if line.contains("State=") {
            current.state = line.split("State=").nth(1).unwrap_or("").trim().into();
        }
    }
    if !current.path.is_empty() {
        devices.push(current);
    }
    devices
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct ProbeInfo {
    pub transport: Transport,
    pub target: String,
    pub connected: bool,
}

pub struct DfuMonitor {
    previous: std::collections::HashMap<String, DfuDeviceInfo>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum DfuChange {
    Connected(DfuDeviceInfo),
    Disconnected(DfuDeviceInfo),
}

impl DfuMonitor {
    pub fn new() -> Self {
        Self {
            previous: std::collections::HashMap::new(),
        }
    }

    pub fn prime(&mut self) {
        self.previous = Self::snapshot();
    }

    fn snapshot() -> std::collections::HashMap<String, DfuDeviceInfo> {
        DfuTransport::enumerate()
            .into_iter()
            .map(|d| (d.path.clone(), d))
            .collect()
    }

    fn diff(
        previous: &std::collections::HashMap<String, DfuDeviceInfo>,
        current: &std::collections::HashMap<String, DfuDeviceInfo>,
    ) -> Vec<DfuChange> {
        let mut changes = Vec::new();
        for dev in current.values() {
            if !previous.contains_key(&dev.path) {
                changes.push(DfuChange::Connected(dev.clone()));
            }
        }
        for dev in previous.values() {
            if !current.contains_key(&dev.path) {
                changes.push(DfuChange::Disconnected(dev.clone()));
            }
        }
        changes
    }

    pub fn poll(&mut self) -> Vec<DfuChange> {
        let current = Self::snapshot();
        let changes = Self::diff(&self.previous, &current);
        self.previous = current;
        changes
    }

    pub fn connected(&self) -> Vec<DfuDeviceInfo> {
        self.previous.values().cloned().collect()
    }
}

impl Default for DfuMonitor {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn enumerate_returns_devices() {
        let devices = DfuTransport::enumerate();
        assert!(!devices.is_empty());
        assert!(devices.iter().all(|d| !d.path.is_empty()));
    }

    #[test]
    fn probe_accepts_dfu_prefix() {
        let transport = DfuTransport;
        let r = transport.probe("dfu:0483:df11").unwrap();
        assert_eq!(r.transport, Transport::Dfu);
        assert!(r.connected);
    }

    #[cfg(feature = "dfu-real")]
    #[test]
    fn parses_dfu_list_output() {
        let raw = r#"manufacturer="0483:df11"
idVendor=0x0483
idProduct=0xdf11
bcdDevice=0x0200
State=2
"#;
        let parsed = parse_dfu_list(raw);
        assert_eq!(parsed.len(), 1);
        assert_eq!(parsed[0].vendor_id, Some(0x0483));
        assert_eq!(parsed[0].product_id, Some(0xdf11));
    }

    #[test]
    fn monitor_emits_connect_and_disconnect() {
        let dev = DfuDeviceInfo {
            path: "/dev/bus/usb/001/003".into(),
            vendor_id: Some(0x0483),
            product_id: Some(0xDF11),
            state: "dfuIDLE".into(),
            firmware_version: Some(2),
            can_detach: Some(true),
        };

        let mut monitor = DfuMonitor::new();
        monitor.previous.insert(dev.path.clone(), dev.clone());
        assert!(DfuMonitor::diff(&monitor.previous, &monitor.previous).is_empty());

        let empty = std::collections::HashMap::new();
        let changes = DfuMonitor::diff(&monitor.previous, &empty);
        assert_eq!(changes.len(), 1);
        assert!(matches!(changes[0], DfuChange::Disconnected(_)));

        let changes = DfuMonitor::diff(&empty, &monitor.previous);
        assert_eq!(changes.len(), 1);
        assert!(matches!(changes[0], DfuChange::Connected(_)));
    }
}
