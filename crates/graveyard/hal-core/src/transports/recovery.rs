use crate::{HalError, Transport};

/// Recovery mode identifiers supported by the platform.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, serde::Serialize, serde::Deserialize)]
pub enum RecoveryMode {
    AndroidRecovery,
    Edl,
    Odin,
    Dfu,
    Bios,
    Uefi,
    Tpm,
    Router,
    IoT,
    Drone,
    Vehicle,
    Ecu,
    Eeprom,
    Nand,
    Nor,
    SpiFlash,
    EmbeddedLinux,
}

impl RecoveryMode {
    pub fn as_str(&self) -> &'static str {
        match self {
            RecoveryMode::AndroidRecovery => "android_recovery",
            RecoveryMode::Edl => "edl",
            RecoveryMode::Odin => "odin",
            RecoveryMode::Dfu => "dfu",
            RecoveryMode::Bios => "bios",
            RecoveryMode::Uefi => "uefi",
            RecoveryMode::Tpm => "tpm",
            RecoveryMode::Router => "router",
            RecoveryMode::IoT => "iot",
            RecoveryMode::Drone => "drone",
            RecoveryMode::Vehicle => "vehicle",
            RecoveryMode::Ecu => "ecu",
            RecoveryMode::Eeprom => "eeprom",
            RecoveryMode::Nand => "nand",
            RecoveryMode::Nor => "nor",
            RecoveryMode::SpiFlash => "spi_flash",
            RecoveryMode::EmbeddedLinux => "embedded_linux",
        }
    }

    pub fn parse(s: &str) -> Option<Self> {
        match s.to_ascii_lowercase().as_str() {
            "android_recovery" | "android" | "recovery" => Some(RecoveryMode::AndroidRecovery),
            "edl" | "qualcomm" | "sahara" | "firehose" => Some(RecoveryMode::Edl),
            "odin" | "samsung" => Some(RecoveryMode::Odin),
            "dfu" => Some(RecoveryMode::Dfu),
            "bios" => Some(RecoveryMode::Bios),
            "uefi" => Some(RecoveryMode::Uefi),
            "tpm" => Some(RecoveryMode::Tpm),
            "router" => Some(RecoveryMode::Router),
            "iot" => Some(RecoveryMode::IoT),
            "drone" => Some(RecoveryMode::Drone),
            "vehicle" | "obd2" => Some(RecoveryMode::Vehicle),
            "ecu" => Some(RecoveryMode::Ecu),
            "eeprom" => Some(RecoveryMode::Eeprom),
            "nand" => Some(RecoveryMode::Nand),
            "nor" => Some(RecoveryMode::Nor),
            "spi_flash" | "spi" => Some(RecoveryMode::SpiFlash),
            "embedded_linux" | "linux" => Some(RecoveryMode::EmbeddedLinux),
            _ => None,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub struct RecoveryDeviceInfo {
    pub mode: RecoveryMode,
    pub transport: Transport,
    /// Device identifier within the recovery channel.
    pub device_id: String,
    /// Human-readable product/model when available.
    pub product: Option<String>,
    /// Recovery status, e.g. `idle`, `flashing`, `download`, `error`.
    pub status: String,
}

impl RecoveryDeviceInfo {
    pub fn label(&self) -> String {
        format!("{} {}", self.mode.as_str(), self.device_id)
    }
}

pub struct RecoveryTransport;

impl RecoveryTransport {
    pub fn enumerate(mode: RecoveryMode) -> Vec<RecoveryDeviceInfo> {
        enumerate_simulated(mode)
    }

    pub fn probe(&self, target: &str) -> Result<ProbeInfo, HalError> {
        let rest = target.strip_prefix("recovery:").unwrap_or(target);
        let mode = rest.split(':').next().unwrap_or("");
        if RecoveryMode::parse(mode).is_some() {
            Ok(ProbeInfo {
                transport: Transport::Recovery,
                target: target.to_string(),
                mode: RecoveryMode::parse(mode),
                connected: true,
            })
        } else {
            Err(HalError::UnsupportedTransport(target.to_string()))
        }
    }
}

fn enumerate_simulated(mode: RecoveryMode) -> Vec<RecoveryDeviceInfo> {
    vec![
        RecoveryDeviceInfo {
            mode,
            transport: Transport::Recovery,
            device_id: format!("recovery-{:?}", mode).to_lowercase(),
            product: Some(format!("Simulated {:?}", mode)),
            status: "idle".to_string(),
        }
    ]
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct ProbeInfo {
    pub transport: Transport,
    pub target: String,
    pub mode: Option<RecoveryMode>,
    pub connected: bool,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn enumerate_returns_devices() {
        let devices = RecoveryTransport::enumerate(RecoveryMode::Edl);
        assert_eq!(devices.len(), 1);
        assert_eq!(devices[0].mode, RecoveryMode::Edl);
        assert_eq!(devices[0].transport, Transport::Recovery);
    }

    #[test]
    fn probe_accepts_edl_target() {
        let transport = RecoveryTransport;
        let r = transport.probe("recovery:edl:0000").unwrap();
        assert_eq!(r.transport, Transport::Recovery);
        assert_eq!(r.mode, Some(RecoveryMode::Edl));
        assert!(r.connected);
    }

    #[test]
    fn probe_accepts_android_recovery_target() {
        let transport = RecoveryTransport;
        let r = transport.probe("recovery:android_recovery").unwrap();
        assert_eq!(r.transport, Transport::Recovery);
        assert_eq!(r.mode, Some(RecoveryMode::AndroidRecovery));
    }

    #[test]
    fn probe_accepts_uefi_target() {
        let transport = RecoveryTransport;
        let r = transport.probe("recovery:uefi").unwrap();
        assert_eq!(r.transport, Transport::Recovery);
        assert_eq!(r.mode, Some(RecoveryMode::Uefi));
    }

    #[test]
    fn recovery_mode_parse_roundtrip() {
        assert_eq!(RecoveryMode::parse("edl"), Some(RecoveryMode::Edl));
        assert_eq!(RecoveryMode::parse("odIN"), Some(RecoveryMode::Odin));
        assert_eq!(RecoveryMode::parse("unknown"), None);
    }

    #[test]
    fn mode_as_str_roundtrip() {
        for mode in [
            RecoveryMode::AndroidRecovery,
            RecoveryMode::Edl,
            RecoveryMode::Odin,
            RecoveryMode::Dfu,
            RecoveryMode::Bios,
            RecoveryMode::Uefi,
            RecoveryMode::Tpm,
        ] {
            assert_eq!(RecoveryMode::parse(mode.as_str()), Some(mode));
        }
    }
}
