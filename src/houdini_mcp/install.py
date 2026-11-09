from __future__ import annotations

import json
import os
import platform
import sys
from pathlib import Path

from . import constants

PACKAGE_DIR = 'houdini'
PACKAGE_FILE = 'houdini_mcp.json'
HOUDINI_USER_PREF_DIR = 'HOUDINI_USER_PREF_DIR'


def install(packages_dir: Path | None = None) -> list[Path]:
    """Write the Houdini package file into the detected packages directories."""

    repo_root = _repo_root()
    targets = _packages_dirs(packages_dir)
    if not targets:
        raise RuntimeError(_missing_packages_message())

    content = _package_json(repo_root)
    written: list[Path] = []
    for target in targets:
        target.mkdir(parents=True, exist_ok=True)
        path = target / PACKAGE_FILE
        path.write_text(content, encoding='utf-8')
        written.append(path)
    return written


def uninstall(packages_dir: Path | None = None) -> list[Path]:
    """Remove the Houdini package file from the detected packages directories."""

    removed: list[Path] = []
    for target in _packages_dirs(packages_dir):
        path = target / PACKAGE_FILE
        try:
            path.unlink()
        except FileNotFoundError:
            continue
        removed.append(path)
    return removed


def client_config() -> str:
    """Return the MCP client configuration as JSON."""

    return json.dumps(
        {
            'mcpServers': {
                'houdini': {
                    'command': sys.executable,
                    'args': ['-m', 'houdini_mcp'],
                }
            }
        },
        indent=2,
    )


def _repo_root() -> Path:
    """Return the repository root for the editable install."""

    root = Path(__file__).resolve().parents[2]
    if not (root / PACKAGE_DIR).is_dir():
        raise RuntimeError(
            'houdini-mcp must be installed editable from its repository '
            'so the houdini package directory is available'
        )
    return root


def _package_json(repo_root: Path) -> str:
    """Return the Houdini package file contents."""

    data = {
        'env': [
            {constants.HOUDINI_MCP: repo_root.as_posix()},
            {'PYTHONPATH': f'${constants.HOUDINI_MCP}/src'},
        ],
        'path': f'${constants.HOUDINI_MCP}/{PACKAGE_DIR}',
    }
    return json.dumps(data, indent=4) + '\n'


def _packages_dirs(packages_dir: Path | None) -> list[Path]:
    """Return the packages directories to install into."""

    if packages_dir is not None:
        return [packages_dir]

    pref = os.getenv(HOUDINI_USER_PREF_DIR)
    if pref:
        return [Path(pref) / 'packages']

    return [version_dir / 'packages' for version_dir in _version_dirs()]


def _version_dirs() -> list[Path]:
    """Return existing Houdini user preference directories."""

    home = Path.home()
    system = platform.system()

    if system == 'Darwin':
        root = home / 'Library' / 'Preferences' / 'houdini'
        return sorted(path for path in root.glob('[0-9]*.[0-9]*') if path.is_dir())

    if system == 'Windows':
        roots = [home / 'Documents', home / 'OneDrive' / 'Documents']
        return sorted(
            path
            for root in roots
            if root.is_dir()
            for path in root.glob('houdini[0-9]*')
            if path.is_dir()
        )

    return sorted(path for path in home.glob('houdini[0-9]*') if path.is_dir())


def _missing_packages_message() -> str:
    """Return the platform-specific missing-packages hint."""

    system = platform.system()

    if system == 'Darwin':
        example = '~/Library/Preferences/houdini/<version>/packages'
    elif system == 'Windows':
        example = '~/Documents/houdini<version>/packages'
    else:
        example = '~/houdini<version>/packages'

    return (
        f'no houdini packages directory found; create {example} or pass --packages-dir'
    )
