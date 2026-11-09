"""MCP tool wrappers for Houdini VEX operations."""

from __future__ import annotations

from .context import BridgeContext, run_command
from .registry import tool


@tool
async def create_wrangle(
    ctx: BridgeContext,
    parent_path: str,
    vex_code: str,
    justification: str,
    run_over: str = 'Points',
    name: str | None = None,
) -> dict:
    """Create an Attribute Wrangle node with VEX code."""

    params: dict = {
        'parent_path': parent_path,
        'vex_code': vex_code,
        'run_over': run_over,
    }
    if name is not None:
        params['name'] = name
    result = await run_command(ctx, 'vex.create_wrangle', params)
    if isinstance(result, dict):
        result['justification'] = justification
    return result


@tool
async def set_wrangle_code(
    ctx: BridgeContext,
    node_path: str,
    vex_code: str,
) -> dict:
    """Set VEX code on an existing Attribute Wrangle node."""

    return await run_command(
        ctx,
        'vex.set_wrangle_code',
        {
            'node_path': node_path,
            'vex_code': vex_code,
        },
    )


@tool
async def get_wrangle_code(ctx: BridgeContext, node_path: str) -> dict:
    """Read the VEX code from an Attribute Wrangle node."""

    return await run_command(ctx, 'vex.get_wrangle_code', {'node_path': node_path})


@tool
async def create_vex_expression(
    ctx: BridgeContext,
    node_path: str,
    parm_name: str,
    vex_code: str,
) -> dict:
    """Set an HScript expression on a parameter, evaluated before it is kept."""

    return await run_command(
        ctx,
        'vex.create_vex_expression',
        {
            'node_path': node_path,
            'parm_name': parm_name,
            'vex_code': vex_code,
        },
    )


@tool
async def validate_vex(ctx: BridgeContext, node_path: str) -> dict:
    """Validate VEX code by cooking the node and checking for errors."""

    return await run_command(ctx, 'vex.validate_vex', {'node_path': node_path})
