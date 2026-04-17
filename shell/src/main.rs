//! Bantu-OS Shell — AI REPL
//! Layer 2: Rust shell connecting to Layer 3 Python AI engine.

use std::io::{self, Write};
use std::process::{Command, Stdio};

mod parser;
mod tools;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    println!("Bantu-OS Shell v0.1.0 — AI-powered REPL");
    println!("Type 'help' for commands, or chat naturally with the AI.\n");

    let registry = tools::ToolRegistry::new();
    let mut ai_mode = false;

    loop {
        let prompt = if ai_mode { "bantu-ai> " } else { "bantu> " };
        print!("{}", prompt);
        std::io::stdout().flush()?;

        let mut line = String::new();
        if std::io::stdin().read_line(&mut line).is_err() {
            break;
        }

        let trimmed = line.trim();
        if trimmed.is_empty() {
            continue;
        }

        if trimmed == "exit" || trimmed == "quit" {
            println!("Goodbye from Bantu-OS.");
            break;
        }

        if trimmed == "ai" || trimmed == "ai on" {
            ai_mode = true;
            println!("AI mode enabled. Chat naturally or type 'ai off' to return to shell mode.");
            continue;
        }

        if trimmed == "ai off" {
            ai_mode = false;
            println!("Shell mode restored.");
            continue;
        }

        // "ai hello" works directly from shell mode — no need to enter AI mode first
        if !ai_mode && trimmed.starts_with("ai ") {
            handle_ai_input(trimmed);
            continue;
        }

        if ai_mode {
            handle_ai_input(trimmed);
        } else {
            handle_shell_input(trimmed, &registry);
        }
    }

    Ok(())
}

fn handle_shell_input(input: &str, registry: &tools::ToolRegistry) {
    match parser::parse(input) {
        Ok(call) => {
            match registry.execute(&call.tool, &call.args) {
                Ok(output) => println!("{}", output),
                Err(e) => eprintln!("Error: {:?}", e),
            }
        }
        Err(_) => {
            let output = Command::new("sh")
                .arg("-c")
                .arg(input)
                .stdout(Stdio::piped())
                .stderr(Stdio::piped())
                .output();
            match output {
                Ok(out) => {
                    if out.status.success() {
                        print!("{}", String::from_utf8_lossy(&out.stdout));
                    } else {
                        eprint!("{}", String::from_utf8_lossy(&out.stderr));
                    }
                }
                Err(e) => eprintln!("Could not execute: {}", e),
            }
        }
    }
}

fn handle_ai_input(input: &str) {
    // Strip "ai " prefix if present so we only send the actual query
    let query = input.strip_prefix("ai ").map(str::trim).unwrap_or(input);
    if query.is_empty() {
        println!("Usage: ai <your message>");
        return;
    }

    let socket_path = "/tmp/bantu.sock";
    let mut sock = match std::os::unix::net::UnixStream::connect(socket_path) {
        Ok(s) => s,
        Err(e) => {
            println!("AI unavailable: socket connection failed ({})", e);
            return;
        }
    };

    let request = serde_json::json!({"cmd": "ai", "text": query});
    let msg = serde_json::to_string(&request).unwrap();
    use std::io::{Read, Write};
    if let Err(e) = sock.write_all(msg.as_bytes()) {
        println!("AI unavailable: write failed ({})", e);
        return;
    }
    if let Err(e) = sock.write_all(b"\n") {
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

// DEBUG: subprocess fallback kept for manual debugging only.
// Uncomment below and comment out handle_ai_input body to use subprocess mode.
/*
fn handle_ai_subprocess(input: &str) {
    let script = format!(
        "cd /home/workspace/bantu_os && python3 -c \"\nimport sys\nfrom bantu_os.core.kernel import Kernel\nimport asyncio\nk = Kernel()\nresult = asyncio.run(k.process_input('{}'))\nprint(result)\n\"",
        input.replace('\'', "'\\''")
    );
    let output = std::process::Command::new("sh")
        .arg("-c")
        .arg(&script)
        .output();
    match output {
        Ok(out) => {
            let stdout = String::from_utf8_lossy(&out.stdout);
            let stderr = String::from_utf8_lossy(&out.stderr);
            if stdout.trim().is_empty() && !stderr.trim().is_empty() {
                println!("(AI: {})", stderr.trim());
            } else {
                println!("{}", stdout.trim());
            }
        }
        Err(e) => println!("AI unavailable: {}", e),
    }
}
*/