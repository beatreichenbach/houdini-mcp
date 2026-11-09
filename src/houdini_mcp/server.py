from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from mcp.server.mcpserver import MCPServer

from . import __version__
from .bridge import HoudiniBridge, set_bridge
from .config import Settings
from .prompts import build_instructions, load_content, register_prompts
from .resources import register_resources
from .tools import register_tools


def create_server(settings: Settings) -> MCPServer[dict[str, HoudiniBridge]]:
    """Create the Houdini MCP server."""

    content = load_content()

    @asynccontextmanager
    async def lifespan(
        _server: MCPServer[dict[str, HoudiniBridge]],
    ) -> AsyncGenerator[dict[str, HoudiniBridge], None]:
        bridge = HoudiniBridge(settings)
        try:
            await bridge.discover()
            set_bridge(bridge)
            yield {'bridge': bridge}
        finally:
            set_bridge(None)
            await bridge.close()

    server = MCPServer(
        name='Houdini MCP',
        version=__version__,
        instructions=build_instructions(content),
        lifespan=lifespan,
    )
    register_tools(server)
    register_resources(server)
    register_prompts(server, content)
    return server
