"""Logging configuration for the langchain-prolog library."""

import logging
import sys
from pathlib import Path
from typing import (
    Any,
    Callable,
    Union,
)


# Define custom log levels
TRACE = 5
logging.addLevelName(TRACE, "TRACE")


class LangChainPrologLogger:
    """Logger for the langchain-prolog package."""

    def __init__(self, name: str = "langchain_prolog"):
        """Initialize logger with default configuration.

        Args:
            name (str): Logger name, defaults to 'langchain_prolog'
        """
        self.logger = logging.getLogger(name)
        self._configure_default_logger()

    def _configure_default_logger(self) -> None:
        """Configure default logging settings."""
        if not self.logger.handlers:
            self.logger.setLevel(logging.WARNING)

            # Console handler
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.WARNING)

            # Format
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
            )
            console_handler.setFormatter(formatter)

            self.logger.addHandler(console_handler)

    def setup_file_logging(self, log_file: Union[str, Path] = "langchain_prolog.log") -> None:
        """Setup file logging.

        Args:
            log_file (str | Path): Path to log file. Defaults to 'langchain_prolog.log'.
        """

        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

    def set_level(self, level: int) -> None:
        """Set logging level.

        Args:
            level (int): Logging level (e.g., logging.DEBUG, logging.INFO)
        """
        self.logger.setLevel(level)

    def trace(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log at TRACE level."""
        self.logger.log(TRACE, msg, *args, **kwargs)

    @property
    def debug(self) -> Callable:
        """Debug level logging."""
        return self.logger.debug

    @property
    def info(self) -> Callable:
        """Info level logging."""
        return self.logger.info

    @property
    def warning(self) -> Callable:
        """Warning level logging."""
        return self.logger.warning

    @property
    def error(self) -> Callable:
        """Error level logging."""
        return self.logger.error

    @property
    def critical(self) -> Callable:
        """Critical level logging."""
        return self.logger.critical


# Create default logger instance
logger_setup = LangChainPrologLogger()
logger = logger_setup.logger
