"""MCP tools for LOPs / USD stage inspection and manipulation."""

from __future__ import annotations

from typing import Any

from ..types import Value
from .context import BridgeContext, run_command
from .registry import tool


@tool
async def get_stage_info(ctx: BridgeContext, node_path: str = '/stage') -> dict:
    """Get USD stage info from a LOP node, or from a LOP network."""

    return await run_command(
        ctx,
        'lops.get_stage_info',
        {
            'node_path': node_path,
        },
    )


@tool
async def get_usd_prim(
    ctx: BridgeContext,
    node_path: str,
    prim_path: str,
    full: bool = False,
    traverse_instance_proxies: bool = False,
    time: float | None = None,
    attr_patterns: list[str] | None = None,
) -> dict:
    """Get detailed info about a USD prim."""

    params: dict[str, Any] = {'node_path': node_path, 'prim_path': prim_path}
    if full:
        params['full'] = True
    if traverse_instance_proxies:
        params['traverse_instance_proxies'] = True
    if time is not None:
        params['time'] = time
    if attr_patterns:
        params['attr_patterns'] = attr_patterns
    return await run_command(ctx, 'lops.get_usd_prim', params)


@tool
async def list_usd_prims(
    ctx: BridgeContext,
    node_path: str,
    root_path: str = '/',
    prim_type: str | None = None,
    kind: str | None = None,
    depth: int | None = None,
    traverse_instance_proxies: bool = False,
) -> dict:
    """List USD prims on a stage with filtering."""

    params: dict[str, Any] = {
        'node_path': node_path,
        'root_path': root_path,
    }
    if prim_type is not None:
        params['prim_type'] = prim_type
    if kind is not None:
        params['kind'] = kind
    if depth is not None:
        params['depth'] = depth
    if traverse_instance_proxies:
        params['traverse_instance_proxies'] = True
    return await run_command(ctx, 'lops.list_usd_prims', params)


@tool
async def get_usd_attribute(
    ctx: BridgeContext,
    node_path: str,
    prim_path: str,
    attr_name: str,
    time: float | None = None,
    full: bool = False,
    offset: int = 0,
    limit: int = 64,
    all_samples: bool = False,
) -> dict:
    """Read a USD attribute value from a prim."""

    params: dict[str, Any] = {
        'node_path': node_path,
        'prim_path': prim_path,
        'attr_name': attr_name,
    }
    if time is not None:
        params['time'] = time
    if full:
        params['full'] = True
    if offset:
        params['offset'] = offset
    if limit != 64:
        params['limit'] = limit
    if all_samples:
        params['all_samples'] = True
    return await run_command(ctx, 'lops.get_usd_attribute', params)


@tool
async def get_usd_attributes(
    ctx: BridgeContext,
    node_path: str,
    prims: list[str],
    attr_patterns: list[str] | None = None,
    prim_type: str | None = None,
    relationships: bool = True,
    time: float | None = None,
    full: bool = False,
    traverse_instance_proxies: bool = False,
    limit: int = 500,
) -> dict:
    """Read the same attributes across many prims as one table."""

    params: dict[str, Any] = {'node_path': node_path, 'prims': prims}
    if attr_patterns:
        params['attr_patterns'] = attr_patterns
    if prim_type:
        params['prim_type'] = prim_type
    if not relationships:
        params['relationships'] = False
    if time is not None:
        params['time'] = time
    if full:
        params['full'] = True
    if traverse_instance_proxies:
        params['traverse_instance_proxies'] = True
    if limit != 500:
        params['limit'] = limit
    return await run_command(ctx, 'lops.get_usd_attributes', params)


@tool
async def get_usd_world_transform(
    ctx: BridgeContext,
    node_path: str,
    prim_paths: list[str],
    frames: list[float] | None = None,
) -> dict:
    """World transform of USD prims at one or more frames."""

    params: dict[str, Any] = {'node_path': node_path, 'prim_paths': prim_paths}
    if frames is not None:
        params['frames'] = frames
    return await run_command(ctx, 'lops.get_usd_world_transform', params)


@tool
async def get_usd_layers(ctx: BridgeContext, node_path: str) -> dict:
    """List all layers in a USD stage."""

    return await run_command(
        ctx,
        'lops.get_usd_layers',
        {
            'node_path': node_path,
        },
    )


@tool
async def get_usd_prim_stats(
    ctx: BridgeContext,
    node_path: str,
    prim_path: str = '/',
    traverse_instance_proxies: bool = False,
) -> dict:
    """Get prim counts by USD type under a root path."""

    return await run_command(
        ctx,
        'lops.get_usd_prim_stats',
        {
            'node_path': node_path,
            'prim_path': prim_path,
            'traverse_instance_proxies': traverse_instance_proxies,
        },
    )


