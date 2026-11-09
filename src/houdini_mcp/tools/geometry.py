"""MCP tools for SOP geometry inspection and manipulation."""

from __future__ import annotations

# Built-in
from typing import Any

from ..bridge import NO_TIMEOUT

# Third-party
# Internal
from ..types import Value
from .context import BridgeContext, run_command
from .registry import tool


@tool
async def get_geometry_info(
    ctx: BridgeContext, node_path: str, output_index: int = 0
) -> dict:
    """Get geometry summary for a SOP node."""

    return await run_command(
        ctx,
        'geometry.get_geometry_info',
        {'node_path': node_path, 'output_index': output_index},
    )


@tool
async def get_points(
    ctx: BridgeContext,
    node_path: str,
    attributes: list[str] | None = None,
    start: int = 0,
    count: int = 200,
    group: str | None = None,
) -> dict:
    """Read point positions and attributes with pagination."""

    params: dict[str, Any] = {
        'node_path': node_path,
        'start': start,
        'count': count,
    }
    if attributes is not None:
        params['attributes'] = attributes
    if group is not None:
        params['group'] = group
    return await run_command(ctx, 'geometry.get_points', params)


@tool
async def get_prims(
    ctx: BridgeContext,
    node_path: str,
    attributes: list[str] | None = None,
    start: int = 0,
    count: int = 200,
    group: str | None = None,
) -> dict:
    """Read primitive data and attributes with pagination."""

    params: dict[str, Any] = {
        'node_path': node_path,
        'start': start,
        'count': count,
    }
    if attributes is not None:
        params['attributes'] = attributes
    if group is not None:
        params['group'] = group
    return await run_command(ctx, 'geometry.get_prims', params)


@tool
async def get_attrib_values(
    ctx: BridgeContext,
    node_path: str,
    attrib_name: str,
    attrib_class: str = 'point',
    start: int = 0,
    count: int = 200,
) -> dict:
    """Read attribute values as a flat array with pagination."""

    return await run_command(
        ctx,
        'geometry.get_attrib_values',
        {
            'node_path': node_path,
            'attrib_name': attrib_name,
            'attrib_class': attrib_class,
            'start': start,
            'count': count,
        },
    )


@tool
async def set_detail_attrib(
    ctx: BridgeContext,
    node_path: str,
    attrib_name: str,
    value: Value,
) -> dict:
    """Set a detail attribute on a SOP node."""

    return await run_command(
        ctx,
        'geometry.set_detail_attrib',
        {
            'node_path': node_path,
            'attrib_name': attrib_name,
            'value': value,
        },
    )


@tool
async def get_groups(ctx: BridgeContext, node_path: str) -> dict:
    """List all geometry groups on a SOP node."""

    return await run_command(
        ctx,
        'geometry.get_groups',
        {
            'node_path': node_path,
        },
    )


@tool
async def get_group_members(
    ctx: BridgeContext,
    node_path: str,
    group_name: str,
    group_type: str = 'point',
    start: int = 0,
    count: int = 5000,
) -> dict:
    """Get element indices in a geometry group, with pagination."""

    return await run_command(
        ctx,
        'geometry.get_group_members',
        {
            'node_path': node_path,
            'group_name': group_name,
            'group_type': group_type,
            'start': start,
            'count': count,
        },
    )


@tool
async def get_bounding_box(ctx: BridgeContext, node_path: str) -> dict:
    """Get the bounding box of a SOP node's geometry."""

    return await run_command(
        ctx,
        'geometry.get_bounding_box',
        {
            'node_path': node_path,
        },
    )


@tool
async def get_attribute_info(
    ctx: BridgeContext,
    node_path: str,
    attrib_name: str,
    attrib_class: str = 'point',
) -> dict:
    """Get metadata for a geometry attribute."""

    return await run_command(
        ctx,
        'geometry.get_attribute_info',
        {
            'node_path': node_path,
            'attrib_name': attrib_name,
            'attrib_class': attrib_class,
        },
    )


@tool
async def sample_geometry(
    ctx: BridgeContext,
    node_path: str,
    sample_count: int = 100,
    seed: int = 0,
) -> dict:
    """Sample evenly distributed points from a SOP node's geometry."""

    return await run_command(
        ctx,
        'geometry.sample_geometry',
        {
            'node_path': node_path,
            'sample_count': sample_count,
            'seed': seed,
        },
    )


