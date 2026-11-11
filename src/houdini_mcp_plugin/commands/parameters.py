"""Houdini-side handlers for parameter operations."""

from __future__ import annotations

import contextlib
import os
import re
from difflib import get_close_matches
from typing import Any, cast

import hou

from houdini_mcp_protocol import PluginCommand

from ..host import register_command
from ..runtime import callbacks as callback_helpers
from ..runtime import dop_cache
from ..runtime import errors as error_helpers
from ..runtime import menus as menu_helpers
from ..serialize import geometry_summary, ramp_to_dict


def _resolve_node(node_path: str) -> hou.Node:
    """Return the hou.Node at *node_path* or raise."""

    node = hou.node(node_path)
    if node is None:
        raise ValueError(f'Node not found: {node_path}')
    return node


def _available_parm_names(node: hou.Node) -> list[str]:
    """Return sorted list of parameter names on a node."""

    return sorted(p.name() for p in node.parms())


def _squash(text: str) -> str:
    return re.sub(r'[^a-z0-9]', '', text.lower())


def suggest_parms(wanted: str, labels: dict[str, str], n: int = 3) -> list[str]:
    """Parm names a mistyped *wanted* most likely meant; *labels* maps name -> label."""

    by_label: dict[str, list[str]] = {}
    for name, label in labels.items():
        by_label.setdefault(_squash(label), []).append(name)
    found = [
        name
        for label in get_close_matches(_squash(wanted), list(by_label), n=n, cutoff=0.8)
        for name in by_label[label]
    ]
    found += get_close_matches(wanted, sorted(labels), n=n, cutoff=0.5)
    return list(dict.fromkeys(found))[: n + 1]


def _wrapped_expression(value: Any) -> tuple[str, Any] | None:
    """(expression, hou.exprLanguage) of an ``{"expr": ..., "language": ...}`` value."""

    if not isinstance(value, dict):
        return None
    unknown = sorted(set(value) - {'expr', 'language'})
    if 'expr' not in value or unknown:
        raise ValueError(
            f'an expression is written '
            f'{{"expr": ..., "language": "hscript" | "python"}}, '
            f'got {value!r}'
        )
    language = str(value.get('language', 'hscript')).strip().lower()
    if language not in ('hscript', 'python'):
        raise ValueError(
            f"expression language must be 'hscript' or 'python', got {language!r}"
        )
    python = language == 'python'
    return str(
        value['expr']
    ), hou.exprLanguage.Python if python else hou.exprLanguage.Hscript


def set_whole_expression(parm: hou.Parm, expression: str, language: Any = None) -> int:
    """Make *expression* drive *parm* on every frame; returns keys replaced."""

    replaced = len(parm.keyframes())
    if replaced > 1:
        parm.deleteAllKeyframes()
    if language is None:
        parm.setExpression(expression)
    else:
        parm.setExpression(expression, language)
    return replaced if replaced > 1 else 0


def parm_labels(node: hou.Node) -> dict[str, str]:
    """Name -> label for every parm on a live node, multiparm instances included."""

    return {p.name(): p.description() for p in node.parms()}


def template_labels(templates: Any) -> dict[str, str]:
    """Name -> label for a node type's parm templates, folders walked."""

    labels: dict[str, str] = {}
    for template in templates:
        if template.type() == hou.parmTemplateType.Folder:
            labels.update(template_labels(template.parmTemplates()))
        elif template.type() != hou.parmTemplateType.FolderSet:
            labels[template.name()] = template.label()
    return labels


def _resolve_parm(node_path: str, parm_name: str) -> hou.Parm:
    """Return the hou.Parm on *node_path* named *parm_name* or raise."""

    node = _resolve_node(node_path)
    parm = node.parm(parm_name)
    if parm is None:
        # No full name list: on a Pyro Solver it was 14.5 KB, sent on every
        # guessed name, the most common mistake there is.
        close = suggest_parms(parm_name, parm_labels(node))
        hint = f' Did you mean: {close}?' if close else ''
        raise ValueError(
            f"Parameter '{parm_name}' not found on node '{node_path}'.{hint} "
            f'get_node_card(node_type, parm_filter=...) lists the real names.'
        )
    return parm


def _parm_type_name(parm_template: hou.ParmTemplate) -> str:
    """Return a human-readable type string for a parameter template."""

    return parm_template.type().name()


# What a whole ramp is written as: the shape serialize.ramp_to_dict reads it
# back in, so a ramp read from one parm can be written to another as it is.
_RAMP_KEYS = frozenset({'keys', 'values', 'basis', 'is_color', 'type'})


def is_ramp_value(value: Any) -> bool:
    """Whether *value* is a whole ramp: ``{"keys": [...], "values": [...],..."""

    return (
        isinstance(value, dict)
        and 'keys' in value
        and 'values' in value
        and not set(value) - _RAMP_KEYS
    )


def _ramp_basis(name: Any) -> Any:
    """hou.rampBasis for a name such as "linear" or "CatmullRom", in any case."""

    wanted = str(name).replace('-', '').replace('_', '').lower()
    known = sorted(
        a for a in dir(hou.rampBasis) if not a.startswith('_') and a[0].isupper()
    )
    for attr in known:
        if attr.lower() == wanted:
            return getattr(hou.rampBasis, attr)
    raise ValueError(f'unknown ramp basis {name!r}; known: {known}')


def ramp_shape_error(value: dict) -> str | None:
    """What is wrong with a ramp value whatever parm it goes to, or None."""

    try:
        keys = [float(k) for k in value['keys']]
        values = list(value['values'])
    except (TypeError, ValueError):
        return "a ramp's keys are numbers and its values a list"
    if len(keys) != len(values):
        return f'a ramp needs one value per key: {len(keys)} keys, {len(values)} values'
    basis = value.get('basis', 'linear')
    names = list(basis) if isinstance(basis, (list, tuple)) else [basis] * len(keys)
    if len(names) != len(keys):
        return (
            f'a ramp takes one basis or one per key: {len(keys)} keys, '
            f'{len(names)} bases'
        )
    try:
        for name in names:
            _ramp_basis(name)
    except ValueError as exc:
        return str(exc)
    return None


def ramp_from_value(parm: hou.Parm, value: dict) -> hou.Ramp:
    """The hou.Ramp a ``{"keys", "values", "basis"}`` value describes, for *parm*."""

    template = parm.parmTemplate()
    if template.type() != hou.parmTemplateType.Ramp:
        raise ValueError(
            f"'{parm.name()}' is not a ramp parameter; a dict for it is an "
            f'expression, {{"expr": ...}}'
        )
    if problem := ramp_shape_error(value):
        raise ValueError(problem)
    keys = [float(k) for k in value['keys']]
    values = list(value['values'])
    if template.parmType() == hou.rampParmType.Color:
        try:
            values = [tuple(float(c) for c in v) for v in values]
        except TypeError:
            raise ValueError('a colour ramp takes [r, g, b] values') from None
        if any(len(v) != 3 for v in values):
            raise ValueError('a colour ramp takes [r, g, b] values')
    else:
        try:
            values = [float(v) for v in values]
        except TypeError:
            raise ValueError('a float ramp takes numbers as values') from None
    basis = value.get('basis', 'linear')
    names = list(basis) if isinstance(basis, (list, tuple)) else [basis] * len(keys)
    return hou.Ramp(tuple(_ramp_basis(n) for n in names), tuple(keys), tuple(values))


def _serialize_value(value: Any) -> Any:
    """Convert a value to a JSON-safe Python type."""

    if isinstance(value, hou.Vector2):
        return list(value)
    if isinstance(value, hou.Vector3):
        return list(value)
    if isinstance(value, hou.Vector4):
        return list(value)
    if isinstance(value, hou.Matrix3):
        return [list(row) for row in value.asTupleOfTuples()]
    if isinstance(value, hou.Matrix4):
        return [list(row) for row in value.asTupleOfTuples()]
    if isinstance(value, hou.Ramp):
        # Data, in the shape a ramp is written in; its repr was all a caller got.
        return ramp_to_dict(value)
    if isinstance(value, (list, tuple)):
        return [_serialize_value(v) for v in value]
    return value


def _data_parm_summary(parm: hou.Parm, pt: hou.ParmTemplate) -> dict[str, Any]:
    """What a Data parameter holds, never the blob itself."""

    summary: dict[str, Any] = {'is_set': False}
    with contextlib.suppress(Exception):
        summary['data_parm_type'] = pt.dataParmType().name()
    value = None
    with contextlib.suppress(Exception):
        value = parm.eval()
    if isinstance(value, hou.Geometry):
        # Set, possibly to an empty geometry: the counts say which.
        summary['is_set'] = True
        summary['geometry'] = geometry_summary(value)
    elif isinstance(value, dict):
        # A KeyValueDictionary evaluates to {} when empty.
        summary['is_set'] = bool(value)
        summary['key_count'] = len(value)
    elif value is not None:
        summary['is_set'] = True
        summary['value_type'] = type(value).__name__
    return summary


def _data_parm_value(parm: hou.Parm, pt: hou.ParmTemplate) -> dict[str, Any] | None:
    """For a Data parameter, the fields a reader reports; None for any other."""

    if _parm_type_name(pt) != 'Data':
        return None
    data = _data_parm_summary(parm, pt)
    value = data.get('geometry')
    if 'key_count' in data:
        # A KeyValueDictionary always answered with the dictionary itself.
        with contextlib.suppress(Exception):
            value = _serialize_value(parm.eval())
    return {'value': value, 'data': data}


def _template_to_dict(pt: hou.ParmTemplate) -> dict[str, Any]:
    """Convert a ParmTemplate to a JSON-serialisable dictionary."""

    info: dict[str, Any] = {
        'name': pt.name(),
        'label': pt.label(),
        'type': _parm_type_name(pt),
        'num_components': pt.numComponents(),
        'is_hidden': pt.isHidden(),
    }

    # Default value
    try:
        info['default_value'] = list(pt.defaultValue())
    except Exception:
        try:
            info['default_value'] = pt.defaultValue()
        except Exception:
            info['default_value'] = None

    # Range
    try:
        info['min'] = pt.minValue()
        info['max'] = pt.maxValue()
        info['min_is_strict'] = pt.minIsStrict()
        info['max_is_strict'] = pt.maxIsStrict()
    except Exception:
        pass

    # Menu items — capped at 50 to avoid enormous enum lists
    try:
        items = pt.menuItems()
        labels = pt.menuLabels()
        if items:
            info['menu_items'] = list(items)[:50]
            info['menu_labels'] = list(labels)[:50]
            if len(items) > 50:
                info['menu_items_truncated'] = True
    except Exception:
        pass

    # Naming scheme (for multi-component parms)
    with contextlib.suppress(Exception):
        info['naming_scheme'] = pt.namingScheme().name()

    # Conditionals and tags omitted — internal Houdini UI metadata,
    # not useful for LLM-driven parameter setting.

    return info


