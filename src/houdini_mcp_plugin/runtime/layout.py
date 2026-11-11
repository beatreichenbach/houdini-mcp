"""
Block placement for new or copied nodes.

The rest of the runtime places a node at a time
(:func:`config.place_new_node`). A copied branch needs the other half: move
the whole set, keeping the relative layout the template gave it, into free
space beside whatever is already in the network.

Deliberately not a re-layout: nothing outside *nodes* moves.
"""

from __future__ import annotations

import contextlib

import hou

from . import config


def items_bbox(items: list) -> tuple[float, float, float, float] | None:
    """
    Return ``(min_x, min_y, max_x, max_y)`` covering *items*, or ``None``.

    Nodes and network boxes both report a top-left ``position()`` and a
    ``size()``, so the box has to include the size: the gap between a new
    block and an existing node is measured from the node's right edge, not
    from its corner. Items that report neither are skipped rather than
    faulting the layout.
    """

    xs: list[float] = []
    ys: list[float] = []
    for item in items:
        with contextlib.suppress(Exception):
            position = item.position()
            size = item.size()
            xs.extend((position[0], position[0] + size[0]))
            ys.extend((position[1] - size[1], position[1]))
    if not xs:
        return None
    return min(xs), min(ys), max(xs), max(ys)


def place_nodes_block(nodes: list, margin: list[float] | None = None) -> dict:
    """
    Move *nodes* as one block into free space beside the rest of their network.

    The block keeps its internal layout and is placed to the right of the
    existing items, top-aligned with them. Nodes in different parents are
    placed per parent, because "beside" only means something inside one
    network. An empty network leaves the nodes where creation put them.

    Placement is cosmetic, so a failure never reaches the caller. Every moved
    node is tagged as placed, which is what keeps the creation floor from
    nudging it again later.
    """

    if not nodes:
        return {'success': True, 'placed': False, 'blocks': [], 'node_count': 0}

    margin_x, margin_y = margin if margin is not None else (1.0, 0.0)

    blocks: dict[hou.Node, list] = {}
    for node in nodes:
        parent = node.parent()
        if parent is not None:
            blocks.setdefault(parent, []).append(node)

    results = []
    for parent, block in blocks.items():
        existing = [item for item in parent.allItems() if item not in block]
        existing_box = items_bbox(existing)
        block_box = items_bbox(block)

        if existing_box is None or block_box is None:
            results.append({'parent': parent.path(), 'placed': False})
            continue

        offset = hou.Vector2(
            existing_box[2] + margin_x - block_box[0],
            existing_box[3] + margin_y - block_box[3],
        )
        with contextlib.suppress(Exception), hou.undos.group('Layout nodes'):
            for node in block:
                node.move(offset)
        for node in block:
            config.mark_placed(node)

        results.append(
            {
                'parent': parent.path(),
                'placed': True,
                'node_count': len(block),
                'offset': [offset[0], offset[1]],
            }
        )

    return {
        'success': True,
        'placed': any(block['placed'] for block in results),
        'blocks': results,
        'node_count': len(nodes),
    }
