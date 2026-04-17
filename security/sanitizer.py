"""
Bantu-OS Input Sanitizer

Provides defense-in-depth against prompt injection attacks.

Layer 1 (Rust shell): Syntax filtering, length limits, control char rejection
Layer 2 (Python engine): Semantic context injection, delimiter escaping
Layer 3 (Python engine): Output redaction
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional


# === Constants ===

MAX_INPUT_LENGTH = 64_000
MAX_LINE_LENGTH = 10_000

# Prompt injection delimiters — patterns that attempt to override system behavior
INJECTION_PATTERNS = [
    re.compile(r"---[\s]*system[\s]*---", re.IGNORECASE),
    re.compile(r"===[\s]*(instruction|system|admin)[\s]*===", re.IGNORECASE),
    re.compile(r"###[\s]*(system|admin|root|override)[\s]*###", re.IGNORECASE),
    re.compile(r"<system>", re.IGNORECASE),
    re.compile(r"{{[\s]*system[\s]*}}", re.IGNORECASE),
    re.compile(r"\[SYSTEM\]", re.IGNORECASE),
    re.compile(r"^\s*SYSTEM\s*:", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^__system__\s*:", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^ROOT\s*:", re.IGNORECASE | re.MULTILINE),
]

# Control characters that should never appear in valid user input
CONTROL_CHARS = re.compile(
    r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]"
)

# Paths that should never be exposed to or manipulable by user input
INTERNAL_PATHS = re.compile(
    r"(\.bantu|/run/bantu|/etc/bantu-secrets|\.bashrc|\.profile)"
)


class SanitizerError(Exception):
    """Base exception for sanitizer errors."""
    pass


class InputTooLongError(SanitizerError):
    """Input exceeds maximum allowed length."""
    pass


class ControlCharacterError(SanitizerError):
    """Input contains forbidden control characters."""
    pass


class InjectionDetectedError(SanitizerError):
    """Input matches known prompt injection pattern."""
    pass


class PathTraversalError(SanitizerError):
    """Input attempts to access internal paths."""
    pass


class ValidationResult(Enum):
    """Result of input validation."""
    VALID = auto()
    REJECTED = auto()
    ESCAPED = auto()


@dataclass
class SanitizeResult:
    """Result of sanitization."""
    status: ValidationResult
    cleaned_input: str
    warnings: list[str]

    @property
    def is_valid(self) -> bool:
        return self.status != ValidationResult.REJECTED


def detect_injection(text: str) -> Optional[re.Match]:
    """
    Check if text matches known injection patterns.

    Returns:
        Match object if injection detected, None otherwise.
    """
    for pattern in INJECTION_PATTERNS:
        match = pattern.search(text)
        if match:
            return match
    return None


def contains_control_chars(text: str) -> bool:
    """Check if text contains forbidden control characters."""
    return bool(CONTROL_CHARS.search(text))


def contains_internal_paths(text: str) -> bool:
    """Check if text references internal system paths."""
    return bool(INTERNAL_PATHS.search(text))


def strip_unicode_overlong(text: str) -> str:
    """
    Reject or normalize overlong UTF-8 representations.
    These can be used to bypass pattern matching.
    """
    # Normalize to NFC form
    normalized = unicodedata.normalize("NFC", text)
    # Check for null bytes (even in composed form)
    if "\x00" in normalized:
        raise ControlCharacterError("Null byte detected")
    return normalized


class InputSanitizer:
    """
    Multi-layer input sanitizer for prompt injection defense.

    Layer 1: Fast rejection of obviously malicious patterns
    Layer 2: Context-aware cleaning with warnings
    Layer 3: Path and internal reference validation
    """

    def __init__(
        self,
        max_length: int = MAX_INPUT_LENGTH,
        reject_injection: bool = True,
        reject_control_chars: bool = True,
    ):
        self.max_length = max_length
        self.reject_injection = reject_injection
        self.reject_control_chars = reject_control_chars

    def sanitize(self, raw_input: str) -> SanitizeResult:
        """
        Sanitize user input.

        Args:
            raw_input: The raw user input string.

        Returns:
            SanitizeResult with status, cleaned input, and any warnings.
        """
        warnings: list[str] = []

        # --- Pre-checks ---

        if not isinstance(raw_input, str):
            raw_input = str(raw_input)

        # Normalize unicode
        try:
            raw_input = strip_unicode_overlong(raw_input)
        except ControlCharacterError:
            if self.reject_control_chars:
                raise

        # Length check
        if len(raw_input) > self.max_length:
            if self.reject_control_chars:
                raise InputTooLongError(
                    f"Input too long: {len(raw_input)} > {self.max_length}"
                )
            warnings.append(f"Input truncated from {len(raw_input)} to {self.max_length}")
            raw_input = raw_input[: self.max_length]

        # Control character check
        if contains_control_chars(raw_input):
            if self.reject_control_chars:
                raise ControlCharacterError(
                    "Input contains forbidden control characters"
                )
            warnings.append("Control characters removed")
            raw_input = CONTROL_CHARS.sub("", raw_input)

        # Injection pattern check
        injection_match = detect_injection(raw_input)
        if injection_match:
            if self.reject_injection:
                raise InjectionDetectedError(
                    f"Prompt injection pattern detected: '{injection_match.group()}'"
                )
            warnings.append("Potential injection pattern escaped")
            # Escape rather than remove — preserves user intent for false positives
            raw_input = self._escape_injection_delimiters(raw_input, injection_match)

        # Internal path check
        if contains_internal_paths(raw_input):
            raise PathTraversalError(
                "Input references internal system paths"
            )

        return SanitizeResult(
            status=ValidationResult.VALID,
            cleaned_input=raw_input,
            warnings=warnings,
        )

    def _escape_injection_delimiters(
        self, text: str, injection_match: re.Match
    ) -> str:
        """
        Escape injection delimiters by adding zero-width space.
        Preserves the text but breaks pattern matching.
        """
        escaped = text
        # Add zero-width space after suspected delimiter to break pattern
        for pattern in INJECTION_PATTERNS:
            escaped = pattern.sub(lambda m: m.group() + "\u200b", escaped)
        return escaped

    def validate_output(self, output: str) -> str:
        """
        Validate and redact AI output.

        Removes references to internal paths and secret patterns.
        """
        redacted = output

        # Remove internal path references
        redacted = INTERNAL_PATHS.sub("[internal path redacted]", redacted)

        # Remove potential secret patterns (base64-looking strings that are 40+ chars)
        redacted = re.sub(
            r"[A-Za-z0-9+/]{40,}={0,2}",
            lambda m: "[value redacted]" if len(m.group()) >= 40 else m.group(),
            redacted,
        )

        return redacted


# Global instance
_default_sanitizer: Optional[InputSanitizer] = None


def get_sanitizer() -> InputSanitizer:
    """Get the default sanitizer instance."""
    global _default_sanitizer
    if _default_sanitizer is None:
        _default_sanitizer = InputSanitizer()
    return _default_sanitizer


def sanitize(raw_input: str) -> SanitizeResult:
    """Convenience function to sanitize input using default sanitizer."""
    return get_sanitizer().sanitize(raw_input)
