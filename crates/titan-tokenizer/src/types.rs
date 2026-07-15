//! Tokenizer types and configuration.

use crate::error::TokenId;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TokenizerConfig {
    pub vocab_size: usize,
    pub pad_token: TokenId,
    pub unk_token: TokenId,
    pub bos_token: TokenId,
    pub eos_token: TokenId,
    pub mask_token: TokenId,
}

impl Default for TokenizerConfig {
    fn default() -> Self {
        Self {
            vocab_size: 1024,
            pad_token: 0,
            unk_token: 1,
            bos_token: 2,
            eos_token: 3,
            mask_token: 4,
        }
    }
}
