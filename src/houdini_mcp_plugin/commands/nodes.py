"""Node-level handlers for Houdini MCP."""

from __future__ import annotations

import contextlib
import re
import time
from difflib import get_close_matches
from typing import Any

import hou

from houdini_mcp_protocol import PluginCommand

from .. import constants
from ..callbacks import (
    CallbackError,
    action_script,
    callback_script,
    press,
    run_action,
)
from ..config import (
    auto_layout_enabled,
    mark_placed,
    place_new_node,
)
from ..dispatcher import register_command
from ..dop_cache import dop_cache_note
from ..errors import readable_message
from ..serialize import to_jsonable
from ..ui import focus_network_editor as _focus_network_editor


def _get_node(node_path: str) -> hou.Node:
    """Resolve a node path and raise a clear error if it does not exist."""

    node = hou.node(node_path)
    if node is None:
        raise ValueError(f'Node not found: {node_path}')
    return node


def _node_summary(node: hou.Node) -> dict:
    """Return a compact summary dict for a single node."""

    return {
        'name': node.name(),
        'path': node.path(),
        'type': node.type().name(),
        'category': node.type().category().name(),
    }


def _is_locked_hda(node: hou.Node) -> bool:
    """True when the node is a locked HDA instance."""

    with contextlib.suppress(Exception):
        return bool(node.isLockedHDA())
    return False


def _dive_target_path(node: hou.Node) -> str | None:
    """Return the node's editable dive target as an absolute path."""

    if not _is_locked_hda(node):
        return None
    definition = node.type().definition()
    if definition is None:
        return None
    with contextlib.suppress(Exception):
        section = definition.sections().get('DiveTarget')
        target = section.contents().strip() if section is not None else ''
        if target:
            return node.node(target).path()
    return None


@register_command(PluginCommand.NODES_CREATE_NODE)
def create_node(
    parent_path: str,
    node_type: str,
    name: str | None = None,
    position: list | None = None,
) -> dict:
    """Create a new node inside the given parent network."""

    parent = _get_node(parent_path)
    if name:
        _refuse_taken_name(parent, name)

    try:
        node = parent.createNode(node_type, node_name=name)
    except hou.OperationFailed as e:
        raise ValueError(
            f"Failed to create node of type '{node_type}' inside '{parent_path}': "
            f'{readable_message(e)}'
        ) from e

    if position is not None and len(position) >= 2:
        node.setPosition(hou.Vector2(position[0], position[1]))
        # The caller's position is final, including [0, 0] -- without the tag
        # the floor would read that as "never positioned" and move it.
        mark_placed(node)
    else:
        # No position asked for: place it beside its inputs rather than leaving
        # it at (0, 0) on top of whatever is already there.
        place_new_node(node)

    _focus_network_editor(node)

    result = {
        'success': True,
        'node_path': node.path(),
        'node_type': node.type().name(),
        'name': node.name(),
        'position': list(node.position()),
    }
    if cache := dop_cache_note([node]):
        result['simulation_cache'] = cache
    return result


@register_command(PluginCommand.NODES_DELETE_NODE)
def delete_node(node_path: str | None = None, node_paths: list | None = None) -> dict:
    """Delete a node from the scene, or several in one call."""

    if (node_path is None) == (node_paths is None):
        raise ValueError('pass node_path or node_paths, not both and not neither.')
    if node_paths is not None:
        return _delete_nodes(node_paths)
    assert node_path is not None
    node = _get_node(node_path)
    name = node.name()
    parent_path = node.parent().path()
    node.destroy()

    return {
        'success': True,
        'deleted_node': node_path,
        'name': name,
        'parent_path': parent_path,
    }


def _delete_nodes(node_paths: list) -> dict:
    """delete_node over a list: every path resolved first, then deleted."""

    if not isinstance(node_paths, (list, tuple)) or not node_paths:
        raise ValueError('node_paths must be a non-empty list of node paths.')
    paths = [str(path) for path in node_paths]
    missing = [path for path in paths if hou.node(path) is None]
    if missing:
        raise ValueError(f'Node(s) not found, nothing deleted: {missing}')
    nodes = {hou.node(path).path(): hou.node(path) for path in paths}
    # A node under another one on the list is destroyed with it; destroying
    # it again would raise on a dead node.
    inside = sorted(
        path
        for path in nodes
        if any(path.startswith(other + '/') for other in nodes if other != path)
    )
    # destroy() refuses these, after the ones before them in the list are gone.
    locked = [
        path
        for path, node in nodes.items()
        if path not in inside and node.isInsideLockedHDA()
    ]
    if locked:
        raise PermissionError(
            f'Inside a locked asset, nothing deleted: {locked}. Unlock it '
            '(allow editing of contents) or delete the asset itself.'
        )
    deleted = []
    for path, node in sorted(nodes.items()):
        if path in inside:
            continue
        node.destroy()
        deleted.append(path)
    reply: dict[str, Any] = {
        'success': True,
        'deleted_nodes': deleted,
        'deleted_count': len(deleted),
    }
    if inside:
        reply['deleted_with_parent'] = inside
    return reply


def _refuse_taken_name(parent: Any, name: str, node: Any = None) -> None:
    """Raise when ``name`` belongs to another child of ``parent``."""

    taken = parent.node(name)
    if taken is not None and taken != node:
        raise ValueError(
            f"'{name}' is already taken in {parent.path()} by {taken.path()}. "
            f'Rename or delete that node first, or pick another name.'
        )


@register_command(PluginCommand.NODES_RENAME_NODE)
def rename_node(node_path: str, new_name: str) -> dict:
    """Rename an existing node."""

    node = _get_node(node_path)
    old_name = node.name()
    _refuse_taken_name(node.parent(), new_name, node)
    node.setName(new_name)

    return {
        'success': True,
        'old_name': old_name,
        'new_name': node.name(),
        'new_path': node.path(),
    }