@register_command(PluginCommand.PARAMETERS_GET_PARAMETER)
def _get_parameter(node_path: str, parm_name: str, **_: Any) -> dict[str, Any]:
    """Get the current value, expression, keyframe info, and metadata of a parameter."""

    parm = _resolve_parm(node_path, parm_name)
    pt = parm.parmTemplate()

    data_parm = _data_parm_value(parm, pt)
    result: dict[str, Any] = {
        'node_path': node_path,
        'parm_name': parm_name,
        'value': data_parm['value'] if data_parm else _serialize_value(parm.eval()),
        'raw_value': _serialize_value(parm.rawValue()),
        'parm_type': _parm_type_name(pt),
        'is_locked': parm.isLocked(),
        'is_at_default': not _off_default(parm),
    }
    if data_parm:
        result['data'] = data_parm['data']

    # Expression
    try:
        result['expression'] = parm.expression()
        result['expression_language'] = parm.expressionLanguage().name()
    except hou.OperationFailed:
        result['expression'] = None
        result['expression_language'] = None

    # Keyframes
    keyframes = parm.keyframes()
    result['keyframe_count'] = len(keyframes)

    return result


class LockedParmError(ValueError):
    """A write refused because the parm is locked by its node's interface."""


def _is_locked(parm: hou.Parm) -> bool:
    # HOM answers a real bool; anything else (a stand-in) is not a lock.
    with contextlib.suppress(Exception):
        return parm.isLocked() is True
    return False


def _words(text: str) -> list[str]:
    """*text* split into lowercase words, camelCase and snake_case alike."""

    return [w.lower() for w in re.findall(r'[A-Z]+(?![a-z])|[A-Z]?[a-z]+|[0-9]+', text)]


def _names_word(text: str, name: str) -> bool:
    """Whether *name* is a whole word (or a run of words) of *text*."""

    wanted = _words(name)
    found = _words(text)
    size = len(wanted)
    return bool(wanted) and any(
        found[i : i + size] == wanted for i in range(len(found) - size + 1)
    )


def locked_controllers(parm: hou.Parm) -> list[dict[str, Any]]:
    """Menu and toggle parms on *parm*'s node whose Python callback names its tuple."""

    try:
        node = parm.node()
        tuple_name = parm.tuple().name().lower()
    except Exception:
        return []
    found: list[dict[str, Any]] = []
    for other in node.parms():
        if other.name() == parm.name():
            continue
        callback = callback_helpers.callback_script(other)
        if not callback or not _names_word(callback, tuple_name):
            continue
        with contextlib.suppress(Exception):
            template = other.parmTemplate()
            # A lock is set and cleared through HOM (parm.lock), i.e. from a
            # Python callback; an HScript preset button (resolutionMenu) that
            # merely names the tuple does not control it.
            if template.scriptCallbackLanguage() != hou.scriptLanguage.Python:
                continue
            # A menu of any template type -- res_mode is a String parm with a
            # Normal menu, not a Menu parm (measured on 22.0.429) -- or a toggle.
            menu: list[str] = []
            with contextlib.suppress(Exception):
                menu = menu_helpers.items(other)
            if not menu and template.type() != hou.parmTemplateType.Toggle:
                continue
            entry: dict[str, Any] = {
                'parm': other.name(),
                'value': other.evalAsString(),
            }
            if menu:
                entry['menu'] = menu
            found.append(entry)
    return found


def locked_message(parm: hou.Parm) -> str | None:
    """Why *parm* cannot be written because it is locked, or None."""

    if not _is_locked(parm):
        return None
    message = (
        f"'{parm.name()}' on {parm.node().path()} is locked by the node's interface "
        f'(Parm.isLocked() is true): no value, expression or revert can be written '
        f'to it, and override_expression / revert_parameter do not help.'
    )
    controllers = locked_controllers(parm)
    if controllers:
        named = ', '.join(
            f'{c["parm"]} (now {c["value"]!r}'
            + (f', menu {c["menu"]}' if c.get('menu') else '')
            + ')'
            for c in controllers
        )
        message += (
            f' The lock is set by the callback of {named}. Set that parm with '
            f'run_callbacks=true first -- a plain write does not run callbacks, the '
            f"UI does -- then write '{parm.name()}'."
        )
    else:
        message += (
            " Something in the node's interface sets the lock; see "
            'get_parm_template_tree.'
        )
    return message


def _run_callback(parm: hou.Parm) -> dict[str, Any] | None:
    """Run *parm*'s callback script the way the UI does after an edit."""

    if not callback_helpers.callback_script(parm):
        return None
    try:
        route = callback_helpers.press(parm)
    except callback_helpers.CallbackError as exc:
        return {'run': False, 'route': 'python', 'error': str(exc).splitlines()[0]}
    except Exception as exc:
        # The Hscript route goes through pressButton(), which raises
        # hou.OperationFailed ("callback script could not be run") -- after
        # set() already wrote the value, so the write itself stands. Anything
        # else unexpected lands here too, so the route is read, not assumed.
        route = 'python' if callback_helpers._is_python(parm) else 'hscript'
        return {
            'run': False,
            'route': route,
            'error': error_helpers.readable_message(exc),
        }
    return {'run': True, 'route': route}


def _callback_report(outcome: dict[str, Any] | None) -> dict[str, Any]:
    """Reply keys for a callback outcome: callback_run, and why not."""

    if outcome is None:
        return {}
    report: dict[str, Any] = {'callback_run': outcome['run']}
    if 'error' in outcome:
        report['callback_error'] = outcome['error']
    return report


def _expression_driven(parms: list[hou.Parm]) -> str | None:
    """A sentence naming the first of *parms* driven by an expression, or None."""

    for parm in parms:
        locked = locked_message(parm)
        if locked:
            return locked
    for parm in parms:
        try:
            expression = parm.expression()
        except hou.OperationFailed:
            continue
        return (
            f"'{parm.name()}' on {parm.node().path()} is driven by the expression "
            f'{expression!r}, so it cannot be set directly. Set the parameter that '
            f'controls it, or remove the expression with revert_parameter first.'
        )
    return None


# Keys of an animation curve: bezier(), linear(), constant(), cubic(), ...
_CURVE_FUNCTION = re.compile(r'[A-Za-z]+\(\)')


def _expression_of(parm: hou.Parm) -> str | None:
    """The expression *parm* holds, or None when it holds a plain value."""

    try:
        expression = parm.expression()
    except Exception:
        # hou.Parm.expression() wants exactly one key. Writing a literal to a
        # parm whose expression sits on another frame (a File Cache's $FEND,
        # written at frame 6) adds a second key with the same expression and
        # changes nothing, and after that the expression could no longer be
        # seen: the write neither landed nor was reported. Keys that all carry
        # one plain expression are that same expression; animation curves are
        # not, and stay "no expression" as before.
        with contextlib.suppress(Exception):
            texts = {key.expression() for key in parm.keyframes()}
            if len(texts) == 1 and not _CURVE_FUNCTION.fullmatch(next(iter(texts))):
                expression = next(iter(texts))
                return expression or None
        return None
    return expression if isinstance(expression, str) and expression else None


def _expression_error(parm: hou.Parm) -> str | None:
    """The error *parm*'s expression gives when evaluated, or None."""

    suffix = f'{parm.path()})'
    node = parm.node()

    def current() -> str | None:
        with contextlib.suppress(Exception):
            parm.eval()
        with contextlib.suppress(Exception):
            for message in (*node.errors(), *node.warnings()):
                if suffix in message:
                    return message.strip()
        return None

    if current() is None:
        return None
    with contextlib.suppress(Exception):
        node.cook(force=True)
    return current()


def _clear_expression(parm: hou.Parm) -> None:
    """Remove *parm*'s expression without evaluating it."""

    with contextlib.suppress(Exception):
        parm.setExpression('0', hou.exprLanguage.Hscript, replace_expression=True)
    with contextlib.suppress(Exception):
        parm.deleteAllKeyframes()


def _values_match(requested: Any, actual: Any) -> bool:
    """Whether a write of *requested* is what *actual* now reads back as."""

    if isinstance(requested, bool) or isinstance(actual, bool):
        return bool(requested) == bool(actual)
    if isinstance(requested, (int, float)) and isinstance(actual, (int, float)):
        return abs(float(requested) - float(actual)) <= 1e-6 * max(
            1.0, abs(float(actual))
        )
    return requested == actual


def _referenced_parm(parm: hou.Parm) -> str | None:
    """Path of the parm a pure `ch()` reference points at, or None."""

    with contextlib.suppress(Exception):
        target = parm.getReferencedParm()
        if target is not None and target.path() != parm.path():
            return str(target.path())
    return None


_WRITTEN_THROUGH_NOTE = (
    'This parameter is a pure channel reference, so the value was written into '
    'the parameter it reads, not into this one. Break the link with '
    'revert_parameter, or set the source directly, if that was not intended.'
)

_EXPRESSION_KEPT_NOTE = (
    'The parameter still holds its expression, so the literal did not take. '
    'Set the parameter that drives it, replace the expression with '
    'set_expression, or repeat this call with override_expression=true.'
)

_EXPRESSION_KEPT_SAME_VALUE_NOTE = (
    'The value asked for is what the expression evaluates to right now, but the '
    'expression is still there and will keep driving the parameter. '
    + _EXPRESSION_KEPT_NOTE.split('. ', 1)[1]
)


def _raw_string(parm: hou.Parm) -> str | None:
    """The unexpanded text of a String parm (`$JOB/geo/a_$F4.bgeo.sc`), or None."""

    with contextlib.suppress(Exception):
        if parm.parmTemplate().type() == hou.parmTemplateType.String:
            return parm.unexpandedString()
    return None


