import logging

try:
    from houdini_mcp_plugin import startup

    if startup.autostart_enabled():
        startup.ensure_running()
except Exception:
    logging.getLogger(__name__).exception('Failed to start Houdini MCP plugin')
