"""MCP tool wrappers for Houdini cache management operations."""

from __future__ import annotations

# Built-in
from typing import Any

# Third-party
# Internal
from ..bridge import NO_TIMEOUT
from .context import BridgeContext, run_command
from .registry import tool


@tool
async def list_caches(
    ctx: BridgeContext,
    root_path: str = '/',
) -> dict:
    """List all cache-type nodes under a root path."""

    return await run_command(
        ctx,
        'cache.list_caches',
        {
            'root_path': root_path,
        },
    )


@tool
async def get_cache_status(ctx: BridgeContext, node_path: str) -> dict:
    """Frames on disk for a cache node, against the range it is set to write."""

    return await run_command(
        ctx,
        'cache.get_cache_status',
        {
            'node_path': node_path,
        },
    )


@tool
async def clear_cache(
    ctx: BridgeContext,
    node_path: str,
    frame_range: list[int] | None = None,
) -> dict:
    """Delete cached files on disk for a cache node."""

    params: dict[str, Any] = {'node_path': node_path}
    if frame_range is not None:
        params['frame_range'] = frame_range
    return await run_command(ctx, 'cache.clear_cache', params)


@tool
async def write_cache(
    ctx: BridgeContext,
    node_path: str,
    frame_range: list[int] | None = None,
    background: bool = False,
) -> dict:
    """Execute a cache node, and report whether a cache actually appeared."""

    params: dict[str, Any] = {'node_path': node_path, 'background': background}
    if frame_range is not None:
        params['frame_range'] = frame_range
    return await run_command(ctx, 'cache.write_cache', params, timeout=NO_TIMEOUT)
