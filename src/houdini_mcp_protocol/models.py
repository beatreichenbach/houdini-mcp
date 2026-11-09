from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, cast
from uuid import uuid4


class ResponseStatus(StrEnum):
    SUCCESS = 'success'
    ERROR = 'error'


@dataclass
class Request:
    command: str
    params: dict[str, Any] = field(default_factory=dict)
    request_id: str = field(default_factory=lambda: uuid4().hex)

    def to_payload(self) -> dict[str, Any]:
        return {
            'command': self.command,
            'params': self.params,
            'request_id': self.request_id,
        }

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> Request:
        params = payload.get('params')
        return cls(
            command=str(payload['command']),
            params=cast(dict[str, Any], params) if isinstance(params, dict) else {},
            request_id=str(payload.get('request_id', '')),
        )


@dataclass
class Response:
    status: ResponseStatus
    data: Any = None
    error: dict[str, Any] | None = None
    request_id: str = ''
    timing_ms: float = 0.0

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> Response:
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
            request_id=str(payload.get('request_id', '')),
            timing_ms=float(timing) if isinstance(timing, int | float) else 0.0,
        )
