from pathlib import Path

import pytest

from houdini_mcp.prompts import build_instructions, load_content
from houdini_mcp.prompts.loader import BUILTIN_CONTENT_DIR


def test_load_builtin_content() -> None:
    content = load_content([BUILTIN_CONTENT_DIR])

    workflow = content.workflows['example']

    assert workflow.description == 'Minimal example workflow for authoring new content.'
    assert content.instructions.startswith('# Houdini MCP')
    assert 'housekeeping' in content.shared


def test_render_prompt() -> None:
    content = load_content([BUILTIN_CONTENT_DIR])

    text = content.workflows['example'].render('custom context', content.shared)

    assert 'custom context' in text
    assert 'Housekeeping' in text
    assert '{context}' not in text
    assert '{include:housekeeping}' not in text


def test_instructions_list_workflows() -> None:
    content = load_content([BUILTIN_CONTENT_DIR])

    instructions = build_instructions(content)

    assert 'example' in instructions
    assert 'houdini-mcp://workflows' in instructions


def test_user_content_overrides_builtin(tmp_path: Path) -> None:
    workflows = tmp_path / 'workflows'
    workflows.mkdir()
    (workflows / 'example.md').write_text(
        '# Local example\n\nLocal description.\n',
        encoding='utf-8',
    )

    content = load_content([tmp_path, BUILTIN_CONTENT_DIR])

    assert content.workflows['example'].description == 'Local description.'


def test_user_content_adds_workflow(tmp_path: Path) -> None:
    workflows = tmp_path / 'workflows'
    workflows.mkdir()
    (workflows / 'custom.md').write_text(
        '# Custom\n\nCustom workflow.\n\n{include:housekeeping}\n',
        encoding='utf-8',
    )

    content = load_content([tmp_path, BUILTIN_CONTENT_DIR])

    custom = content.workflows['custom']

    assert custom.description == 'Custom workflow.'
    assert 'Housekeeping' in custom.source(content.shared)


def test_user_instructions_override(tmp_path: Path) -> None:
    instructions = tmp_path / 'instructions'
    instructions.mkdir()
    (instructions / 'server.md').write_text('# Local instructions\n', encoding='utf-8')

    content = load_content([tmp_path, BUILTIN_CONTENT_DIR])

    assert content.instructions.strip() == '# Local instructions'


def test_invalid_workflow_name(tmp_path: Path) -> None:
    workflows = tmp_path / 'workflows'
    workflows.mkdir()
    (workflows / 'Bad Name.md').write_text('# Bad\n', encoding='utf-8')

    with pytest.raises(ValueError, match='invalid workflow or shared name'):
        load_content([tmp_path, BUILTIN_CONTENT_DIR])


def test_unknown_shared_fragment(tmp_path: Path) -> None:
    workflows = tmp_path / 'workflows'
    workflows.mkdir()
    (workflows / 'bad.md').write_text(
        '# Bad\n\n{include:missing}\n',
        encoding='utf-8',
    )

    content = load_content([tmp_path, BUILTIN_CONTENT_DIR])

    with pytest.raises(ValueError, match='unknown shared fragment'):
        content.workflows['bad'].render('', content.shared)
