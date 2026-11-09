"""Scene tools."""

from __future__ import annotations

from typing import Any

from .context import BridgeContext, run_command
from .registry import tool


@tool
async def get_scene_info(ctx: BridgeContext) -> dict:
    """Get information about the current Houdini scene."""

    return await run_command(ctx, 'scene.get_scene_info')


@tool
async def new_scene(ctx: BridgeContext, save_current: bool = False) -> dict:
    """Create a new empty Houdini scene."""

    return await run_command(ctx, 'scene.new_scene', {'save_current': save_current})


@tool
async def save_scene(ctx: BridgeContext, file_path: str | None = None) -> dict:
    """Save the current Houdini scene to disk."""

    params: dict = {}
    if file_path is not None:
        params['file_path'] = file_path
    return await run_command(ctx, 'scene.save_scene', params)


@tool
async def load_scene(
    ctx: BridgeContext,
    file_path: str,
    merge: bool = False,
    node_paths: list[str] | None = None,
    overwrite_on_conflict: bool = False,
) -> dict:
    """Open a hip file, or merge it into the current scene."""

    payload: dict[str, Any] = {'file_path': file_path, 'merge': merge}
    # Sent only when used, so a plugin that predates them still loads and
    # merges whole files.
    if node_paths is not None:
        payload['node_paths'] = node_paths
    if overwrite_on_conflict:
        payload['overwrite_on_conflict'] = True
    return await run_command(ctx, 'scene.load_scene', payload)


@tool
async def import_file(
    ctx: BridgeContext,
    file_path: str,
    parent_path: str = '/obj',
    node_name: str | None = None,
) -> dict:
    """Import a geometry, USD, or Alembic file into the scene."""

    params: dict = {
        'file_path': file_path,
        'parent_path': parent_path,
    }
    if node_name is not None:
        params['node_name'] = node_name
    return await run_command(ctx, 'scene.import_file', params)


@tool
async def export_file(
    ctx: BridgeContext,
    node_path: str,
    file_path: str,
    frame_range: list[float] | None = None,
) -> dict:
    """Export a node's output to a file on disk, and report whether it landed."""

    params: dict = {
        'node_path': node_path,
        'file_path': file_path,
    }
    if frame_range is not None:
        params['frame_range'] = frame_range
    return await run_command(ctx, 'scene.export_file', params)


@tool
async def get_context_info(ctx: BridgeContext, context: str) -> dict:
    """Get information about a Houdini network context."""

    return await run_command(ctx, 'scene.get_context_info', {'context': context})


@tool
async def undo(ctx: BridgeContext, steps: int = 1) -> dict:
    """Undo the last change(s) made in Houdini."""

    return await run_command(ctx, 'scene.undo', {'steps': steps})


@tool
async def redo(ctx: BridgeContext, steps: int = 1) -> dict:
    """Redo the last undone change(s) in Houdini."""

    return await run_command(ctx, 'scene.redo', {'steps': steps})
