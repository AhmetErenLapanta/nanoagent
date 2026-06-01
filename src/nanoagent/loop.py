from __future__ import annotations

from collections.abc import Generator

from anthropic import Anthropic
from anthropic.types import (
    Message,
    MessageParam,
    TextBlockParam,
    ToolResultBlockParam,
    ToolUseBlockParam,
)

from .tools import anthropic_tool_schemas, dispatch
from .types import (
    AgentError,
    AgentEvent,
    AssistantText,
    Thinking,
    ToolCall,
    ToolResult,
    TurnDone,
)


def run(
    messages: list[MessageParam],
    *,
    client: Anthropic,
    model: str,
    system: str,
    max_iterations: int = 25,
) -> Generator[AgentEvent, None, None]:
    schemas = anthropic_tool_schemas()

    for _ in range(max_iterations):
        yield Thinking()
        response = client.messages.create(
            model=model,
            system=system,
            max_tokens=4096,
            tools=schemas,
            messages=messages,
        )

        events, blocks, calls = _process_response(response)
        yield from events
        messages.append({"role": "assistant", "content": blocks})

        if response.stop_reason != "tool_use":
            yield TurnDone()
            return

        results = [dispatch(call) for call in calls]
        yield from results
        messages.append(
            {"role": "user", "content": [_to_result_block(r) for r in results]}
        )

    yield AgentError(message=f"max_iterations ({max_iterations}) exceeded")


def _process_response(
    response: Message,
) -> tuple[
    list[AgentEvent],
    list[TextBlockParam | ToolUseBlockParam],
    list[ToolCall],
]:
    events: list[AgentEvent] = []
    blocks: list[TextBlockParam | ToolUseBlockParam] = []
    calls: list[ToolCall] = []
    for block in response.content:
        if block.type == "text":
            events.append(AssistantText(text=block.text))
            blocks.append(_to_text_block(block.text))
        elif block.type == "tool_use":
            call = ToolCall(id=block.id, name=block.name, input=dict(block.input))
            events.append(call)
            calls.append(call)
            blocks.append(_to_tool_use_block(call))
    return events, blocks, calls


def _to_text_block(text: str) -> TextBlockParam:
    return {"type": "text", "text": text}


def _to_tool_use_block(call: ToolCall) -> ToolUseBlockParam:
    return {
        "type": "tool_use",
        "id": call.id,
        "name": call.name,
        "input": call.input,
    }


def _to_result_block(result: ToolResult) -> ToolResultBlockParam:
    return {
        "type": "tool_result",
        "tool_use_id": result.id,
        "content": result.output,
        "is_error": result.is_error,
    }
