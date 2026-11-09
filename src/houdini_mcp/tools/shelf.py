"""MCP tools for Houdini's shelf tools."""

from __future__ import annotations

# Built-in
from typing import Any

# Third-party
# Internal
from .context import BridgeContext, run_command
from .registry import tool


@tool
async def list_shelf_tools(
    ctx: BridgeContext,
    filter: str | None = None,
    limit: int = 60,
) -> dict:
    """Find shelf tools by name, label or keyword."""

    params: dict[str, Any] = {'limit': limit}
    if filter is not None:
        params['filter'] = filter
    return await run_command(ctx, 'shelf.list_shelf_tools', params)


@tool
async def get_shelf_tool_script(ctx: BridgeContext, tool_name: str) -> dict:
    """Read the script a shelf tool runs, plus its help and imports."""

    return await run_command(
        ctx, 'shelf.get_shelf_tool_script', {'tool_name': tool_name}
    )


@tool
async def run_shelf_tool(
    ctx: BridgeContext,
    tool_name: str,
    kwargs: dict[str, Any] | None = None,
    parent_path: str | None = None,
    selection: list[str] | None = None,
    dop_network: str | None = None,
) -> dict:
    """Run a shelf tool and report the nodes it created."""

    params: dict[str, Any] = {'tool_name': tool_name}
    if kwargs is not None:
        params['kwargs'] = kwargs
    if parent_path is not None:
        params['parent_path'] = parent_path
    if selection is not None:
        params['selection'] = selection
    if dop_network is not None:
        params['dop_network'] = dop_network
    return await run_command(ctx, 'shelf.run_shelf_tool', params)
