# Bantu OS

Bantu OS is an AI-powered operating system that combines the power of large language models with traditional system operations to create an intelligent, adaptive computing environment.

## Project Structure

```
bantu_os/
├── core/                    # Core system components
│   ├── __init__.py
│   ├── kernel/             # Core LLM integration and system services
│   │   ├── __init__.py
│   │   ├── llm_manager.py  # LLM model management
│   │   └── services.py     # System services management
│   │
│   └── utils/              # Core utilities
│       ├── __init__.py
│       └── helpers.py      # Helper functions
│
├── agents/                 # AI agents and task management
│   ├── __init__.py
│   ├── base_agent.py      # Base agent class
│   ├── task_manager.py    # Task management
│   └── api/               # API integrations
│       ├── __init__.py
│       └── base_api.py    # Base API handler
│
├── interface/             # User interfaces
│   ├── __init__.py
│   ├── cli/               # Command Line Interface
│   │   ├── __init__.py
│   │   ├── commands.py    # CLI commands
│   │   └── shell.py       # Interactive shell
│   │
│   └── hooks/             # Hooks for future interfaces
│       ├── __init__.py
│       ├── voice.py       # Voice interface hooks
│       └── text.py        # Text interface hooks
│
├── memory/                # Memory and knowledge management
│   ├── __init__.py
│   ├── vector_db.py       # Vector database integration
│   └── knowledge_graph.py # Knowledge graph implementation
│
├── config/                # Configuration files
│   ├── __init__.py
│   ├── settings.py        # Application settings
│   └── logging.conf       # Logging configuration
│
└── tests/                 # Test suite
    ├── __init__.py
    ├── unit/             # Unit tests
    └── integration/      # Integration tests
```

## Getting Started

### Prerequisites
- Python 3.9+
- Poetry (for dependency management)

### Installation
1. Clone the repository
2. Install dependencies:
   ```bash
   poetry install
   ```
3. Configure your environment variables in `.env`

## Development

### Running the CLI
```bash
poetry run python -m bantu_os.interface.cli.shell
```

### Running Tests
```bash
poetry run pytest
```

## Architecture Overview

1. **Core**: The foundation layer handling LLM integration and system services
2. **Agents**: Manages AI agents, tasks, and API integrations
3. **Interface**: User interaction points (CLI, with hooks for future interfaces)
4. **Memory**: Vector database and knowledge graph for persistent storage

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a new Pull Request

## License

[Your License Here]
