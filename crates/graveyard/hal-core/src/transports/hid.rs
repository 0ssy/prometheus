use crate::{HalError, Transport};

/// A snapshot of a HID device as seen by the host.
#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub struct HidDeviceInfo {
    /// Platform-specific path or handle, e.g. `/dev/hidraw0` or `\\?\hid#vid_18d1...`.
    pub path: String,
    /// USB VID when the HID device is USB-backed.
    pub vendor_id: Option<u16>,
    /// USB PID when the HID device is USB-backed.
    pub product_id: Option<u16>,
    pub manufacturer: Option<String>,
    pub product: Option<String>,
    pub serial_number: Option<String>,
    /// HID usage page, e.g. `0xFF00` for vendor-defined.
    pub usage_page: Option<u16>,
    /// HID usage ID within the page.
    pub usage_id: Option<u16>,
    /// Interface number (USB HID class).
    pub interface_number: Option<u8>,
}

impl HidDeviceInfo {
    pub fn vid_pid(&self) -> String {
        match (self.vendor_id, self.product_id) {
            (Some(v), Some(p)) => format!("{:04x}:{:04x}", v, p),
            _ => "unknown".to_string(),
        }
    }

    pub fn label(&self) -> String {
        match (self.manufacturer.as_deref(), self.product.as_deref()) {
            (Some(m), Some(p)) => format!("{m} {p}"),
            (None, Some(p)) => p.to_string(),
            (Some(m), None) => m.to_string(),
            (None, None) => self.vid_pid(),
        }
    }
}

/// HID transport: real enumeration via `hidapi` when the `hid-real` feature
/// is enabled; otherwise a deterministic simulated device set is returned
/// so tests and CI stay portable.
pub struct HidTransport;

impl HidTransport {
    /// Enumerate all currently attached HID devices.
    pub fn enumerate() -> Vec<HidDeviceInfo> {
        #[cfg(feature = "hid-real")]
        {
            enumerate_real()
        }
        #[cfg(not(feature = "hid-real"))]
        {
            vec![
                HidDeviceInfo {
                    path: "/dev/hidraw0".to_string(),
                    vendor_id: Some(0x046D),
                    product_id: Some(0xC52B),
                    manufacturer: Some("Logitech".into()),
                    product: Some("Unifying Receiver".into()),
                    serial_number: Some("12345678".into()),
                    usage_page: Some(0x01),
                    usage_id: Some(0x02),
                    interface_number: Some(0),
                },
                HidDeviceInfo {
                    path: "/dev/hidraw1".to_string(),
                    vendor_id: Some(0x0C45),
                    product_id: Some(0x6366),
                    manufacturer: Some("Microdia".into()),
                    product: Some("USB Keyboard".into()),
                    serial_number: None,
                    usage_page: Some(0x01),
                    usage_id: Some(0x06),
                    interface_number: Some(0),
                },
            ]
        }
    }

    pub fn probe(&self, target: &str) -> Result<ProbeInfo, HalError> {
        if target.starts_with("hid:") || target.starts_with("/dev/hidraw") {
            Ok(ProbeInfo {
                transport: Transport::Hid,
                target: target.to_string(),
                connected: true,
            })
        } else {
            Err(HalError::UnsupportedTransport(target.to_string()))
        }
    }
}

#[cfg(feature = "hid-real")]
fn enumerate_real() -> Vec<HidDeviceInfo> {
    match hidapi::HidApi::new() {
        Ok(api) => api
            .device_list()
            .filter_map(|info| {
                let vid = if info.vendor_id() != 0 {
                    Some(info.vendor_id() as u16)
                } else {
                    None
                };
                let pid = if info.product_id() != 0 {
                    Some(info.product_id() as u16)
                } else {
                    None
                };
                Some(HidDeviceInfo {
                    path: info.path().to_string_lossy().into_owned(),
                    vendor_id: vid,
                    product_id: pid,
                    manufacturer: info.manufacturer_string().ok(),
                    product: info.product_string().ok(),
                    serial_number: info.serial_number().ok(),
                    usage_page: Some(info.usage_page()),
                    usage_id: Some(info.usage()),
                    interface_number: None,
                })
            })
            .collect(),
        Err(_) => Vec::new(),
    }
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct ProbeInfo {
    pub transport: Transport,
    pub target: String,
    pub connected: bool,
}

pub struct HidMonitor {
    previous: std::collections::HashMap<String, HidDeviceInfo>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum HidChange {
    Connected(HidDeviceInfo),
    Disconnected(HidDeviceInfo),
}

impl HidMonitor {
    pub fn new() -> Self {
        Self {
            previous: std::collections::HashMap::new(),
        }
    }

    pub fn prime(&mut self) {
        self.previous = Self::snapshot();
    }

    fn snapshot() -> std::collections::HashMap<String, HidDeviceInfo> {
        HidTransport::enumerate()
            .into_iter()
            .map(|d| (d.path.clone(), d))
            .collect()
    }

    fn diff(
        previous: &std::collections::HashMap<String, HidDeviceInfo>,
        current: &std::collections::HashMap<String, HidDeviceInfo>,
    ) -> Vec<HidChange> {
        let mut changes = Vec::new();
        for dev in current.values() {
            if !previous.contains_key(&dev.path) {
                changes.push(HidChange::Connected(dev.clone()));
            }
        }
        for dev in previous.values() {
            if !current.contains_key(&dev.path) {
                changes.push(HidChange::Disconnected(dev.clone()));
            }
        }
        changes
    }

    pub fn poll(&mut self) -> Vec<HidChange> {
        let current = Self::snapshot();
        let changes = Self::diff(&self.previous, &current);
        self.previous = current;
        changes
    }

    pub fn connected(&self) -> Vec<HidDeviceInfo> {
        self.previous.values().cloned().collect()
    }
}

impl Default for HidMonitor {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn enumerate_returns_devices() {
        let devices = HidTransport::enumerate();
        assert!(!devices.is_empty());
        assert!(devices.iter().all(|d| !d.path.is_empty()));
    }

    #[test]
    fn probe_accepts_hid_prefix() {
        let transport = HidTransport;
        let r = transport.probe("hid:046D:C52B").unwrap();
        assert_eq!(r.transport, Transport::Hid);
        assert!(r.connected);
    }

    #[test]
    fn probe_accepts_hidraw_path() {
        let transport = HidTransport;
        let r = transport.probe("/dev/hidraw0").unwrap();
        assert_eq!(r.transport, Transport::Hid);
        assert!(r.connected);
    }

    #[test]
    fn monitor_emits_connect_and_disconnect() {
        let dev = HidDeviceInfo {
            path: "/dev/hidraw2".into(),
            vendor_id: Some(0x1234),
            product_id: Some(0x5678),
            manufacturer: None,
            product: None,
            serial_number: None,
            usage_page: Some(0x01),
            usage_id: Some(0x02),
            interface_number: Some(0),
        };

        let mut monitor = HidMonitor::new();
        monitor.previous.insert(dev.path.clone(), dev.clone());
        assert!(HidMonitor::diff(&monitor.previous, &monitor.previous).is_empty());

        let empty = std::collections::HashMap::new();
        let changes = HidMonitor::diff(&monitor.previous, &empty);
        assert_eq!(changes.len(), 1);
        assert!(matches!(changes[0], HidChange::Disconnected(_)));

        let changes = HidMonitor::diff(&empty, &monitor.previous);
        assert_eq!(changes.len(), 1);
        assert!(matches!(changes[0], HidChange::Connected(_)));
    }
}
