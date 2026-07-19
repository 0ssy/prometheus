use crate::{HalError, Transport};

#[cfg(feature = "c-hal")]
use crate::c_hal;

/// A snapshot of a USB device as seen by the host.
#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub struct UsbDeviceInfo {
    /// Stable identity used to track connect/disconnect across events.
    /// On platforms where the OS provides a stable path/port we use it;
    /// otherwise we fall back to `vid:pid:serial`.
    pub device_id: String,
    pub vendor_id: u16,
    pub product_id: u16,
    pub manufacturer: Option<String>,
    pub product: Option<String>,
    pub serial_number: Option<String>,
    /// Bus number the device is attached to (OS dependent).
    pub bus_number: u8,
    /// Address/port on the bus (OS dependent).
    pub port_number: u8,
    /// USB spec release number, e.g. 0x0200 = USB 2.0.
    pub usb_spec: u16,
    /// Device class code.
    pub device_class: u8,
    /// Maximum packet size for endpoint 0.
    pub max_packet_size: u8,
}

impl UsbDeviceInfo {
    /// `vid:pid` formatted as hex, e.g. `18d1:4ee7`.
    pub fn vid_pid(&self) -> String {
        format!("{:04x}:{:04x}", self.vendor_id, self.product_id)
    }

    /// Human-readable label combining product/manufacturer when known.
    pub fn label(&self) -> String {
        match (self.manufacturer.as_deref(), self.product.as_deref()) {
            (Some(m), Some(p)) => format!("{m} {p}"),
            (None, Some(p)) => p.to_string(),
            (Some(m), None) => m.to_string(),
            (None, None) => self.vid_pid(),
        }
    }
}

/// USB transport: real (libusb via `rusb`) enumeration and hot-plug
/// detection, with a simulated fallback when the `usb-real` feature is
/// disabled (used by CI / hosts without libusb).
pub struct UsbTransport;

impl UsbTransport {
    /// Enumerate all currently attached USB devices.
    #[cfg(feature = "usb-real")]
    pub fn enumerate() -> Vec<UsbDeviceInfo> {
        match rusb::devices() {
            Ok(devices) => devices
                .iter()
                .filter_map(|device| {
                    let desc = device.device_descriptor().ok()?;
                    let handle = device.open().ok();
                    let languages = handle
                        .as_ref()
                        .and_then(|h| h.read_languages(std::time::Duration::from_millis(100)).ok());
                    let lang = languages.and_then(|l| l.first().copied());
                    let manufacturer = lang.and_then(|l| {
                        handle
                            .as_ref()
                            .and_then(|h| h.read_manufacturer_string(l, &desc, std::time::Duration::from_millis(100)).ok())
                    });
                    let product = lang.and_then(|l| {
                        handle
                            .as_ref()
                            .and_then(|h| h.read_product_string(l, &desc, std::time::Duration::from_millis(100)).ok())
                    });
                    let serial_number = lang.and_then(|l| {
                        handle
                            .as_ref()
                            .and_then(|h| h.read_serial_number_string(l, &desc, std::time::Duration::from_millis(100)).ok())
                    });
                    let port = device.port_numbers().ok();
                    Some(UsbDeviceInfo {
                        device_id: device_id_for(
                            desc.vendor_id(),
                            desc.product_id(),
                            serial_number.as_deref(),
                            device.bus_number(),
                            port.as_deref(),
                        ),
                        vendor_id: desc.vendor_id(),
                        product_id: desc.product_id(),
                        manufacturer,
                        product,
                        serial_number,
                        bus_number: device.bus_number(),
                        port_number: port.and_then(|p| p.last().copied()).unwrap_or(0),
                        usb_spec: ((desc.usb_version().major() as u16) << 8)
                            | (desc.usb_version().minor() as u16),
                        device_class: desc.class_code(),
                        max_packet_size: desc.max_packet_size(),
                    })
                })
                .collect(),
            Err(_) => Vec::new(),
        }
    }

    #[cfg(not(feature = "usb-real"))]
    pub fn enumerate() -> Vec<UsbDeviceInfo> {
        vec![
            UsbDeviceInfo {
                device_id: "simulated-usb-0".to_string(),
                vendor_id: 0x18d1,
                product_id: 0x4ee7,
                manufacturer: Some("Mock Manufacturer".into()),
                product: Some("Mock USB Device".into()),
                serial_number: Some("USB123456789".into()),
                bus_number: 1,
                port_number: 1,
                usb_spec: 0x0200,
                device_class: 0,
                max_packet_size: 64,
            },
            UsbDeviceInfo {
                device_id: "simulated-usb-1".to_string(),
                vendor_id: 0x2e8a,
                product_id: 0x0005,
                manufacturer: Some("Raspberry Pi".into()),
                product: Some("RP2 Boot".into()),
                serial_number: Some("0000000000000000".into()),
                bus_number: 1,
                port_number: 2,
                usb_spec: 0x0210,
                device_class: 0xef,
                max_packet_size: 64,
            },
        ]
    }

    /// Build an identity string that is stable across re-enumerations so
    /// hot-plug detection can correlate connect/disconnect events.
    pub fn device_id(
        vendor_id: u16,
        product_id: u16,
        serial_number: Option<&str>,
        bus_number: u8,
        port: Option<&[u8]>,
    ) -> String {
        device_id_for(vendor_id, product_id, serial_number, bus_number, port)
    }

