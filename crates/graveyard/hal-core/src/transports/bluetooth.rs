use crate::HalError;

pub struct BluetoothTransport;

impl BluetoothTransport {
    pub fn probe(&self, target: &str) -> Result<(), HalError> {
        if target.starts_with("ble:") || target.starts_with("bt:") {
            Ok(())
        } else {
            Err(HalError::UnsupportedTransport(target.to_string()))
        }
    }
}