@register_command(PluginCommand.NODES_COPY_NODE)
def copy_node(
    node_path: str,
    dest_parent: str | None = None,
    new_name: str | None = None,
    offset: list | None = None,
) -> dict:
    """Copy a node, optionally into a different parent network."""

    node = _get_node(node_path)
    parent = _get_node(dest_parent) if dest_parent else node.parent()

    # Checked before copying, so a bad offset does not leave a stray copy behind.
    if offset is not None:
        try:
            if not isinstance(offset, (list, tuple)):
                raise TypeError
            dx, dy = (float(value) for value in offset)
        except (TypeError, ValueError):
            raise ValueError(f'offset must be [dx, dy], got {offset!r}.') from None
        offset = [dx, dy]
    if new_name:
        _refuse_taken_name(parent, new_name)

    copied = hou.copyNodesTo([node], parent)[0]

    if new_name:
        copied.setName(new_name)

    if offset is None and parent == node.parent():
        offset = [float(node.size()[0]) + 1.0, 0.0]
    if offset is not None:
        copied.setPosition(node.position() + hou.Vector2(offset[0], offset[1]))
    # The copy's position is decided here, including a copy that keeps the
    # original's (0, 0) in another network -- without the tag the floor would
    # read that as "never positioned" and move it on a later call.
    mark_placed(copied)

    result = {
        'success': True,
        'source_path': node_path,
        'copied_path': copied.path(),
        'name': copied.name(),
        'position': list(copied.position()),
        'offset_applied': offset,
    }
    # The wires the copy came with: without them a caller had to read the
    # copy's inputs back to learn they had survived. A copy into another
    # network cannot keep a wire from this one, and that is said rather than
    # left to be discovered.
    with contextlib.suppress(Exception):
        kept = _wires(copied)
        result['inputs'] = [{'index': i, **kept[i]} for i in sorted(kept)]
        original = _wires(node)
        lost = [{'index': i, **original[i]} for i in sorted(original) if i not in kept]
        if lost:
            result['inputs_not_copied'] = lost
    return result


def _wires(node: hou.Node) -> dict[int, dict[str, Any]]:
    """Each input of *node* by index: {"from": path}, or {"indirect_input": n}."""

    wires: dict[int, dict[str, Any]] = {}
    for conn in node.inputConnections():
        item = conn.inputItem()
        if isinstance(item, hou.SubnetIndirectInput):
            wires[conn.inputIndex()] = {'indirect_input': item.number()}
        else:
            wires[conn.inputIndex()] = {'from': item.path()}
    return wires


@register_command(PluginCommand.NODES_MOVE_NODE)
def move_node(node_path: str, dest_parent: str) -> dict:
    """Move a node to a different parent network."""

    node = _get_node(node_path)
    dest = _get_node(dest_parent)

    moved = hou.moveNodesTo([node], dest)[0]

    return {
        'success': True,
        'original_path': node_path,
        'new_path': moved.path(),
        'name': moved.name(),
    }


# Parameter kinds that carry no value: pressing, grouping, decorating.
_VALUELESS_PARM_TYPES = frozenset(
    {'Button', 'Folder', 'FolderSet', 'Separator', 'Label'}
)


def _component_default(parm: hou.Parm) -> Any:
    """The default of *parm* itself, not of the tuple it belongs to."""

    default = parm.parmTemplate().defaultValue()
    if isinstance(default, (tuple, list)):
        try:
            index = parm.componentIndex()
        except Exception:
            index = 0
        if not isinstance(index, int) or index < 0 or index >= len(default):
            return default[0] if len(default) == 1 else None
        return default[index]
    return default


def _is_at_default(parm: hou.Parm, value: Any, default: Any) -> bool:
    """Whether *parm* still holds its default."""

    try:
        answer = parm.isAtDefault()
        if isinstance(answer, bool):
            return answer
    except Exception:
        pass
    # Reached only when isAtDefault() is unavailable or answers non-bool.
    # Ramp and Data parameters have no comparable defaultValue(), so == is
    # false for them here and they reach the response -- which is why they
    # have to survive JSON encoding (see serialize.py).
    try:
        return bool(value == default)
    except Exception:
        return False


# SOP local variables, which only exist while the node cooks ($CEX/$CEY/$CEZ
# for a pivot at the centroid, $BBX, $SIZEX, $XMIN, $NPT, $PT, a Group SOP's
# factory $N), and `@attr` references (a Ray SOP's factory `@N.x`).
_COOK_LOCAL = re.compile(
    r'\$(?:CE[XYZ]|GC[XYZ]|BB[XYZ]|SIZE[XYZ]|[XYZ](?:MIN|MAX)|NPT|NPRIM|PT|PR|VTX|'
    r'NVTX|NGRP|N)\b'
    r'|(?<![\w@])@[A-Za-z_]\w*'
)

_COOK_LOCAL_NOTE = (
    'SOP local variable: substituted while the node cooks, so it is not evaluated '
    'here (outside a cook it reads 0). Judge the value by the cooked geometry.'
)


def _cook_local_expression(parm: hou.Parm) -> str | None:
    """*parm*'s expression when it uses a SOP local variable, else None."""

    try:
        expression = parm.expression()
    except Exception:
        return None
    if isinstance(expression, str) and _COOK_LOCAL.search(expression):
        return expression
    return None


def _non_default_parms(node: hou.Node, parms: list[hou.Parm]) -> list[dict[str, Any]]:
    """The parameters of *node* that differ from their defaults, as summaries."""

    summary: list[dict[str, Any]] = []
    for parm in parms:
        try:
            template = parm.parmTemplate()
            type_name = template.type().name()
        except Exception:
            continue
        if type_name in _VALUELESS_PARM_TYPES:
            continue
        expression = _cook_local_expression(parm)
        if expression is not None:
            try:
                default = _component_default(parm)
            except Exception:
                default = None
            # A type's own expression (a Group SOP's $N) is its default.
            if _is_at_default(parm, None, default):
                continue
            summary.append(
                {
                    'name': parm.name(),
                    'label': parm.description(),
                    'value': None,
                    'default': to_jsonable(default),
                    'type': type_name,
                    'expression': expression,
                    'local_variable': True,
                    'note': _COOK_LOCAL_NOTE,
                }
            )
            continue
        try:
            val = parm.eval()
        except Exception:
            continue
        try:
            default = _component_default(parm)
        except Exception:
            default = None
        if _is_at_default(parm, val, default):
            continue
        summary.append(
            {
                'name': parm.name(),
                'label': parm.description(),
                'value': to_jsonable(val),
                'default': to_jsonable(default),
                'type': type_name,
            }
        )
    return summary


