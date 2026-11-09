from __future__ import annotations

import logging
import os
from dataclasses import dataclass

from . import env


@dataclass(frozen=True)
class Settings:
    host: str
    port: int
    timeout: float
    log_level: int

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            host=os.getenv(env.HOST, env.DEFAULT_HOST),
            port=_read_int(env.PORT, env.DEFAULT_PORT),
            timeout=_read_float(env.TIMEOUT, env.DEFAULT_TIMEOUT),
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
    value = os.getenv(env.LOG_LEVEL)
    if value is None:
        return logging.INFO
    level = logging.getLevelNamesMapping().get(value.upper())
    if level is None:
        raise ValueError(f'invalid {env.LOG_LEVEL}: {value!r}')
    return level
