import sys
from pathlib import Path

import pytest

from houdini_mcp.__main__ import _validate_content_or_exit, main
from houdini_mcp.prompts import load_content


def test_content_path_ignores_invalid_server_settings(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv('HOUDINI_MCP_PORT', 'not-a-port')
    monkeypatch.setattr(sys, 'argv', ['houdini-mcp', 'content', 'path'])

    main()

    output = Path(capsys.readouterr().out.strip())

    assert output.name == 'content'
    assert output.parent.name == 'houdini_mcp'


def test_validate_rejects_unknown_shared_fragment(tmp_path: Path) -> None:
    workflows = tmp_path / 'workflows'
    workflows.mkdir()
    (workflows / 'bad.md').write_text(
        '# Bad\n\n{include:missing}\n',
        encoding='utf-8',
    )

    content = load_content([tmp_path])

    with pytest.raises(SystemExit):
        _validate_content_or_exit(content)
