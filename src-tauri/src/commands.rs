//! Tauri command surface backed by the Prometheus kernel.
//!
//! The `Kernel` owns the PTY terminal manager, the SQLite session manager,
//! and the in-process event bus. The bus is bridged once at startup into
//! Tauri webview events (`terminal-output`, `terminal-exited`, `session-*`)
//! so the frontend receives kernel events without bespoke plumbing.

use std::sync::Mutex;
use std::path::PathBuf;

use prometheus_kernel::{
    Kernel, KernelStatus, Session, WindowState,
};
use tauri::{AppHandle, Manager, State};

/// Tauri-managed kernel state. Constructed in `setup` once the app path is
/// known, then shared with every command via `State`.
pub struct KernelState(Mutex<Kernel>);

impl KernelState {
    pub fn new(session_db: PathBuf) -> KernelResult<Self> {
        Ok(KernelState(Mutex::new(Kernel::new(&session_db)?)))
    }
}

type KernelResult<T> = Result<T, String>;

/// Spawn a PTY-backed terminal session for `shell` with the given size.
/// Returns the session id. Output is streamed to the webview via the
/// `terminal-output` event (tagged with the session id).
#[tauri::command]
pub fn terminal_spawn(shell: String, cols: u16, rows: u16, state: State<KernelState>) -> KernelResult<String> {
    state
        .0
        .lock()
        .unwrap()
        .terminal_spawn(&shell, cols, rows)
        .map_err(|e| e.to_string())
}

/// Write raw bytes (base64-decoded) to a terminal session's PTY stdin.
#[tauri::command]
pub fn terminal_write(session_id: String, data: String, state: State<KernelState>) -> KernelResult<()> {
    let bytes = base64_decode(&data).map_err(|e| e.to_string())?;
    state
        .0
        .lock()
        .unwrap()
        .terminal_write(&session_id, &bytes)
        .map_err(|e| e.to_string())
}

/// Resize a terminal session's PTY (pane resize / SIGWINCH equivalent).
#[tauri::command]
pub fn terminal_resize(session_id: String, cols: u16, rows: u16, state: State<KernelState>) -> KernelResult<()> {
    state
        .0
        .lock()
        .unwrap()
        .terminal_resize(&session_id, cols, rows)
        .map_err(|e| e.to_string())
}

/// Kill a terminal session's PTY process and drop the session.
#[tauri::command]
pub fn terminal_kill(session_id: String, state: State<KernelState>) -> KernelResult<()> {
    state
        .0
        .lock()
        .unwrap()
        .terminal_kill(&session_id)
        .map_err(|e| e.to_string())
}

/// Persist a command into a session's history (up/down arrow replay).
#[tauri::command]
pub fn terminal_record_command(session_id: String, line: String, state: State<KernelState>) -> KernelResult<()> {
    state
        .0
        .lock()
        .unwrap()
        .terminals
        .record_command(&session_id, &line)
        .map_err(|e| e.to_string())
}

/// Recall history relative to `back` (0 = most recent).
#[tauri::command]
pub fn terminal_history(session_id: String, back: usize, state: State<KernelState>) -> KernelResult<Option<String>> {
    state
        .0
        .lock()
        .unwrap()
        .terminals
        .history(&session_id, back)
        .map_err(|e| e.to_string())
}

/// Aggregate kernel health for `kernel_status()`.
#[tauri::command]
pub fn kernel_status(state: State<KernelState>) -> KernelStatus {
    state.0.lock().unwrap().status()
}

/// Persist a full workspace session.
#[tauri::command]
pub fn session_save(session: Session, state: State<KernelState>) -> KernelResult<()> {
    state
        .0
        .lock()
        .unwrap()
        .session_save(&session)
        .map_err(|e| e.to_string())
}

/// Persist a single window within a session (live editing).
#[tauri::command]
pub fn session_save_window(session_id: String, window: WindowState, state: State<KernelState>) -> KernelResult<()> {
    state
        .0
        .lock()
        .unwrap()
        .session_save_window(&session_id, &window)
        .map_err(|e| e.to_string())
}

/// Restore a saved session by id. Returns `None` if absent.
#[tauri::command]
pub fn session_restore(id: String, state: State<KernelState>) -> KernelResult<Option<Session>> {
    state
        .0
        .lock()
        .unwrap()
        .session_restore(&id)
        .map_err(|e| e.to_string())
}

/// Bridge the kernel event bus into Tauri webview events. Call once during
/// `setup`. Every kernel event becomes a Tauri event named after its topic;
/// the frontend listens via `listen(topic, handler)`.
pub fn bridge_kernel_events(app: &AppHandle, state: &KernelState) {
    let app = app.clone();
    state.0.lock().unwrap().bus.subscribe(move |event| {
        let _ = app.emit(&event.topic, event.clone());
    });
}

/// Minimal, dependency-free base64 decoder for terminal write payloads.
fn base64_decode(input: &str) -> Result<Vec<u8>, Box<dyn std::error::Error>> {
    const DECODE: &[i16; 256] = &{
        let mut table = [-1i16; 256];
        let mut i = 0;
        while i < 64 {
            let c = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
                .as_bytes()[i];
            table[c as usize] = i as i16;
            i += 1;
        }
        table
    };
    let bytes = input.as_bytes();
    let mut out = Vec::with_capacity(bytes.len() / 4 * 3);
    let mut i = 0;
    while i < bytes.len() {
        // Pull four 6-bit groups, skipping whitespace and honouring padding.
        let mut groups = [0u8; 4];
        let mut pad = 0u8;
        for slot in 0..4 {
            // Skip whitespace.
            while i < bytes.len() && (bytes[i] == b' ' || bytes[i] == b'\n' || bytes[i] == b'\r') {
                i += 1;
            }
            if i >= bytes.len() || bytes[i] == b'=' {
                if i < bytes.len() && bytes[i] == b'=' {
                    i += 1;
                }
                pad += 1;
                continue;
            }
            let v = DECODE[bytes[i] as usize];
            if v < 0 {
                return Err(format!("invalid base64 at {i}").into());
            }
            groups[slot] = v as u8;
            i += 1;
        }
        if pad == 4 {
            break;
        }
        out.push((groups[0] << 2) | (groups[1] >> 4));
        if pad < 2 {
            out.push((groups[1] << 4) | (groups[2] >> 2));
        }
        if pad < 1 {
            out.push((groups[2] << 6) | groups[3]);
        }
        if pad > 0 {
            break;
        }
    }
    Ok(out)
}
