//! Bantu-OS Shell — AI REPL
//! Layer 2: Rust shell connecting to Layer 3 Python AI engine.

use std::io::{self, Read, Write};
use std::process::{Command, Stdio};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex};
use rustyline::completion::{Completer, Pair};
use rustyline::error::ReadlineError;
use rustyline::highlight::Highlighter;
use rustyline::hint::Hinter;
use rustyline::history::DefaultHistory;
use rustyline::validate::Validator;
use rustyline::{Context, Editor, Helper};

mod parser;
mod tools;

const HISTORY_FILE: &str = "bantu_os_data/shell_history.txt";
const SOCKET_PATH: &str = "/tmp/bantu.sock";

static AI_MODE: AtomicBool = AtomicBool::new(false);

struct CommandCompleter {
    commands: Vec<String>,
}

impl Completer for CommandCompleter {
    type Candidate = Pair;

    fn complete(
        &self,
        line: &str,
        pos: usize,
        _ctx: &Context<'_>,
    ) -> rustyline::Result<(usize, Vec<Pair>)> {
        let start = line[..pos].rfind(char::is_whitespace).map_or(0, |index| index + 1);
        let prefix = &line[start..pos];
        let matches = self
            .commands
            .iter()
            .filter(|command| command.starts_with(prefix))
            .map(|command| Pair {
                display: command.clone(),
                replacement: command.clone(),
            })
            .collect();
        Ok((start, matches))
    }
}

