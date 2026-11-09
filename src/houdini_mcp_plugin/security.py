from __future__ import annotations

from collections.abc import Mapping

from houdini_mcp_protocol import REQUEST_HEADER, REQUEST_HEADER_VALUE


def request_allowed(headers: Mapping[str, str], port: int) -> bool:
    """Return whether a request may access the local plugin API."""

    values = {str(name).lower(): str(value) for name, value in headers.items()}
    if 'origin' in values:
        return False
    allowed_hosts = {f'127.0.0.1:{port}', f'localhost:{port}'}
    if values.get('host', '').lower() not in allowed_hosts:
        return False
    return values.get(REQUEST_HEADER.lower()) == REQUEST_HEADER_VALUE
