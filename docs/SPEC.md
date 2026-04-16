# Bantu-OS — Technical Specification

## 1. Project Overview

**Bantu-OS** is an AI-native personal operating system designed from the ground up for the AI era.

Unlike legacy operating systems that bolt-on AI as an afterthought, Bantu-OS places the LLM at the core of the OS — making your personal AI the primary interface and executive partner of your digital life.

### Core Pillars

| Pillar | Description |
|--------|-------------|
| **AI-Native** | LLM is the OS kernel; every operation is AI-mediated |
| **Lightweight** | Runs on modern and low-power devices; minimal resource footprint |
| **Resilient** | Works offline and online; bridges connectivity gaps |
| **Globally Inclusive** | Born in Africa, built for the world |

### Repository

```
https://github.com/MB-Ndhlovu/Bantu-Os
```

---

## 2. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     USER INTERFACE LAYER                     │
│                 (CLI Shell, Voice Hooks, Text)              │
├─────────────────────────────────────────────────────────────┤
│                    AGENT ORCHESTRATION LAYER                 │
│          (SchedulingAgent, TaskManager, BaseAgent)         │
├─────────────────────────────────────────────────────────────┤
│                      CORE SERVICES LAYER                      │
│        (Kernel, LLM Manager, System Services, API Base)      │
├─────────────────────────────────────────────────────────────┤
│                      MEMORY LAYER                             │
│        (VectorDB, KnowledgeGraph, Embeddings)               │
├─────────────────────────────────────────────────────────────┤
│                   INFRASTRUCTURE LAYER                       │
│     (Python Runtime, Linux Kernel, Config, Logging)         │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Layer Descriptions

### Layer 0 — Infrastructure

The foundation that everything runs on.

| Component | Language | Description |
|-----------|----------|-------------|
| Linux Kernel | C | System-level operations, device management |
| Python Runtime | Python | Core OS logic, agent system, memory management |
| Poetry | Python | Dependency management |
| Logging System | Python | Structured logging via `logging.conf` |

### Layer 1 — Memory

Persistent storage and retrieval systems.

| Component | Language | Description |
|-----------|----------|-------------|
| `vector_db.py` | Python | ChromaDB vector store for semantic search |
| `knowledge_graph.py` | Python | Structured knowledge representation |
| `embeddings/base.py` | Python | Embedding protocol (OpenAI adapter) |
| `embeddings/openai.py` | Python | OpenAI embedding implementation |

### Layer 2 — Core Services

The kernel and service orchestration.

| Component | Language | Description |
|-----------|----------|-------------|
| `kernel.py` | Python | Central OS kernel, agent pipeline orchestration |
| `llm_manager.py` | Python | LLM lifecycle management (load, inference, swap) |
| `services.py` | Python | System service registry and lifecycle |
| `providers/base.py` | Python | Abstract LLM provider interface |
| `providers/openai_chat.py` | Python | OpenAI Chat API provider implementation |

### Layer 3 — Agent Orchestration

AI agents that plan, schedule, and execute.

| Component | Language | Description |
|-----------|----------|-------------|
| `base_agent.py` | Python | Base class for all agents |
| `scheduling_agent.py` | Python | Time-aware task scheduling agent |
| `task_manager.py` | Python | Task queue, persistence, and execution |
| `agent_manager.py` | Python | Agent lifecycle and coordination |
| `api/base_api.py` | Python | Abstract API handler for tool integrations |

### Layer 4 — User Interface

Human-facing interaction points.

| Component | Language | Description |
|-----------|----------|-------------|
| `cli/shell.py` | Python | Interactive CLI shell |
| `cli/commands.py` | Python | CLI command definitions |
| `hooks/text.py` | Python | Text input/output hooks |
| `hooks/voice.py` | Python | Voice interface hooks (future) |

---

## 4. Language Breakdown

| Language | Use Case | Count (est.) |
|----------|----------|-------------|
| **Python** | Core logic, agents, memory, interface, config | ~85% |
| **C** | Linux kernel, low-level system calls | ~10% |
| **Rust** | Planned for future performance-critical paths | ~5% (future) |

---

## 5. Phase 1 Feature List

**Phase 1 — Foundation: OS Core + AI Assistant MVP**

### Target: MVP deliverable

- [ ] **Kernel Core**
  - LLM Manager with OpenAI provider
  - Base kernel orchestrating agent pipeline
  - System service registry

- [ ] **Agent System**
  - BaseAgent abstract class
  - SchedulingAgent with cron-based scheduling
  - TaskManager with persistent task queue
  - AgentManager for lifecycle coordination

- [ ] **Memory System**
  - ChromaDB vector database integration
  - KnowledgeGraph for structured memory
  - OpenAI embeddings (text-embedding-ada-002)

- [ ] **CLI Interface**
  - Interactive shell (`shell.py`)
  - Core commands (`commands.py`)
  - Text hooks for input/output

- [ ] **Tool System**
  - Calculator tool
  - File manager tool
  - Filesystem tool
  - Web search tool
  - Browser tool
  - Scheduler tool

- [ ] **Configuration**
  - JSON-based settings (`settings.json`)
  - Settings manager (`settings_manager.py`)
  - Structured logging (`logging.conf`)

- [ ] **Testing**
  - Unit tests for scheduling_agent (30 passing)
  - Unit tests for task_manager (8 passing)
  - Unit tests for llm_manager (11 passing)
  - Kernel async tool pipeline tests
  - Memory system tests

---

## 6. Contributing Guide (Excerpt)

### Quick Start

```bash
# 1. Fork and clone
git clone https://github.com/<your-username>/Bantu-Os.git
cd Bantu-Os

# 2. Install dependencies
poetry install

# 3. Configure environment
cp .env.template .env
# Edit .env with your API keys

# 4. Run the shell
poetry run python -m bantu_os.interface.cli.shell

# 5. Run tests
poetry run pytest
```

### Commit Workflow

Every contributor follows this cycle:

```
git pull origin main   # Always start fresh
→ Make changes
git add .
git commit -m "descriptive message"
git push origin main
```

### Code Standards

- Type hints on all function signatures
- Docstrings on public classes and methods
- One logical change per commit
- Tests must pass before push

### Areas Needing Help

| Priority | Area | Notes |
|----------|------|-------|
| 🔴 High | Kernel tests | Pipeline coverage needed |
| 🔴 High | Memory tests | ChromaDB + KG coverage |
| 🟡 Medium | CLI commands | Shell integration incomplete |
| 🟡 Medium | Real API provider | Currently mock mode |
| 🟢 Low | Voice hooks | Future-facing |

---

## 7. Roadmap

```
Phase 1: Foundation (NOW)
  └── OS Core + AI Assistant MVP
      ├── Kernel + LLM Manager ✅ (in progress)
      ├── Agent System ✅ (in progress)
      ├── Memory Layer 🔄 (in progress)
      ├── CLI Interface 🔄 (in progress)
      └── Testing 🔄 (in progress)

Phase 2: Connectivity
  └── Messaging, Banking, Crypto Integrations
      ├── Payment APIs (Stripe, PayPal)
      ├── Crypto wallet integration
      ├── Messaging (Telegram, WhatsApp)
      └── Banking aggregation

Phase 3: Ecosystem
  └── IoT & Smart Devices
      ├── IoT agent for device control
      ├── Hardware prototype (ESP32)
      └── Smart home hub integration

Phase 4: Scale
  └── Enterprise + Global Rollout
      ├── Multi-tenant architecture
      ├── Enterprise licensing
      ├── Mobile OS (Android, iOS)
      └── App store ecosystem
```

---

*Last updated: 2026-04-16*