def _name_input(
    entry: dict, node: Any, source: Any, output_index: int, named_inputs: bool
) -> None:
    """Name the wire into *entry*'s input where an index alone is ambiguous."""

    with contextlib.suppress(Exception):
        names = list(source.outputNames())
        if len(names) > 1:
            entry['output_index'] = output_index
            if output_index < len(names):
                entry['output_name'] = names[output_index]
    if named_inputs:
        with contextlib.suppress(Exception):
            names = list(node.inputNames())
            if entry['index'] < len(names):
                entry['input_name'] = names[entry['index']]


@register_command(PluginCommand.NODES_GET_NODE_INFO)
def get_node_info(node_path: str) -> dict:
    """Return comprehensive information about a node."""

    node = _get_node(node_path)

    # Errors and warnings BEFORE any parameter is evaluated. Evaluating a
    # cook-local expression outside a cook (a factory ``$N`` in a Group SOP's
    # rangeend, ``@N.x`` in a Ray SOP's dir) sets a transient "Unable to
    # evaluate expression" on the node, and errors() called afterwards in the
    # same main-thread tick makes it stick: a healthy node came back with a
    # real error, and kept it until it was force-cooked. Read first, it is
    # the node's actual state and nothing is left behind.
    try:
        errors = list(node.errors())
    except Exception:
        errors = []
    try:
        warnings = list(node.warnings())
    except Exception:
        warnings = []

    # Only return parameters that differ from their defaults — this keeps
    # the response compact (a complex node can have 500+ parms, most at default).
    # Use get_parameter_schema to inspect the full parameter list.
    all_parms = node.parms()
    parms_summary = _non_default_parms(node, all_parms)

    # Inputs. Which output of the source feeds each one is the wire's own
    # outputIndex(): a VOP input fed by geometryvopglobal's v and one fed by
    # its P differ only there.
    output_of: dict[int, int] = {}
    named_inputs = False
    with contextlib.suppress(Exception):
        output_of = {c.inputIndex(): c.outputIndex() for c in node.inputConnections()}
        named_inputs = node.type().category().name() in ('Vop', 'Cop')
    inputs = []
    for i, conn in enumerate(node.inputs()):
        if conn is not None:
            entry = {
                'index': i,
                'node_path': conn.path(),
                'node_name': conn.name(),
            }
            _name_input(entry, node, conn, output_of.get(i, 0), named_inputs)
            inputs.append(entry)
        else:
            inputs.append({'index': i, 'node_path': None, 'node_name': None})

    # Outputs
    outputs = []
    for conn in node.outputs():
        outputs.append(
            {
                'node_path': conn.path(),
                'node_name': conn.name(),
            }
        )

    # Flags
    flags = {}
    with contextlib.suppress(Exception):
        flags['display'] = node.isDisplayFlagSet()
    with contextlib.suppress(Exception):
        flags['render'] = node.isRenderFlagSet()
    with contextlib.suppress(Exception):
        flags['bypass'] = node.isBypassed()
    with contextlib.suppress(Exception):
        flags['template'] = node.isTemplateFlagSet()
    with contextlib.suppress(Exception):
        flags['lock'] = node.isHardLocked()

    # Cook time
    try:
        cook_time = node.cookTime()
    except Exception:
        cook_time = None

    # Type info — icon omitted (string path, useless to LLM)
    node_type = node.type()
    type_info = {
        'name': node_type.name(),
        'label': node_type.description(),
        'category': node_type.category().name(),
    }

    info = {
        'node_path': node.path(),
        'name': node.name(),
        'type': type_info,
        'total_param_count': len(all_parms),
        'non_default_parameters': parms_summary,
        'input_connectors': node.type().maxNumInputs(),
        'inputs': inputs,
        'outputs': outputs,
        'flags': flags,
        'errors': errors,
        'warnings': warnings,
        'cook_time': cook_time,
        'comment': node.comment(),
        'position': list(node.position()),
        'color': list(node.color().rgb()),
    }
    # What a VOP's connectors carry now: a variadic input is "undef" on the
    # type and becomes float or int once wired, so whether a multiply comes
    # out float is a question about the live node, not its card.
    with contextlib.suppress(Exception):
        if isinstance(node, hou.VopNode):
            info['connector_types'] = {
                'inputs': dict(
                    zip(node.inputNames(), node.inputDataTypes(), strict=False)
                ),
                'outputs': dict(
                    zip(node.outputNames(), node.outputDataTypes(), strict=False)
                ),
            }
    return info


