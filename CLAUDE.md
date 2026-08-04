# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

This project uses UV for dependency management and a custom `run.sh` script for development tasks. All commands can be executed via either the Makefile (which delegates to `run.sh`) or directly via `run.sh`.

### Environment Setup
```bash
make venv                 # Create and activate local virtual environment
make install              # Install core dependencies
make install-lint         # Install linting dependencies
make install-test         # Install testing dependencies
make install-docs         # Install documentation dependencies
make install-dev          # Install all development dependencies (dev, test, lint, typing and docs dependency groups)
./run.sh install:all      # CI alternative: install all dependencies without interaction
```

### Code Quality
```bash
make format               # Format code with black and isort
make format-diff          # Run formatters on changed files
make lint                 # Run mypy, flake8, and pylint
make lint-diff             # Run all linters on changed files
make check                # Run format + lint + tests on all files(local development)
make pre-commit           # Format and lint only on changed files
./run.sh check:ci         # CI version (format only checks, no file modifications)

```

### Running
```bash
make run                  # Run the app, or an example of the library
make run ARGS="--help"    # Run with arguments
```

`make run` dispatches in order: `scripts/run.sh` if it exists and is executable, then the
console script entry point if `src/langchain_prolog/main.py` exists, then
`examples/main.py`. To customize how this project starts, create an executable
`scripts/run.sh` — that file is not owned by the template, so it survives dev-environment
syncs. Do not hand-edit the `run` function in `run.sh` or the `run` target in the `Makefile`.

### Worktree lifecycle
```bash
make worktree-setup       # Prepare a freshly created worktree
make worktree-archive     # Tear down a worktree before archiving
make worktree-delete      # Guardrail + teardown before deleting a worktree
```

These back Supacode's `setupScript` / `archiveScript` / `deleteScript` (see `supacode.json`), but
work standalone too. Each phase runs its generic steps and then `scripts/worktree-<phase>.sh` if
that file exists and is executable — exit 0 when absent, the hook's exit code when present. Put
project-specific teardown (stopping docker containers, freeing ports) there; it is not owned by
the template, so it survives dev-environment syncs.

`worktree-delete` refuses to proceed when the tree is dirty, when commits are reachable from no
other ref, or when the branch has stash entries — deleting a worktree also deletes its branch, so
those commits would be lost. Override with `SUPACODE_FORCE_DELETE=1 make worktree-delete`.

### Testing
```bash
make test                 # Run all tests
make test-cov             # Run tests with coverage
make coverage             # Generate coverage report
make test-verbose         # Run tests with verbose output
make test-file f=tests/test_runnable.py    # Run a specific test file
make test-pattern p="async"                # Run tests matching pattern
./run.sh tests:pattern "test_name"  # Run only tests matching pattern
```

### Documentation
```bash
make docs-api             # Generate API documentation automatically
make docs                 # Build Sphinx documentation
make docs-live            # Start live documentation server with auto-reload
make docs-clean           # Clean and rebuild documentation
```

### Package Building
```bash
make build                # Build package with UV
make validate-build       # Validate package builds correctly
make clean                # Clean build artifacts
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

## Development Workflow

The project uses UV for dependency management with multiple dependency groups:
- `test`: pytest and testing utilities
- `lint`: black, isort, flake8, pylint, mypy
- `docs`: Sphinx and documentation tools
- `typing`: mypy type checking

Use `uv add <pkg>` to add dependencies and `uv sync` to install from lockfile. Avoid using `pip install` directly.

## Code Style

- Formatter: Black with 119 character line length
- Import sorting: isort (configured to be Black-compatible)
- Linting: flake8 + pylint + mypy (all configured in `pyproject.toml`)
- Do not add inline `# noqa` without a specific reason

## Gotchas

<!-- Tip: Press `#` during a Claude Code session to auto-incorporate session learnings here. -->

- **Release drafts**: `make release-*` → `scripts/release.py create … --release-docs` reads
  `.tmp_release_docs/{commit.txt,tag.txt,changelog.md,release_notes.md}`. A draft is used only if
  it exists, is non-empty, and is newer than the previous release tag; otherwise it prompts a
  fallback to generated content (per draft). The folder is git-ignored. `--changes` is deprecated.
- **RELEASE_NOTES.md**: Generated and committed each release. `release.yml` uses it as the GitHub
  Release body only when it was part of the tagged commit; otherwise it extracts that version's
  `CHANGELOG.md` entry.

See @./notes for additional private information
