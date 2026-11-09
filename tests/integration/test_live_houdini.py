import asyncio
import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp_types import TextResourceContents

pytestmark = pytest.mark.integration


def _call(port: int, name: str, **kwargs: object) -> dict[str, Any]:
    body = urllib.parse.urlencode({'json': json.dumps([name, [], kwargs])}).encode()
    request = urllib.request.Request(
        f'http://127.0.0.1:{port}/api',
        data=body,
        headers={
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-Houdini-MCP': '1',
        },
    )
    with urllib.request.urlopen(request, timeout=2) as response:
        return json.loads(response.read().decode())


def _plugin_port() -> int:
    for port in range(8100, 8116):
        try:
            health = _call(port, 'mcp.health')
        except (OSError, ValueError):
            continue
        if health.get('status') == 'ok':
            return port
    pytest.skip('no running Houdini MCP plugin')


async def _read_resources(uris: list[str]) -> list[Any]:
    script = Path(sys.executable).with_name(
        'houdini-mcp.exe' if os.name == 'nt' else 'houdini-mcp'
    )
    params = StdioServerParameters(command=str(script))
    async with (
        stdio_client(params) as (read, write),
        ClientSession(read, write) as session,
    ):
        await session.initialize()
        payloads: list[Any] = []
        for uri in uris:
            result = await session.read_resource(uri)
            content = result.contents[0]
            if not isinstance(content, TextResourceContents):
                raise TypeError(f'expected text resource for {uri}')
            payloads.append(json.loads(content.text))
        return payloads


def test_get_scene_info() -> None:
    port = _plugin_port()
    response = _call(
        port,
        'mcp.execute',
        command='scene.get_scene_info',
        params={},
    )

    assert response['status'] == 'success'
    assert 'houdini_version' in response['data']


def test_scene_resources() -> None:
    _plugin_port()

    scene, selection, nodes, node = asyncio.run(
        _read_resources(
            [
                'houdini-mcp://scene',
                'houdini-mcp://scene/selection',
                'houdini-mcp://scene/nodes',
                'houdini-mcp://scene/nodes/obj',
            ]
        )
    )

    assert 'houdini_version' in scene
    assert isinstance(selection['nodes'], list)
    assert nodes['path'] == '/'
    assert node['path'] == '/obj'
