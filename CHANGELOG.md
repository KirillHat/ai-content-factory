# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] — 2026-05-11

First public release of the AI Content Factory framework.

### Added
- `app/card_generator.py` — Pillow-based 1080×1350 card renderer with real brand logos
  (App Store icon fetch, fallback to gilbarbara/logos SVG via cairo, then favicon).
- `app/platform_renderers.py` — single `Post` dataclass rendered into 7 platforms
  (Telegram, Instagram, LinkedIn RU + EN, Pinterest, Threads, X / Twitter thread).
  Handles per-platform char limits, hashtags, tone (ты / вы / you), and HTML escape.
- `app/niche_history.py` — counts niche frequency across published rows to
  produce a rotation hint that the GPT writer follows.
- `make_blueprints/` — five Make.com scenario builders:
  - `03_writer.py` — single GPT-4o-mini call → 8 platform versions
  - `06_publisher_telegram.py` — Telegram channel auto-posting
  - `07_stacks_publisher.py` — tool-stack publisher
  - `08_publisher_multi.py` — Buffer-based IG / LinkedIn / Pinterest distributor
  - `00_factory_overview.py` — 60-module showcase scenario combining all stages
- `scripts/create_notion_dbs.py`, `scripts/seed_notion_dbs.py`,
  `scripts/backup_blueprints.py` — one-time setup + weekly backup.
- Test suite: smoke tests for card_generator, platform_renderers, niche_history.
- Docker config + GitHub Actions CI (ruff + pytest).
- `.env.example` covering every required token / ID / brand config.
