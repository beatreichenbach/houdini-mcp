from pathlib import Path

import pytest

from houdini_mcp.prompts import build_instructions, load_content
from houdini_mcp.prompts.loader import BUILTIN_CONTENT_DIR


def _write(root: Path, kind: str, name: str, text: str) -> None:
    directory = root / kind
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f'{name}.md').write_text(text, encoding='utf-8')


def test_builtin_content_loads() -> None:
    content = load_content([BUILTIN_CONTENT_DIR])

    assert content.instructions.strip()


def test_workflow_description_and_render(tmp_path: Path) -> None:
    _write(tmp_path, 'shared', 'cleanup', '## Cleanup\n')
    _write(
        tmp_path,
        'workflows',
        'demo',
        '# Demo\n\nDemo workflow.\n\n{include:cleanup}\n\n{context}\n',
    )

    content = load_content([tmp_path])
    workflow = content.workflows['demo']

    assert workflow.description == 'Demo workflow.'
    assert 'Cleanup' in workflow.render('custom context', content.shared)


def test_render_resolves_placeholders(tmp_path: Path) -> None:
    _write(
        tmp_path,
        'workflows',
        'demo',
        '# Demo\n\nDemo workflow.\n\n{include:cleanup}\n\n{context}\n',
    )
    _write(tmp_path, 'shared', 'cleanup', '## Cleanup\n')

    content = load_content([tmp_path])
    text = content.workflows['demo'].render('custom context', content.shared)

    assert 'custom context' in text
    assert '{context}' not in text
    assert '{include:cleanup}' not in text


def test_render_appends_context_when_placeholder_missing(tmp_path: Path) -> None:
    _write(tmp_path, 'workflows', 'demo', '# Demo\n\nDemo workflow.\n')

    content = load_content([tmp_path])
    text = content.workflows['demo'].render('custom context', content.shared)

    assert text.endswith('Context:\ncustom context')


def test_instructions_include_workflow_index(tmp_path: Path) -> None:
    _write(tmp_path, 'workflows', 'demo', '# Demo\n\nDemo workflow.\n')

    content = load_content([tmp_path])
    instructions = build_instructions(content)

    assert 'demo: Demo workflow.' in instructions


def test_instructions_omit_empty_workflow_index(tmp_path: Path) -> None:
    _write(tmp_path, 'instructions', '00-overview', '# Rules\n')

    content = load_content([tmp_path])

    assert 'Available workflows' not in build_instructions(content)


def test_earlier_root_wins(tmp_path: Path) -> None:
    first = tmp_path / 'first'
    second = tmp_path / 'second'
    _write(first, 'workflows', 'demo', '# First\n\nFirst workflow.\n')
    _write(second, 'workflows', 'demo', '# Second\n\nSecond workflow.\n')
    _write(first, 'instructions', '00-overview', '# First instructions\n')
    _write(second, 'instructions', '00-overview', '# Second instructions\n')

    content = load_content([first, second])

    assert content.workflows['demo'].description == 'First workflow.'
    assert content.instructions.strip() == '# First instructions'


def test_roots_add_content(tmp_path: Path) -> None:
    first = tmp_path / 'first'
    second = tmp_path / 'second'
    _write(first, 'workflows', 'one', '# One\n\nOne workflow.\n')
    _write(second, 'workflows', 'two', '# Two\n\nTwo workflow.\n')

    content = load_content([first, second])

    assert set(content.workflows) == {'one', 'two'}


def test_invalid_workflow_name(tmp_path: Path) -> None:
    _write(tmp_path, 'workflows', 'Bad Name', '# Bad\n')

    with pytest.raises(ValueError, match='invalid workflow or shared name'):
        load_content([tmp_path])


def test_unknown_shared_fragment(tmp_path: Path) -> None:
    _write(tmp_path, 'workflows', 'bad', '# Bad\n\n{include:missing}\n')

    content = load_content([tmp_path])

    with pytest.raises(ValueError, match='unknown shared fragment'):
        content.workflows['bad'].render('', content.shared)
