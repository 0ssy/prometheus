use crate::{HalError, Transport};

pub struct SerialTransport;

impl SerialTransport {
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
