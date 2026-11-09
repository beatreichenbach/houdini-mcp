"""MCP tool wrappers for Houdini PDG/TOPs operations."""

from __future__ import annotations

from .context import BridgeContext, run_command
from .registry import tool


@tool
async def get_top_network_info(ctx: BridgeContext, node_path: str) -> dict:
    """Get an overview of a TOP network."""

    return await run_command(ctx, 'tops.get_top_network_info', {'node_path': node_path})


@tool
async def cook_top_node(
    ctx: BridgeContext,
    node_path: str,
    block: bool = True,
    generate_only: bool = False,
) -> dict:
    """Cook a TOP node to execute its work items."""

    return await run_command(
        ctx,
        'tops.cook_top_node',
        {
            'node_path': node_path,
            'block': block,
            'generate_only': generate_only,
        },
    )


@tool
async def cancel_top_cook(ctx: BridgeContext, node_path: str) -> dict:
    """Cancel active cooking on a TOP network."""

    return await run_command(ctx, 'tops.cancel_top_cook', {'node_path': node_path})


@tool
async def pause_top_cook(ctx: BridgeContext, node_path: str) -> dict:
    """Pause cooking on a TOP network."""

    return await run_command(ctx, 'tops.pause_top_cook', {'node_path': node_path})


@tool
async def dirty_work_items(
    ctx: BridgeContext,
    node_path: str,
    remove_outputs: bool = False,
) -> dict:
    """Dirty work items on a TOP node so they can be regenerated."""

    return await run_command(
        ctx,
        'tops.dirty_work_items',
        {
            'node_path': node_path,
            'remove_outputs': remove_outputs,
        },
    )


@tool
async def get_work_item_states(ctx: BridgeContext, node_path: str) -> dict:
    """Get work item state counts for a TOP node."""

    return await run_command(ctx, 'tops.get_work_item_states', {'node_path': node_path})


@tool
async def get_work_item_info(
    ctx: BridgeContext,
    node_path: str,
    work_item_index: int,
) -> dict:
    """Get detailed information about a specific work item."""

    return await run_command(
        ctx,
        'tops.get_work_item_info',
        {
            'node_path': node_path,
            'work_item_index': work_item_index,
        },
    )


@tool
async def get_pdg_graph(ctx: BridgeContext, node_path: str) -> dict:
    """Get the PDG dependency graph structure for a TOP network."""

    return await run_command(ctx, 'tops.get_pdg_graph', {'node_path': node_path})


@tool
async def generate_static_items(ctx: BridgeContext, node_path: str) -> dict:
    """Generate static work items on a TOP node without cooking."""

    return await run_command(
        ctx, 'tops.generate_static_items', {'node_path': node_path}
    )


@tool
async def get_top_scheduler_info(ctx: BridgeContext, node_path: str) -> dict:
    """Get information about TOP scheduler nodes in a network."""

    return await run_command(
        ctx, 'tops.get_top_scheduler_info', {'node_path': node_path}
    )


@tool
async def get_failed_work_items(
    ctx: BridgeContext, node_path: str, limit: int = 10
) -> dict:
    """List the work items that failed on a TOP node, with the tail of each log."""

    return await run_command(
        ctx, 'tops.get_failed_work_items', {'node_path': node_path, 'limit': limit}
    )


@tool
async def get_top_logs(
    ctx: BridgeContext,
    node_path: str,
    work_item_index: int | None = None,
    tail: int = 4000,
) -> dict:
    """Cook logs for a TOP node, or the scheduler log of one work item."""

    params: dict = {'node_path': node_path, 'tail': tail}
    if work_item_index is not None:
        params['work_item_index'] = work_item_index
    return await run_command(ctx, 'tops.get_top_logs', params)
