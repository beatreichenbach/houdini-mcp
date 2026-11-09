import sys
import types

from houdini_mcp_plugin import dispatcher
from houdini_mcp_protocol import PLUGIN_COMMANDS


def test_all_commands_registered() -> None:
    hou = types.ModuleType('hou')
    hou.__dict__['folderType'] = types.SimpleNamespace(
        Tabs='Tabs', Collapsible='Collapsible', Simple='Simple'
    )
    sys.modules['hou'] = hou

    import houdini_mcp_plugin.commands  # noqa: F401

    assert set(dispatcher.list_commands()) == set(PLUGIN_COMMANDS)
