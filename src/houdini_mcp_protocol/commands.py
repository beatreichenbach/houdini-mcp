from enum import StrEnum


class ApiCommand(StrEnum):
    EXECUTE = 'mcp.execute'
    HEALTH = 'mcp.health'
    LIST_COMMANDS = 'mcp.list_commands'


class PluginCommand(StrEnum):
    SCENE_GET_SCENE_INFO = 'scene.get_scene_info'


API_COMMANDS: frozenset[str] = frozenset(item.value for item in ApiCommand)
PLUGIN_COMMANDS: frozenset[str] = frozenset(item.value for item in PluginCommand)
