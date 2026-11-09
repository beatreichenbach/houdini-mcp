"""Takes handlers for Houdini MCP."""

from __future__ import annotations

from typing import Any

import hou

from houdini_mcp_protocol import PluginCommand

from ..dispatcher import register_command


@register_command(PluginCommand.TAKES_LIST_TAKES)
def _list_takes(**_: Any) -> dict[str, Any]:
    """List all takes in the scene with their hierarchy."""

    current_take = hou.takes.currentTake()
    current_name = current_take.name() if current_take else None

    takes_list: list[dict[str, Any]] = []
    for take in hou.takes.takes():
        parent = take.parent()
        parent_name = parent.name() if parent else None
        children = take.children()

        takes_list.append(
            {
                'name': take.name(),
                'is_current': take.name() == current_name,
                'parent': parent_name,
                'children': [c.name() for c in children],
            }
        )

    return {
        'count': len(takes_list),
        'takes': takes_list,
        'current_take': current_name,
    }


@register_command(PluginCommand.TAKES_GET_CURRENT_TAKE)
def _get_current_take(**_: Any) -> dict[str, Any]:
    """Get the current take and list its overridden parameters."""

    current_take = hou.takes.currentTake()
    if current_take is None:
        return {
            'name': None,
            'overridden_parms': [],
        }

    take_name = current_take.name()

    # Collect overridden parameters
    overridden_parms: list[dict[str, Any]] = []
    for parm_tuple in current_take.parmTuples():
        node = parm_tuple.node()
        for parm in parm_tuple:
            try:
                val = parm.eval()
            except Exception:
                val = None
            overridden_parms.append(
                {
                    'node_path': node.path(),
                    'parm_name': parm.name(),
                    'value': val,
                }
            )

    return {
        'name': take_name,
        'overridden_parms': overridden_parms,
    }


@register_command(PluginCommand.TAKES_SET_CURRENT_TAKE)
def _set_current_take(*, name: str, **_: Any) -> dict[str, Any]:
    """Set the current take by name."""

    target_take = None
    for take in hou.takes.takes():
        if take.name() == name:
            target_take = take
            break

    if target_take is None:
        available = [t.name() for t in hou.takes.takes()]
        raise ValueError(f"Take not found: '{name}'. Available takes: {available}")

    hou.takes.setCurrentTake(target_take)

    return {
        'name': name,
        'success': True,
    }


@register_command(PluginCommand.TAKES_CREATE_TAKE)
def _create_take(
    *,
    name: str,
    parent_name: str | None = None,
    **_: Any,
) -> dict[str, Any]:
    """Create a new take, optionally as a child of an existing take."""

    if parent_name is not None:
        # Find and set the parent take as current first
        parent_take = None
        for take in hou.takes.takes():
            if take.name() == parent_name:
                parent_take = take
                break

        if parent_take is None:
            available = [t.name() for t in hou.takes.takes()]
            raise ValueError(
                f"Parent take not found: '{parent_name}'. Available takes: {available}"
            )

        hou.takes.setCurrentTake(parent_take)

    # Create the new take (it becomes a child of the current take)
    new_take = hou.takes.currentTake().addChildTake(name)
    hou.takes.setCurrentTake(new_take)

    actual_parent = new_take.parent()
    actual_parent_name = actual_parent.name() if actual_parent else None

    return {
        'name': new_take.name(),
        'parent': actual_parent_name,
    }
