import asyncio

from mcp.server.mcpserver import MCPServer

from houdini_mcp.bridge import HoudiniBridge
from houdini_mcp.resources.scene import register_scene_resources


def test_scene_resources_registered() -> None:
    server: MCPServer[dict[str, HoudiniBridge]] = MCPServer(name='test')

    register_scene_resources(server)

    resources = {str(resource.uri) for resource in asyncio.run(server.list_resources())}
    templates = {
        template.uri_template
        for template in asyncio.run(server.list_resource_templates())
    }

    assert resources == {
        'houdini-mcp://scene',
        'houdini-mcp://scene/selection',
        'houdini-mcp://scene/nodes',
    }
    assert templates == {'houdini-mcp://scene/nodes{+path}'}
