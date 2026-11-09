from __future__ import annotations

import json
import logging
import os
import time
import urllib.parse
import urllib.request
from typing import Any

import hou
import hwebserver

from houdini_mcp_plugin import constants
from houdini_mcp_protocol import PORT_SEARCH_RANGE, request_headers

logger = logging.getLogger(__name__)

_running = False
_port = constants.DEFAULT_PORT


def start(port: int | None = None) -> None:
    """Start the plugin HTTP server."""

    global _running, _port

    if _running:
        logger.info('Houdini MCP plugin is already running on port %d', _port)
        return

    base = port if port is not None else _configured_port()
    for candidate in range(base, base + PORT_SEARCH_RANGE):
        health = _query_health(constants.BIND_ADDRESS, candidate)
        if health is None:
            _port = candidate
            break
        if health.get('pid') == os.getpid():
            _port = candidate
            _running = True
            logger.info('Houdini MCP plugin resumed on port %d', _port)
            return
    else:
        raise RuntimeError(f'no free port in {base}-{base + PORT_SEARCH_RANGE - 1}')

    _bind_loopback()

    from houdini_mcp_plugin import commands, http  # noqa: F401

    in_background = hou.isUIAvailable()
    _running = True
    try:
        hwebserver.run(_port, debug=False, in_background=in_background)
        if in_background:
            _wait_until_healthy(_port)
        else:
            _running = False
    except Exception:
        _running = False
        raise

    if not in_background:
        logger.info('Houdini MCP plugin stopped')
        return
    logger.info('Houdini MCP plugin started on port %d', _port)


def pause() -> None:
    """Pause the plugin without stopping hwebserver."""

    global _running

    if not _running:
        return
    _running = False
    logger.info('Houdini MCP plugin paused')


def is_running() -> bool:
    return _running


def get_port() -> int:
    return _port


def ensure_running() -> None:
    """Start the plugin if it is not running."""

    if not _running:
        start()


def autostart_enabled() -> bool:
    """Return whether the plugin should start automatically."""

    value = os.getenv(constants.AUTOSTART)
    if value is None:
        return constants.DEFAULT_AUTOSTART
    return value.strip().lower() not in {'0', 'false', 'off', 'no'}


def _configured_port() -> int:
    """Return the configured port or the default."""

    value = os.getenv(constants.PORT)
    if value is None:
        return constants.DEFAULT_PORT
    try:
        return int(value)
    except ValueError:
        logger.debug('Invalid %s value: %r', constants.PORT, value, exc_info=True)
        return constants.DEFAULT_PORT


def _bind_loopback() -> None:
    """Restrict hwebserver to the loopback address."""

    try:
        hwebserver.setSettingsForPort(
            {
                'ADDRESS': constants.BIND_ADDRESS,
                'ALLOWED_HOSTS': list(constants.ALLOWED_HOSTS),
            },
            'main',
        )
    except Exception:
        logger.exception('Could not restrict Houdini MCP to %s', constants.BIND_ADDRESS)
        raise


def _wait_until_healthy(port: int, timeout: float = 2.0) -> None:
    """Wait for the plugin HTTP server to answer on a port."""

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        health = _query_health(constants.BIND_ADDRESS, port, timeout=0.2)
        if health is not None and health.get('pid') == os.getpid():
            return
        time.sleep(0.05)
    raise RuntimeError(f'Houdini MCP plugin did not start on port {port}')


def _query_health(
    host: str,
    port: int,
    timeout: float = 0.3,
) -> dict[str, Any] | None:
    """Return the plugin health payload for a port, or None."""

    host_part = f'[{host}]' if ':' in host else host
    request = urllib.request.Request(
        f'http://{host_part}:{port}/api',
        data=urllib.parse.urlencode(
            {'json': json.dumps(['mcp.health', [], {}])}
        ).encode('utf-8'),
        headers={
            **request_headers(),
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        method='POST',
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = response.read().decode('utf-8')
    except OSError:
        return None
    try:
        data = json.loads(payload)
    except ValueError:
        return None
    return data if isinstance(data, dict) else None
