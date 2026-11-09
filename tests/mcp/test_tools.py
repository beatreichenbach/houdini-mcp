import asyncio
from types import SimpleNamespace
from typing import cast

import pytest
from mcp.server.mcpserver.exceptions import ToolError

from houdini_mcp.errors import (
    HoudiniCommandError,
    HoudiniConnectionError,
    HoudiniMCPError,
)
from houdini_mcp.tools.context import BridgeContext, run_command


class FailingBridge:
    def __init__(self, error: Exception) -> None:
        self._error = error

    async def execute(
        self,
        command: str,
        params: dict[str, object] | None = None,
    ) -> object:
        raise self._error


def _context(bridge: object) -> BridgeContext:
    request_context = SimpleNamespace(lifespan_context={'bridge': bridge})
    return cast(BridgeContext, SimpleNamespace(request_context=request_context))


@pytest.mark.parametrize(
    ('error', 'message'),
    [
        (
            HoudiniCommandError('node not found', 'command failed'),
            r'node not found \(code: command failed\)',
        ),
        (HoudiniConnectionError('cannot reach houdini'), 'cannot reach houdini'),
    ],
)
def test_errors_become_tool_errors(error: HoudiniMCPError, message: str) -> None:
    with pytest.raises(ToolError, match=message):
        asyncio.run(run_command(_context(FailingBridge(error)), 'scene.get_scene_info'))
