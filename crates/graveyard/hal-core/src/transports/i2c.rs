use crate::HalError;

pub struct I2cTransport;

impl I2cTransport {
    pub fn probe(&self, target: &str) -> Result<(), HalError> {
        if target.starts_with("i2c:") {
            Ok(())
        } else {
            Err(HalError::UnsupportedTransport(target.to_string()))
        }
    }
}
