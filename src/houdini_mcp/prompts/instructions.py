from __future__ import annotations

from .models import Content


def build_instructions(content: Content) -> str:
    """Return server instructions with the workflow index."""

    text = content.instructions.strip() or 'Houdini MCP server.'
    lines = [text, '', 'Available workflows:']
    lines.extend(
        f'- {workflow.name}: {workflow.description}'
        for workflow in content.workflows.values()
    )
    lines.extend(
        [
            '',
            'Each workflow is available as a prompt with the same name.',
            'Workflow files are available as houdini-mcp://workflows/<name> resources.',
        ]
    )
    return '\n'.join(lines)
