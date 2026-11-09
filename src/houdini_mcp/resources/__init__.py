from __future__ import annotations

from mcp.server.mcpserver import MCPServer

from ..bridge import HoudiniBridge
from ..prompts.models import Content
from .workflows import register_workflow_resources


def register_resources(
    server: MCPServer[dict[str, HoudiniBridge]],
    content: Content,
) -> None:
    """Register all server resources."""

    register_workflow_resources(server, content)


__all__ = ['register_resources']
