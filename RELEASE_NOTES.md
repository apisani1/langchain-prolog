## langchain-prolog v1.0.3

Maintenance release: no changes to the public API or runtime behavior.

### Fixed

- PyPI badge in the README and docs is now static, so it no longer displays a stale cached version.
- `run.sh` activates the worktree's own virtual environment.

### Internal

- Dev environment synced with generate-project v2.5.0 (new `make run` and worktree lifecycle targets).
- CI: Claude PR Assistant workflow, Dependabot for GitHub Actions, and updated `actions/checkout`, `actions/cache`, and `astral-sh/setup-uv`.
- Minor code cleanups in `tool.py` and `exceptions.py` (import path, redundant `pass`, pylint fixes).

**Full changelog**: https://github.com/apisani1/langchain-prolog/compare/v1.0.2...v1.0.3
