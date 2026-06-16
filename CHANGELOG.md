# Changelog

## [1.0.0] - 2026-06-16

### Breaking Changes

- **Requires `langchain >= 1.3.9, < 2.0.0`** (was `^0.3.0`). Projects pinning langchain to the 0.3 line cannot upgrade in place.
- **Requires `pydantic >= 2.7.4, < 3.0.0`** (was `^2.0.0`) to satisfy the new langchain-core floor.
- **New explicit dependency: `langchain-core >= 1.4.6, < 1.5.0`.** Pulled transitively by langchain 1.x; pinned narrowly to hedge against future removal of the private `langchain_core.tools.base._get_runnable_config_param` used by `PrologTool`.
- **New transitive dependency: `langgraph >= 1.2.4, < 1.3.0`.**

#### Upgrade notes

If your project pins `langchain-prolog` and `langchain` separately, bump both:

```toml
langchain-prolog = "^1.0.0"
langchain = "^1.3.9"
pydantic = "^2.7.4"
```

The public `PrologConfig` / `PrologRunnable` / `PrologTool` API is unchanged — no caller-side code changes are required for the langchain upgrade itself. However, code in your project that referenced the removed top-level `langchain.{verbose,debug,llm_cache}` globals or the `langchain.globals` submodule must switch to `from langchain_core.globals import set_verbose, set_debug, set_llm_cache` (and pass `None` to `set_llm_cache` to disable, not `False`).

### Added

- New test module `tests/test_prolog_init.py` with 20 fully-mocked unit tests covering every fix in this release's Prolog initialization work. No SWI-Prolog install required to run.

### Changed

- Internal: `src/langchain_prolog/runnable.py` swaps the removed top-level `langchain.{verbose,debug,llm_cache}` module attributes for the `langchain_core.globals.{set_verbose,set_debug,set_llm_cache}` setters. Drop-in; library behavior unchanged.

### Fixed

