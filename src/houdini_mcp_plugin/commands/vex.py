"""VEX handlers for Houdini MCP."""

from __future__ import annotations

import contextlib
import re

import hou

from houdini_mcp_protocol import PluginCommand

from ..dispatcher import register_command
from ..errors import readable_message
from ..ui import focus_network_editor as _focus_network_editor


def _get_node(node_path: str) -> hou.Node:
    """Return a node or raise if not found."""

    node = hou.node(node_path)
    if node is None:
        raise ValueError(f'Node not found: {node_path}')
    return node


def _validate_vex_quick(node: hou.Node) -> dict:
    """Cook a wrangle node and return any VEX errors/warnings."""

    with contextlib.suppress(hou.OperationFailed):
        node.cook(
            force=False
        )  # the new code already dirtied it; force only redid the work

    errors = []
    warnings = []
    with contextlib.suppress(Exception):
        errors = list(node.errors() or [])
    with contextlib.suppress(Exception):
        warnings = list(node.warnings() or [])

    return {
        'vex_valid': len(errors) == 0,
        'vex_errors': errors,
        'vex_warnings': warnings,
    }


def _resolve_class_value(node: hou.Node, run_over: str) -> int:
    """Resolve a run_over string to the correct menu index on this node."""

    class_parm = node.parm('class')
    if class_parm is None:
        raise ValueError(
            f"Node {node.path()} has no 'class' parameter — is it an Attribute Wrangle?"
        )

    template = class_parm.parmTemplate()
    labels = list(template.menuLabels())
    items = list(template.menuItems())

    # Try exact match first (case-insensitive), then substring match
    target = run_over.strip().lower()
    for idx, label in enumerate(labels):
        if label.lower() == target:
            return int(items[idx]) if items[idx].isdigit() else idx
    for idx, label in enumerate(labels):
        if target in label.lower():
            return int(items[idx]) if items[idx].isdigit() else idx

    raise ValueError(
        f"Invalid run_over value '{run_over}'. Available options: {labels}"
    )


def _reverse_class_label(node: hou.Node) -> str | None:
    """Return the human-readable label for the current class value."""

    class_parm = node.parm('class')
    if class_parm is None:
        return None
    value = class_parm.eval()
    template = class_parm.parmTemplate()
    labels = list(template.menuLabels())
    items = list(template.menuItems())
    for idx, item in enumerate(items):
        if (item.isdigit() and int(item) == value) or idx == value:
            return labels[idx] if idx < len(labels) else str(value)
    return str(value)


# Regex pattern for detecting absolute channel paths in VEX code
_RE_ABS_CH = re.compile(r'ch[sfiv]?\s*\(\s*["\']/')


def _check_channel_paths(vex_code: str) -> list[str]:
    """Return warnings if the VEX code contains absolute channel refs."""

    warnings = []
    if _RE_ABS_CH.search(vex_code):
        warnings.append(
            'VEX contains absolute channel path (ch("/...")). '
            'Prefer relative paths — use ../parm_name to reach the '
            'immediate parent, ../../parm_name for two levels up, etc. '
            'Absolute paths break when nodes are renamed or moved.'
        )
    return warnings


@register_command(PluginCommand.VEX_CREATE_WRANGLE)
def create_wrangle(
    parent_path: str,
    vex_code: str,
    run_over: str = 'Points',
    name: str | None = None,
) -> dict:
    """Create an Attribute Wrangle node with VEX code."""

    parent = hou.node(parent_path)
    if parent is None:
        raise ValueError(f'Parent node not found: {parent_path}')

    # Create the attribwrangle node
    try:
        if name:
            node = parent.createNode('attribwrangle', name)
        else:
            node = parent.createNode('attribwrangle')
    except hou.OperationFailed as e:
        raise ValueError(
            f'Failed to create attribwrangle node: {readable_message(e)}'
        ) from e

    # Set the VEX snippet
    snippet_parm = node.parm('snippet')
    if snippet_parm is None:
        raise ValueError(
            f"Created node {node.path()} does not have a 'snippet' parameter."
        )
    snippet_parm.set(vex_code)

    # Set the run_over class (resolved dynamically from menu labels)
    class_value = _resolve_class_value(node, run_over)
    node.parm('class').set(class_value)

    _focus_network_editor(node)

    # Build relative prefix map so the AI knows what each ../ level reaches.
    ancestors = {}
    current = node.parent()
    level = 1
    while current is not None:
        dots = '/'.join(['..'] * level)
        ancestors[dots] = current.path()
        current = current.parent()
        level += 1

    result = {
        'success': True,
        'node_path': node.path(),
        'node_name': node.name(),
        'run_over': run_over,
        'vex_code': vex_code,
        'channel_prefix': '../',
        'channel_ancestors': ancestors,
        'channel_hint': (
            'Use relative paths for channel references. '
            'See channel_ancestors to find the correct ../ depth '
            'for the node whose parameters you want to reference.'
        ),
    }
    result.update(_validate_vex_quick(node))

    path_warnings = _check_channel_paths(vex_code)
    if path_warnings:
        existing = result.get('vex_warnings')
        if not isinstance(existing, list):
            existing = []
            result['vex_warnings'] = existing
        existing.extend(path_warnings)

    return result