def _write_parm(
    parm: hou.Parm,
    value: Any,
    override_expression: bool = False,
    run_callbacks: bool = False,
) -> dict[str, Any]:
    """Set one parm and report honestly whether the write actually took."""

    locked = locked_message(parm)
    if locked:
        raise LockedParmError(locked)
    before = _expression_of(parm)
    through = _referenced_parm(parm) if before is not None else None
    if before is not None and override_expression:
        _clear_expression(parm)
        through = None
    parm.set(value)
    callback = _run_callback(parm) if run_callbacks else None
    after = _expression_of(parm)
    new_value = _serialize_value(parm.eval())
    info: dict[str, Any] = {'new_value': new_value}
    info.update(_callback_report(callback))
    raw = _raw_string(parm)
    # Only when it differs: "$HIP/geo" is worth seeing, "/geo/ball" twice is not.
    if raw is not None and raw != new_value:
        info['raw_value'] = raw
    matches = _values_match(value, new_value)
    if after is not None and through is not None and matches:
        # The value did land, in the parm this one reads.
        info['written_through'] = through
        info['expression'] = after
        info['note'] = _WRITTEN_THROUGH_NOTE
    elif after is not None:
        info['expression_kept'] = True
        info['expression'] = after
        info['requested'] = _serialize_value(value)
        if matches:
            info['same_as_evaluated'] = True
        info['note'] = (
            _EXPRESSION_KEPT_SAME_VALUE_NOTE if matches else _EXPRESSION_KEPT_NOTE
        )
    elif before is not None:
        info['expression_removed'] = before
    return info


def _write_ramp(
    parm: hou.Parm, value: dict, run_callbacks: bool = False
) -> dict[str, Any]:
    """Set a whole ramp; answer with what the parm holds afterwards."""

    if locked := locked_message(parm):
        raise LockedParmError(locked)
    try:
        parm.set(ramp_from_value(parm, value))
    except hou.PermissionError:
        reason = _expression_driven([parm])
        if reason:
            raise ValueError(reason) from None
        raise
    callback = _run_callback(parm) if run_callbacks else None
    return {'new_value': ramp_to_dict(parm.evalAsRamp()), **_callback_report(callback)}


def _set_tuple(
    node: hou.Node,
    parm_name: str,
    value: list | tuple,
    override_expression: bool = False,
    run_callbacks: bool = False,
) -> tuple[Any | None, dict[str, Any]]:
    """Apply a list value to the parm tuple of that name; None if there is none."""

    parm_tuple = node.parmTuple(parm_name)
    if parm_tuple is None:
        return None, {}
    if len(value) != len(parm_tuple):
        raise ValueError(
            f"Parameter '{parm_name}' on {node.path()} has "
            f'{len(parm_tuple)} components, got {len(value)} values.'
        )
    components = list(parm_tuple)
    # {"expr": ...} on a component sets that component's expression; the
    # others take their literal. It used to reach ParmTuple.set() and fail
    # with the raw SWIG overload list.
    wrapped = {
        index: found
        for index, component in enumerate(value)
        if (found := _wrapped_expression(component)) is not None
    }
    for parm in components:
        # Before any component is written: a tuple is one write.
        locked = locked_message(parm)
        if locked:
            raise LockedParmError(locked)
    through = {
        parm.name(): target
        for parm in components
        if _expression_of(parm) is not None
        and (target := _referenced_parm(parm)) is not None
    }
    if override_expression:
        for parm in components:
            if _expression_of(parm) is not None:
                _clear_expression(parm)
        through = {}
    try:
        if wrapped:
            for index, parm in enumerate(components):
                if index in wrapped:
                    set_whole_expression(parm, *wrapped[index])
                else:
                    parm.set(value[index])
        else:
            parm_tuple.set(value)
    except hou.PermissionError:
        # Not the components this call gave an expression: those took it.
        reason = _expression_driven(
            [p for i, p in enumerate(components) if i not in wrapped]
        )
        if reason:
            raise ValueError(reason) from None
        raise
    callback = _run_callback(components[0]) if run_callbacks else None
    new_value = [_serialize_value(p.eval()) for p in components]
    kept: list[dict[str, Any]] = []
    landed_elsewhere: dict[str, str] = {}
    for index, parm in enumerate(components):
        expression = _expression_of(parm)
        if expression is None or index in wrapped:
            continue
        matches = _values_match(value[index], new_value[index])
        if parm.name() in through and matches:
            landed_elsewhere[parm.name()] = through[parm.name()]
            continue
        # Kept whenever the expression survived, equal values or not.
        entry: dict[str, Any] = {
            'component': parm.name(),
            'index': index,
            'expression': expression,
            'requested': _serialize_value(value[index]),
        }
        if matches:
            entry['same_as_evaluated'] = True
        kept.append(entry)
    report: dict[str, Any] = _callback_report(callback)
    if wrapped:
        report['expressions_set'] = {
            components[index].name(): expression
            for index, (expression, _) in wrapped.items()
        }
    raw = [_raw_string(p) for p in components]
    if any(r is not None and r != v for r, v in zip(raw, new_value, strict=False)):
        report['raw_value'] = raw
    if kept:
        same = all(entry.get('same_as_evaluated') for entry in kept)
        report.update(
            {
                'expression_kept': True,
                'expression_components': kept,
                'requested': [_serialize_value(v) for v in value],
                'note': _EXPRESSION_KEPT_SAME_VALUE_NOTE
                if same
                else _EXPRESSION_KEPT_NOTE,
            }
        )
    if landed_elsewhere:
        report['written_through'] = landed_elsewhere
        report.setdefault('note', _WRITTEN_THROUGH_NOTE)
    return new_value, report


@register_command(PluginCommand.PARAMETERS_SET_PARAMETER)
def _set_parameter(
    node_path: str,
    parm_name: str,
    value: Any,
    override_expression: bool = False,
    run_callbacks: bool = False,
    **_: Any,
) -> dict[str, Any]:
    """Set a parameter value, auto-detecting the appropriate type."""

    if isinstance(value, (list, tuple)):
        new_value, report = _set_tuple(
            _resolve_node(node_path),
            parm_name,
            value,
            bool(override_expression),
            bool(run_callbacks),
        )
        if new_value is not None:
            result: dict[str, Any] = {
                'node_path': node_path,
                'parm_name': parm_name,
                'new_value': new_value,
            }
            result.update(report)
            if cache := dop_cache.dop_cache_note([_resolve_node(node_path)]):
                result['simulation_cache'] = cache
            return result

    parm = _resolve_parm(node_path, parm_name)

    try:
        written = _write_parm(
            parm, value, bool(override_expression), bool(run_callbacks)
        )
    except hou.PermissionError:
        reason = _expression_driven([parm])
        if reason:
            raise ValueError(reason) from None
        raise

    result = {'node_path': node_path, 'parm_name': parm_name}
    result.update(written)
    if cache := dop_cache.dop_cache_note([parm.node()]):
        result['simulation_cache'] = cache
    return result


def _error_entry(name: str, exc: Exception) -> dict[str, Any]:
    entry: dict[str, Any] = {'parm_name': name, 'error': str(exc)}
    if isinstance(exc, LockedParmError):
        entry['locked'] = True
    return entry


@register_command(PluginCommand.PARAMETERS_SET_PARAMETERS)
def _set_parameters(
    node_path: str,
    params: dict[str, Any],
    override_expression: bool = False,
    run_callbacks: bool = False,
    **_: Any,
) -> dict[str, Any]:
    """Batch-set multiple parameters on a single node, in the order given."""

    node = _resolve_node(node_path)
    override = bool(override_expression)
    callbacks = bool(run_callbacks)

    results: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for name, value in params.items():
        # {"expr": ..., "language": ...} is build_network's spelling for an
        # expression. Here it used to fall through to a literal write that
        # stored 0 and reported success, so the expression silently vanished.
        if isinstance(value, dict):
            parm = node.parm(name)
            if parm is not None and is_ramp_value(value):
                # A whole ramp at once; key by key through its multiparm
                # (`ramp`, `ramp1pos`, `ramp1c`, ...) was the only way in.
                try:
                    results.append(
                        {'parm_name': name, **_write_ramp(parm, value, callbacks)}
                    )
                except Exception as exc:
                    errors.append(_error_entry(name, exc))
                continue
            if 'expr' not in value or parm is None:
                problem = (
                    'no such parameter' if parm is None else 'a dict value needs "expr"'
                )
                errors.append({'parm_name': name, 'error': f'{problem}: {value!r}'})
                continue
            # Named as locked before the write, as every other branch here does.
            if locked := locked_message(parm):
                errors.append(_error_entry(name, LockedParmError(locked)))
                continue
            language = str(value.get('language', 'hscript')).lower()
            try:
                replaced = set_whole_expression(
                    parm,
                    str(value['expr']),
                    hou.exprLanguage.Python
                    if language == 'python'
                    else hou.exprLanguage.Hscript,
                )
            except Exception as exc:
                errors.append({'parm_name': name, 'error': str(exc)})
                continue
            entry = {'parm_name': name, 'expression': str(value['expr'])}
            if replaced:
                entry['replaced_keyframes'] = replaced
            if broken := broken_references(parm):
                entry['warning'] = '; '.join(broken)
            results.append(entry)
            continue
        # A list on a vector name sets the whole tuple, exactly as the single
        # setter does. The batch path used to know only per-component names,
        # which made "prefer set_parameters" and "set a light colour" collide.
        if isinstance(value, (list, tuple)):
            try:
                new_value, report = _set_tuple(node, name, value, override, callbacks)
            except Exception as exc:
                errors.append(_error_entry(name, exc))
                continue
            if new_value is not None:
                entry: dict[str, Any] = {'parm_name': name, 'new_value': new_value}
                entry.update(report)
                results.append(entry)
                continue
        parm = node.parm(name)
        if parm is None:
            close = suggest_parms(name, parm_labels(node))
            hint = f' Did you mean: {close}?' if close else ''
            errors.append(
                {'parm_name': name, 'error': f"Parameter '{name}' not found.{hint}"}
            )
            continue
        try:
            entry = {'parm_name': name}
            entry.update(_write_parm(parm, value, override, callbacks))
            results.append(entry)
        except Exception as exc:
            errors.append(_error_entry(name, exc))

    # A ramp written key by key (`ramp: 3`, `ramp3pos`, `ramp3c`) was echoed
    # straight after the count, when the new key still read t=0, black,
    # though the same call went on to set it. Ramps answer with what they
    # hold once the whole call is through.
    for entry in results:
        with contextlib.suppress(Exception):
            ramp_parm = node.parm(entry['parm_name'])
            if ramp_parm.parmTemplate().type() == hou.parmTemplateType.Ramp:
                entry['new_value'] = ramp_to_dict(ramp_parm.evalAsRamp())

    # A batch whose `errors` is empty while a parm kept its expression reads as
    # a clean success: name it at the top level too, so a caller that only
    # reads `errors` still sees that a write did not take, or landed elsewhere.
    kept = [entry['parm_name'] for entry in results if entry.get('expression_kept')]
    through = {
        entry['parm_name']: entry['written_through']
        for entry in results
        if entry.get('written_through')
    }
    reply: dict[str, Any] = {
        'node_path': node_path,
        'set': results,
        'errors': errors,
    }
    locked = [entry['parm_name'] for entry in errors if entry.get('locked')]
    if locked:
        reply['locked_parms'] = locked
    not_run = {
        entry['parm_name']: entry.get('callback_error')
        for entry in results
        if entry.get('callback_run') is False
    }
    if not_run:
        reply['callbacks_not_run'] = not_run
    warnings: list[str] = []
    if kept:
        reply['expressions_kept'] = kept
        warnings.append(
            f'{len(kept)} parameter(s) kept an expression and did not take the '
            f'value asked for: {kept}. {_EXPRESSION_KEPT_NOTE}'
        )
    if through:
        reply['written_through'] = through
        warnings.append(
            f'{len(through)} value(s) were written into the parameters these read '
            f'rather than into them: {through}. {_WRITTEN_THROUGH_NOTE}'
        )
    if warnings:
        reply['warning'] = ' '.join(warnings)
    if results and (cache := dop_cache.dop_cache_note([node])):
        reply['simulation_cache'] = cache
    return reply


