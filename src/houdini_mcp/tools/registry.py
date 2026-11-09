"""Local tool decorator, not the third-party MCP SDK module."""

from __future__ import annotations

from collections.abc import Callable
from types import ModuleType
from typing import Any, ParamSpec, TypeVar

P = ParamSpec('P')
R = TypeVar('R')

_TOOL_ATTR = '__houdini_mcp_tool__'


def tool(function: Callable[P, R]) -> Callable[P, R]:
    """Mark a function as an MCP tool without registering it."""

    setattr(function, _TOOL_ATTR, True)
    return function


def marked_tools(module: ModuleType) -> list[Callable[..., Any]]:
    """Return the functions in *module* marked with :func:`tool`."""

    return [
        value
        for value in vars(module).values()
        if getattr(value, _TOOL_ATTR, False)
        and getattr(value, '__module__', None) == module.__name__
    ]
