"""
SWI-Prolog initialization script for Python.
Set the following environment variables if using non-standard installation paths:

For macOS
export SWIPL_HOME_DIR=/path/to/swipl/lib/swipl
export SWIPL_LIB_DIR=/path/to/swipl/lib/arm64-darwin
export SWIPL_BASE_DIR=/path/to/swipl

# For Linux
export SWIPL_HOME_DIR=/path/to/swi-prolog
export SWIPL_LIB_DIR=/path/to/swi-prolog/lib/x86_64-linux

# For Windows (in PowerShell)
$env:SWIPL_HOME_DIR="C:\path\to\swipl"
$env:SWIPL_LIB_DIR="C:\path\to\swipl\bin"
"""

import ctypes
import os
import platform
import sys
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


def initialize_macos() -> None:
    """Initialize SWI-Prolog environment for macOS."""
    # Try default Homebrew paths first
    homebrew_base = Path("/opt/homebrew/Cellar/swi-prolog")
    versions = [x for x in homebrew_base.iterdir() if x.is_dir()]
    if versions:
        swipl_base = max(versions)  # Latest version
        arch = platform.machine()
        swipl_lib = swipl_base / "lib" / "swipl" / "lib" / f"{arch}-darwin"
        swipl_home = swipl_base / "lib" / "swipl"
    else:
        raise PrologInitializationError("No SWI-Prolog versions found in Homebrew")

    # If default paths don't exist, try environment variables
    if not swipl_lib.exists() or not swipl_home.exists():
        env_home, env_lib, env_base = get_env_paths()
        if env_lib and env_home and env_base:
            swipl_lib = env_lib
            swipl_home = env_home
            swipl_base = env_base
        else:
            raise PrologInitializationError(
                "SWI-Prolog libraries not found. Please set SWIPL_LIB_DIR, SWIPL_HOME_DIR and SWIPL_BASE_DIR"
            )

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

    # Set environment variables
    os.environ["DYLD_LIBRARY_PATH"] = f"{swipl_lib}:{frameworks_dir}"
    os.environ["SWIPL_HOME_DIR"] = str(swipl_home)

    # Update system path
    paths = [str(swipl_lib), str(frameworks_dir)]
    for path in paths:
        if path not in os.environ["PATH"]:
            logger.info(f"Adding {path} to PATH")
            os.environ["PATH"] = f"{path}:{os.environ['PATH']}"

    # Load libraries
    try:
        ctypes.CDLL("/opt/homebrew/opt/zlib/lib/libz.1.dylib")
        ctypes.CDLL(str(swipl_lib / "libswipl.dylib"), mode=ctypes.RTLD_GLOBAL)
    except Exception as e:
        logger.warning(f"Could not preload libraries: {e}")


def initialize_linux() -> None:
    """Initialize SWI-Prolog environment for Linux."""
    # Try standard Linux paths
    standard_paths = [
        Path("/usr/lib/swi-prolog"),
        Path("/usr/local/lib/swi-prolog"),
    ]

    swipl_lib = None
    swipl_home = None

    # Check standard paths
    for path in standard_paths:
        if path.exists():
            swipl_home = path
            swipl_lib = path / "lib" / (platform.machine() + "-linux")
            if swipl_lib.exists():
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

    # Load library
    try:
        ctypes.CDLL(str(swipl_lib / "libswipl.so"), mode=ctypes.RTLD_GLOBAL)
    except Exception as e:
        logger.warning(f"Could not load SWI-Prolog library: {e}")


def initialize_windows() -> None:
    """Initialize SWI-Prolog environment for Windows."""
    # Try standard Windows paths
    standard_paths = [
        Path("C:/Program Files/swipl"),
        Path("C:/Program Files (x86)/swipl"),
    ]

    swipl_home = None
    swipl_lib = None

    # Check standard paths
    for path in standard_paths:
        if path.exists():
            swipl_home = path
            swipl_lib = path / "bin"
            if swipl_lib.exists():
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
    os.environ["PATH"] = f"{swipl_lib};{os.environ['PATH']}"
    os.environ["SWIPL_HOME_DIR"] = str(swipl_home)

    # Load library
    try:
        ctypes.CDLL(str(swipl_lib / "libswipl.dll"), mode=ctypes.RTLD_GLOBAL)
    except Exception as e:
        logger.warning(f"Could not load SWI-Prolog library: {e}")


def is_doc_build() -> bool:
    """Check if we're running in a documentation build environment."""
    return (
        os.environ.get("READTHEDOCS") == "True"  # Read the Docs
        or os.environ.get("SPHINX_BUILD") == "True"  # Sphinx build
        or "sphinx" in sys.modules  # Any documentation build
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

        logger.info(f"SWI-Prolog initialized for {system}")
        logger.info(f"SWIPL_HOME_DIR: {os.environ.get('SWIPL_HOME_DIR')}")
        if system == "darwin":
            logger.info(f"DYLD_LIBRARY_PATH: {os.environ.get('DYLD_LIBRARY_PATH')}")
        elif system == "linux":
            logger.info(f"LD_LIBRARY_PATH: {os.environ.get('LD_LIBRARY_PATH')}")
        elif system == "windows":
            logger.info(f"PATH: {os.environ.get('PATH')}")

    except Exception as e:
        raise PrologInitializationError(f"Error initializing SWI-Prolog: {e}")
