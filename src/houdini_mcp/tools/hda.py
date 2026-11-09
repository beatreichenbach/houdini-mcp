"""MCP tool wrappers for Houdini Digital Asset (HDA) operations."""

from __future__ import annotations

# Built-in
# Third-party
# Internal
from .context import BridgeContext, run_command
from .registry import tool


@tool
async def list_installed_hdas(
    ctx: BridgeContext,
    filter: str | None = None,
    limit: int = 100,
) -> dict:
    """List installed HDA definitions, grouped by library file."""

    params: dict = {'limit': limit}
    if filter is not None:
        params['filter'] = filter
    return await run_command(ctx, 'hda.list_installed_hdas', params)


@tool
async def get_hda_info(
    ctx: BridgeContext,
    node_path: str | None = None,
    hda_file: str | None = None,
    type_name: str | None = None,
) -> dict:
    """Get detailed information about an HDA definition."""

    params: dict = {}
    if node_path is not None:
        params['node_path'] = node_path
    if hda_file is not None:
        params['hda_file'] = hda_file
    if type_name is not None:
        params['type_name'] = type_name
    return await run_command(ctx, 'hda.get_hda_info', params)


@tool
async def install_hda(
    ctx: BridgeContext,
    file_path: str,
    force: bool = False,
) -> dict:
    """Install an HDA file into the current session."""

    return await run_command(
        ctx,
        'hda.install_hda',
        {
            'file_path': file_path,
            'force': force,
        },
    )


@tool
async def uninstall_hda(ctx: BridgeContext, file_path: str) -> dict:
    """Uninstall an HDA file from the current session."""

    return await run_command(ctx, 'hda.uninstall_hda', {'file_path': file_path})


@tool
async def reload_hda(ctx: BridgeContext, file_path: str) -> dict:
    """Reload an HDA file from disk."""

    return await run_command(ctx, 'hda.reload_hda', {'file_path': file_path})


@tool
async def create_hda(
    ctx: BridgeContext,
    node_path: str,
    hda_file: str,
    type_name: str,
    label: str,
    version: str = '1.0',
) -> dict:
    """Create a new HDA from an existing subnet node."""

    return await run_command(
        ctx,
        'hda.create_hda',
        {
            'node_path': node_path,
            'hda_file': hda_file,
            'type_name': type_name,
            'label': label,
            'version': version,
        },
    )


@tool
async def update_hda(ctx: BridgeContext, node_path: str) -> dict:
    """Save the current node contents back to its HDA definition."""

    return await run_command(ctx, 'hda.update_hda', {'node_path': node_path})


@tool
async def get_hda_sections(ctx: BridgeContext, node_path: str) -> dict:
    """List all sections in an HDA definition."""

    return await run_command(ctx, 'hda.get_hda_sections', {'node_path': node_path})


@tool
async def get_hda_section_content(
    ctx: BridgeContext,
    node_path: str,
    section_name: str,
) -> dict:
    """Read the content of a specific section in an HDA definition."""

    return await run_command(
        ctx,
        'hda.get_hda_section_content',
        {
            'node_path': node_path,
            'section_name': section_name,
        },
    )


@tool
async def set_hda_section_content(
    ctx: BridgeContext,
    node_path: str,
    section_name: str,
    content: str,
) -> dict:
    """Write content to a specific section in an HDA definition."""

    return await run_command(
        ctx,
        'hda.set_hda_section_content',
        {
            'node_path': node_path,
            'section_name': section_name,
            'content': content,
        },
    )


@tool
async def list_hda_versions(ctx: BridgeContext, node_path: str) -> dict:
    """List installed definitions of an HDA type."""

    return await run_command(ctx, 'hda.list_hda_versions', {'node_path': node_path})


@tool
async def set_hda_interface(
    ctx: BridgeContext,
    node_path: str,
    parameters: list[dict],
    replace: bool = False,
    dry_run: bool = False,
) -> dict:
    """Author an HDA's Type Properties interface in one call."""

    payload: dict = {
        'node_path': node_path,
        'parameters': parameters,
        'replace': replace,
    }
    if dry_run:
        payload['dry_run'] = True
    return await run_command(ctx, 'hda.set_hda_interface', payload)


@tool
async def edit_hda_interface(
    ctx: BridgeContext,
    node_path: str,
    ops: list[dict],
    dry_run: bool = False,
) -> dict:
    """Edit an existing HDA interface in one atomic call."""

    return await run_command(
        ctx,
        'hda.edit_hda_interface',
        {'node_path': node_path, 'ops': ops, 'dry_run': dry_run},
    )