@register_command(PluginCommand.PARAMETERS_GET_PARAMETER_SCHEMA)
def _get_parameter_schema(
    node_path: str,
    parm_name: str | None = None,
    filter: str | None = None,
    **_: Any,
) -> dict[str, Any]:
    """Get full parameter template info."""

    node = _resolve_node(node_path)

    if parm_name is not None:
        parm = node.parm(parm_name)
        if parm is None:
            return {
                'node_path': node_path,
                'error': f"Parameter '{parm_name}' not found",
                'did_you_mean': suggest_parms(parm_name, parm_labels(node)),
            }
        return {
            'node_path': node_path,
            'parameter': _template_to_dict(parm.parmTemplate()),
        }

    # All parameters — hidden params skipped to keep the response compact.
    ptg = node.parmTemplateGroup()
    parm_infos: list[dict[str, Any]] = []

    def _walk(entries: tuple) -> None:
        for entry in entries:
            if isinstance(entry, hou.FolderParmTemplate):
                _walk(entry.parmTemplates())
            elif not entry.isHidden():
                parm_infos.append(_template_to_dict(entry))

    _walk(ptg.parmTemplates())

    if filter:
        f = filter.lower()
        parm_infos = [
            p for p in parm_infos if f in p['name'].lower() or f in p['label'].lower()
        ]

    # Unfiltered this was every visible template with up to 50 menu items each:
    # 70 KB on a Pyro Solver. The first 60 in full, the rest by name.
    shown = parm_infos if filter else parm_infos[:_SCHEMA_CAP]
    result = {
        'node_path': node_path,
        'parameter_count': len(parm_infos),
        'parameters': shown,
    }
    if len(shown) < len(parm_infos):
        result['not_shown'] = [p['name'] for p in parm_infos[len(shown) :]]
        result['note'] = (
            'Pass filter=... (or parm_name) for the full entries of the rest.'
        )
    return result


_SCHEMA_CAP = 60


@register_command(PluginCommand.PARAMETERS_SET_EXPRESSION)
def _set_expression(
    node_path: str,
    parm_name: str,
    expression: str,
    language: str = 'hscript',
    **_: Any,
) -> dict[str, Any]:
    """Set an expression on a parameter."""

    parm = _resolve_parm(node_path, parm_name)

    lang = (
        hou.exprLanguage.Python
        if language.lower() == 'python'
        else hou.exprLanguage.Hscript
    )

    replaced = set_whole_expression(parm, expression, lang)

    result = {
        'node_path': node_path,
        'parm_name': parm_name,
        'expression': expression,
        'language': language,
    }
    if replaced:
        result['replaced_keyframes'] = replaced
    problems = broken_references(parm)
    if lang == hou.exprLanguage.Hscript:
        # An unknown function or a bracing error evaluates to 0 without
        # raising, so the expression looks set and quietly reads zero.
        previous = hou.pwd()
        try:
            hou.setPwd(parm.node())
            hou.hscriptExpression(expression)
        except hou.OperationFailed as exc:
            detail = str(exc).replace('The attempted operation failed.', '').strip()
            problems.append(f'{parm_name}: the expression does not evaluate ({detail})')
        except Exception:
            pass
        finally:
            hou.setPwd(previous)
    if problems:
        result['warning'] = '; '.join(problems)
    return result


@register_command(PluginCommand.PARAMETERS_GET_EXPRESSION)
def _get_expression(node_path: str, parm_name: str, **_: Any) -> dict[str, Any]:
    """Get the current expression on a parameter."""

    parm = _resolve_parm(node_path, parm_name)

    try:
        expr = parm.expression()
        lang = parm.expressionLanguage().name()
    except hou.OperationFailed:
        expr = None
        lang = None

    return {
        'node_path': node_path,
        'parm_name': parm_name,
        'expression': expr,
        'language': lang,
    }


@register_command(PluginCommand.PARAMETERS_REVERT_PARAMETER)
def _revert_parameter(node_path: str, parm_name: str, **_: Any) -> dict[str, Any]:
    """Revert a parameter to its default value."""

    parm = _resolve_parm(node_path, parm_name)

    # Reverting a locked parm fails with the same bare permission error as a
    # write -- and the #41 hint used to send callers exactly here.
    locked = locked_message(parm)
    if locked:
        raise LockedParmError(locked)
    # revertToDefaults() alone leaves an expression and keyframes in place
    # (measured on 22.0.368: $F*2 and two keys survived it), while this
    # reported reverted: True. Deleting the keyframes first clears both, and
    # a factory default expression ($FSTART on a ROP's f1) still comes back.
    parm.deleteAllKeyframes()
    parm.revertToDefaults()

    result = {
        'node_path': node_path,
        'parm_name': parm_name,
        'reverted': True,
        'value': _serialize_value(parm.eval()),
    }
    if (expression := _expression_of(parm)) is not None:
        result['default_expression'] = expression
        # A default expression in the wrong language comes back too and
        # evaluates to an empty value without raising; name its language and
        # the error it leaves on the node.
        with contextlib.suppress(Exception):
            result['default_expression_language'] = (
                str(parm.expressionLanguage()).rsplit('.', 1)[-1].lower()
            )
        if error := _expression_error(parm):
            result['expression_error'] = error
    return result


def _channel_function(parm: hou.Parm) -> str:
    """The HScript channel function that reads *parm* as its own type."""

    try:
        kind = parm.parmTemplate().type()
    except Exception:
        return 'ch'
    return 'chs' if kind == hou.parmTemplateType.String else 'ch'


def _relative_channel_path(dst: hou.Parm, src: hou.Parm) -> str:
    """Path to *src* as *dst* would write it: relative, the way Houdini's own..."""

    rel = dst.node().relativePathTo(src.node())
    if rel in ('', '.'):
        return src.name()
    return f'{rel}/{src.name()}'


_CH_REF = re.compile(r"""\bch[fis]?\(\s*["']([^"']+)["']\s*\)""")


def _reaches(parm: hou.Parm, goal: str, seen: set[str]) -> bool:
    """True when *parm* reads *goal* through static HScript ch() references."""

    if parm.path() == goal:
        return True
    if parm.path() in seen:
        return False
    seen.add(parm.path())
    for key in parm.keyframes():
        with contextlib.suppress(hou.OperationFailed):
            for ref in _CH_REF.findall(key.expression()):
                dep = parm.node().parm(ref)
                if dep is not None and _reaches(dep, goal, seen):
                    return True
    return False


@register_command(PluginCommand.PARAMETERS_LINK_PARAMETERS)
def _link_parameters(
    source_path: str,
    source_parm: str,
    dest_path: str,
    dest_parm: str,
    replace_existing: bool = False,
    **_: Any,
) -> dict[str, Any]:
    """Create a channel reference from destination parameter to source parameter."""

    src = _resolve_parm(source_path, source_parm)
    dst = _resolve_parm(dest_path, dest_parm)

    if dst.keyframes() and not replace_existing:
        raise ValueError(
            f'{dst.path()} already has animation or an expression; '
            'pass replace_existing=True to overwrite it.'
        )
    if _reaches(src, dst.path(), set()):
        raise ValueError(
            f'Linking {dst.path()} to {src.path()} would create a channel cycle.'
        )

    function = _channel_function(dst)
    channel_path = _relative_channel_path(dst, src)
    ref_expr = f'{function}("{channel_path}")'
    set_whole_expression(dst, ref_expr, hou.exprLanguage.Hscript)

    reply: dict[str, Any] = {
        'source': src.path(),
        'destination': dst.path(),
        'expression': ref_expr,
        'function': function,
        'relative': not channel_path.startswith('/'),
    }
    with contextlib.suppress(Exception):
        reply['value'] = _serialize_value(dst.eval())
    src_kind = _channel_function(src)
    if src_kind != function:
        reply['warning'] = (
            f"'{dst.name()}' is a {'String' if function == 'chs' else 'numeric'} "
            f'parameter '
            f'linked to a {"String" if src_kind == "chs" else "numeric"} source; '
            f'{function}() converts the value on read.'
        )
    return reply


