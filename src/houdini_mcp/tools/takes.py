"""MCP tool wrappers for Houdini takes (parameter override system)."""

from __future__ import annotations

from .context import BridgeContext, run_command
from .registry import tool


@tool
async def list_takes(ctx: BridgeContext) -> dict:
    """List all takes in the scene with their hierarchy."""

    return await run_command(ctx, 'takes.list_takes', {})


@tool
async def get_current_take(ctx: BridgeContext) -> dict:
    """Get the current take and its overridden parameters."""

    return await run_command(ctx, 'takes.get_current_take', {})


@tool
async def set_current_take(ctx: BridgeContext, name: str) -> dict:
    """Set the current take by name."""

    return await run_command(
        ctx,
        'takes.set_current_take',
        {
            'name': name,
        },
    )


@tool
async def create_take(
    ctx: BridgeContext,
    name: str,
    parent_name: str | None = None,
) -> dict:
    """Create a new take, optionally under a parent take."""

    params: dict = {'name': name}
    if parent_name is not None:
        params['parent_name'] = parent_name
    return await run_command(ctx, 'takes.create_take', params)
