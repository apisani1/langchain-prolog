# langchain-prolog 1.0.0

Two themes in this release: **langchain 1.x compatibility** and **SWI-Prolog initialization robustness**. The public `PrologConfig` / `PrologRunnable` / `PrologTool` API is unchanged — the breaking part is the supported langchain version range.

## Breaking changes

- **Requires `langchain >= 1.3.9, < 2.0.0`** (was `^0.3.0`). Projects on the langchain 0.3 line cannot upgrade in place.
- **Requires `pydantic >= 2.7.4`** (was `^2.0.0`).
- **New explicit pin: `langchain-core >= 1.4.6, < 1.5.0`.** Narrow on purpose — `PrologTool` uses a private langchain-core import that could disappear in a minor bump.
- New transitive dep: `langgraph >= 1.2.4, < 1.3.0`.

### How to upgrade

Bump both pins together:

```toml
langchain-prolog = "^1.0.0"
langchain = "^1.3.9"
pydantic = "^2.7.4"
```

No caller-side code changes are needed for `langchain-prolog` itself. However, if **your project's own code** referenced the removed top-level `langchain.{verbose,debug,llm_cache}` globals or the `langchain.globals` submodule (both removed in langchain 1.0), switch them to `langchain_core.globals`:

```python
from langchain_core.globals import set_verbose, set_debug, set_llm_cache

set_verbose(False)
set_debug(False)
set_llm_cache(None)   # pass None, not False, to disable
```

The agent examples in `README.md` and `docs/source/tool.md` have been updated to use the canonical 1.x `langchain.agents.create_agent` API. If you copy-pasted the old `create_tool_calling_agent` + `AgentExecutor` pattern from the README, see the new section for the replacement.

## SWI-Prolog initialization is now much more reliable

`_prolog_init` was the source of most "works on my machine" reports. This release fixes a lot of small bugs that compounded:

- **macOS Intel** installs (`/usr/local`) are now supported alongside Apple Silicon; the zlib path is derived from the matching Homebrew prefix.
- **macOS version selection** is now numeric — `9.10.0` correctly beats `9.2.0`. Homebrew revision suffixes like `9.10.0_2` are handled.
- The documented `SWIPL_*_DIR` **env-var fallbacks** are now actually reachable on every platform; previously they were dead code if the standard install path was missing.
- `DYLD_LIBRARY_PATH` is appended to instead of clobbered.
- A failed `libswipl` preload now raises `PrologInitializationError` immediately with the original cause attached, instead of warning and failing later with a cryptic downstream error.
- `initialize_prolog` no longer double-wraps inner `PrologInitializationError`s, so error messages stay readable.
- 20 new fully-mocked unit tests cover every fix above (no SWI-Prolog install required to run them).

## Examples + docs migrated to `create_agent`

`create_tool_calling_agent` and `AgentExecutor` were removed from `langchain.agents` in langchain 1.0. Every example in this repo that used them is now on the canonical replacement:

```python
from langchain.agents import create_agent

agent = create_agent(
    llm,
    [prolog_tool],
    system_prompt="You are a helpful assistant",
)

result = agent.invoke({"messages": [("human", "Who are John's children?")]})
print(result["messages"][-1].content)
```

The Google Colab route-planner notebook had outdated pinned versions for `langgraph` and related packages. Its setup cell now resolves everything transitively via a single `pip install langchain-prolog` and is markedly faster to bootstrap.

## Other fixes

- Pylint clean: four chronic warnings in `runnable.py` resolved without behavior change; score is now 10.00/10.
- Security: `docs/requirements.txt` pins `tornado >= 6.5.3` per a Snyk advisory (docs build only).

## Full changelog

See `CHANGELOG.md` for the complete list.
