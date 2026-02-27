"""Shared rubric loader with process-level cache to avoid repeated disk reads."""

import json
from pathlib import Path
from typing import Any

_RUBRIC_CACHE: dict[str, Any] | None = None
_RUBRIC_PATH: Path | None = None


def _find_rubric_path() -> Path:
    global _RUBRIC_PATH
    if _RUBRIC_PATH is not None:
        return _RUBRIC_PATH
    for p in (
        Path(__file__).resolve().parent.parent / "rubric.json",
        Path.cwd() / "rubric.json",
    ):
        if p.is_file():
            _RUBRIC_PATH = p
            return p
    _RUBRIC_PATH = Path(__file__).resolve().parent.parent / "rubric.json"
    return _RUBRIC_PATH


def get_rubric() -> dict[str, Any]:
    """Return full rubric (dimensions + synthesis_rules). Cached per process."""
    global _RUBRIC_CACHE
    if _RUBRIC_CACHE is not None:
        return _RUBRIC_CACHE
    path = _find_rubric_path()
    if not path.is_file():
        _RUBRIC_CACHE = {"dimensions": [], "synthesis_rules": {}}
        return _RUBRIC_CACHE
    try:
        _RUBRIC_CACHE = json.loads(path.read_text(encoding="utf-8"))
        return _RUBRIC_CACHE
    except (json.JSONDecodeError, OSError):
        _RUBRIC_CACHE = {"dimensions": [], "synthesis_rules": {}}
        return _RUBRIC_CACHE


def get_dimensions() -> list[dict[str, Any]]:
    """Return rubric dimensions. Uses cached rubric."""
    return get_rubric().get("dimensions", []) or []


def get_synthesis_rules() -> dict[str, str]:
    """Return synthesis_rules. Uses cached rubric."""
    return get_rubric().get("synthesis_rules") or {}
