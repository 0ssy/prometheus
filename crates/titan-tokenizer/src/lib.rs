//! Titan Tokenizer — Phase 5.2
//!
//! Provides encode/decode and special-token management for the Titan
//! fine-tuning pipelines. Pure Rust implementation with optional
//! `pyo3` bindings exposed as `titan_tokenizer` on the Python side.

pub mod decoder;
pub mod encoder;
pub mod error;
pub mod special_tokens;
pub mod types;

#[cfg(feature = "python")]
pub mod bindings;

pub use decoder::decode;
pub use encoder::encode;
pub use error::{TokenId, TokenizerError};
pub use special_tokens::{add_special_tokens, list_special_tokens, SpecialTokenSet};
pub use types::TokenizerConfig;

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn encode_wraps_with_special_tokens() {
        let ids = encode("ab");
        assert_eq!(ids.first(), Some(&TokenizerConfig::default().bos_token));
        assert_eq!(ids.last(), Some(&TokenizerConfig::default().eos_token));
    }

    #[test]
    fn round_trip_preserves_characters() {
        let text = "hi";
        let ids = encode(text);
        let decoded = decode(&ids).expect("decode succeeds");
        assert_eq!(decoded, text);
    }

    #[test]
    fn special_token_set_defaults() {
        let set = list_special_tokens();
        assert_eq!(set.id("<BOS>"), Some(2));
        assert_eq!(set.token(0), Some("<PAD>"));
    }

    #[test]
    fn add_special_tokens_returns_ids() {
        let mut set = list_special_tokens();
        let ids = add_special_tokens(&mut set, &["<CUSTOM>", "<BOS>"]);
        assert!(ids.contains(&set.id("<CUSTOM>").unwrap()));
    }
}
