"""MCP tools for Houdini's shipped documentation."""

from __future__ import annotations

# Built-in
from typing import Any

# Third-party
# Internal
from mcp.server.mcpserver.exceptions import ToolError

from ..prompts import load_content
from .context import BridgeContext, run_command
from .registry import tool


@tool
async def search_help(
    ctx: BridgeContext,
    query: str,
    scope: str | None = None,
    limit: int = 10,
) -> dict:
    """Search Houdini's installed documentation."""

    params: dict[str, Any] = {'query': query, 'limit': limit}
    if scope is not None:
        params['scope'] = scope
    return await run_command(ctx, 'help.search_help', params)


@tool
async def get_help_page(
    ctx: BridgeContext,
    path: str,
    offset: int = 0,
    section: str | None = None,
) -> dict:
    """Fetch one page of Houdini's shipped documentation by path."""

    params: dict[str, Any] = {'path': path}
    if offset:
        params['offset'] = offset
    if section is not None:
        params['section'] = section
    return await run_command(ctx, 'help.get_help_page', params)


@tool
async def get_workflow_guide(
    ctx: BridgeContext, topic: str, description: str = ''
) -> dict:
    """Return the written guide for a workflow topic."""

    del ctx
    content = load_content()
    workflow = content.workflows.get(topic.strip().lower())
    if workflow is None:
        available = ', '.join(sorted(content.workflows))
        raise ToolError(f"No workflow guide for '{topic}'. Available: {available}")
    return {'topic': topic, 'guide': workflow.render(description, content.shared)}
