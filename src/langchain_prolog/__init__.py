"""
langchain_prolog - A LangChain integration for SWI-Prolog

This module provides a bridge between LangChain and SWI-Prolog, allowing seamless
integration of Prolog's logic programming capabilities into LangChain pipelines.

Key Components:
    - PrologConfig: Configuration class for Prolog settings
    - PrologRunnable: Main class for executing Prolog queries
    - PrologTool: Utility class for integrating Prolog queries into LangChain tools
    - PrologResult: Type representing possible Prolog query results
    - PrologInput: Type representing valid input formats
    - PrologRuntimeError: Exception class for Prolog execution errors

Requirements:
    - Python 3.9 or higher
    - LangChain 0.3.0 or higher
    - Pydantic 2.0 or higher
    - SWI-Prolog must be installed and accessible in the system path
    - On macOS, requires Homebrew installation of SWI-Prolog
    - The janus_swipl package must be installed
"""

from pydantic import ValidationError

from ._prolog_init import initialize_prolog
from .exceptions import (
    PrologFileNotFoundError,
    PrologInitializationError,
    PrologRuntimeError,
    PrologToolException,
    PrologValueError,
)
from .runnable import (
    PrologConfig,
    PrologInput,
    PrologResult,
    PrologRunnable,
)
from .tool import PrologTool
from .__version__ import __version__


__all__ = [
    "PrologConfig",
    "PrologInput",
    "PrologRunnable",
    "PrologRuntimeError",
    "PrologFileNotFoundError",
    "PrologInitializationError",
    "PrologToolException",
    "PrologValueError",
    "PrologResult",
    "PrologTool",
    "ValidationError",
]

# Initialize Prolog immediately when this module is imported
initialize_prolog()
