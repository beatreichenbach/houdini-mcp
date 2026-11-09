"""MCP tool wrappers for Houdini COP (Copernicus) operations."""

from __future__ import annotations

from .context import BridgeContext, run_command
from .registry import tool


@tool
async def get_cop_info(ctx: BridgeContext, node_path: str) -> dict:
    """Get information about a COP node."""

    return await run_command(ctx, 'cops.get_cop_info', {'node_path': node_path})


@tool
async def get_cop_geometry(
    ctx: BridgeContext,
    node_path: str,
    output_index: int = 0,
) -> dict:
    """Get geometry representation from a COP node."""

    return await run_command(
        ctx,
        'cops.get_cop_geometry',
        {
            'node_path': node_path,
            'output_index': output_index,
        },
    )


@tool
async def get_cop_layer(
    ctx: BridgeContext,
    node_path: str,
    output_index: int = 0,
) -> dict:
    """Get image layer data from a COP node."""

    return await run_command(
        ctx,
        'cops.get_cop_layer',
        {
            'node_path': node_path,
            'output_index': output_index,
        },
    )


@tool
async def create_cop_node(
    ctx: BridgeContext,
    parent_path: str,
    cop_type: str,
    name: str | None = None,
) -> dict:
    """Create a COP node in the specified network."""

    params: dict = {
        'parent_path': parent_path,
        'cop_type': cop_type,
    }
    if name is not None:
        params['name'] = name
    return await run_command(ctx, 'cops.create_cop_node', params)


@tool
async def set_cop_flags(
    ctx: BridgeContext,
    node_path: str,
    display: bool | None = None,
    export_flag: bool | None = None,
    compress: bool | None = None,
) -> dict:
    """Set flags on a COP node."""

    params: dict = {'node_path': node_path}
    if display is not None:
        params['display'] = display
    if export_flag is not None:
        params['export_flag'] = export_flag
    if compress is not None:
        params['compress'] = compress
    return await run_command(ctx, 'cops.set_cop_flags', params)


@tool
async def list_cop_node_types(
    ctx: BridgeContext,
    filter: str | None = None,
) -> dict:
    """List available COP node types."""

    params: dict = {}
    if filter is not None:
        params['filter'] = filter
    return await run_command(ctx, 'cops.list_cop_node_types', params)


@tool
async def get_cop_vdb(
    ctx: BridgeContext,
    node_path: str,
    output_index: int = 0,
) -> dict:
    """Get VDB volumetric data from a COP node."""

    return await run_command(
        ctx,
        'cops.get_cop_vdb',
        {
            'node_path': node_path,
            'output_index': output_index,
        },
    )
