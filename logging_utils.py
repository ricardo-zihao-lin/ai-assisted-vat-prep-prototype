"""Shared logging helpers for CLI-friendly coloured pipeline output."""

from __future__ import annotations

import logging
import sys

SUCCESS_LEVEL = 25


class ColourFormatter(logging.Formatter):
    """Render compact coloured log lines when ANSI output is supported."""

    RESET = "\x1b[0m"
    COLOURS = {
        logging.DEBUG: "\x1b[90m",
        logging.INFO: "\x1b[94m",
        logging.WARNING: "\x1b[93m",
        logging.ERROR: "\x1b[91m",
        logging.CRITICAL: "\x1b[95m",
        SUCCESS_LEVEL: "\x1b[92m",
    }

    def __init__(self, *, use_colour: bool) -> None:
        super().__init__("%(message)s")
        self.use_colour = use_colour

    def format(self, record: logging.LogRecord) -> str:
        level_label = "SUCCESS" if record.levelno == SUCCESS_LEVEL else record.levelname
        message = record.getMessage()
        rendered = f"[{level_label}] {message}"
        if not self.use_colour:
            return rendered
        colour = self.COLOURS.get(record.levelno, "")
        return f"{colour}{rendered}{self.RESET}"


def _supports_ansi() -> bool:
    if not sys.stdout.isatty():
        return False
    return True


def configure_logging(level_name: str) -> None:
    """Configure the root logger for compact CLI output."""
    if logging.getLevelName(SUCCESS_LEVEL) != "SUCCESS":
        logging.addLevelName(SUCCESS_LEVEL, "SUCCESS")

        def success(self: logging.Logger, message: str, *args, **kwargs) -> None:
            if self.isEnabledFor(SUCCESS_LEVEL):
                self._log(SUCCESS_LEVEL, message, args, **kwargs)

        logging.Logger.success = success  # type: ignore[attr-defined]

    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(ColourFormatter(use_colour=_supports_ansi()))

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, level_name))
