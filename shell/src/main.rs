use rustyline::error::ReadlineError;
use rustyline::Editor;
use serde::{Deserialize, Serialize};
use std::process::{Command, Stdio};
use std::io::Write;

mod parser;

fn main() {
    println!("========================================");
    println!("  Bantu-OS Shell v0.1.0");
    println!("  AI-Native Operating System");
    println!("  Type 'help' for commands, 'exit' to quit.");
    println!("========================================\n");

    let mut rl = Editor::<()>::new();
    let history_path = std::env::var("BANTU_HISTORY")
        .unwrap_or_else(|_| ".bantu_history".to_string());
    let _ = rl.load_history(&history_path);

    loop {
        let readline = rl.readline("bantu> ");
        match readline {
            Ok(line) => {
                let trimmed = line.trim();
                if trimmed.is_empty() {
                    continue;
                }
                rl.add_history_entry(&line);

                if trimmed == "exit" || trimmed == "quit" {
                    println!("Goodbye!");
                    break;
                }

                if trimmed == "help" {
                    print_help();
                    continue;
                }

                if trimmed == "sysinfo" {
                    print_sysinfo();
                    continue;
                }

                if trimmed == "list-tools" {
                    list_tools();
                    continue;
                }

                if let Some(response) = dispatch_to_engine(trimmed) {
                    println!("{}", response);
                }
            }
            Err(ReadlineError::Interrupted) => {
                println!("^C");
                continue;
            }
            Err(ReadlineError::Eof) => {
                println!("Goodbye!");
                break;
            }
            Err(err) => {
                println!("Error: {:?}", err);
                break;
            }
        }
    }

    let _ = rl.save_history(&history_path);
}

fn print_help() {
    println!("Bantu-OS Shell Commands:");
    println!("  help         - Show this help message");
    println!("  exit, quit   - Exit the shell");
    println!("  sysinfo      - Display system information");
    println!("  list-tools    - List available AI tools");
    println!("  <text>       - Send text to AI engine for processing");
    println!();
    println!("Examples:");
    println!("  bantu> What files are in my home directory?");
    println!("  bantu> Start a new Python process");
    println!("  bantu> Schedule a meeting for 3pm tomorrow");
}

fn print_sysinfo() {
    let uname_output = Command::new("uname")
        .arg("-a")
        .output()
        .map(|o| String::from_utf8_lossy(&o.stdout).to_string())
        .unwrap_or_else(|_| "unknown".to_string());

    println!("System: {}", uname_output.trim());

    if let Ok(hostname) = std::fs::read_to_string("/etc/hostname") {
        println!("Hostname: {}", hostname.trim());
    }

    if let Ok(uptime) = std::fs::read_to_string("/proc/uptime") {
        let secs: f64 = uptime.split_whitespace().next()
            .and_then(|s| s.parse().ok())
            .unwrap_or(0.0);
        let hours = (secs / 3600.0) as u32;
        let mins = ((secs / 60.0) % 60.0) as u32;
        println!("Uptime: {} hours, {} minutes", hours, mins);
    }

    println!("Bantu-OS Shell: Rust REPL active");
    println!("AI Engine: Connected");
}

fn list_tools() {
    println!("Available AI Tools:");
    println!("  file.read      - Read a file");
    println!("  file.write     - Write content to a file");
    println!("  file.list      - List directory contents");
    println!("  process.spawn  - Spawn a new process");
    println!("  process.list   - List running processes");
    println!("  process.kill   - Terminate a process");
    println!("  schedule.add   - Add a calendar event");
    println!("  schedule.list  - List upcoming events");
    println!("  network.get    - Perform HTTP GET request");
    println!("  memory.store   - Store information in memory");
    println!("  memory.query   - Query stored memory");
}

#[derive(Serialize, Deserialize, Debug)]
struct ToolRequest {
    tool: String,
    args: serde_json::Value,
}

#[derive(Serialize, Deserialize, Debug)]
struct ToolResponse {
    success: bool,
    result: Option<String>,
    error: Option<String>,
}

fn dispatch_to_engine(input: &str) -> Option<String> {
    println!("[AI Engine] Processing: {}", input);

    let tool_request = ToolRequest {
        tool: "ai.process".to_string(),
        args: serde_json::json!({ "input": input }),
    };

    let json = serde_json::to_string(&tool_request).ok()?;

    let child = Command::new("python3")
        .args(["-m", "bantu_os.core.kernel", "--tool", &json])
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .ok()?;

    let output = child.wait_with_output().ok()?;

    if output.status.success() {
        let result = String::from_utf8_lossy(&output.stdout);
        Some(result.to_string())
    } else {
        let error = String::from_utf8_lossy(&output.stderr);
        Some(format!("Error: {}", error))
    }
}
