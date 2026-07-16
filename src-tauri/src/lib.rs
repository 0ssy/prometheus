#![cfg_attr(mobile, tauri::mobile_entry_point)]

use std::sync::Mutex;

use aether_runtime::{AetherError, ChatRequest, ContextEngine, ProviderInfo, ProviderManager, RuntimeHealth, ToolDispatcher, DEFAULT_BACKEND_URL};
use tauri::Manager;
use tauri_plugin_shell::process::CommandChild;
use tauri_plugin_shell::ShellExt;

mod commands;
use commands::{bridge_kernel_events, KernelState};

/// Handle to the bundled Python backend process, so we can terminate it
/// when the desktop app exits.
struct SidecarHandle(Mutex<Option<CommandChild>>);

/// Tauri state wrapping the AI provider manager. Narrow lock scope: commands
/// clone the cheaply-cloneable manager out of the lock, then `await` without
/// holding it.
struct AetherManager(Mutex<ProviderManager>);

/// Stubbed context engine (Stage 4). Managed separately to keep the lock scope
/// narrow and independent of the provider manager. Read by later stages.
#[allow(dead_code)]
struct AetherContext(Mutex<ContextEngine>);

/// Stubbed tool dispatcher (Stage 5). Managed separately for the same reason.
#[allow(dead_code)]
struct AetherTools(Mutex<ToolDispatcher>);

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let runtime = aether_runtime::AetherRuntime::new();

    let builder = tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(SidecarHandle(Mutex::new(None)))
        .manage(AetherManager(Mutex::new(runtime.manager)))
        .manage(AetherContext(Mutex::new(runtime.context)))
        .manage(AetherTools(Mutex::new(runtime.tools)))
        .invoke_handler(tauri::generate_handler![
            aether_health,
            aether_list_providers,
            aether_ask,
            commands::terminal_spawn,
            commands::terminal_write,
            commands::terminal_resize,
            commands::terminal_kill,
            commands::terminal_record_command,
            commands::terminal_history,
            commands::kernel_status,
            commands::session_save,
            commands::session_save_window,
            commands::session_restore,
        ])
        .setup(|app| {
            // Build the kernel session DB path under the app's data dir
            // (Tauri persists this across runs, satisfying Phase 1 session
            // restore). Falls back to a temp dir if unavailable.
            let session_db = app
                .path()
                .app_data_dir()
                .map(|p| p.join("kernel_sessions.db"))
                .unwrap_or_else(|_| std::env::temp_dir().join("prometheus_kernel_sessions.db"));
            if let Some(parent) = session_db.parent() {
                let _ = std::fs::create_dir_all(parent);
            }
            let kernel = KernelState::new(session_db)
                .expect("failed to initialise Prometheus kernel");
            app.manage(kernel);
            bridge_kernel_events(app.handle(), app.state::<KernelState>());

            // Launch the bundled Python backend as a sidecar so the installed
            // app is fully self-contained (no external `python` on PATH needed).
            // In dev the sidecar binary is absent because `beforeDevCommand`
            // already started the Python server, so a spawn failure is expected
            // and ignored here.
            match app.shell().sidecar("prometheus") {
                Ok(command) => match command.args(["--server"]).spawn() {
                    Ok((_event_rx, child)) => {
                        app.state::<SidecarHandle>()
                            .0
                            .lock()
                            .unwrap()
                            .replace(child);
                        println!("Prometheus backend sidecar started");
                        // Block window creation until the backend actually listens, so the
                        // SPA never loads against a not-yet-ready server (blank window).
                        let addr = "127.0.0.1:8000";
                        for _ in 0..150 {
                            if std::net::TcpStream::connect(addr).is_ok() {
                                println!("Prometheus backend reachable at {addr}");
                                break;
                            }
                            std::thread::sleep(std::time::Duration::from_millis(100));
                        }
                    }
                    Err(e) => eprintln!("sidecar spawn failed (dev mode?): {e}"),
                },
                Err(e) => eprintln!("sidecar not configured (dev mode?): {e}"),
            }
            Ok(())
        });

    let app = builder
        .build(tauri::generate_context!())
        .expect("error while building Prometheus tauri application");

    app.run(|app_handle, event| {
        if let tauri::RunEvent::ExitRequested { .. } = event {
            if let Some(child) = app_handle
                .state::<SidecarHandle>()
                .0
                .lock()
                .unwrap()
                .take()
            {
                let _ = child.kill();
            }
        }
    });
}

/// Aggregate health across all providers and the Prometheus backend.
#[tauri::command]
async fn aether_health(manager: tauri::State<'_, AetherManager>) -> Result<RuntimeHealth, String> {
    let manager = manager.0.lock().unwrap().clone();
    Ok(aether_runtime::check_runtime(&manager, DEFAULT_BACKEND_URL).await)
}

/// List registered providers (ids, kinds, default flag).
#[tauri::command]
fn aether_list_providers(manager: tauri::State<'_, AetherManager>) -> Vec<ProviderInfo> {
    manager.0.lock().unwrap().list()
}

/// Ask the default or named provider a single-turn question and return its text.
#[tauri::command]
async fn aether_ask(
    prompt: String,
    provider: Option<String>,
    manager: tauri::State<'_, AetherManager>,
) -> Result<String, String> {
    let manager = manager.0.lock().unwrap().clone();
    let req = ChatRequest::from_prompt("", prompt);
    manager
        .chat(provider.as_deref(), req)
        .await
        .map(|resp| resp.content)
        .map_err(|e: AetherError| e.to_string())
}
