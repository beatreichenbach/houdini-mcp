from .commands import PLUGIN_COMMANDS, ApiCommand, PluginCommand
from .errors import ErrorCode
from .models import Request, Response, ResponseStatus

PROTOCOL_VERSION = 1
PORT_SEARCH_RANGE = 16

REQUEST_HEADER = 'X-Houdini-MCP'
REQUEST_HEADER_VALUE = '1'


def request_headers() -> dict[str, str]:
    """Return the headers required by the local plugin API."""

    return {REQUEST_HEADER: REQUEST_HEADER_VALUE}


__all__ = [
    'PLUGIN_COMMANDS',
    'PORT_SEARCH_RANGE',
    'PROTOCOL_VERSION',
    'REQUEST_HEADER',
    'REQUEST_HEADER_VALUE',
    'ApiCommand',
    'ErrorCode',
    'PluginCommand',
    'Request',
    'Response',
    'ResponseStatus',
    'request_headers',
]
