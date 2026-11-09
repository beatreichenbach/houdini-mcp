"""MCP tool definitions for animation operations."""

from __future__ import annotations

# Built-in
from typing import Any

# Third-party
# Internal
from .context import BridgeContext, run_command
from .registry import tool


@tool
async def set_keyframe(
    ctx: BridgeContext,
    node_path: str,
    parm_name: str,
    frame: float,
    value: float,
    slope: float | None = None,
    accel: float | None = None,
) -> dict:
    """Set a single keyframe on a parameter."""

    params: dict[str, Any] = {
        'node_path': node_path,
        'parm_name': parm_name,
        'frame': frame,
        'value': value,
    }
    if slope is not None:
        params['slope'] = slope
    if accel is not None:
        params['accel'] = accel
    return await run_command(ctx, 'animation.set_keyframe', params)


@tool
async def set_keyframes(
    ctx: BridgeContext,
    node_path: str,
    parm_name: str,
    keyframes: list[dict],
) -> dict:
    """Batch-set multiple keyframes on a parameter."""

    return await run_command(
        ctx,
        'animation.set_keyframes',
        {
            'node_path': node_path,
            'parm_name': parm_name,
            'keyframes': keyframes,
        },
    )


@tool
async def delete_keyframe(
    ctx: BridgeContext,
    node_path: str,
    parm_name: str,
    frame: float,
) -> dict:
    """Delete a keyframe at a specific frame."""

    return await run_command(
        ctx,
        'animation.delete_keyframe',
        {'node_path': node_path, 'parm_name': parm_name, 'frame': frame},
    )


@tool
async def get_keyframes(
    ctx: BridgeContext,
    node_path: str,
    parm_name: str,
) -> dict:
    """Get all keyframes on a parameter."""

    return await run_command(
        ctx,
        'animation.get_keyframes',
        {'node_path': node_path, 'parm_name': parm_name},
    )


@tool
async def set_frame(ctx: BridgeContext, frame: float) -> dict:
    """Set the current frame in the timeline."""

    return await run_command(ctx, 'animation.set_frame', {'frame': frame})


@tool
async def get_frame(ctx: BridgeContext) -> dict:
    """Get the current frame and FPS."""

    return await run_command(ctx, 'animation.get_frame', {})


@tool
async def set_frame_range(ctx: BridgeContext, start: float, end: float) -> dict:
    """Set the global frame range."""

    return await run_command(
        ctx,
        'animation.set_frame_range',
        {'start': start, 'end': end},
    )


@tool
async def set_playback_range(ctx: BridgeContext, start: float, end: float) -> dict:
    """Set the playback range (green bar in the timeline)."""

    return await run_command(
        ctx,
        'animation.set_playback_range',
        {'start': start, 'end': end},
    )


@tool
async def playbar_control(
    ctx: BridgeContext,
    action: str,
    real_time: bool | None = None,
    fps: float | None = None,
) -> dict:
    """Control playback: play, stop, or reverse."""

    params: dict[str, Any] = {'action': action}
    if real_time is not None:
        params['real_time'] = real_time
    if fps is not None:
        params['fps'] = fps
    return await run_command(ctx, 'animation.playbar_control', params)
