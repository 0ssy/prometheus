use std::collections::HashMap;
use std::sync::{Arc, Mutex};
use std::time::Duration;

use portable_pty::{native_pty_system, Child, CommandBuilder, PtySize};
use uuid::Uuid;

use crate::error::{KernelError, KernelResult};
use crate::event_bus::{EventBus, KernelEvent};

/// Snapshot of a terminal session for API/UI consumption.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct TerminalInfo {
    pub id: String,
    pub shell: String,
    pub cols: u16,
    pub rows: u16,
    pub alive: bool,
}

/// A live terminal: a PTY child process plus a reader task that pumps output
/// into the event bus.
pub struct TerminalHandle {
    pub id: String,
    pub shell: String,
    pub size: Mutex<PtySize>,
    pub alive: Mutex<bool>,
    child: Mutex<Box<dyn Child + Send + Sync>>,
    writer: Mutex<Box<dyn std::io::Write + Send>>,
    history: Mutex<Vec<String>>,
}

impl TerminalHandle {
    /// Write bytes to the PTY stdin.
    pub fn write(&self, data: &[u8]) -> KernelResult<()> {
        use std::io::Write;
        let mut w = self.writer.lock().unwrap();
        w.write_all(data)?;
        w.flush()?;
        Ok(())
    }

    /// Push a command into history (for up/down arrow replay).
    pub fn push_history(&self, line: &str) {
        if line.trim().is_empty() {
            return;
        }
        let mut h = self.history.lock().unwrap();
        if h.last().map(|s| s.as_str()) != Some(line) {
            h.push(line.to_string());
        }
    }

    /// Nth-most-recent history entry (0 = latest).
    pub fn history_back(&self, n: usize) -> Option<String> {
        let h = self.history.lock().unwrap();
        h.len()
            .checked_sub(1)
            .and_then(|last| last.checked_sub(n))
            .and_then(|i| h.get(i).cloned())
    }

    pub fn info(&self) -> TerminalInfo {
        let size = *self.size.lock().unwrap();
        TerminalInfo {
            id: self.id.clone(),
            shell: self.shell.clone(),
            cols: size.cols,
            rows: size.rows,
            alive: *self.alive.lock().unwrap(),
        }
    }

    fn mark_dead(&self) {
        *self.alive.lock().unwrap() = false;
    }
}

/// Spawns and tracks PTY-backed terminal sessions.
pub struct TerminalManager {
    terminals: Mutex<HashMap<String, Arc<TerminalHandle>>>,
    bus: EventBus,
}

impl TerminalManager {
    pub fn new(bus: EventBus) -> Self {
        Self {
            terminals: Mutex::new(HashMap::new()),
            bus,
        }
    }

    /// Resolve the real shell command for a logical shell name, applying the
    /// platform preference order from the plan (PowerShell 7 > PowerShell >
    /// CMD on Windows; zsh > bash > sh elsewhere).
    fn resolve_command(shell: &str) -> CommandBuilder {
        let lower = shell.to_lowercase();
        let name = match lower.as_str() {
            "pwsh" | "powershell7" => "pwsh",
            "powershell" | "ps" => "powershell",
            "cmd" => "cmd",
            "bash" => "bash",
            "zsh" => "zsh",
            "sh" => "sh",
            _ => {
                if cfg!(windows) {
                    "pwsh"
                } else {
                    "bash"
                }
            }
        };
        CommandBuilder::new(name)
    }

    /// Spawn a PTY for `shell`. Output is streamed via the event bus under the
    /// `terminal-output` topic, tagged with the session id.
    pub fn spawn(&self, shell: &str, cols: u16, rows: u16) -> KernelResult<String> {
        let id = Uuid::new_v4().to_string();
        let pair = native_pty_system()
            .openpty(PtySize {
                rows,
                cols,
                pixel_width: 0,
                pixel_height: 0,
            })
            .map_err(|e| KernelError::Pty(e.to_string()))?;

        let cmd = Self::resolve_command(shell);
        let child = pair
            .slave
            .spawn_command(cmd)
            .map_err(|e| KernelError::Pty(e.to_string()))?;
        // Drop the slave so EOF is observed when the child exits.
        drop(pair.slave);

        let mut reader = pair
            .master
            .try_clone_reader()
            .map_err(|e| KernelError::Pty(e.to_string()))?;
        let writer = pair
            .master
            .take_writer()
            .map_err(|e| KernelError::Pty(e.to_string()))?;

        let handle = Arc::new(TerminalHandle {
            id: id.clone(),
            shell: shell.to_string(),
            size: Mutex::new(PtySize {
                rows,
                cols,
                pixel_width: 0,
                pixel_height: 0,
            }),
            alive: Mutex::new(true),
            child: Mutex::new(child),
            writer: Mutex::new(writer),
            history: Mutex::new(Vec::new()),
        });

        // Pump PTY output to the event bus on a background thread.
        let bus = self.bus.clone();
        let out_id = id.clone();
        let out_handle = Arc::clone(&handle);
        std::thread::spawn(move || {
            use std::io::Read;
            let mut buf = [0u8; 4096];
            loop {
                match reader.read(&mut buf) {
                    Ok(0) => break,
                    Ok(n) => {
                        let chunk = &buf[..n];
                        bus.publish(KernelEvent {
                            topic: "terminal-output".to_string(),
                            target: Some(out_id.clone()),
                            payload: Some(serde_json::json!({ "data": base64_encode(chunk) })),
                        });
                    }
                    Err(_) => break,
                }
            }
            out_handle.mark_dead();
            bus.publish(KernelEvent {
                topic: "terminal-exited".to_string(),
                target: Some(out_id.clone()),
                payload: None,
            });
        });

        self.terminals.lock().unwrap().insert(id.clone(), handle);
        Ok(id)
    }

