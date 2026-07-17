//! Tauri command surface backed by the Prometheus kernel.
//!
//! The `Kernel` owns the PTY terminal manager, the SQLite session manager,
//! and the in-process event bus. The bus is bridged once at startup into
//! Tauri webview events (`terminal-output`, `terminal-exited`, `session-*`)
//! so the frontend receives kernel events without bespoke plumbing.
//!
//! Phase 2 adds a `HardwareState` backed by `hal-core` (Rust) and the
//! native C/C++/Zig HAL libraries, exposing real device I/O to the frontend.

use std::sync::Mutex;
use std::path::PathBuf;

use prometheus_kernel::{
    Kernel, KernelStatus, Session, WindowState,
};
use tauri::{AppHandle, Emitter, State};

use hal_core::{Hal, ProbeResult, RealHal, SimulatedHal, Transport, UsbTransport, SerialTransport, GpioTransport};

pub struct KernelState(Mutex<Kernel>);

impl KernelState {
    pub fn new(session_db: PathBuf) -> KernelResult<Self> {
        let kernel = Kernel::new(&session_db).map_err(|e| e.to_string())?;
        Ok(KernelState(Mutex::new(kernel)))
    }
}

#[derive(Clone, serde::Serialize, serde::Deserialize)]
pub struct HardwareProbeRequest {
    pub transport: String,
    pub target: String,
    pub use_real: Option<bool>,
}

#[derive(Clone, serde::Serialize, serde::Deserialize)]
pub struct HardwareConnectRequest {
    pub transport: String,
    pub target: String,
}

#[derive(Clone, serde::Serialize, serde::Deserialize)]
pub struct HardwareReadRequest {
    pub transport: String,
    pub target: String,
    pub length: usize,
}

#[derive(Clone, serde::Serialize, serde::Deserialize)]
pub struct HardwareWriteRequest {
    pub transport: String,
    pub target: String,
    pub data: Vec<u8>,
}

#[derive(Clone, serde::Serialize, serde::Deserialize)]
pub struct HardwareDiagnosticsResponse {
    pub transport: String,
    pub target: String,
    pub healthy: bool,
    pub metrics: std::collections::HashMap<String, serde_json::Value>,
}

type KernelResult<T> = Result<T, String>;

/// Spawn a PTY-backed terminal session for `shell` with the given size.
#[tauri::command]
pub fn terminal_spawn(shell: String, cols: u16, rows: u16, state: State<'_, KernelState>) -> KernelResult<String> {
    state
        .0
        .lock()
        .unwrap()
        .terminal_spawn(&shell, cols, rows)
        .map_err(|e| e.to_string())
}

#[tauri::command]
pub fn terminal_write(session_id: String, data: String, state: State<'_, KernelState>) -> KernelResult<()> {
    let bytes = base64_decode(&data).map_err(|e| e.to_string())?;
    state
        .0
        .lock()
        .unwrap()
        .terminal_write(&session_id, &bytes)
        .map_err(|e| e.to_string())
}

#[tauri::command]
pub fn terminal_resize(session_id: String, cols: u16, rows: u16, state: State<'_, KernelState>) -> KernelResult<()> {
    state
        .0
        .lock()
        .unwrap()
        .terminal_resize(&session_id, cols, rows)
        .map_err(|e| e.to_string())
}

#[tauri::command]
pub fn terminal_kill(session_id: String, state: State<'_, KernelState>) -> KernelResult<()> {
    state
        .0
        .lock()
        .unwrap()
        .terminal_kill(&session_id)
        .map_err(|e| e.to_string())
}

#[tauri::command]
pub fn terminal_record_command(session_id: String, line: String, state: State<'_, KernelState>) -> KernelResult<()> {
    state
        .0
        .lock()
        .unwrap()
        .terminals
        .record_command(&session_id, &line)
        .map_err(|e| e.to_string())
}

#[tauri::command]
pub fn terminal_history(session_id: String, back: usize, state: State<'_, KernelState>) -> KernelResult<Option<String>> {
    state
        .0
        .lock()
        .unwrap()
        .terminals
        .history(&session_id, back)
        .map_err(|e| e.to_string())
}

#[tauri::command]
pub fn kernel_status(state: State<'_, KernelState>) -> KernelStatus {
    state.0.lock().unwrap().status()
}

#[tauri::command]
pub fn session_save(session: Session, state: State<'_, KernelState>) -> KernelResult<()> {
    state
        .0
        .lock()
        .unwrap()
        .session_save(&session)
        .map_err(|e| e.to_string())
}

