use thiserror::Error;

/// Errors surfaced by the kernel and its managers.
#[derive(Debug, Error)]
pub enum KernelError {
    #[error("pty error: {0}")]
    Pty(String),

    #[error("session not found: {0}")]
    SessionNotFound(String),

    #[error("terminal not found: {0}")]
    TerminalNotFound(String),

    #[error("io error: {0}")]
    Io(#[from] std::io::Error),

    #[error("sqlite error: {0}")]
    Sqlite(#[from] rusqlite::Error),

    #[error("serialization error: {0}")]
    Json(#[from] serde_json::Error),

    #[error("invalid state: {0}")]
    InvalidState(String),
}

pub type KernelResult<T> = Result<T, KernelError>;
