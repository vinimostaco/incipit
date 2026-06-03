// Learn more about Tauri commands at https://tauri.app/develop/calling-rust/
use std::sync::Mutex;

use tauri::{Manager, RunEvent};
use tauri_plugin_shell::process::{CommandChild, CommandEvent};
use tauri_plugin_shell::ShellExt;

// Guarda o processo do sidecar (backend FastAPI) para encerrá-lo ao sair.
#[derive(Default)]
struct Backend(Mutex<Option<CommandChild>>);

// Sobe o sidecar `incipit-backend` (porta fixa 8765; o frontend faz polling de
// /health). O stdout/stderr do backend é repassado pro log do app.
fn spawn_backend(app: &tauri::AppHandle) {
    let sidecar = match app.shell().sidecar("incipit-backend") {
        Ok(cmd) => cmd,
        Err(e) => {
            eprintln!("[incipit] falha ao resolver o sidecar: {e}");
            return;
        }
    };

    let (mut rx, child) = match sidecar.spawn() {
        Ok(pair) => pair,
        Err(e) => {
            eprintln!("[incipit] falha ao subir o backend: {e}");
            return;
        }
    };

    app.state::<Backend>().0.lock().unwrap().replace(child);

    tauri::async_runtime::spawn(async move {
        while let Some(event) = rx.recv().await {
            match event {
                CommandEvent::Stdout(line) => {
                    print!("[backend] {}", String::from_utf8_lossy(&line))
                }
                CommandEvent::Stderr(line) => {
                    eprint!("[backend] {}", String::from_utf8_lossy(&line))
                }
                CommandEvent::Terminated(payload) => {
                    eprintln!("[incipit] backend encerrou: {:?}", payload.code);
                    break;
                }
                _ => {}
            }
        }
    });
}

// Encerra o sidecar (chamado na saída do app).
fn kill_backend(app: &tauri::AppHandle) {
    let child = app.state::<Backend>().0.lock().unwrap().take();
    if let Some(child) = child {
        let _ = child.kill();
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_shell::init())
        .manage(Backend::default())
        .setup(|app| {
            // Define o ícone da janela (barra de tarefas no Linux usa _NET_WM_ICON;
            // sem isso o WM mostra um ícone genérico).
            if let Some(window) = app.get_webview_window("main") {
                if let Ok(icon) = tauri::image::Image::from_bytes(include_bytes!("../icons/icon.png")) {
                    let _ = window.set_icon(icon);
                }
            }
            spawn_backend(app.handle());
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while running tauri application")
        .run(|app, event| match event {
            RunEvent::ExitRequested { .. } | RunEvent::Exit => kill_backend(app),
            _ => {}
        });
}
