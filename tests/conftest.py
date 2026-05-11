"""Shared pytest fixtures."""
import os
import sys
from pathlib import Path

# Make `app`, `make_blueprints`, `scripts` importable when pytest is run from the repo root.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Provide stub env vars so importing app.config doesn't blow up in CI.
os.environ.setdefault("NOTION_TOKEN", "stub")
os.environ.setdefault("OPENAI_API_KEY", "stub")
os.environ.setdefault("MAKE_TOKEN", "stub")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "stub")
os.environ.setdefault("MAKE_TEAM_ID", "1")
os.environ.setdefault("NOTION_TOOLS_DB", "stub-tools-db")
os.environ.setdefault("NOTION_STACKS_DB", "stub-stacks-db")
os.environ.setdefault("TELEGRAM_CHANNEL", "@stub_channel")
os.environ.setdefault("BRAND_NAME", "TestFactory")
os.environ.setdefault("BRAND_TAGLINE", "Test tagline for unit tests")
