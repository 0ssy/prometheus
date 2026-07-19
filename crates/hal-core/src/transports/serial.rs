use crate::{HalError, Transport};

#[cfg(feature = "c-hal")]
use crate::c_hal;

/// A snapshot of a serial port as seen by the host.
#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub struct SerialPortInfo {
    /// Stable port path, e.g. `/dev/ttyUSB0`, `COM3`, `/dev/ttyACM0`.
    pub port: String,
    /// USB VID/PID when the port is backed by a USB CDC/ACM device.
    pub vendor_id: Option<u16>,
    pub product_id: Option<u16>,
    pub manufacturer: Option<String>,
    pub product: Option<String>,
    pub serial_number: Option<String>,
    /// Common baud rates the port is known to support (informational).
    pub baud_rates: Vec<u32>,
}

impl SerialPortInfo {
    /// Human-readable label combining product/manufacturer when known.
    pub fn label(&self) -> String {
        match (self.manufacturer.as_deref(), self.product.as_deref()) {
            (Some(m), Some(p)) => format!("{m} {p} ({})", self.port),
            (None, Some(p)) => format!("{p} ({})", self.port),
            (Some(m), None) => format!("{m} ({})", self.port),
            (None, None) => self.port.clone(),
        }
    }
}

/// Serial transport: real (libserialport via `serialport`) enumeration and
/// hot-plug detection, with a simulated fallback when the `serial-real`
/// feature is disabled (used by CI / hosts without libserialport).
pub struct SerialTransport;

impl SerialTransport {
    /// Enumerate all currently available serial ports.
    #[cfg(feature = "serial-real")]
    pub fn enumerate() -> Vec<SerialPortInfo> {
        match serialport::available_ports() {
            Ok(ports) => ports
                .into_iter()
                .map(|p| {
                    let (vid, pid, manufacturer, product, serial) = match &p.port_type {
                        serialport::SerialPortType::UsbPort(usb) => (
                            Some(usb.vid),
                            Some(usb.pid),
                            usb.manufacturer.clone(),
                            usb.product.clone(),
                            usb.serial_number.clone(),
                        ),
                        _ => (None, None, None, None, None),
                    };
                    SerialPortInfo {
                        port: p.port_name,
                        vendor_id: vid,
                        product_id: pid,
                        manufacturer,
                        product,
                        serial_number: serial,
                        baud_rates: vec![
                            9600, 19200, 38400, 57600, 115200, 230400, 460800, 921600,
                        ],
                    }
                })
                .collect(),
            Err(_) => Vec::new(),
        }
    }

    #[cfg(not(feature = "serial-real"))]
    pub fn enumerate() -> Vec<SerialPortInfo> {
        vec![
            SerialPortInfo {
                port: "/dev/ttyUSB0".to_string(),
                vendor_id: Some(0x18D1),
                product_id: Some(0x4EE7),
                manufacturer: Some("Mock Manufacturer".into()),
                product: Some("Mock UART Device".into()),
                serial_number: Some("TTY123456789".into()),
                baud_rates: vec![9600, 115200, 921600],
            },
            SerialPortInfo {
                port: "COM3".to_string(),
                vendor_id: Some(0x2E8A),
                product_id: Some(0x0005),
                manufacturer: Some("Raspberry Pi".into()),
                product: Some("RP2 UART".into()),
                serial_number: Some("0000000000000000".into()),
                baud_rates: vec![9600, 115200],
            },
        ]
    }

    pub fn probe(&self, target: &str) -> Result<ProbeInfo, HalError> {
        if target.starts_with("serial:") || target.starts_with("COM") || target.starts_with("/dev/tty") {
            Ok(ProbeInfo {
                transport: Transport::Serial,
                target: target.to_string(),
                connected: true,
                baud_rate: None,
            })
        } else {
            Err(HalError::UnsupportedTransport(target.to_string()))
        }
    }
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct ProbeInfo {
    pub transport: Transport,
    pub target: String,
    pub connected: bool,
    pub baud_rate: Option<u32>,
}

/// Minimal hot-plug detector backed by periodic re-enumeration.
pub struct SerialMonitor {
    previous: std::collections::HashMap<String, SerialPortInfo>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum SerialChange {
    Connected(SerialPortInfo),
    Disconnected(SerialPortInfo),
}

impl SerialMonitor {
    pub fn new() -> Self {
        Self {
            previous: std::collections::HashMap::new(),
        }
    }

    pub fn prime(&mut self) {
        self.previous = Self::snapshot();
    }

    fn snapshot() -> std::collections::HashMap<String, SerialPortInfo> {
        SerialTransport::enumerate()
            .into_iter()
            .map(|p| (p.port.clone(), p))
            .collect()
    }

    fn diff(
        previous: &std::collections::HashMap<String, SerialPortInfo>,
        current: &std::collections::HashMap<String, SerialPortInfo>,
    ) -> Vec<SerialChange> {
        let mut changes = Vec::new();
        for port in current.values() {
            if !previous.contains_key(&port.port) {
                changes.push(SerialChange::Connected(port.clone()));
            }
        }
        for port in previous.values() {
            if !current.contains_key(&port.port) {
                changes.push(SerialChange::Disconnected(port.clone()));
            }
        }
        changes
    }

    /// Compare the current port set with the previous snapshot and return
    /// the connect/disconnect deltas, updating internal state.
    pub fn poll(&mut self) -> Vec<SerialChange> {
        let current = Self::snapshot();
        let changes = Self::diff(&self.previous, &current);
        self.previous = current;
        changes
    }

    pub fn connected(&self) -> Vec<SerialPortInfo> {
        self.previous.values().cloned().collect()
    }
}

impl Default for SerialMonitor {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn monitor_emits_connect_and_disconnect() {
        let port = SerialPortInfo {
            port: "COM9".into(),
            vendor_id: Some(0x18D1),
            product_id: Some(0x4EE7),
            manufacturer: None,
            product: None,
            serial_number: None,
            baud_rates: vec![115200],
        };

        let mut monitor = SerialMonitor::new();
        monitor.previous.insert(port.port.clone(), port.clone());
        assert!(SerialMonitor::diff(&monitor.previous, &monitor.previous).is_empty());

        let empty = std::collections::HashMap::new();
        let changes = SerialMonitor::diff(&monitor.previous, &empty);
        assert_eq!(changes.len(), 1);
        assert!(matches!(changes[0], SerialChange::Disconnected(_)));

        let changes = SerialMonitor::diff(&empty, &monitor.previous);
        assert_eq!(changes.len(), 1);
        assert!(matches!(changes[0], SerialChange::Connected(_)));
    }

    #[test]
    fn enumerate_returns_ports() {
        let ports = SerialTransport::enumerate();
        assert!(!ports.is_empty());
        assert!(ports.iter().all(|p| !p.port.is_empty()));
    }
}
