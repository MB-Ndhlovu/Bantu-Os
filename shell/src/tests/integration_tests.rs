//! Integration tests for bantu-shell

use bantu_shell::parser;
use bantu_shell::tools::ToolRegistry;

#[test]
fn test_integration_list_command() {
    let registry = ToolRegistry::new();
    let result = parser::parse("list files");
    assert!(result.is_ok());
    let call = result.unwrap();
    let output = registry.execute(&call.tool, &call.args);
    assert!(output.is_ok());
}

#[test]
fn test_integration_cat_command() {
    let registry = ToolRegistry::new();
    let result = parser::parse("cat /etc/hostname");
    assert!(result.is_ok());
    let call = result.unwrap();
    assert_eq!(call.tool, "cat");
}

#[test]
fn test_integration_ps_command() {
    let registry = ToolRegistry::new();
    let result = parser::parse("show processes");
    assert!(result.is_ok());
    let call = result.unwrap();
    assert_eq!(call.tool, "ps");
}

#[test]
fn test_natural_language_parsing() {
    let test_cases = vec![
        ("list files", "ls"),
        ("show running processes", "ps"),
        ("cat /etc/passwd", "cat"),
        ("where am i", "pwd"),
        ("who is the user", "whoami"),
        ("show", "ls"),
        ("show ./some/path", "cat"),
        ("where is file.txt", "grep"),
    ];
    
    for (input, expected_tool) in test_cases {
        let result = parser::parse(input);
        assert!(result.is_ok(), "Failed to parse: {}", input);
        let call = result.unwrap();
        assert_eq!(call.tool, expected_tool, "Failed for input: {}", input);
    }
}
