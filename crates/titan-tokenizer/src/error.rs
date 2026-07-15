//! Tokenizer error types.

use thiserror::Error;

#[derive(Debug, Error, Clone)]
pub enum TokenizerError {
    #[error("empty input")]
    EmptyInput,
    #[error("invalid token id: {0}")]
    InvalidTokenId(TokenId),
    #[error("unknown special token: {0}")]
    UnknownSpecialToken(String),
}

pub type TokenId = u32;
pub type TokenizerResult<T> = Result<T, TokenizerError>;
