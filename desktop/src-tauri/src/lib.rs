/// skill-hub desktop — Rust 薄层。
/// 只做窗口 + shell 插件注册；所有业务逻辑走 skill-hub CLI 子进程。
#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_dialog::init())
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
