//! Prometheus Kernel — Phase 1.1 OS layer.
//!
//! Owns the parts of the desktop OS that Rust/Tauri must own: PTY-backed
//! terminals, workspace session persistence (SQLite), and an in-process event
//! bus that the Tauri layer fans out to webview listeners.
//!
//! Deliberately depends only on `portable-pty`, `rusqlite`, `serde`, `tokio`,
//! `uuid`. It must NOT depend on `aether-runtime` (circular dep avoidance);
//! `src-tauri` owns both as peers.

pub mod error;
pub mod event_bus;
pub mod hardware;
pub mod session;
pub mod terminal;
pub mod kernel;

pub use error::KernelError;
pub use event_bus::{EventBus, KernelEvent};
pub use hardware::HardwareManager;
pub use kernel::{Kernel, KernelStatus};
pub use session::{Session, SessionManager, WindowState};
pub use terminal::{TerminalHandle, TerminalInfo, TerminalManager};
