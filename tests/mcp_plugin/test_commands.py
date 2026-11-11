import sys
import types
from unittest.mock import MagicMock

from houdini_mcp_plugin.host import dispatcher
from houdini_mcp_protocol import PLUGIN_COMMANDS


class _Hou(types.ModuleType):
    def __getattr__(self, name: str) -> MagicMock:
        value = MagicMock(name=name)
        setattr(self, name, value)
        return value


def test_all_commands_registered() -> None:
    hou = _Hou('hou')
    hou.__dict__['folderType'] = types.SimpleNamespace(
        Tabs='Tabs', Collapsible='Collapsible', Simple='Simple'
    )
    sys.modules['hou'] = hou

    import houdini_mcp_plugin.runtime.commands  # noqa: F401

    assert set(dispatcher.list_commands()) == set(PLUGIN_COMMANDS)
