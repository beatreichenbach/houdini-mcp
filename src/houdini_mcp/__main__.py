from __future__ import annotations

import argparse
import contextlib
import logging
from pathlib import Path

from .config import Settings
from .install import client_config, install
from .logging_config import configure_logging
from .server import create_server

logger = logging.getLogger(__name__)


def main() -> None:
    """Run the MCP server or install the Houdini package."""

    parser = argparse.ArgumentParser(prog='houdini-mcp')
    parser.add_argument('command', nargs='?', choices=('run', 'install'), default='run')
    parser.add_argument('--packages-dir', type=Path)
    args = parser.parse_args()

    settings = Settings.from_env()
    configure_logging(settings.log_level)

    if args.command == 'install':
        try:
            paths = install(args.packages_dir)
        except RuntimeError as exc:
            logger.error('%s', exc)
            raise SystemExit(1) from exc
        for path in paths:
            logger.info('Wrote %s', path)
        print(client_config())
        return

    logger.info('Starting Houdini MCP server')
    server = create_server(settings)
    with contextlib.suppress(KeyboardInterrupt):
        server.run(transport='stdio')


if __name__ == '__main__':
    main()
