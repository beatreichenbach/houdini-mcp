"""MCP tools for graph-level intelligence."""

from __future__ import annotations

from typing import Any

from ..bridge import NO_TIMEOUT
from .context import BridgeContext, run_command
from .registry import tool


@tool
async def build_network(
    ctx: BridgeContext,
    parent_path: str,
    nodes: list[dict[str, Any]],
    dry_run: bool = False,
    layout: bool = True,
) -> dict:
    """Build a whole node network in one atomic call."""

    return await run_command(
        ctx,
        'graph.build_network',
        {
            'parent_path': parent_path,
            'nodes': nodes,
            'dry_run': dry_run,
            'layout': layout,
        },
    )


@tool
async def verify_network(
    ctx: BridgeContext, parent_path: str, force_cook: bool = False
) -> dict:
    """Inspect every node in a network for errors and cook state."""

    return await run_command(
        ctx,
        'graph.verify_network',
        {'parent_path': parent_path, 'force_cook': force_cook},
    )


@tool
async def get_node_card(
    ctx: BridgeContext,
    node_type: str,
    context: str = 'Sop',
    parm_filter: str | None = None,
    include_help: bool | None = None,
) -> dict:
    """Return a node type's connectors, parameters, and help text."""

    params: dict[str, Any] = {'node_type': node_type, 'context': context}
    if parm_filter is not None:
        params['parm_filter'] = parm_filter
    # A filtered card is a question about a few parameters; the help text was
    # 5 of its 7 KB on a Pyro Solver.
    if include_help is None:
        include_help = parm_filter is None
    if not include_help:
        params['include_help'] = False
    return await run_command(ctx, 'graph.get_node_card', params)


@tool
async def find_expensive_nodes(
    ctx: BridgeContext,
    root_path: str = '/',
    frame: float | None = None,
    limit: int = 15,
) -> dict:
    """Profile cooking and rank the most expensive nodes."""

    params: dict[str, Any] = {'root_path': root_path, 'limit': limit}
    if frame is not None:
        params['frame'] = frame
    return await run_command(ctx, 'graph.find_expensive_nodes', params)


@tool
async def cook_frame_range(
    ctx: BridgeContext,
    node_path: str,
    start: float | None = None,
    end: float | None = None,
    step: float = 1.0,
    attribs: list[str] | None = None,
    volumes: bool = False,
) -> dict:
    """Cook a node frame by frame and report what changed on each frame."""

    params: dict[str, Any] = {
        'node_path': node_path,
        'step': step,
        'volumes': volumes,
    }
    if start is not None:
        params['start'] = start
    if end is not None:
        params['end'] = end
    if attribs is not None:
        params['attribs'] = attribs
    return await run_command(ctx, 'graph.cook_frame_range', params, timeout=NO_TIMEOUT)


@tool
async def get_cook_status(ctx: BridgeContext, node_path: str = '/obj') -> dict:
    """Whether a node has cooked, how often, and whether it is time dependent."""

    return await run_command(ctx, 'graph.get_cook_status', {'node_path': node_path})
