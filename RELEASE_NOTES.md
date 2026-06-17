# langchain-prolog 1.0.1

This is a maintenance release with no changes to the `PrologConfig`, `PrologRunnable`, or `PrologTool` APIs. The highlights are a full migration from Poetry to UV and a tightening of the minimum dependency floors to match what the library already required in practice.

## Build tooling: Poetry → UV

`pyproject.toml` has been migrated from Poetry (`poetry-core` build backend, `[tool.poetry.*]` tables) to the standard PEP 517 layout with Hatchling as the build backend and UV as the package manager. `uv.lock` replaces `poetry.lock`. All CI workflows (`tests.yml`, `release.yml`, `docs.yml`), `run.sh`, and `Makefile` have been updated accordingly.

If you contribute to this project, replace `poetry install` / `poetry run` invocations with `uv sync` / `uv run`.

## Dependency floor changes

| Package | Before | After |
|---------|--------|-------|
| `langchain` | `>= 0.3.0` | `>= 1.3.9` |
| `pydantic` | `>= 2.0.0` | `>= 2.7.4` |

The library already depended on langchain 1.x behavior in practice; the floors now reflect that. No caller-side code changes are required.

## Other changes

- Python 3.12 and 3.13 added to supported-versions classifiers.
- LangGraph agent usage example removed from `README.md` and docs — documentation now covers two patterns (function-calling via an LLM and direct `PrologRunnable` invocation).
- **Security**: `docs/requirements.txt` pins `tornado >= 6.5.7` per a Snyk CVE advisory (PR #3). This affects documentation builds only, not library consumers.
- Example notebooks refreshed for the langchain 1.x API.

## Full changelog

See [`CHANGELOG.md`](CHANGELOG.md) for the complete list of changes.
