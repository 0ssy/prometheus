use std::collections::BTreeMap;
use std::io::{Error, ErrorKind};

#[derive(Debug, Clone)]
enum JsonValue {
    String(String),
    Array(Vec<JsonValue>),
    Object(BTreeMap<String, JsonValue>),
    Bool(bool),
    Number(f64),
    Null,
}

struct JsonParser<'a> {
    src: &'a [u8],
    pos: usize,
}

impl<'a> JsonParser<'a> {
    fn new(s: &'a str) -> Self {
        Self {
            src: s.as_bytes(),
            pos: 0,
        }
    }

    fn parse(mut self) -> Result<JsonValue, Error> {
        self.skip_ws();
        let value = self.parse_value()?;
        self.skip_ws();
        if self.pos != self.src.len() {
            return Err(Error::new(ErrorKind::InvalidData, "trailing characters in JSON"));
        }
        Ok(value)
    }

    fn parse_value(&mut self) -> Result<JsonValue, Error> {
        self.skip_ws();
        match self.peek() {
            Some(b'"') => self.parse_string().map(JsonValue::String),
            Some(b'{') => self.parse_object(),
            Some(b'[') => self.parse_array(),
            Some(b't') => self.parse_true(),
            Some(b'f') => self.parse_false(),
            Some(b'n') => self.parse_null(),
            Some(b'-') | Some(b'0'..=b'9') => self.parse_number(),
            _ => Err(Error::new(ErrorKind::InvalidData, "invalid JSON value")),
        }
    }

    fn parse_object(&mut self) -> Result<JsonValue, Error> {
        self.expect(b'{')?;
        self.skip_ws();
        let mut map = BTreeMap::new();
        if self.peek() == Some(b'}') {
            self.pos += 1;
            return Ok(JsonValue::Object(map));
        }

        loop {
            self.skip_ws();
            let key = self.parse_string()?;
            self.skip_ws();
            self.expect(b':')?;
            self.skip_ws();
            let value = self.parse_value()?;
            map.insert(key, value);
            self.skip_ws();
            match self.peek() {
                Some(b',') => self.pos += 1,
                Some(b'}') => {
                    self.pos += 1;
                    break;
                }
                _ => return Err(Error::new(ErrorKind::InvalidData, "invalid JSON object")),
            }
        }
        Ok(JsonValue::Object(map))
    }

    fn parse_array(&mut self) -> Result<JsonValue, Error> {
        self.expect(b'[')?;
        self.skip_ws();
        let mut items = Vec::new();
        if self.peek() == Some(b']') {
            self.pos += 1;
            return Ok(JsonValue::Array(items));
        }
        loop {
            self.skip_ws();
            items.push(self.parse_value()?);
            self.skip_ws();
            match self.peek() {
                Some(b',') => self.pos += 1,
                Some(b']') => {
                    self.pos += 1;
                    break;
                }
                _ => return Err(Error::new(ErrorKind::InvalidData, "invalid JSON array")),
            }
        }
        Ok(JsonValue::Array(items))
    }

    fn parse_string(&mut self) -> Result<String, Error> {
        self.expect(b'"')?;
        let mut out = String::new();
        while let Some(ch) = self.next() {
            match ch {
                b'"' => return Ok(out),
                b'\\' => {
                    let esc = self
                        .next()
                        .ok_or_else(|| Error::new(ErrorKind::InvalidData, "invalid escape"))?;
                    match esc {
                        b'"' => out.push('"'),
                        b'\\' => out.push('\\'),
                        b'/' => out.push('/'),
                        b'b' => out.push('\u{0008}'),
                        b'f' => out.push('\u{000C}'),
                        b'n' => out.push('\n'),
                        b'r' => out.push('\r'),
                        b't' => out.push('\t'),
                        b'u' => {
                            let code = self.parse_hex4()?;
                            let c = char::from_u32(code as u32).ok_or_else(|| {
                                Error::new(ErrorKind::InvalidData, "invalid unicode escape")
                            })?;
                            out.push(c);
                        }
                        _ => return Err(Error::new(ErrorKind::InvalidData, "invalid escape")),
                    }
                }
                c if c < 0x20 => {
                    return Err(Error::new(
                        ErrorKind::InvalidData,
                        "control character in string",
                    ));
                }
                c => out.push(c as char),
            }
        }
        Err(Error::new(ErrorKind::InvalidData, "unterminated string"))
    }

