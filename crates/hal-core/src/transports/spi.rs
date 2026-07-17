use crate::HalError;

pub struct SpiTransport;

impl SpiTransport {
    pub fn probe(&self, target: &str) -> Result<(), HalError> {
        if target.starts_with("spi:") {
            Ok(())
        } else {
            Err(HalError::UnsupportedTransport(target.to_string()))
        }
    }
}
