//! Command parser - converts natural language to structured tool calls

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ToolCall {
    pub tool: String,
    pub args: Vec<String>,
    pub raw: String,
}

impl ToolCall {
    pub fn new(tool: &str, args: Vec<&str>) -> Self {
        Self {
            tool: tool.to_string(),
            args: args.into_iter().map(|s| s.to_string()).collect(),
            raw: String::new(),
        }
    }
}

/// Parse natural language input into tool calls
pub fn parse(input: &str) -> Result<ToolCall, String> {
    let trimmed = input.trim();
    if trimmed.is_empty() {
        return Err("Empty input".to_string());
    }

    let tokens = tokenize(trimmed);
    if tokens.is_empty() {
        return Err("No tokens found".to_string());
    }

    let (tool, args) = dispatch(&tokens)?;
    let mut call = ToolCall::new(tool, args);
    call.raw = trimmed.to_string();
    Ok(call)
}

fn tokenize(input: &str) -> Vec<String> {
    let mut tokens = Vec::new();
    let mut current = String::new();
    let mut in_quotes = false;

    for ch in input.chars() {
        match ch {
            '"' => in_quotes = !in_quotes,
            ' ' if !in_quotes => {
                if !current.is_empty() {
                    tokens.push(current.clone());
                    current.clear();
                }
            }
            _ => current.push(ch),
        }
    }
    if !current.is_empty() {
        tokens.push(current);
    }
    tokens
}

fn dispatch(tokens: &[String]) -> Result<(&str, Vec<&str>), String> {
    let first = tokens.first().map(|s| s.as_str()).unwrap_or("");
    let all_lower = tokens.iter().map(|s| s.to_lowercase()).collect::<Vec<_>>();
    let all_lower_first = first.to_lowercase();
    let joined = all_lower.join(" ");
    
    // Single-word tool dispatch (check first for exact matches)
    let tool = match all_lower_first.as_str() {
        "list" | "ls" => "ls",
        "read" | "cat" | "view" => "cat",
        "find" | "search" => "grep",
        "run" | "execute" | "do" => "run",
        "status" => "ps",
        "kill" | "stop" => "kill",
        "help" | "?" => "help",
        "cd" | "change" => "cd",
        "pwd" => "pwd",
        "whoami" | "user" => "whoami",
        "mkdir" | "create" => "mkdir",
        "rm" | "delete" | "remove" => "rm",
        "cp" | "copy" => "cp",
        "mv" | "move" => "mv",
        "write" | "echo" => "write",
        "readfile" | "open" => "readfile",
        "show" => {
            if joined.contains("process") || joined.contains("running") {
                "ps"
            } else if tokens.len() > 1
                && (tokens[1].starts_with('/')
                    || tokens[1].starts_with("./")
                    || tokens[1].starts_with("."))
            {
                "cat"
            } else {
                "ls"
            }
        }
        "where" => "pwd",
        _ => first,
    };

    // Handle multi-word patterns that need post-processing
    // "where am i" / "where current" → pwd (handled in match above)
    // "where is X" → grep (search for X)
    if tool == "pwd" && joined.contains("where") && joined.contains("is ") {
        return Ok(("grep", tokens[1..].iter().map(|s| s.as_str()).collect()));
    }

    let args: Vec<&str> = tokens[1..].iter().map(|s| s.as_str()).collect();
    Ok((tool, args))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_list_command() {
        let result = parse("list files in current directory");
        assert!(result.is_ok());
        let call = result.unwrap();
        assert_eq!(call.tool, "ls");
    }

    #[test]
    fn test_parse_cat_command() {
        let result = parse("cat /etc/hostname");
        assert!(result.is_ok());
        let call = result.unwrap();
        assert_eq!(call.tool, "cat");
        assert_eq!(call.args, vec!["/etc/hostname"]);
    }

    #[test]
    fn test_parse_ps_command() {
        let result = parse("show running processes");
        assert!(result.is_ok());
        let call = result.unwrap();
        assert_eq!(call.tool, "ps");
    }

    #[test]
    fn test_parse_pwd_command() {
        let result = parse("where am i");
        assert!(result.is_ok());
        let call = result.unwrap();
        assert_eq!(call.tool, "pwd");
    }

    #[test]
    fn test_empty_input() {
        let result = parse("");
        assert!(result.is_err());
    }

    #[test]
    fn test_tokenize_with_quotes() {
        let tokens = tokenize("write \"hello world\" to /tmp/test");
        assert_eq!(tokens.len(), 4);
        assert_eq!(tokens[0], "write");
        assert_eq!(tokens[1], "hello world");
    }

    #[test]
    fn test_show_routes_to_cat_for_path() {
        let result = parse("show /etc/passwd");
        assert!(result.is_ok());
        let call = result.unwrap();
        assert_eq!(call.tool, "cat");
        assert_eq!(call.args, vec!["/etc/passwd"]);
    }

    #[test]
    fn test_show_routes_to_ls_by_default() {
        let result = parse("show");
        assert!(result.is_ok());
        let call = result.unwrap();
        assert_eq!(call.tool, "ls");
    }

    #[test]
    fn test_show_routes_to_ps_for_processes() {
        let result = parse("show running processes");
        assert!(result.is_ok());
        let call = result.unwrap();
        assert_eq!(call.tool, "ps");
    }

    #[test]
    fn test_where_is_this_routes_to_grep() {
        let result = parse("where is this");
        assert!(result.is_ok());
        let call = result.unwrap();
        assert_eq!(call.tool, "grep");
        assert_eq!(call.args, vec!["is", "this"]);
    }
}
