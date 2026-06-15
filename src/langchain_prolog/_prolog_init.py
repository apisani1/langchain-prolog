"""
SWI-Prolog initialization script for Python.

Standard Homebrew (macOS), system-package (Linux) and default (Windows) installs
are detected automatically. Set the following environment variables only when
using non-standard installation paths:

# For macOS (use x86_64-darwin instead of arm64-darwin on Intel Macs)
export SWIPL_HOME_DIR=/path/to/swipl/lib/swipl
export SWIPL_LIB_DIR=/path/to/swipl/lib/arm64-darwin
export SWIPL_BASE_DIR=/path/to/swipl

# For Linux
export SWIPL_HOME_DIR=/path/to/swi-prolog
export SWIPL_LIB_DIR=/path/to/swi-prolog/lib/x86_64-linux

# For Windows (in PowerShell)
$env:SWIPL_HOME_DIR="C:\\path\\to\\swipl"
$env:SWIPL_LIB_DIR="C:\\path\\to\\swipl\\bin"
"""

import ctypes
import os
import platform
from pathlib import Path
from typing import Optional

from .exceptions import PrologInitializationError
from .logger import logger


def get_env_paths() -> tuple[Optional[Path], Optional[Path], Optional[Path]]:
    """Get paths from environment variables."""
    swipl_home = os.environ.get("SWIPL_HOME_DIR")
    swipl_lib = os.environ.get("SWIPL_LIB_DIR")
    swipl_base = os.environ.get("SWIPL_BASE_DIR")

    return (
        Path(swipl_home) if swipl_home else None,
        Path(swipl_lib) if swipl_lib else None,
        Path(swipl_base) if swipl_base else None,
    )


def _version_key(path: Path) -> tuple[int, ...]:
    """Sort key that orders version directories numerically (so 9.10.0 > 9.2.0).

    Each dot-separated component contributes its leading digit run, so Homebrew
    revision suffixes such as ``9.10.0_2`` are handled (``0_2`` -> ``0``).
    """
    parts = []
    for component in path.name.split("."):
        digits = ""
        for char in component:
            if char.isdigit():
                digits += char
            else:
                break
        if not digits:
            break
        parts.append(int(digits))
    return tuple(parts)


def _find_homebrew_swipl() -> Optional[tuple[Path, Path, Path, Path]]:
    """Locate a Homebrew SWI-Prolog install.

    Returns ``(swipl_base, swipl_lib, swipl_home, brew_prefix)`` for the latest
    installed version, or ``None`` if no Homebrew install is found. Apple Silicon
    uses ``/opt/homebrew`` while Intel uses ``/usr/local``; both are probed so the
    correct one is selected regardless of the reported architecture.
    """
    arch = platform.machine()
    primary = Path("/opt/homebrew") if arch == "arm64" else Path("/usr/local")
    prefixes = [primary] + [p for p in (Path("/opt/homebrew"), Path("/usr/local")) if p != primary]

    for prefix in prefixes:
        cellar = prefix / "Cellar" / "swi-prolog"
        if not cellar.exists():
            continue
        try:
            versions = [x for x in cellar.iterdir() if x.is_dir()]
        except OSError:
            continue
        if not versions:
            continue
        swipl_base = max(versions, key=_version_key)
        swipl_home = swipl_base / "lib" / "swipl"
        swipl_lib = swipl_home / "lib" / f"{arch}-darwin"
        return swipl_base, swipl_lib, swipl_home, prefix
    return None


