from enum import StrEnum


class ApiCommand(StrEnum):
    EXECUTE = 'mcp.execute'
    HEALTH = 'mcp.health'
    LIST_COMMANDS = 'mcp.list_commands'


class PluginCommand(StrEnum):
    SCENE_GET_SCENE_INFO = 'scene.get_scene_info'
    SCENE_GET_SELECTION = 'scene.get_selection'
    SCENE_GET_NODE = 'scene.get_node'


PLUGIN_COMMANDS: frozenset[str] = frozenset(item.value for item in PluginCommand)
