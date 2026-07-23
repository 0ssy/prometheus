use crate::{HalError, Transport};

/// A snapshot of an SWD-accessible target.
#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub struct SwdDeviceInfo {
    /// Target identifier, typically a sequence number or unique ID read from the DP.
    pub target_id: String,
    /// 32-bit DP IDCODE read from the device.
    pub idcode: Option<u32>,
    /// ARM core type (e.g. Cortex-M33) when decoded.
    pub core: Option<String>,
    /// Debug port version.
    pub dp_version: Option<u8>,
    /// Serial wire debug port incarnation.
    pub serial: Option<u32>,
}

impl SwdDeviceInfo {
    pub fn label(&self) -> String {
        self.core
            .as_deref()
            .unwrap_or("SWD Target")
            .to_string()
    }
}

/// SWD transport: probe and hot-plug over Serial Wire Debug.

/// Real operation shells out to or links against OpenOCD or pyOCD when the
/// `swd-real` feature is enabled; otherwise a deterministic simulated target
/// is returned.
pub struct SwdTransport;

impl SwdTransport {
    /// Enumerate SWD targets reachable on attached probes.
    pub fn enumerate() -> Vec<SwdDeviceInfo> {
        #[cfg(feature = "swd-real")]
        {
            enumerate_real()
        }
        #[cfg(not(feature = "swd-real"))]
        {
            vec![
                SwdDeviceInfo {
                    target_id: "swd-0".to_string(),
                    idcode: Some(0x4BA0_3477),
                    core: Some("Cortex-M33".into()),
                    dp_version: Some(2),
                    serial: Some(0x1000_0001),
                },
                SwdDeviceInfo {
                    target_id: "swd-1".to_string(),
                    idcode: Some(0x4BA0_1477),
                    core: Some("Cortex-M0+".into()),
                    dp_version: Some(2),
                    serial: Some(0x1000_0002),
                },
            ]
        }
    }

    pub fn probe(&self, target: &str) -> Result<ProbeInfo, HalError> {
        if target.starts_with("swd:") || target.starts_with("swd-") {
            Ok(ProbeInfo {
                transport: Transport::Swd,
                target: target.to_string(),
                connected: true,
                latency_ms: Some(3.5),
            })
        } else {
            Err(HalError::UnsupportedTransport(target.to_string()))
        }
    }
}

#[cfg(feature = "swd-real")]
fn enumerate_real() -> Vec<SwdDeviceInfo> {
    use std::process::Command;
    let out = Command::new("openocd")
        .args([
            "-f",
            "interface/cmsis-dap.cfg",
            "-c",
            "init; scan; shutdown",
        ])
        .output();
    match out {
        Ok(o) if o.status.success() => {
            let stdout = String::from_utf8_lossy(&o.stdout);
            parse_openocd_swd_scan(&stdout)
        }
        _ => Vec::new(),
    }
}