@tool
async def get_prim_intrinsics(
    ctx: BridgeContext,
    node_path: str,
    prim_index: int | None = None,
    prim_indices: list[int] | None = None,
    prim_range: list[int] | None = None,
    intrinsics: list[str] | None = None,
) -> dict:
    """Get intrinsic values for primitives: one, many, or all of them."""

    params: dict[str, Any] = {'node_path': node_path}
    if prim_index is not None:
        params['prim_index'] = prim_index
    if prim_indices is not None:
        params['prim_indices'] = prim_indices
    if prim_range is not None:
        params['prim_range'] = prim_range
    if intrinsics is not None:
        params['intrinsics'] = intrinsics
    return await run_command(ctx, 'geometry.get_prim_intrinsics', params)


@tool
async def find_nearest_point(
    ctx: BridgeContext,
    node_path: str,
    position: list[float],
    max_results: int = 1,
) -> dict:
    """Find the nearest point(s) to a given position."""

    return await run_command(
        ctx,
        'geometry.find_nearest_point',
        {
            'node_path': node_path,
            'position': position,
            'max_results': max_results,
        },
    )


@tool
async def get_attrib_stats(
    ctx: BridgeContext,
    node_path: str | None = None,
    attribs: list[str] | None = None,
    attrib_class: str = 'point',
    frames: list[float] | None = None,
    node_paths: list[str] | None = None,
    percentiles: list[float] | None = None,
    group: str | None = None,
    unique: bool = False,
    distance_to: str | None = None,
) -> dict:
    """Aggregate statistics for numeric attributes: min, max, mean, sum."""

    params: dict[str, Any] = {'attrib_class': attrib_class}
    if group is not None:
        params['group'] = group
    if unique:
        params['unique'] = True
    if distance_to is not None:
        params['distance_to'] = distance_to
    for key, value in (
        ('node_path', node_path),
        ('attribs', attribs),
        ('frames', frames),
        ('node_paths', node_paths),
        ('percentiles', percentiles),
    ):
        if value is not None:
            params[key] = value
    if frames or node_paths:
        # Several frames of a simulation cook as long as they take.
        return await run_command(
            ctx, 'geometry.get_attrib_stats', params, timeout=NO_TIMEOUT
        )
    return await run_command(ctx, 'geometry.get_attrib_stats', params)


@tool
async def get_volume_info(
    ctx: BridgeContext,
    node_path: str,
    max_volumes: int = 24,
    threshold: float | None = None,
    bins: int | list[float] = 0,
) -> dict:
    """Per-volume name, resolution, active voxels, value range, mean and sum."""

    params: dict[str, Any] = {'node_path': node_path, 'max_volumes': max_volumes}
    if threshold is not None:
        params['threshold'] = threshold
    if bins:
        params['bins'] = bins
    return await run_command(ctx, 'geometry.get_volume_info', params)


@tool
async def sample_volume(
    ctx: BridgeContext,
    node_path: str,
    fields: list[str],
    positions: list[list[float]] | None = None,
    from_node: str | None = None,
    limit: int = 1000,
    bins: int | list[float] = 0,
    threshold: float | None = None,
) -> dict:
    """Read named volume fields at world positions, or at another SOP's points."""

    params: dict[str, Any] = {'node_path': node_path, 'fields': fields, 'limit': limit}
    if positions is not None:
        params['positions'] = positions
    if from_node is not None:
        params['from_node'] = from_node
    if bins:
        params['bins'] = bins
    if threshold is not None:
        params['threshold'] = threshold
    return await run_command(ctx, 'geometry.sample_volume', params)


@tool
async def compare_volumes(
    ctx: BridgeContext,
    node_path: str,
    field: str,
    against: str,
    against_node: str | None = None,
    bands: int | list[float] = 10,
) -> dict:
    """How much of one field sits in each band of another field."""

    params: dict[str, Any] = {
        'node_path': node_path,
        'field': field,
        'against': against,
        'bands': bands,
    }
    if against_node is not None:
        params['against_node'] = against_node
    return await run_command(ctx, 'geometry.compare_volumes', params)
