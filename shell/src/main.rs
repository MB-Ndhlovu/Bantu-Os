//! Bantu-OS Shell — AI REPL
//! Layer 2: Rust shell connecting to Layer 3 Python AI engine.

use std::io::{self, Read, Write};
use std::process::{Command, Stdio};
use std::sync::atomic::{AtomicBool, Ordering};
use rustyline::history::History;

mod parser;
mod tools;

const HISTORY_FILE: &str = "/tmp/bantu_shell_history";
const SOCKET_PATH: &str = "/tmp/bantu.sock";

static AI_MODE: AtomicBool = AtomicBool::new(false);

fn main() -> Result<(), Box<dyn std::error::Error>> {
    println!("Bantu-OS Shell v0.1.0 — AI-powered REPL");
    println!("Type 'help' for commands, or chat naturally with the AI.\n");

    // Pipe mode: read stdin line-by-line, process each, then exit
    if !atty::is(atty::Stream::Stdin) {
        let registry = tools::ToolRegistry::new();
        check_kernel_status();
        let stdin = std::io::stdin();
        for line in stdin.lines().map_while(Result::ok) {
            let trimmed = line.trim();
            if trimmed.is_empty() {
                continue;
            }
            if trimmed == "exit" || trimmed == "quit" {
                break;
            }
            if let Some(msg) = process_input(trimmed, &registry) {
                println!("{}", msg);
            }
        }
        return Ok(());
    }

    let registry = tools::ToolRegistry::new();

    // Set up rustyline editor with file-backed history
    let mut editor = match setup_editor() {
        Ok(ed) => ed,
        Err(e) => {
            eprintln!("[shell] readline error: {} — using basic mode", e);
            run_simple_loop(&registry);
            return Ok(());
        }
    };

    check_kernel_status();

    loop {
        let prompt = if AI_MODE.load(Ordering::SeqCst) {
            "bantu-ai> "
        } else {
            "bantu> "
        };

        let readline = editor.readline(prompt);
        match readline {
            Ok(line) => {
                let trimmed = line.trim();
                if trimmed.is_empty() {
                    continue;
                }
                let _ = editor.add_history_entry(line.as_str());
                save_history(&editor);
                if let Some(msg) = process_input(trimmed, &registry) {
                    println!("{}", msg);
                }
            }
            Err(rustyline::error::ReadlineError::Interrupted) => {
                println!("(use 'exit' or 'quit' to exit)");
                continue;
            }
            Err(rustyline::error::ReadlineError::Eof) => {
                println!("Goodbye from Bantu-OS.");
                break;
            }
            Err(e) => {
                eprintln!("Error: {}", e);
                break;
            }
        }
    }

    Ok(())
}

fn setup_editor() -> rustyline::Result<rustyline::Editor<(), rustyline::history::MemHistory>> {
    let mut editor = rustyline::Editor::new()?;

    // Load existing history from file
    if let Ok(content) = std::fs::read_to_string(HISTORY_FILE) {
        for line in content.lines() {
            if !line.is_empty() {
                let _ = editor.add_history_entry(line);
            }
        }
    }

    Ok(editor)
}

fn save_history(editor: &rustyline::Editor<(), rustyline::history::MemHistory>) {
    use rustyline::history::SearchDirection;
    let history = editor.history();
    let count = history.len();
    let mut entries = Vec::with_capacity(count);
    for i in 0..count {
        if let Ok(Some(entry)) = history.get(i, SearchDirection::Forward) {
            entries.push(entry.entry.clone());
        }
    }
    let _ = std::fs::write(HISTORY_FILE, entries.join("\n"));
}

fn run_simple_loop(registry: &tools::ToolRegistry) {
    let stdin = io::stdin();
    loop {
        let prompt = if AI_MODE.load(Ordering::SeqCst) {
            "bantu-ai> "
        } else {
            "bantu> "
        };
        print!("{}", prompt);
        let _ = io::stdout().flush();
        let mut line = String::new();
        if stdin.read_line(&mut line).is_err() {
            break;
        }
        let trimmed = line.trim();
        if trimmed.is_empty() {
            continue;
        }
        if let Some(msg) = process_input(trimmed, registry) {
            println!("{}", msg);
        }
    }
}

fn process_input(input: &str, registry: &tools::ToolRegistry) -> Option<String> {
    let trimmed = input.trim();

    // Pipe mode: detect raw JSON from stdin and forward directly to kernel
    if trimmed.starts_with('{') {
        return Some(handle_raw_json(trimmed));
    }

    match trimmed {
        "exit" | "quit" => {
            println!("Goodbye from Bantu-OS.");
            std::process::exit(0);
        }
        "help" => return Some(get_shell_help()),
        "clear" => {
            print!("\x1b[2J\x1b[H");
            std::io::stdout().flush().ok();
            return None;
        }
        "ai" => return Some("Usage: ai <your message>. Or type 'ai on' for persistent AI mode.".to_string()),
        "ai on" => {
            AI_MODE.store(true, Ordering::SeqCst);
            return Some("AI mode enabled. Chat naturally or type 'ai off' to return to shell mode.".to_string());
        }
        "ai off" => {
            AI_MODE.store(false, Ordering::SeqCst);
            return Some("Shell mode restored.".to_string());
        }
        "status" => return Some(get_status()),
        _ => {}
    }

    if !AI_MODE.load(Ordering::SeqCst) && trimmed.starts_with("ai ") {
        handle_ai_input(trimmed);
        return None;
    }

    if AI_MODE.load(Ordering::SeqCst) {
        handle_ai_input(trimmed);
        return None;
    }

    match parser::parse(trimmed) {
        Ok(call) => {
            match registry.execute(&call.tool, &call.args) {
                Ok(output) => if output.is_empty() { None } else { Some(output) },
                Err(e) => Some(format!("Error: {:?}", e)),
            }
        }
        Err(_) => {
            let output = Command::new("sh").arg("-c").arg(trimmed)
                .stdout(Stdio::piped()).stderr(Stdio::piped()).output();
            match output {
                Ok(out) => {
                    if out.status.success() {
                        let stdout = String::from_utf8_lossy(&out.stdout);
                        if stdout.is_empty() { None } else { Some(stdout.to_string()) }
                    } else {
                        let stderr = String::from_utf8_lossy(&out.stderr);
                        if stderr.is_empty() {
                            Some(format!("Command exited with code {}", out.status.code().unwrap_or(1)))
                        } else { Some(stderr.to_string()) }
                    }
                }
                Err(e) => Some(format!("Could not execute: {}", e)),
            }
        }
    }
}