    fn parse_hex4(&mut self) -> Result<u16, Error> {
        let mut value: u16 = 0;
        for _ in 0..4 {
            let b = self
                .next()
                .ok_or_else(|| Error::new(ErrorKind::InvalidData, "invalid unicode escape"))?;
            value <<= 4;
            value |= match b {
                b'0'..=b'9' => (b - b'0') as u16,
                b'a'..=b'f' => (10 + b - b'a') as u16,
                b'A'..=b'F' => (10 + b - b'A') as u16,
                _ => return Err(Error::new(ErrorKind::InvalidData, "invalid unicode escape")),
            };
        }
        Ok(value)
    }

    fn parse_true(&mut self) -> Result<JsonValue, Error> {
        self.expect_bytes(b"true")?;
        Ok(JsonValue::Bool(true))
    }

    fn parse_false(&mut self) -> Result<JsonValue, Error> {
        self.expect_bytes(b"false")?;
        Ok(JsonValue::Bool(false))
    }

    fn parse_null(&mut self) -> Result<JsonValue, Error> {
        self.expect_bytes(b"null")?;
        Ok(JsonValue::Null)
    }

    fn parse_number(&mut self) -> Result<JsonValue, Error> {
        let start = self.pos;
        if self.peek() == Some(b'-') {
            self.pos += 1;
        }
        match self.peek() {
            Some(b'0') => self.pos += 1,
            Some(b'1'..=b'9') => {
                self.pos += 1;
                while matches!(self.peek(), Some(b'0'..=b'9')) {
                    self.pos += 1;
                }
            }
            _ => return Err(Error::new(ErrorKind::InvalidData, "invalid number")),
        }

        if self.peek() == Some(b'.') {
            self.pos += 1;
            if !matches!(self.peek(), Some(b'0'..=b'9')) {
                return Err(Error::new(ErrorKind::InvalidData, "invalid number"));
            }
            while matches!(self.peek(), Some(b'0'..=b'9')) {
                self.pos += 1;
            }
        }

        if matches!(self.peek(), Some(b'e' | b'E')) {
            self.pos += 1;
            if matches!(self.peek(), Some(b'+' | b'-')) {
                self.pos += 1;
            }
            if !matches!(self.peek(), Some(b'0'..=b'9')) {
                return Err(Error::new(ErrorKind::InvalidData, "invalid number"));
            }
            while matches!(self.peek(), Some(b'0'..=b'9')) {
                self.pos += 1;
            }
        }

        let s = std::str::from_utf8(&self.src[start..self.pos])
            .map_err(|_| Error::new(ErrorKind::InvalidData, "invalid number"))?;
        let n = s
            .parse::<f64>()
            .map_err(|_| Error::new(ErrorKind::InvalidData, "invalid number"))?;
        Ok(JsonValue::Number(n))
    }

    fn skip_ws(&mut self) {
        while matches!(self.peek(), Some(b' ' | b'\n' | b'\r' | b'\t')) {
            self.pos += 1;
        }
    }

    fn expect(&mut self, ch: u8) -> Result<(), Error> {
        if self.next() == Some(ch) {
            Ok(())
        } else {
            Err(Error::new(ErrorKind::InvalidData, "unexpected JSON token"))
        }
    }

    fn expect_bytes(&mut self, expected: &[u8]) -> Result<(), Error> {
        for &b in expected {
            if self.next() != Some(b) {
                return Err(Error::new(ErrorKind::InvalidData, "invalid JSON literal"));
            }
        }
        Ok(())
    }

