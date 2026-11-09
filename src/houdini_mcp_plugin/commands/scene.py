from __future__ import annotations

from typing import Any

import hou

from houdini_mcp_plugin.dispatcher import register_command
from houdini_mcp_protocol import PluginCommand


@register_command(PluginCommand.SCENE_GET_SCENE_INFO)
def get_scene_info() -> dict[str, Any]:
    """Return basic information about the current Houdini scene."""

    start, end = hou.playbar.frameRange()
    return {
        'path': hou.hipFile.path(),
        'frame': hou.frame(),
        'fps': hou.fps(),
        'frame_range': [start, end],
        'houdini_version': hou.applicationVersionString(),
    }


@register_command(PluginCommand.SCENE_GET_SELECTION)
def get_selection() -> dict[str, Any]:
    """Return the nodes selected in the current session."""

    return {'nodes': [_node_summary(node) for node in hou.selectedNodes()]}


@register_command(PluginCommand.SCENE_GET_NODE)
def get_node(path: str = '/') -> dict[str, Any]:
    """Return details for a node path."""

    node_path = path or '/'
    if not node_path.startswith('/'):
        node_path = f'/{node_path}'
    node = hou.node(node_path)
    if node is None:
        raise ValueError(f'node not found: {node_path}')

    node_type = node.type()
    parent = node.parent()
    return {
        'path': node.path(),
        'name': node.name(),
        'type': node_type.name(),
        'category': node_type.category().name(),
        'type_description': node_type.description(),
        'parent': parent.path() if parent is not None else None,
        'children': [_node_summary(child) for child in node.children()],
        'inputs': [
            _connection_summary(connection) for connection in node.inputConnections()
        ],
        'errors': list(node.errors()),
        'warnings': list(node.warnings()),
        'is_displayed': _flag(node, 'isDisplayFlagSet'),
        'is_bypassed': _flag(node, 'isBypassed'),
        'is_locked': _flag(node, 'isLocked'),
    }


def _node_summary(node: hou.Node) -> dict[str, Any]:
    node_type = node.type()
    return {
        'path': node.path(),
        'name': node.name(),
        'type': node_type.name(),
        'category': node_type.category().name(),
    }


def _connection_summary(connection: hou.NodeConnection) -> dict[str, Any]:
    input_node = connection.inputNode()
    return {
        'path': input_node.path() if input_node is not None else None,
        'input_index': connection.inputIndex(),
        'output_index': connection.outputIndex(),
    }


def _flag(node: hou.Node, name: str) -> bool | None:
    try:
        return bool(getattr(node, name)())
    except (AttributeError, hou.Error):
        return None
