"""Full-screen error view and the warnings / help overlays."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.screen import ModalScreen, Screen
from textual.widgets import Footer, Static

# Shown instead of Textual's Footer under 100 columns; everything else is on the `?` screen.
NARROW_FOOTER = "/ search  ⏎ details  o open  ? help  q quit"

# Every key the app binds appears here. tests/ui/test_help.py checks that.
HELP_GROUPS = [
    (
        "Everywhere",
        [
            ("1-5", "Switch section"),
            ("Tab / Shift-Tab", "Next / previous section"),
            ("/", "Focus search"),
            ("Esc", "Clear search, leave a form or list, go back"),
            ("j k  ↑ ↓", "Move"),
            ("o", "Open the selected item in your editor"),
            ("r", "Refresh"),
            ("w", "Warnings"),
            ("?", "This help"),
            ("q", "Quit"),
        ],
    ),
    (
        "Endpoints",
        [
            ("Enter", "Open in editor (wide) / show details (narrow)"),
            ("b", "Show / hide framework endpoints"),
        ],
    ),
    (
        "Models",
        [
            ("Enter", "Open in editor (wide) / show details (narrow)"),
            ("l / →", "Focus the relation list"),
            ("Enter on a relation", "Go to that model"),
            ("Backspace", "Back to the previous model"),
            ("b", "Show / hide Django built-in models"),
        ],
    ),
    (
        "Apps",
        [
            ("Enter", "Open the app in your editor (wide) / details (narrow)"),
            ("l / →", "Focus the model list"),
            ("Enter on a model", "Go to that model"),
            ("Backspace", "Back to the app"),
        ],
    ),
    (
        "Commands",
        [
            ("Enter", "Open in editor (wide) / show details (narrow)"),
            ("b", "Show / hide Django built-in commands"),
        ],
    ),
    (
        "URLs",
        [
            ("Enter", "Open in editor (wide) / show details (narrow)"),
            ("l / →", "Fill in the args form"),
            ("Enter in the form", "Next field"),
            ("p", "Resolve a path"),
            ("b", "Show / hide framework URLs"),
        ],
    ),
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
            for title, rows in HELP_GROUPS:
                yield Static(title, classes="dialog-title")
                for keys, what in rows:
                    yield Static(f"{keys}\n    {what}", markup=False)
            yield Static("Esc to close", classes="dim")

    def action_close(self) -> None:
        self.dismiss()
