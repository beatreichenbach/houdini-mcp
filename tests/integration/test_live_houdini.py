import json
import urllib.parse
import urllib.request
from typing import Any

import pytest

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


def test_get_scene_info() -> None:
    port = _plugin_port()
    response = _call(
        port,
        'mcp.execute',
        command='scene.get_scene_info',
        params={},
        request_id='test',
    )

    assert response['status'] == 'success'
    assert 'houdini_version' in response['data']
