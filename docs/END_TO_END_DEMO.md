# Bantu-OS — End-to-End Demo Walkthrough

**Version:** 1.0 | **Date:** 2026-04-17 | **Status:** Phase 1 Complete ✅

This document walks you through the complete Bantu-OS architecture and how to run the full system end-to-end.

---

## What is Bantu-OS?

Bantu-OS is a layered, AI-native operating system built on Linux. Instead of starting from kernel space like a traditional OS, it layers intelligent services on top of an existing Linux kernel — putting a personal AI assistant at the center of the experience.

The key differentiator: every layer is independently buildable, testable, and swappable. You can replace the LLM provider, swap the vector store, or rewrite the shell in a different language — without breaking the rest of the system.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│  LAYER 4 — Services (Python)                               │
│  file_service | process_service | network_service          │
├─────────────────────────────────────────────────────────────┤
│  LAYER 3 — AI Engine (Python)                              │
│  Kernel | LLMManager | OpenRouterProvider | Agentic Loop   │
├─────────────────────────────────────────────────────────────┤
│  LAYER 2 — Shell (Rust)                                    │
│  AI REPL | Command Parser | Tool Dispatch                  │
├─────────────────────────────────────────────────────────────┤
│  LAYER 1 — Init System (C)                                 │
│  PID 1 | Service Registry | Signal Handling                │
├─────────────────────────────────────────────────────────────┤
│  BASE — Linux Kernel (Debian-based)                         │
└─────────────────────────────────────────────────────────────┘

Socket Bridge: Layer 2 (Rust) ←→ Layer 3 (Python) via Unix socket /tmp/bantu.sock
```

---

## Component Map

### Layer 1 — C Init System
- **Location:** `init/init.c`
- **Role:** PID 1 process, service registry, signal handling
- **Status:** Compiles, works as standalone C program
- **To build:** `cd init && make`

### Layer 2 — Rust Shell
- **Location:** `shell/src/main.rs`, `parser.rs`, `tools.rs`
- **Role:** AI-powered REPL that accepts natural language commands and routes them to tools or the AI engine
- **Status:** Compiles, 13 tests passing
- **To build:** `cd shell && cargo build`
- **To test:** `cd shell && cargo test`
- **Tool dispatch:** Parses natural language → routes to correct tool (e.g. `show /path` → cat, `where am i` → pwd)
- **AI mode:** Type `ai` to enter AI mode, `ai off` to return to shell mode

### Layer 3 — Python AI Engine
- **Location:** `bantu_os/core/kernel/`
- **Kernel** (`kernel.py`): High-level orchestrator. Provides `process_input()` and `agentic_loop()`
- **LLMManager** (`llm_manager.py`): Manages multiple LLM provider instances and model switching
- **Providers:**
  - `openrouter.py` — OpenAI-compatible API for OpenRouter (DeepSeek, Claude, Llama, Gemini, etc.)
  - `openai_chat.py` — Direct OpenAI API
- **Agentic Loop:** Detects `[TOOL_CALL] name args:{...} [/TOOL_CALL]` in LLM output, executes tools, re-prompts with results
- **Status:** 43 tests passing (kernel, integration, agentic loop)

### Layer 4 — Python Services
- **Location:** `bantu_os/services/`
- **FileService** (`file_service.py`): Read/write/copy/move/delete with safety checks, metadata, SHA256 checksums
- **ProcessService** (`process_service.py`): List processes, start/stop/kill, system resource stats (CPU, memory, disk)
- **NetworkService** (`network_service.py`): HTTP GET/POST, DNS lookup, port checks, local/public IP
- **ServiceBase** (`service_base.py`): Abstract base class with health checks and operation logging

### Memory Layer
- **Location:** `bantu_os/memory/`
- **ChromaVectorStore** (`vector_store.py`): Persistent ChromaDB-backed vector store with in-memory fallback
- **Memory** (`memory.py`): High-level memory orchestrator with embedding support
- **OpenAIEmbeddingsProvider** (`embeddings/openai.py`): Text → vector embedding via OpenAI
- **Status:** 9 ChromaDB tests passing

### Socket Bridge
- **Location:** `bantu_os/core/socket_server.py`
- **Role:** Unix socket server (`/tmp/bantu.sock`) that receives JSON commands from Rust shell and routes them to the Python Kernel
- **Protocol:** JSON over Unix socket — `{cmd: string, text: string, args?: object}`
- **Commands:** `ai` (pass to LLM), `echo` (run tool), any other cmd routed to Kernel

---

## Running the Full System End-to-End

### Prerequisites

```bash
# Install system dependencies
apt install -y python3 python3-venv python3-pip gcc make

