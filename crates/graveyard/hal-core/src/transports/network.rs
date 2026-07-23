use crate::HalError;

pub struct NetworkTransport;

impl NetworkTransport {
    pub fn probe(&self, target: &str) -> Result<(), HalError> {
        if target.starts_with("tcp:") || target.starts_with("udp:") || target.starts_with("http:") {
            Ok(())
        } else {
            Err(HalError::UnsupportedTransport(target.to_string()))
        }
    }
}
