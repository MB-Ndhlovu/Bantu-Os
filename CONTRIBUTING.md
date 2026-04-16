# Contributing to Bantu-OS

Welcome. We're building something real — a Linux-based, AI-native operating system from Africa, for the world. This guide will get you set up and productive fast.

> ⚡ **First time contributing?** Pick up an issue labeled `good first issue` or `help wanted`. If anything is unclear, open an issue. We're a small team and we want contributors, not confused contributors.

---

## 🏗️ Development Setup

### Prerequisites

- Linux (Debian/Ubuntu) — Bantu-OS is built on Linux
- Python 3.10+
- Rust 1.70+ (for the shell layer)
- GCC
- Git

### 1. Fork & Clone

```bash
# Fork on GitHub, then clone YOUR fork
git clone https://github.com/YOUR_USERNAME/Bantu-Os.git
cd Bantu-Os
```

### 2. Add Upstream

```bash
git remote add upstream https://github.com/MB-Ndhlovu/Bantu-Os.git
```

### 3. Install Python Dependencies

```bash
pip install -e .
# or with poetry:
poetry install
```

### 4. Build Each Layer

```bash
# Layer 1 — C Init System
cd init && make

# Layer 2 — Rust Shell
cd ../shell && cargo build --release

# Back to root
cd ..
```

### 5. Run Tests

```bash
# Python tests
python -m pytest tests/ -v

# C init compilation test
cd init && make test
```

---

## 🔧 Coding Standards

### Python

- Follow PEP 8
- Use type hints on all function signatures
- Every new module needs a docstring
- Tests must pass before merging: `python -m pytest tests/ -v`

### C

- Follow C11 standard
- Use `-Wall -Wextra -pedantic` without warnings
- All functions must be documented
- Signal-safe code only in signal handlers

### Rust

- Follow `rustfmt` (run `cargo fmt` before committing)
- No `unsafe` blocks without a comment explaining why
- All public API items need doc comments

### Commit Messages

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**Types:** `feat` | `fix` | `docs` | `test` | `refactor` | `chore`

**Examples:**
```
feat(init): add service restart command
fix(scheduler): correct timezone handling in parse_natural_time
docs(readme): add architecture diagram
test(llm_manager): add provider switching test
```

---

## 🔄 Development Workflow

### Always Work on a Feature Branch

```bash
# Fetch latest from upstream
git fetch upstream

# Start from a clean main
git checkout main
git pull upstream main

# Create a descriptive feature branch
git checkout -b feat/your-feature-name
```

### Make Your Changes

1. Write code following the standards above
2. Add tests for your feature or fix
3. Run the full test suite: `python -m pytest tests/ -v`
4. Update docs if needed

### Submit a Pull Request

```bash
# Push your branch
git push origin feat/your-feature-name
```

Then open a Pull Request on GitHub.

**PRs are required to:**
- Pass all CI checks
- Have a clear description of what changed and why
- Reference any related issues

### What to Work On

Check the [open issues](https://github.com/MB-Ndhlovu/Bantu-Os/issues) for priorities. The current focus is:

| Layer | Priority | What to Build |
|-------|----------|---------------|
| Layer 1 (C) | High | Process supervision, rc scripts |
| Layer 2 (Rust) | High | Complete tool dispatch, command parser |
| Layer 3 (Python) | High | LLM provider abstraction, kernel tests |
| Layer 4 (Python) | Medium | Service APIs: file, process, network |
| Memory | Medium | ChromaDB integration, embeddings |
| CI/CD | Medium | Add cargo test to CI |
| Docs | Ongoing | Architecture docs, API docs |

---

## 📐 Architecture Context

Bantu-OS is a layered system. Before writing code, read the relevant spec:

- [SPEC.md](docs/SPEC.md) — Full architecture specification
- [KERNEL.md](docs/KERNEL.md) — Kernel design
- [SECURITY.md](docs/SECURITY.md) — Security model

Each layer has a clear owner (see AGENTS.md). If you're unsure which layer your change belongs in, ask in an issue.

---

## ❓ Getting Help

- **Issues:** Open one on GitHub — we respond within 24 hours
- **Email:** malibongwendhlovu05@gmail.com
- **GitHub Discussions:** Use the Discussions tab

---

## 🌍 Code of Conduct

This project follows our [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you agree to uphold a welcoming, respectful community.

---

*Built in Africa. Open to the world. Let's build the future together.*