@tool
async def get_last_modified_prims(ctx: BridgeContext, node_path: str) -> dict:
    """Get prims modified by the last LOP node cook."""

    return await run_command(
        ctx,
        'lops.get_last_modified_prims',
        {
            'node_path': node_path,
        },
    )


@tool
async def create_lop_node(
    ctx: BridgeContext,
    parent_path: str,
    lop_type: str,
    name: str | None = None,
    prim_path: str | None = None,
) -> dict:
    """Create a new LOP node."""

    params: dict[str, Any] = {
        'parent_path': parent_path,
        'lop_type': lop_type,
    }
    if name is not None:
        params['name'] = name
    if prim_path is not None:
        params['prim_path'] = prim_path
    return await run_command(ctx, 'lops.create_lop_node', params)


@tool
async def set_usd_attribute(
    ctx: BridgeContext,
    node_path: str,
    prim_path: str,
    attr_name: str,
    value: Value,
) -> dict:
    """Set a USD attribute value via an inline Python LOP."""

    return await run_command(
        ctx,
        'lops.set_usd_attribute',
        {
            'node_path': node_path,
            'prim_path': prim_path,
            'attr_name': attr_name,
            'value': value,
        },
    )


@tool
async def get_usd_bound_material(
    ctx: BridgeContext,
    node_path: str,
    prim_paths: list[str],
    purpose: str = 'full',
) -> dict:
    """Return the material bound to each prim and where the binding comes from."""

    return await run_command(
        ctx,
        'lops.get_usd_bound_material',
        {'node_path': node_path, 'prim_paths': prim_paths, 'purpose': purpose},
    )


@tool
async def get_usd_materials(ctx: BridgeContext, node_path: str) -> dict:
    """List all USD materials on a stage."""

    return await run_command(
        ctx,
        'lops.get_usd_materials',
        {
            'node_path': node_path,
        },
    )


@tool
async def find_usd_prims(
    ctx: BridgeContext,
    node_path: str,
    pattern: str,
    traverse_instance_proxies: bool = False,
) -> dict:
    """Search USD prims by path pattern."""

    return await run_command(
        ctx,
        'lops.find_usd_prims',
        {
            'node_path': node_path,
            'pattern': pattern,
            'traverse_instance_proxies': traverse_instance_proxies,
        },
    )


@tool
async def get_usd_composition(
    ctx: BridgeContext,
    node_path: str,
    prim_path: str,
) -> dict:
    """Get composition arcs for a USD prim."""

    return await run_command(
        ctx,
        'lops.get_usd_composition',
        {
            'node_path': node_path,
            'prim_path': prim_path,
        },
    )


@tool
async def get_usd_variants(
    ctx: BridgeContext,
    node_path: str,
    prim_path: str,
) -> dict:
    """Get variant sets and selections for a USD prim."""

    return await run_command(
        ctx,
        'lops.get_usd_variants',
        {
            'node_path': node_path,
            'prim_path': prim_path,
        },
    )


@tool
async def inspect_usd_layer(
    ctx: BridgeContext,
    node_path: str,
    layer_index: int = 0,
) -> dict:
    """Inspect a USD layer by index."""

    return await run_command(
        ctx,
        'lops.inspect_usd_layer',
        {
            'node_path': node_path,
            'layer_index': layer_index,
        },
    )


@tool
async def create_light(
    ctx: BridgeContext,
    parent_path: str = '/stage',
    light_type: str = 'dome',
    name: str | None = None,
    intensity: float = 1.0,
    color: list[float] | None = None,
    position: list[float] | None = None,
) -> dict:
    """Create a USD light in a LOP network."""

    params: dict[str, Any] = {
        'parent_path': parent_path,
        'light_type': light_type,
        'intensity': intensity,
    }
    if name is not None:
        params['name'] = name
    if color is not None:
        params['color'] = color
    if position is not None:
        params['position'] = position
    return await run_command(ctx, 'lops.create_light', params)


@tool
async def list_lights(ctx: BridgeContext, node_path: str) -> dict:
    """List all USD lights on a LOP stage."""

    return await run_command(
        ctx,
        'lops.list_lights',
        {
            'node_path': node_path,
        },
    )


@tool
async def set_light_properties(
    ctx: BridgeContext,
    node_path: str,
    prim_path: str,
    properties: dict[str, Any],
) -> dict:
    """Set properties on a USD light prim via an inline Python LOP."""

    return await run_command(
        ctx,
        'lops.set_light_properties',
        {
            'node_path': node_path,
            'prim_path': prim_path,
            'properties': properties,
        },
    )


@tool
async def create_light_rig(
    ctx: BridgeContext,
    parent_path: str = '/stage',
    preset: str = 'three_point',
    intensity_mult: float = 1.0,
) -> dict:
    """Create a preset lighting rig in a LOP network."""

    return await run_command(
        ctx,
        'lops.create_light_rig',
        {
            'parent_path': parent_path,
            'preset': preset,
            'intensity_mult': intensity_mult,
        },
    )
