"""MCP tool definitions for Houdini viewport and UI operations."""

from __future__ import annotations

import asyncio
import os
import tempfile
import time
from typing import Any

from .context import BridgeContext, run_command
from .registry import tool


def capture_path(output_path: str | None, prefix: str) -> str:
    """``output_path``, or a fresh PNG under the temp dir when none was given."""

    if output_path:
        return output_path
    folder = os.path.join(tempfile.gettempdir(), 'houdini_mcp')
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, f'{prefix}_{time.time_ns() // 1_000_000}.png')


@tool
async def list_panes(ctx: BridgeContext) -> dict:
    """List all visible pane tabs in the Houdini UI."""

    return await run_command(ctx, 'viewport.list_panes', {})


@tool
async def get_viewport_info(
    ctx: BridgeContext,
    pane_name: str | None = None,
) -> dict:
    """Get viewport settings for a pane tab."""

    params: dict[str, Any] = {}
    if pane_name is not None:
        params['pane_name'] = pane_name
    return await run_command(ctx, 'viewport.get_viewport_info', params)


@tool
async def set_viewport_camera(
    ctx: BridgeContext,
    camera_path: str,
    pane_name: str | None = None,
) -> dict:
    """Set the viewport to look through a specific camera."""

    params: dict[str, Any] = {'camera_path': camera_path}
    if pane_name is not None:
        params['pane_name'] = pane_name
    return await run_command(ctx, 'viewport.set_viewport_camera', params)


@tool
async def set_viewport_display(
    ctx: BridgeContext,
    display_mode: str | None = None,
    pane_name: str | None = None,
    environment_background: bool | None = None,
    reference_plane: bool | None = None,
    point_size: float | None = None,
    color_scheme: str | None = None,
) -> dict:
    """Set how the viewport draws and return the applied settings."""

    params: dict[str, Any] = {}
    for key, value in (
        ('display_mode', display_mode),
        ('pane_name', pane_name),
        ('environment_background', environment_background),
        ('reference_plane', reference_plane),
        ('point_size', point_size),
        ('color_scheme', color_scheme),
    ):
        if value is not None:
            params[key] = value
    return await run_command(ctx, 'viewport.set_viewport_display', params)


@tool
async def set_viewport_renderer(
    ctx: BridgeContext,
    renderer: str,
    pane_name: str | None = None,
) -> dict:
    """Set the viewport's Hydra rendering delegate for live preview."""

    params: dict[str, Any] = {'renderer': renderer}
    if pane_name is not None:
        params['pane_name'] = pane_name
    return await run_command(ctx, 'viewport.set_viewport_renderer', params)


@tool
async def frame_selection(
    ctx: BridgeContext,
    pane_name: str | None = None,
) -> dict:
    """Frame the current selection in the viewport."""

    params: dict[str, Any] = {}
    if pane_name is not None:
        params['pane_name'] = pane_name
    return await run_command(ctx, 'viewport.frame_selection', params)


@tool
async def frame_all(
    ctx: BridgeContext,
    pane_name: str | None = None,
    node_paths: list[str] | None = None,
    bounds: list[float] | None = None,
) -> dict:
    """Frame all geometry in the viewport, or only some nodes or a box."""

    params: dict[str, Any] = {}
    for key, value in (
        ('pane_name', pane_name),
        ('node_paths', node_paths),
        ('bounds', bounds),
    ):
        if value is not None:
            params[key] = value
    return await run_command(ctx, 'viewport.frame_all', params)


@tool
async def set_viewport_direction(
    ctx: BridgeContext,
    direction: str | None = None,
    pane_name: str | None = None,
    rotation: list[float] | None = None,
    pivot: list[float] | None = None,
    distance: float | None = None,
) -> dict:
    """Set the viewport to a standard viewing direction, or place the free view."""

    params: dict[str, Any] = {}
    for key, value in (
        ('direction', direction),
        ('pane_name', pane_name),
        ('rotation', rotation),
        ('pivot', pivot),
        ('distance', distance),
    ):
        if value is not None:
            params[key] = value
    return await run_command(ctx, 'viewport.set_viewport_direction', params)


@tool
async def capture_screenshot(
    ctx: BridgeContext,
    output_path: str | None = None,
    pane_name: str | None = None,
    settle_seconds: float = 0,
) -> dict:
    """Capture a screenshot of the viewport or a specific pane tab."""

    if settle_seconds > 0:
        await asyncio.sleep(min(settle_seconds, 120))
    params: dict[str, Any] = {'output_path': capture_path(output_path, 'screenshot')}
    if pane_name is not None:
        params['pane_name'] = pane_name
    return await run_command(ctx, 'viewport.capture_screenshot', params)


@tool
async def capture_network_editor(
    ctx: BridgeContext,
    output_path: str | None = None,
    node_path: str | None = None,
) -> dict:
    """Capture a screenshot of the network editor."""

    params: dict[str, Any] = {'output_path': capture_path(output_path, 'network')}
    if node_path is not None:
        params['node_path'] = node_path
    return await run_command(ctx, 'viewport.capture_network_editor', params)


@tool
async def set_current_network(
    ctx: BridgeContext,
    network_path: str,
    other_objects: str | None = 'hide',
) -> dict:
    """Navigate the network editor to a network; the viewer follows it in."""

    return await run_command(
        ctx,
        'viewport.set_current_network',
        {'network_path': network_path, 'other_objects': other_objects},
    )


@tool
async def find_error_nodes(
    ctx: BridgeContext,
    root_path: str = '/',
) -> dict:
    """Find all nodes with errors or warnings in the scene."""

    return await run_command(
        ctx,
        'viewport.find_error_nodes',
        {'root_path': root_path},
    )


@tool
async def log_status(
    ctx: BridgeContext,
    message: str,
    severity: str = 'message',
) -> dict:
    """Display a status message in Houdini's status bar."""

    return await run_command(
        ctx,
        'viewport.log_status',
        {'message': message, 'severity': severity},
    )


@tool
async def set_viewer_context(
    ctx: BridgeContext,
    network_path: str,
    current_node: str | None = None,
    pane_name: str | None = None,
) -> dict:
    """Point the Scene Viewer at a network, and optionally a node inside it."""

    params: dict[str, Any] = {'network_path': network_path}
    if current_node is not None:
        params['current_node'] = current_node
    if pane_name is not None:
        params['pane_name'] = pane_name
    return await run_command(ctx, 'viewport.set_viewer_context', params)