- **SWI-Prolog initialization hardened across platforms** (PR #2):
  - **macOS:** the documented `SWIPL_*_DIR` env-var fallback is now actually reachable when Homebrew Cellar is absent (previously failed earlier with an unrelated error).
  - **macOS:** Intel installs at `/usr/local` are now supported alongside Apple Silicon; the zlib path is derived from the matching Homebrew prefix.
  - **macOS:** latest SWI-Prolog version selected numerically (9.10.0 > 9.2.0) instead of lexicographically; Homebrew revision suffixes like `9.10.0_2` are handled.
  - **macOS:** `DYLD_LIBRARY_PATH` is appended to instead of clobbered.
  - **All platforms:** a failed `libswipl` preload now raises `PrologInitializationError` immediately instead of warning and failing later with a cryptic downstream error. The original cause is preserved with `from e`.
  - **All platforms:** `initialize_prolog` re-raises an inner `PrologInitializationError` unchanged to avoid nested messages and double logging.
  - **Linux/Windows:** only standard paths whose `lib/` or `bin/` subdir actually exists are accepted, so the env-var fallbacks are reachable on these platforms too.
  - `is_doc_build` no longer relies on the broad `"sphinx" in sys.modules` heuristic; uses `READTHEDOCS` / `SPHINX_BUILD` env signals only.
  - Use `os.environ.get("PATH", "")` so initialization no longer raises `KeyError` in minimal environments.
- Cleared four chronic pylint warnings in `src/langchain_prolog/runnable.py` (`R0913` on `__init__`, `R0914` / `R0912` on `stream`, `R1714` on the truth-tuple comparison). Pylint score 9.85/10 → 10.00/10; behavior unchanged.

### Security

- `docs/requirements.txt` now pins `tornado >= 6.5.3` per Snyk advisory (PR #1). Affects the documentation build only.

### Documentation

- All examples migrated to the canonical langchain 1.x agent API. The "LangChain agent" sections of `README.md`, `docs/source/tool.md`, `examples/prolog_tool.ipynb`, and `examples/route_planner/route_planner_google_colab.ipynb` now use `from langchain.agents import create_agent` instead of the removed `create_tool_calling_agent` + `AgentExecutor` pattern. Result extraction updates from `answer["output"]` to `answer["messages"][-1].content`.
- The "LangGraph agent" sections of these files continue to demonstrate `langgraph.prebuilt.create_react_agent` as the alternative-API path. `examples/route_planner/route_planner.ipynb` migrated fully to `create_agent` (no parallel-API structure).
- Google Colab notebook (`route_planner_google_colab.ipynb`): the 8-line pip install block — with outdated `langgraph==0.2.74` / `langgraph-checkpoint==2.0.16` / `langgraph-sdk==0.1.53` pins, a never-imported `langchain-community`, and a `--quie` typo — collapsed to a single `pip install --quiet langchain-prolog`. Runtime deps now arrive transitively. Provider-specific `get_answer` lambdas collapsed into a uniform `response["messages"][-1].content` accessor.

### Internal

- Dev-environment files synced from [`apisani1/generate-project v2.2.0`](https://github.com/apisani1/generate-project) (poetry-template), preserving project-specific customizations:
  - `scripts/release.py` — replaced with the v2.2.0 version. Adds the new `--release-docs` / `.tmp_release_docs/` flow, skills-manifest hook, and backup-delete handling. `--changes` is now deprecated.
  - `scripts/install_claude_skills.py` — new template helper.
  - `run.sh` — adopt the `--release-docs` flow (drop deprecated `get:changes` / `--changes`), unquote `$PYTHON_FILES` so multi-file linting actually lints multiple files, add mypy-exclude `LINT_FILES` logic.
  - `.github/workflows/release.yml` — smarter "Prepare release notes" step (RELEASE_NOTES.md / CHANGELOG.md) with emoji.
  - `.github/workflows/docs.yml` — permissions block, `-poetry-v2-` cache restore-key, continue-on-error on the PR-comment step.
  - `.vscode/settings.json` — linters now run via poetry; pylint `--ignore-paths` typo fixed.
  - `Makefile` — `test-manual` help line.
  - `CLAUDE.md` — appended Development Workflow, Code Style, and Gotchas sections.
  - `.readthedocs.yaml` intentionally left unchanged (its `--only docs` flow avoids `janus-swi`, which cannot build on Read the Docs).
- `.tmp_release_docs/` (release-docs skill output) added to `.gitignore` so release drafts no longer appear in `git status`.
- VS Code workbench theme switched to "Dark+" in `.vscode/settings.json`.

## [0.1.1.post18] - 2026-03-11

### Changes

### CI/CD & Documentation Fixes

This is a maintenance release fixing several issues in the documentation build pipeline and release workflow discovered after v0.1.1.post17.

**Documentation Build (docs.yml)**
Fixed docs build producing no HTML output: The docs.yml workflow was calling poetry run make html, which invokes the docs/Makefile's default SPHINXBUILD = poetry run sphinx-build — creating a nested poetry run invocation that silently failed in CI, leaving only _static/ in the output directory with no pages written. Fixed by running sphinx-build directly and bypassing make entirely.

Fixed intersphinx crash (Sphinx 8.2.3 bug): A bug in sphinx.ext.intersphinx._load causes a TypeError: not enough arguments for format string whenever any inventory URL fails to load (redirect, 404, or network error). The LangChain inventory URL had moved, triggering this bug on every build. Fixed by removing the LangChain entry from intersphinx_mapping (all cross-references are already disabled via intersphinx_disabled_reftypes = ["*"]).

Fixed autodoc requiring SWI-Prolog at build time: Added autodoc_mock_imports = ["janus_swi"] to conf.py so Sphinx does not attempt to load the janus_swi C extension during the docs build. Removed the stale docs/api/langchain_prolog 2.rst duplicate file that was generating ~125 spurious warnings.

Fixed Check Build Output step: Refactored to work from the workspace root rather than cd-ing into a directory that might not exist.

**Release Workflow (release.yml)**
Fixed TestPyPI installation picking up wrong version: The test installation step did not pin a version, so pip resolved the highest semver on TestPyPI (an older 0.3.0 upload rather than the freshly published version). Fixed by installing langchain-prolog==$VERSION with an exact pin. Added an explicit version assertion to fail the workflow if __version__ doesn't match the expected release version.
Other

Updated copyright year to 2026 in docs/conf.py.


## [0.1.1.post17] - 2026-03-11

 ### Changes
 
### Infrastructure & Tooling Improvements
This release is a maintenance release focused on CI/CD, developer tooling, and project infrastructure.

**CI/CD Workflows**
* New workflow: Added delete_workflow_runs.yml to automatically clean up old GitHub Actions runs
* docs.yml: Updated dependency cache key for better cache hit rates; fixed GitHub Script syntax in the PR comment step
* tests.yml: Added pull_request trigger so tests also run on PRs; improved cache key to include poetry.lock; added exit 5 handling to allow "no tests collected" as a passing result
* release.yml:
    * Added tag-on-main branch verification step
    * Improved release type detection (is_latest, release_type classification for stable, pre-release, post, draft)
    * Upgraded to softprops/action-gh-release@v2 with make_latest support
    * Added retry/polling loop for ReadTheDocs updates
    * Added release summary step
    * Added strict publish modes (publish:test:strict, publish:strict)
  
**Developer Scripts**
* scripts/release.py: Refactored to use a RollbackState class for safer rollbacks; improved bump_version logic with nested helper functions; added --no-interactive CLI flag; improved commit message derivation
* scripts/update_versions.py: New script for managing version updates across project files
Makefile & run.sh
* Makefile: Added venv-clean, lint-mypy, lint-flake8, lint-pylint, test-manual, publish-test-strict, publish-strict, and all pre-release variant targets (release-major-a/b/rc, release-minor-a/b/rc, release-micro-a/b/rc)
* run.sh: Added Python 3 shim for compatibility, venv:clean command, config_get helper replacing try-load-dotenv, proper publish token handling, extended release functions
Project Configuration
* CLAUDE.md: Added development commands reference and architecture overview for Claude Code integration
* .gitignore: Added .claude/ directory exclusion


## [0.1.1.post16] - 2025-06-29

 ### Changes
- Add langchain to RTD workflow to solve API doc generation issue



## [0.1.1.post15] - 2025-06-29

 ### Changes
- Add comments to RTD build workflow



## [0.1.1.post14] - 2025-06-29

 ### Changes
- Manually install core depandancies to avoid installing janus_swi



## [0.1.1.post13] - 2025-06-29

 ### Changes
- Manually install prolog in RTD build workflow



## [0.1.1.post12] - 2025-06-29

 ### Changes
- Install prolog directly in RTD build workflow



## [0.1.1.post11] - 2025-06-29

 ### Changes
- Use apt_packages to install prolog in RTD build workflow



## [0.1.1.post10] - 2025-06-29

 ### Changes
- Add prolog installation to rtd build workflow



## [0.1.1.post9] - 2025-06-29

 ### Changes
- Use poetry in read the docs build workflow
- Add ignore codes for pylint and flake8
- Deactivate conda and/or regular virtual environments when activating poetry local environment via run.sh venv
- Add test coverage to .gitignore and run.sh clean
- Add optional parameters to run.sh tests:cov test with coverage report
- Rewrite Makefile using run.sh functions



## [0.1.1.post8] - 2025-05-26

 ### Changes
- Add poetry cache to tests and release workflows



## [0.1.1.post7] - 2025-05-26

 ### Changes
- Replace Makefile with run.sh bash script and migrate github workflows to use it for a single source of truth
- Add linting and formating to tests workflow
- Separate test workflow from release
- Add makefile actions to create and remove jupiter notebook kernels
- Correct mock settings for documentation
- Correct GitHub PR request endpoint
- Update RTD endpoint for sync versions
- Delete annoucement
- Reformat conf.py to test documentation workflow
- Add documentation checks
- Activate TestPyPI for all releases
- Add PR comment in docs workflow


## [0.1.1.post6] - 2025-05-18

 ### Changes
- Correct RTD trigger in release workflow



## [0.1.1.post5] - 2025-05-18

 ### Changes
- Correct RTD trigger in release workflow



## [0.1.1.post4] - 2025-05-18

 ### Changes
- Correct RTD trigger in release workflow



## [0.1.1.post3] - 2025-05-18

 ### Changes
- Correct RTD trigger in release workflow



## [0.1.1.post2] - 2025-05-18

 ### Changes
- Correct release-type check on release workflow
- Correct Update ReadTheDocs workflow version prompt



## [0.1.1.post1] - 2025-05-18

 ### Changes
- Solve version handling issue with RTD workflow


## v0.1.1 - 2025-05-17

 ### Changes
- Overide run definition in Prolog Tool to allow passing a pydantic model
- Update doc project files
- Update Makefiles for release management script and other CLI tools
- Update release workflow to use tag messages for release notes
- Redesign release management script
- Transition formatting and linting configuration to pyproject.toml


## [0.1.0.post1] - 2025-03-07

### Changed
- Fixed repository and release links in package metadata

## [0.1.0] - 2025-02-13

### Initial Release
* Initial version of langchain-prolog
* Basic Prolog integration with LangChain
* Support for Prolog queries as runnables and tools
