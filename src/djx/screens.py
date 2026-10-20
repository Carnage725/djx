"""Full-screen error view and the warnings / help overlays."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.screen import ModalScreen, Screen
from textual.widgets import Footer, Static

HELP_ROWS = [
    ("1-5", "Switch section"),
    ("Tab / Shift-Tab", "Next / previous section"),
    ("/", "Focus search"),
    ("Esc", "Clear search / go back"),
    ("j k  ↑ ↓", "Move"),
    ("Enter", "Open details (narrow) or open in editor"),
    ("o", "Open in editor"),
    ("b", "Show / hide framework items"),
    ("r", "Refresh"),
    ("w", "Warnings"),
    ("?", "This help"),
    ("q", "Quit"),
]


class ErrorScreen(Screen):
    BINDINGS = [
        Binding("r", "retry", "Retry"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self, error: dict[str, str]):
        super().__init__()
        self.error = error

    def compose(self) -> ComposeResult:
        error = self.error
        with VerticalScroll(id="error-body"):
            yield Static(error["type"] or "Error", id="error-type")
            yield Static(error["message"], id="error-message")
            yield Static(error["hint"], id="error-hint")
            yield Static("Traceback", id="error-traceback-title")
            yield Static(error["traceback"] or "(none)", id="error-traceback", markup=False)
        yield Footer()

    def action_retry(self) -> None:
        self.app.action_refresh()

    def action_quit(self) -> None:
        self.app.exit()


class WarningsScreen(ModalScreen):
    BINDINGS = [Binding("escape", "close", "Close"), Binding("w", "close", "Close")]

    def __init__(self, warnings: list[dict[str, str]]):
        super().__init__()
        self.warnings = warnings

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="dialog"):
            yield Static(f"{len(self.warnings)} warnings", classes="dialog-title")
            for warning in self.warnings:
                yield Static(f"{warning['collector']}: {warning['message']}", markup=False)
            yield Static("Esc to close", classes="dim")

    def action_close(self) -> None:
        self.dismiss()


class HelpScreen(ModalScreen):
    BINDINGS = [Binding("escape", "close", "Close"), Binding("question_mark", "close", "Close")]

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="dialog"):
            yield Static("Keys", classes="dialog-title")
            for keys, what in HELP_ROWS:
                yield Static(f"{keys:<16}{what}", markup=False)
            yield Static("Esc to close", classes="dim")

    def action_close(self) -> None:
        self.dismiss()