impl Hinter for CommandCompleter {
    type Hint = String;
}
impl Highlighter for CommandCompleter {}
impl Validator for CommandCompleter {}
impl Helper for CommandCompleter {}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    println!("Bantu-OS Shell v0.1.0 — AI-powered REPL");
    println!("Type 'help' for commands, or chat naturally with the AI.\n");

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
    let mut editor = match setup_editor(&registry) {
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
                save_history(&mut editor);
                if let Some(msg) = process_input(trimmed, &registry) {
                    println!("{}", msg);
                }
            }
            Err(ReadlineError::Interrupted) => {
                println!("(use 'exit' or 'quit' to exit)");
                continue;
            }
            Err(ReadlineError::Eof) => {
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

fn setup_editor(
    registry: &tools::ToolRegistry,
) -> rustyline::Result<Editor<CommandCompleter, DefaultHistory>> {
    let mut editor = Editor::new()?;
    editor.set_helper(Some(CommandCompleter {
        commands: shell_commands(registry),
    }));
    let history_path = std::path::Path::new(HISTORY_FILE);
    let _ = editor.load_history(history_path);
    Ok(editor)
}

fn save_history(editor: &mut Editor<CommandCompleter, DefaultHistory>) {
    let history_path = std::path::Path::new(HISTORY_FILE);
    if let Some(parent) = history_path.parent() {
        let _ = std::fs::create_dir_all(parent);
    }
    let _ = editor.save_history(history_path);
}

fn shell_commands(registry: &tools::ToolRegistry) -> Vec<String> {
    let mut commands = vec![
        "ai", "ai on", "ai off", "clear", "exit", "help", "login", "logout", "quit", "status", "whoami",
    ]
    .into_iter()
    .map(String::from)
    .collect::<Vec<_>>();
    commands.extend(registry.list_tools().into_iter().map(|tool| tool.name.clone()));
    commands.sort();
    commands.dedup();
    commands
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
        "ai" => return Some("Usage: ai <your message>. Or type 'ai on' for persistent goal mode.".to_string()),
        "ai on" => {
            AI_MODE.store(true, Ordering::SeqCst);
            return Some("AI mode enabled. Speak your goal naturally or type 'ai off' to return to shell mode.".to_string());
        }
        "ai off" => {
            AI_MODE.store(false, Ordering::SeqCst);
            return Some("Shell mode restored.".to_string());
        }
        "status" => return Some(get_status()),
        _ if trimmed.starts_with("login ") => {
            let username = trimmed.strip_prefix("login ").unwrap().trim();
            if username.is_empty() {
                return Some("Usage: login <username>".to_string());
            }
            let cmd = serde_json::json!({"cmd": "login", "username": username});
            return send_kernel_cmd(&serde_json::to_string(&cmd).unwrap());
        }
        "logout" => {
            let cmd = serde_json::json!({"cmd": "logout"});
            return send_kernel_cmd(&serde_json::to_string(&cmd).unwrap());
        }
        "whoami" => {
            let cmd = serde_json::json!({"cmd": "whoami"});
            return send_kernel_cmd(&serde_json::to_string(&cmd).unwrap());
        }
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
        Ok(call) => match registry.execute(&call.tool, &call.args) {
            Ok(output) => if output.is_empty() { None } else { Some(output) },
            Err(e) => Some(format!("Error: {:?}", e)),
        },
        Err(_) => {
            let output = Command::new("sh")
                .arg("-c")
                .arg(trimmed)
                .stdout(Stdio::piped())
                .stderr(Stdio::piped())
                .output();
            match output {
                Ok(out) => {
                    if out.status.success() {
                        let stdout = String::from_utf8_lossy(&out.stdout);
                        if stdout.is_empty() { None } else { Some(stdout.to_string()) }
                    } else {
                        let stderr = String::from_utf8_lossy(&out.stderr);
                        if stderr.is_empty() {
                            Some(format!("Command exited with code {}", out.status.code().unwrap_or(1)))
                        } else {
                            Some(stderr.to_string())
                        }
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
    let request = serde_json::json!({"cmd": "intent", "text": query, "stream": true});
    let msg = serde_json::to_string(&request).unwrap();
    if let Err(e) = sock.write_all(msg.as_bytes()).and_then(|_| sock.write_all(b"\n")) {
        println!("AI unavailable: write failed ({})", e);
        return;
    }
    // After sending the request, take a separate read-only view of the socket
    // for streaming responses. The original `sock` keeps write access so we can
    // answer confirmation prompts on the same connection.
    let read_stream = sock.try_clone().expect("clone socket for read half");
    let mut reader = std::io::BufReader::new(read_stream);
    use std::io::BufRead;
    let mut lines = reader.lines();
    loop {
        let line = match lines.next() {
            Some(Ok(l)) => l,
            Some(Err(e)) => {
                eprintln!("AI read error: {}", e);
                break;
            }
            None => break,
        };
        let trimmed = line.trim();
        if trimmed.is_empty() {
            continue;
        }
        let resp: serde_json::Value = match serde_json::from_str(trimmed) {
            Ok(v) => v,
            Err(_) => continue,
        };
        let kind = resp["type"].as_str().unwrap_or("");
        match kind {
            "clarification_needed" => {
                println!("{}", resp["question"].as_str().unwrap_or("Could you clarify?"));
            }
            "goal_update" => {
                if let Some(msg) = resp["message"].as_str() {
                    if !msg.is_empty() {
                        println!("> {}", msg);
                    }
                }
            }
            "confirmation_required" => {
                let step_id = resp["step_id"].as_str().unwrap_or("").to_string();
                let description = resp["description"].as_str().unwrap_or("(action)");
                let impact = resp["impact"].as_str().unwrap_or("");
                println!("\n⚠  Confirmation required: {}", description);
                if !impact.is_empty() {
                    println!("   Impact: {}", impact);
                }
                println!("   [Y] Approve   [S] Skip   [A] Abort   [?] Explain");
                use std::io::Write;
                let mut input_buf = String::new();
                let _ = std::io::stdin().read_line(&mut input_buf);
                let choice = input_buf.trim().to_lowercase();
                let decision = match choice.as_str() {
                    "y" | "yes" => "approve",
                    "a" | "abort" => "abort",
                    "?" | "explain" => "explain",
                    _ => "skip",
                };
                let reply = serde_json::json!({
                    "cmd": "confirm",
                    "step_id": step_id,
                    "decision": decision,
                });
                let payload = format!("{}\n", serde_json::to_string(&reply).unwrap());
                if let Err(e) = sock.write_all(payload.as_bytes()) {
                    println!("Failed to send confirmation: {}", e);
                    return;
                }
                let _ = std::io::stdout().flush();
            }
            "goal_complete" => {
                println!("\n{}", resp["summary"].as_str().unwrap_or(""));
                break;
            }
            "goal_failed" => {
                println!("Goal failed: {}", resp["error"].as_str().unwrap_or("unknown"));
                break;
            }
            _ => {
                if resp["ok"].as_bool() == Some(true) {
                    println!("{}", resp["result"].as_str().unwrap_or("(no response)"));
                } else if let Some(err) = resp["error"].as_str() {
                    println!("AI error: {}", err);
                }
            }
        }
    }
}
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
    help.push_str("  login <name>   Login as a user (creates persistent session)\n");
    help.push_str("  logout         Logout and destroy session\n");
    help.push_str("  whoami         Show current user and session info\n");
    help.push_str("  exit / quit    Exit shell\n\n");
    help.push_str("SYSTEM TOOLS:\n");
    for tool in registry.list_tools() {
        help.push_str(&format!("  {:12} — {}\n", tool.name, tool.description));
    }
    help.push_str("\nQUICK TIPS:\n");
    help.push_str("  ai <message>   Ask the AI anything\n");
    help.push_str("  ai on          Persistent goal mode\n");
    help.push_str("  Up/Down arrows Navigate command history\n");
    help
}

fn send_kernel_cmd(json_cmd: &str) -> Option<String> {
    let mut sock = match std::os::unix::net::UnixStream::connect(SOCKET_PATH) {
        Ok(s) => s,
        Err(e) => {
            println!("AI unavailable: socket connection failed ({})", e);
            println!("Hint: Run ./start.sh to start the Python kernel server");
            return None;
        }
    };

    let msg = format!("{}\n", json_cmd.trim());
    if let Err(e) = sock.write_all(msg.as_bytes()) {
        println!("AI unavailable: write failed ({})", e);
        return None;
    }

    let mut response = String::new();
    match sock.read_to_string(&mut response) {
        Ok(_) => {}
        Err(e) => {
            println!("AI unavailable: read failed ({})", e);
            return None;
        }
    }

    if let Ok(resp) = serde_json::from_str::<serde_json::Value>(&response) {
        if resp["ok"].as_bool() == Some(true) {
            return Some(resp["result"].as_str().unwrap_or("(no response)").to_string());
        } else {
            return Some(format!("Error: {}", resp["error"].as_str().unwrap_or("unknown")));
        }
    }
    Some(String::from("(invalid response)"))
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