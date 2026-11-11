"""Materials & Shaders handlers for Houdini MCP."""

from __future__ import annotations

from typing import Any

import hou

from houdini_mcp_protocol import PluginCommand

from ..host import register_command
from ..runtime import config, ui
from ..runtime import errors as error_helpers
from .nodes import (
    _component_default,
    _is_at_default,
    _refuse_taken_name,
)


def _get_node(node_path: str) -> hou.Node:
    """Resolve a node path and raise a clear error if it does not exist."""

    node = hou.node(node_path)
    if node is None:
        raise ValueError(f'Node not found: {node_path}')
    return node


_MATERIAL_PARM_HINTS = ('materialpath', 'matspecpath', 'matpath', 'shop_material')
_ASSIGNMENT_ROOTS = ('/obj', '/stage')
_material_parm_cache: dict[str, list[str]] = {}


def _material_parm_templates(node_type: hou.NodeType) -> list[str]:
    """String parameter names of *node_type* that hold a material path."""

    key = node_type.nameWithCategory()
    cached = _material_parm_cache.get(key)
    if cached is not None:
        return cached
    names: list[str] = []

    def walk(templates: Any) -> None:
        for template in templates:
            if template.type() == hou.parmTemplateType.Folder:
                walk(template.parmTemplates())
                continue
            if template.type() != hou.parmTemplateType.String:
                continue
            lowered = template.name().lower()
            if any(hint in lowered for hint in _MATERIAL_PARM_HINTS):
                names.append(template.name())

    try:
        walk(node_type.parmTemplateGroup().entries())
    except Exception:
        names = []
    _material_parm_cache[key] = names
    return names


def _find_material_assignments(mat_path: str) -> tuple[list[str], int]:
    """Paths of nodes whose material-path parameters name *mat_path*."""

    hits: list[str] = []
    scanned = 0
    for root_path in _ASSIGNMENT_ROOTS:
        root = hou.node(root_path)
        if root is None:
            continue
        for child in root.allSubChildren():
            scanned += 1
            names = _material_parm_templates(child.type())
            if not names:
                continue
            found = False
            for name in names:
                if '#' in name:
                    prefix = name.split('#', 1)[0]
                    candidates = [
                        p
                        for p in child.parms()
                        if p.name().startswith(prefix)
                        and p.name()[len(prefix) :].isdigit()
                    ]
                else:
                    parm = child.parm(name)
                    candidates = [parm] if parm is not None else []
                for parm in candidates:
                    try:
                        value = parm.evalAsString()
                    except Exception:
                        continue
                    if mat_path in value:
                        found = True
                        break
                if found:
                    break
            if found:
                hits.append(child.path())
    return hits, scanned


def _material_summary(node: hou.Node) -> dict[str, Any]:
    """Return a compact summary dict for a material node."""

    return {
        'path': node.path(),
        'type': node.type().name(),
        'label': node.type().description(),
        'param_count': len(node.parms()),
    }


@register_command(PluginCommand.MATERIALS_LIST_MATERIALS)
def _list_materials(*, root_path: str = '/mat', **_: Any) -> dict[str, Any]:
    """List all material nodes under the given root path."""

    # The requested root must exist. The loop below tolerates a missing node so
    # that the /stage it adds on its own can be absent, but applying that tolerance
    # to the caller's own argument meant a misspelled root_path came back
    # {"count": 0, "materials": []} -- indistinguishable from a scene with no
    # materials, and the caller goes looking for why its shaders vanished.
    if hou.node(root_path) is None:
        raise ValueError(
            f'Root path not found: {root_path}. Materials usually live under /mat, '
            f'or under a material library LOP in /stage.'
        )

    materials: list[dict[str, Any]] = []
    search_paths = [root_path]

    # Also search /stage if it exists and is not already the root
    if root_path != '/stage' and hou.node('/stage') is not None:
        search_paths.append('/stage')

    for search_path in search_paths:
        root = hou.node(search_path)
        if root is None:
            continue

        for node in root.allSubChildren(recurse_in_locked_nodes=False):
            # A material is a VOP whose parent is not itself a VOP: it sits in
            # /mat, a matnet or a Material Library, not inside a builder. The
            # old test (any Vop, or "material"/"shader" in the type name)
            # listed every shader node inside every builder as a material, and
            # assignmaterial / materiallibrary LOPs as materials too.
            category = node.type().category().name()
            parent = node.parent()
            parent_category = parent.type().category().name() if parent else ''
            if category == 'Shop' or (category == 'Vop' and parent_category != 'Vop'):
                materials.append(_material_summary(node))

    return {
        'count': len(materials),
        'materials': materials,
    }


@register_command(PluginCommand.MATERIALS_GET_MATERIAL_INFO)
def _get_material_info(*, node_path: str, **_: Any) -> dict[str, Any]:
    """Get detailed information about a material node."""

    node = _get_node(node_path)

    # Gather non-default parameters
    params: dict[str, Any] = {}
    for parm in node.parms():
        try:
            val = parm.eval()
            # Per component, as node_handlers does: the tuple default made
            # every vector component read as changed.
            if not _is_at_default(parm, val, _component_default(parm)):
                params[parm.name()] = val
        except Exception:
            pass

    # List shader VOP nodes inside (if this is a material builder)
    shaders: list[dict[str, str]] = []
    try:
        for child in node.children():
            if child.type().category().name() == 'Vop':
                shaders.append(
                    {
                        'name': child.name(),
                        'path': child.path(),
                        'type': child.type().name(),
                    }
                )
    except Exception:
        pass

    # Nodes that reference this material: material-path parameters only, on
    # the node types that have one (see _find_material_assignments).
    try:
        assignments, scanned = _find_material_assignments(node.path())
    except Exception:
        assignments, scanned = [], 0

    return {
        'path': node.path(),
        'type': node.type().name(),
        'params': params,
        'shaders': shaders,
        'assignments': assignments,
        'assignment_scan': {'nodes': scanned, 'roots': list(_ASSIGNMENT_ROOTS)},
    }


