from __future__ import annotations

from typing import Any

from mcp.server.mcpserver import Context
from mcp.server.mcpserver.exceptions import ToolError

from ..bridge import HoudiniBridge
from ..errors import HoudiniCommandError, HoudiniMCPError

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
) -> Any:  # noqa: ANN401
    """Run a Houdini command, reporting failures as tool errors."""

    try:
        return await get_bridge(ctx).execute(command, params)
    except HoudiniMCPError as exc:
        raise ToolError(_message(exc)) from exc


def _message(error: HoudiniMCPError) -> str:
    if isinstance(error, HoudiniCommandError):
        return f'{error} (code: {error.code})'
    return str(error)
