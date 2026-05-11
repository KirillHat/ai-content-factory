"""Smoke tests for app.card_generator.

These don't render the full card (which would hit the network for logos).
They verify imports, helper utilities, and that key constants are wired correctly.
"""
from __future__ import annotations


def test_module_imports() -> None:
    from app import card_generator

    assert hasattr(card_generator, "generate_card")
    assert hasattr(card_generator, "WIDTH")
    assert hasattr(card_generator, "HEIGHT")
    assert card_generator.WIDTH == 1080
    assert card_generator.HEIGHT == 1350


def test_text_helpers_work() -> None:
    """Avoid hitting the network — only test pure helpers."""
    from app.card_generator import _safe_pricing

    assert _safe_pricing("Free → $20") == "Free · $20"
    assert _safe_pricing("Free ⟶ $10") == "Free · $10"
    assert _safe_pricing("no arrow here") == "no arrow here"


def test_trim_logo_handles_none() -> None:
    """_trim_logo should be tolerant of edge cases."""
    from PIL import Image

    from app.card_generator import _trim_logo

    # Empty RGBA image — getbbox returns None
    empty = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
    result = _trim_logo(empty)
    # Should return original image without crashing
    assert result.size == (100, 100)


def test_load_font_falls_back_safely() -> None:
    """load_font should never raise — it falls back to default."""
    from app.card_generator import load_font

    f = load_font("/nonexistent/path.ttf", 12)
    assert f is not None
