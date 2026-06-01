from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

from anthropic import Anthropic

from nanoagent.loop import run
from nanoagent.types import (
    AgentError,
    AssistantText,
    Thinking,
    ToolCall,
    ToolResult,
    TurnDone,
)


def _text_block(text: str) -> SimpleNamespace:
    return SimpleNamespace(type="text", text=text)


def _tool_use_block(id: str, name: str, input: dict[str, Any]) -> SimpleNamespace:
    return SimpleNamespace(type="tool_use", id=id, name=name, input=input)


def _response(content: list[Any], stop_reason: str) -> SimpleNamespace:
    return SimpleNamespace(content=content, stop_reason=stop_reason)


class _FakeMessages:
    def __init__(self, responses: list[SimpleNamespace]) -> None:
        self._responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> SimpleNamespace:
        self.calls.append(kwargs)
        return self._responses.pop(0)


class _FakeClient:
    def __init__(self, responses: list[SimpleNamespace]) -> None:
        self.messages = _FakeMessages(responses)


def _client(responses: list[SimpleNamespace]) -> Anthropic:
    return cast(Anthropic, _FakeClient(responses))


def test_run_text_only() -> None:
    client = _client([_response([_text_block("hi")], "end_turn")])
    messages: list[Any] = [{"role": "user", "content": "hello"}]

    events = list(run(messages, client=client, model="m", system="s"))

    assert events == [Thinking(), AssistantText(text="hi"), TurnDone()]
    assert len(messages) == 2
    assert messages[1]["role"] == "assistant"


def test_run_tool_then_text(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("x")
    client = _client(
        [
            _response(
                [_tool_use_block("call1", "ls", {"path": str(tmp_path)})],
                "tool_use",
            ),
            _response([_text_block("found a.txt")], "end_turn"),
        ]
    )
    messages: list[Any] = [{"role": "user", "content": f"list {tmp_path}"}]

    events = list(run(messages, client=client, model="m", system="s"))

    assert events[0] == Thinking()
    assert events[1] == ToolCall(id="call1", name="ls", input={"path": str(tmp_path)})
    assert isinstance(events[2], ToolResult)
    assert events[2].id == "call1"
    assert events[2].is_error is False
    assert "a.txt" in events[2].output
    assert events[3] == Thinking()
    assert events[4] == AssistantText(text="found a.txt")
    assert events[5] == TurnDone()
    assert len(messages) == 4
    assert messages[1]["role"] == "assistant"
    assert messages[2]["role"] == "user"
    assert messages[3]["role"] == "assistant"


def test_run_max_iterations() -> None:
    looping_response = _response(
        [_tool_use_block("c", "ls", {"path": "."})],
        "tool_use",
    )
    client = _client([looping_response] * 5)
    messages: list[Any] = [{"role": "user", "content": "loop"}]

    events = list(run(messages, client=client, model="m", system="s", max_iterations=3))

    assert isinstance(events[-1], AgentError)
    assert "max_iterations" in events[-1].message
