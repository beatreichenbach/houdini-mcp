"""MCP tools for code execution inside Houdini."""

from __future__ import annotations

from typing import Any

from .context import BridgeContext, run_command
from .registry import tool

###### code.execute_python


@tool
async def execute_python(
    ctx: BridgeContext,
    code: str,
    justification: str,
    return_expression: str | None = None,
) -> dict:
    """Execute arbitrary Python code inside Houdini. LAST RESORT only."""

    payload: dict[str, Any] = {'code': code}
    if return_expression is not None:
        payload['return_expression'] = return_expression
    result = await run_command(ctx, 'code.execute_python', payload)
    if isinstance(result, dict):
        result['justification'] = justification
    return result


###### code.execute_hscript


@tool
async def execute_hscript(ctx: BridgeContext, command: str) -> dict:
    """Execute an HScript command in Houdini."""

    return await run_command(ctx, 'code.execute_hscript', {'command': command})


###### code.evaluate_expression


@tool
async def evaluate_expression(
    ctx: BridgeContext, expression: str, language: str = 'hscript'
) -> dict:
    """Evaluate an expression in Houdini and return its result."""

    return await run_command(
        ctx,
        'code.evaluate_expression',
        {'expression': expression, 'language': language},
    )


###### code.get_env_variable


@tool
async def get_env_variable(ctx: BridgeContext, var_name: str) -> dict:
    """Get a Houdini environment variable value."""

    return await run_command(ctx, 'code.get_env_variable', {'var_name': var_name})


@tool
async def get_file_references(
    ctx: BridgeContext, include_missing_only: bool = False
) -> dict:
    """Return every file path the scene references."""

    return await run_command(
        ctx, 'code.get_file_references', {'include_missing_only': include_missing_only}
    )


@tool
async def set_update_mode(ctx: BridgeContext, mode: str | None = None) -> dict:
    """Set Houdini's cook update mode, or read it when called with no mode."""

    params: dict = {}
    if mode is not None:
        params['mode'] = mode
    return await run_command(ctx, 'code.set_update_mode', params)
