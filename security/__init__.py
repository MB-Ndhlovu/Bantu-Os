"""
Bantu-OS Security Primitives

This package provides security-critical functionality for Bantu-OS:
- secrets: Secure secrets management
- sanitizer: Input sanitization for prompt injection defense
- privilege: Privilege model and action classification
"""

from security.secrets import SecretsManager, get_secret, get_manager
from security.sanitizer import (
    InputSanitizer,
    SanitizeResult,
    ValidationResult,
    sanitize,
    SanitizerError,
    InputTooLongError,
    ControlCharacterError,
    InjectionDetectedError,
    PathTraversalError,
)
from security.privilege import (
    PrivilegeModel,
    PrivilegeLevel,
    Action,
    requires_confirmation,
    is_allowed,
)

__all__ = [
    # Secrets
    "SecretsManager",
    "get_secret",
    "get_manager",
    # Sanitizer
    "InputSanitizer",
    "SanitizeResult",
    "ValidationResult",
    "sanitize",
    "SanitizerError",
    "InputTooLongError",
    "ControlCharacterError",
    "InjectionDetectedError",
    "PathTraversalError",
    # Privilege
    "PrivilegeModel",
    "PrivilegeLevel",
    "Action",
    "requires_confirmation",
    "is_allowed",
]
