"""Guard against our names hiding Textual's (as `query` and `_context` once did)."""

import ast
import inspect
import textwrap

import pytest
from textual.app import App
from textual.screen import Screen
from textual.widget import Widget

import djx.app
import djx.screens

# Names we really do override on purpose.
ALLOWED_OVERRIDES = {
    "compose",
    "on_mount",
    "on_resize",
    "BINDINGS",
    "CSS",
    "CSS_PATH",
    "TITLE",
    "SUB_TITLE",
}


def injected_by_textual():
    """Bookkeeping names Textual's metaclass adds to every subclass; they are not ours."""
    names = set()
    for base in (App, Widget, Screen):
        probe = type("Probe", (base,), {})
        names |= set(vars(probe))
    return names


def custom_classes():
    found = []
    for module in (djx.app, djx.screens):
        for _, cls in inspect.getmembers(module, inspect.isclass):
            if cls.__module__ == module.__name__ and issubclass(cls, (App, Widget, Screen)):
                found.append(cls)
    return found


def own_names(cls):
    skip = injected_by_textual()
    return [n for n in vars(cls) if n not in skip and not (n.startswith("__") and n.endswith("__"))]


def instance_attributes(cls):
    """Names assigned as `self.x = ...` in __init__ (these are not in the class __dict__)."""
    init = vars(cls).get("__init__")
    if init is None:
        return []
    tree = ast.parse(textwrap.dedent(inspect.getsource(init)))
    names = []
    for node in ast.walk(tree):
        targets = []
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
        for target in targets:
            if (
                isinstance(target, ast.Attribute)
                and isinstance(target.value, ast.Name)
                and target.value.id == "self"
            ):
                names.append(target.attr)
    return names


def clashes(cls):
    problems = []
    for name in own_names(cls):
        for base in cls.__mro__[1:]:
            if base is not object and name in vars(base) and name not in ALLOWED_OVERRIDES:
                problems.append(f"{cls.__name__}.{name} hides {base.__module__}.{base.__name__}.{name}")
                break
    for name in instance_attributes(cls):
        for base in cls.__mro__[1:]:
            if base is not object and hasattr(base, name) and name not in ALLOWED_OVERRIDES:
                problems.append(
                    f"{cls.__name__}.{name} (set in __init__) hides "
                    f"{base.__module__}.{base.__name__}.{name}"
                )
                break
    return problems


def test_we_found_our_classes():
    names = {c.__name__ for c in custom_classes()}
    assert {"DjxApp", "SectionLabel", "ArgInput", "ErrorScreen", "HelpScreen"} <= names


@pytest.mark.parametrize("cls", custom_classes(), ids=lambda c: c.__name__)
def test_no_name_hides_a_textual_name(cls):
    problems = clashes(cls)
    assert not problems, "\n".join(problems) + "\nPrefix our own names with `djx_`."


def test_the_check_catches_a_clash():
    class Bad(Widget):
        def __init__(self):
            super().__init__()
            self.query = "x"  # shadows DOMNode.query, the bug we once shipped

        def _context(self):  # shadows MessagePump._context
            return None

    assert any("Bad.query" in p for p in clashes(Bad))
    assert any("Bad._context" in p for p in clashes(Bad))
