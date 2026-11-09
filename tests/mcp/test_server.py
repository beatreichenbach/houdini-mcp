import logging

import pytest
from mcp.server.mcpserver import MCPServer

from houdini_mcp.config import Settings
from houdini_mcp.server import create_server


def test_create_server() -> None:
    settings = Settings(
        host='localhost', port=8100, timeout=1.0, log_level=logging.INFO
    )

    server = create_server(settings)

    assert isinstance(server, MCPServer)


def test_settings_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('HOUDINI_MCP_HOST', 'example')
    monkeypatch.setenv('HOUDINI_MCP_PORT', '8200')
    monkeypatch.setenv('HOUDINI_MCP_TIMEOUT', '2.5')
    monkeypatch.setenv('HOUDINI_MCP_LOG_LEVEL', 'debug')

    settings = Settings.from_env()

    assert settings == Settings(
        host='example', port=8200, timeout=2.5, log_level=logging.DEBUG
    )


def test_invalid_log_level(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('HOUDINI_MCP_LOG_LEVEL', 'verbose')

    with pytest.raises(ValueError, match='invalid HOUDINI_MCP_LOG_LEVEL'):
        Settings.from_env()
