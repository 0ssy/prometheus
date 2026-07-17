use crate::error::KernelResult;
use crate::event_bus::{EventBus, KernelEvent};
use crate::hardware::HardwareManager;
use crate::session::{Session, SessionManager, WindowState};
use crate::terminal::{TerminalInfo, TerminalManager};

pub struct Kernel {
    pub terminals: TerminalManager,
    pub sessions: SessionManager,
    pub bus: EventBus,
    pub hardware: HardwareManager,
}

impl Kernel {
    /// Build a kernel with a session DB at `session_db_path`.
    pub fn new(session_db_path: &std::path::Path) -> KernelResult<Self> {
        let bus = EventBus::new();
        let terminals = TerminalManager::new(bus.clone());
        let sessions = SessionManager::open(session_db_path)?;
        let hardware = HardwareManager::new(bus.clone());
        Ok(Self {
            terminals,
            sessions,
            bus,
            hardware,
        })
    }

    /// Health probe for `kernel_status()`.
    pub fn status(&self) -> KernelStatus {
        let _hw = self.hardware.status();
        KernelStatus {
            healthy: true,
            terminals: self.terminals.list().len(),
            session_db: "ok".to_string(),
        }
    }

    // --- Terminal passthrough -------------------------------------------------

    pub fn terminal_spawn(&self, shell: &str, cols: u16, rows: u16) -> KernelResult<String> {
        self.terminals.spawn(shell, cols, rows)
    }

    pub fn terminal_write(&self, session_id: &str, data: &[u8]) -> KernelResult<()> {
        self.terminals.write(session_id, data)
    }

    pub fn terminal_resize(&self, session_id: &str, cols: u16, rows: u16) -> KernelResult<()> {
        self.terminals.resize(session_id, cols, rows)
    }

    pub fn terminal_kill(&self, session_id: &str) -> KernelResult<()> {
        self.terminals.kill(session_id)
    }

    pub fn terminal_list(&self) -> Vec<TerminalInfo> {
        self.terminals.list()
    }

    // --- Session passthrough --------------------------------------------------

    pub fn session_save(&self, session: &Session) -> KernelResult<()> {
        self.sessions.save(session)
    }

    pub fn session_restore(&self, id: &str) -> KernelResult<Option<Session>> {
        self.sessions.load(id)
    }

    pub fn session_save_window(&self, session_id: &str, window: &WindowState) -> KernelResult<()> {
        self.sessions.save_window(session_id, window)
    }

    /// Persist a snapshot of live window state so the desktop restores on boot.
    pub fn session_snapshot(
        &self,
        id: &str,
        windows: Vec<WindowState>,
        terminals: Vec<String>,
    ) -> KernelResult<Session> {
        self.sessions.snapshot_and_save(id, windows, terminals)
    }

    // --- Hardware passthrough -------------------------------------------------

    pub fn hardware_probe(&self, transport: hal_core::Transport, target: &str) -> hal_core::ProbeResult {
        self.hardware.probe(transport, target)
    }

    // --- Event bus passthrough ------------------------------------------------

    pub fn emit(&self, event: KernelEvent) {
        self.bus.publish(event);
    }
}

#[derive(Debug, Clone, serde::Serialize)]
pub struct KernelStatus {
    pub healthy: bool,
    pub terminals: usize,
    pub session_db: String,
}
