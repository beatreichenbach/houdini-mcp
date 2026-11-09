from __future__ import annotations

from typing import Any

from mcp.server.mcpserver import MCPServer

from houdini_mcp_protocol import PluginCommand

from ..bridge import HoudiniBridge
from .context import BridgeContext, run_command


def register_scene_tools(server: MCPServer[dict[str, HoudiniBridge]]) -> None:
    """Register scene-related tools on the server."""

    @server.tool()
    async def get_scene_info(ctx: BridgeContext) -> dict[str, Any]:
        """Return information about the current Houdini scene."""

        return await run_command(ctx, PluginCommand.SCENE_GET_SCENE_INFO)
