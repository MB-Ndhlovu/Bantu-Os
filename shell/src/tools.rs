//! Tool registry - system commands available to the shell

use std::collections::HashMap;
use std::process::{Command, Stdio};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Tool {
    pub name: String,
    pub description: String,
    pub args: Vec<String>,
}

#[derive(Debug)]
pub enum ToolError {
    ExecutionFailed(String),
    NotFound(String),
    InvalidArgs(String),
}

#[derive(Debug, Clone)]
pub struct ToolRegistry {
    tools: HashMap<String, Tool>,
}

impl ToolRegistry {
    pub fn new() -> Self {
        let mut registry = Self {
            tools: HashMap::new(),
        };
        registry.register_default_tools();
        registry
    }

    fn register_default_tools(&mut self) {
        let default_tools = vec![
            Tool { name: "ls".to_string(), description: "List directory contents".to_string(), args: vec!["path".to_string()] },
            Tool { name: "cat".to_string(), description: "Display file contents".to_string(), args: vec!["file".to_string()] },
            Tool { name: "ps".to_string(), description: "List running processes".to_string(), args: vec![] },
            Tool { name: "pwd".to_string(), description: "Print working directory".to_string(), args: vec![] },
            Tool { name: "whoami".to_string(), description: "Print current user".to_string(), args: vec![] },
            Tool { name: "cd".to_string(), description: "Change directory".to_string(), args: vec!["path".to_string()] },
            Tool { name: "mkdir".to_string(), description: "Create directory".to_string(), args: vec!["path".to_string()] },
            Tool { name: "rm".to_string(), description: "Remove file".to_string(), args: vec!["path".to_string()] },
            Tool { name: "cp".to_string(), description: "Copy file".to_string(), args: vec!["source".to_string(), "dest".to_string()] },
            Tool { name: "mv".to_string(), description: "Move file".to_string(), args: vec!["source".to_string(), "dest".to_string()] },
            Tool { name: "grep".to_string(), description: "Search text in files".to_string(), args: vec!["pattern".to_string(), "path".to_string()] },
            Tool { name: "run".to_string(), description: "Execute a command".to_string(), args: vec!["command".to_string(), "args".to_string()] },
            Tool { name: "help".to_string(), description: "Show help".to_string(), args: vec![] },
            Tool { name: "kill".to_string(), description: "Kill a process".to_string(), args: vec!["pid".to_string()] },
            Tool { name: "readfile".to_string(), description: "Read file contents".to_string(), args: vec!["path".to_string()] },
            Tool { name: "write".to_string(), description: "Write content to file".to_string(), args: vec!["content".to_string(), "path".to_string()] },
        ];

        for tool in default_tools {
            self.tools.insert(tool.name.clone(), tool);
        }
    }

    pub fn get_tool(&self, name: &str) -> Option<&Tool> {
        self.tools.get(name)
    }

    pub fn list_tools(&self) -> Vec<&Tool> {
        self.tools.values().collect()
    }

    pub fn execute(&self, tool_name: &str, args: &[String]) -> Result<String, ToolError> {
        match tool_name {
            "ls" => self.execute_ls(args),
            "cat" | "readfile" => self.execute_cat(args),
            "ps" => self.execute_ps(),
            "pwd" => self.execute_pwd(),
            "whoami" => self.execute_whoami(),
            "cd" => self.execute_cd(args),
            "mkdir" => self.execute_mkdir(args),
            "rm" => self.execute_rm(args),
            "cp" => self.execute_cp(args),
            "mv" => self.execute_mv(args),
            "grep" => self.execute_grep(args),
            "run" => self.execute_run(args),
            "help" => Ok(self.get_help()),
            "kill" => self.execute_kill(args),
            "write" => self.execute_write(args),
            _ => Err(ToolError::NotFound(format!("Unknown tool: {}", tool_name))),
        }
    }

    fn execute_ls(&self, args: &[String]) -> Result<String, ToolError> {
        let path = args.first().map(|s| s.as_str()).unwrap_or(".");
        let output = Command::new("ls").args(["-F", path]).stdout(Stdio::piped()).stderr(Stdio::piped()).output().map_err(|e| ToolError::ExecutionFailed(e.to_string()))?;
        if output.status.success() { Ok(String::from_utf8_lossy(&output.stdout).to_string()) } else { Err(ToolError::ExecutionFailed(String::from_utf8_lossy(&output.stderr).to_string())) }
    }

    fn execute_cat(&self, args: &[String]) -> Result<String, ToolError> {
        let file = args.first().ok_or_else(|| ToolError::InvalidArgs("Expected file path".to_string()))?;
        let output = Command::new("cat").arg(file).stdout(Stdio::piped()).stderr(Stdio::piped()).output().map_err(|e| ToolError::ExecutionFailed(e.to_string()))?;
        if output.status.success() { Ok(String::from_utf8_lossy(&output.stdout).to_string()) } else { Err(ToolError::ExecutionFailed(String::from_utf8_lossy(&output.stderr).to_string())) }
    }

    fn execute_ps(&self) -> Result<String, ToolError> {
        let output = Command::new("ps").args(["aux"]).stdout(Stdio::piped()).stderr(Stdio::piped()).output().map_err(|e| ToolError::ExecutionFailed(e.to_string()))?;
        Ok(String::from_utf8_lossy(&output.stdout).to_string())
    }

    fn execute_pwd(&self) -> Result<String, ToolError> {
        std::env::current_dir().map(|p| p.display().to_string()).map_err(|e| ToolError::ExecutionFailed(e.to_string()))
    }

    fn execute_whoami(&self) -> Result<String, ToolError> {
        Ok(std::env::var("USER").unwrap_or_else(|_| "bantu".to_string()))
    }

