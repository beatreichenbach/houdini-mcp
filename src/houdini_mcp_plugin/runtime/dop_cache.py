from __future__ import annotations

import contextlib
from typing import Any

import hou

_MAX_DEPTH = 64
_DOWNSTREAM_LIMIT = 500
_DOP_CACHE_NOTE = (
    'Frames this simulation cooked before this edit may still hold the old result: '
    'an edit inside a DOP network, or upstream of a simulation, does not reset its '
    'cache. Call reset_simulation(node_path=<network>) before reading such a frame. '
    'Leave the memory cache (cacheenabled) on: it is what keeps the cooked frames, '
    'and turning it off is not the fix.'
)


def dop_cache_note(nodes: Any, rewired: bool = False) -> dict[str, Any] | None:
    """Return simulations left stale by editing nodes, or None."""

    networks: list[str] = []

    def add(owner: hou.Node | None) -> None:
        if owner is not None and owner.path() not in networks:
            networks.append(owner.path())

    for node in nodes or ():
        with contextlib.suppress(Exception):
            if _inside_dop(node):
                add(_simulation_to_reset(node))
                continue
            if rewired and node.parm('resimulate') is not None:
                add(_simulation_to_reset(node))
            for reader in _downstream(node):
                if _inside_dop(reader) or reader.parm('resimulate') is not None:
                    add(_simulation_to_reset(reader))
    if not networks:
        return None
    return {'networks': networks, 'note': _DOP_CACHE_NOTE}


def _reset_button_owner(node: hou.Node) -> hou.Node | None:
    owner = node
    while owner is not None and owner.parm('resimulate') is None:
        owner = owner.parent()
    return owner


def _inside_dop(node: hou.Node) -> bool:
    for _ in range(_MAX_DEPTH):
        if node is None:
            return False
        if node.type().category() == hou.dopNodeTypeCategory():
            return True
        node = node.parent()
    return False


def _simulation_to_reset(node: hou.Node) -> hou.Node | None:
    owner = _reset_button_owner(node)
    for _ in range(_MAX_DEPTH):
        buried = False
        with contextlib.suppress(Exception):
            buried = owner is not None and owner.isInsideLockedHDA() is True
        if not buried:
            break
        lifted = _reset_button_owner(owner.parent())
        if lifted is None:
            break
        owner = lifted
    return owner


def _downstream(node: hou.Node) -> list[hou.Node]:
    seen = {node.path()}
    queue, found = [node], []
    while queue and len(seen) < _DOWNSTREAM_LIMIT:
        current = queue.pop(0)
        inside = current.path() + '/'
        neighbours: list = []
        with contextlib.suppress(Exception):
            neighbours = list(current.outputs()) + list(current.dependents())
        with contextlib.suppress(Exception):
            parent = current.parent()
            if not neighbours and (
                current.type().name() == 'output' or parent.displayNode() == current
            ):
                neighbours.append(parent)
        for other in neighbours:
            path = other.path()
            if path in seen or path.startswith(inside):
                continue
            seen.add(path)
            found.append(other)
            if not _inside_dop(other):
                queue.append(other)
    return found
