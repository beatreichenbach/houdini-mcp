from __future__ import annotations

from typing import Any

from mcp.server.mcpserver import Context, MCPServer

from houdini_mcp_protocol import PluginCommand

from ..bridge import HoudiniBridge

BridgeContext = Context[dict[str, HoudiniBridge], Any]


def register_scene_tools(server: MCPServer[dict[str, HoudiniBridge]]) -> None:
    """Register scene-related tools on the server."""

    @server.tool()
    async def get_scene_info(ctx: BridgeContext) -> dict[str, Any]:
        """Return information about the current Houdini scene."""

        request_context = ctx.request_context
        if request_context is None:
            raise RuntimeError('no request context')
        bridge = request_context.lifespan_context['bridge']
        return await bridge.execute(PluginCommand.SCENE_GET_SCENE_INFO)
