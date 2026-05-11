"""Central configuration — all secrets and IDs loaded from environment variables.

Every value is required at runtime but resolves to empty string in import time so
modules can be imported in tests / CI without env present.

Load from:
  1. process env vars (preferred for prod / CI)
  2. local .env file (auto-loaded if python-dotenv is installed)

See .env.example for the full list with descriptions.
"""
from __future__ import annotations

import os
from pathlib import Path


def _load_dotenv() -> None:
    """Best-effort .env loading. No error if file or library missing."""
    try:
        from dotenv import load_dotenv  # type: ignore[import-not-found]
    except ImportError:
        return
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)


_load_dotenv()


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


# ---- API tokens (REQUIRED for live operation) ----
NOTION_TOKEN: str = _env("NOTION_TOKEN")
OPENAI_API_KEY: str = _env("OPENAI_API_KEY")
MAKE_TOKEN: str = _env("MAKE_TOKEN")
TELEGRAM_BOT_TOKEN: str = _env("TELEGRAM_BOT_TOKEN")
SLACK_BOT_TOKEN: str = _env("SLACK_BOT_TOKEN")
BUFFER_TOKEN: str = _env("BUFFER_TOKEN")

# ---- Make.com workspace ----
MAKE_ZONE: str = _env("MAKE_ZONE", "us2")
MAKE_TEAM_ID: int = int(_env("MAKE_TEAM_ID", "0") or 0)

# ---- Make.com connection IDs (per-workspace integration IDs) ----
NOTION_CONN: int = int(_env("MAKE_NOTION_CONN", "0") or 0)
OPENAI_CONN: int = int(_env("MAKE_OPENAI_CONN", "0") or 0)
TELEGRAM_CONN: int = int(_env("MAKE_TELEGRAM_CONN", "0") or 0)
SLACK_CONN: int = int(_env("MAKE_SLACK_CONN", "0") or 0)

# ---- Notion database IDs ----
NOTION_TOOLS_DB: str = _env("NOTION_TOOLS_DB")
NOTION_STACKS_DB: str = _env("NOTION_STACKS_DB")

# ---- Telegram ----
TELEGRAM_CHANNEL: str = _env("TELEGRAM_CHANNEL")  # @handle or numeric -100xxxxx
TELEGRAM_CHANNEL_USERNAME: str = _env("TELEGRAM_CHANNEL_USERNAME", "@your_channel")

# ---- Buffer profile IDs (multi-platform publishing) ----
BUFFER_IG_PROFILE: str = _env("BUFFER_IG_PROFILE")
BUFFER_LINKEDIN_RU_PROFILE: str = _env("BUFFER_LINKEDIN_RU_PROFILE")
BUFFER_LINKEDIN_EN_PROFILE: str = _env("BUFFER_LINKEDIN_EN_PROFILE")
BUFFER_PINTEREST_PROFILE: str = _env("BUFFER_PINTEREST_PROFILE")

# ---- Brand customization (replace with your brand name in the cards) ----
BRAND_NAME: str = _env("BRAND_NAME", "AI Content Factory")
BRAND_TAGLINE: str = _env("BRAND_TAGLINE", "Simple AI tools for small business growth")


def require(name: str) -> str:
    """Fail-fast accessor for required env vars at the top of CLI entrypoints."""
    val = os.environ.get(name, "").strip()
    if not val:
        raise RuntimeError(
            f"Required environment variable {name!r} is not set. "
            "See .env.example for the full list."
        )
    return val
