from __future__ import annotations

import contextlib
import os
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


def _layer_summary(layer: Any) -> dict:
    """Return resolution, channels, and value ranges for a COP layer."""

    summary: dict = {'available': True}
    with contextlib.suppress(Exception):
        summary['resolution'] = list(layer.bufferResolution())
    with contextlib.suppress(Exception):
        summary['storage'] = str(layer.storageType()).rsplit('.', 1)[-1]
    with contextlib.suppress(Exception):
        summary['is_constant'] = bool(layer.isConstant())
    channels = 0
    with contextlib.suppress(Exception):
        channels = int(layer.channelCount())
    summary['channels'] = channels
    ranges = []
    for channel in range(min(channels, 4)):
        with contextlib.suppress(Exception):
            ranges.append(
                {
                    'min': layer.computeMin(channel),
                    'max': layer.computeMax(channel),
                    'mean': layer.computeAverage(channel),
                }
            )
    if ranges:
        summary['channel_ranges'] = ranges
    return summary


def _track_entry(track: Any) -> dict[str, Any]:
    """Return name, sample count, rate, and value range for a CHOP track."""

    samples = track.allSamples()
    return {
        'name': track.name(),
        'length': track.numSamples(),
        'rate': track.clip().sampleRate(),
        'min': min(samples) if samples else 0.0,
        'max': max(samples) if samples else 0.0,
    }


def _find_flipbook_output(output_path: str, frame: float) -> str:
    """Find the actual flipbook output after Houdini inserts a frame number."""

    if os.path.isfile(output_path):
        return output_path

    base, ext = os.path.splitext(output_path)
    frame_int = int(frame)
    candidates = [
        f'{base}.{frame_int:04d}{ext}',
        f'{base}.{frame_int:03d}{ext}',
        f'{base}.{frame_int}{ext}',
        f'{base}_{frame_int:04d}{ext}',
    ]
    for candidate in candidates:
        if os.path.isfile(candidate):
            try:
                os.rename(candidate, output_path)
                return output_path
            except OSError:
                return candidate

    return output_path


def _size_flipbook(settings: Any, resolution: list | None) -> None:
    """Size a flipbook from the viewport unless an explicit resolution is given."""

    if resolution is not None:
        settings.useResolution(True)
        settings.resolution(tuple(resolution))
    else:
        settings.useResolution(False)
    settings.outputZoom(100)


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
