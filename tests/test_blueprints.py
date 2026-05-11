"""Smoke tests for Make.com blueprint builders — verify they produce valid JSON."""
from __future__ import annotations

import importlib
import json


def _load(module_name: str):
    return importlib.import_module(f"make_blueprints.{module_name}")


def test_writer_blueprint_structure() -> None:
    mod = _load("03_writer")
    bp = mod.make_blueprint()
    assert bp["name"]
    assert isinstance(bp["flow"], list)
    assert len(bp["flow"]) >= 3
    # Must be JSON-serialisable (Make API requires it)
    json.dumps(bp)


def test_publisher_telegram_blueprint() -> None:
    mod = _load("06_publisher_telegram")
    bp = mod.make_blueprint()
    assert bp["name"] == "06_publisher_telegram"
    flow_modules = [m.get("module") for m in bp["flow"]]
    assert "telegram:SendPhoto" in flow_modules


def test_stacks_publisher_blueprint() -> None:
    mod = _load("07_stacks_publisher")
    bp = mod.make_blueprint()
    assert "stacks" in bp["name"].lower()
    json.dumps(bp)


def test_factory_overview_blueprint_is_heavy() -> None:
    """The showcase scenario should have ~60 modules across 5 router branches."""
    mod = _load("00_factory_overview")
    bp = mod.make_blueprint()
    total = sum(
        len(branch["flow"]) for branch in bp["flow"][7].get("routes", [])
    )
    total += 7 + 1  # prep + router
    assert total >= 40, f"Expected at least 40 modules, got {total}"
