import logging

import pytest

from houdini_mcp.config import Settings


def test_settings_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('HOUDINI_MCP_PORT', '8200')
    monkeypatch.setenv('HOUDINI_MCP_TIMEOUT', '2.5')
    monkeypatch.setenv('HOUDINI_MCP_LOG_LEVEL', 'debug')

    settings = Settings.from_env()

    assert settings == Settings(port=8200, timeout=2.5, log_level=logging.DEBUG)
    assert settings.host == '127.0.0.1'


def test_invalid_log_level(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('HOUDINI_MCP_LOG_LEVEL', 'verbose')

    with pytest.raises(ValueError, match='invalid HOUDINI_MCP_LOG_LEVEL'):
        Settings.from_env()
