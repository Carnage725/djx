"""The djx Textual app. Engine calls run in a thread worker; the UI thread never blocks."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from rich.text import Text
from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.events import Click, Resize
from textual.widgets import Footer, Input, LoadingIndicator, Static, Tree
from textual.widgets.tree import TreeNode

from djx import endpoints_view
from djx.engine_client import EngineClient, Envelope, find_python
from djx.screens import ErrorScreen, HelpScreen, WarningsScreen

SECTIONS = ["Endpoints", "Models", "Apps", "Commands", "URLs"]
NARROW_BELOW = 100


class SectionLabel(Static):
    def __init__(self, number: int):
        super().__init__(f"{number} {SECTIONS[number - 1]}")
        self.number = number

    def on_click(self, event: Click) -> None:
        self.app.action_section(self.number)


class DjxApp(App):
    CSS_PATH = "djx.tcss"
    TITLE = "djx"

    BINDINGS = [
        Binding("1", "section(1)", show=False),
        Binding("2", "section(2)", show=False),
        Binding("3", "section(3)", show=False),
        Binding("4", "section(4)", show=False),
        Binding("5", "section(5)", show=False),
        Binding("tab", "next_section", show=False, priority=True),
        Binding("shift+tab", "previous_section", show=False, priority=True),
        Binding("slash", "focus_search", "Search"),
        Binding("escape", "escape", "Back", show=False),
        Binding("j", "cursor_down", show=False),
        Binding("k", "cursor_up", show=False),
        Binding("enter", "open", "Open"),
        Binding("o", "open", show=False),
        Binding("b", "toggle_framework", "Framework"),
        Binding("r", "refresh", "Refresh"),
        Binding("w", "warnings", "Warnings"),
        Binding("question_mark", "help", "Help"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self, client: Any):
        super().__init__()
        self.client = client
        self.envelope: Envelope | None = None
        self.section = 1
        self.search_text = ""
        self.show_framework = False
        self.narrow = False
        self.drilled = False
        self._generation = 0
        self._selected_id: str | None = None

    # ---- layout ----

    def compose(self) -> ComposeResult:
        yield Static(id="top")
        with Horizontal(id="sections"):
            for number in range(1, len(SECTIONS) + 1):
                yield SectionLabel(number)
        yield Input(placeholder="/ search", id="search")
        yield Static(id="summary")
        with Horizontal(id="body"):
            with Vertical(id="list-pane"):
                yield LoadingIndicator(id="loading")
                yield Tree("root", id="tree")
            with VerticalScroll(id="detail-pane"):
                yield Static("‹ Esc to go back", id="back-hint")
                yield Static(id="detail", markup=False)
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#tree", Tree).show_root = False
        self._apply_layout(self.size.width)
        self._refresh_sections()
        self._refresh_top()
        self.reload()

    def on_resize(self, event: Resize) -> None:
        self._apply_layout(event.size.width)

    def _apply_layout(self, width: int) -> None:
        self.narrow = width < NARROW_BELOW
        if not self.narrow:
            self.drilled = False
        list_pane = self.query_one("#list-pane")
        detail_pane = self.query_one("#detail-pane")
        list_pane.display = not (self.narrow and self.drilled)
        detail_pane.display = not self.narrow or self.drilled
        self.query_one("#back-hint").display = self.narrow

    def _refresh_sections(self) -> None:
        for label in self.query(SectionLabel):
            label.set_class(label.number == self.section, "active")

    def _refresh_top(self) -> None:
        project = self.envelope.project if self.envelope else {}
        top = Text(Path(project["root"]).name if project else "djx", style="bold")
        if project:
            top.append(f" · Django {project['django_version']} · {project['settings_module']}")
        warnings = self.envelope.warnings if self.envelope else []
        if warnings:
            top.append(f"  ⚠ {len(warnings)} warnings", style="bold yellow")
        self.query_one("#top", Static).update(top)

    # ---- loading ----

    def reload(self) -> None:
        self._generation += 1
        self.query_one("#loading").display = True
        self.query_one("#tree").display = False
        self._load(self._generation)

    @work(thread=True, exclusive=True)
    def _load(self, generation: int) -> None:
        envelope = self.client.collect()
        self.call_from_thread(self._loaded, generation, envelope)

    def _loaded(self, generation: int, envelope: Envelope) -> None:
        if generation != self._generation:
            return
        self.query_one("#loading").display = False
        self.query_one("#tree").display = True
        if not envelope.ok:
            self.push_screen(ErrorScreen(envelope.error))
            return
        self.envelope = envelope
        self._refresh_top()
        self._rebuild()
        search = self.query_one("#search", Input)
        if not (search.has_focus and search.value):  # do not steal focus from typing
            self.query_one("#tree").focus()

    # ---- tree ----

    def _rebuild(self) -> None:
        tree = self.query_one("#tree", Tree)
        tree.clear()
        summary = self.query_one("#summary", Static)
        if self.section != 1 or self.envelope is None:
            tree.root.add_leaf("coming in next step")
            summary.update("")
            self.query_one("#detail", Static).update("Coming in the next step.")
            return
        groups, counts = endpoints_view.build_groups(
            self.envelope.data["endpoints"], self.search_text, self.show_framework
        )
        suffix = "  (framework shown)" if self.show_framework else ""
        summary.update(counts.text() + suffix)
        self._add_items(tree.root, groups)
        if not groups:
            tree.root.add_leaf("no matches")
        self.call_after_refresh(self._select_initial)

    def _add_items(self, parent: TreeNode, items: list) -> None:
        for item in items:
            if isinstance(item, endpoints_view.Group):
                node = parent.add(Text(item.title, style="bold"), expand=not item.collapsed)
                self._add_items(node, item.items)
            else:
                parent.add_leaf(endpoints_view.label(item.endpoint, item.path), data=item.endpoint)

    def _leaves(self, node: TreeNode) -> list[TreeNode]:
        found = []
        for child in node.children:
            found.extend(self._leaves(child) if child.children else [child])
        return found

    def _select_initial(self) -> None:
        tree = self.query_one("#tree", Tree)
        leaves = [n for n in self._leaves(tree.root) if n.data]
        if not leaves:
            return
        chosen = next((n for n in leaves if n.data["id"] == self._selected_id), leaves[0])
        parent = chosen.parent
        while parent is not None:  # make sure the chosen row is visible
            if self.search_text and parent is not tree.root:
                parent.expand()
            parent = parent.parent
        tree.move_cursor(chosen)
        self._show_node(chosen)

    def _show_node(self, node: TreeNode) -> None:
        detail = self.query_one("#detail", Static)
        if node.data:
            self._selected_id = node.data["id"]
            root = self.envelope.project["root"] if self.envelope else ""
            detail.update(endpoints_view.detail(node.data, root))
        elif self.section == 1 and node.children:
            detail.update(f"{node.label.plain}\n{len(self._leaves(node))} endpoints")

    def on_tree_node_highlighted(self, event: Tree.NodeHighlighted) -> None:
        self._show_node(event.node)

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        if not event.node.data:
            return
        if self.narrow and not self.drilled:
            self._drill(True)
        else:
            self.action_open()

    def _drill(self, drilled: bool) -> None:
        self.drilled = drilled
        self._apply_layout(self.size.width)
        if drilled:
            self.query_one("#detail-pane").focus()
        else:
            self.query_one("#tree").focus()

    # ---- search ----

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.value == self.search_text:
            return
        self.search_text = event.value
        self._rebuild()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.query_one("#tree").focus()

    # ---- actions ----

    def action_section(self, number: int) -> None:
        self.section = number
        self.drilled = False
        self.search_text = ""
        self.query_one("#search", Input).value = ""
        self._apply_layout(self.size.width)
        self._refresh_sections()
        self._rebuild()
        self.query_one("#tree").focus()

    def action_next_section(self) -> None:
        self.action_section(self.section % len(SECTIONS) + 1)

    def action_previous_section(self) -> None:
        self.action_section((self.section - 2) % len(SECTIONS) + 1)

    def action_focus_search(self) -> None:
        if self.drilled:
            self._drill(False)
        self.query_one("#search", Input).focus()

    def action_escape(self) -> None:
        search = self.query_one("#search", Input)
        if self.drilled:
            self._drill(False)
        elif self.search_text or search.has_focus:
            search.value = ""
            self.query_one("#tree").focus()

    def action_cursor_down(self) -> None:
        if self.drilled:
            self.query_one("#detail-pane").scroll_down()
        else:
            self.query_one("#tree", Tree).action_cursor_down()

    def action_cursor_up(self) -> None:
        if self.drilled:
            self.query_one("#detail-pane").scroll_up()
        else:
            self.query_one("#tree", Tree).action_cursor_up()

    def action_open(self) -> None:
        self.notify("Open in editor: coming in a later step.")

    def action_toggle_framework(self) -> None:
        self.show_framework = not self.show_framework
        self._rebuild()

    def action_refresh(self) -> None:
        if isinstance(self.screen, ErrorScreen):
            self.pop_screen()
        self.reload()

    def action_warnings(self) -> None:
        warnings = self.envelope.warnings if self.envelope else []
        if warnings:
            self.push_screen(WarningsScreen(warnings))
        else:
            self.notify("No warnings.")

    def action_help(self) -> None:
        self.push_screen(HelpScreen())


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="djx.app")
    parser.add_argument("--root", default=".")
    parser.add_argument("--python")
    parser.add_argument("--settings")
    args = parser.parse_args(argv)
    client = EngineClient(args.root, find_python(args.root, args.python), args.settings)
    DjxApp(client).run()


if __name__ == "__main__":
    main()
