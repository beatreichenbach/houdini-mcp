from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from mcp.server.mcpserver import MCPServer

from . import __version__
from .bridge import HoudiniBridge
from .config import Settings


def create_server(settings: Settings) -> MCPServer[dict[str, HoudiniBridge]]:
    @asynccontextmanager
    async def lifespan(
        _server: MCPServer[dict[str, HoudiniBridge]],
    ) -> AsyncGenerator[dict[str, HoudiniBridge], None]:
        bridge = HoudiniBridge(settings)
        await bridge.discover()
        try:
            yield {'bridge': bridge}
        finally:
            await bridge.close()

    return MCPServer(
        name='Houdini MCP',
        version=__version__,
        lifespan=lifespan,
    )
