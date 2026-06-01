from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class Thinking:
    pass


@dataclass(frozen=True, slots=True)
class AssistantText:
    text: str


@dataclass(frozen=True, slots=True)
class ToolCall:
    id: str
    name: str
    input: dict[str, Any]


@dataclass(frozen=True, slots=True)
class ToolResult:
    id: str
    output: str
    is_error: bool


@dataclass(frozen=True, slots=True)
class TurnDone:
    pass


@dataclass(frozen=True, slots=True)
class AgentError:
    message: str


AgentEvent = Thinking | AssistantText | ToolCall | ToolResult | TurnDone | AgentError
