"""MCP tool wrappers for Houdini scene-understanding / context operations."""

from __future__ import annotations

from .context import BridgeContext, run_command
from .registry import tool


@tool
async def get_network_overview(
    ctx: BridgeContext,
    path: str = '/obj',
    depth: int = 2,
) -> dict:
    """Get a compact overview of a network."""

    return await run_command(
        ctx,
        'context.get_network_overview',
        {
            'path': path,
            'depth': depth,
        },
    )


@tool
async def get_cook_chain(ctx: BridgeContext, node_path: str) -> dict:
    """Trace the cook dependency chain for a node."""

    return await run_command(
        ctx,
        'context.get_cook_chain',
        {
            'node_path': node_path,
        },
    )


@tool
async def explain_node(ctx: BridgeContext, node_path: str) -> dict:
    """Explain a node in human-readable form."""

    return await run_command(
        ctx,
        'context.explain_node',
        {
            'node_path': node_path,
        },
    )


@tool
async def get_selection(ctx: BridgeContext) -> dict:
    """Get the current node selection."""

    return await run_command(ctx, 'context.get_selection')


@tool
async def set_selection(
    ctx: BridgeContext,
    node_paths: list[str] | None = None,
) -> dict:
    """Set the node selection."""

    params: dict = {}
    if node_paths is not None:
        params['node_paths'] = node_paths
    return await run_command(ctx, 'context.set_selection', params)


@tool
async def get_scene_summary(ctx: BridgeContext) -> dict:
    """Get a high-level summary of the scene."""

    return await run_command(ctx, 'context.get_scene_summary')


@tool
async def compare_snapshots(
    ctx: BridgeContext,
    action: str = 'take',
    snapshot_name: str = 'default',
) -> dict:
    """Take or compare scene state snapshots."""

    return await run_command(
        ctx,
        'context.compare_snapshots',
        {
            'action': action,
            'snapshot_name': snapshot_name,
        },
    )


@tool
async def get_node_errors_detailed(
    ctx: BridgeContext,
    node_path: str | None = None,
    root_path: str = '/',
) -> dict:
    """Get detailed error analysis for nodes."""

    params: dict = {'root_path': root_path}
    if node_path is not None:
        params['node_path'] = node_path
    return await run_command(ctx, 'context.get_node_errors_detailed', params)
