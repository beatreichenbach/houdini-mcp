from __future__ import annotations

import contextlib
from typing import Any

import hou

_VALUELESS_PARM_TYPES = frozenset(
    {'Button', 'Folder', 'FolderSet', 'Separator', 'Label'}
)


def _version_key(version: Any) -> tuple:
    """Sort key that orders 1.2 before 1.10 and puts an unversioned first."""

    if not version:
        return (0, ())
    parts = []
    for piece in str(version).split('.'):
        parts.append((0, int(piece)) if piece.isdigit() else (1, piece))
    return (1, tuple(parts))


def _resolve_node_type(
    category: hou.NodeTypeCategory,
    type_name: str,
) -> hou.NodeType | None:
    """Resolve a type name in a category the way createNode would."""

    with contextlib.suppress(Exception):
        preferred = hou.preferredNodeType(f'{category.name()}/{type_name}')
        if preferred is not None:
            return preferred
    types = category.nodeTypes()
    if type_name in types:
        return types[type_name]
    prefix = type_name + '::'
    versioned = [key for key in types if key.startswith(prefix)]
    if versioned:
        return types[max(versioned, key=lambda key: _version_key(key[len(prefix) :]))]
    return None


def _menu_pairs(spec: dict) -> tuple:
    """Normalise menu_items into (values, labels)."""

    items = spec.get('menu_items')
    if not items:
        raise ValueError(f'Menu parameter {spec.get("name")!r} needs menu_items.')
    if isinstance(items, str):
        raise ValueError(
            f'menu_items on {spec.get("name")!r} must be a list, e.g. '
            f'["low", "high"] or [["low", "Low"], ["high", "High"]], not {items!r}.'
        )
    values, labels = [], []
    for item in items:
        if isinstance(item, (list, tuple)):
            if len(item) != 2:
                raise ValueError(
                    f'Menu item {item!r} on {spec.get("name")!r} must be '
                    f'[value, label] or a plain string.'
                )
            values.append(str(item[0]))
            labels.append(str(item[1]))
        else:
            values.append(str(item))
            labels.append(str(item))
    return tuple(values), tuple(labels)


def _menu_default(spec: dict, values: tuple) -> int:
    """A menu's default as an index, checked against its items either way."""

    default = spec.get('default', 0)
    if isinstance(default, str):
        if default not in values:
            raise ValueError(
                f'Default {default!r} of menu {spec.get("name")!r} is not one of its '
                f'items {list(values)}.'
            )
        return values.index(default)
    index = int(default)
    if not 0 <= index < len(values):
        raise ValueError(
            f'Default {index} of menu {spec.get("name")!r} is out of range: it has '
            f'{len(values)} item(s), 0-{len(values) - 1}.'
        )
    return index
