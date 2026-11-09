from __future__ import annotations

import logging
import os
from dataclasses import dataclass

from . import constants


@dataclass(frozen=True)
class Settings:
    port: int
    timeout: float
    log_level: int

    @property
    def host(self) -> str:
        """Return the fixed loopback host."""

        return constants.HOST

    @classmethod
    def from_env(cls) -> Settings:
        """Return settings read from environment variables."""

        return cls(
            port=_read_int(constants.PORT, constants.DEFAULT_PORT),
            timeout=_read_float(constants.TIMEOUT, constants.DEFAULT_TIMEOUT),
            log_level=_read_log_level(),
        )


def _read_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f'invalid {name}: {value!r}') from exc


def _read_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(f'invalid {name}: {value!r}') from exc


def _read_log_level() -> int:
    value = os.getenv(constants.LOG_LEVEL)
    if value is None:
        return logging.INFO
    level = logging.getLevelNamesMapping().get(value.upper())
    if level is None:
        raise ValueError(f'invalid {constants.LOG_LEVEL}: {value!r}')
    return level
