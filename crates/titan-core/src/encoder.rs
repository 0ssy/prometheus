//! Encoder — tokenize text into token ids.

use crate::{types::TokenizerConfig, TokenId};

#[derive(Debug, Clone)]
pub struct Encoder {
    config: TokenizerConfig,
    vocab: Vec<String>,
}

impl Default for Encoder {
    fn default() -> Self {
        Self::new(TokenizerConfig::default())
    }
}

impl Encoder {
    pub fn new(config: TokenizerConfig) -> Self {
        let vocab = vec![
            String::from("<PAD>"),
            String::from("<UNK>"),
            String::from("<BOS>"),
            String::from("<EOS>"),
            String::from("<MASK>"),
        ];
        let mut enc = Self { config, vocab };
        for i in 5..enc.config.vocab_size {
            enc.vocab.push(format!("<tok_{i}>"));
        }
        enc
    }

    pub fn encode(&self, text: &str) -> Vec<TokenId> {
        let mut ids = vec![self.config.bos_token];
        for ch in text.chars() {
            let id = self.char_id(ch);
            ids.push(id);
        }
        ids.push(self.config.eos_token);
        ids
    }

    pub fn vocab_size(&self) -> usize {
        self.config.vocab_size
    }

    fn char_id(&self, ch: char) -> TokenId {
        let byte = ch as u32;
        if byte < self.config.vocab_size as u32 {
            byte
        } else {
            self.config.unk_token
        }
    }
}

pub fn encode(text: &str) -> Vec<TokenId> {
    Encoder::default().encode(text)
}
