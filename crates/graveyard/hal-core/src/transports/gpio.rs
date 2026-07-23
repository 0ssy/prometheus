use crate::{HalError, Transport};

#[cfg(feature = "c-hal")]
use crate::c_hal;

pub struct GpioTransport;

impl GpioTransport {
    #[cfg(feature = "c-hal")]
    pub fn enumerate_chips() -> Vec<(u32, String)> {
        let list = unsafe { c_hal::prom_gpio_list_chips() };
        let mut chips = Vec::new();
        for i in 0..list.chip_count {
            let chip = unsafe { *list.chips.as_ptr().add(i) };
            let label = unsafe {
                std::ffi::CStr::from_ptr(chip.label.as_ptr() as *const i8)
                    .to_string_lossy()
                    .into_owned()
            };
            chips.push((chip.chip_id, label));
        }
        chips
    }

    #[cfg(not(feature = "c-hal"))]
    pub fn enumerate_chips() -> Vec<(u32, String)> {
        vec![(0, "gpio0".to_string())]
    }

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
