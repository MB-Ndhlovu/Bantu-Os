# Security module for Bantu-OS
# Provides secrets management, input sanitization, and privilege model

from .secrets import (
    SecretsVault,
    get_vault,
    get_secret,
    set_secret,
    delete_secret,
    list_secrets,
    get_audit_log,
)

from .sanitizer import (
    SanitizationError,
    sanitize_path,
    sanitize_url,
    sanitize_cmd_arg,
    sanitize_cmd_args,
    sanitize_tool_args,
    sanitize_tool_name,
    sanitize_prompt,
    sanitize_content,
)

from .privilege import (
    PrivilegeLevel,
    PrivilegeResult,
    get_privilege,
    check_privilege,
    set_privilege,
    require_confirmation,
    is_allowed,
)

__all__ = [
    # Secrets
    "SecretsVault",
    "get_vault",
    "get_secret",
    "set_secret",
    "delete_secret",
    "list_secrets",
    "get_audit_log",
    # Sanitizer
    "SanitizationError",
    "sanitize_path",
    "sanitize_url",
    "sanitize_cmd_arg",
    "sanitize_cmd_args",
    "sanitize_tool_args",
    "sanitize_tool_name",
    "sanitize_prompt",
    "sanitize_content",
    # Privilege
    "PrivilegeLevel",
    "PrivilegeResult",
    "get_privilege",
    "check_privilege",
    "set_privilege",
    "require_confirmation",
    "is_allowed",
]