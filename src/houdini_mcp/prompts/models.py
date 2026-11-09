from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_INCLUDE_PATTERN = re.compile(r'\{include:([a-z0-9-]+)\}')


@dataclass(frozen=True)
class Workflow:
    name: str
    description: str
    path: Path
    text: str

    def source(self, shared: dict[str, str]) -> str:
        """Return the workflow text with shared fragments resolved."""

        return _resolve_includes(self.text, shared, {self.name})

    def render(self, context: str, shared: dict[str, str]) -> str:
        """Return the workflow prompt with includes and context resolved."""

        text = self.source(shared)
        if '{context}' in text:
            return text.replace('{context}', context)
        if context:
            return f'{text.rstrip()}\n\nContext:\n{context}'
        return text


@dataclass(frozen=True)
class Content:
    instructions: str
    shared: dict[str, str]
    workflows: dict[str, Workflow]


def _resolve_includes(
    text: str,
    shared: dict[str, str],
    seen: set[str],
) -> str:
    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        if name in seen:
            raise ValueError(f'cyclic include: {name!r}')
        if name not in shared:
            raise ValueError(f'unknown shared fragment: {name!r}')
        return _resolve_includes(shared[name], shared, seen | {name})

    return _INCLUDE_PATTERN.sub(replace, text)
