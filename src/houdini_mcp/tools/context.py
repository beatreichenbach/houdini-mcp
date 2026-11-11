"""Shared context helpers for tool registration."""

from __future__ import annotations

from typing import Any

from mcp.server.mcpserver import Context
from mcp.server.mcpserver.exceptions import ToolError

from ..bridge import HoudiniBridge
from ..errors import HoudiniMCPError

BridgeContext = Context[dict[str, HoudiniBridge], Any]


def get_bridge(ctx: BridgeContext) -> HoudiniBridge:
    """Return the Houdini bridge from the request context."""

    request_context = ctx.request_context
    if request_context is None:
        raise ToolError('no request context')
    return request_context.lifespan_context['bridge']


async def run_command(
    ctx: BridgeContext,
    command: str,
    params: dict[str, Any] | None = None,
    timeout: float | None = None,
) -> Any:  # noqa: ANN401
    """Run a Houdini command, reporting failures as tool errors."""

    bridge = get_bridge(ctx)
    try:
        if timeout is None:
            return await bridge.execute(command, params)
        return await bridge.execute(command, params, timeout=timeout)
    except HoudiniMCPError as e:
        raise ToolError(str(e)) from e
