"""Node tools."""

from __future__ import annotations

from typing import Any

from ..bridge import NO_TIMEOUT
from ..errors import HoudiniCommandError
from .context import BridgeContext, run_command
from .registry import tool


@tool
async def create_node(
    ctx: BridgeContext,
    parent_path: str,
    node_type: str,
    name: str | None = None,
    position: list[float] | None = None,
) -> dict:
    """Create a node inside a parent network."""

    params: dict = {
        'parent_path': parent_path,
        'node_type': node_type,
    }
    if name is not None:
        params['name'] = name
    if position is not None:
        params['position'] = position
    return await run_command(ctx, 'nodes.create_node', params)


@tool
async def delete_node(
    ctx: BridgeContext,
    node_path: str | None = None,
    node_paths: list[str] | None = None,
) -> dict:
    """Delete a node, or several in one call."""

    params: dict[str, Any] = {}
    if node_path is not None:
        params['node_path'] = node_path
    if node_paths is not None:
        params['node_paths'] = node_paths
    return await run_command(ctx, 'nodes.delete_node', params)


@tool
async def delete_sticky_notes(
    ctx: BridgeContext,
    parent_path: str,
    recursive: bool = True,
) -> dict:
    """Delete sticky notes under a network, including nested networks."""

    return await run_command(
        ctx,
        'nodes.delete_sticky_notes',
        {
            'parent_path': parent_path,
            'recursive': recursive,
        },
    )


@tool
async def rename_node(ctx: BridgeContext, node_path: str, new_name: str) -> dict:
    """Rename a node."""

    return await run_command(
        ctx,
        'nodes.rename_node',
        {
            'node_path': node_path,
            'new_name': new_name,
        },
    )


@tool
async def copy_node(
    ctx: BridgeContext,
    node_path: str,
    dest_parent: str | None = None,
    new_name: str | None = None,
    offset: list[float] | None = None,
) -> dict:
    """Copy a node, optionally into a different parent network."""

    params: dict = {'node_path': node_path}
    if dest_parent is not None:
        params['dest_parent'] = dest_parent
    if new_name is not None:
        params['new_name'] = new_name
    if offset is not None:
        params['offset'] = offset
    return await run_command(ctx, 'nodes.copy_node', params)


@tool
async def move_node(ctx: BridgeContext, node_path: str, dest_parent: str) -> dict:
    """Move a node to a different parent network."""

    return await run_command(
        ctx,
        'nodes.move_node',
        {
            'node_path': node_path,
            'dest_parent': dest_parent,
        },
    )


@tool
async def get_node_info(ctx: BridgeContext, node_path: str) -> dict:
    """Return a node's type, connections, flags, errors, and changed parameters."""

    return await run_command(ctx, 'nodes.get_node_info', {'node_path': node_path})


@tool
async def list_children(
    ctx: BridgeContext,
    parent_path: str,
    recursive: bool = False,
    filter_type: str | None = None,
    include_locked_assets: bool = False,
    dive_target: bool = False,
) -> dict:
    """List children of a network node. Locked assets are opaque unless
    `include_locked_assets` (raw contents) or `dive_target` (editable content)
    asks for them."""

    params: dict = {
        'parent_path': parent_path,
        'recursive': recursive,
    }
    if filter_type is not None:
        params['filter_type'] = filter_type
    if include_locked_assets:
        params['include_locked_assets'] = True
    return await run_command(ctx, 'nodes.list_children', params)


@tool
async def find_nodes(
    ctx: BridgeContext,
    pattern: str | None = None,
    node_type: str | None = None,
    context: str | None = None,
    inside: str = '/',
) -> dict:
    """Search for nodes by name pattern, type, or context."""

    params: dict = {'inside': inside}
    if pattern is not None:
        params['pattern'] = pattern
    if node_type is not None:
        params['node_type'] = node_type
    if context is not None:
        params['context'] = context
    return await run_command(ctx, 'nodes.find_nodes', params)


@tool
async def list_node_types(
    ctx: BridgeContext,
    context: str,
    filter: str | None = None,
    limit: int = 200,
) -> dict:
    """List available node types for a context category."""

    params: dict = {'context': context, 'limit': limit}
    if filter is not None:
        params['filter'] = filter
    return await run_command(ctx, 'nodes.list_node_types', params)


@tool
async def change_node_type(
    ctx: BridgeContext,
    node_path: str,
    new_type: str,
    keep_name: bool = True,
    keep_parms: bool = True,
    keep_network_contents: bool = True,
) -> dict:
    """Change a node's type in place, preserving wires and parameters."""

    return await run_command(
        ctx,
        'nodes.change_node_type',
        {
            'node_path': node_path,
            'new_type': new_type,
            'keep_name': keep_name,
            'keep_parms': keep_parms,
            'keep_network_contents': keep_network_contents,
        },
    )


@tool
async def press_button(
    ctx: BridgeContext,
    node_path: str,
    parm_name: str,
    arguments: dict[str, Any] | None = None,
    cook: bool = False,
    action: bool = False,
) -> dict:
    """Press a button parameter and return the node's errors and warnings."""

    payload: dict[str, Any] = {'node_path': node_path, 'parm_name': parm_name}
    if arguments:
        payload['arguments'] = arguments
    if cook:
        payload['cook'] = True
    if action:
        payload['action'] = True
    return await run_command(ctx, 'nodes.press_button', payload, timeout=NO_TIMEOUT)


