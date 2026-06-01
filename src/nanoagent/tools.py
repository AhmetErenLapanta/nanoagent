from __future__ import annotations

import re
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from anthropic.types import ToolParam
from pydantic import BaseModel, Field

from .types import ToolCall, ToolResult


class ReadFileInput(BaseModel):
    path: str = Field(
        description="Path to the file to read (relative to cwd or absolute)."
    )


def _read_file(args: ReadFileInput) -> str:
    return Path(args.path).read_text()


class WriteFileInput(BaseModel):
    path: str = Field(
        description="Path to the file to write (relative to cwd or absolute). Parent directories must already exist."
    )
    content: str = Field(
        description="Full UTF-8 content to write. Overwrites the file if it exists."
    )


def _write_file(args: WriteFileInput) -> str:
    path = Path(args.path)
    path.write_text(args.content)
    return f"wrote {len(args.content)} chars to {path}"


class LsInput(BaseModel):
    path: str = Field(
        default=".",
        description="Directory to list. Defaults to the current working directory.",
    )


def _ls(args: LsInput) -> str:
    entries = sorted(Path(args.path).iterdir(), key=lambda p: p.name)
    return "\n".join(e.name + ("/" if e.is_dir() else "") for e in entries)


class EditFileInput(BaseModel):
    path: str = Field(description="Path to the file to edit.")
    old_str: str = Field(
        description="Exact text to find in the file. Must occur EXACTLY ONCE; include enough surrounding context (whitespace, neighboring lines) to make it unique."
    )
    new_str: str = Field(
        description="Replacement text. May be empty to delete old_str."
    )


def _edit_file(args: EditFileInput) -> str:
    path = Path(args.path)
    content = path.read_text()
    count = content.count(args.old_str)
    if count == 0:
        raise ValueError(f"old_str not found in {path}")
    if count > 1:
        raise ValueError(
            f"old_str appears {count} times in {path}, need uniquely-occurring snippet"
        )
    offset = content.index(args.old_str)
    path.write_text(content.replace(args.old_str, args.new_str, 1))
    return f"edited {path}: replaced {len(args.old_str)} chars at offset {offset}"


class GrepFilesInput(BaseModel):
    pattern: str = Field(
        description="Python regular expression to search for in file contents."
    )
    path: str = Field(
        default=".",
        description="Root directory to search recursively. Defaults to cwd.",
    )
    glob: str = Field(
        default="*",
        description="Filename glob filter applied to each candidate (e.g. '*.py', '*.md'). Defaults to all files.",
    )


_GREP_MATCH_CAP = 100


def _grep_files(args: GrepFilesInput) -> str:
    regex = re.compile(args.pattern)
    matches: list[str] = []
    total = 0
    for entry in sorted(Path(args.path).rglob(args.glob)):
        if not entry.is_file():
            continue
        try:
            text = entry.read_text()
        except (UnicodeDecodeError, OSError):
            continue
        for line_no, line in enumerate(text.splitlines(), start=1):
            if regex.search(line):
                total += 1
                if len(matches) < _GREP_MATCH_CAP:
                    matches.append(f"{entry}:{line_no}:{line}")
    if total == 0:
        return "no matches"
    if total > _GREP_MATCH_CAP:
        matches.append(f"... ({total - _GREP_MATCH_CAP} more matches)")
    return "\n".join(matches)


class BashInput(BaseModel):
    command: str = Field(
        description="Shell command to execute. Runs via /bin/sh with a 30 second timeout."
    )


def _bash(args: BashInput) -> str:
    try:
        result = subprocess.run(
            args.command,
            shell=True,
            capture_output=True,
            timeout=30,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = _decode_stream(exc.stdout)
        stderr = _decode_stream(exc.stderr)
        return f"exit timeout (30s)\nstdout (partial):\n{stdout}\nstderr (partial):\n{stderr}"
    stdout = _decode_stream(result.stdout)
    stderr = _decode_stream(result.stderr)
    return f"exit {result.returncode}\nstdout:\n{stdout}\nstderr:\n{stderr}"


def _decode_stream(stream: str | bytes | None) -> str:
    if stream is None:
        return ""
    if isinstance(stream, bytes):
        return stream.decode(errors="replace")
    return stream


@dataclass(frozen=True, slots=True)
class _Tool:
    description: str
    input_model: type[BaseModel]
    runner: Callable[[Any], str]


TOOLS: dict[str, _Tool] = {
    "read_file": _Tool(
        description="Read a UTF-8 text file and return its full contents. Use this to inspect a known file; prefer grep_files to search inside files and ls to list a directory.",
        input_model=ReadFileInput,
        runner=_read_file,
    ),
    "write_file": _Tool(
        description="Write UTF-8 text to a file, overwriting it entirely (parent directories are not created). Use only for creating a new file or replacing the whole contents; for in-place changes use edit_file.",
        input_model=WriteFileInput,
        runner=_write_file,
    ),
    "edit_file": _Tool(
        description="Surgically replace a unique snippet in a file. old_str must match EXACTLY ONCE; include surrounding lines or whitespace when needed to disambiguate. Prefer this over write_file for any change that preserves most of the existing content.",
        input_model=EditFileInput,
        runner=_edit_file,
    ),
    "ls": _Tool(
        description="List the entries of a directory. Directory entries are suffixed with '/'. Use for a quick directory listing; for content search use grep_files.",
        input_model=LsInput,
        runner=_ls,
    ),
    "grep_files": _Tool(
        description="Recursively search file contents under a directory for a Python regex, returning '{path}:{lineno}:{line}' for each match (capped at 100). Use this for content search instead of bash with find/grep; pass a glob like '*.py' to narrow the file set.",
        input_model=GrepFilesInput,
        runner=_grep_files,
    ),
    "bash": _Tool(
        description="Run a shell command via /bin/sh with a 30s timeout, returning exit code, stdout, and stderr. Each call runs in a fresh shell with no memory of the previous one, so chain dependent steps in one command (e.g. 'cd sub && ls'). Use for operations no other tool covers; prefer read_file/edit_file/grep_files for file work.",
        input_model=BashInput,
        runner=_bash,
    ),
}


def anthropic_tool_schemas() -> list[ToolParam]:
    return [
        ToolParam(
            name=name,
            description=tool.description,
            input_schema=tool.input_model.model_json_schema(),
        )
        for name, tool in TOOLS.items()
    ]


def dispatch(call: ToolCall) -> ToolResult:
    tool = TOOLS.get(call.name)
    if tool is None:
        return ToolResult(
            id=call.id, output=f"unknown tool: {call.name}", is_error=True
        )
    try:
        args = tool.input_model.model_validate(call.input)
        output = tool.runner(args)
    except Exception as exc:
        return ToolResult(
            id=call.id,
            output=_safe_utf8(f"{type(exc).__name__}: {exc}"),
            is_error=True,
        )
    return ToolResult(id=call.id, output=_safe_utf8(output), is_error=False)


def _safe_utf8(s: str) -> str:
    return s.encode("utf-8", errors="replace").decode("utf-8")
