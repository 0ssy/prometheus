use crate::HalError;

pub struct CanTransport;

impl CanTransport {
    pub fn probe(&self, target: &str) -> Result<(), HalError> {
        if target.starts_with("can:") || target.starts_with("vcan:") {
            Ok(())
        } else {
            Err(HalError::UnsupportedTransport(target.to_string()))
        }
    }
}