    pub fn write(&self, session_id: &str, data: &[u8]) -> KernelResult<()> {
        let terminals = self.terminals.lock().unwrap();
        let handle = terminals
            .get(session_id)
            .ok_or_else(|| KernelError::TerminalNotFound(session_id.to_string()))?;
        handle.write(data)
    }

    /// Resize the PTY (called on pane resize / SIGWINCH equivalent).
    pub fn resize(&self, session_id: &str, cols: u16, rows: u16) -> KernelResult<()> {
        let terminals = self.terminals.lock().unwrap();
        let handle = terminals
            .get(session_id)
            .ok_or_else(|| KernelError::TerminalNotFound(session_id.to_string()))?;
        *handle.size.lock().unwrap() = PtySize {
            rows,
            cols,
            pixel_width: 0,
            pixel_height: 0,
        };
        Ok(())
    }

    /// Record a command in a session's history.
    pub fn record_command(&self, session_id: &str, line: &str) -> KernelResult<()> {
        let terminals = self.terminals.lock().unwrap();
        let handle = terminals
            .get(session_id)
            .ok_or_else(|| KernelError::TerminalNotFound(session_id.to_string()))?;
        handle.push_history(line);
        Ok(())
    }

    /// Recall history relative to `back` (0 = most recent).
    pub fn history(&self, session_id: &str, back: usize) -> KernelResult<Option<String>> {
        let terminals = self.terminals.lock().unwrap();
        let handle = terminals
            .get(session_id)
            .ok_or_else(|| KernelError::TerminalNotFound(session_id.to_string()))?;
        Ok(handle.history_back(back))
    }

    /// Kill the PTY process and drop the session.
    pub fn kill(&self, session_id: &str) -> KernelResult<()> {
        let handle = {
            let mut terminals = self.terminals.lock().unwrap();
            terminals
                .remove(session_id)
                .ok_or_else(|| KernelError::TerminalNotFound(session_id.to_string()))?
        };
        let _ = handle.child.lock().unwrap().kill();
        // Give the reader thread a moment to observe EOF.
        std::thread::sleep(Duration::from_millis(20));
        Ok(())
    }

    pub fn list(&self) -> Vec<TerminalInfo> {
        self.terminals
            .lock()
            .unwrap()
            .values()
            .map(|h| h.info())
            .collect()
    }

    pub fn get(&self, session_id: &str) -> KernelResult<TerminalInfo> {
        let terminals = self.terminals.lock().unwrap();
        let handle = terminals
            .get(session_id)
            .ok_or_else(|| KernelError::TerminalNotFound(session_id.to_string()))?;
        Ok(handle.info())
    }
}

fn base64_encode(bytes: &[u8]) -> String {
    let mut enc = Base64Encoder::new();
    enc.write_all(bytes).ok();
    enc.finish()
}

/// Inline base64 encoder to avoid an extra dependency.
struct Base64Encoder {
    buf: Vec<u8>,
}

impl Base64Encoder {
    fn new() -> Self {
        Self { buf: Vec::new() }
    }

    fn push6(&mut self, b: u8) {
        const CHARS: &[u8; 64] = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
        self.buf.push(CHARS[(b & 0x3f) as usize]);
    }

    fn write_all(&mut self, mut data: &[u8]) -> std::io::Result<()> {
        while data.len() >= 3 {
            let n = u32::from_be_bytes([0, data[0], data[1], data[2]]);
            self.push6((n >> 18) as u8);
            self.push6((n >> 12) as u8);
            self.push6((n >> 6) as u8);
            self.push6(n as u8);
            data = &data[3..];
        }
        if data.len() == 1 {
            let n = u32::from_be_bytes([0, data[0], 0, 0]);
            self.push6((n >> 18) as u8);
            self.push6((n >> 12) as u8);
            self.buf.push(b'=');
            self.buf.push(b'=');
        } else if data.len() == 2 {
            let n = u32::from_be_bytes([0, data[0], data[1], 0]);
            self.push6((n >> 18) as u8);
            self.push6((n >> 12) as u8);
            self.push6((n >> 6) as u8);
            self.buf.push(b'=');
        }
        Ok(())
    }

    fn finish(self) -> String {
        String::from_utf8(self.buf).unwrap_or_default()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::event_bus::EventBus;

    /// These tests spawn a real PTY process. On Windows that exercises ConPTY
    /// (Windows 10+). Gate them behind `--features pty-test` so they don't run
    /// in constrained CI by default, but are available for the Phase 1.2
    /// ConPTY validation step.
    #[cfg(feature = "pty-test")]
    mod pty {
        use super::*;

        fn manager() -> TerminalManager {
            TerminalManager::new(EventBus::new())
        }

        #[test]
        fn spawn_kill_removes_session() {
            let m = manager();
            let id = m.spawn(if cfg!(windows) { "cmd" } else { "sh" }, 80, 24).unwrap();
            m.kill(&id).unwrap();
            assert!(m.get(&id).is_err());
        }

        #[test]
        fn resize_is_applied() {
            let m = manager();
            let id = m.spawn(if cfg!(windows) { "cmd" } else { "sh" }, 80, 24).unwrap();
            m.resize(&id, 120, 40).unwrap();
            assert_eq!(m.get(&id).unwrap().cols, 120);
            assert_eq!(m.get(&id).unwrap().rows, 40);
            m.kill(&id).unwrap();
        }

        #[test]
        fn unknown_session_errors() {
            let m = manager();
            assert!(m.write("nope", b"x").is_err());
            assert!(m.kill("nope").is_err());
        }
    }
}
