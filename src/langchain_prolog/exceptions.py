from typing import Any

from langchain_core.tools import ToolException

from .logger import logger


class LangChainPrologException(Exception):
    """Base exception class for langchain-prolog with automatic logging."""

    def __init__(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Initialize exception and log it.

        Args:
            message (str): Error message
            *args: Additional positional arguments for Exception
            **kwargs: Additional keyword arguments. Special keys:
                     - log_level: Logging level (default: error)
                     - exc_info: Exception info to include in log
        """
        super().__init__(message, *args)

        # Extract logging parameters
        log_level = kwargs.pop("log_level", "error")
        exc_info = kwargs.pop("exc_info", None)

        # Log the exception
        log_func = getattr(logger, log_level)
        log_func(message, exc_info=exc_info)


class PrologRuntimeError(LangChainPrologException):
    """Raised when a Prolog execution error occurs."""

    pass


class PrologInitializationError(LangChainPrologException):
    """Raised when Prolog initialization fails."""

    pass


class PrologValueError(LangChainPrologException):
    """Raised when a value error occurs."""

    pass


class PrologFileNotFoundError(LangChainPrologException):
    """Raised when a file is not found."""

    pass


class PrologToolException(LangChainPrologException):
    """Raised when a Prolog tool execution error occurs."""

    def __init__(self, message: str, *args: Any, **kwargs: Any) -> None:
        super().__init__(message, *args, **kwargs)
        raise ToolException(message, *args)
