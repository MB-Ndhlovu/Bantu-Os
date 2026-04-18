# Bantu-OS Security Architecture

## 1. Threat Model

### Adversaries We Defend Against

| Threat | Attack Vector | Impact |
|--------|--------------|--------|
| **Prompt Injection** | Malicious user input crafted to manipulate AI behavior | Unauthorized actions, data exfiltration |
| **Secrets Exfiltration** | Stealing API keys, tokens, credentials from memory/disk | Account compromise, financial loss |
| **Privilege Escalation** | AI or process gaining capabilities beyond its role | System compromise, lateral movement |
| **IPC Spoofing** | Attacker interposing between Rust shell and Python engine | Command injection, data manipulation |
| **Boot Path Attack** | Compromising initramfs, kernel, or early userspace | Persistent rootkit, full system control |
| **Data Leakage** | AI inadvertently exposing sensitive context | Privacy violation, compliance breach |

### Trust Boundaries

```
[Hardware/TPM] ---> [Boot Loader] ---> [Kernel] ---> [Init] ---> [Rust Shell]
                                                                  |
                                                                  v
                                                         [Python Engine]
                                                                  |
                                                     [Services & AI Tools]
```

Each boundary assumes the prior layer is trusted. A compromise at any layer invalidates guarantees from layers below.

---

## 2. Privilege Model

### Capability Roles

| Role | Read FS | Write FS | Execute | Network | AI Actions | User Confirm Required |
|------|---------|----------|---------|---------|------------|-----------------------|
| **User** | `~/` | `~/` | Own files | Full | No | — |
| **AI Shell (Rust)** | Limited | Restricted | No | Outbound only | Yes | See below |
| **AI Engine (Python)** | Service dirs | Service dirs | No | Outbound only | Yes | Yes for privileged ops |
| **System Services** | `/opt/bantu/` | `/opt/bantu/` | No | Configured | No | No |

### AI Action Classification

**Auto-approve (no confirmation):**
- Read public documentation
- General knowledge queries
- Displaying the user's own files
- Calculations and transformations on user data

**Confirm-first (user must approve):**
- File operations outside `~/`
- Network requests to third-party APIs
- Running executables or scripts
- Accessing credential stores
- Creating or modifying system configuration
- Sending data external to the OS

**Never-allowed:**
- Disabling security controls
- Modifying the boot chain
- Extracting or exfiltrating secrets
- Privilege escalation attempts

---

## 3. Secrets Management

### Guiding Principles

1. **No hardcoding** — Zero secrets in source code, ever.
2. **Defense in depth** — Environment variables + optional encrypted storage.
3. **Least privilege** — Each component gets only the secrets it needs.
4. **Memory safety** — Secrets cleared from memory after use.

### Secret Sources (in priority order)

1. **Environment variables** — Set by the shell before process start. Preferred for deployment.
2. **Encrypted secrets file** — `~/.bantu/secrets.enc` (AES-256-GCM). Key derived from user's auth token via Argon2id.
3. **TPM-backed keystore** — For hardware with TPM 2.0. Keys never leave the TPM.

### Access Pattern

```python
# security/secrets.py
def get_secret(name: str) -> str | None:
    """
    Retrieve a secret by name.
    1. Check environment variable BANTU_SECRET_<NAME>
    2. Check encrypted secrets file (if unlocked)
    3. Return None if not found
    """
```

### Stored Secrets

| Secret | Storage | Access |
|--------|---------|--------|
| AI API keys | Env or encrypted file | Python engine only |
| User auth tokens | Encrypted file | Rust shell + Python engine |
| Service credentials | Env or encrypted file | Respective service |

---

## 4. Input Sanitization (Prompt Injection Defense)

### Attack Surface

User input flows through the Rust shell to the Python AI engine. Each hop is an injection vector.

### Defense Layers

**Layer 1: Syntax Filtering (Rust shell)**
- Reject input containing null bytes or control characters
- Length limit: 64,000 characters per command
- Detect and escape prompt injection delimiters (`---`, `===`, `###`)

