# nanoagent

A minimal, lean AI coding agent in a few hundred lines of Python.

**Agents are not magic.** Behind the complex frameworks, an agent is fundamentally three things:
a loop, a tool dispatch table, and an event stream. The model never touches your
filesystem — it only *asks* for things to happen, and your code makes them happen.
`nanoagent` is the smallest honest implementation of that idea, built directly on the
Anthropic API with no framework in between.

## Features

- **6 hardcoded tools** — `read_file`, `write_file`, `edit_file`, `ls`, `grep_files`, `bash`
- **Typed tool I/O** — Pydantic v2 models generate the JSON Schema sent to the model
- **Generator event stream** — the loop yields events (`AssistantText`, `ToolCall`, `ToolResult`, …); the CLI just renders them
- **Append-only conversation state** — historical messages are never mutated
- **A small, live CLI** — Rich-powered: a thinking spinner, styled tool calls, panels for replies
- **No framework** — just the Anthropic SDK, Pydantic, and Rich

## Requirements

- Python 3.12+
- [`uv`](https://docs.astral.sh/uv/)
- An Anthropic API key

## Setup

```bash
git clone https://github.com/AhmetErenLapanta/nanoagent.git
cd nanoagent
uv sync
cp .env.example .env          # then put your ANTHROPIC_API_KEY in .env
```

## Usage

```bash
uv run nanoagent
```

```
╭─────────────────────────────────────────────────╮
│ nanoagent · a minimal coding agent              │
│ Enter to send · Ctrl-C to stop · Ctrl-D to quit │
╰─────────────────────────────────────────────────╯
you› what does this project do? read the source and summarize

⚙ ls  path="src/nanoagent"
  └ ✓ __init__.py
cli.py
loop.py
...
⚙ read_file  path="src/nanoagent/loop.py"
  └ ✓ from __future__ import annotations ...
╭─ assistant ─────────────────────────────────────╮
│ It's a small agent loop: each turn calls the     │
│ model, runs any tools it requests, feeds the     │
│ results back, and repeats until the model stops. │
╰─────────────────────────────────────────────────╯
```

- **Enter** sends your message. **Ctrl-C** stops the agent mid-run and returns you to the prompt. **Ctrl-D** quits.

## Article

A walkthrough of how this is built is coming soon. (Link to be added.)

## License

[MIT](LICENSE)
