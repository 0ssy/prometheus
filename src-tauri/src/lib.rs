#![cfg_attr(mobile, tauri::mobile_entry_point)]

use std::sync::Mutex;

use tauri::Manager;
use tauri_plugin_shell::process::CommandChild;
use tauri_plugin_shell::ShellExt;

/// Handle to the bundled Python backend process, so we can terminate it
/// when the desktop app exits.
struct SidecarHandle(Mutex<Option<CommandChild>>);

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let builder = tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(SidecarHandle(Mutex::new(None)))
        .setup(|app| {
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
