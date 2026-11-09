from __future__ import annotations

from collections.abc import Mapping

from houdini_mcp_protocol import REQUEST_HEADER, REQUEST_HEADER_VALUE


def request_allowed(headers: Mapping[str, str]) -> bool:
    """Return whether a request may access the local plugin API."""

    values = {str(name).lower(): str(value) for name, value in headers.items()}
    if 'origin' in values:
        return False
    if not _is_loopback_host(values.get('host', '')):
        return False
    return values.get(REQUEST_HEADER.lower()) == REQUEST_HEADER_VALUE


def _is_loopback_host(host: str) -> bool:
    host = host.lower()
    return host in {'127.0.0.1', 'localhost'} or host.startswith(
        ('127.0.0.1:', 'localhost:')
    )