@register_command(PluginCommand.NODES_LIST_CHILDREN)
def list_children(
    parent_path: str,
    recursive: bool = False,
    filter_type: str | None = None,
    include_locked_assets: bool = False,
    dive_target: bool = False,
) -> dict:
    """List children of a network node.

    A locked asset is opaque: its children are the definition's internals, not
    a network. Ask for `include_locked_assets` to read the raw contents, or for
    `dive_target` to read the editable dive target only.
    """

    requested = _get_node(parent_path)
    parent = requested

    if _is_locked_hda(requested) and not include_locked_assets:
        dive_path = _dive_target_path(requested)
        if not (dive_target and dive_path):
            return {
                'parent_path': parent_path,
                'count': 0,
                'truncated': False,
                'locked_asset': True,
                'dive_target_path': dive_path,
                'children': [],
            }
        parent = _get_node(dive_path)

    # A locked asset's contents load on demand: a fresh popsolver answers 0
    # children until synced.
    children = (
        parent.allSubChildren(
            recurse_in_locked_nodes=bool(include_locked_assets),
            sync_delayed_definition=bool(include_locked_assets),
        )
        if recursive
        else parent.children()
    )

    _MAX_CHILDREN = 500
    results = []
    for child in children:
        if filter_type and child.type().name() != filter_type:
            continue
        summary = _node_summary(child)
        if recursive and not include_locked_assets:
            # Say where the listing stopped, so the caller knows there is more.
            with contextlib.suppress(Exception):
                # isNetwork(), not children(): unsynced contents count 0.
                if child.isLockedHDA() is True and child.isNetwork() is True:
                    summary['locked_asset'] = True
        results.append(summary)
        if len(results) >= _MAX_CHILDREN:
            break

    return {
        'parent_path': parent_path,
        'count': len(results),
        'truncated': len(results) >= _MAX_CHILDREN,
        'children': results,
    }


@register_command(PluginCommand.NODES_FIND_NODES)
def find_nodes(
    pattern: str | None = None,
    node_type: str | None = None,
    context: str | None = None,
    inside: str = '/',
) -> dict:
    """Search for nodes by name pattern and/or type."""

    root = _get_node(inside)
    all_nodes = root.allSubChildren()

    _MAX_RESULTS = 500
    results = []
    for node in all_nodes:
        # Filter by name pattern
        if pattern is not None:
            import fnmatch

            if not fnmatch.fnmatch(node.name(), pattern):
                continue

        # Filter by type
        if node_type is not None and node.type().name() != node_type:
            continue

        # Filter by category/context
        if context is not None and node.type().category().name() != context:
            continue

        results.append(_node_summary(node))
        if len(results) >= _MAX_RESULTS:
            break

    return {
        'count': len(results),
        'truncated': len(results) >= _MAX_RESULTS,
        'nodes': results,
    }


@register_command(PluginCommand.NODES_LIST_NODE_TYPES)
def list_node_types(
    context: str,
    filter: str | None = None,
    limit: int = 200,
    **_: Any,
) -> dict:
    """List available node types in a given context category."""

    categories = hou.nodeTypeCategories()
    category = categories.get(context)
    if category is None:
        available = sorted(categories.keys())
        raise ValueError(
            f"Unknown node type category: '{context}'. Available categories: "
            f'{available}'
        )

    types_dict = category.nodeTypes()
    type_list = []
    for type_name, node_type in sorted(types_dict.items()):
        # Skip hidden/deprecated types
        try:
            if node_type.hidden():
                continue
        except Exception:
            pass
        type_list.append(
            {
                'name': type_name,
                'label': node_type.description(),
            }
        )

    if filter:
        f = filter.lower()
        type_list = [
            t for t in type_list if f in t['name'].lower() or f in t['label'].lower()
        ]

    total = len(type_list)
    type_list = type_list[:limit]
    return {
        'context': context,
        'total_count': total,
        'returned_count': len(type_list),
        'truncated': total > limit,
        'types': type_list,
    }


def _input_table(node: hou.Node) -> list[dict[str, Any]]:
    """A node's input connectors in order: index, name, label, data type."""

    names: list[str] = []
    labels: list[str] = []
    data_types: list[str] = []
    with contextlib.suppress(Exception):
        names = list(node.inputNames())
    with contextlib.suppress(Exception):
        labels = list(node.inputLabels())
    with contextlib.suppress(Exception):
        data_types = list(node.inputDataTypes())
    table: list[dict[str, Any]] = []
    for index, name in enumerate(names):
        entry: dict[str, Any] = {'index': index, 'name': name}
        if index < len(labels):
            entry['label'] = labels[index]
        if index < len(data_types):
            entry['data_type'] = data_types[index]
        table.append(entry)
    return table


_NUMBERED = re.compile(r'(.*?)(\d+)')


def _variadic_index(
    inputs: list[dict[str, Any]], name: str, max_inputs: int
) -> int | None:
    """Index of `input3` on a node that grows inputs as they are wired."""

    if not inputs or max_inputs <= len(inputs):
        return None
    first = _NUMBERED.fullmatch(str(inputs[0].get('name', '')))
    wanted = _NUMBERED.fullmatch(name)
    if first is None or wanted is None or wanted.group(1) != first.group(1):
        return None
    stem, start = first.group(1), int(first.group(2))
    if any(entry.get('name') != f'{stem}{start + entry["index"]}' for entry in inputs):
        return None
    index = int(wanted.group(2)) - start
    return index if 0 <= index < max_inputs else None


def _find_input(
    inputs: list[dict[str, Any]], input_name: str, max_inputs: int = 0
) -> int:
    """Index of the input called *input_name*: names first, then labels, then the..."""

    for entry in inputs:
        if entry.get('name') == input_name:
            return int(entry['index'])
    for entry in inputs:
        if entry.get('label') == input_name:
            return int(entry['index'])
    variadic = _variadic_index(inputs, input_name, max_inputs)
    if variadic is not None:
        return variadic
    candidates: list[str] = []
    for entry in inputs:
        for value in (entry.get('name'), entry.get('label')):
            if value and value not in candidates:
                candidates.append(value)
    close = get_close_matches(input_name, candidates, n=3, cutoff=0.4)
    if close:
        hint = f' Did you mean: {close}?'
    else:
        hint = f' Inputs: {candidates[:15] + (["..."] if len(candidates) > 15 else [])}'
    raise ValueError(f"has no input named '{input_name}'.{hint}")