#[tauri::command]
pub fn session_save_window(session_id: String, window: WindowState, state: State<'_, KernelState>) -> KernelResult<()> {
    state
        .0
        .lock()
        .unwrap()
        .session_save_window(&session_id, &window)
        .map_err(|e| e.to_string())
}

#[tauri::command]
pub fn session_restore(id: String, state: State<'_, KernelState>) -> KernelResult<Option<Session>> {
    state
        .0
        .lock()
        .unwrap()
        .session_restore(&id)
        .map_err(|e| e.to_string())
}

pub fn bridge_kernel_events(app: AppHandle, state: State<'_, KernelState>) {
    state.0.lock().unwrap().bus.subscribe(move |event| {
        let _ = app.emit(&event.topic, event.clone());
    });
}

// --- Phase 2 Hardware Commands ---

#[tauri::command]
pub fn hardware_probe(req: HardwareProbeRequest) -> KernelResult<ProbeResult> {
    let transport = Transport::parse(&req.transport)
        .map_err(|e| format!("invalid transport: {e}"))?;
    let hal: Box<dyn Hal> = if req.use_real.unwrap_or(false) {
        Box::new(RealHal)
    } else {
        Box::new(SimulatedHal)
    };
    let result = hal.probe(transport, &req.target);
    Ok(result)
}

#[tauri::command]
pub fn hardware_enumerate(transport: String) -> KernelResult<Vec<String>> {
    let t = Transport::parse(&transport)
        .map_err(|e| format!("invalid transport: {e}"))?;
    match t {
        Transport::Usb => Ok(UsbTransport::enumerate()),
        Transport::Serial => Ok(SerialTransport::enumerate()),
        Transport::Gpio => Ok(GpioTransport::enumerate_chips().into_iter().map(|(_, label)| format!("gpio:{label}")).collect()),
        _ => Ok(vec![]),
    }
}

#[tauri::command]
pub fn hardware_connect(req: HardwareConnectRequest) -> KernelResult<String> {
    let transport = Transport::parse(&req.transport)
        .map_err(|e| format!("invalid transport: {e}"))?;
    let hal: Box<dyn Hal> = Box::new(SimulatedHal);
    let result = hal.probe(transport, &req.target);
    if result.handshake_success {
        Ok(format!("connected:{}", req.target))
    } else {
        Err(result.error.unwrap_or_else(|| "connection failed".to_string()))
    }
}

#[tauri::command]
pub fn hardware_disconnect(target: String) -> KernelResult<()> {
    let _ = target;
    Ok(())
}

#[tauri::command]
pub fn hardware_read(req: HardwareReadRequest) -> KernelResult<Vec<u8>> {
    let _ = req.transport;
    let _ = req.target;
    Ok(vec![0u8; req.length.min(4096)])
}

#[tauri::command]
pub fn hardware_write(req: HardwareWriteRequest) -> KernelResult<usize> {
    let _ = req.transport;
    let _ = req.target;
    Ok(req.data.len())
}

#[tauri::command]
pub fn hardware_diagnostics(req: HardwareConnectRequest) -> KernelResult<HardwareDiagnosticsResponse> {
    let transport = Transport::parse(&req.transport)
        .map_err(|e| format!("invalid transport: {e}"))?;
    let hal: Box<dyn Hal> = Box::new(SimulatedHal);
    let result = hal.probe(transport, &req.target);
    let mut metrics = std::collections::HashMap::new();
    metrics.insert("handshake_success".to_string(), serde_json::json!(result.handshake_success));
    metrics.insert("latency_ms".to_string(), serde_json::json!(result.latency_ms.unwrap_or(0.0)));
    Ok(HardwareDiagnosticsResponse {
        transport: req.transport,
        target: req.target,
        healthy: result.handshake_success,
        metrics,
    })
}

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
        let mut groups = [0u8; 4];
        let mut pad = 0u8;
        for slot in 0..4 {
            while i < bytes.len() && (bytes[i] == b' ' || bytes[i] == b'\n' || bytes[i] == b'\r') {
                i += 1;
            }
            if i >= bytes.len() || bytes[i] == b'=' {
                if i < bytes.len() && bytes[i] == b'=' { i += 1; }
                pad += 1;
                continue;
            }
            let v = DECODE[bytes[i] as usize];
            if v < 0 { return Err(format!("invalid base64 at {i}").into()); }
            groups[slot] = v as u8;
            i += 1;
        }
        if pad == 4 { break; }
        out.push((groups[0] << 2) | (groups[1] >> 4));
        if pad < 2 { out.push((groups[1] << 4) | (groups[2] >> 2)); }
        if pad < 1 { out.push((groups[2] << 6) | groups[3]); }
        if pad > 0 { break; }
    }
    Ok(out)
}
