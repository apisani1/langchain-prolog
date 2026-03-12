# Changelog
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