def _find_output(outputs: list[dict[str, Any]], output_name: str) -> int:
    """Index of the output called *output_name*: names first, then labels."""

    for key in ('name', 'label'):
        for entry in outputs:
            if entry.get(key) == output_name:
                return int(entry['index'])
    candidates: list[str] = []
    for entry in outputs:
        for value in (entry.get('name'), entry.get('label')):
            if value and value not in candidates:
                candidates.append(value)
    close = get_close_matches(output_name, candidates, n=3, cutoff=0.4)
    if close:
        hint = f' Did you mean: {close}?'
    else:
        hint = (
            f' Outputs: {candidates[:15] + (["..."] if len(candidates) > 15 else [])}'
        )
    raise ValueError(f"has no output named '{output_name}'.{hint}")


def _output_index(source: hou.Node, source_output: int | str) -> int:
    """*source_output* as an index on the live *source*: an index, or an output name."""

    if isinstance(source_output, int):
        return source_output
    outputs = [
        {'index': i, 'name': name} for i, name in enumerate(source.outputNames())
    ]
    with contextlib.suppress(Exception):
        for entry, label in zip(outputs, source.outputLabels(), strict=False):
            entry['label'] = label
    try:
        return _find_output(outputs, source_output)
    except ValueError as exc:
        raise ValueError(f'{source.path()} {exc}') from None


def _resolve_input_index(
    dest: hou.Node, input_index: int, input_name: str | None
) -> int:
    """Turn an input name (VOP connector such as "base_color") into its index."""

    if not input_name:
        return int(input_index)
    max_inputs = 0
    with contextlib.suppress(Exception):
        max_inputs = int(dest.type().maxNumInputs())
    try:
        return _find_input(_input_table(dest), str(input_name), max_inputs)
    except ValueError as exc:
        raise ValueError(f'{dest.path()} {exc}') from None


def _indirect_input_item(
    subnet: hou.Node, indirect: Any, connectors: list | None = None
) -> Any:
    """Input connector *indirect* of *subnet*, or ValueError saying why not."""

    if isinstance(indirect, float) and indirect.is_integer():
        indirect = int(indirect)
    if isinstance(indirect, bool) or not isinstance(indirect, int):
        raise ValueError(f'indirect_input must be an integer, got {indirect!r}')
    if connectors is None:
        try:
            connectors = list(subnet.indirectInputs())
        except Exception as exc:
            raise ValueError(
                f'{subnet.path()} has no input connectors to wire from: '
                f'{readable_message(exc)}'
            ) from exc
    if not connectors:
        # Not a subnet (a Box answers an empty tuple on 22.0 rather than the
        # documented InvalidNodeType), or a subnet with no inputs.
        raise ValueError(
            f'{subnet.path()} has no input connectors to wire from: it is not a '
            f'subnet, or a subnet without inputs.'
        )
    if not 0 <= indirect < len(connectors):
        raise ValueError(
            f'{subnet.path()} has {len(connectors)} input connector(s); asked for '
            f'#{indirect}.'
        )
    return connectors[indirect]


def _resolve_source(
    source_path: str, indirect_input: Any, dest: hou.Node, output_index: int
) -> Any:
    """The item to wire from: a node, or one of a subnet's indirect inputs."""

    node = _get_node(source_path)
    if indirect_input is None:
        return node
    item = _indirect_input_item(node, indirect_input)
    if dest.parent() != node:
        raise ValueError(
            f"{dest.path()} is not inside {node.path()}: a subnet's input connector "
            f'feeds only nodes inside that subnet.'
        )
    if int(output_index) != 0:
        raise ValueError(
            f'a subnet input connector has one output; output_index must be 0, got '
            f'{output_index}.'
        )
    return item


@register_command(PluginCommand.NODES_CONNECT_NODES)
def connect_nodes(
    source_path: str,
    dest_path: str,
    output_index: int = 0,
    input_index: int = 0,
    input_name: str | None = None,
    indirect_input: int | None = None,
) -> dict:
    """Wire two nodes together."""

    dest = _get_node(dest_path)
    source = _resolve_source(source_path, indirect_input, dest, output_index)

    input_index = _resolve_input_index(dest, input_index, input_name)
    dest.setInput(input_index, source, output_index)

    _focus_network_editor(dest, place_unpositioned=False)

    result = {
        'success': True,
        'source_path': _get_node(source_path).path(),
        'dest_path': dest.path(),
        'output_index': output_index,
        'input_index': input_index,
    }
    if indirect_input is not None:
        # source_path stays a path a caller can reuse; the connector is here.
        result['indirect_input'] = int(indirect_input)
    if cache := dop_cache_note([dest], rewired=True):
        result['simulation_cache'] = cache
    return result


def _non_default_parm_names(node: hou.Node) -> set[str]:
    names = set()
    for parm in node.parms():
        with contextlib.suppress(Exception):
            if not parm.isAtDefault():
                names.add(parm.name())
    return names


