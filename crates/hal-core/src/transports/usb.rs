use crate::{HalError, Transport};

#[cfg(feature = "c-hal")]
use crate::c_hal;

/// USB transport via platform adapters (libusb / WinUSB / usbd).
pub struct UsbTransport;

impl UsbTransport {
    #[cfg(feature = "c-hal")]
    pub fn enumerate() -> Vec<String> {
        let list = unsafe { c_hal::prom_usb_enumerate() };
        let mut devices = Vec::new();
        for i in 0..list.count {
            let dev = unsafe { *list.devices.as_ptr().add(i) };
            let desc = unsafe {
                std::ffi::CStr::from_ptr(dev.product.as_ptr() as *const i8)
                    .to_string_lossy()
                    .into_owned()
            };
            devices.push(format!("{:04x}:{:04x}:{}", dev.vendor_id, dev.product_id, desc));
        }
        devices
    }

    #[cfg(not(feature = "c-hal"))]
    pub fn enumerate() -> Vec<String> {
        vec!["simulated-usb-0".to_string(), "simulated-usb-1".to_string()]
    }

    pub fn probe(&self, target: &str) -> Result<ProbeInfo, HalError> {
        if target.starts_with("usb:") || target.starts_with("dev-") || target.contains(':') {
            Ok(ProbeInfo {
                transport: Transport::Usb,
                target: target.to_string(),
                connected: true,
                descriptor: None,
                vendor_id: None,
                product_id: None,
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
    pub vendor_id: Option<u16>,
    pub product_id: Option<u16>,
}
