"""Warnings collected during one engine run. Collectors call warn() and keep going."""

from __future__ import annotations

WARNINGS: list[dict[str, str]] = []


def warn(collector: str, message: str) -> None:
    WARNINGS.append({"collector": collector, "message": message})


def reset() -> None:
    WARNINGS.clear()