def initialize_macos() -> None:
    """Initialize SWI-Prolog environment for macOS."""
    swipl_base: Optional[Path] = None
    swipl_lib: Optional[Path] = None
    swipl_home: Optional[Path] = None
    brew_prefix: Optional[Path] = None

    found = _find_homebrew_swipl()
    if found is not None:
        swipl_base, swipl_lib, swipl_home, brew_prefix = found

    # Fall back to environment variables when Homebrew discovery fails or the
    # discovered paths are incomplete (e.g. official .dmg / custom installs).
    if swipl_lib is None or swipl_home is None or not swipl_lib.exists() or not swipl_home.exists():
        env_home, env_lib, env_base = get_env_paths()
        if env_lib and env_home and env_base:
            swipl_lib = env_lib
            swipl_home = env_home
            swipl_base = env_base
        else:
            raise PrologInitializationError(
                "SWI-Prolog libraries not found. Please set SWIPL_LIB_DIR, SWIPL_HOME_DIR and SWIPL_BASE_DIR"
            )

    # At this point all three paths are resolved (otherwise we raised above)
    assert swipl_base is not None and swipl_lib is not None and swipl_home is not None

    # Create Frameworks directory
    frameworks_dir = swipl_base / "lib" / "Frameworks"
    frameworks_dir.mkdir(parents=True, exist_ok=True)

    # Create symbolic links
    try:
        for lib in swipl_lib.glob("libswipl*"):
            target = frameworks_dir / lib.name
            if not target.exists():
                target.symlink_to(lib)
    except Exception as e:
        logger.warning(f"Could not create symbolic links: {e}")

    # Set environment variables, preserving any existing DYLD_LIBRARY_PATH
    dyld_parts = [str(swipl_lib), str(frameworks_dir)]
    existing_dyld = os.environ.get("DYLD_LIBRARY_PATH")
    if existing_dyld:
        dyld_parts.append(existing_dyld)
    os.environ["DYLD_LIBRARY_PATH"] = ":".join(dyld_parts)
    os.environ["SWIPL_HOME_DIR"] = str(swipl_home)

    # Update system path
    current_path = os.environ.get("PATH", "")
    for path in (str(swipl_lib), str(frameworks_dir)):
        if path not in current_path:
            logger.info(f"Adding {path} to PATH")
            current_path = f"{path}:{current_path}" if current_path else path
    os.environ["PATH"] = current_path

    # Preload zlib (best-effort) from the matching Homebrew prefix
    zlib_candidates = []
    if brew_prefix is not None:
        zlib_candidates.append(brew_prefix / "opt" / "zlib" / "lib" / "libz.1.dylib")
    zlib_candidates += [
        Path("/opt/homebrew/opt/zlib/lib/libz.1.dylib"),
        Path("/usr/local/opt/zlib/lib/libz.1.dylib"),
    ]
    for zlib_path in zlib_candidates:
        if zlib_path.exists():
            try:
                ctypes.CDLL(str(zlib_path))
            except Exception as e:
                logger.warning(f"Could not preload zlib ({zlib_path}): {e}")
            break

    # Load the SWI-Prolog library. This preload is the operative step that makes
    # `import janus_swi` work, so a failure here is fatal.
    libswipl_path = swipl_lib / "libswipl.dylib"
    try:
        ctypes.CDLL(str(libswipl_path), mode=ctypes.RTLD_GLOBAL)
    except Exception as e:
        raise PrologInitializationError(f"Could not load SWI-Prolog library at {libswipl_path}: {e}") from e


def initialize_linux() -> None:
    """Initialize SWI-Prolog environment for Linux."""
    # Try standard Linux paths
    standard_paths = [
        Path("/usr/lib/swi-prolog"),
        Path("/usr/local/lib/swi-prolog"),
    ]

    swipl_lib: Optional[Path] = None
    swipl_home: Optional[Path] = None

    # Check standard paths (only accept a path whose lib subdirectory exists)
    for path in standard_paths:
        candidate_lib = path / "lib" / (platform.machine() + "-linux")
        if path.exists() and candidate_lib.exists():
            swipl_home = path
            swipl_lib = candidate_lib
            break

    # If standard paths don't work, try environment variables
    if not swipl_lib or not swipl_home:
        env_home, env_lib, _ = get_env_paths()
        if env_lib and env_home:
            swipl_lib = env_lib
            swipl_home = env_home
        else:
            raise PrologInitializationError(
                "SWI-Prolog libraries not found. Please set SWIPL_LIB_DIR and SWIPL_HOME_DIR"
            )

    # Set environment variables
    os.environ["LD_LIBRARY_PATH"] = f"{swipl_lib}:{os.environ.get('LD_LIBRARY_PATH', '')}"
    os.environ["SWIPL_HOME_DIR"] = str(swipl_home)

    # Load library (fatal on failure)
    libswipl_path = swipl_lib / "libswipl.so"
    try:
        ctypes.CDLL(str(libswipl_path), mode=ctypes.RTLD_GLOBAL)
    except Exception as e:
        raise PrologInitializationError(f"Could not load SWI-Prolog library at {libswipl_path}: {e}") from e