@register_command(PluginCommand.PARAMETERS_LOCK_PARAMETER)
def _lock_parameter(
    node_path: str, parm_name: str, locked: bool, **_: Any
) -> dict[str, Any]:
    """Lock or unlock a parameter."""

    parm = _resolve_parm(node_path, parm_name)

    parm.lock(locked)

    return {
        'node_path': node_path,
        'parm_name': parm_name,
        'locked': parm.isLocked(),
    }


def _menu_template(
    parm_name: str, label: str, menu_items: Any, default_value: Any
) -> hou.MenuParmTemplate:
    """A menu spare parm: items as set_hda_interface takes them, default by token..."""

    from ._helpers import _menu_default, _menu_pairs

    spec: dict[str, Any] = {'name': parm_name, 'menu_items': menu_items}
    if menu_items is None and isinstance(default_value, (list, tuple)):
        spec['menu_items'] = default_value
    elif default_value is not None:
        spec['default'] = default_value
    if not spec['menu_items']:
        raise ValueError(
            f'Menu parameter {parm_name!r} needs menu_items: plain strings, or '
            f'[value, label] pairs such as [["0", "Uniform"], ["1", "By Attribute"]]; '
            f'default_value then picks one by value or index.'
        )
    values, labels = _menu_pairs(spec)
    return hou.MenuParmTemplate(
        parm_name,
        label,
        menu_items=values,
        menu_labels=labels,
        default_value=_menu_default(spec, values),
    )


def _menu_readback(parm: hou.Parm) -> dict[str, Any]:
    """The menu as the node now holds it: [value, label] pairs and the default token."""

    template = parm.parmTemplate()
    values, labels = list(template.menuItems()), list(template.menuLabels())
    return {
        'menu_items': [[v, lab] for v, lab in zip(values, labels, strict=True)],
        'default_value': values[template.defaultValue()] if values else None,
    }


@register_command(PluginCommand.PARAMETERS_CREATE_SPARE_PARAMETER)
def _create_spare_parameter(
    node_path: str,
    parm_name: str,
    parm_type: str,
    label: str,
    default_value: Any = None,
    min_val: float | None = None,
    max_val: float | None = None,
    menu_items: list | None = None,
    **_: Any,
) -> dict[str, Any]:
    """Add a custom spare parameter to a node."""

    node = _resolve_node(node_path)

    # Map string type names to ParmTemplate constructors
    type_map: dict[str, type] = {
        'float': hou.FloatParmTemplate,
        'int': hou.IntParmTemplate,
        'string': hou.StringParmTemplate,
        'toggle': hou.ToggleParmTemplate,
        'menu': hou.MenuParmTemplate,
    }

    template_cls = type_map.get(parm_type.lower())
    if template_cls is None:
        raise ValueError(
            f"Unsupported parm_type '{parm_type}'. Supported types: "
            f'{list(type_map.keys())}'
        )

    # Build keyword arguments for the template constructor
    kwargs: dict[str, Any] = {}

    if template_cls in (hou.FloatParmTemplate, hou.IntParmTemplate):
        # Cast to the correct numeric type for the template
        _cast = int if template_cls is hou.IntParmTemplate else float

        # These require num_components; default to 1
        if default_value is not None:
            if not isinstance(default_value, (list, tuple)):
                default_value = [default_value]
            kwargs['num_components'] = len(default_value)
            kwargs['default_value'] = tuple(_cast(v) for v in default_value)
        else:
            kwargs['num_components'] = 1

        if min_val is not None:
            kwargs['min'] = _cast(min_val)
            kwargs['min_is_strict'] = False
        if max_val is not None:
            kwargs['max'] = _cast(max_val)
            kwargs['max_is_strict'] = False

        pt = template_cls(parm_name, label, **kwargs)

    elif template_cls is hou.StringParmTemplate:
        kwargs['num_components'] = 1
        if default_value is not None:
            if not isinstance(default_value, (list, tuple)):
                default_value = [default_value]
            kwargs['default_value'] = tuple(str(v) for v in default_value)
        pt = template_cls(parm_name, label, **kwargs)

    elif template_cls is hou.ToggleParmTemplate:
        dv = bool(default_value) if default_value is not None else False
        pt = template_cls(parm_name, label, default_value=dv)

    elif template_cls is hou.MenuParmTemplate:
        pt = _menu_template(parm_name, label, menu_items, default_value)
    else:
        pt = template_cls(parm_name, label, **kwargs)

    # Add to node
    ptg = node.parmTemplateGroup()
    ptg.addParmTemplate(pt)
    node.setParmTemplateGroup(ptg)

    result: dict[str, Any] = {
        'node_path': node_path,
        'parm_name': parm_name,
        'parm_type': parm_type,
        'label': label,
        'created': True,
    }
    if template_cls is hou.MenuParmTemplate:
        with contextlib.suppress(Exception):
            result.update(_menu_readback(node.parm(parm_name)))
    return result


def _build_parm_template(spec: dict) -> hou.ParmTemplate:
    """Build a single ParmTemplate from a specification dict."""

    type_map: dict[str, type] = {
        'float': hou.FloatParmTemplate,
        'int': hou.IntParmTemplate,
        'string': hou.StringParmTemplate,
        'toggle': hou.ToggleParmTemplate,
        'menu': hou.MenuParmTemplate,
    }

    parm_name = spec['parm_name']
    parm_type = spec['parm_type'].lower()
    label = spec['label']
    default_value = spec.get('default_value')
    min_val = spec.get('min_val')
    max_val = spec.get('max_val')

    template_cls = type_map.get(parm_type)
    if template_cls is None:
        raise ValueError(
            f"Unsupported parm_type '{parm_type}' for parameter '{parm_name}'."
        )

    kwargs: dict[str, Any] = {}

    if template_cls in (hou.FloatParmTemplate, hou.IntParmTemplate):
        _cast = int if template_cls is hou.IntParmTemplate else float
        if default_value is not None:
            if not isinstance(default_value, (list, tuple)):
                default_value = [default_value]
            kwargs['num_components'] = len(default_value)
            kwargs['default_value'] = tuple(_cast(v) for v in default_value)
        else:
            kwargs['num_components'] = 1
        if min_val is not None:
            kwargs['min'] = _cast(min_val)
            kwargs['min_is_strict'] = False
        if max_val is not None:
            kwargs['max'] = _cast(max_val)
            kwargs['max_is_strict'] = False
        return template_cls(parm_name, label, **kwargs)

    if template_cls is hou.StringParmTemplate:
        kwargs['num_components'] = 1
        if default_value is not None:
            if not isinstance(default_value, (list, tuple)):
                default_value = [default_value]
            kwargs['default_value'] = tuple(str(v) for v in default_value)
        return template_cls(parm_name, label, **kwargs)

    if template_cls is hou.ToggleParmTemplate:
        dv = bool(default_value) if default_value is not None else False
        return template_cls(parm_name, label, default_value=dv)

    if template_cls is hou.MenuParmTemplate:
        return _menu_template(parm_name, label, spec.get('menu_items'), default_value)

    return template_cls(parm_name, label, **kwargs)


_FOLDER_TYPE_MAP = {
    'Tabs': hou.folderType.Tabs,
    'tabs': hou.folderType.Tabs,
    'Collapsible': hou.folderType.Collapsible,
    'collapsible': hou.folderType.Collapsible,
    'Simple': hou.folderType.Simple,
    'simple': hou.folderType.Simple,
}


@register_command(PluginCommand.PARAMETERS_CREATE_SPARE_PARAMETERS)
def _create_spare_parameters(
    node_path: str,
    parameters: list,
    folder_name: str | None = None,
    folder_type: str = 'Tabs',
    **_: Any,
) -> dict[str, Any]:
    """Batch-create spare parameters, optionally inside a folder/tab."""

    node = _resolve_node(node_path)
    ptg = node.parmTemplateGroup()

    templates = []
    created = []
    updated = []
    for spec in parameters:
        pt = _build_parm_template(spec)
        existing = ptg.find(spec['parm_name'])
        if existing is None:
            # A tuple component such as "tx" is not a template name, so the
            # group does not know it, but Houdini refuses it at commit time.
            component = node.parm(spec['parm_name'])
            if component is not None:
                raise ValueError(
                    f"'{spec['parm_name']}' is a component of the existing tuple "
                    f"'{component.tuple().name()}'; pick another name."
                )
            templates.append(pt)
            created.append(spec['parm_name'])
            continue
        # Same name: edit in place. Houdini keeps the current value and
        # keyframes when the name and type are unchanged, so a type change
        # is refused rather than silently dropping data.
        current = node.parm(spec['parm_name']) or node.parmTuple(spec['parm_name'])
        if current is not None and not (
            current.isSpare()
            if isinstance(current, hou.Parm)
            else all(p.isSpare() for p in current)
        ):
            raise ValueError(
                f"'{spec['parm_name']}' is a built-in parameter; only spare parameters "
                f'can be edited.'
            )
        if existing.type() != pt.type():
            raise ValueError(
                f"'{spec['parm_name']}' exists as {existing.type().name()}; "
                f'cannot change it to {pt.type().name()} without losing its value.'
            )
        ptg.replace(spec['parm_name'], pt)
        updated.append(spec['parm_name'])

    if not templates:
        pass
    elif folder_name is not None:
        ft = _FOLDER_TYPE_MAP.get(folder_type, hou.folderType.Tabs)
        folder = hou.FolderParmTemplate(
            folder_name.lower().replace(' ', '_'),
            folder_name,
            parm_templates=templates,
            folder_type=ft,
        )
        ptg.addParmTemplate(folder)
    else:
        for pt in templates:
            ptg.addParmTemplate(pt)

    node.setParmTemplateGroup(ptg)

    return {
        'node_path': node_path,
        'created': created,
        'updated': updated,
        'count': len(created) + len(updated),
        'folder_name': folder_name,
    }


_GET_PARMS_CAP = 60

# Rows a network sweep returns before it reports `truncated`.
_SWEEP_ROW_CAP = 2000


