"""Render each .scene from mockups.html into a separate PNG using Playwright.

Usage:
    pip install playwright && python -m playwright install chromium
    python screenshots/render.py

Outputs:
    screenshots/01_architecture.png
    screenshots/02_card_preview.png
    ...
    screenshots/all_screens.png  (combined gallery)
"""
from __future__ import annotations

import sys
from pathlib import Path

SCREENS = [
    ("s01", "01_architecture.png", "Pipeline architecture diagram"),
    ("s02", "02_card_preview.png", "Generated 1080×1350 card mock"),
    ("s03", "03_seven_platforms.png", "7 channel adapters"),
    ("s04", "04_notion_schema.png", "Notion DB content state"),
    ("s05", "05_make_scenario.png", "Make.com scenario (60 modules)"),
    ("s06", "06_cost_log.png", "Per-run cost log"),
    ("s07", "07_niche_rotation.png", "Niche rotation analyzer"),
    ("s08", "08_slack_signals.png", "Operational Slack notifications"),
]


def render() -> None:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.exit(
            "playwright is required. Run:\n"
            "  pip install playwright\n"
            "  python -m playwright install chromium"
        )

    out_dir = Path(__file__).resolve().parent
    mockups = out_dir / "mockups.html"
    if not mockups.exists():
        sys.exit(f"missing {mockups}")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1400, "height": 1000}, device_scale_factor=2)
        page.goto(f"file://{mockups}")
        page.wait_for_load_state("networkidle")

        # Per-screen tight crop overrides (selector relative to the scene).
        # For scenes whose visual element is much narrower than the scene container
        # (e.g. card preview), screenshot just the visual to avoid trailing whitespace.
        TIGHT_CROP = {"s02": ".card-preview"}

        for section_id, filename, label in SCREENS:
            scene = page.locator(f"#{section_id}")
            scene.scroll_into_view_if_needed()
            if section_id in TIGHT_CROP:
                page.locator(f"#{section_id} {TIGHT_CROP[section_id]}").screenshot(
                    path=str(out_dir / filename)
                )
            else:
                scene.screenshot(path=str(out_dir / filename))
            print(f"  ✓ {filename:32} {label}")

        # Combined gallery: full-page screenshot
        page.screenshot(path=str(out_dir / "all_screens.png"), full_page=True)
        print("  ✓ all_screens.png             combined gallery")
        browser.close()

    print(f"\nDone — {len(SCREENS)} per-scene + 1 combined screenshot saved to {out_dir}/")


if __name__ == "__main__":
    render()
