from __future__ import annotations

import json
import random
import sys
import termios

from rich.console import Console, Group
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.spinner import Spinner
from rich.text import Text

from .types import (
    AgentError,
    AgentEvent,
    AssistantText,
    Thinking,
    ToolCall,
    ToolResult,
    TurnDone,
)

_SNIPPET_LIMIT = 200
_RESULT_PREFIX = "  └ "
_RESULT_INDENT = " " * (len(_RESULT_PREFIX) + 2)


def _snippet(s: str) -> str:
    return s if len(s) <= _SNIPPET_LIMIT else s[:_SNIPPET_LIMIT] + "..."


def _format_args(args: dict[str, object]) -> str:
    parts: list[str] = []
    for k, v in args.items():
        if isinstance(v, str):
            shown = v if len(v) <= 60 else v[:60] + "..."
            parts.append(f'{k}="{shown}"')
        else:
            parts.append(f"{k}={json.dumps(v)}")
    return " ".join(parts)


class Renderer:
    def __init__(self) -> None:
        self.console = Console()
        self._live: Live | None = None

    def banner(self) -> None:
        body = Text.from_markup(
            "[bold cyan]nanoagent[/bold cyan] [dim]· a minimal coding agent[/dim]\n"
            "[dim]Enter to send · Ctrl-C to stop · Ctrl-D to quit[/dim]"
        )
        self.console.print(Panel(body, border_style="cyan", expand=False))

    def prompt(self) -> str:
        _drain_stdin()
        return self.console.input("[bold cyan]›[/bold cyan] ").strip()

    def goodbye(self) -> None:
        self.console.print()

    def event(self, event: AgentEvent) -> None:
        match event:
            case Thinking():
                self._start_spinner()
            case AssistantText(text=t):
                self._stop_spinner()
                self._render_assistant(t)
            case ToolCall(name=n, input=i):
                self._stop_spinner()
                self._render_tool_call(n, i)
            case ToolResult(output=o, is_error=err):
                self._stop_spinner()
                self._render_tool_result(o, is_error=err)
            case TurnDone():
                self._stop_spinner()
            case AgentError(message=m):
                self._stop_spinner()
                self.console.print(
                    Panel(
                        Text(m, style="bold red"),
                        title="nanoagent error",
                        border_style="red",
                        expand=False,
                    )
                )

    def crash(self, exc: BaseException) -> None:
        self._stop_spinner()
        self.console.print(
            Panel(
                Text(f"{type(exc).__name__}: {exc}", style="bold red"),
                title="nanoagent crashed",
                border_style="red",
                expand=False,
            )
        )

    def interrupted(self) -> None:
        self._stop_spinner()
        self.console.print(Text("interrupted", style="yellow"))

    def _render_assistant(self, text: str) -> None:
        renderable = Markdown(text) if _looks_like_markdown(text) else Text(text)
        self.console.print(
            Panel(
                renderable,
                title="[bold magenta]nanoagent[/bold magenta]",
                title_align="left",
                border_style="magenta",
            )
        )

    def _render_tool_call(self, name: str, args: dict[str, object]) -> None:
        self.console.print(
            Text.assemble(
                ("⚙ ", "yellow"),
                (name, "bold cyan"),
                ("  ", ""),
                (_format_args(args), "dim"),
            )
        )

    def _render_tool_result(self, output: str, *, is_error: bool) -> None:
        marker = "✗" if is_error else "✓"
        marker_style = "red" if is_error else "green"
        body_style = "red" if is_error else "dim"
        lines = _snippet(output).splitlines() or [""]
        self.console.print(
            Text.assemble(
                (_RESULT_PREFIX, "dim"),
                (f"{marker} ", marker_style),
                (lines[0], body_style),
            )
        )
        for line in lines[1:]:
            self.console.print(Text(_RESULT_INDENT + line, style=body_style))

    def _start_spinner(self) -> None:
        if self._live is not None:
            return
        word = random.choice(_THINKING_WORDS)
        spinner = Spinner("dots", text=Text(f"{word}…", style="dim"))
        self._live = Live(
            Group(spinner),
            console=self.console,
            refresh_per_second=12,
            transient=True,
        )
        self._live.start()

    def _stop_spinner(self) -> None:
        if self._live is None:
            return
        self._live.stop()
        self._live = None


def _looks_like_markdown(text: str) -> bool:
    markers = ("```", "**", "`", "# ", "## ", "- ", "* ", "1. ", "> ")
    return any(m in text for m in markers)


def _drain_stdin() -> None:
    if not sys.stdin.isatty():
        return
    termios.tcflush(sys.stdin, termios.TCIFLUSH)


_THINKING_WORDS = (
    "baking",
    "bamboozling",
    "bossing",
    "brewing",
    "caffeinating",
    "conjuring",
    "cooking",
    "coping",
    "doomscrolling",
    "finessing",
    "flexing",
    "galaxy-braining",
    "gaslighting",
    "gatekeeping",
    "ghosting",
    "glazing",
    "hustling",
    "hypnotizing",
    "interfering",
    "lollygagging",
    "lurking",
    "magnetizing",
    "magnificing",
    "manifesting",
    "manipulating",
    "marinating",
    "menacing",
    "mesmerizing",
    "mogging",
    "moseying",
    "noodling",
    "overthinking",
    "patronizing",
    "percolating",
    "plotting",
    "pondering",
    "procrastinating",
    "rizzing",
    "scheming",
    "seething",
    "side-eyeing",
    "simmering",
    "slaying",
    "slurping",
    "smirking",
    "smoothing",
    "spelunking",
    "spiraling",
    "sporting",
    "stewing",
    "thinking",
    "tinkering",
    "vibe-checking",
    "vibing",
    "wrestling",
    "yapping",
    "yeeting",
)
