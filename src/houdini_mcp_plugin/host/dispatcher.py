from __future__ import annotations

import contextlib
import inspect
import logging
import threading
import time
import traceback
from collections.abc import Callable, Generator
from typing import Any

import hdefereval

from houdini_mcp_protocol import ErrorCode, Response, ResponseStatus

from ..serialize import to_jsonable

logger = logging.getLogger(__name__)

Handler = Callable[..., Any]

_registry: dict[str, Handler] = {}
_registry_lock = threading.RLock()
_NO_UNDO_GROUP = frozenset({'scene.undo', 'scene.redo'})


def register_command(name: str) -> Callable[[Handler], Handler]:
    """Register a handler for a command name."""

    def decorator(handler: Handler) -> Handler:
        with _registry_lock:
            _registry[str(name)] = handler
        return handler

    return decorator


def list_commands() -> list[str]:
    """Return the registered command names."""

    with _registry_lock:
        return sorted(_registry)


def dispatch(command: str, params: dict[str, Any]) -> Response:
    """Run a command and return a protocol response."""

    with _registry_lock:
        handler = _registry.get(command)
    if handler is None:
        return Response(
            status=ResponseStatus.ERROR,
            error={
                'code': ErrorCode.UNKNOWN_COMMAND,
                'message': f'no handler registered for command: {command}',
                'available_commands': list_commands(),
            },
        )

    started = time.monotonic()
    try:
        inspect.signature(handler).bind(**params)
    except TypeError as e:
        return Response(
            status=ResponseStatus.ERROR,
            error={
                'code': ErrorCode.BAD_ARGUMENTS,
                'message': f'{command} received invalid arguments: {e}',
            },
            timing_ms=_elapsed(started),
        )

    try:
        data = _run_handler(handler, command, params)
    except Exception as e:
        logger.exception('Houdini command failed: %s', command)
        return Response(
            status=ResponseStatus.ERROR,
            error={
                'code': ErrorCode.COMMAND_ERROR,
                'message': str(e),
                'traceback': traceback.format_exc(),
            },
            timing_ms=_elapsed(started),
        )

    return Response(
        status=ResponseStatus.SUCCESS,
        data=to_jsonable(data),
        timing_ms=_elapsed(started),
    )


def _elapsed(started: float) -> float:
    """Return elapsed milliseconds since a monotonic timestamp."""

    return round((time.monotonic() - started) * 1000, 2)


def _run_handler(handler: Handler, command: str, params: dict[str, Any]) -> Any:
    """Run a handler on Houdini's main thread."""

    return hdefereval.executeInMainThreadWithResult(
        lambda: _call_handler(handler, command, params)
    )


def _call_handler(handler: Handler, command: str, params: dict[str, Any]) -> Any:
    """Call a handler inside an undo group."""

    if command in _NO_UNDO_GROUP:
        return handler(**params)
    with _undo_group(command):
        return handler(**params)


@contextlib.contextmanager
def _undo_group(command: str) -> Generator[None, None, None]:
    """Group a command's Houdini changes into one undo step."""

    try:
        import hou

        group = hou.undos.group(f'MCP {command}')
    except Exception:
        logger.debug('Could not open an undo group for %s', command, exc_info=True)
        group = None
    if group is None:
        yield
        return
    with group:
        yield
