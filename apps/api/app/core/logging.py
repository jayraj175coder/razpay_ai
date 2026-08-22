"""Structured logging for RecoverAI."""
import logging
import sys
from typing import Optional
from app.core.config import settings


def setup_logging() -> None:
    """Configure structured console logging."""
    log_format = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
        format=log_format,
        datefmt=date_format,
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with specified module name."""
    return logging.getLogger(name)


class ContextLogger:
    """Logger wrapper that injects contextual attributes (case_id, request_id, etc.)."""
    def __init__(self, logger: logging.Logger, context: dict):
        self.logger = logger
        self.context = context

    def info(self, msg: str, **kwargs):
        ctx_str = " ".join(f"[{k}={v}]" for k, v in self.context.items() if v)
        self.logger.info(f"{ctx_str} {msg}" if ctx_str else msg, **kwargs)

    def warning(self, msg: str, **kwargs):
        ctx_str = " ".join(f"[{k}={v}]" for k, v in self.context.items() if v)
        self.logger.warning(f"{ctx_str} {msg}" if ctx_str else msg, **kwargs)

    def error(self, msg: str, **kwargs):
        ctx_str = " ".join(f"[{k}={v}]" for k, v in self.context.items() if v)
        self.logger.error(f"{ctx_str} {msg}" if ctx_str else msg, **kwargs)

    def debug(self, msg: str, **kwargs):
        ctx_str = " ".join(f"[{k}={v}]" for k, v in self.context.items() if v)
        self.logger.debug(f"{ctx_str} {msg}" if ctx_str else msg, **kwargs)
