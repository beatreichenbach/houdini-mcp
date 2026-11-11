"""Run handlers with the scene cooked at a requested frame."""

from __future__ import annotations

import contextlib
import functools
from typing import Any

import hou

from . import outputs


def stage_frame() -> float | None:
    """The current frame, or None when hou cannot say."""

    with contextlib.suppress(Exception):
        return float(hou.frame())
    return None


def cooked_at_time(handler: Any) -> Any:
    """Run a stage read with the stage cooked at the requested *time*."""

    # wraps keeps the handler's signature visible: the dispatcher reads it to
    # explain a bad argument, and a bare **kwargs answered every call alike.
    @functools.wraps(handler)
    def run(**kwargs: Any) -> Any:
        time = kwargs.get('time')
        if time is None or time == stage_frame():
            return handler(**kwargs)
        with outputs.at_frame(float(time)):
            return handler(**kwargs)

    return run
