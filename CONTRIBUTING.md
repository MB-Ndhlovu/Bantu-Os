# Contributing to Bantu-OS

Thank you for your interest in contributing to Bantu-OS. This guide covers everything you need to set up your development environment, run tests, and submit changes.

---

## Development Setup

### Prerequisites

- Linux (Debian/Ubuntu-based recommended)
- Python 3.10+
- Rust 1.70+
- GCC
- Git
- `pip` or `poetry`

### 1. Clone the Repository

```bash
git clone https://github.com/MB-Ndhlovu/Bantu-Os.git
cd Bantu-Os
```

### 2. Set Up Python Environment

```bash
# Using pip
python3 -m venv venv
source venv/bin/activate
pip install -e .

# Or using poetry
poetry install
poetry shell
```

### 3. Set Up Rust Environment

```bash
# Install Rust if not present
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source ~/.cargo/env

# Verify
rustc --version
cargo --version
```

### 4. Build All Layers

```bash
# Python package
pip install -e .

# C init system
cd init && make

# Rust shell
cd ../shell && cargo build --release
```

### 5. Run the Dev Setup Script

```bash
bash scripts/dev-setup.sh
```

---

## Running Tests

### All Tests

```bash
make test
```

### Python Tests Only

```bash
python -m pytest tests/ -v
```

### Rust Tests Only

```bash
cd shell && cargo test
```

### C Init Tests

```bash
cd init && make test
```

### Watch Mode (Python)

```bash
pip install pytest-watch
pytest-watch tests/ -v
```

---

## Project Layout

```
bantu_os/
├── init/           # C init system (Layer 1)
├── shell/          # Rust shell (Layer 2)
├── bantu_os/       # Python AI engine + services (Layers 3 & 4)
├── tests/          # Python test suite
└── docs/           # Architecture docs
```

---

## Code Standards

### Python

- Follow PEP 8
- Use type hints where possible
- All public APIs must have docstrings
- Run `python -m pytest tests/ -v` before committing

### Rust

- Follow `rustfmt` style
- Include doc comments on public items
- All tests must pass: `cargo test`

### C

- Comment complex logic
- Include a `Makefile` for each component
- Verify compilation on clean build

---

## Commit Convention

Format: `<type>(<scope>): <description>`

| Type | When to Use |
|------|-------------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `test` | Adding or updating tests |
| `refactor` | Code restructure (no behavior change) |
| `chore` | Maintenance, deps, CI |

**Examples:**
```
feat(kernel): add socket reconnection logic
fix(scheduler): correct HHMM time regex
docs(init): add signal handling section
test(shell): add integration test for tool dispatch
```

---

## Submitting Changes

### 1. Branch

```bash
git fetch upstream
git checkout main && git pull upstream main
git checkout -b feat/your-feature-name
```

### 2. Make Changes

- Write code
- Write tests
- Update docs if needed

### 3. Verify Tests Pass

```bash
python -m pytest tests/ -v
cd shell && cargo test
```

### 4. Commit

```bash
git add .
git commit -m "feat(scope): description"
```

### 5. Push & Open PR

```bash
git push origin feat/your-feature-name
```

Then open a Pull Request on GitHub with:
- Clear description of the change
- Link to any relevant issue
- Confirmation that tests pass

---

## What to Build Next

See [AGENTS.md](./AGENTS.md) for the current priority list:

1. AI-native shell UX (polish REPL, history, tab completion)
2. C init integration (service registry wiring)
3. Phase 2: Connectivity (messaging, fintech APIs, crypto wallet)

---

## Getting Help

- Open an [issue](https://github.com/MB-Ndhlovu/Bantu-Os/issues)
- Read the [SPEC.md](./SPEC.md) for architecture context
- Check existing PRs for patterns

---

*Last updated: 2026-04-17*
