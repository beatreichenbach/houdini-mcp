from __future__ import annotations

from typing import Any

from mcp.server.mcpserver.exceptions import ResourceError

from ..bridge import current_bridge
from ..errors import HoudiniMCPError


async def run_command(
    command: str,
    params: dict[str, Any] | None = None,
) -> Any:  # noqa: ANN401
    """Run a Houdini command, reporting failures as resource errors."""

    try:
        bridge = current_bridge()
    except RuntimeError as e:
        raise ResourceError(str(e)) from e
    try:
        return await bridge.execute(command, params)
    except HoudiniMCPError as e:
        raise ResourceError(str(e)) from e
