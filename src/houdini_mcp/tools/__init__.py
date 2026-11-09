"""Tool discovery and registration."""

from __future__ import annotations

import importlib
import logging
import pkgutil

from mcp.server.mcpserver import MCPServer

from ..bridge import HoudiniBridge
from .registry import marked_tools

logger = logging.getLogger(__name__)


def register_tools(server: MCPServer[dict[str, HoudiniBridge]]) -> None:
    """Discover and register every tool in this package."""

    seen: set[str] = set()
    for info in sorted(pkgutil.iter_modules(__path__), key=lambda item: item.name):
        if info.name.startswith('_'):
            continue
        module = importlib.import_module(f'{__name__}.{info.name}')
        for function in marked_tools(module):
            name = getattr(function, '__name__', '<tool>')
            if name in seen:
                raise ValueError(f'duplicate tool name: {name}')
            seen.add(name)
            server.tool()(function)

    logger.info('Registered %d tools', len(seen))


__all__ = ['register_tools']
