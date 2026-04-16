# Bantu-OS Security Model

## Threat Model

### Overview
Bantu-OS is an AI-native operating system where an AI assistant (JARVIS) operates with elevated privileges to manage system resources, execute tools, and interact with external services on behalf of the user. The threat model addresses the unique risks of this architecture.

### Trust Boundaries

| Zone | Description | Trust Level |
|------|-------------|-------------|
| User | Human operator at the CLI/interface | Trusted |
| AI Assistant (JARVIS) | Autonomous agent with tool access | Semi-trusted |
| Tool Dispatch | Executes AI-decided actions on system | Delegated trust |
| External Services | APIs, web, filesystem | Untrusted |
| Root/Host | System-level operations | Highest privilege |

### Threat Vectors

1. **Prompt Injection**: Malicious instructions injected into AI context to escalate privileges or exfiltrate data
2. **Tool Abuse**: AI assistant requesting excessive or destructive tool operations
3. **Credential Exfiltration**: API keys or secrets exposed through AI responses or logs
4. **Input Pollution**: Unsanitized user input propagating through AI tool dispatch
5. **Context poisoning**: Long-term memory or knowledge graph manipulation
6. **Third-party compromise**: External services being attacked leading to key exposure

### Attack Surface

- **User → AI**: Conversation context (potential injection)
- **AI → Tools**: Action dispatch layer (potential abuse)
- **Tools → System**: Filesystem, network, process execution
- **External → System**: Web content, downloaded files

---

## Privilege Model

### Permission Tiers

```
┌─────────────────────────────────────────────┐
│  USER                                       │
│  - Full control over AI behavior            │
│  - Can override any AI decision             │
│  - Explicit consent for dangerous ops       │
└─────────────────────────────────────────────┘
          │
          ▼ grants permission
┌─────────────────────────────────────────────┐
│  AI ASSISTANT (JARVIS)                      │
│  - Manages system on user's behalf          │
│  - Can call tools autonomously              │
│  - Cannot escalate to raw root directly     │
│  - Operates within constraints               │
└─────────────────────────────────────────────┘
          │
          ▼ via tool dispatch
┌─────────────────────────────────────────────┐
│  PROCESS-LEVEL (AI tools)                   │
│  - File operations (scoped to workspace)    │
│  - Network requests (external APIs)         │
│  - Process spawning (sandboxed)             │
└─────────────────────────────────────────────┘
          │
          ▼ privileged operations
┌─────────────────────────────────────────────┐
│  ROOT                                        │
│  - System package management                │
│  - Service management                       │
│  - User account control                     │
│  - Requires explicit user confirmation      │
└─────────────────────────────────────────────┘
```

### Privilege Levels

| Level | Identity | Can Do | Cannot Do |
|-------|----------|--------|-----------|
| 0 | Anonymous | View public docs, basic chat | Access user data, execute tools |
| 1 | Authenticated User | Full AI interaction, tool use | Root/system modification |
| 2 | AI Assistant (agent) | Tool execution, memory access | Direct root escalation |
| 3 | System (root) | Package install, service control | Bypass confirmation |

---

## API Key Handling Guidelines

### Classification

| Key Type | Risk Level | Handling |
|----------|------------|----------|
| LLM Provider Keys | Critical | Never log, never expose to AI |
| External Service Keys | High | Scope to minimum required |
| User OAuth Tokens | High | Encrypted at rest, refresh rotation |
| Internal Service Keys | Medium | Isolated to service-to-service |

### Storage Rules

1. **Secrets must NEVER appear in**:
   - AI conversation context
   - Log files (structured or unstructured)
   - Error messages returned to user
   - Unencrypted storage

2. **Key Access Pattern**:
   ```
   AI requests tool → Tool validates need → 
   Key fetched from secrets manager → 
   Used in API call → 
   Never returned to AI or logged
   ```

3. **Key Rotation**:
   - All keys must be rotatable without code changes
   - Rotation should not disrupt active sessions
   - Old keys invalidated after grace period

