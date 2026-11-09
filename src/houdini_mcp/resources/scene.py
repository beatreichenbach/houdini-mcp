from __future__ import annotations

from typing import Any

from mcp.server.mcpserver import MCPServer, ResourceSecurity

from houdini_mcp_protocol import PluginCommand

from ..bridge import HoudiniBridge
from .context import run_command


def register_scene_resources(server: MCPServer[dict[str, HoudiniBridge]]) -> None:
    """Register resources for the current Houdini scene."""

    @server.resource(
        'houdini-mcp://scene',
        name='scene-info',
        description='Current Houdini scene information.',
        mime_type='application/json',
    )
    async def scene_info() -> dict[str, Any]:
        return await run_command(PluginCommand.SCENE_GET_SCENE_INFO)

    @server.resource(
        'houdini-mcp://scene/selection',
        name='scene-selection',
        description='Nodes selected in the current Houdini session.',
        mime_type='application/json',
    )
    async def scene_selection() -> dict[str, Any]:
        return await run_command(PluginCommand.SCENE_GET_SELECTION)

    @server.resource(
        'houdini-mcp://scene/nodes',
        name='scene-nodes',
        description='Top-level nodes in the current Houdini scene.',
        mime_type='application/json',
    )
    async def scene_nodes() -> dict[str, Any]:
        return await run_command(PluginCommand.SCENE_GET_NODE, {'path': '/'})

    @server.resource(
        'houdini-mcp://scene/nodes{+path}',
        name='scene-node',
        description='Details for the node at the path appended to this URI.',
        mime_type='application/json',
        security=ResourceSecurity(reject_absolute_paths=False),
    )
    async def scene_node(path: str) -> dict[str, Any]:
        return await run_command(PluginCommand.SCENE_GET_NODE, {'path': path or '/'})
