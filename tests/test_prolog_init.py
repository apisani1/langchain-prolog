"""Unit tests for ``langchain_prolog._prolog_init``.

These tests mock the platform, filesystem and native-library loading so they run
without a SWI-Prolog installation. They therefore do **not** use the
``requires_prolog`` marker and target the module's functions directly rather than
relying on the import-time ``initialize_prolog()`` call.
"""

import platform
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from langchain_prolog import _prolog_init
from langchain_prolog._prolog_init import (
    _find_homebrew_swipl,
    _version_key,
    get_env_paths,
    initialize_macos,
    initialize_prolog,
    is_doc_build,
)
from langchain_prolog.exceptions import PrologInitializationError


SWIPL_ENV_VARS = ("SWIPL_HOME_DIR", "SWIPL_LIB_DIR", "SWIPL_BASE_DIR")


@pytest.fixture
def clear_swipl_env(monkeypatch):
    """Remove SWI-Prolog env vars so discovery logic is exercised in isolation."""
    for var in SWIPL_ENV_VARS:
        monkeypatch.delenv(var, raising=False)


@pytest.fixture
def mock_cdll(monkeypatch):
    """Replace ctypes.CDLL with a no-op mock and return it."""
    cdll = MagicMock(name="CDLL")
    monkeypatch.setattr(_prolog_init.ctypes, "CDLL", cdll)
    return cdll


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------
class TestVersionKey:
    def test_orders_numerically_not_lexicographically(self):
        # Regression for #3: 9.10.0 must outrank 9.2.0
        versions = [Path("9.2.0"), Path("9.10.0"), Path("9.3.1")]
        assert max(versions, key=_version_key).name == "9.10.0"

    def test_non_numeric_suffix_is_truncated(self):
        assert _version_key(Path("9.10.0_2")) == (9, 10, 0)

    def test_non_numeric_name_is_safe(self):
        assert _version_key(Path("dev")) == ()


class TestGetEnvPaths:
    def test_returns_none_when_unset(self, clear_swipl_env):
        assert get_env_paths() == (None, None, None)

    def test_reads_env_vars(self, monkeypatch):
        monkeypatch.setenv("SWIPL_HOME_DIR", "/h")
        monkeypatch.setenv("SWIPL_LIB_DIR", "/l")
        monkeypatch.setenv("SWIPL_BASE_DIR", "/b")
        home, lib, base = get_env_paths()
        assert (home, lib, base) == (Path("/h"), Path("/l"), Path("/b"))


class TestIsDocBuild:
    def test_readthedocs(self, monkeypatch):
        monkeypatch.setenv("READTHEDOCS", "True")
        monkeypatch.delenv("SPHINX_BUILD", raising=False)
        assert is_doc_build() is True

    def test_sphinx_build_flag(self, monkeypatch):
        monkeypatch.delenv("READTHEDOCS", raising=False)
        monkeypatch.setenv("SPHINX_BUILD", "True")
        assert is_doc_build() is True

    def test_false_when_unset(self, monkeypatch):
        monkeypatch.delenv("READTHEDOCS", raising=False)
        monkeypatch.delenv("SPHINX_BUILD", raising=False)
        assert is_doc_build() is False

    def test_sphinx_in_sys_modules_does_not_trigger(self, monkeypatch):
        # Regression for #8: merely importing sphinx must not skip initialization
        monkeypatch.delenv("READTHEDOCS", raising=False)
        monkeypatch.delenv("SPHINX_BUILD", raising=False)
        monkeypatch.setitem(sys.modules, "sphinx", types.ModuleType("sphinx"))
        assert is_doc_build() is False


# ---------------------------------------------------------------------------
# Homebrew discovery
# ---------------------------------------------------------------------------
class TestFindHomebrewSwipl:
    def test_returns_none_when_cellar_absent(self, monkeypatch):
        # Regression for #1: absent Cellar must not raise (old code crashed here)
        monkeypatch.setattr(Path, "exists", lambda self: False)
        assert _find_homebrew_swipl() is None

    def _mock_cellar(self, monkeypatch, names):
        monkeypatch.setattr(Path, "exists", lambda self: True)
        monkeypatch.setattr(Path, "is_dir", lambda self: True)
        monkeypatch.setattr(
            Path,
            "iterdir",
            lambda self: iter([self / name for name in names]),
        )

    def test_arm64_prefix_and_latest_version(self, monkeypatch):
        monkeypatch.setattr(platform, "machine", lambda: "arm64")
        self._mock_cellar(monkeypatch, ["9.2.0", "9.10.0"])
        result = _find_homebrew_swipl()
        assert result is not None
        base, lib, home, prefix = result
        assert prefix == Path("/opt/homebrew")
        assert base.name == "9.10.0"
        assert "arm64-darwin" in str(lib)

    def test_x86_64_prefix(self, monkeypatch):
        monkeypatch.setattr(platform, "machine", lambda: "x86_64")
        self._mock_cellar(monkeypatch, ["9.6.0"])
        result = _find_homebrew_swipl()
        assert result is not None
        _, lib, _, prefix = result
        assert prefix == Path("/usr/local")
        assert "x86_64-darwin" in str(lib)


