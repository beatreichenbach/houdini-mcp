from __future__ import annotations

from mcp.server.mcpserver import MCPServer

from ..bridge import HoudiniBridge
from .models import Content, Workflow


def register_prompts(
    server: MCPServer[dict[str, HoudiniBridge]],
    content: Content,
) -> None:
    """Register one prompt per workflow."""

    for workflow in content.workflows.values():
        _register_workflow_prompt(server, workflow, content.shared)


def _register_workflow_prompt(
    server: MCPServer[dict[str, HoudiniBridge]],
    workflow: Workflow,
    shared: dict[str, str],
) -> None:
    @server.prompt(name=workflow.name, description=workflow.description)
    def prompt(context: str = '') -> str:
        return workflow.render(context, shared)
