"""MCP tool wrappers for Houdini materials and shaders operations."""

from __future__ import annotations

# Built-in
from typing import Any

# Third-party
# Internal
from .context import BridgeContext, run_command
from .registry import tool


@tool
async def list_materials(
    ctx: BridgeContext,
    root_path: str = '/mat',
) -> dict:
    """List all material nodes under a root path."""

    return await run_command(
        ctx,
        'materials.list_materials',
        {
            'root_path': root_path,
        },
    )


@tool
async def get_material_info(ctx: BridgeContext, node_path: str) -> dict:
    """Get detailed information about a material node."""

    return await run_command(
        ctx,
        'materials.get_material_info',
        {
            'node_path': node_path,
        },
    )


@tool
async def create_material_network(
    ctx: BridgeContext,
    name: str,
    shader_type: str = 'principled',
    params: dict[str, Any] | None = None,
) -> dict:
    """Create a new material network in /mat."""

    p: dict[str, Any] = {
        'name': name,
        'shader_type': shader_type,
    }
    if params is not None:
        p['params'] = params
    return await run_command(ctx, 'materials.create_material_network', p)


@tool
async def list_material_types(
    ctx: BridgeContext,
    filter: str | None = None,
) -> dict:
    """List available VOP/material node types."""

    p: dict[str, Any] = {}
    if filter is not None:
        p['filter'] = filter
    return await run_command(ctx, 'materials.list_material_types', p)
