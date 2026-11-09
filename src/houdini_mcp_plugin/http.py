from __future__ import annotations

import json
import logging
import os
from collections.abc import Callable
from typing import Any, TypeVar

import hwebserver

from houdini_mcp_plugin import __version__, dispatcher, security, startup
from houdini_mcp_protocol import PROTOCOL_VERSION, ErrorCode, Response, ResponseStatus

logger = logging.getLogger(__name__)

Function = TypeVar('Function', bound=Callable[..., Any])


def _api_function(namespace: str) -> Callable[[Function], Function]:
    """Register an hwebserver API function and return it."""

    def decorator(function: Function) -> Function:
        hwebserver.apiFunction(namespace=namespace)(function)
        return function

    return decorator


def _json_response(payload: dict[str, Any]) -> hwebserver.Response:
    """Encode a payload as an hwebserver JSON response."""

    body = json.dumps(payload, default=str)
    return hwebserver.Response(body.encode('utf-8'), 200, 'application/json')


def _forbidden(reason: str) -> hwebserver.Response:
    """Return a JSON 403 response."""

    payload = {
        'status': 'error',
        'error': {'code': ErrorCode.INVALID_REQUEST, 'message': reason},
    }
    body = json.dumps(payload, default=str)
    return hwebserver.Response(body.encode('utf-8'), 403, 'application/json')


def _guard(request: object) -> hwebserver.Response | None:
    """Return a 403 response unless the request comes from the local server."""

    try:
        headers = {
            str(name): str(value)
            for name, value in dict(getattr(request, 'headers')()).items()  # noqa: B009
        }
    except Exception:
        logger.debug('Could not read request headers', exc_info=True)
        headers = {}
    if security.request_allowed(headers):
        return None
    return _forbidden('request is not allowed from this origin')


@_api_function('mcp')
def execute(
    request: object,
    command: str = '',
    params: dict[str, Any] | None = None,
    request_id: str = '',
) -> hwebserver.Response:
    """Dispatch a command and return a protocol response."""

    denied = _guard(request)
    if denied is not None:
        return denied
    if not startup.is_running():
        response = Response(
            status=ResponseStatus.ERROR,
            error={
                'code': ErrorCode.INVALID_REQUEST,
                'message': 'the Houdini MCP plugin is not running',
            },
        )
        return _json_response(response.to_payload())

    response = dispatcher.dispatch(command, params or {})
    response.request_id = request_id
    return _json_response(response.to_payload())


@_api_function('mcp')
def health(request: object) -> hwebserver.Response:
    """Return plugin health without touching HOM."""

    denied = _guard(request)
    if denied is not None:
        return denied
    return _json_response(
        {
            'status': 'ok' if startup.is_running() else 'stopped',
            'pid': os.getpid(),
            'houdini_version': os.environ.get('HOUDINI_VERSION', 'unknown'),
            'protocol_version': PROTOCOL_VERSION,
            'plugin_version': __version__,
        }
    )


@_api_function('mcp')
def list_commands(request: object) -> hwebserver.Response:
    """Return the registered command names."""

    denied = _guard(request)
    if denied is not None:
        return denied
    return _json_response({'commands': dispatcher.list_commands()})
