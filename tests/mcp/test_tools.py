import asyncio
import logging
from types import SimpleNamespace
from typing import cast

import pytest
from mcp.server.mcpserver.exceptions import ToolError

from houdini_mcp.config import Settings
from houdini_mcp.errors import (
    HoudiniCommandError,
    HoudiniConnectionError,
    HoudiniMCPError,
)
from houdini_mcp.server import create_server
from houdini_mcp.tools.context import BridgeContext, run_command
from houdini_mcp.tools.lops import get_usd_material_textures
from houdini_mcp.tools.nodes import create_node, list_children, list_network_boxes
from houdini_mcp.tools.parameters import set_parameter


class FailingBridge:
    def __init__(self, error: Exception) -> None:
        self._error = error

    async def execute(
        self,
        command: str,
        params: dict[str, object] | None = None,
    ) -> object:
        raise self._error


class RecordingBridge:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object] | None]] = []

    async def execute(
        self,
        command: str,
        params: dict[str, object] | None = None,
        timeout: float | None = None,
    ) -> dict[str, object]:
        self.calls.append((command, params))
        return {}


def _context(bridge: object) -> BridgeContext:
    request_context = SimpleNamespace(lifespan_context={'bridge': bridge})
    return cast(BridgeContext, SimpleNamespace(request_context=request_context))


def test_server_registers_initial_tools() -> None:
    server = create_server(Settings(port=8100, timeout=1.0, log_level=logging.INFO))

    names = {tool.name for tool in asyncio.run(server.list_tools())}

    assert {
        'get_scene_info',
        'create_node',
        'delete_sticky_notes',
        'set_parameter',
        'build_network',
        'get_geometry_info',
        'search_help',
        'capture_screenshot',
    } <= names


def test_create_node_sends_expected_params() -> None:
    bridge = RecordingBridge()

    asyncio.run(_create_node(_context(bridge)))

    assert bridge.calls == [
        ('nodes.create_node', {'parent_path': '/obj', 'node_type': 'box', 'name': 'b'})
    ]


def test_set_parameter_sends_expected_params() -> None:
    bridge = RecordingBridge()

    asyncio.run(_set_parameter(_context(bridge)))

    assert bridge.calls == [
        (
            'parameters.set_parameter',
            {
                'node_path': '/obj/geo1',
                'parm_name': 'tx',
                'value': 2.5,
                'override_expression': False,
                'run_callbacks': False,
            },
        )
    ]


async def _create_node(ctx: BridgeContext) -> object:
    return await create_node(ctx, '/obj', 'box', name='b')


async def _set_parameter(ctx: BridgeContext) -> object:
    return await set_parameter(ctx, '/obj/geo1', 'tx', 2.5)


def test_list_network_boxes_sends_expected_params() -> None:
    bridge = RecordingBridge()

    asyncio.run(list_network_boxes(_context(bridge), '/stage'))

    assert bridge.calls == [('nodes.list_network_boxes', {'parent_path': '/stage'})]


def test_list_children_sends_dive_target_flag() -> None:
    bridge = RecordingBridge()

    asyncio.run(
        list_children(_context(bridge), '/stage/componentgeometry6', dive_target=True)
    )

    assert bridge.calls == [
        (
            'nodes.list_children',
            {
                'parent_path': '/stage/componentgeometry6',
                'recursive': False,
                'dive_target': True,
            },
        )
    ]


def test_get_usd_material_textures_sends_expected_params() -> None:
    bridge = RecordingBridge()

    asyncio.run(
        get_usd_material_textures(
            _context(bridge), '/stage/Curb01', include_prototypes=True
        )
    )

    command, params = bridge.calls[0]
    assert command == 'lops.get_usd_material_textures'
    assert params is not None
    assert params['node_path'] == '/stage/Curb01'
    assert params['include_prototypes'] is True
    assert params['traverse_instance_proxies'] is True


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