@register_command(PluginCommand.NODES_CHANGE_NODE_TYPE)
def change_node_type(
    node_path: str,
    new_type: str,
    keep_name: bool = True,
    keep_parms: bool = True,
    keep_network_contents: bool = True,
) -> dict:
    """Swap a node for another type in place — wires, name, position, flags and..."""

    from ._helpers import _resolve_node_type

    node = _get_node(node_path)
    category = node.type().category()
    resolved = _resolve_node_type(category, new_type)
    if resolved is None:
        close = get_close_matches(new_type, list(category.nodeTypes()), n=3, cutoff=0.5)
        hint = f' Did you mean: {close}?' if close else ''
        raise ValueError(
            f"Type '{new_type}' does not exist in {category.name()}.{hint}"
        )
    old_type = node.type().name()
    same_type = resolved.name() == old_type
    # Re-applying the same type only does something when the contents are
    # to be reset; otherwise it would be a no-op that still costs an undo.
    changing = not same_type or not keep_network_contents

    before_parms = {p.name() for p in node.parms()}
    before_non_default = _non_default_parm_names(node)
    changed = node
    if changing:
        kwargs = {
            'keep_name': bool(keep_name),
            'keep_parms': bool(keep_parms),
            'keep_network_contents': bool(keep_network_contents),
        }
        if same_type:
            kwargs['force_change_on_node_type_match'] = True
        try:
            changed = node.changeNodeType(resolved.name(), **kwargs)
        except Exception as exc:
            raise ValueError(
                f'Could not change {node_path} ({old_type}) to {resolved.name()}: '
                f'{readable_message(exc)}'
            ) from exc
        _focus_network_editor(changed, place_unpositioned=False)

    after_parms = {p.name() for p in changed.parms()}
    lost = before_non_default - _non_default_parm_names(changed)
    result: dict[str, Any] = {
        'success': True,
        'node_path': changed.path(),
        'old_type': old_type,
        'new_type': changed.type().name(),
        'changed': changing,
        'keep_parms': bool(keep_parms),
        'keep_network_contents': bool(keep_network_contents),
        # Set values with no home on the new type, and set values that are
        # back at their default: together, everything the swap lost.
        'parms_dropped': sorted(lost - after_parms),
        'parms_reset': sorted(lost & after_parms),
        # Every parameter the new type lacks, set or not.
        'parms_removed_count': len(before_parms - after_parms),
        'inputs': [i.path() if i is not None else None for i in changed.inputs()],
        'outputs': [o.path() for o in changed.outputs()],
    }
    if not changing:
        result['message'] = (
            f'{changed.path()} is already of type {old_type}; nothing changed.'
        )
    with contextlib.suppress(Exception):
        result['child_count'] = len(changed.children())
    with contextlib.suppress(Exception):
        if changed.type().definition() is not None:
            result['matches_definition'] = changed.matchesCurrentDefinition()
    return result


# The value types HOM's pressButton accepts in its arguments dict.
_BUTTON_ARGUMENT_TYPES = (bool, int, float, str)


@register_command(PluginCommand.NODES_PRESS_BUTTON)
def press_button(
    node_path: str,
    parm_name: str,
    arguments: dict | None = None,
    cook: bool = False,
    action: bool = False,
) -> dict:
    """Press a button parameter and report what the node says afterwards."""

    node = _get_node(node_path)
    parm = node.parm(parm_name)
    if parm is None:
        names = [p.name() for p in node.parms()]
        close = get_close_matches(parm_name, names, n=3, cutoff=0.4)
        buttons = [
            p.name() for p in node.parms() if p.parmTemplate().type().name() == 'Button'
        ]
        hint = f' Did you mean: {close}?' if close else ''
        raise ValueError(
            f"{node.path()} has no parameter '{parm_name}'.{hint} Buttons on this "
            f'node: '
            f'{buttons}'
        )
    for key, value in (arguments or {}).items():
        if not isinstance(value, _BUTTON_ARGUMENT_TYPES):
            raise ValueError(
                f"arguments['{key}'] is {type(value).__name__}; a button callback "
                f'takes only int, bool, float or str values. Nothing was pressed.'
            )
    template = parm.parmTemplate()
    parm_type = template.type().name()
    action_code = action_script(parm)
    action_help = ''
    with contextlib.suppress(Exception):
        help_tag = template.tags().get('script_action_help')
        if isinstance(help_tag, str):
            action_help = help_tag
    if action and not action_code:
        raise ValueError(
            f'{node.path()}/{parm_name} has no action button (no script_action tag). '
            f'Nothing was run.'
        )
    if not action and parm_type != 'Button' and not callback_script(parm):
        # pressButton() on it returns without doing anything, which used to
        # come back as success.
        message = (
            f'{node.path()}/{parm_name} is a {parm_type} parameter with no callback: '
            f'pressing it does nothing. Nothing was run.'
        )
        if action_code:
            message += (
                f' Its action button ({action_help or "script_action"}) runs with '
                f'action=True; an action that opens a picker or a dialog holds the '
                f'bridge until it is closed.'
            )
        raise ValueError(message)
    started = time.perf_counter()
    try:
        if action:
            run_action(parm, dict(arguments) if arguments else None)
            route = 'action'
        else:
            # Not parm.pressButton() for a Python callback: one that raises
            # opens Houdini's modal error window and holds the main thread.
            route = press(parm, dict(arguments) if arguments else None)
    except CallbackError as exc:
        raise ValueError(f'Button callback failed: {exc}') from exc
    except Exception as exc:
        raise ValueError(
            f'Callback of {node.path()}/{parm_name} failed: {readable_message(exc)}'
        ) from exc
    duration_ms = round((time.perf_counter() - started) * 1000, 1)
    result: dict[str, Any] = {
        'success': True,
        'node_path': node.path(),
        'parm_name': parm.name(),
        'parm_type': parm_type,
        'duration_ms': duration_ms,
        'cooked': False,
        # python: the callback script ran here; hscript / native: pressButton();
        # action: the parm's script_action ran here.
        'callback_route': route,
    }
    if action and action_help:
        result['action_help'] = action_help
    if cook:
        # A failed cook is an answer, not a failure of the press: its
        # messages land in errors() below.
        with contextlib.suppress(Exception):
            node.cook(force=False)
        result['cooked'] = True
    with contextlib.suppress(Exception):
        result['needs_cook'] = node.needsToCook()
    for key, read in (('errors', node.errors), ('warnings', node.warnings)):
        try:
            result[key] = list(read())
        except Exception:
            result[key] = []
    with contextlib.suppress(Exception):
        # Built-in buttons (File's Reload, Stash's Stash Input) are handled in
        # C++ and have no script callback; False does not mean inert.
        result['has_script_callback'] = bool(template.scriptCallback())
    if parm_type != 'Button' and not action:
        result['note'] = (
            f"'{parm_name}' is a {parm_type} parameter, not a Button; its callback "
            f'script (if any) was triggered the way pressButton does for any parameter.'
        )
    return result


