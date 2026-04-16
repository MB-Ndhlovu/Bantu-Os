//! Bantu-OS AI Shell - Rust REPL for tool dispatch
//! 
//! Layer 2 of Bantu-OS: replaces bash as the primary interface.
//! Receives natural language commands, parses them, dispatches to system tools.

mod parser;
mod tools;

use parser::parse;
use tools::ToolRegistry;
use std::process::{Command, Stdio};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    println!("Bantu-OS Shell — AI-native command interface");
    println!("Type natural language commands or traditional shell syntax.\n");

    let mut rl = rustyline::Editor::<(), _>::new()?;
    let history_path = "/tmp/bantu_shell_history";
    let _ = rl.load_history(history_path);
    let registry = ToolRegistry::new();

    loop {
        let readline = rl.readline("bantu> ");
        match readline {
            Ok(line) => {
                if let Err(e) = process_input(&line, &registry) {
                    eprintln!("Error: {}", e);
                }
                let _ = rl.add_history_entry(line.trim());
            }
            Err(rustyline::error::ReadlineError::Interrupted) => {
                println!("^C");
                continue;
            }
            Err(rustyline::error::ReadlineError::Eof) => {
                println!("Goodbye.");
                break;
            }
            Err(e) => {
                eprintln!("Error: {:?}", e);
                break;
            }
        }
    }

    let _ = rl.save_history(history_path);
    Ok(())
}

fn process_input(input: &str, registry: &ToolRegistry) -> Result<(), String> {
    let trimmed = input.trim();
    if trimmed.is_empty() {
        return Ok(());
    }

    // Handle built-in commands
    match trimmed {
        "exit" | "quit" => {
            println!("Goodbye.");
            std::process::exit(0);
        }
        "help" => {
            print_registry_help(registry);
            return Ok(());
        }
        _ => {}
    }

    // Parse natural language to tool call
    let tool_call = parse(trimmed)?;
    
    // Execute via registry or fallback to shell
    match registry.execute(&tool_call.tool, &tool_call.args) {
        Ok(output) => {
            if !output.is_empty() {
                println!("{}", output);
            }
        }
        Err(e) => {
            // Fallback: try as raw shell command
            let status = Command::new(trimmed)
                .stdout(Stdio::inherit())
                .stderr(Stdio::inherit())
                .status();
            if let Err(e) = status {
                eprintln!("bantu: {}", e);
            }
        }
    }
    Ok(())
}

fn print_registry_help(registry: &ToolRegistry) {
    println!("Bantu-OS Shell Commands:");
    println!("  exit/quit  — exit shell");
    println!("  help       — show this help");
    println!();
    println!("Tool commands:");
    for tool in registry.list_tools() {
        println!("  {:12} — {}", tool.name, tool.description);
    }
    println!();
    println!("Examples:");
    println!("  list files in current directory");
    println!("  show running processes");
    println!("  cat /etc/hostname");
}
