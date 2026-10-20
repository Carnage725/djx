import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "regen_fixture.py"


def load_script():
    spec = importlib.util.spec_from_file_location("regen_fixture", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_fixture_is_up_to_date(collected):
    script = load_script()
    expected = script.normalize(collected)
    actual = script.FIXTURE.read_text(encoding="utf-8")
    assert actual == expected, "Fixture is stale: run `uv run python scripts/regen_fixture.py`"


def test_fixture_is_machine_independent():
    text = load_script().FIXTURE.read_text(encoding="utf-8")
    assert str(SCRIPT.parents[1]) not in text
