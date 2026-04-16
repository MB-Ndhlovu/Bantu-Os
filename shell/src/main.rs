use std::io::{self, Write};

fn main() {
    println!("Bantu-OS Shell v0.1.0");
    println!("Type 'exit' to quit.\n");

    loop {
        print!("bantu> ");
        io::stdout().flush().unwrap();

        let mut input = String::new();
        if io::stdin().read_line(&mut input).unwrap() == 0 {
            break;
        }

        let input = input.trim();
        if input.is_empty() {
            continue;
        }

        if input == "exit" {
            println!("Goodbye!");
            break;
        }

        println!("You entered: {}", input);
    }
}