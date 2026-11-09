from __future__ import annotations

from mcp.server.mcpserver import MCPServer

from ..bridge import HoudiniBridge
from .scene import register_scene_resources


def register_resources(server: MCPServer[dict[str, HoudiniBridge]]) -> None:
    """Register all server resources."""

    register_scene_resources(server)


__all__ = ['register_resources']
