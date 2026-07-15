//! Decoder — reconstruct text from token ids.

use crate::{error::TokenizerError, types::TokenizerConfig, TokenId};

#[derive(Debug, Clone)]
pub struct Decoder {
    config: TokenizerConfig,
}

impl Default for Decoder {
    fn default() -> Self {
        Self::new(TokenizerConfig::default())
    }
}

impl Decoder {
    pub fn new(config: TokenizerConfig) -> Self {
        Self { config }
    }

    pub fn decode(&self, ids: &[TokenId]) -> Result<String, TokenizerError> {
        if ids.is_empty() {
            return Err(TokenizerError::EmptyInput);
        }
        let mut out = String::new();
        for &id in ids {
            if id == self.config.bos_token || id == self.config.eos_token {
                continue;
            }
            if id == self.config.pad_token || id == self.config.unk_token {
                continue;
            }
            let ch = char::from_u32(id % 0x110000).unwrap_or('\u{FFFD}');
            out.push(ch);
        }
        Ok(out)
    }
}

pub fn decode(ids: &[TokenId]) -> Result<String, TokenizerError> {
    Decoder::default().decode(ids)
}