4. **Key Scoping**:
   - External API keys stored per-user or per-workspace
   - Service-to-service keys isolated to specific capabilities
   - No wildcard or overly permissive keys

---

## Input Sanitization Rules for AI Tool Dispatch

### Pipeline Overview

```
User Input → Context Building → AI Reasoning → Tool Selection → 
Input Validation → Tool Execution → Output Sanitization → User
```

### Sanitization Rules

#### 1. Path Inputs (Filesystem Tools)
```python
# ALLOWED: Controlled workspace paths only
- Must resolve within /home/workspace or /home/.z
- No symlink traversal (.. escape)
- No null bytes or encoding attacks
- Filenames: alphanumeric, dash, underscore, dot only
```

#### 2. URL Inputs (Network Tools)
```python
# ALLOWED: HTTP/HTTPS only (no file://, ftp://)
- Block localhost/internal network access
- Block authentication in URLs
- Validate URL encoding
- Domain allowlist where applicable
```

#### 3. Command Inputs (Shell/Process Tools)
```python
# ALLOWED: Strict argument lists only
- No shell interpolation ($(), ||, &&)
- No environment variable injection
- No pipe/redirection characters in args
- Args must be list of strings, not shell string
```

#### 4. Tool Name Validation
```python
# ALLOWED: Only registered tool names
- Validate against registered tool registry
- No dynamic tool construction from user input
- Tool aliases resolved to canonical names
```

#### 5. Content Length Limits
```python
# Enforce maximum input sizes per tool
- File paths: 4096 chars max
- URLs: 2048 chars max
- Command args: 65536 chars max
- Content payloads: 16MB max (configurable)
```

### Reject Conditions

Any of the following triggers automatic rejection:
- Null bytes (`\u0000`)
- Path traversal attempts (`../`, `..\\`)
- Shell metacharacters in argument contexts
- Attempted injection patterns (`{{`, `${`, `<%`)
- Encoding anomalies (overlong UTF-8, BOM)

---

## Secrets Management Approach

### Architecture

```
┌─────────────────────────────────────────────────────┐
│              Secrets Manager (basic_secrets.py)      │
│                                                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐           │
│  │  Env     │  │  File    │  │  API     │           │
│  │  Vars    │  │  (AES)   │  │  Keys    │           │
│  └──────────┘  └──────────┘  └──────────┘           │
└─────────────────────────────────────────────────────┘
           │            │            │
           ▼            ▼            ▼
        Encrypted storage with access control
```

### Principles

1. **Defense in Depth**: Secrets stored with multiple layers of protection
2. **Least Privilege**: Tool access to secrets requires explicit permission
3. **Audit Trail**: All secret access logged (key name, tool, timestamp)
4. **Encryption at Rest**: Sensitive values encrypted with AES-256-GCM
5. **Zero Retention**: Secret values cleared from memory after use

### Implementation Requirements

```python
# basic_secrets.py must provide:
- get_secret(name: str) -> str | None  # Fetches decrypted value
- set_secret(name: str, value: str) -> bool  # Stores encrypted
- delete_secret(name: str) -> bool  # Irreversibly removes
- list_secrets() -> list[str]  # Returns names only (no values)
- rotate_secret(name: str) -> bool  # Re-encrypts with new key
```

### Security Properties

| Property | Requirement |
|----------|-------------|
| Encryption | AES-256-GCM with unique IV per encryption |
| Key Derivation | PBKDF2 with min 100,000 iterations |
| Memory Safety | Secrets zeroed after use (where possible) |
| Access Control | Capability-based, not role-based |
| Rotation | Support non-disruptive key rotation |

---

## Incident Response

### Suspected Compromise Actions

1. **Immediate**: Revoke exposed secrets via secrets manager
2. **Short-term**: Audit logs for access patterns, identify scope
3. **Recovery**: Rotate all potentially affected keys
4. **Post-incident**: Review injection points, update sanitization rules

### Security Contacts

For vulnerabilities or security concerns, contact the Bantu-OS security team through official channels.