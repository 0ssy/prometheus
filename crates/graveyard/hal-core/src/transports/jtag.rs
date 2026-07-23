use crate::HalError;

pub struct JtagTransport;

impl JtagTransport {
    pub fn probe(&self, target: &str) -> Result<(), HalError> {
        if target.starts_with("jtag:") || target.starts_with("swd:") {
            Ok(())
        } else {
            Err(HalError::UnsupportedTransport(target.to_string()))
        }
    }
}