    fn peek(&self) -> Option<u8> {
        self.src.get(self.pos).copied()
    }

    fn next(&mut self) -> Option<u8> {
        let b = self.peek()?;
        self.pos += 1;
        Some(b)
    }
}

fn json_escape(s: &str) -> String {
    let mut out = String::with_capacity(s.len() + 2);
    for ch in s.chars() {
        match ch {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            c if c < ' ' => out.push(' '),
            c => out.push(c),
        }
    }
    out
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
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

    pub fn from_str(s: &str) -> Option<Self> {
        match s {
            "GPIO" => Some(Protocol::GPIO),
            "Serial" => Some(Protocol::Serial),
            "USB" => Some(Protocol::USB),
            "I2C" => Some(Protocol::I2C),
            "SPI" => Some(Protocol::SPI),
            "CAN" => Some(Protocol::CAN),
            "JTAG" => Some(Protocol::JTAG),
            "Bluetooth" => Some(Protocol::Bluetooth),
            "Network" => Some(Protocol::Network),
            _ => None,
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SafetyLevel {
    Safe,
    Unsafe,
    Critical,
}

impl SafetyLevel {
    pub fn as_str(&self) -> &'static str {
        match self {
            SafetyLevel::Safe => "Safe",
            SafetyLevel::Unsafe => "Unsafe",
            SafetyLevel::Critical => "Critical",
        }
    }

    pub fn from_str(s: &str) -> Option<Self> {
        match s {
            "Safe" => Some(SafetyLevel::Safe),
            "Unsafe" => Some(SafetyLevel::Unsafe),
            "Critical" => Some(SafetyLevel::Critical),
            _ => None,
        }
    }
}

#[derive(Debug, Clone)]
pub struct HalTraitMethod {
    pub name: String,
    pub signature: String,
}

#[derive(Debug, Clone)]
pub struct HalTraitDefinition {
    pub name: String,
    pub methods: Vec<HalTraitMethod>,
    pub safety_level: SafetyLevel,
}

#[derive(Debug, Clone)]
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
    pub fn from_json(s: &str) -> Result<Self, Error> {
        let value = JsonParser::new(s).parse()?;

        let obj = match value {
            JsonValue::Object(obj) => obj,
            _ => return Err(Error::new(ErrorKind::InvalidData, "manifest must be a JSON object")),
        };

        let get_string = |key: &str| -> Result<String, Error> {
            match obj.get(key) {
                Some(JsonValue::String(s)) => Ok(s.clone()),
                _ => Err(Error::new(
                    ErrorKind::InvalidData,
                    format!("missing or invalid string field: {key}"),
                )),
            }
        };

        let protocols = match obj.get("protocols") {
            Some(JsonValue::Array(arr)) => arr
                .iter()
                .map(|v| match v {
                    JsonValue::String(s) => Protocol::from_str(s).ok_or_else(|| {
                        Error::new(ErrorKind::InvalidData, "invalid protocol value")
                    }),
                    _ => Err(Error::new(ErrorKind::InvalidData, "invalid protocol value")),
                })
                .collect::<Result<Vec<_>, _>>()?,
            _ => {
                return Err(Error::new(
                    ErrorKind::InvalidData,
                    "missing or invalid array field: protocols",
                ));
            }
        };

        let hal_traits = match obj.get("hal_traits") {
            Some(JsonValue::Array(arr)) => arr
                .iter()
                .map(|t| {
                    let t_obj = match t {
                        JsonValue::Object(o) => o,
                        _ => {
                            return Err(Error::new(
                                ErrorKind::InvalidData,
                                "invalid hal_traits entry",
                            ));
                        }
                    };

                    let name = match t_obj.get("name") {
                        Some(JsonValue::String(s)) => s.clone(),
                        _ => {
                            return Err(Error::new(
                                ErrorKind::InvalidData,
                                "missing or invalid hal_traits.name",
                            ));
                        }
                    };

                    let safety_level = match t_obj.get("safety_level") {
                        Some(JsonValue::String(s)) => SafetyLevel::from_str(s).ok_or_else(|| {
                            Error::new(
                                ErrorKind::InvalidData,
                                "missing or invalid hal_traits.safety_level",
                            )
                        })?,
                        _ => {
                            return Err(Error::new(
                                ErrorKind::InvalidData,
                                "missing or invalid hal_traits.safety_level",
                            ));
                        }
                    };

                    let methods = match t_obj.get("methods") {
                        Some(JsonValue::Array(methods)) => methods
                            .iter()
                            .map(|m| {
                                let m_obj = match m {
                                    JsonValue::Object(o) => o,
                                    _ => {
                                        return Err(Error::new(
                                            ErrorKind::InvalidData,
                                            "invalid method entry",
                                        ));
                                    }
                                };

                                let method_name = match m_obj.get("name") {
                                    Some(JsonValue::String(s)) => s.clone(),
                                    _ => {
                                        return Err(Error::new(
                                            ErrorKind::InvalidData,
                                            "missing or invalid method.name",
                                        ));
                                    }
                                };

                                let signature = match m_obj.get("signature") {
                                    Some(JsonValue::String(s)) => s.clone(),
                                    _ => {
                                        return Err(Error::new(
                                            ErrorKind::InvalidData,
                                            "missing or invalid method.signature",
                                        ));
                                    }
                                };

                                Ok(HalTraitMethod {
                                    name: method_name,
                                    signature,
                                })
                            })
                            .collect::<Result<Vec<_>, Error>>()?,
                        _ => {
                            return Err(Error::new(
                                ErrorKind::InvalidData,
                                "missing or invalid hal_traits.methods",
                            ));
                        }
                    };

                    Ok(HalTraitDefinition {
                        name,
                        methods,
                        safety_level,
                    })
                })
                .collect::<Result<Vec<_>, Error>>()?,
            _ => {
                return Err(Error::new(
                    ErrorKind::InvalidData,
                    "missing or invalid array field: hal_traits",
                ));
            }
        };

        Ok(Self {
            id: get_string("id")?,
            name: get_string("name")?,
            version: get_string("version")?,
            description: get_string("description")?,
            author: get_string("author")?,
            protocols,
            hal_traits,
            entrypoint: get_string("entrypoint")?,
        })
    }

    pub fn to_json(&self) -> Result<String, Error> {
        let protocols = self
            .protocols
            .iter()
            .map(|p| format!("\"{}\"", json_escape(p.as_str())))
            .collect::<Vec<_>>()
            .join(", ");

        let hal_traits = self
            .hal_traits
            .iter()
            .map(|t| {
                let methods = t
                    .methods
                    .iter()
                    .map(|m| {
                        format!(
                            "{{\"name\": \"{}\", \"signature\": \"{}\"}}",
                            json_escape(&m.name),
                            json_escape(&m.signature)
                        )
                    })
                    .collect::<Vec<_>>()
                    .join(", ");

                format!(
                    "{{\"name\": \"{}\", \"methods\": [{}], \"safety_level\": \"{}\"}}",
                    json_escape(&t.name),
                    methods,
                    json_escape(t.safety_level.as_str())
                )
            })
            .collect::<Vec<_>>()
            .join(", ");

        Ok(format!(
            "{{\n  \"id\": \"{}\",\n  \"name\": \"{}\",\n  \"version\": \"{}\",\n  \"description\": \"{}\",\n  \"author\": \"{}\",\n  \"protocols\": [{}],\n  \"hal_traits\": [{}],\n  \"entrypoint\": \"{}\"\n}}",
            json_escape(&self.id),
            json_escape(&self.name),
            json_escape(&self.version),
            json_escape(&self.description),
            json_escape(&self.author),
            protocols,
            hal_traits,
            json_escape(&self.entrypoint)
        ))
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
