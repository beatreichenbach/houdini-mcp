from __future__ import annotations

from mcp.server.mcpserver import MCPServer

from ..bridge import HoudiniBridge
from .scene import register_scene_tools


def register_tools(server: MCPServer[dict[str, HoudiniBridge]]) -> None:
    """Register all MCP tools on the server."""

    register_scene_tools(server)


__all__ = ['register_tools']
