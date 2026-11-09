from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, cast


class ResponseStatus(StrEnum):
    SUCCESS = 'success'
    ERROR = 'error'


@dataclass
class Request:
    command: str
    params: dict[str, Any] = field(default_factory=dict)

    def to_payload(self) -> dict[str, Any]:
        """Return this request as a JSON-compatible payload."""

        return {
            'command': self.command,
            'params': self.params,
        }


@dataclass
class Response:
    status: ResponseStatus
    data: Any = None
    error: dict[str, Any] | None = None
    timing_ms: float = 0.0

    def to_payload(self) -> dict[str, Any]:
        """Return this response as a JSON-compatible payload."""

        return {
            'status': self.status,
            'data': self.data,
            'error': self.error,
            'timing_ms': self.timing_ms,
        }

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> Response:
        """Build a response from a payload."""

        status = (
            ResponseStatus.SUCCESS
            if payload.get('status') == ResponseStatus.SUCCESS
            else ResponseStatus.ERROR
        )
        error = payload.get('error')
        timing = payload.get('timing_ms', 0.0)
        return cls(
            status=status,
            data=payload.get('data'),
            error=cast(dict[str, Any], error) if isinstance(error, dict) else None,
            timing_ms=float(timing) if isinstance(timing, int | float) else 0.0,
        )
