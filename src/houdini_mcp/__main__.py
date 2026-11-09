from __future__ import annotations

import argparse
import contextlib
import logging
from pathlib import Path

from .config import Settings
from .install import client_config, install, uninstall
from .logging_config import configure_logging
from .prompts import Content, load_content, local_content_dir
from .server import create_server

logger = logging.getLogger(__name__)


def _load_content_or_exit() -> Content:
    try:
        return load_content()
    except ValueError as exc:
        logger.error('%s', exc)
        raise SystemExit(1) from exc


def _validate_content_or_exit(content: Content) -> None:
    try:
        for workflow in content.workflows.values():
            workflow.source(content.shared)
    except ValueError as exc:
        logger.error('%s', exc)
        raise SystemExit(1) from exc


def main() -> None:
    """Run the MCP server or install the Houdini package."""

    parser = argparse.ArgumentParser(prog='houdini-mcp')
    parser.add_argument(
        'command',
        nargs='?',
        choices=('run', 'install', 'uninstall', 'content'),
        default='run',
    )
    parser.add_argument(
        'content_command',
        nargs='?',
        choices=('path', 'list', 'validate'),
        default='list',
    )
    parser.add_argument('--packages-dir', type=Path)
    args = parser.parse_args()

    if args.command != 'run':
        configure_logging(logging.INFO)

    if args.command == 'content':
        if args.content_command == 'path':
            print(local_content_dir())
            return
        content = _load_content_or_exit()
        if args.content_command == 'list':
            for workflow in content.workflows.values():
                print(f'{workflow.name}\t{workflow.description}\t{workflow.path}')
            return
        _validate_content_or_exit(content)
        logger.info(
            'Content validation passed: %d workflows, %d shared files',
            len(content.workflows),
            len(content.shared),
        )
        return

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

    if args.command == 'uninstall':
        paths = uninstall(args.packages_dir)
        if not paths:
            logger.warning('No Houdini package file found')
        for path in paths:
            logger.info('Removed %s', path)
        return

    settings = Settings.from_env()
    configure_logging(settings.log_level)
    logger.info('Starting Houdini MCP server')
    server = create_server(settings)
    with contextlib.suppress(KeyboardInterrupt):
        server.run(transport='stdio')


if __name__ == '__main__':
    main()