    fn execute_cd(&self, args: &[String]) -> Result<String, ToolError> {
        let path = args.first().ok_or_else(|| ToolError::InvalidArgs("Expected directory path".to_string()))?;
        std::env::set_current_dir(path).map_err(|e| ToolError::ExecutionFailed(e.to_string()))?;
        std::env::current_dir().map(|p| p.display().to_string()).map_err(|e| ToolError::ExecutionFailed(e.to_string()))
    }

    fn execute_mkdir(&self, args: &[String]) -> Result<String, ToolError> {
        let path = args.first().ok_or_else(|| ToolError::InvalidArgs("Expected directory path".to_string()))?;
        let output = Command::new("mkdir").args(["-p", path]).stdout(Stdio::piped()).stderr(Stdio::piped()).output().map_err(|e| ToolError::ExecutionFailed(e.to_string()))?;
        if output.status.success() { Ok(format!("Created directory: {}", path)) } else { Err(ToolError::ExecutionFailed(String::from_utf8_lossy(&output.stderr).to_string())) }
    }

    fn execute_rm(&self, args: &[String]) -> Result<String, ToolError> {
        let path = args.first().ok_or_else(|| ToolError::InvalidArgs("Expected file path".to_string()))?;
        let output = Command::new("rm").args(["-rf", path]).stdout(Stdio::piped()).stderr(Stdio::piped()).output().map_err(|e| ToolError::ExecutionFailed(e.to_string()))?;
        if output.status.success() { Ok(format!("Removed: {}", path)) } else { Err(ToolError::ExecutionFailed(String::from_utf8_lossy(&output.stderr).to_string())) }
    }

    fn execute_cp(&self, args: &[String]) -> Result<String, ToolError> {
        if args.len() < 2 { return Err(ToolError::InvalidArgs("Expected source and destination".to_string())); }
        let output = Command::new("cp").args([&args[0], &args[1]]).stdout(Stdio::piped()).stderr(Stdio::piped()).output().map_err(|e| ToolError::ExecutionFailed(e.to_string()))?;
        if output.status.success() { Ok(format!("Copied {} to {}", args[0], args[1])) } else { Err(ToolError::ExecutionFailed(String::from_utf8_lossy(&output.stderr).to_string())) }
    }

    fn execute_mv(&self, args: &[String]) -> Result<String, ToolError> {
        if args.len() < 2 { return Err(ToolError::InvalidArgs("Expected source and destination".to_string())); }
        let output = Command::new("mv").args([&args[0], &args[1]]).stdout(Stdio::piped()).stderr(Stdio::piped()).output().map_err(|e| ToolError::ExecutionFailed(e.to_string()))?;
        if output.status.success() { Ok(format!("Moved {} to {}", args[0], args[1])) } else { Err(ToolError::ExecutionFailed(String::from_utf8_lossy(&output.stderr).to_string())) }
    }

    fn execute_grep(&self, args: &[String]) -> Result<String, ToolError> {
        if args.len() < 2 { return Err(ToolError::InvalidArgs("Expected pattern and path".to_string())); }
        let output = Command::new("grep").args([&args[0], &args[1]]).stdout(Stdio::piped()).stderr(Stdio::piped()).output().map_err(|e| ToolError::ExecutionFailed(e.to_string()))?;
        Ok(String::from_utf8_lossy(&output.stdout).to_string())
    }

    fn execute_run(&self, args: &[String]) -> Result<String, ToolError> {
        if args.is_empty() { return Err(ToolError::InvalidArgs("Expected command".to_string())); }
        let output = Command::new(&args[0]).args(&args[1..]).stdout(Stdio::piped()).stderr(Stdio::piped()).output().map_err(|e| ToolError::ExecutionFailed(e.to_string()))?;
        if output.status.success() { Ok(String::from_utf8_lossy(&output.stdout).to_string()) } else { Err(ToolError::ExecutionFailed(String::from_utf8_lossy(&output.stderr).to_string())) }
    }

    fn execute_kill(&self, args: &[String]) -> Result<String, ToolError> {
        let pid = args.first().ok_or_else(|| ToolError::InvalidArgs("Expected PID".to_string()))?;
        let output = Command::new("kill").arg(pid).stdout(Stdio::piped()).stderr(Stdio::piped()).output().map_err(|e| ToolError::ExecutionFailed(e.to_string()))?;
        if output.status.success() { Ok(format!("Killed process {}", pid)) } else { Err(ToolError::ExecutionFailed(String::from_utf8_lossy(&output.stderr).to_string())) }
    }

    fn execute_write(&self, args: &[String]) -> Result<String, ToolError> {
        if args.len() < 2 { return Err(ToolError::InvalidArgs("Expected content and path".to_string())); }
        std::fs::write(&args[1], &args[0]).map_err(|e| ToolError::ExecutionFailed(e.to_string()))?;
        Ok(format!("Wrote to {}", args[1]))
    }

    fn get_help(&self) -> String {
        let mut help = String::from("Available tools:\n");
        for tool in self.list_tools() {
            help.push_str(&format!("  {} — {}\n", tool.name, tool.description));
        }
        help
    }
}

impl Default for ToolRegistry {
    fn default() -> Self { Self::new() }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_registry_creation() {
        let registry = ToolRegistry::new();
        assert!(registry.get_tool("ls").is_some());
        assert!(registry.get_tool("cat").is_some());
    }

    #[test]
    fn test_execute_pwd() {
        let registry = ToolRegistry::new();
        assert!(registry.execute("pwd", &[]).is_ok());
    }

    #[test]
    fn test_unknown_tool() {
        let registry = ToolRegistry::new();
        assert!(registry.execute("nonexistent", &[]).is_err());
    }
}
