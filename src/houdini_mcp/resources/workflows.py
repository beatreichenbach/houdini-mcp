from __future__ import annotations

from mcp.server.mcpserver import MCPServer

from ..bridge import HoudiniBridge
from ..prompts.models import Content, Workflow


def register_workflow_resources(
    server: MCPServer[dict[str, HoudiniBridge]],
    content: Content,
) -> None:
    """Register each workflow markdown file as a resource."""

    for workflow in content.workflows.values():
        _register_workflow(server, workflow, content.shared)


def _register_workflow(
    server: MCPServer[dict[str, HoudiniBridge]],
    workflow: Workflow,
    shared: dict[str, str],
) -> None:
    @server.resource(
        f'houdini-mcp://workflows/{workflow.name}',
        name=workflow.name,
        description=workflow.description,
        mime_type='text/markdown',
    )
    def read_workflow() -> str:
        return workflow.source(shared)