fn handle_ai_input(input: &str) {
    let query = input.strip_prefix("ai ").map(str::trim).unwrap_or(input);
    if query.is_empty() {
        println!("Usage: ai <your message>");
        return;
    }

    let mut sock = match std::os::unix::net::UnixStream::connect(SOCKET_PATH) {
        Ok(s) => s,
        Err(e) => {
            println!("AI unavailable: socket connection failed ({})", e);
            println!("Hint: Run ./start.sh to start the Python kernel server");
            return;
        }
    };

    let request = serde_json::json!({"cmd": "ai", "text": query});
    let msg = serde_json::to_string(&request).unwrap();
    if let Err(e) = sock.write_all(msg.as_bytes()).and_then(|_| sock.write_all(b"\n")) {
        println!("AI unavailable: write failed ({})", e);
        return;
    }

    let mut response = String::new();
    match sock.read_to_string(&mut response) {
        Ok(_) => {}
        Err(e) => {
            println!("AI unavailable: read failed ({})", e);
            return;
        }
    }

    if let Ok(resp) = serde_json::from_str::<serde_json::Value>(&response) {
        if resp["ok"].as_bool() == Some(true) {
            println!("{}", resp["result"].as_str().unwrap_or("(no response)"));
        } else {
            println!("AI error: {}", resp["error"].as_str().unwrap_or("unknown"));
        }
    } else {
        println!("AI: (invalid response)");
    }
}

/// Handle raw JSON input piped from stdin (pipe mode).
/// Directly forwards the JSON to the kernel socket and prints the result.
fn handle_raw_json(json_input: &str) -> String {
    let mut sock = match std::os::unix::net::UnixStream::connect(SOCKET_PATH) {
        Ok(s) => s,
        Err(e) => {
            return format!("Socket error: {e}");
        }
    };

    let msg = json_input.to_string();
    if let Err(e) = sock.write_all(msg.as_bytes()).and_then(|_| sock.write_all(b"\n")) {
        return format!("Write error: {e}");
    }

    let mut response = String::new();
    match sock.read_to_string(&mut response) {
        Ok(_) => {}
        Err(e) => {
            return format!("Read error: {e}");
        }
    }

    if let Ok(resp) = serde_json::from_str::<serde_json::Value>(&response) {
        if resp["ok"].as_bool() == Some(true) {
            return resp["result"].as_str().unwrap_or("(no response)").to_string();
        } else {
            return format!("Error: {}", resp["error"].as_str().unwrap_or("unknown"));
        }
    }
    "Invalid response from kernel".to_string()
}

fn get_shell_help() -> String {
    let registry = tools::ToolRegistry::new();
    let mut help = String::from("Bantu-OS Shell — Available commands:\n\n");
    help.push_str("SHELL COMMANDS:\n");
    help.push_str("  help           Show this help\n");
    help.push_str("  clear          Clear screen\n");
    help.push_str("  status         Show kernel/socket status\n");
    help.push_str("  ai on / ai off Toggle AI mode\n");
    help.push_str("  exit / quit    Exit shell\n\n");
    help.push_str("SYSTEM TOOLS:\n");
    for tool in registry.list_tools() {
        help.push_str(&format!("  {:12} — {}\n", tool.name, tool.description));
    }
    help.push_str("\nQUICK TIPS:\n");
    help.push_str("  ai <message>   Ask the AI anything\n");
    help.push_str("  ai on          Persistent AI conversation mode\n");
    help.push_str("  Up/Down arrows Navigate command history\n");
    help
}

fn check_kernel_status() {
    if std::path::Path::new(SOCKET_PATH).exists() {
        println!("[boot] Unix socket found at {}\n", SOCKET_PATH);
    } else {
        println!("[boot] Unix socket NOT found — AI features disabled until kernel starts");
        println!("[boot] Run ./start.sh to start the Python kernel\n");
    }
}

fn get_status() -> String {
    let socket_exists = std::path::Path::new(SOCKET_PATH).exists();
    let ai_mode = AI_MODE.load(Ordering::SeqCst);
    let mut s = String::from("=== Bantu-OS Status ===\n");
    s.push_str(&format!("Socket:  {} ({})\n", SOCKET_PATH, if socket_exists { "available" } else { "not found" }));
    s.push_str(&format!("AI mode: {}\n", if ai_mode { "enabled" } else { "disabled" }));
    s.push_str(&format!("History: {} (file-backed)\n", HISTORY_FILE));
    if !socket_exists {
        s.push_str("\nHint: Run ./start.sh to start the kernel server");
    }
    s
}