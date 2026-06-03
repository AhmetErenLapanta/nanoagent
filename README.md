# nanoagent

A minimal AI coding agent in a few hundred lines — no framework, no magic.

Behind the complex frameworks, an agent is fundamentally three things:
a loop, a tool dispatch table, and an event stream.

The model never touches your filesystem — it only *asks*,
and your code makes things happen.

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

Install [`uv`](https://docs.astral.sh/uv/) if you don't have it (macOS / Linux):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

> Windows or other installers: see the [`uv` install docs](https://docs.astral.sh/uv/getting-started/installation/).

Then clone and set up the project:

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

A session looks like this:

```
› what does this project do? read the source and summarize

⚙ read_file  path="src/nanoagent/loop.py"
  └ ✓ from __future__ import annotations
      from collections.abc import Generator
      ...

╭─ nanoagent ──────────────────────────────────────────╮
│ A small agent loop: each turn calls the model, runs  │
│ any tools it requests, feeds the results back, and   │
│ repeats until the model stops.                       │
╰──────────────────────────────────────────────────────╯
```

Keys:

- **Enter** sends your message
- **Ctrl-C** stops the agent mid-run and returns you to the prompt
- **Ctrl-D** quits

## Article

A walkthrough of how this is built is coming soon. (Link to be added.)

## License

[MIT](LICENSE)