@register_command(PluginCommand.NODES_CONNECT_NODES_BATCH)
def connect_nodes_batch(
    connections: list,
) -> dict:
    """Wire multiple node pairs in a single call."""

    results = []
    errors = []
    wired: list = []

    last_dest = None
    for conn in connections:
        src_path = conn['source_path']
        dst_path = conn['dest_path']
        out_idx = int(conn.get('output_index', 0))
        in_idx = int(conn.get('input_index', 0))
        try:
            dest = _get_node(dst_path)
            source = _resolve_source(
                src_path, conn.get('indirect_input'), dest, out_idx
            )
            in_idx = _resolve_input_index(dest, in_idx, conn.get('input_name'))
            dest.setInput(in_idx, source, out_idx)
            last_dest = dest
            wired.append(dest)
            entry = {
                'source_path': _get_node(src_path).path(),
                'dest_path': dest.path(),
                'output_index': out_idx,
                'input_index': in_idx,
            }
            if conn.get('indirect_input') is not None:
                entry['indirect_input'] = int(conn['indirect_input'])
            results.append(entry)
        except Exception as exc:
            errors.append(
                {
                    'source_path': src_path,
                    'dest_path': dst_path,
                    'error': str(exc),
                }
            )

    if last_dest is not None:
        _focus_network_editor(last_dest, place_unpositioned=False)

    reply = {
        'success': len(errors) == 0,
        'connected': results,
        'errors': errors,
    }
    if cache := dop_cache_note(wired, rewired=True):
        reply['simulation_cache'] = cache
    return reply


@register_command(PluginCommand.NODES_DISCONNECT_NODE)
def disconnect_node(
    node_path: str,
    input_index: int | None = None,
    disconnect_all: bool = False,
) -> dict:
    """Disconnect one or all inputs of a node."""

    node = _get_node(node_path)
    disconnected = []
    # inputConnections(), not inputs(): inputs() hides a wire from a subnet's
    # input connector (it reports the node outside the subnet, or None when
    # that input is open), so such a wire could be made but not removed.
    connected = sorted({conn.inputIndex() for conn in node.inputConnections()})

    if disconnect_all:
        for i in connected:
            node.setInput(i, None)
            disconnected.append(i)
    elif input_index is not None:
        if input_index in connected:
            node.setInput(input_index, None)
            disconnected.append(input_index)
        else:
            raise ValueError(
                f'Input index {input_index} is out of range or already disconnected '
                f'on node {node_path}. Connected inputs: {connected}.'
            )
    else:
        raise ValueError('provide either input_index or set disconnect_all=True.')

    reply = {
        'success': True,
        'node_path': node_path,
        'disconnected_inputs': disconnected,
    }
    if cache := dop_cache_note([node], rewired=True):
        reply['simulation_cache'] = cache
    return reply


@register_command(PluginCommand.NODES_REORDER_INPUTS)
def reorder_inputs(node_path: str, new_order: list) -> dict:
    """Reorder the input connections of a node."""

    node = _get_node(node_path)
    # Every wire with the item it comes from and that item's output: a
    # subnet input connector is an item, not a node, and inputs() hides it.
    wires = {
        conn.inputIndex(): (conn.inputItem(), conn.inputItemOutputIndex())
        for conn in node.inputConnections()
    }
    count = max([len(node.inputs())] + [index + 1 for index in wires])

    if len(new_order) > count:
        raise ValueError(
            f'new_order has {len(new_order)} entries but node only has {count} inputs.'
        )
    bad = [old for old in new_order if not isinstance(old, int) or not 0 <= old < count]
    if bad:
        raise ValueError(
            f'new_order refers to inputs {bad}; {node_path} has inputs 0-{count - 1}.'
        )

    # Inputs new_order does not mention follow in their original order. They
    # used to be cleared and never rewired: [1, 0] on a 3-input merge, the
    # docstring's own example, silently dropped input 2.
    order = list(new_order) + [i for i in range(count) if i not in new_order]

    # Checked before anything is disconnected, so a refusal leaves the wires.
    for i in wires:
        node.setInput(i, None)
    for new_idx, old_idx in enumerate(order):
        if old_idx in wires:
            item, output_index = wires[old_idx]
            node.setInput(new_idx, item, output_index)

    reply = {
        'success': True,
        'node_path': node_path,
        'new_order': order,
    }
    if cache := dop_cache_note([node], rewired=True):
        reply['simulation_cache'] = cache
    return reply


@register_command(PluginCommand.NODES_SET_NODE_FLAGS)
def set_node_flags(
    node_path: str,
    display: bool | None = None,
    render: bool | None = None,
    bypass: bool | None = None,
    template: bool | None = None,
    lock: bool | None = None,
) -> dict:
    """Set one or more flags on a node."""

    node = _get_node(node_path)
    requested = {
        'display': display,
        'render': render,
        'bypass': bypass,
        'template': template,
        'lock': lock,
    }
    changed: dict[str, bool] = {}
    not_applied: dict[str, str] = {}
    for flag, wanted in requested.items():
        if wanted is None:
            continue
        setter, getter = _FLAG_ACCESSORS[flag]
        try:
            getattr(node, setter)(bool(wanted))
            actual = bool(getattr(node, getter)())
        except (AttributeError, hou.OperationFailed) as exc:
            not_applied[flag] = (
                f'{node.type().name()} has no {flag} flag ({type(exc).__name__})'
            )
            continue
        # Read back: Houdini ignores some requests without raising. A SOP's
        # display flag cannot be turned off (one node always holds it), and
        # this used to report display: False regardless.
        if actual == bool(wanted):
            changed[flag] = actual
        else:
            not_applied[flag] = f'asked for {bool(wanted)}, Houdini kept {actual}'

    if not changed and not not_applied:
        raise ValueError('no flags were specified.')

    if changed.get('display'):
        _focus_network_editor(node, place_unpositioned=False)

    result = {
        'success': not not_applied,
        'node_path': node_path,
        'changed_flags': changed,
    }
    if not_applied:
        result['not_applied'] = not_applied
    return result


