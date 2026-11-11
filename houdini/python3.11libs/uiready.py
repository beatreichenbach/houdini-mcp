import logging

try:
    from houdini_mcp_plugin.host import startup

    if startup.autostart_enabled():
        startup.ensure_running()
except Exception as e:
    logging.getLogger(__name__).exception('%s', e)
