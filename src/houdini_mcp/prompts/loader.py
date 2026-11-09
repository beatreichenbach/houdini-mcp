from __future__ import annotations

import os
import re
from pathlib import Path

import platformdirs

from .. import constants
from .models import Content, Workflow

BUILTIN_CONTENT_DIR = Path(__file__).resolve().parent.parent / 'content'

_NAME_PATTERN = re.compile(r'^[a-z0-9][a-z0-9-]*$')


def load_content(roots: list[Path] | None = None) -> Content:
    """Load content from the given roots, with earlier roots taking priority."""

    roots = content_roots() if roots is None else roots
    instructions: dict[str, str] = {}
    shared: dict[str, str] = {}
    workflows: dict[str, Workflow] = {}

    for root in roots:
        for path in _md_files(root / 'instructions'):
            instructions.setdefault(path.stem, path.read_text(encoding='utf-8'))
        for path in _md_files(root / 'shared'):
            shared.setdefault(_valid_name(path), path.read_text(encoding='utf-8'))
        for path in _md_files(root / 'workflows'):
            name = _valid_name(path)
            if name in workflows:
                continue
            text = path.read_text(encoding='utf-8')
            workflows[name] = Workflow(
                name=name,
                description=_description(text, name),
                path=path,
                text=text,
            )

    return Content(
        instructions='\n\n'.join(instructions[key] for key in sorted(instructions)),
        shared=shared,
        workflows=dict(sorted(workflows.items())),
    )


def content_roots() -> list[Path]:
    """Return user content roots followed by the built-in root."""

    roots = [local_content_dir()]
    value = os.getenv(constants.CONTENT)
    if value:
        roots.extend(
            Path(part).expanduser() for part in value.split(os.pathsep) if part
        )
    roots.append(BUILTIN_CONTENT_DIR)
    return roots


def local_content_dir() -> Path:
    """Return the default local content directory."""

    return Path(platformdirs.user_config_dir('houdini_mcp')) / 'content'


def _md_files(root: Path) -> list[Path]:
    if not root.is_dir():
        return []
    return sorted(root.glob('*.md'))


def _valid_name(path: Path) -> str:
    name = path.stem
    if not _NAME_PATTERN.fullmatch(name):
        raise ValueError(f'invalid workflow or shared name in {path}: {name!r}')
    return name


def _description(text: str, fallback: str) -> str:
    for line in text.splitlines():
        value = line.strip()
        if not value or value.startswith('#'):
            continue
        return value
    return fallback