# ---------------------------------------------------------------------------
# initialize_macos
# ---------------------------------------------------------------------------
class TestInitializeMacos:
    def _existing_install(self, tmp_path):
        base = tmp_path / "swipl"
        home = base / "lib" / "swipl"
        lib = home / "lib" / "arm64-darwin"
        lib.mkdir(parents=True)
        return base, lib, home, Path("/opt/homebrew")

    def test_env_fallback_when_homebrew_missing(self, monkeypatch, tmp_path, mock_cdll):
        # Regression for #1: env vars are honored when Homebrew discovery fails
        monkeypatch.setattr(_prolog_init, "_find_homebrew_swipl", lambda: None)
        lib = tmp_path / "lib"
        lib.mkdir()
        monkeypatch.setenv("SWIPL_HOME_DIR", str(tmp_path))
        monkeypatch.setenv("SWIPL_LIB_DIR", str(lib))
        monkeypatch.setenv("SWIPL_BASE_DIR", str(tmp_path))

        initialize_macos()  # must not raise

        assert _prolog_init.os.environ["SWIPL_HOME_DIR"] == str(tmp_path)
        assert mock_cdll.called

    def test_raises_when_nothing_found(self, monkeypatch, clear_swipl_env, mock_cdll):
        monkeypatch.setattr(_prolog_init, "_find_homebrew_swipl", lambda: None)
        with pytest.raises(PrologInitializationError):
            initialize_macos()

    def test_dyld_library_path_preserved(self, monkeypatch, tmp_path, mock_cdll):
        # Regression for #4: an existing DYLD_LIBRARY_PATH must be preserved
        install = self._existing_install(tmp_path)
        monkeypatch.setattr(_prolog_init, "_find_homebrew_swipl", lambda: install)
        monkeypatch.setenv("DYLD_LIBRARY_PATH", "/pre/existing")

        initialize_macos()

        dyld = _prolog_init.os.environ["DYLD_LIBRARY_PATH"]
        assert dyld.endswith("/pre/existing")
        assert str(install[1]) in dyld

    def test_libswipl_load_failure_is_fatal(self, monkeypatch, tmp_path):
        # Regression for #5: a failed libswipl preload raises instead of warning
        install = self._existing_install(tmp_path)
        monkeypatch.setattr(_prolog_init, "_find_homebrew_swipl", lambda: install)
        monkeypatch.setattr(_prolog_init.ctypes, "CDLL", MagicMock(side_effect=OSError("boom")))

        with pytest.raises(PrologInitializationError, match="SWI-Prolog library"):
            initialize_macos()


# ---------------------------------------------------------------------------
# initialize_prolog error handling
# ---------------------------------------------------------------------------
class TestInitializePrologErrorWrapping:
    def test_doc_build_short_circuits(self, monkeypatch):
        monkeypatch.setenv("SPHINX_BUILD", "True")
        called = MagicMock()
        monkeypatch.setattr(_prolog_init, "initialize_macos", called)
        initialize_prolog()
        assert not called.called

    def test_init_error_not_double_wrapped(self, monkeypatch):
        # Regression for #6: an inner PrologInitializationError propagates unchanged
        monkeypatch.delenv("SPHINX_BUILD", raising=False)
        monkeypatch.delenv("READTHEDOCS", raising=False)
        monkeypatch.setattr(platform, "system", lambda: "Darwin")
        inner = PrologInitializationError("inner message")
        monkeypatch.setattr(_prolog_init, "initialize_macos", MagicMock(side_effect=inner))

        with pytest.raises(PrologInitializationError) as exc_info:
            initialize_prolog()

        assert exc_info.value is inner
        assert "Error initializing SWI-Prolog" not in str(exc_info.value)

    def test_unexpected_error_is_wrapped_with_cause(self, monkeypatch):
        monkeypatch.delenv("SPHINX_BUILD", raising=False)
        monkeypatch.delenv("READTHEDOCS", raising=False)
        monkeypatch.setattr(platform, "system", lambda: "Darwin")
        cause = ValueError("weird")
        monkeypatch.setattr(_prolog_init, "initialize_macos", MagicMock(side_effect=cause))

        with pytest.raises(PrologInitializationError) as exc_info:
            initialize_prolog()

        assert "Error initializing SWI-Prolog" in str(exc_info.value)
        assert exc_info.value.__cause__ is cause

    def test_unsupported_os_raises(self, monkeypatch):
        monkeypatch.delenv("SPHINX_BUILD", raising=False)
        monkeypatch.delenv("READTHEDOCS", raising=False)
        monkeypatch.setattr(platform, "system", lambda: "Plan9")
        with pytest.raises(PrologInitializationError, match="Unsupported operating system"):
            initialize_prolog()