# The documented create_material_network keys, per shader node type. Only
# metalness happens to share its name with the mtlxstandard_surface parameter;
# base_color and roughness were dropped on the floor, silently (#39).
_SHADER_PARM_ALIASES: dict[str, dict[str, str]] = {
    'mtlxstandard_surface': {'roughness': 'specular_roughness'},
    'principledshader::2.0': {
        'base_color': 'basecolor',
        'roughness': 'rough',
        'metalness': 'metallic',
        'opacity': 'opac',
    },
}


def _apply_shader_params(
    node: hou.Node, shader_type: str, params: dict[str, Any]
) -> tuple[dict[str, str], dict[str, str]]:
    """Set *params* on a shader node; a list sets the parm tuple of that name."""

    aliases = _SHADER_PARM_ALIASES.get(shader_type, {})
    applied: dict[str, str] = {}
    skipped: dict[str, str] = {}
    for key, value in params.items():
        name = aliases.get(key, key)
        target = (
            node.parmTuple(name)
            if isinstance(value, (list, tuple))
            else node.parm(name)
        )
        if target is None:
            skipped[key] = f"no parameter '{name}' on {shader_type}"
            continue
        try:
            target.set(value)
        except Exception as exc:
            skipped[key] = error_helpers.readable_message(exc)
            continue
        applied[key] = name
    return applied, skipped


@register_command(PluginCommand.MATERIALS_CREATE_MATERIAL_NETWORK)
def _create_material_network(
    *,
    name: str,
    shader_type: str = 'principled',
    params: dict[str, Any] | None = None,
    **_: Any,
) -> dict[str, Any]:
    """Create a new material network in /mat."""

    mat_context = hou.node('/mat')
    if mat_context is None:
        # Create /mat if it doesn't exist
        mat_context = hou.node('/').createNode('matnet', 'mat')

    # Map shader_type to actual Houdini node type
    type_map = {
        'principled': 'principledshader::2.0',
        'materialx': 'mtlxstandard_surface',
    }
    actual_type = type_map.get(shader_type, shader_type)
    _refuse_taken_name(mat_context, name)

    try:
        node = mat_context.createNode(actual_type, node_name=name)
    except hou.OperationFailed as e:
        raise ValueError(
            f"Failed to create material of type '{actual_type}' in /mat: "
            f'{error_helpers.readable_message(e)}'
        ) from e

    applied, skipped = _apply_shader_params(node, actual_type, params or {})

    config.place_new_node(node)
    ui.focus_network_editor(node)

    return {
        'material_path': node.path(),
        'shader_type': actual_type,
        'applied': applied,
        'skipped': skipped,
    }


@register_command(PluginCommand.MATERIALS_ASSIGN_MATERIAL)
def _assign_material(
    *,
    geo_path: str,
    material_path: str,
    **_: Any,
) -> dict[str, Any]:
    """Assign a material to a geometry node."""

    geo_node = _get_node(geo_path)

    # Find the SOP network inside the geo node
    # Look for the display node (the one with the display flag set)
    display_node = None
    sop_children = geo_node.children()

    for child in sop_children:
        try:
            if child.isDisplayFlagSet():
                display_node = child
                break
        except Exception:
            continue

    if display_node is None and sop_children:
        display_node = sop_children[-1]

    # Create a material SOP
    mat_sop = geo_node.createNode('material', node_name='assign_material')

    # Connect to the display node
    if display_node is not None:
        mat_sop.setInput(0, display_node)

    # Set the material path
    mat_parm = mat_sop.parm('shop_materialpath1')
    if mat_parm is not None:
        mat_parm.set(material_path)

    # Set display flag on the new material SOP
    mat_sop.setDisplayFlag(True)
    mat_sop.setRenderFlag(True)
    config.place_new_node(mat_sop)
    ui.focus_network_editor(mat_sop)

    return {
        'material_sop_path': mat_sop.path(),
    }


@register_command(PluginCommand.MATERIALS_LIST_MATERIAL_TYPES)
def _list_material_types(
    *,
    filter: str | None = None,
    **_: Any,
) -> dict[str, Any]:
    """List available VOP/material node types."""

    results: list[dict[str, str]] = []

    categories_to_search = ['Vop', 'Shop']
    all_categories = hou.nodeTypeCategories()

    for cat_name in categories_to_search:
        category = all_categories.get(cat_name)
        if category is None:
            continue

        types_dict = category.nodeTypes()
        for type_name, node_type in sorted(types_dict.items()):
            # Skip hidden types
            try:
                if node_type.hidden():
                    continue
            except Exception:
                pass

            label = node_type.description()

            # Apply filter if provided
            filter_lower = error_helpers.as_text(filter, 'filter').lower()
            if filter_lower and (
                filter_lower not in type_name.lower()
                and filter_lower not in label.lower()
            ):
                continue

            results.append({'name': type_name, 'label': label, 'category': cat_name})

    # Unfiltered this was every VOP and SHOP type, 76 KB. The first 200, and
    # the count; a filter is the way to the rest.
    shown = results[:_TYPE_LIST_CAP]
    return {
        'count': len(results),
        'truncated': len(results) > len(shown),
        'types': shown,
    }


_TYPE_LIST_CAP = 200
