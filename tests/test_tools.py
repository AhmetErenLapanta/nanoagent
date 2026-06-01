from __future__ import annotations

from pathlib import Path

from nanoagent.tools import dispatch
from nanoagent.types import ToolCall


def test_dispatch_happy_path(tmp_path: Path) -> None:
    target = tmp_path / "x.txt"
    target.write_text("hello")

    result = dispatch(ToolCall(id="c1", name="read_file", input={"path": str(target)}))

    assert result.id == "c1"
    assert result.is_error is False
    assert result.output == "hello"


def test_dispatch_unknown_tool() -> None:
    result = dispatch(ToolCall(id="c1", name="does_not_exist", input={}))

    assert result.is_error is True
    assert "unknown tool" in result.output


def test_dispatch_validation_error() -> None:
    result = dispatch(ToolCall(id="c1", name="read_file", input={}))

    assert result.is_error is True
    assert "ValidationError" in result.output


def test_dispatch_runner_exception(tmp_path: Path) -> None:
    missing = tmp_path / "nope.txt"

    result = dispatch(ToolCall(id="c1", name="read_file", input={"path": str(missing)}))

    assert result.is_error is True
    assert "FileNotFoundError" in result.output


def _bash(command: str) -> str:
    result = dispatch(ToolCall(id="c1", name="bash", input={"command": command}))
    assert result.is_error is False
    return result.output


def test_bash_non_utf8_output_is_safe() -> None:
    output = _bash(r"printf '\xc4\xc4 hi'")

    output.encode("utf-8")
    assert "hi" in output


def test_edit_file_happy_path(tmp_path: Path) -> None:
    target = tmp_path / "x.txt"
    target.write_text("alpha beta gamma")

    result = dispatch(
        ToolCall(
            id="c1",
            name="edit_file",
            input={"path": str(target), "old_str": "beta", "new_str": "BETA"},
        )
    )

    assert result.is_error is False
    assert "replaced 4 chars at offset 6" in result.output
    assert target.read_text() == "alpha BETA gamma"


def test_edit_file_not_found(tmp_path: Path) -> None:
    target = tmp_path / "x.txt"
    target.write_text("alpha beta gamma")

    result = dispatch(
        ToolCall(
            id="c1",
            name="edit_file",
            input={"path": str(target), "old_str": "delta", "new_str": "X"},
        )
    )

    assert result.is_error is True
    assert "old_str not found" in result.output
    assert str(target) in result.output
    assert target.read_text() == "alpha beta gamma"


def test_edit_file_ambiguous(tmp_path: Path) -> None:
    target = tmp_path / "x.txt"
    target.write_text("foo\nfoo\n")

    result = dispatch(
        ToolCall(
            id="c1",
            name="edit_file",
            input={"path": str(target), "old_str": "foo", "new_str": "bar"},
        )
    )

    assert result.is_error is True
    assert "appears 2 times" in result.output
    assert target.read_text() == "foo\nfoo\n"


def test_grep_files_matches(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("import os\nx = 1\nimport sys\n")
    (tmp_path / "b.py").write_text("y = 2\nimport json\n")
    (tmp_path / "c.txt").write_text("import nope\n")

    result = dispatch(
        ToolCall(
            id="c1",
            name="grep_files",
            input={"pattern": r"^import ", "path": str(tmp_path), "glob": "*.py"},
        )
    )

    assert result.is_error is False
    lines = result.output.splitlines()
    assert f"{tmp_path / 'a.py'}:1:import os" in lines
    assert f"{tmp_path / 'a.py'}:3:import sys" in lines
    assert f"{tmp_path / 'b.py'}:2:import json" in lines
    assert not any("c.txt" in line for line in lines)


def test_grep_files_no_matches(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("hello world\n")

    result = dispatch(
        ToolCall(
            id="c1",
            name="grep_files",
            input={"pattern": "nope", "path": str(tmp_path)},
        )
    )

    assert result.is_error is False
    assert result.output == "no matches"