def initialize_windows() -> None:
    """Initialize SWI-Prolog environment for Windows."""
    # Try standard Windows paths
    standard_paths = [
        Path("C:/Program Files/swipl"),
        Path("C:/Program Files (x86)/swipl"),
    ]

    swipl_home: Optional[Path] = None
    swipl_lib: Optional[Path] = None

    # Check standard paths (only accept a path whose bin subdirectory exists)
    for path in standard_paths:
        candidate_lib = path / "bin"
        if path.exists() and candidate_lib.exists():
            swipl_home = path
            swipl_lib = candidate_lib
            break

    # If standard paths don't work, try environment variables
    if not swipl_lib or not swipl_home:
        env_home, env_lib, _ = get_env_paths()
        if env_lib and env_home:
            swipl_lib = env_lib
            swipl_home = env_home
        else:
            raise PrologInitializationError(
                "SWI-Prolog libraries not found. Please set SWIPL_LIB_DIR and SWIPL_HOME_DIR"
            )

    # Set environment variables
    os.environ["PATH"] = f"{swipl_lib};{os.environ.get('PATH', '')}"
    os.environ["SWIPL_HOME_DIR"] = str(swipl_home)

    # Load library (fatal on failure)
    libswipl_path = swipl_lib / "libswipl.dll"
    try:
        ctypes.CDLL(str(libswipl_path), mode=ctypes.RTLD_GLOBAL)
    except Exception as e:
        raise PrologInitializationError(f"Could not load SWI-Prolog library at {libswipl_path}: {e}") from e


def is_doc_build() -> bool:
    """Check if we're running in a documentation build environment."""
    return (
        os.environ.get("READTHEDOCS") == "True"  # Read the Docs
        or os.environ.get("SPHINX_BUILD") == "True"  # Explicit Sphinx build flag (set in docs/conf.py)
    )


def initialize_prolog() -> None:
    """Initialize SWI-Prolog environment based on operating system."""
    # Skip initialization if we're building documentation
    if is_doc_build():
        logger.info("Documentation build detected - skipping SWI-Prolog initialization")
        return

    system = platform.system().lower()
    try:
        if system == "darwin":
            initialize_macos()
        elif system == "linux":
            initialize_linux()
        elif system == "windows":
            initialize_windows()
        else:
            raise PrologInitializationError(f"Unsupported operating system: {system}")
    except PrologInitializationError:
        # Already a well-formed (and logged) initialization error; propagate as-is
        # to avoid nested messages and double logging.
        raise
    except Exception as e:
        raise PrologInitializationError(f"Error initializing SWI-Prolog: {e}") from e

    logger.info(f"SWI-Prolog initialized for {system}")
    logger.info(f"SWIPL_HOME_DIR: {os.environ.get('SWIPL_HOME_DIR')}")
    if system == "darwin":
        logger.info(f"DYLD_LIBRARY_PATH: {os.environ.get('DYLD_LIBRARY_PATH')}")
    elif system == "linux":
        logger.info(f"LD_LIBRARY_PATH: {os.environ.get('LD_LIBRARY_PATH')}")
    elif system == "windows":
        logger.info(f"PATH: {os.environ.get('PATH')}")
