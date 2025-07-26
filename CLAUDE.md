# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Environment Setup
```bash
# Install core dependencies
make install

# Install all development dependencies  
make install-dev

# Create virtual environment
make venv
```

### Testing
```bash
# Run all tests
make test

# Run tests with coverage
make test-cov

# Run specific test file
make test-file f=tests/test_runnable.py

# Run tests matching pattern
make test-pattern p="async"
```

### Code Quality
```bash
# Format code
make format

# Run linters
make lint

# Combined format, lint, and test
make check
```

### Building and Documentation
```bash
# Build package
make build

# Generate documentation
make docs

# Live documentation server
make docs-live
```

## Architecture Overview

This is a Python library that integrates SWI-Prolog with LangChain, enabling logic programming capabilities in LangChain applications.

### Core Components

- **PrologConfig** (`src/langchain_prolog/runnable.py`): Configuration class that manages Prolog settings, rules files, and query schemas
- **PrologRunnable** (`src/langchain_prolog/runnable.py`): Main class implementing LangChain's Runnable interface for executing Prolog queries with support for sync/async operations
- **PrologTool** (`src/langchain_prolog/tool.py`): LangChain Tool wrapper that allows LLMs to invoke Prolog queries through function calling

### Key Design Patterns

1. **Three Query Modes**: Full predicate strings, default predicate with arguments, or schema-validated dictionaries
2. **Schema Validation**: Pydantic-based schemas for type-safe Prolog query construction
3. **Async Support**: Full async/await support for non-blocking Prolog execution
4. **Error Handling**: Custom exception hierarchy for Prolog-specific errors

### Dependencies

- Requires SWI-Prolog system installation
- Uses `janus-swi` for Python-Prolog bridge
- Built on LangChain 0.3.0+ and Pydantic 2.0+

### Test Structure

Tests are organized by component:
- `test_runnable.py`: Core PrologRunnable functionality
- `test_async_runnable.py`: Async operation tests  
- `test_tool.py`: Tool integration tests

All tests require SWI-Prolog installation and use the `@pytest.mark.requires_prolog` marker.