@tool
async def connect_nodes(
    ctx: BridgeContext,
    source_path: str,
    dest_path: str,
    output_index: int = 0,
    input_index: int = 0,
    input_name: str | None = None,
    indirect_input: int | None = None,
) -> dict:
    """Connect two nodes together."""

    params: dict[str, Any] = {
        'source_path': source_path,
        'dest_path': dest_path,
        'output_index': output_index,
        'input_index': input_index,
        'input_name': input_name,
    }
    if indirect_input is None:
        return await run_command(ctx, 'nodes.connect_nodes', params)
    params['indirect_input'] = indirect_input
    try:
        return await run_command(ctx, 'nodes.connect_nodes', params)
    except HoudiniCommandError as exc:
        # The compatibility check compares command names, and connect_nodes
        # exists on a plugin that predates indirect_input: say so.
        if exc.code == 'BAD_ARGUMENTS' and 'indirect_input' in str(exc):
            raise HoudiniCommandError(
                f'{exc} The Houdini plugin predates indirect_input; update the '
                f"plugin to wire from a subnet's input connector.",
                code=exc.code,
                details=exc.details,
            ) from exc
        raise


@tool
async def connect_nodes_batch(
    ctx: BridgeContext,
    connections: list[dict[str, Any]],
) -> dict:
    """Connect multiple node pairs in a single call."""

    return await run_command(
        ctx,
        'nodes.connect_nodes_batch',
        {'connections': connections},
    )


@tool
async def disconnect_node(
    ctx: BridgeContext,
    node_path: str,
    input_index: int | None = None,
    disconnect_all: bool = False,
) -> dict:
    """Disconnect one or all inputs of a node."""

    params: dict = {'node_path': node_path, 'disconnect_all': disconnect_all}
    if input_index is not None:
        params['input_index'] = input_index
    return await run_command(ctx, 'nodes.disconnect_node', params)


@tool
async def reorder_inputs(
    ctx: BridgeContext, node_path: str, new_order: list[int]
) -> dict:
    """Reorder the input connections of a node."""

    return await run_command(
        ctx,
        'nodes.reorder_inputs',
        {
            'node_path': node_path,
            'new_order': new_order,
        },
    )


@tool
async def set_node_flags(
    ctx: BridgeContext,
    node_path: str,
    display: bool | None = None,
    render: bool | None = None,
    bypass: bool | None = None,
    template: bool | None = None,
    lock: bool | None = None,
) -> dict:
    """Set flags on a node."""

    params: dict = {'node_path': node_path}
    if display is not None:
        params['display'] = display
    if render is not None:
        params['render'] = render
    if bypass is not None:
        params['bypass'] = bypass
    if template is not None:
        params['template'] = template
    if lock is not None:
        params['lock'] = lock
    return await run_command(ctx, 'nodes.set_node_flags', params)


@tool
async def layout_children(
    ctx: BridgeContext,
    parent_path: str,
    spacing: float | None = None,
) -> dict:
    """Auto-layout children of a network node."""

    params: dict = {'parent_path': parent_path}
    if spacing is not None:
        params['spacing'] = spacing
    return await run_command(ctx, 'nodes.layout_children', params)


@tool
async def set_node_position(
    ctx: BridgeContext, node_path: str, x: float, y: float
) -> dict:
    """Set a node's position in the network editor."""

    return await run_command(
        ctx,
        'nodes.set_node_position',
        {
            'node_path': node_path,
            'x': x,
            'y': y,
        },
    )


@tool
async def set_node_color(
    ctx: BridgeContext,
    node_path: str,
    r: float,
    g: float,
    b: float,
) -> dict:
    """Set a node's color in the network editor."""

    return await run_command(
        ctx,
        'nodes.set_node_color',
        {
            'node_path': node_path,
            'r': r,
            'g': g,
            'b': b,
        },
    )


@tool
async def create_network_box(
    ctx: BridgeContext,
    parent_path: str,
    node_paths: list[str] | None = None,
    comment: str | None = None,
    color: list[float] | None = None,
) -> dict:
    """Draw a titled network box around nodes, to document a graph you built."""

    params: dict[str, Any] = {'parent_path': parent_path}
    if node_paths is not None:
        params['node_paths'] = node_paths
    if comment is not None:
        params['comment'] = comment
    if color is not None:
        params['color'] = color
    return await run_command(ctx, 'nodes.create_network_box', params)


@tool
async def create_sticky_note(
    ctx: BridgeContext,
    parent_path: str,
    text: str,
    position: list[float] | None = None,
    size: list[float] | None = None,
    color: list[float] | None = None,
) -> dict:
    """Leave a sticky note in a network."""

    params: dict[str, Any] = {'parent_path': parent_path, 'text': text}
    if position is not None:
        params['position'] = position
    if size is not None:
        params['size'] = size
    if color is not None:
        params['color'] = color
    return await run_command(ctx, 'nodes.create_sticky_note', params)


@tool
async def set_object_transform(
    ctx: BridgeContext,
    node_path: str,
    translate: list[float] | None = None,
    rotate: list[float] | None = None,
    scale: list[float] | None = None,
    parent: str | None = None,
) -> dict:
    """Set an object's translate, rotate, scale and/or parent in one call."""

    params: dict[str, Any] = {'node_path': node_path}
    if translate is not None:
        params['translate'] = translate
    if rotate is not None:
        params['rotate'] = rotate
    if scale is not None:
        params['scale'] = scale
    if parent is not None:
        params['parent'] = parent
    return await run_command(ctx, 'nodes.set_object_transform', params)
