from __future__ import annotations

from typing import Any

import hou

from houdini_mcp_plugin.dispatcher import register_command
from houdini_mcp_protocol import PluginCommand


@register_command(PluginCommand.SCENE_GET_SCENE_INFO)
def get_scene_info() -> dict[str, Any]:
    """Return basic information about the current Houdini scene."""

    start, end = hou.playbar.frameRange()
    return {
        'path': hou.hipFile.path(),
        'frame': hou.frame(),
        'fps': hou.fps(),
        'frame_range': [start, end],
        'houdini_version': hou.applicationVersionString(),
    }
