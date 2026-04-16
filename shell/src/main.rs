use std::process::{Command, Stdio};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    println!("Bantu-OS Shell — built with Rust");
    println!("Type 'help' for commands, 'exit' to quit.\n");

    let mut rl = rustyline::Editor::<(), _>::new()?;

    let history_path = "/tmp/bantu_shell_history";
    let _ = rl.load_history(history_path);

    loop {
        let readline = rl.readline("bantu> ");
        match readline {
            Ok(line) => {
                let trimmed = line.trim();
                if trimmed.is_empty() {
                    continue;
                }
                let _ = rl.add_history_entry(trimmed);

                match trimmed {
                    "exit" | "quit" => {
                        println!("Goodbye.");
                        break;
                    }
                    "help" => {
                        println!("Commands:");
                        println!("  help       — show this");
                        println!("  exit/quit  — exit");
                        println!("  whoami     — current user");
                        println!("  pwd        — current dir");
                        println!("  ls         — list files");
                        println!("  <any>      — run shell command");
                        println!();
                        continue;
                    }
                    "whoami" => {
                        println!("{}", std::env::var("USER").unwrap_or_else(|_| "bantu".into()));
                        continue;
                    }
                    "pwd" => {
                        println!("{}", std::env::current_dir().unwrap_or_default().display());
                        continue;
                    }
                    "ls" => {
                        let _ = Command::new("ls")
                            .args(["-F"])
                            .stdout(Stdio::inherit())
                            .stderr(Stdio::inherit())
                            .status();
                        continue;
                    }
                    _ => {
                        let parts: Vec<&str> = trimmed.split_whitespace().collect();
                        if parts.is_empty() {
                            continue;
                        }
                        let status = Command::new(parts[0])
                            .args(&parts[1..])
                            .stdout(Stdio::inherit())
                            .stderr(Stdio::inherit())
                            .status();
                        if let Err(e) = status {
                            eprintln!("bantu: {}: {}", parts[0], e);
                        }
                    }
                }
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