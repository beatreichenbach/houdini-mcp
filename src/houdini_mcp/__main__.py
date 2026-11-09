from __future__ import annotations

import contextlib
import logging

from .config import Settings
from .logging_config import configure_logging
from .server import create_server

logger = logging.getLogger(__name__)


def main() -> None:
    settings = Settings.from_env()
    configure_logging(settings.log_level)
    logger.info('Starting Houdini MCP server')
    server = create_server(settings)
    with contextlib.suppress(KeyboardInterrupt):
        server.run(transport='stdio')


if __name__ == '__main__':
    main()
