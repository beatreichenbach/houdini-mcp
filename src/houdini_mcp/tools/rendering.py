"""MCP tool definitions for Houdini rendering operations."""

from __future__ import annotations

import asyncio
from typing import Any

from ..bridge import NO_TIMEOUT
from .context import BridgeContext, run_command
from .registry import tool
from .viewport import capture_path


@tool
async def render_viewport(
    ctx: BridgeContext,
    output_path: str | None = None,
    resolution: list[int] | None = None,
    camera: str | None = None,
    settle_seconds: float = 0,
) -> dict:
    """Capture the current 3D viewport to an image file."""

    if settle_seconds > 0:
        await asyncio.sleep(min(settle_seconds, 120))
    params: dict[str, Any] = {'output_path': capture_path(output_path, 'viewport')}
    if resolution is not None:
        params['resolution'] = resolution
    if camera is not None:
        params['camera'] = camera
    return await run_command(ctx, 'rendering.render_viewport', params)


@tool
async def render_quad_view(
    ctx: BridgeContext,
    output_path: str | None = None,
    resolution: list[int] | None = None,
) -> dict:
    """Capture all four viewport panes to separate images."""

    params: dict[str, Any] = {'output_path': capture_path(output_path, 'quad')}
    if resolution is not None:
        params['resolution'] = resolution
    return await run_command(ctx, 'rendering.render_quad_view', params)


@tool
async def list_render_nodes(ctx: BridgeContext) -> dict:
    """List all render (ROP/Driver) nodes in the scene."""

    return await run_command(ctx, 'rendering.list_render_nodes', {})


@tool
async def get_render_settings(ctx: BridgeContext, node_path: str) -> dict:
    """Get render settings from a ROP node."""

    return await run_command(
        ctx, 'rendering.get_render_settings', {'node_path': node_path}
    )


@tool
async def set_render_settings(
    ctx: BridgeContext,
    node_path: str,
    settings: dict[str, Any] | None = None,
) -> dict:
    """Set render parameters on a ROP node."""

    # The default was a mutable {} literal. None is the safe default, but the
    # handler is still sent a dict, so the wire format does not change.
    return await run_command(
        ctx,
        'rendering.set_render_settings',
        {'node_path': node_path, 'settings': settings or {}},
    )


@tool
async def create_render_node(
    ctx: BridgeContext,
    renderer: str,
    name: str | None = None,
    camera: str | None = None,
    output_path: str | None = None,
) -> dict:
    """Create a new render (ROP) node in /out."""

    params: dict[str, Any] = {'renderer': renderer}
    if name is not None:
        params['name'] = name
    if camera is not None:
        params['camera'] = camera
    if output_path is not None:
        params['output_path'] = output_path
    return await run_command(ctx, 'rendering.create_render_node', params)


# How long a render that wrote nothing is watched for the error husk posts late.
_ERROR_POLLS = 10
_ERROR_POLL_SECONDS = 0.5


@tool
async def start_render(
    ctx: BridgeContext,
    node_path: str,
    frame_range: list[float] | None = None,
    background: bool = False,
    overrides: dict[str, Any] | None = None,
) -> dict:
    """Execute any node that renders or writes files."""

    params: dict[str, Any] = {'node_path': node_path, 'background': background}
    if frame_range is not None:
        params['frame_range'] = frame_range
    if overrides:
        params['overrides'] = overrides
    result = await run_command(
        ctx, 'rendering.start_render', params, timeout=NO_TIMEOUT
    )
    if (
        isinstance(result, dict)
        and result.get('success') is False
        and not result.get('errors')
    ):
        # A usdrender_rop gets husk's exit error (a missing license, a bad
        # scene) some time after render() returns: measured on 22.0.368, an
        # immediate follow-up still saw none. Poll briefly without blocking
        # Houdini, so "reported no errors" is not said about a render that
        # failed on one.
        progress: Any = None
        for _ in range(_ERROR_POLLS):
            await asyncio.sleep(_ERROR_POLL_SECONDS)
            progress = await run_command(
                ctx, 'rendering.get_render_progress', {'node_path': node_path}
            )
            if isinstance(progress, dict) and progress.get('errors'):
                break
        if isinstance(progress, dict) and progress.get('errors'):
            result['errors'] = progress['errors']
            result['license_error'] = progress.get('license_error')
            result['message'] = (
                'Render failed: '
                + (
                    'no license for the renderer'
                    if progress.get('license_error')
                    else 'the ROP reported errors'
                )
                + '; nothing was written.'
            )
    return result


@tool
async def render_node_network(
    ctx: BridgeContext,
    node_path: str,
    output_path: str | None = None,
) -> dict:
    """Capture a screenshot of a node's network editor view."""

    return await run_command(
        ctx,
        'rendering.render_node_network',
        {'node_path': node_path, 'output_path': capture_path(output_path, 'network')},
    )


@tool
async def get_render_progress(ctx: BridgeContext, node_path: str) -> dict:
    """Progress of a render or write started with start_render."""

    return await run_command(
        ctx, 'rendering.get_render_progress', {'node_path': node_path}
    )