# flag -> (setter, reader), for set_node_flags' readback.
_FLAG_ACCESSORS = {
    'display': ('setDisplayFlag', 'isDisplayFlagSet'),
    'render': ('setRenderFlag', 'isRenderFlagSet'),
    'bypass': ('bypass', 'isBypassed'),
    'template': ('setTemplateFlag', 'isTemplateFlagSet'),
    'lock': ('setHardLocked', 'isHardLocked'),
}


@register_command(PluginCommand.NODES_LAYOUT_CHILDREN)
def layout_children(parent_path: str, spacing: float | None = None) -> dict:
    """Auto-layout the children of a network node."""

    # Resolve first, so a bad path is named even when layout is disabled.
    parent = _get_node(parent_path)

    if not auto_layout_enabled():
        return {
            'success': False,
            'skipped': True,
            'reason': f'Auto-layout is disabled ({constants.AUTO_LAYOUT}=0).',
        }

    if spacing is not None:
        parent.layoutChildren(horizontal_spacing=spacing, vertical_spacing=spacing)
    else:
        parent.layoutChildren()

    children_paths = [c.path() for c in parent.children()]

    return {
        'success': True,
        'parent_path': parent_path,
        'laid_out_count': len(children_paths),
    }


@register_command(PluginCommand.NODES_SET_NODE_POSITION)
def set_node_position(node_path: str, x: float, y: float) -> dict:
    """Set the position of a node in the network editor."""

    node = _get_node(node_path)
    node.setPosition(hou.Vector2(x, y))

    return {
        'success': True,
        'node_path': node_path,
        'position': [x, y],
    }


@register_command(PluginCommand.NODES_SET_NODE_COLOR)
def set_node_color(node_path: str, r: float, g: float, b: float) -> dict:
    """Set the color of a node in the network editor."""

    node = _get_node(node_path)
    color = hou.Color((r, g, b))
    node.setColor(color)

    return {
        'success': True,
        'node_path': node_path,
        'color': [r, g, b],
    }


@register_command(PluginCommand.NODES_CREATE_NETWORK_BOX)
def create_network_box(
    parent_path: str,
    node_paths: list[str] | None = None,
    comment: str | None = None,
    color: list[float] | None = None,
) -> dict:
    """Draw a network box around nodes, so a built graph explains itself."""

    parent = _get_node(parent_path)
    box = parent.createNetworkBox()
    for path in node_paths or []:
        node = _get_node(path)
        if node.parent() != parent:
            raise ValueError(
                f'{path} is not a child of {parent_path}; a box only holds siblings.'
            )
        box.addItem(node)
    if comment:
        box.setComment(comment)
    if color is not None:
        box.setColor(hou.Color(*color))
    if node_paths:
        box.fitAroundContents()
    return {
        'success': True,
        'name': box.name(),
        'parent_path': parent.path(),
        'contains': [n.path() for n in box.nodes()],
    }


@register_command(PluginCommand.NODES_CREATE_STICKY_NOTE)
def create_sticky_note(
    parent_path: str,
    text: str,
    position: list[float] | None = None,
    size: list[float] | None = None,
    color: list[float] | None = None,
) -> dict:
    """Leave a note in a network."""

    parent = _get_node(parent_path)
    note = parent.createStickyNote()
    note.setText(text)
    if position is not None:
        note.setPosition(hou.Vector2(*position))
    if size is not None:
        note.setSize(hou.Vector2(*size))
    if color is not None:
        note.setColor(hou.Color(*color))
    return {
        'success': True,
        'name': note.name(),
        'parent_path': parent.path(),
        'position': list(note.position()),
    }


def _sticky_notes_in(node: hou.Node) -> list[hou.StickyNote]:
    """Every sticky note in *node*'s network and in nested networks."""

    notes = list(node.stickyNotes())
    for child in node.children():
        if child.isNetwork():
            notes.extend(_sticky_notes_in(child))
    return notes


@register_command(PluginCommand.NODES_DELETE_STICKY_NOTES)
def delete_sticky_notes(parent_path: str, recursive: bool = True) -> dict:
    """Delete sticky notes under a network, recursing into nested networks."""

    parent = _get_node(parent_path)
    notes = _sticky_notes_in(parent) if recursive else list(parent.stickyNotes())
    paths = [note.path() for note in notes]
    for note in notes:
        note.destroy()
    return {
        'success': True,
        'parent_path': parent.path(),
        'recursive': recursive,
        'deleted_count': len(paths),
        'deleted': paths,
    }


_XFORM_PARMS = {'translate': 't', 'rotate': 'r', 'scale': 's'}


@register_command(PluginCommand.NODES_SET_OBJECT_TRANSFORM)
def set_object_transform(
    node_path: str,
    translate: list[float] | None = None,
    rotate: list[float] | None = None,
    scale: list[float] | None = None,
    parent: str | None = None,
) -> dict:
    """Set an object's transform parameters and/or parent in one call."""

    node = _get_node(node_path)
    if node.type().category().name() != 'Object':
        raise ValueError(
            f'{node_path} is a {node.type().category().name()} node; transforms live '
            f'on '
            f'object-level nodes under /obj.'
        )
    applied: dict = {}
    for key, values in (('translate', translate), ('rotate', rotate), ('scale', scale)):
        prefix = _XFORM_PARMS[key]
        if values is None:
            continue
        if len(values) != 3:
            raise ValueError(f'{key} needs three values, got {len(values)}.')
        tuple_parm = node.parmTuple(prefix)
        if tuple_parm is None:
            raise ValueError(f"{node_path} has no '{prefix}' parameter.")
        tuple_parm.set([float(v) for v in values])
        applied[key] = list(tuple_parm.eval())
    if parent is not None:
        if parent == '':
            node.setInput(0, None)
            applied['parent'] = None
        else:
            new_parent = _get_node(parent)
            node.setInput(0, new_parent)
            applied['parent'] = new_parent.path()
    if not applied:
        raise ValueError('nothing to set: give translate, rotate, scale or parent.')
    return {'success': True, 'node_path': node.path(), **applied}
