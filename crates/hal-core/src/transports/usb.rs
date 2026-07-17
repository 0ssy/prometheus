use crate::{HalError, Transport};

/// USB transport via platform adapters (libusb / WinUSB / usbd).
pub struct UsbTransport;

impl UsbTransport {
    pub fn probe(&self, target: &str) -> Result<ProbeInfo, HalError> {
        if target.starts_with("usb:") || target.starts_with("dev-") {
            Ok(ProbeInfo {
                transport: Transport::Usb,
                target: target.to_string(),
                connected: true,
                descriptor: None,
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
    pub descriptor: Option<String>,
}
