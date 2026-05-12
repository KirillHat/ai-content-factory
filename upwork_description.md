# Upwork portfolio description (ready-to-paste)

## Title (under 70 chars)
> **AI Content Factory — one row in Notion → 7 social channels (Python + Make.com)**

Alternative shorter variants:
- *AI Content Factory for SMB owners — Notion + GPT-4o + Make.com*
- *Multi-platform content automation: Notion → 7 channels via Make.com*
- *Notion + GPT-4o + DALL-E content factory (Python, Make.com, Buffer)*

## Description (~230 words)

An end-to-end automation that turns a single Notion row into a fully branded post on **7 social channels** — Telegram, Instagram, LinkedIn (RU + EN), Pinterest, Threads, and X / Twitter — in under 30 seconds.

Built for small-business content owners who want consistent multi-channel publishing without a content team. The pipeline runs entirely on Make.com + Python with Notion as the content database. One GPT-4o-mini call produces **all 8 platform versions at once** (instead of 8 separate calls); image generation (DALL-E 3) and a Pillow renderer produce a 1080×1350 card with the real brand logo for each tool reviewed.

🚀 **Highlights:**
- 🤖 Single GPT call → 8 platform variants (Telegram HTML, Instagram, LinkedIn RU+EN, Pinterest, Threads, X thread)
- 🎨 1080×1350 card generator with real brand logos (3-tier fallback: App Store → SVG → favicon)
- 🔀 Make.com showcase blueprint (`make_blueprints/00_factory_overview.py`) — router fan-out into 5 platform branches with Iterator/Aggregator pattern, built programmatically from Python
- 📊 Niche-rotation analyzer prevents repetitive content over time
- 💰 ~$0.0044 text-generation cost per content package (8-platform GPT call), excluding optional DALL-E 3 image generation
- 🧪 18 smoke tests passing, ruff-clean, Docker-ready, CI on 3 Python versions
- ⚙️ All secrets via env vars (`app/config.py`) — zero hardcoded IDs

**Demo evidence:** Make.com scenario screenshots + Pillow card samples + Notion CMS schema seeds are included in the repo. Architecture-mockup screenshots (`screenshots/sample_*.png`) are HTML-rendered and clearly labelled as such.
**Code:** https://github.com/KirillHat/ai-content-factory

## Skills / tags

`Python` · `Make.com` · `Notion API` · `OpenAI` · `GPT-4` · `DALL-E 3` · `Pillow` · `Buffer API` · `Telegram Bot API` · `Slack API` · `LinkedIn API` · `Pinterest API` · `Content Automation` · `Workflow Automation` · `no-code` · `low-code` · `Docker` · `pytest` · `ruff` · `GitHub Actions` · `Content Marketing` · `Multi-Platform Publishing` · `Cron Jobs` · `REST API`

## Suggested cover & gallery images

- **Cover image:** `screenshots/all_screens.png` — grid of architecture, card preview, and platform fan-out (regenerate via `python screenshots/render.py`)
- **Gallery (5 shots in this order):**
  1. `screenshots/sample_make_scenario.png` — full Make canvas (architecture at a glance)
  2. `screenshots/sample_linkedin_branch.png` — LinkedIn Iterator + Aggregator pattern close-up
  3. `screenshots/02_card_preview.png` — sample 1080×1350 card with brand logo (generated from mockups.html)
  4. `screenshots/03_seven_platforms.png` — 7 platform adapters grid
  5. `screenshots/06_cost_log.png` — per-run cost log (~$0.0044 / tool)

## Suggested rate / pricing

- **Hourly rate:** $45 – $65 / hr
- **Fixed-price (full factory build for a new channel):** $1,800 – $3,500
- **Add-ons:**
  - +1 social platform: $250 — covers GPT prompt tuning + new renderer + Buffer/native publisher
  - Brand voice tuning (1 round, voice DNA doc + 20 review samples): $400
  - Card design refactor (new color/font/layout): $300
  - Setup + maintenance retainer: $400 / mo

## Pinned first reply to a client

> Hey {{name}}, thanks for reaching out!
>
> The portfolio repo has the full source + Make.com blueprints (one Python file per scenario) + a showcase blueprint that builds a 60-module router fan-out scenario covering 5 platform branches.
>
> Quick links:
> - Code: https://github.com/KirillHat/ai-content-factory
> - Architecture diagram + card mocks: `screenshots/mockups.html` in the repo
> - Make scenarios: `make_blueprints/` (one .py per scenario, run `python -m make_blueprints.03_writer` to deploy)
>
> Happy to walk you through the architecture on a 30-min call — give me a couple of times that work for your timezone.