**Layer 2: Semantic Filtering (Python engine)**
- AI is provided a system prompt that defines its **implicit persona and hard limits**. This prompt is isolated and never user-controlled.
- User input is wrapped in a `user:` turn and prepended with a **context prefix** that reminds the AI of its constraints.
- The AI is explicitly instructed to refuse instruction overrides.

**Layer 3: Output Validation (Python engine)**
- AI responses that reference internal paths or secrets are redacted before display.
- Structured outputs (JSON, code) are validated against a schema before execution.

### Injection Pattern Detection

```python
# security/sanitizer.py
INJECTION_PATTERNS = [
    r"---[\s]*system[\s]*---",
    r"===[\s]*instruction",
    r"###[\s]*(system|admin|root)",
    r"<system>",
    r"{{[\s]*system[\s]*}}",
]
```

Any match causes the input to be rejected with a security warning.

---

## 5. IPC Security (Rust ↔ Python Communication)

### Transport

- **Unix domain sockets** — Not network-accessible. Path: `/tmp/bantu.sock`.
  - Permissions: `0700` owner-only.
- **TCP socket** (future multi-client): `127.0.0.1:18792`.

### Protocol

- **JSON** serialization — Line-delimited JSON messages (no external serialization library).
- **Schema-validated messages** — Each message type has a rigid schema (`cmd`, `tool`, `method`, `args`).
- **No eval()** — Commands are dispatched via a fixed match table in the Python kernel, not dynamic execution.

### Security Properties (Aspirational)

The following security properties are **planned** but not yet implemented:

| Property | Status | Mechanism |
|----------|--------|-----------|
| **Authenticity** | 🔲 Planned | HMAC-SHA256 per-session key |
| **Integrity** | 🔲 Planned | HMAC prevents tampering |
| **Non-replay** | 🔲 Planned | Nonce + sliding window |
| **Isolation** | ✅ Current | Unix socket scoped to user session |

### Message Flow (Current)

```
User Input
    |
    v
Rust Shell  ---- JSON line ----> Python Kernel (socket_server.py)
    |                                           |
    | <------- JSON response --------          |
    v                                           v
Display                                      Execute
```

**Note:** HMAC signing and replay protection are not yet implemented. The current socket uses `0700` permissions for isolation. These are planned enhancements for production hardening.

### What's NOT Protected (Known Gaps)

- HMAC/MsgPack security layer — planned, not yet built
- Replay attack protection — planned, not yet built
- Full disk encryption (FDE) — planned, not yet implemented
- Remote attestation via TPM — planned, not yet implemented

---

## 6. Boot Integrity

### Boot Chain

```
TPM (PCRs)
    |
    v
Boot Loader (GRUB with secure boot)
    |
    v
Kernel (signed, + dm-verity if root is read-only)
    |
    v
Initramfs (checked via SHA-256 hash)
    |
    v
Systemd (system slice isolation)
    |
    v
Bantu-OS Services
```

### Guarantees

| Component | Protection | Verification |
|-----------|-------------|---------------|
| Boot Loader | UEFI Secure Boot + GRUB signed | PCR 0-7 extend |
| Kernel | Signed kernel image | dm-verity on root |
| Initramfs | Hash stored in TPM PCR | Measured boot |
| OS Services | cgroups + namespacing | Kernel enforcement |

### What's NOT Protected (Known Gaps)

- The initramfs hash is checked but not yet signed.
- PCR renewal on kernel update requires manual intervention.
- Full disk encryption (FDE) is planned but not yet implemented.

### Attestation

Remote attestation via TPM quote is planned for future releases to verify boot state to a remote server.

---

## 7. Security Principles Summary

1. **Zero trust** — Every input is untrusted until validated.
2. **Least privilege** — Every component gets minimum capabilities.
3. **Defense in depth** — Multiple independent security layers.
4. **Fail-safe defaults** — Unknown input → reject, not allow.
5. **Auditability** — Security events are logged (when implemented).
6. **Transparency** — Security architecture is documented and open.

---

*Document version: 1.0 | Last updated: 2026-04-17*
