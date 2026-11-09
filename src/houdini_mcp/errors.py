from __future__ import annotations

from typing import Any


class HoudiniMCPError(Exception):
    pass


class HoudiniConnectionError(HoudiniMCPError):
    pass


class HoudiniCommandError(HoudiniMCPError):
    def __init__(
        self, message: str, code: str, details: dict[str, Any] | None = None
    ) -> None:
        super().__init__(message)
        self.code = code
        self.details = details or {}

    def __str__(self) -> str:
        message = super().__str__()
        if not self.code:
            return message
        return f'{message} (code: {self.code})'