@register_command(PluginCommand.VEX_SET_WRANGLE_CODE)
def set_wrangle_code(node_path: str, vex_code: str) -> dict:
    """Set VEX code on an existing Attribute Wrangle node."""

    node = _get_node(node_path)

    snippet_parm = node.parm('snippet')
    if snippet_parm is None:
        raise ValueError(
            f"Node {node_path} does not have a 'snippet' parameter. Is it an Attribute "
            f'Wrangle?'
        )

    snippet_parm.set(vex_code)

    result = {
        'success': True,
        'node_path': node.path(),
        'vex_code': vex_code,
        'channel_prefix': '../',
    }
    result.update(_validate_vex_quick(node))

    path_warnings = _check_channel_paths(vex_code)
    if path_warnings:
        existing = result.get('vex_warnings')
        if not isinstance(existing, list):
            existing = []
            result['vex_warnings'] = existing
        existing.extend(path_warnings)

    return result


@register_command(PluginCommand.VEX_GET_WRANGLE_CODE)
def get_wrangle_code(node_path: str) -> dict:
    """Read the VEX code from an Attribute Wrangle node."""

    node = _get_node(node_path)

    snippet_parm = node.parm('snippet')
    if snippet_parm is None:
        raise ValueError(
            f"Node {node_path} does not have a 'snippet' parameter. Is it an Attribute "
            f'Wrangle?'
        )

    vex_code = snippet_parm.eval()

    # Also get the run_over class (resolved dynamically from menu labels)
    run_over = _reverse_class_label(node)

    return {
        'node_path': node.path(),
        'vex_code': vex_code,
        'run_over': run_over,
    }


@register_command(PluginCommand.VEX_CREATE_VEX_EXPRESSION)
def create_vex_expression(
    node_path: str,
    parm_name: str,
    vex_code: str,
) -> dict:
    """Set a parameter expression, refusing VEX that cannot run there."""

    import re

    node = _get_node(node_path)

    parm = node.parm(parm_name)
    if parm is None:
        raise ValueError(f"Parameter '{parm_name}' not found on node {node_path}.")
    if re.search(r'(^|[^\w$])[fvisp]?\[?\]?@\w|;\s*$', vex_code):
        raise ValueError(
            "that is VEX (attribute @ syntax or a trailing ';'), which a parameter "
            'expression cannot run: parameters take HScript or Python. Put VEX in a '
            'wrangle with create_wrangle, or write the HScript equivalent (point(), '
            'ch()).'
        )
    # Validated before it is set. setExpression does not parse, eval() of an
    # unknown function answers 0 without raising, and the node error that a
    # cook leaves behind outlives a later valid expression (all measured on
    # 22.0.368). hscriptExpression with the node as pwd raises on an unknown
    # function or a bracing error and resolves relative references.
    previous = hou.pwd()
    try:
        hou.setPwd(node)
        hou.hscriptExpression(vex_code)
    except hou.OperationFailed as e:
        detail = str(e).replace('The attempted operation failed.', '').strip()
        raise ValueError(
            f'The expression does not evaluate on {node_path}/{parm_name}, so it was '
            f'not set: {detail or readable_message(e)}'
        ) from e
    finally:
        hou.setPwd(previous)
    from .parameters import set_whole_expression

    replaced = set_whole_expression(parm, vex_code, hou.exprLanguage.Hscript)
    value = parm.eval()

    return {
        'success': True,
        'node_path': node.path(),
        'parm_name': parm_name,
        'expression': vex_code,
        'language': 'hscript',
        'value': value if isinstance(value, (int, float, str)) else str(value),
        **({'replaced_keyframes': replaced} if replaced else {}),
    }


@register_command(PluginCommand.VEX_VALIDATE_VEX)
def validate_vex(node_path: str) -> dict:
    """Validate VEX code by cooking the node and checking for errors."""

    node = _get_node(node_path)

    # Read the current VEX code for reference
    vex_code = None
    snippet_parm = node.parm('snippet')
    if snippet_parm is not None:
        vex_code = snippet_parm.eval()

    # Force cook the node to trigger VEX compilation. A failure here is the
    # expected path for broken VEX; the errors are read off the node below.
    with contextlib.suppress(hou.OperationFailed):
        node.cook(
            force=False
        )  # the new code already dirtied it; force only redid the work

    # Gather errors and warnings
    errors = []
    warnings = []

    try:
        node_errors = node.errors()
        if node_errors:
            errors = list(node_errors)
    except Exception:
        pass

    try:
        node_warnings = node.warnings()
        if node_warnings:
            warnings = list(node_warnings)
    except Exception:
        pass

    is_valid = len(errors) == 0

    result = {
        'node_path': node.path(),
        'is_valid': is_valid,
        'errors': errors,
        'warnings': warnings,
    }

    if vex_code is not None:
        result['vex_code'] = vex_code

    if is_valid:
        result['message'] = 'VEX code is valid.'
    else:
        result['message'] = f'VEX code has {len(errors)} error(s).'

    return result
