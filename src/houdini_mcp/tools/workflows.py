"""MCP tool wrappers for higher-level composite workflow operations."""

from __future__ import annotations

from typing import Any

from .context import BridgeContext, run_command
from .registry import tool


@tool
async def setup_pyro_sim(
    ctx: BridgeContext,
    source_geo: str = '/obj/geo1/sphere1',
    container: str = 'box',
    res_scale: float = 1.0,
    substeps: int = 1,
    name: str = 'pyro_sim',
) -> dict:
    """Build a Pyro smoke/fire simulation network from source geometry."""

    return await run_command(
        ctx,
        'workflow.setup_pyro_sim',
        {
            'source_geo': source_geo,
            'container': container,
            'res_scale': res_scale,
            'substeps': substeps,
            'name': name,
        },
    )


@tool
async def setup_rbd_sim(
    ctx: BridgeContext,
    geo_path: str = '/obj/geo1',
    ground: bool = True,
    pieces_type: str = 'voronoi',
    name: str = 'rbd_sim',
) -> dict:
    """Build an RBD rigid-body simulation network with fracture and solver."""

    return await run_command(
        ctx,
        'workflow.setup_rbd_sim',
        {
            'geo_path': geo_path,
            'ground': ground,
            'pieces_type': pieces_type,
            'name': name,
        },
    )


@tool
async def setup_flip_sim(
    ctx: BridgeContext,
    source_geo: str = '/obj/geo1/sphere1',
    domain: str = 'box',
    particle_sep: float = 0.05,
    name: str = 'flip_sim',
) -> dict:
    """Build a FLIP fluid simulation network from source geometry."""

    return await run_command(
        ctx,
        'workflow.setup_flip_sim',
        {
            'source_geo': source_geo,
            'domain': domain,
            'particle_sep': particle_sep,
            'name': name,
        },
    )


@tool
async def setup_vellum_sim(
    ctx: BridgeContext,
    geo_path: str = '/obj/geo1',
    sim_type: str = 'cloth',
    substeps: int = 5,
    name: str = 'vellum_sim',
    ground: bool = True,
) -> dict:
    """Build a Vellum simulation network with configure node and solver."""

    return await run_command(
        ctx,
        'workflow.setup_vellum_sim',
        {
            'geo_path': geo_path,
            'sim_type': sim_type,
            'substeps': substeps,
            'name': name,
            'ground': ground,
        },
    )


@tool
async def create_material(
    ctx: BridgeContext,
    name: str | None = None,
    mat_type: str = 'principled',
    base_color: list[float] | None = None,
    roughness: float = 0.5,
    metallic: float = 0.0,
    opacity: float = 1.0,
) -> dict:
    """Create a material in /mat with configurable surface properties."""

    params: dict = {
        'mat_type': mat_type,
        'roughness': roughness,
        'metallic': metallic,
        'opacity': opacity,
    }
    if name is not None:
        params['name'] = name
    if base_color is not None:
        params['base_color'] = base_color
    return await run_command(ctx, 'workflow.create_material', params)


@tool
async def assign_material(
    ctx: BridgeContext,
    geo_path: str,
    material_path: str,
) -> dict:
    """Assign a material to a geometry node via a Material SOP."""

    return await run_command(
        ctx,
        'workflow.assign_material',
        {
            'geo_path': geo_path,
            'material_path': material_path,
        },
    )


@tool
async def build_sop_chain(
    ctx: BridgeContext,
    parent_path: str = '/obj/geo1',
    steps: list[dict[str, Any]] | None = None,
) -> dict:
    """Build a sequential chain of SOP nodes wired together in a single call."""

    params: dict = {'parent_path': parent_path}
    if steps is not None:
        params['steps'] = steps
    return await run_command(ctx, 'workflow.build_sop_chain', params)


@tool
async def setup_render(
    ctx: BridgeContext,
    renderer: str = 'karma',
    camera: str | None = None,
    output_path: str = '$HIP/render/output.$F4.exr',
    resolution: list[int] | None = None,
    samples: int = 64,
    name: str = 'render1',
) -> dict:
    """Set up a render configuration with camera and ROP node."""

    params: dict = {
        'renderer': renderer,
        'output_path': output_path,
        'samples': samples,
        'name': name,
    }
    if camera is not None:
        params['camera'] = camera
    if resolution is not None:
        params['resolution'] = resolution
    return await run_command(ctx, 'workflow.setup_render', params)
