"""
Structured logging configuration for Poolula Platform

Provides consistent logging across all modules with:
- JSON format for machine parsing
- Automatic log rotation
- Context injection (request_id, user, timestamp)
- Environment-appropriate log levels

Usage:
    from core.logging_config import get_logger

    logger = get_logger(__name__)
    logger.info("Processing transaction", extra={
        "transaction_id": "uuid-here",
        "amount": 150.00,
        "category": "utilities"
    })

Author: Poolula Platform
Date: 2025-11-13
"""

import logging
import logging.handlers
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from contextvars import ContextVar


# Context variables for request tracking
request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar("user_id", default=None)


class JSONFormatter(logging.Formatter):
    """
    Custom formatter that outputs logs as JSON

    Includes automatic fields:
    - timestamp (ISO 8601)
    - level (INFO, ERROR, etc.)
    - logger (module name)
    - message
    - request_id (if set)
    - user_id (if set)
    - Any extra fields passed via logger.info(..., extra={...})
    """

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON string

        Args:
            record: Log record from logging module

        Returns:
            JSON string with log data
        """
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add context if available
        request_id = request_id_var.get()
        if request_id:
            log_data["request_id"] = request_id

        user_id = user_id_var.get()
        if user_id:
            log_data["user_id"] = user_id

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add any extra fields from logger.info(..., extra={...})
        if hasattr(record, "extra_data"):
            log_data.update(record.extra_data)

        return json.dumps(log_data)


class StructuredLoggerAdapter(logging.LoggerAdapter):
    """
    Logger adapter that injects extra fields consistently

    Usage:
        logger = get_logger(__name__)
        logger.info("User action", extra={"action": "login", "user_id": "123"})
    """

    def process(self, msg: str, kwargs: dict) -> tuple[str, dict]:
        """
        Process log message to inject extra fields

        Args:
            msg: Log message
            kwargs: Keyword arguments (including 'extra')

        Returns:
            Tuple of (message, kwargs) with processed extra fields
        """
        # Move 'extra' dict to record for JSON formatter
        if "extra" in kwargs:
            kwargs.setdefault("extra", {})
            kwargs["extra"]["extra_data"] = kwargs.pop("extra")

        return msg, kwargs


def setup_logging(
    level: str = None,
    log_file: Path = None,
    log_dir: Path = None,
    max_bytes: int = 10 * 1024 * 1024,  # 10 MB
    backup_count: int = 5,
) -> None:
    """
    Set up logging configuration for the entire application

    Call this once at application startup

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
               Defaults to DEBUG in dev, INFO in prod (from ENV var)
        log_file: Specific log file path (overrides log_dir)
        log_dir: Directory for log files (default: ./logs)
        max_bytes: Max size of each log file before rotation
        backup_count: Number of rotated log files to keep

    Example:
        # In main.py or app.py
        from core.logging_config import setup_logging

        setup_logging(level="INFO", log_dir=Path("logs"))
    """
    # Determine log level
    if level is None:
        env = os.getenv("ENV", "development").lower()
        level = "DEBUG" if env == "development" else "INFO"

    # Determine log file path
    if log_file is None:
        if log_dir is None:
            log_dir = Path("logs")
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "poolula_platform.log"

    # Create formatters
    json_formatter = JSONFormatter()

    # Console handler (human-readable for development)
    console_handler = logging.StreamHandler(sys.stdout)
    if os.getenv("ENV", "development").lower() == "development":
        # Simple format for dev console
        console_format = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        console_handler.setFormatter(console_format)
    else:
        # JSON format for prod console (easier to parse)
        console_handler.setFormatter(json_formatter)

    console_handler.setLevel(level)

    # File handler (JSON for parsing, with rotation)
    file_handler = logging.handlers.RotatingFileHandler(
        filename=log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8"
    )
    file_handler.setFormatter(json_formatter)
    file_handler.setLevel(level)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers.clear()  # Remove any existing handlers
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # Suppress noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("anthropic").setLevel(logging.INFO)

    root_logger.info("Logging initialized", extra={"level": level, "log_file": str(log_file)})


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger for the specified module

    Args:
        name: Module name (typically __name__)

    Returns:
        Logger instance configured for structured logging

    Example:
        from core.logging_config import get_logger

        logger = get_logger(__name__)
        logger.info("Processing started", extra={"item_count": 10})
    """
    logger = logging.getLogger(name)
    return logger


def set_request_context(request_id: str, user_id: Optional[str] = None) -> None:
    """
    Set request context for current async context

    All logs within this context will include request_id and user_id

    Args:
        request_id: Unique identifier for the request (UUID)
        user_id: Optional user identifier

    Example:
        from core.logging_config import set_request_context

        async def handle_request(request):
            set_request_context(request_id=str(uuid.uuid4()), user_id=request.user.id)
            # All subsequent logs will include these IDs
    """
    request_id_var.set(request_id)
    if user_id:
        user_id_var.set(user_id)


def clear_request_context() -> None:
    """
    Clear request context (call at end of request)

    Example:
        try:
            set_request_context(...)
            # ... handle request ...
        finally:
            clear_request_context()
    """
    request_id_var.set(None)
    user_id_var.set(None)


# Example usage and testing
if __name__ == "__main__":
    # Test logging configuration
    setup_logging(level="DEBUG")

    logger = get_logger(__name__)

    logger.debug("This is a debug message")
    logger.info("Application started", extra={"version": "0.1.0"})
    logger.warning("This is a warning")

    # Test with request context
    set_request_context(request_id="test-request-123", user_id="user-456")
    logger.info("Processing user action", extra={"action": "login"})
    clear_request_context()

    logger.error("This is an error without context")

    try:
        raise ValueError("Test exception")
    except Exception as e:
        logger.exception("Caught exception", extra={"error_type": "ValueError"})