    pub fn probe(&self, target: &str) -> Result<ProbeInfo, HalError> {
        if target.starts_with("usb:") || target.starts_with("dev-") || target.contains(':') {
            Ok(ProbeInfo {
                transport: Transport::Usb,
                target: target.to_string(),
                connected: true,
                descriptor: None,
                vendor_id: None,
                product_id: None,
            })
        } else {
            Err(HalError::UnsupportedTransport(target.to_string()))
        }
    }
}

fn device_id_for(
    vendor_id: u16,
    product_id: u16,
    serial_number: Option<&str>,
    bus_number: u8,
    port: Option<&[u8]>,
) -> String {
    let vid_pid = format!("{:04x}:{:04x}", vendor_id, product_id);
    match (serial_number, port) {
        // Prefer bus+port path when available: it is the most stable identity.
        (_, Some(p)) if !p.is_empty() => {
            let port_path = p.iter().map(|n| n.to_string()).collect::<Vec<_>>().join(".");
            format!("usb-{bus_number}.{port_path}:{vid_pid}")
        }
        (Some(s), _) => format!("usb-{vid_pid}:{s}"),
        _ => format!("usb-{vid_pid}:{bus_number}"),
    }
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct ProbeInfo {
    pub transport: Transport,
    pub target: String,
    pub connected: bool,
    pub descriptor: Option<String>,
    pub vendor_id: Option<u16>,
    pub product_id: Option<u16>,
}

/// Minimal hot-plug detector backed by periodic re-enumeration.
///
/// libusb hotplug callbacks require a running event loop; polling is
/// portable, dependency-free, and good enough for tooling and automation.
/// `UsbMonitor` keeps the previous snapshot and yields connect/disconnect
/// deltas on `poll()`.
pub struct UsbMonitor {
    previous: std::collections::HashMap<String, UsbDeviceInfo>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum UsbChange {
    Connected(UsbDeviceInfo),
    Disconnected(UsbDeviceInfo),
}

impl UsbMonitor {
    pub fn new() -> Self {
        Self {
            previous: std::collections::HashMap::new(),
        }
    }

    /// Seed the monitor with the current device set without emitting events.
    pub fn prime(&mut self) {
        self.previous = Self::snapshot();
    }

    fn snapshot() -> std::collections::HashMap<String, UsbDeviceInfo> {
        UsbTransport::enumerate()
            .into_iter()
            .map(|d| (d.device_id.clone(), d))
            .collect()
    }

    /// Compute the connect/disconnect deltas between `previous` and `current`.
    fn diff(
        previous: &std::collections::HashMap<String, UsbDeviceInfo>,
        current: &std::collections::HashMap<String, UsbDeviceInfo>,
    ) -> Vec<UsbChange> {
        let mut changes = Vec::new();
        for dev in current.values() {
            if !previous.contains_key(&dev.device_id) {
                changes.push(UsbChange::Connected(dev.clone()));
            }
        }
        for dev in previous.values() {
            if !current.contains_key(&dev.device_id) {
                changes.push(UsbChange::Disconnected(dev.clone()));
            }
        }
        changes
    }

    /// Compare the current device set with the previous snapshot and return
    /// the connect/disconnect deltas, updating internal state.
    pub fn poll(&mut self) -> Vec<UsbChange> {
        let current = Self::snapshot();
        let changes = Self::diff(&self.previous, &current);
        self.previous = current;
        changes
    }

    pub fn connected(&self) -> Vec<UsbDeviceInfo> {
        self.previous.values().cloned().collect()
    }
}

impl Default for UsbMonitor {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn device_id_is_stable_without_serial() {
        let a = UsbTransport::device_id(0x18d1, 0x4ee7, None, 1, Some(&[1, 2]));
        let b = UsbTransport::device_id(0x18d1, 0x4ee7, None, 1, Some(&[1, 2]));
        assert_eq!(a, b);
        assert!(a.starts_with("usb-1.1.2:18d1:4ee7"));
    }

    #[test]
    fn device_id_falls_back_to_serial() {
        let a = UsbTransport::device_id(0x18d1, 0x4ee7, Some("ABC"), 1, None);
        assert_eq!(a, "usb-18d1:4ee7:ABC");
    }

    #[test]
    fn monitor_emits_connect_and_disconnect() {
        // Drive the monitor purely from injected baselines so the test does
        // not depend on whatever USB devices happen to be attached to the
        // host running the suite.
        let dev = UsbDeviceInfo {
            device_id: "usb-x:18d1:4ee7".into(),
            vendor_id: 0x18d1,
            product_id: 0x4ee7,
            manufacturer: None,
            product: None,
            serial_number: None,
            bus_number: 1,
            port_number: 1,
            usb_spec: 0x0200,
            device_class: 0,
            max_packet_size: 64,
        };

        let mut monitor = UsbMonitor::new();
        // Baseline: device already known -> next poll produces no changes.
        monitor.previous.insert(dev.device_id.clone(), dev.clone());
        assert!(UsbMonitor::diff(&monitor.previous, &monitor.previous).is_empty());

        // Device disappears -> disconnect event.
        let empty = std::collections::HashMap::new();
        let changes = UsbMonitor::diff(&monitor.previous, &empty);
        assert_eq!(changes.len(), 1);
        assert!(matches!(changes[0], UsbChange::Disconnected(_)));

        // Device reappears -> connect event.
        let changes = UsbMonitor::diff(&empty, &monitor.previous);
        assert_eq!(changes.len(), 1);
        assert!(matches!(changes[0], UsbChange::Connected(_)));
    }
}
