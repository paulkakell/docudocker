from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

LOGGER_NAME = "docudocker"


def configure_logging(level: str) -> logging.Logger:
    logging.basicConfig(level=getattr(logging, level), format="%(message)s")
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(getattr(logging, level))
    return logger


def log_event(level: int, event: str, **fields: Any) -> None:
    logger = logging.getLogger(LOGGER_NAME)
    payload = {
        "timestamp": datetime.now(UTC).isoformat(),
        "level": logging.getLevelName(level),
        "event": event,
        **fields,
    }
    logger.log(level, json.dumps(payload, default=str, separators=(",", ":")))