def _parm_entry(parm: hou.Parm, include_defaults: bool) -> dict[str, Any]:
    """One parameter as get_parameters reports it, for a node or a sweep row."""

    data_parm = _data_parm_value(parm, parm.parmTemplate())
    entry: dict[str, Any] = data_parm or {'value': _serialize_value(parm.eval())}
    raw = parm.rawValue()
    # Only worth reporting when it differs: an expression is the thing a
    # caller most often needs to see and a literal is just noise.
    if not data_parm and isinstance(raw, str) and raw != str(entry['value']):
        entry['raw_value'] = raw
    if include_defaults:
        # The same rule as non_default_only: a ramp by isAtRampDefault.
        at_default = not _off_default(parm)
        entry['is_at_default'] = at_default
        # At its default the default only repeats the value: on a full popsource
        # sweep that was 2398 -> 4429 characters for nothing new.
        if not at_default:
            entry.update(_default_of(parm))
    return entry


def _default_of(parm: hou.Parm) -> dict[str, Any]:
    """The template default of one parm component: `default`, `default_expression`."""

    found: dict[str, Any] = {}
    with contextlib.suppress(Exception):
        template = parm.parmTemplate()
        index = parm.componentIndex()
        values = template.defaultValue()
        # A tuple per component for Float/Int/String; a menu or a toggle has
        # a single value.
        if isinstance(values, (tuple, list)):
            values = (
                values[index]
                if index < len(values)
                else (values[0] if values else None)
            )
        found['default'] = _serialize_value(values)
        with contextlib.suppress(Exception):
            expressions = template.defaultExpression()
            # A str on a menu or a toggle: indexing it would give one character.
            if isinstance(expressions, str):
                expression = expressions
            else:
                expression = expressions[index] if index < len(expressions) else ''
            # Built-in toggles answer their default as the token "on"/"off",
            # which is the value spelt out, not an expression.
            if expression and expression not in ('on', 'off'):
                found['default_expression'] = expression
    return found


def _off_default(parm: hou.Parm) -> bool:
    """Whether *parm* was changed from its default (a type's own expression is not)."""

    try:
        ramp = parm if parm.parmTemplate().type() == hou.parmTemplateType.Ramp else None
        if ramp is None:
            parent = parm.parentMultiParm()
            if (
                parent is not None
                and parent.parmTemplate().type() == hou.parmTemplateType.Ramp
            ):
                ramp = parent
        if ramp is not None:
            return not ramp.isAtRampDefault()
        return not parm.isAtDefault()
    except Exception:
        return False


def _valueless(parm: hou.Parm) -> bool:
    """Whether *parm* is a button, a folder or another parm with no value to report."""

    from ._helpers import _VALUELESS_PARM_TYPES

    try:
        return parm.parmTemplate().type().name() in _VALUELESS_PARM_TYPES
    except Exception:
        return False


def _ramp_key_folded(parm: hou.Parm, lowered: list[str] | None) -> bool:
    """Whether *parm* is a ramp's key that non_default_only reports inside the ramp."""

    try:
        if not parm.isMultiParmInstance():
            return False
        ramp = parm.parentMultiParm()
        if ramp is None or ramp.parmTemplate().type() != hou.parmTemplateType.Ramp:
            return False
    except Exception:
        return False
    if lowered is None or _matches_patterns(ramp, lowered):
        return True
    # Key labels ("Position", "Value") are the same on every key: only the
    # index in the name sets one key apart. ramp2pos -> ramppos.
    name = parm.name().lower()
    generic = re.sub(r'\d+', '', name)
    named_apart = any(p in name and p not in generic for p in lowered)
    return not named_apart


def _ramp_named_by_key(parm: hou.Parm, lowered: list[str] | None) -> bool:
    """Whether a pattern matches *parm*'s keys though not *parm*, a ramp."""

    if lowered is None:
        return False
    try:
        if parm.parmTemplate().type() != hou.parmTemplateType.Ramp:
            return False
        return any(
            _matches_patterns(key, lowered) and _ramp_key_folded(key, lowered)
            for key in parm.multiParmInstances()
        )
    except Exception:
        return False


def _matches_patterns(parm: hou.Parm, lowered: list[str] | None) -> bool:
    """Whether any lowered pattern is a substring of the parm's name or label."""

    if lowered is None:
        return True
    name = parm.name().lower()
    label = parm.parmTemplate().label().lower()
    return any(p in name or p in label for p in lowered)


@register_command(PluginCommand.PARAMETERS_GET_PARAMETERS)
def _get_parameters(
    node_path: str | None = None,
    patterns: list[str] | str | None = None,
    include_defaults: bool = False,
    inside: str | None = None,
    recursive: bool = False,
    node_type: str | None = None,
    include_locked_assets: bool = False,
    non_default_only: bool = False,
    value_contains: str | None = None,
    **_: Any,
) -> dict[str, Any]:
    """Current values for every parameter matching any of several patterns."""

    if non_default_only:
        include_defaults = True
    if inside is not None:
        if node_path is not None:
            raise ValueError(
                'pass either node_path (one node) or inside (a network), not both.'
            )
        return _sweep_parameters(
            inside,
            patterns,
            include_defaults,
            recursive,
            node_type,
            include_locked_assets,
            non_default_only,
            value_contains,
        )
    if node_path is None:
        raise ValueError('node_path is required (or inside, to read a whole network).')
    needle = _needle(value_contains)
    node = hou.node(node_path)
    if node is None:
        raise hou.OperationFailed(f'Node not found: {node_path}')

    if isinstance(patterns, str):
        patterns = [patterns]
    lowered = [p.lower() for p in patterns] if patterns else None

    values: dict[str, Any] = {}
    matched = 0
    for parm in node.parms():
        # A folder stores its open tab: a switched tab read as "changed".
        if (non_default_only or needle is not None) and _valueless(parm):
            continue
        folds = non_default_only and needle is None
        if not _matches_patterns(parm, lowered) and not (
            folds and _ramp_named_by_key(parm, lowered)
        ):
            continue
        # A key that holds the needle is the answer, not part of its ramp.
        if folds and _ramp_key_folded(parm, lowered):
            continue
        if non_default_only and not _off_default(parm):
            continue
        if needle is not None and not _holds_text(parm, needle):
            continue
        matched += 1
        if len(values) >= _GET_PARMS_CAP:
            continue
        values[parm.name()] = _parm_entry(parm, include_defaults)

    return {
        'node_path': node_path,
        'node_type': node.type().name(),
        'patterns': patterns,
        **({'value_contains': value_contains} if needle is not None else {}),
        'matched': matched,
        'returned': len(values),
        'truncated': matched > len(values),
        'parameters': values,
    }


def _needle(value_contains: Any) -> str | None:
    """The lowered substring value_contains asks for, or None."""

    if value_contains is None:
        return None
    text = str(value_contains)
    if not text:
        raise ValueError('value_contains must not be empty.')
    return text.lower()


def _holds_text(parm: hou.Parm, needle: str) -> bool:
    """Whether *parm*'s raw text or expression contains *needle* (lowered)."""

    texts: list[str] = []
    with contextlib.suppress(Exception):
        texts.append(str(parm.rawValue()))
    with contextlib.suppress(Exception):
        texts.extend(
            key.expression() for key in parm.keyframes() if key.isExpressionSet()
        )
    return any(needle in text.lower() for text in texts if text)


def _sweep_parameters(
    inside: str,
    patterns: list[str] | str | None,
    include_defaults: bool,
    recursive: bool,
    node_type: str | None,
    include_locked_assets: bool = False,
    non_default_only: bool = False,
    value_contains: str | None = None,
) -> dict[str, Any]:
    """get_parameters over the nodes of a network, as one table of rows."""

    from ._helpers import _VALUELESS_PARM_TYPES

    parent = hou.node(inside)
    if parent is None:
        raise hou.OperationFailed(f'Node not found: {inside}')
    if isinstance(patterns, str):
        patterns = [patterns]
    needle = _needle(value_contains)
    if not patterns and not non_default_only and needle is None:
        raise ValueError(
            'patterns is required with inside: every parameter of a whole network '
            "is not an answer anyone can read. Name what to look for, e.g. ['file'], "
            'or ask for non_default_only=True or value_contains.'
        )
    lowered = [p.lower() for p in patterns] if patterns else None
    # A locked asset's instance stays (its interface is the user's); what is
    # inside it is the asset's own business -- unless the sweep was asked to
    # start inside one.
    asked_inside = False
    with contextlib.suppress(Exception):
        asked_inside = parent.isLockedHDA() or parent.isInsideLockedHDA()
    reads_locked = include_locked_assets or asked_inside
    # A locked asset's contents load on demand: until something syncs them,
    # allSubChildren() answers none (a fresh popsolver: 0 of its ~670 nodes).
    nodes = list(
        parent.allSubChildren(sync_delayed_definition=reads_locked)
        if recursive
        else parent.children()
    )
    skipped_locked = 0
    if recursive and not reads_locked:
        kept = []
        for node in nodes:
            buried = False
            with contextlib.suppress(Exception):
                buried = node.isInsideLockedHDA()
            if buried:
                # Counted only if the sweep would have read it: node_type="file"
                # used to report every node of every asset as skipped.
                if not node_type or node.type().name() == node_type:
                    skipped_locked += 1
            else:
                kept.append(node)
        nodes = kept
    rows: list[dict[str, Any]] = []
    matched = 0
    scanned = 0
    nodes_matched = 0
    for node in nodes:
        if node_type and node.type().name() != node_type:
            continue
        scanned += 1
        hit = False
        for parm in node.parms():
            # A button or a folder matched by label has no value to report.
            with contextlib.suppress(Exception):
                if parm.parmTemplate().type().name() in _VALUELESS_PARM_TYPES:
                    continue
            folds = non_default_only and needle is None
            if not _matches_patterns(parm, lowered) and not (
                folds and _ramp_named_by_key(parm, lowered)
            ):
                continue
            # A key that holds the needle is the answer, not part of its ramp.
            if folds and _ramp_key_folded(parm, lowered):
                continue
            if non_default_only and not _off_default(parm):
                continue
            if needle is not None and not _holds_text(parm, needle):
                continue
            matched += 1
            hit = True
            if len(rows) >= _SWEEP_ROW_CAP:
                continue
            row: dict[str, Any] = {'node': node.path(), 'parm': parm.name()}
            row.update(_parm_entry(parm, include_defaults))
            rows.append(row)
        nodes_matched += hit
    return {
        'inside': parent.path(),
        'recursive': bool(recursive),
        'node_type': node_type,
        'patterns': patterns,
        **({'non_default_only': True} if non_default_only else {}),
        **({'value_contains': value_contains} if needle is not None else {}),
        'nodes_scanned': scanned,
        'nodes_matched': nodes_matched,
        'matched': matched,
        'returned': len(rows),
        'truncated': matched > len(rows),
        'rows': rows,
        **(
            {
                'skipped_inside_locked_assets': skipped_locked,
                'note': (
                    'Nodes inside locked HDAs were not read; '
                    'include_locked_assets=True '
                    'reads them.'
                ),
            }
            if skipped_locked
            else {}
        ),
    }


