"""Parameter tools."""

from __future__ import annotations

from typing import Any

from ..types import Value
from .context import BridgeContext, run_command
from .registry import tool


@tool
async def get_parameter(ctx: BridgeContext, node_path: str, parm_name: str) -> dict:
    """Get the value and metadata of a parameter."""

    return await run_command(
        ctx,
        'parameters.get_parameter',
        {'node_path': node_path, 'parm_name': parm_name},
    )


###### parameters.set_parameter


@tool
async def set_parameter(
    ctx: BridgeContext,
    node_path: str,
    parm_name: str,
    value: Value,
    override_expression: bool = False,
    run_callbacks: bool = False,
) -> dict:
    """Set a parameter value."""

    return await run_command(
        ctx,
        'parameters.set_parameter',
        {
            'node_path': node_path,
            'parm_name': parm_name,
            'value': value,
            'override_expression': override_expression,
            'run_callbacks': run_callbacks,
        },
    )


###### parameters.set_parameters


@tool
async def set_parameters(
    ctx: BridgeContext,
    node_path: str,
    params: dict[str, Any],
    override_expression: bool = False,
    run_callbacks: bool = False,
) -> dict:
    """Batch-set multiple parameters on a node, in the order given."""

    return await run_command(
        ctx,
        'parameters.set_parameters',
        {
            'node_path': node_path,
            'params': params,
            'override_expression': override_expression,
            'run_callbacks': run_callbacks,
        },
    )


###### parameters.get_parameter_schema


@tool
async def get_parameter_schema(
    ctx: BridgeContext,
    node_path: str,
    parm_name: str | None = None,
    filter: str | None = None,
) -> dict:
    """Get the template schema for parameter(s) on a node."""

    payload: dict[str, Any] = {'node_path': node_path}
    if parm_name is not None:
        payload['parm_name'] = parm_name
    if filter is not None:
        payload['filter'] = filter
    return await run_command(ctx, 'parameters.get_parameter_schema', payload)


###### parameters.get_parm_references


@tool
async def get_parm_references(
    ctx: BridgeContext,
    node_path: str,
    parm_name: str | None = None,
    direction: str = 'both',
    limit: int = 200,
    include_node_level: bool | None = None,
) -> dict:
    """Who references a parameter, and what it references — in one call."""

    payload: dict[str, Any] = {
        'node_path': node_path,
        'direction': direction,
        'limit': limit,
    }
    if parm_name is not None:
        payload['parm_name'] = parm_name
    if include_node_level is not None:
        payload['include_node_level'] = include_node_level
    return await run_command(ctx, 'parameters.get_parm_references', payload)


###### parameters.get_parm_template_tree


@tool
async def get_parm_template_tree(
    ctx: BridgeContext,
    node_path: str | None = None,
    type_name: str | None = None,
    context: str = 'Sop',
    folder: str | list[str] | None = None,
    max_entries: int = 150,
    include_tags: bool = False,
) -> dict:
    """Return the parameter interface as a tree of folders and parameters."""

    payload: dict[str, Any] = {
        'context': context,
        'max_entries': max_entries,
        'include_tags': include_tags,
    }
    if node_path is not None:
        payload['node_path'] = node_path
    if type_name is not None:
        payload['type_name'] = type_name
    if folder is not None:
        payload['folder'] = folder
    return await run_command(ctx, 'parameters.get_parm_template_tree', payload)


###### parameters.set_expression


@tool
async def set_expression(
    ctx: BridgeContext,
    node_path: str,
    parm_name: str,
    expression: str,
    language: str = 'hscript',
) -> dict:
    """Set an expression on a parameter."""

    return await run_command(
        ctx,
        'parameters.set_expression',
        {
            'node_path': node_path,
            'parm_name': parm_name,
            'expression': expression,
            'language': language,
        },
    )


###### parameters.get_expression


@tool
async def get_expression(ctx: BridgeContext, node_path: str, parm_name: str) -> dict:
    """Get the expression on a parameter."""

    return await run_command(
        ctx,
        'parameters.get_expression',
        {'node_path': node_path, 'parm_name': parm_name},
    )


