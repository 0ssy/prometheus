use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum Protocol {
    GPIO,
    Serial,
    USB,
    I2C,
    SPI,
    CAN,
    JTAG,
    Bluetooth,
    Network,
}

impl Protocol {
    pub fn as_str(&self) -> &'static str {
        match self {
            Protocol::GPIO => "GPIO",
            Protocol::Serial => "Serial",
            Protocol::USB => "USB",
            Protocol::I2C => "I2C",
            Protocol::SPI => "SPI",
            Protocol::CAN => "CAN",
            Protocol::JTAG => "JTAG",
            Protocol::Bluetooth => "Bluetooth",
            Protocol::Network => "Network",
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum SafetyLevel {
    Safe,
    Unsafe,
    Critical,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HalTraitMethod {
    pub name: String,
    pub signature: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HalTraitDefinition {
    pub name: String,
    pub methods: Vec<HalTraitMethod>,
    pub safety_level: SafetyLevel,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DriverManifest {
    pub id: String,
    pub name: String,
    pub version: String,
    pub description: String,
    pub author: String,
    pub protocols: Vec<Protocol>,
    pub hal_traits: Vec<HalTraitDefinition>,
    pub entrypoint: String,
}

impl DriverManifest {
    pub fn from_json(s: &str) -> Result<Self, serde_json::Error> {
        serde_json::from_str(s)
    }

    pub fn to_json(&self) -> Result<String, serde_json::Error> {
        serde_json::to_string_pretty(self)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn serialize_roundtrip() {
        let manifest = DriverManifest {
            id: "drv-1".into(),
            name: "Example Driver".into(),
            version: "0.1.0".into(),
            description: "An example driver".into(),
            author: "prometheus".into(),
            protocols: vec![Protocol::USB, Protocol::Serial],
            hal_traits: vec![HalTraitDefinition {
                name: "Probeable".into(),
                methods: vec![HalTraitMethod {
                    name: "probe".into(),
                    signature: "fn probe(&self, target: &str)".into(),
                }],
                safety_level: SafetyLevel::Safe,
            }],
            entrypoint: "libdriver.so".into(),
        };
        let json = manifest.to_json().unwrap();
        let back = DriverManifest::from_json(&json).unwrap();
        assert_eq!(back.id, "drv-1");
        assert_eq!(back.protocols.len(), 2);
    }
}
