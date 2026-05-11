"""Smoke tests for app.platform_renderers."""
from __future__ import annotations

import pytest

from app.platform_renderers import (
    ALL_PLATFORMS,
    Post,
    parse_telegram_html,
    render_all,
    render_instagram,
    render_linkedin_ru,
    render_pinterest,
    render_telegram,
    render_threads,
    render_twitter_thread,
)


@pytest.fixture()
def sample_post() -> Post:
    return Post(
        tool_name="DemoTool",
        domain="demotool.com",
        emoji="📝",
        one_liner="AI writing assistant for small business",
        pricing_short="Free → $12/mo",
        hook="One hour of an editor = 4 months of DemoTool. Except the editor isn't in your inbox 24/7.",
        description="Catches grammar, typos, and style in any app — email, Slack, browser. English only.",
        cases=[
            ("🛍", "E-commerce", "100 product descriptions for Amazon/Etsy without typos"),
            ("💼", "Solo entrepreneur", "Drafts a proposal in 5 minutes — client-ready same day"),
            ("📚", "Online courses", "Quiz questions with answers per lesson topic"),
        ],
        pricing_full="Free — basic grammar, Premium $12/mo (annual) — style, tone, paraphrase",
        cta="Start: install the Chrome plugin in 30 seconds → write as usual.",
        url="https://demotool.com",
        hashtags=["DemoTool", "AItools", "SmallBusiness"],
        category="text-content",
    )


def test_render_telegram_under_limit(sample_post: Post) -> None:
    out = render_telegram(sample_post)
    assert "DemoTool" in out
    assert "<b>" in out
    assert len(out) <= 1024


def test_render_instagram_has_hashtags(sample_post: Post) -> None:
    out = render_instagram(sample_post)
    assert "DemoTool" in out
    assert out.count("#") >= 5
    assert len(out) <= 2200


def test_render_pinterest_returns_dict(sample_post: Post) -> None:
    out = render_pinterest(sample_post)
    assert set(out.keys()) >= {"title", "description", "link"}
    assert len(out["title"]) <= 100
    assert len(out["description"]) <= 500


def test_render_linkedin_ru_under_limit(sample_post: Post) -> None:
    out = render_linkedin_ru(sample_post)
    assert "DemoTool" in out
    assert len(out) <= 3000


def test_render_threads_under_limit(sample_post: Post) -> None:
    out = render_threads(sample_post)
    assert len(out) <= 500


def test_render_twitter_thread_returns_list(sample_post: Post) -> None:
    tweets = render_twitter_thread(sample_post)
    assert isinstance(tweets, list)
    assert len(tweets) >= 3
    for t in tweets:
        assert len(t) <= 280, f"tweet too long ({len(t)} chars): {t[:50]}"


def test_render_all_includes_every_platform(sample_post: Post) -> None:
    out = render_all(sample_post)
    for plat in ALL_PLATFORMS:
        assert plat in out, f"render_all missing {plat}"


def test_parse_telegram_html_roundtrip(sample_post: Post) -> None:
    tg = render_telegram(sample_post)
    parsed = parse_telegram_html(tg, category="text-content")
    assert parsed.tool_name == sample_post.tool_name
    assert parsed.emoji == sample_post.emoji
    assert len(parsed.cases) == 3
