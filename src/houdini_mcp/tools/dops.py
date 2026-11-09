"""MCP tool definitions for DOP (dynamics/simulation) operations."""

from __future__ import annotations

# Built-in
# Third-party
# Internal
from ..bridge import NO_TIMEOUT
from .context import BridgeContext, run_command
from .registry import tool


@tool
async def get_simulation_info(ctx: BridgeContext, node_path: str) -> dict:
    """Get DOP network simulation state, cooked at the current frame."""

    return await run_command(
        ctx, 'dops.get_simulation_info', {'node_path': node_path}, timeout=NO_TIMEOUT
    )


@tool
async def list_dop_objects(ctx: BridgeContext, node_path: str) -> dict:
    """List all DOP objects in a simulation."""

    return await run_command(ctx, 'dops.list_dop_objects', {'node_path': node_path})


@tool
async def get_dop_object(ctx: BridgeContext, node_path: str, object_name: str) -> dict:
    """Get detailed data for a specific DOP object."""

    return await run_command(
        ctx,
        'dops.get_dop_object',
        {'node_path': node_path, 'object_name': object_name},
    )


@tool
async def get_dop_field(
    ctx: BridgeContext,
    node_path: str,
    object_name: str,
    data_path: str,
    field_name: str,
) -> dict:
    """Read a specific field value from a DOP record."""

    return await run_command(
        ctx,
        'dops.get_dop_field',
        {
            'node_path': node_path,
            'object_name': object_name,
            'data_path': data_path,
            'field_name': field_name,
        },
    )


@tool
async def get_dop_relationships(ctx: BridgeContext, node_path: str) -> dict:
    """List all relationships between DOP objects."""

    return await run_command(
        ctx, 'dops.get_dop_relationships', {'node_path': node_path}
    )


@tool
async def step_simulation(ctx: BridgeContext, node_path: str, steps: int = 1) -> dict:
    """Advance the simulation by a number of frames."""

    return await run_command(
        ctx,
        'dops.step_simulation',
        {'node_path': node_path, 'steps': steps},
    )


@tool
async def reset_simulation(ctx: BridgeContext, node_path: str) -> dict:
    """Reset the simulation to its initial state."""

    return await run_command(ctx, 'dops.reset_simulation', {'node_path': node_path})


@tool
async def get_sim_memory_usage(ctx: BridgeContext, node_path: str) -> dict:
    """Get detailed memory breakdown for the simulation."""

    return await run_command(ctx, 'dops.get_sim_memory_usage', {'node_path': node_path})