# Every HScript function that reads a channel by path
# ($HFS/houdini/help/expressions.zip). Longest first, so chsop is not read
# as chs.
_CHANNEL_FUNCTIONS = (
    "ch", "chexist", "chexpr", "chexprf", "chexprt", "chf", "chramp", "chrampf",
    "chrampraw", "chrampt", "chs", "chsop", "chsoplist", "chsraw", "cht",
)  # fmt: skip
_CHANNEL_NAMES = '|'.join(sorted(_CHANNEL_FUNCTIONS, key=len, reverse=True))
_CHANNEL_REF_RE = re.compile(
    r'\b(?:' + _CHANNEL_NAMES + r""")\s*\(\s*['"]([^'"]+)['"]"""
)
_BACKTICKS_RE = re.compile(r'`([^`]*)`')


def _outgoing_reference(parm: hou.Parm) -> dict[str, Any] | None:
    """What *parm* reads from, or None when it reads no other channel."""

    expression = None
    with contextlib.suppress(Exception):
        expression = parm.expression()
    texts: list[str] = []
    in_backticks = False
    if expression:
        texts = [expression]
    else:
        with contextlib.suppress(Exception):
            raw = parm.unexpandedString()
            texts = _BACKTICKS_RE.findall(raw)
            if texts:
                expression, in_backticks = raw, True
    if not texts:
        return None
    entry: dict[str, Any] = {'parm': parm.name(), 'expression': expression}
    if in_backticks:
        entry['in_backticks'] = True
    else:
        with contextlib.suppress(Exception):
            direct = parm.getReferencedParm()
            if direct is not None and direct.path() != parm.path():
                entry['references'] = [direct.path()]
                entry['pure_reference'] = True
                return entry
    resolved: list[str] = []
    unresolved: list[str] = []
    node = parm.node()
    for text in texts:
        for token in _CHANNEL_REF_RE.findall(text):
            target = None
            with contextlib.suppress(Exception):
                target = node.parm(token)
            if target is not None:
                resolved.append(target.path())
            else:
                unresolved.append(token)
    if not resolved and not unresolved:
        return None
    entry['references'] = resolved
    if unresolved:
        # Written in the expression, but no such parameter now: a renamed or
        # deleted target, which is exactly what a rename audit is after.
        entry['unresolved'] = unresolved
    entry['pure_reference'] = False
    return entry


def _factory_type(node_type: hou.NodeType) -> bool:
    """True for a compiled node type or an asset shipped under $HFS."""

    definition = node_type.definition()
    if definition is None:
        return True
    hfs = os.path.normcase(os.path.normpath(hou.text.expandString('$HFS')))
    library = os.path.normcase(os.path.normpath(definition.libraryFilePath()))
    return library.startswith(hfs + os.sep)


def broken_references(parm: hou.Parm) -> list[str]:
    """Channel references in *parm* that point at a node or parameter that is not..."""

    # Cheap gate first: this runs over every parm of every node in a verify,
    # and _outgoing_reference raises and swallows on each plain value.
    try:
        if not parm.keyframes() and (
            parm.parmTemplate().type() != hou.parmTemplateType.String
            or '`' not in parm.unexpandedString()
        ):
            return []
    except Exception:
        return []
    # A factory default is the node type's own, and Houdini evaluates it where
    # it means something: popsteerseek's `state` reads ch("statemethod") off
    # the crowd state, not the node. Twelve popsteer* nodes came back with an
    # error the node does not have (node.errors() empty). Only SideFX's own
    # defaults: a spare or a user asset's parm built with default_expression
    # is also "at default", and its ch("../CTRL/h") is the caller's.
    with contextlib.suppress(Exception):
        if (
            not parm.isSpare()
            and parm.isAtDefault()
            and _factory_type(parm.node().type())
        ):
            return []
    entry = _outgoing_reference(parm)
    return [
        f"{parm.name()}: reference '{token}' does not resolve, so it silently "
        f'evaluates to 0 or an empty string'
        for token in (entry or {}).get('unresolved', [])
        if '$' not in token
    ]


def _capped_paths(nodes: Any, exclude: str, limit: int) -> tuple[list[str], int]:
    paths = sorted({n.path() for n in nodes} - {exclude})
    return paths[:limit], len(paths)


@register_command(PluginCommand.PARAMETERS_GET_PARM_REFERENCES)
def _get_parm_references(
    node_path: str,
    parm_name: str | None = None,
    direction: str = 'both',
    limit: int = 200,
    include_node_level: bool | None = None,
    **_: Any,
) -> dict[str, Any]:
    """Who references a parameter, and what it references -- both directions."""

    if direction not in ('both', 'incoming', 'outgoing'):
        raise ValueError("direction must be 'both', 'incoming' or 'outgoing'.")
    limit = int(limit)
    node = _resolve_node(node_path)
    parms = (
        [_resolve_parm(node_path, parm_name)]
        if parm_name is not None
        else list(node.parms())
    )

    dependents: list = []
    with contextlib.suppress(Exception):
        dependents = list(node.dependents(include_children=False))
    # parmsReferencingThis() walks the whole scene, once per parameter. A
    # reader through ch() or backticks makes its node a dependent (a
    # self-reference makes this node its own), so with no dependents there is
    # nothing to find and the scan is skipped.
    scan_incoming = direction in ('both', 'incoming') and bool(dependents)

    incoming: list[dict[str, Any]] = []
    outgoing: list[dict[str, Any]] = []
    truncated = False
    for parm in parms:
        found: list[tuple[list, dict[str, Any]]] = []
        if scan_incoming:
            with contextlib.suppress(Exception):
                refs = [p.path() for p in parm.parmsReferencingThis()]
                if refs:
                    found.append(
                        (incoming, {'parm': parm.name(), 'referenced_by': refs})
                    )
        if direction in ('both', 'outgoing'):
            entry = _outgoing_reference(parm)
            if entry is not None:
                found.append((outgoing, entry))
        if not found:
            continue
        # Truncated only when there is an entry that does not fit.
        if len(incoming) + len(outgoing) + len(found) > limit:
            truncated = True
            break
        for target, entry in found:
            target.append(entry)

    result: dict[str, Any] = {
        'node_path': node.path(),
        'parm_name': parm_name,
        'direction': direction,
        'incoming': incoming,
        'outgoing': outgoing,
        'truncated': truncated,
    }
    # Asked about one parameter, the answer is about that parameter. On an
    # asset with 947 children the node-level lists came to about 117 KB, next
    # to 7 KB of parameter entries, for a question they do not answer. Still
    # on by default for a whole-node query, and either way on request.
    node_level = (
        parm_name is None if include_node_level is None else bool(include_node_level)
    )
    result['include_node_level'] = node_level
    if node_level:
        # This node only (include_children=False: a subnet's descendants are
        # not its own references), capped like the parameter lists.
        result['node_dependents'], count = _capped_paths(dependents, node.path(), limit)
        if count > limit:
            result['node_dependents_count'] = count
        with contextlib.suppress(Exception):
            references = node.references(include_children=False)
            result['node_references'], count = _capped_paths(
                references, node.path(), limit
            )
            if count > limit:
                result['node_references_count'] = count
    with contextlib.suppress(Exception):
        if node.needsToCook():
            result['note'] = (
                'node_dependents / node_references, and the dependents check that '
                "decides whether `incoming` is scanned, are as of this node's last "
                'cook (HOM: they can differ until it cooks); `outgoing` is parsed '
                'from expressions and is not.'
            )
    return result


def _template_tree_entry(pt: hou.ParmTemplate) -> dict[str, Any]:
    """One template as the Type Properties dialog shows it: folders, ranges,..."""

    entry = _template_to_dict(pt)
    with contextlib.suppress(Exception):
        conditionals = pt.conditionals()
        if conditionals:
            entry['conditionals'] = {
                key.name() if hasattr(key, 'name') else str(key): value
                for key, value in conditionals.items()
            }
    with contextlib.suppress(Exception):
        help_text = pt.help()
        if help_text:
            entry['help'] = help_text
    with contextlib.suppress(Exception):
        if pt.joinsWithNext():
            entry['join_with_next'] = True
    with contextlib.suppress(Exception):
        tags = dict(pt.tags())
        if tags:
            entry['tags'] = {
                k: (v if len(str(v)) <= 120 else str(v)[:120] + '...')
                for k, v in tags.items()
            }
    if entry['type'] == 'Folder':
        with contextlib.suppress(Exception):
            entry['folder_type'] = pt.folderType().name()
            if 'Multiparm' in entry['folder_type']:
                # A multiparm folder's default is the instance count a fresh
                # node gets.
                entry['default_instances'] = entry.get('default_value')
        with contextlib.suppress(Exception):
            if pt.endsTabGroup():
                entry['ends_tab_group'] = True
        children: list[dict[str, Any]] = []
        with contextlib.suppress(Exception):
            for child in pt.parmTemplates():
                # One unreadable child costs that child, not the folder.
                with contextlib.suppress(Exception):
                    children.append(_template_tree_entry(child))
        entry['children'] = children
        return entry
    with contextlib.suppress(Exception):
        expressions = [e for e in pt.defaultExpression() if e]
        if expressions:
            entry['default_expression'] = expressions
    with contextlib.suppress(Exception):
        callback = pt.scriptCallback()
        if callback:
            entry['callback'] = callback
            entry['callback_language'] = pt.scriptCallbackLanguage().name()
    with contextlib.suppress(Exception):
        string_type = pt.stringType().name()
        if string_type != 'Regular':
            entry['string_type'] = string_type
    with contextlib.suppress(Exception):
        entry['data_parm_type'] = pt.dataParmType().name()
    with contextlib.suppress(Exception):
        look = pt.look().name()
        if look != 'Regular':
            entry['look'] = look
    return entry


