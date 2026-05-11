"""Sanity check that app.config exposes the expected names."""
from __future__ import annotations


def test_config_exposes_expected_names() -> None:
    from app import config

    for name in [
        "NOTION_TOKEN",
        "OPENAI_API_KEY",
        "MAKE_TOKEN",
        "TELEGRAM_BOT_TOKEN",
        "MAKE_ZONE",
        "MAKE_TEAM_ID",
        "NOTION_TOOLS_DB",
        "NOTION_STACKS_DB",
        "TELEGRAM_CHANNEL",
        "BRAND_NAME",
        "BRAND_TAGLINE",
    ]:
        assert hasattr(config, name), f"missing config.{name}"


def test_require_raises_when_missing(monkeypatch) -> None:
    from app.config import require

    monkeypatch.delenv("NEVER_SET_THIS", raising=False)
    try:
        require("NEVER_SET_THIS")
    except RuntimeError as exc:
        assert "NEVER_SET_THIS" in str(exc)
    else:
        raise AssertionError("require() should have raised RuntimeError")
