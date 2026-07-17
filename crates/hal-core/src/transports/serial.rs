use crate::{HalError, Transport};

#[cfg(feature = "c-hal")]
use crate::c_hal;

pub struct SerialTransport;

impl SerialTransport {
    #[cfg(feature = "c-hal")]
    pub fn enumerate() -> Vec<String> {
        let list = unsafe { c_hal::prom_serial_list_ports() };
        let mut ports_vec = Vec::new();
        let ports_slice = unsafe { std::slice::from_raw_parts(list.ports.as_ptr(), list.count as usize) };
        for port in ports_slice {
            let path = unsafe {
                std::ffi::CStr::from_ptr(port.path.as_ptr() as *const i8)
                    .to_string_lossy()
                    .into_owned()
            };
            ports_vec.push(path);
        }
        ports_vec
    }

    #[cfg(not(feature = "c-hal"))]
    pub fn enumerate() -> Vec<String> {
        vec!["/dev/ttyUSB0".to_string(), "COM3".to_string()]
    }

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