# Install Python packages
cd Bantu-Os
pip install -r requirements.txt  # or: pip install chromadb aiohttp psutil pytest pytest-asyncio

# Set your OpenRouter API key (get one at https://openrouter.ai)
export OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxxxxx
```

### Step 1 — Build Rust Shell

```bash
cd shell
cargo build --release
# Binary at: shell/target/release/bantu
```

### Step 2 — Start the Python Socket Server

```bash
cd Bantu-Os
python -m bantu_os.core.socket_server &
# Runs on /tmp/bantu.sock
```

### Step 3 — Run the Rust REPL (Optional)

```bash
./shell/target/release/bantu
# Type 'ai' to enter AI mode
# Type 'ai off' to return to shell mode
```

### Step 4 — Test Directly via Socket

```python
import socket, json

sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
sock.connect('/tmp/bantu.sock')

# Send AI command
msg = json.dumps({'cmd': 'ai', 'text': 'What is 2 + 2?'})
sock.sendall((msg + '\n').encode())
resp = sock.recv(4096).decode()
print(json.loads(resp)['result'])  # → '2 + 2 equals 4.'

sock.close()
```

### Step 5 — Run the Agentic Loop (Tool Calls)

```python
import asyncio
import sys
sys.path.insert(0, '/home/workspace/bantu_os')

from bantu_os.core.kernel import Kernel

async def demo():
    kernel = Kernel(provider='openrouter', provider_model='deepseek-ai/DeepSeek-V3')

    def echo_tool(value: str, times: int = 1) -> str:
        return ' '.join([value] * times)

    kernel.register_tool('echo', echo_tool)

    result = await kernel.agentic_loop(
        text='Use the echo tool to say Bantu-OS is live, 3 times'
    )
    print(result)  # → 'Bantu-OS is live Bantu-OS is live Bantu-OS is live'

asyncio.run(demo())
```

---

## Running Tests

```bash
# Python — all tests
cd Bantu-Os && python -m pytest tests/ -v

# Python — kernel only
python -m pytest tests/kernel/ -v

# Python — memory only
python -m pytest tests/memory/ -v

# Rust — shell
cd shell && cargo test
```

---

## Key Design Decisions

### 1. Unix Socket Bridge (Layer 2 ↔ Layer 3)
The Rust shell and Python kernel communicate via a Unix socket at `/tmp/bantu.sock`. This keeps them decoupled — you can replace either side without breaking the other. The protocol is simple JSON over a byte stream.

### 2. OpenRouter as the LLM Gateway
Instead of hardcoding one LLM, we use OpenRouter as a universal gateway. This gives us access to DeepSeek, Claude, Llama, Gemini, and dozens of other models through a single OpenAI-compatible API. Swap the model by changing one string in `config/settings.py`.

### 3. Agentic Loop as a Kernel Method
Tool use isn't a separate framework — it's built into the Kernel class. The `_parse_tool_calls()` static method extracts `[TOOL_CALL] name args:{...} [/TOOL_CALL]` patterns from LLM output, and `agentic_loop()` executes them and re-prompts automatically.

### 4. ChromaDB as the Default Vector Store
The `ChromaVectorStore` class wraps ChromaDB in the `VectorStore` abstraction. If ChromaDB isn't available (not installed or fails), it falls back to the in-memory `VectorDBStore`. Swapping to FAISS or Qdrant later requires only changing the store class.

### 5. Tool Dispatch in Rust
The Rust shell parses natural language commands using `parser.rs` and dispatches to the correct tool based on keyword matching and argument inspection. This is what makes `show /path` route to `cat` instead of `ls` — it inspects whether the first argument looks like a path.

---

## Project Stats

| Metric | Count |
|--------|-------|
| Total PRs merged | 9 |
| Rust tests | 13 passing |
| Python kernel tests | 43 passing |
| ChromaDB memory tests | 9 passing |
| Layers complete | 4 of 4 |
| Providers | OpenRouter ✅, OpenAI ✅ |

---

## What's Next (Phase 2)

1. Wire Rust shell directly into the socket server (type `ai hello` in REPL → get DeepSeek response)
2. Add memory persistence — survive restarts
3. CI/CD — run all tests on every PR automatically
4. C init integration — wire service registry into the C init system

---

*Africa-born. World-class. Bantu-OS is more than technology — it's a statement that the future can come from here.*