def _count_tree(entries: list[dict[str, Any]]) -> int:
    return sum(1 + _count_tree(entry.get('children', [])) for entry in entries)


def _prune_tree(
    entries: list[dict[str, Any]], budget: list[int]
) -> list[dict[str, Any]]:
    """Keep the first *budget* entries depth-first; the rest are cut."""

    kept: list[dict[str, Any]] = []
    for entry in entries:
        if budget[0] <= 0:
            break
        budget[0] -= 1
        if 'children' in entry:
            entry['children'] = _prune_tree(entry['children'], budget)
        kept.append(entry)
    return kept


def _node_type_for_tree(context: str, type_name: str) -> Any:
    """Resolve *type_name* in *context* the way createNode would, through the same..."""

    from ._helpers import _resolve_node_type

    categories = hou.nodeTypeCategories()
    category = categories.get(context)
    if category is None:
        raise ValueError(
            f"Unknown context '{context}'. Available: {sorted(categories)}"
        )
    resolved = _resolve_node_type(category, type_name)
    if resolved is None:
        close = get_close_matches(
            type_name, list(category.nodeTypes()), n=5, cutoff=0.4
        )
        raise ValueError(
            f"Node type '{type_name}' not found in {context}. Close: {close}"
        )
    return resolved


@register_command(PluginCommand.PARAMETERS_GET_PARM_TEMPLATE_TREE)
def _get_parm_template_tree(
    node_path: str | None = None,
    type_name: str | None = None,
    context: str = 'Sop',
    folder: Any = None,
    max_entries: int = 150,
    include_tags: bool = False,
    **_: Any,
) -> dict[str, Any]:
    """The whole parameter interface as a tree -- folders, conditionals, menu..."""

    if node_path is not None:
        node = _resolve_node(node_path)
        group = node.parmTemplateGroup()
        subject: dict[str, Any] = {'node_path': node.path(), 'type': node.type().name()}
    elif type_name is not None:
        node_type = _node_type_for_tree(context, type_name)
        group = node_type.parmTemplateGroup()
        subject = {'type': node_type.name(), 'context': context}
    else:
        raise ValueError('give node_path or type_name.')

    if folder is not None:
        labels = tuple(folder) if isinstance(folder, (list, tuple)) else (str(folder),)
        found = group.findFolder(labels)
        if found is None:
            available = [
                e.label() for e in group.entries() if _parm_type_name(e) == 'Folder'
            ]
            raise ValueError(
                f'No folder labelled {labels!r}. Top-level folders: {available}'
            )
        entries = [_template_tree_entry(found)]
    else:
        entries = [_template_tree_entry(entry) for entry in group.entries()]

    if not include_tags:
        # Tags were 34 of the 141 KB a Pyro Solver tree came back as; they
        # matter when editing an interface, so they stay one flag away.
        _drop_key(entries, 'tags')
    total = _count_tree(entries)
    truncated = total > int(max_entries)
    if truncated:
        entries = _prune_tree(entries, [int(max_entries)])

    result = dict(subject)
    result.update(
        {
            'folder': folder,
            'entry_count': total,
            'truncated': truncated,
            'entries': entries,
        }
    )
    if truncated:
        result['note'] = (
            f'{total} entries, showing the first {int(max_entries)}. Narrow with '
            f'folder=<label> or raise max_entries.'
        )
    return result


def _drop_key(entries: list, key: str) -> None:
    for entry in entries:
        entry.pop(key, None)
        _drop_key(entry.get('children') or [], key)


# kind -> hou.vopParmGenType member: what the network editor's input menu offers.
_PARM_GEN_KINDS = {
    'parameter': 'Parameter',
    'constant': 'Constant',
    'subnet_input': 'SubnetInput',
}


def _check_promotion(
    index: int, item: Any, seen: set
) -> tuple[hou.VopNode, str, str] | str:
    """(node, input, kind) for a valid promotion item, or what is wrong with it."""

    if not isinstance(item, dict):
        return f'promotions[{index}] must be an object, got {type(item).__name__}'
    unknown = sorted(
        set(item) - {'node_path', 'input', 'name', 'label', 'kind', 'use_input_value'}
    )
    if unknown:
        return f'promotions[{index}]: unknown key(s) {unknown}'
    node = hou.node(str(item.get('node_path', '')))
    if node is None:
        return f'promotions[{index}]: node not found: {item.get("node_path")!r}'
    if not isinstance(node, hou.VopNode):
        return (
            f'promotions[{index}]: {node.path()} is a '
            f'{node.type().category().name()} node, not a VOP'
        )
    wanted = str(item.get('input', ''))
    names = list(node.inputNames())
    if wanted not in names:
        close = get_close_matches(wanted, names, n=3, cutoff=0.5)
        hint = f' Did you mean {close}?' if close else ''
        return (
            f'promotions[{index}]: {node.path()} has no input '
            f'{wanted!r}.{hint} Inputs: {names}'
        )
    kind = str(item.get('kind', 'parameter'))
    if kind not in _PARM_GEN_KINDS:
        return (
            f'promotions[{index}]: kind must be one of '
            f'{sorted(_PARM_GEN_KINDS)}, got {kind!r}'
        )
    name = item.get('name')
    if name is not None and not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', str(name)):
        return (
            f'promotions[{index}]: name {name!r} is not a parameter '
            'name (letters, digits, _)'
        )
    if (node.path(), wanted) in seen:
        return f'promotions[{index}]: {node.path()} input {wanted!r} is listed twice'
    seen.add((node.path(), wanted))
    source = (
        node.inputs()[names.index(wanted)]
        if names.index(wanted) < len(node.inputs())
        else None
    )
    if source is not None:
        return (
            f'promotions[{index}]: {node.path()} input {wanted!r} is already wired '
            f'from '
            f'{source.path()}; promoting it would replace that wire. Disconnect it '
            f'first.'
        )
    # A Parameter VOP whose name the owner already has binds to that parm
    # instead of making one: fit1.srcmax promoted as "destmax" came back
    # "success" with destmax's value and drove srcmax from it (22.0.368).
    parm_name = str(name or wanted)
    if kind != 'constant':
        # Reserved per owner: the same name in two separate VOP networks is two parms.
        owners = _vop_owners(node)
        keys = {('parm', o.path(), parm_name) for o in owners}
        if keys & seen:
            return (
                f'promotions[{index}]: parm name {parm_name!r} is used twice in this '
                f'batch '
                'for the same network; give a name'
            )
        seen |= keys
        taken = next((o for o in owners if o.parmTuple(parm_name) is not None), None)
        if taken is not None:
            return (
                f'promotions[{index}]: {taken.path()} already has a parm '
                f'{parm_name!r}; '
                'a Parameter VOP of that name would share it. Give another name.'
            )
    return node, wanted, kind


def _vop_owners(node: hou.Node) -> list[hou.Node]:
    """The VOP node's ancestors, nearest first, up to the network outside VOPs."""

    chain = []
    parent = node.parent()
    while parent is not None and parent.path() != '/':
        chain.append(parent)
        if parent.type().category().name() != 'Vop':
            break
        parent = parent.parent()
    return chain


@register_command(PluginCommand.PARAMETERS_PROMOTE_VOP_PARAMETERS)
def _promote_vop_parameters(promotions: list, **_: Any) -> dict[str, Any]:
    """Promote VOP inputs, as the network editor's Promote Parameter does."""

    if not isinstance(promotions, list) or not promotions:
        raise ValueError(
            'promotions must be a non-empty list of {node_path, input, ...}'
        )
    seen: set = set()
    checked = [_check_promotion(i, item, seen) for i, item in enumerate(promotions)]
    errors = [c for c in checked if isinstance(c, str)]
    if errors:
        raise ValueError('Nothing was promoted. ' + '; '.join(errors))
    valid = cast(list[tuple[hou.VopNode, str, str]], checked)

    made: list[hou.Node] = []
    results: list[dict[str, Any]] = []
    try:
        for item, (node, input_name, kind) in zip(promotions, valid, strict=True):
            gen_type = getattr(hou.vopParmGenType, _PARM_GEN_KINDS[kind])
            generator = node.insertParmGenerator(
                input_name, gen_type, bool(item.get('use_input_value', True))
            )
            made.append(generator)
            if item.get('name') and generator.parm('parmname') is not None:
                generator.parm('parmname').set(str(item['name']))
                with contextlib.suppress(Exception):
                    generator.setName(str(item['name']), unique_name=True)
            if item.get('label') and generator.parm('parmlabel') is not None:
                generator.parm('parmlabel').set(str(item['label']))
            results.append(
                {
                    'node_path': node.path(),
                    'input': input_name,
                    'kind': kind,
                    'generator': generator.path(),
                }
            )
    except Exception:
        for generator in made:
            with contextlib.suppress(Exception):
                generator.destroy()
        raise

    compiled: list[str] = []
    for node, _input, kind in checked:
        if kind != 'parameter':
            continue
        for owner in _vop_owners(node):
            button = owner.parm('vop_forcecompile')
            if button is None or owner.path() in compiled:
                continue
            with contextlib.suppress(Exception):
                callback_helpers.press(button)
                compiled.append(owner.path())
            with contextlib.suppress(Exception):
                owner.cook(force=True)
            break

    for entry, generator, (node, _input, kind) in zip(
        results, made, checked, strict=True
    ):
        name_parm = generator.parm('parmname')
        if name_parm is not None:
            entry['parm_name'] = name_parm.eval()
        if kind != 'parameter' or name_parm is None:
            continue
        for owner in _vop_owners(node):
            tup = owner.parmTuple(entry['parm_name'])
            if tup is not None:
                entry['owner'] = owner.path()
                with contextlib.suppress(Exception):
                    value = tup.eval()
                    entry['value'] = list(value) if len(value) > 1 else value[0]
                break
        else:
            entry['owner'] = None
            entry['note'] = (
                f'The Parameter VOP is wired in, but no network above '
                f'{node.path()} shows '  # ty: ignore[unresolved-attribute]
                f'a parm {entry["parm_name"]!r}; compile its VOP network '
                f'(vop_forcecompile).'
            )
    return {
        'success': all(
            e.get('owner')
            for e, c in zip(results, checked, strict=True)
            if c[2] == 'parameter'
        ),
        'promoted': results,
        'compiled': compiled,
    }
