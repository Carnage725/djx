"""The djx Textual app. Engine calls run in thread workers; the UI thread never blocks."""

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
from textual.timer import Timer
from textual.widgets import Footer, Input, LoadingIndicator, OptionList, Static, Tree
from textual.widgets.option_list import Option
from textual.widgets.tree import TreeNode

from djx import apps_view, commands_view, endpoints_view, models_view, urls_view
from djx.engine_client import EngineClient, Envelope, find_python
from djx.screens import ErrorScreen, HelpScreen, WarningsScreen
from djx.tree_model import Context, Group

SECTIONS = ["Endpoints", "Models", "Apps", "Commands", "URLs"]
VIEWS = {
    1: endpoints_view,
    2: models_view,
    3: apps_view,
    4: commands_view,
    5: urls_view,
}
URLS_SECTION = 5
NARROW_BELOW = 100
DEBOUNCE_SECONDS = 0.3


class SectionLabel(Static):
    def __init__(self, number: int):
        super().__init__(f"{number} {SECTIONS[number - 1]}")
        self.number = number

    def on_click(self, event: Click) -> None:
        self.app.action_section(self.number)


class ArgInput(Input):
    """One input per URL argument of the selected URL name."""

    def __init__(self, arg_name: str):
        super().__init__(placeholder=arg_name, classes="arg")
        self.arg_name = arg_name


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
        Binding("p", "focus_resolve", show=False),
        Binding("l", "focus_side", show=False),
        Binding("right", "focus_side", show=False),
        Binding("escape", "escape", "Back", show=False),
        Binding("backspace", "back_link", "Back", show=False),
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
        self._selected_key: str | None = None
        self._selected_item: dict[str, Any] | None = None
        self._links: list[tuple[int, str] | None] = []
        self._back_stack: list[tuple[int, str | None]] = []
        self._reverse_timer: Timer | None = None
        self._resolve_timer: Timer | None = None
        self._reverse_generation = 0
        self._resolve_generation = 0

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
                yield Input(placeholder="p: resolve a path, e.g. /blog/hello/", id="resolve-input")
                yield Static(id="resolve-result", markup=False)
                yield Tree("root", id="tree")
            with VerticalScroll(id="detail-pane"):
                yield Static("‹ Esc to go back", id="back-hint")
                yield Static(id="detail", markup=False)
                yield OptionList(id="links")
                with Vertical(id="url-form"):
                    yield Static(id="form-hint", markup=False)
                    yield Vertical(id="arg-inputs")
                    yield Static(id="reverse-result", markup=False)
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#tree", Tree).show_root = False
        self._apply_layout(self.size.width)
        self._apply_section_widgets()
        self._refresh_sections()
        self._refresh_top()
        self.reload()

    def on_resize(self, event: Resize) -> None:
        self._apply_layout(event.size.width)

    def _apply_layout(self, width: int) -> None:
        self.narrow = width < NARROW_BELOW
        if not self.narrow:
            self.drilled = False
        self.query_one("#list-pane").display = not (self.narrow and self.drilled)
        self.query_one("#detail-pane").display = not self.narrow or self.drilled
        self.query_one("#back-hint").display = self.narrow

    def _apply_section_widgets(self) -> None:
        urls = self.section == URLS_SECTION
        self.query_one("#resolve-input").display = urls
        self.query_one("#resolve-result").display = urls
        self.query_one("#url-form").display = False
        self.query_one("#links").display = False

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

    def _view_context(self) -> Context:
        assert self.envelope is not None
        return Context(self.envelope.project["root"], self.envelope.data)

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
        if self.envelope is None:
            return
        view = VIEWS[self.section]
        groups, summary = view.build(self.envelope.data, self.search_text, self.show_framework)
        if self.show_framework and self.section != 3:
            summary += "  (framework shown)"
        self.query_one("#summary", Static).update(summary)
        self._add_items(tree.root, groups)
        if not groups:
            tree.root.add_leaf("no matches")
            self._set_detail("", [])
            self.query_one("#url-form").display = False
        self.call_after_refresh(self._select_initial)

    def _add_items(self, parent: TreeNode, items: list) -> None:
        for item in items:
            if isinstance(item, Group):
                node = parent.add(Text(item.title, style="bold"), expand=not item.collapsed)
                self._add_items(node, item.items)
            else:
                parent.add_leaf(item.label, data=item.item)

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
        view = VIEWS[self.section]
        chosen = next((n for n in leaves if view.key(n.data) == self._selected_key), leaves[0])
        parent = chosen.parent
        while parent is not None and parent is not tree.root:  # make the chosen row visible
            parent.expand()
            parent = parent.parent
        tree.move_cursor(chosen)
        self._show_node(chosen)

    def _show_node(self, node: TreeNode) -> None:
        view = VIEWS[self.section]
        form = self.query_one("#url-form")
        if node.data:
            self._selected_key = view.key(node.data)
            self._selected_item = node.data
            detail = view.detail(node.data, self._view_context())
            self._set_detail(detail.body, detail.links)
            if self.section == URLS_SECTION:
                self.run_worker(self._rebuild_form(node.data), exclusive=True, group="form")
            else:
                form.display = False
        elif node.children:
            self._selected_item = None
            form.display = False
            self._set_detail(f"{node.label.plain}\n{len(self._leaves(node))} items", [])

    def _set_detail(self, body: Any, links: list) -> None:
        self.query_one("#detail", Static).update(body)
        options = self.query_one("#links", OptionList)
        options.clear_options()
        self._links = []
        new = []
        for link in links:
            if link.section is None:
                new.append(Option(Text(str(link.text), style="bold"), disabled=True))
                self._links.append(None)
            else:
                new.append(Option(link.text))
                self._links.append((link.section, link.key))
        options.add_options(new)
        options.display = bool(new)

    def on_tree_node_highlighted(self, event: Tree.NodeHighlighted) -> None:
        self._show_node(event.node)

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        if not event.node.data:
            return
        if self.narrow and not self.drilled:
            self._drill(True)
        else:
            self.action_open()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        target = self._links[event.option_index]
        if target:
            self.goto(*target)

    def _drill(self, drilled: bool) -> None:
        self.drilled = drilled
        self._apply_layout(self.size.width)
        self._focus_main()

    def _focus_main(self) -> None:
        self.query_one("#detail-pane" if self.drilled else "#tree").focus()

    # ---- cross-links ----

    def goto(self, section: int, key: str, push: bool = True) -> None:
        """Jump to an item in any section. Backspace returns to where we were."""
        if self.envelope is None:
            return
        view = VIEWS[section]
        item = next((i for i in self.envelope.data[view.ITEMS] if view.key(i) == key), None)
        if item is None:
            self.notify(f"{key} not found")
            return
        if push:
            self._back_stack.append((self.section, self._selected_key))
        if not view.visible(item, self.show_framework):
            self.show_framework = True
            self.notify("Showing framework items")
        self.section = section
        self.search_text = ""
        self.query_one("#search", Input).value = ""
        self._selected_key = key
        self.drilled = self.narrow
        self._apply_layout(self.size.width)
        self._apply_section_widgets()
        self._refresh_sections()
        self._rebuild()
        self._focus_main()

    def action_back_link(self) -> None:
        if not self._back_stack:
            return
        section, key = self._back_stack.pop()
        if key is None:
            self.action_section(section)
        else:
            self.goto(section, key, push=False)

    # ---- inputs ----

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "search":
            if event.value == self.search_text:
                return
            self.search_text = event.value
            self._rebuild()
        elif event.input.id == "resolve-input":
            self._restart_timer("_resolve_timer", self._run_resolve)
        elif isinstance(event.input, ArgInput):
            self._restart_timer("_reverse_timer", self._run_reverse)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if isinstance(event.input, ArgInput):
            inputs = list(self.query(ArgInput))
            index = inputs.index(event.input)
            if index + 1 < len(inputs):
                inputs[index + 1].focus()
                return
        self._focus_main()

    def _restart_timer(self, name: str, callback: Any) -> None:
        timer = getattr(self, name)
        if timer is not None:
            timer.stop()
        setattr(self, name, self.set_timer(DEBOUNCE_SECONDS, callback))

    # ---- reverse form ----

    async def _rebuild_form(self, url: dict[str, Any]) -> None:
        self.query_one("#url-form").display = True
        hint = self.query_one("#form-hint", Static)
        result = self.query_one("#reverse-result", Static)
        box = self.query_one("#arg-inputs")
        await box.remove_children()
        result.update("")
        if url["unnamed_groups"] > 0:
            hint.update(urls_view.NO_POSITIONAL)
            return
        if url["args"]:
            hint.update("Args (type to reverse)")
            await box.mount(*[ArgInput(name) for name in url["args"]])
        else:
            hint.update("No args")
        self._run_reverse()

    def _run_reverse(self) -> None:
        url = self._selected_item
        if self.section != URLS_SECTION or not url or url["unnamed_groups"] > 0:
            return
        values = {i.arg_name: i.value for i in self.query(ArgInput)}
        missing = [name for name, value in values.items() if not value]
        result = self.query_one("#reverse-result", Static)
        if missing:
            result.update(Text("fill in: " + ", ".join(missing), style="dim"))
            return
        self._reverse_generation += 1
        self._reverse_worker(self._reverse_generation, url["name"], values)

    @work(thread=True, exclusive=True, group="reverse")
    def _reverse_worker(self, generation: int, name: str, values: dict[str, str]) -> None:
        envelope = self.client.reverse(name, kwargs=values)
        self.call_from_thread(self._reversed, generation, envelope)

    def _reversed(self, generation: int, envelope: Envelope) -> None:
        if generation != self._reverse_generation:
            return
        result = self.query_one("#reverse-result", Static)
        if envelope.ok:
            result.update(Text("→ " + envelope.data["url"], style="bold green"))
        else:
            result.update(Text(envelope.error["message"].splitlines()[0], style="red"))

    # ---- resolve ----

    def _run_resolve(self) -> None:
        path = self.query_one("#resolve-input", Input).value.strip()
        self._resolve_generation += 1
        if not path:
            self.query_one("#resolve-result", Static).update("")
            return
        self._resolve_worker(self._resolve_generation, path)

    @work(thread=True, exclusive=True, group="resolve")
    def _resolve_worker(self, generation: int, path: str) -> None:
        envelope = self.client.resolve(path)
        self.call_from_thread(self._resolved, generation, envelope)

    def _resolved(self, generation: int, envelope: Envelope) -> None:
        if generation != self._resolve_generation:
            return
        result = self.query_one("#resolve-result", Static)
        if not envelope.ok:
            result.update(Text(envelope.error["message"].splitlines()[0], style="red"))
            return
        data = envelope.data
        root = self.envelope.project["root"] if self.envelope else ""
        lines = [f"→ {data['view']}"]
        if data.get("url_name"):
            lines.append(f"  name: {data['url_name']}")
        from djx.tree_model import source_text

        lines.append("  " + source_text(data["source"], root))
        result.update("\n".join(lines))

    # ---- actions ----

    def action_section(self, number: int) -> None:
        self.section = number
        self.drilled = False
        self.search_text = ""
        self._selected_key = None
        self._back_stack.clear()
        self.query_one("#search", Input).value = ""
        self._apply_layout(self.size.width)
        self._apply_section_widgets()
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

    def action_focus_resolve(self) -> None:
        if self.section != URLS_SECTION:
            return
        if self.drilled:
            self._drill(False)
        self.query_one("#resolve-input", Input).focus()

    def action_focus_side(self) -> None:
        """Move focus from the tree to the relation list or the reverse form."""
        if self.narrow and not self.drilled:
            self._drill(True)
        if self.section == URLS_SECTION:
            inputs = list(self.query(ArgInput))
            if inputs:
                inputs[0].focus()
            return
        options = self.query_one("#links", OptionList)
        if options.display and options.option_count:
            options.focus()
            options.highlighted = next(i for i, link in enumerate(self._links) if link)

    def action_escape(self) -> None:
        focused = self.focused
        in_side = (
            isinstance(focused, ArgInput)
            or (focused is not None and focused.id in ("links", "resolve-input"))
        )
        search = self.query_one("#search", Input)
        if in_side:
            self._focus_main()
        elif self.drilled:
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
