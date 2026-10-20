"""Render README screenshots (PNG) from the real app against the sandbox project.

Textual exports SVG; a Chromium-based browser (Chrome, Brave, Chromium) turns it into PNG.
Run: uv run python scripts/screenshots.py
"""

from __future__ import annotations

import asyncio
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "docs" / "screenshots"
sys.path.insert(0, str(REPO / "src"))

from djx.app import DjxApp
from djx.engine_client import EngineClient


async def settle(pilot, extra: float = 0.0) -> None:
    await pilot.app.workers.wait_for_complete()
    await pilot.pause(extra)
    await pilot.pause()
    await pilot.pause()


async def search(pilot, text: str) -> None:
    await pilot.press("slash")
    await pilot.press(*text)
    await pilot.press("enter")
    await settle(pilot)


def make_app(settings: str | None = None) -> DjxApp:
    client = EngineClient(REPO / "sandbox", sys.executable, settings)
    return DjxApp(client, editor="zed {file}:{line}")


BROWSERS = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "google-chrome",
    "chromium",
]


def browser() -> str:
    for candidate in BROWSERS:
        if Path(candidate).exists() or shutil.which(candidate):
            return candidate
    sys.exit("No Chromium-based browser found to turn the SVG into a PNG.")


def save(app: DjxApp, name: str) -> None:
    svg = app.export_screenshot(title="djx")
    width, height = (int(float(v)) for v in re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', svg).groups())
    with tempfile.TemporaryDirectory() as tmp:
        svg_path = Path(tmp) / f"{name}.svg"
        svg_path.write_text(svg, encoding="utf-8")
        subprocess.run(
            [
                browser(), "--headless=new", "--disable-gpu", "--hide-scrollbars",
                "--force-device-scale-factor=2", f"--window-size={width},{height}",
                f"--screenshot={OUT / (name + '.png')}", svg_path.as_uri(),
            ],
            check=True, capture_output=True,
        )
    print("wrote", name)


async def endpoints() -> None:
    app = make_app()
    async with app.run_test(size=(118, 32)) as pilot:
        await settle(pilot)
        await search(pilot, "cancel")
        await pilot.press("escape")  # clears the search, the selection stays
        await settle(pilot)
        save(app, "endpoints")


async def models() -> None:
    app = make_app()
    async with app.run_test(size=(118, 50)) as pilot:
        await settle(pilot)
        await pilot.press("2")
        await search(pilot, "shop.order")
        await pilot.press("escape")
        await settle(pilot)
        await pilot.press("l")
        await settle(pilot)
        save(app, "models")


async def urls() -> None:
    app = make_app()
    async with app.run_test(size=(118, 34)) as pilot:
        await settle(pilot)
        await pilot.press("5")
        await search(pilot, "post-detail")
        await pilot.press("escape")
        await settle(pilot)
        await pilot.press("l")
        await pilot.press(*"hello-djx")
        await pilot.pause(0.8)
        await settle(pilot)
        await pilot.press("escape")
        await pilot.press("p")
        await pilot.press(*"/api/v1/orders/7/cancel")
        await pilot.pause(0.8)
        await settle(pilot, 0.3)
        app.query_one("#tree").focus()
        await settle(pilot)
        save(app, "urls")


async def narrow() -> None:
    app = make_app()
    async with app.run_test(size=(50, 30)) as pilot:
        await settle(pilot)
        save(app, "narrow-list")
        await pilot.press("j", "j", "j", "enter")
        await settle(pilot)
        save(app, "narrow-detail")


async def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for step in (endpoints, models, urls, narrow):
        await step()


asyncio.run(main())
