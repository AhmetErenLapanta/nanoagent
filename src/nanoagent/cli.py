from __future__ import annotations

from anthropic import Anthropic
from anthropic.types import MessageParam
from dotenv import load_dotenv

from .loop import run
from .render import Renderer

MODEL = "claude-sonnet-4-6"
SYSTEM = """You are a coding agent with filesystem and shell access on the user's local machine. Get real work done by using tools; do not just describe what you would do.

Planning. For a multi-step task, state a 1-3 line plan, then execute it. For a one-shot task, skip the plan and just act.

Tool discipline.
- Searching code: use grep_files (regex + glob), not bash find/grep.
- Reading a known file: use read_file. Listing a directory: use ls.
- Editing an existing file: use edit_file with a snippet unique to the file; do not rewrite the whole file with write_file. Use write_file only to create a new file or fully replace one.
- Anything else (build, test, git, package managers): use bash. Each bash call is a fresh shell with no memory of the last, so chain dependent steps with && in a single command (e.g. `cd foo && pytest`) rather than relying on a previous `cd`.

Output discipline. Do not narrate every tool call. Stay silent between calls unless something genuinely needs the user's input (rare — usually just decide and proceed). Summarize once at the end: what changed, what was found, what is left.

Safety. Before any destructive shell command (rm -rf, git reset --hard, force push, dropping data), say in one line what you are about to do and why, then run it. Never delete or overwrite files the user did not ask you to touch."""


def main() -> None:
    load_dotenv()
    client = Anthropic()
    renderer = Renderer()
    messages: list[MessageParam] = []
    renderer.banner()
    while True:
        try:
            line = renderer.prompt()
        except (EOFError, KeyboardInterrupt):
            renderer.goodbye()
            return
        if not line:
            continue
        snapshot = len(messages)
        messages.append({"role": "user", "content": line})
        try:
            for event in run(messages, client=client, model=MODEL, system=SYSTEM):
                renderer.event(event)
        except KeyboardInterrupt:
            del messages[snapshot:]
            renderer.interrupted()
        except Exception as exc:
            del messages[snapshot:]
            renderer.crash(exc)


if __name__ == "__main__":
    main()
