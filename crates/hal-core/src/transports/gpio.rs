use crate::{HalError, Transport};

pub struct GpioTransport;

impl GpioTransport {
    pub fn probe(&self, target: &str) -> Result<ProbeInfo, HalError> {
        if target.starts_with("gpio:") {
            Ok(ProbeInfo {
                transport: Transport::Gpio,
                target: target.to_string(),
                connected: true,
                pin_count: None,
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
    pub pin_count: Option<u32>,
}