###### parameters.revert_parameter


@tool
async def revert_parameter(ctx: BridgeContext, node_path: str, parm_name: str) -> dict:
    """Revert a parameter to its default value."""

    return await run_command(
        ctx,
        'parameters.revert_parameter',
        {'node_path': node_path, 'parm_name': parm_name},
    )


###### parameters.link_parameters


@tool
async def link_parameters(
    ctx: BridgeContext,
    source_path: str,
    source_parm: str,
    dest_path: str,
    dest_parm: str,
    replace_existing: bool = False,
) -> dict:
    """Create a channel reference from one parameter to another."""

    return await run_command(
        ctx,
        'parameters.link_parameters',
        {
            'source_path': source_path,
            'source_parm': source_parm,
            'dest_path': dest_path,
            'dest_parm': dest_parm,
            'replace_existing': replace_existing,
        },
    )


###### parameters.lock_parameter


@tool
async def lock_parameter(
    ctx: BridgeContext, node_path: str, parm_name: str, locked: bool
) -> dict:
    """Lock or unlock a parameter."""

    return await run_command(
        ctx,
        'parameters.lock_parameter',
        {'node_path': node_path, 'parm_name': parm_name, 'locked': locked},
    )


###### parameters.create_spare_parameter


@tool
async def create_spare_parameter(
    ctx: BridgeContext,
    node_path: str,
    parm_name: str,
    parm_type: str,
    label: str,
    default_value: Value | None = None,
    min_val: float | None = None,
    max_val: float | None = None,
    menu_items: list[str | list[str]] | None = None,
) -> dict:
    """Add a spare parameter to a node."""

    payload: dict[str, Any] = {
        'node_path': node_path,
        'parm_name': parm_name,
        'parm_type': parm_type,
        'label': label,
    }
    if default_value is not None:
        payload['default_value'] = default_value
    if min_val is not None:
        payload['min_val'] = min_val
    if max_val is not None:
        payload['max_val'] = max_val
    if menu_items is not None:
        payload['menu_items'] = menu_items
    return await run_command(ctx, 'parameters.create_spare_parameter', payload)


@tool
async def create_spare_parameters(
    ctx: BridgeContext,
    node_path: str,
    parameters: list[dict[str, Any]],
    folder_name: str | None = None,
    folder_type: str = 'Tabs',
) -> dict:
    """Create multiple spare parameters, optionally in a folder tab."""

    payload: dict[str, Any] = {
        'node_path': node_path,
        'parameters': parameters,
    }
    if folder_name is not None:
        payload['folder_name'] = folder_name
        payload['folder_type'] = folder_type
    return await run_command(ctx, 'parameters.create_spare_parameters', payload)


@tool
async def promote_vop_parameters(
    ctx: BridgeContext, promotions: list[dict[str, Any]]
) -> dict:
    """Promote VOP inputs to parameters."""

    return await run_command(
        ctx, 'parameters.promote_vop_parameters', {'promotions': promotions}
    )


@tool
async def get_parameters(
    ctx: BridgeContext,
    node_path: str | None = None,
    patterns: list[str] | None = None,
    include_defaults: bool = False,
    inside: str | None = None,
    recursive: bool = False,
    node_type: str | None = None,
    include_locked_assets: bool = False,
    value_contains: str | None = None,
    non_default_only: bool = False,
) -> dict:
    """Read many parameter values at once, matched by name or label substring."""

    params: dict[str, Any] = {'include_defaults': include_defaults}
    if non_default_only:
        params['non_default_only'] = True
    if value_contains is not None:
        params['value_contains'] = value_contains
    if node_path is not None:
        params['node_path'] = node_path
    if patterns is not None:
        params['patterns'] = patterns
    if inside is not None:
        params['inside'] = inside
        params['recursive'] = recursive
        if node_type is not None:
            params['node_type'] = node_type
        if include_locked_assets:
            params['include_locked_assets'] = True
    return await run_command(ctx, 'parameters.get_parameters', params)