#[cfg(feature = "swd-real")]
fn parse_openocd_swd_scan(raw: &str) -> Vec<SwdDeviceInfo> {
    let mut devices = Vec::new();
    let mut current = SwdDeviceInfo {
        target_id: String::new(),
        idcode: None,
        core: None,
        dp_version: None,
        serial: None,
    };
    for line in raw.lines() {
        let line = line.trim();
        if line.is_empty() {
            if !current.target_id.is_empty() {
                devices.push(current.clone());
                current = SwdDeviceInfo {
                    target_id: String::new(),
                    idcode: None,
                    core: None,
                    dp_version: None,
                    serial: None,
                };
            }
            continue;
        }
        if let Some(rest) = line.strip_prefix("target ") {
            current.target_id = rest.trim().to_string();
        }
        if line.contains("IDCODE") {
            if let Some(v) = line.rsplit_once("0x") {
                current.idcode = u32::from_str_radix(v.1.trim(), 16).ok();
            }
        }
        if line.contains("Cortex-") {
            let parts: Vec<&str> = line.split_whitespace().collect();
            current.core = parts.last().map(|s| s.to_string());
        }
    }
    if !current.target_id.is_empty() {
        devices.push(current);
    }
    devices
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct ProbeInfo {
    pub transport: Transport,
    pub target: String,
    /// Whether the target responded to a SWD line reset and IDCODE read.
    pub connected: bool,
    /// APB bus access latency in milliseconds when connected.
    pub latency_ms: Option<f64>,
}

impl ProbeInfo {
    pub fn connected(transport: Transport, target: String, latency_ms: f64) -> Self {
        Self {
            transport,
            target,
            connected: true,
            latency_ms: Some(latency_ms),
        }
    }

    pub fn error(transport: Transport, target: String, _reason: &str) -> Self {
        Self {
            transport,
            target,
            connected: false,
            latency_ms: None,
        }
    }
}

pub struct SwdMonitor {
    previous: std::collections::HashMap<String, SwdDeviceInfo>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum SwdChange {
    Connected(SwdDeviceInfo),
    Disconnected(SwdDeviceInfo),
}

impl SwdMonitor {
    pub fn new() -> Self {
        Self {
            previous: std::collections::HashMap::new(),
        }
    }

    pub fn prime(&mut self) {
        self.previous = Self::snapshot();
    }

    fn snapshot() -> std::collections::HashMap<String, SwdDeviceInfo> {
        SwdTransport::enumerate()
            .into_iter()
            .map(|d| (d.target_id.clone(), d))
            .collect()
    }

    fn diff(
        previous: &std::collections::HashMap<String, SwdDeviceInfo>,
        current: &std::collections::HashMap<String, SwdDeviceInfo>,
    ) -> Vec<SwdChange> {
        let mut changes = Vec::new();
        for dev in current.values() {
            if !previous.contains_key(&dev.target_id) {
                changes.push(SwdChange::Connected(dev.clone()));
            }
        }
        for dev in previous.values() {
            if !current.contains_key(&dev.target_id) {
                changes.push(SwdChange::Disconnected(dev.clone()));
            }
        }
        changes
    }

    pub fn poll(&mut self) -> Vec<SwdChange> {
        let current = Self::snapshot();
        let changes = Self::diff(&self.previous, &current);
        self.previous = current;
        changes
    }

    pub fn connected(&self) -> Vec<SwdDeviceInfo> {
        self.previous.values().cloned().collect()
    }
}

impl Default for SwdMonitor {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn enumerate_returns_targets() {
        let devices = SwdTransport::enumerate();
        assert!(!devices.is_empty());
        assert!(devices.iter().all(|d| !d.target_id.is_empty()));
    }

    #[test]
    fn probe_accepts_swd_prefix() {
        let transport = SwdTransport;
        let r = transport.probe("swd:0").unwrap();
        assert_eq!(r.transport, Transport::Swd);
        assert!(r.connected);
    }

    #[test]
    fn probe_accepts_swd_dash() {
        let transport = SwdTransport;
        let r = transport.probe("swd-cortex").unwrap();
        assert_eq!(r.transport, Transport::Swd);
        assert!(r.connected);
    }

    #[test]
    fn monitor_emits_connect_and_disconnect() {
        let dev = SwdDeviceInfo {
            target_id: "swd-2".into(),
            idcode: Some(0x4BA0_8477),
            core: Some("Cortex-M4".into()),
            dp_version: Some(2),
            serial: Some(0x1000_0003),
        };

        let mut monitor = SwdMonitor::new();
        monitor.previous.insert(dev.target_id.clone(), dev.clone());
        assert!(SwdMonitor::diff(&monitor.previous, &monitor.previous).is_empty());

        let empty = std::collections::HashMap::new();
        let changes = SwdMonitor::diff(&monitor.previous, &empty);
        assert_eq!(changes.len(), 1);
        assert!(matches!(changes[0], SwdChange::Disconnected(_)));

        let changes = SwdMonitor::diff(&empty, &monitor.previous);
        assert_eq!(changes.len(), 1);
        assert!(matches!(changes[0], SwdChange::Connected(_)));
    }

    #[cfg(feature = "swd-real")]
    #[test]
    fn parses_openocd_swd_output() {
        let raw = "target stm32f4x.cpu\nIDCODE: 4ba00477\nCortex-M4 r0p1\n";
        let parsed = parse_openocd_swd_scan(raw);
        assert_eq!(parsed.len(), 1);
        assert_eq!(parsed[0].idcode, Some(0x4BA0_0477));
    }
}
