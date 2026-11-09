"""MCP tool wrappers for Houdini CHOP (Channel Operator) operations."""

from __future__ import annotations

from typing import Any

from .context import BridgeContext, run_command
from .registry import tool


@tool
async def get_chop_data(
    ctx: BridgeContext,
    node_path: str,
    channel_name: str | None = None,
    start: int | None = None,
    end: int | None = None,
) -> dict:
    """Get CHOP node track data."""

    params: dict[str, Any] = {'node_path': node_path}
    if channel_name is not None:
        params['channel_name'] = channel_name
    if start is not None:
        params['start'] = start
    if end is not None:
        params['end'] = end
    return await run_command(ctx, 'chops.get_chop_data', params)


@tool
async def create_chop_node(
    ctx: BridgeContext,
    parent_path: str,
    chop_type: str,
    name: str | None = None,
) -> dict:
    """Create a new CHOP node."""

    params: dict[str, Any] = {
        'parent_path': parent_path,
        'chop_type': chop_type,
    }
    if name is not None:
        params['name'] = name
    return await run_command(ctx, 'chops.create_chop_node', params)


@tool
async def list_chop_channels(ctx: BridgeContext, node_path: str) -> dict:
    """List all channels on a CHOP node."""

    return await run_command(
        ctx,
        'chops.list_chop_channels',
        {
            'node_path': node_path,
        },
    )


@tool
async def export_chop_to_parm(
    ctx: BridgeContext,
    chop_path: str,
    channel_name: str,
    target_node_path: str,
    target_parm_name: str,
) -> dict:
    """Export a CHOP channel to a parameter via a chop() expression."""

    return await run_command(
        ctx,
        'chops.export_chop_to_parm',
        {
            'chop_path': chop_path,
            'channel_name': channel_name,
            'target_node_path': target_node_path,
            'target_parm_name': target_parm_name,
        },
    )
