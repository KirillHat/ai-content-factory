"""platform_renderers — single canonical Post → per-platform formatted text.

Design:
  1. Canonical Post dataclass (structured fields, one source of truth)
  2. Renderer per platform with strict rules (length limits, formatting, tone)
  3. HTML→Post parser to extract canonical structure from existing Telegram posts

Platform rule matrix:
  | platform     | format     | limit | hashtags  | tone | link        |
  |--------------|------------|-------|-----------|------|-------------|
  | telegram     | HTML       | 1024  | none      | ты   | inline href |
  | instagram    | plain      | 2200  | 8-10 end  | ты   | "→ link in bio" |
  | pinterest    | title+desc | 100+500| 5 in desc| ты   | clickable   |
  | linkedin_ru  | plain      | 3000  | 3-5 end   | вы   | clickable   |
  | linkedin_en  | plain EN   | 3000  | 3-5 end   | you  | clickable   |
  | threads      | plain      | 500   | none      | ты   | clickable   |
  | twitter      | thread     | 280×N | 1-2/tweet | ты   | last tweet  |
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class Post:
    """Canonical structured post — single source of truth for all platforms."""
    tool_name: str                              # "Grammarly"
    domain: str                                 # "grammarly.com"
    emoji: str                                  # "📝"
    one_liner: str                              # "AI-редактор для текста на английском"
    pricing_short: str                          # "Free → $12/мес"
    hook: str                                   # full hook paragraph (1-2 sentences)
    description: str                            # what tool does (1 paragraph)
    cases: list[tuple[str, str, str]] = field(default_factory=list)
    # cases = [(niche_emoji, niche_label, scenario), ...]
    pricing_full: str = ""                      # "бесплатно — базовая грамматика, Premium $12/мес — стиль, тон..."
    cta: str = ""                               # "Старт: установи плагин в Chrome..."
    url: str = ""                               # "https://grammarly.com"
    hashtags: list[str] = field(default_factory=list)  # ["BrandSlug", "ToolName", "Category"]
    category: str = ""                          # "text-content" / "video" / "automation" — for hashtag generation


# ---- Renderers ----

def render_telegram(post: Post) -> str:
    """Telegram: HTML, no hashtags, ≤1024 chars, inline href, 'ты'."""
    cases = "\n".join(
        f"{e} <b>{niche}:</b> {scen}" for e, niche, scen in post.cases
    )
    text = (
        f"{post.emoji} <b>{post.tool_name}</b> — {post.one_liner}. {post.pricing_short}.\n\n"
        f"{post.hook}\n\n"
        f"{post.description}\n\n"
        f"<b>3 кейса для малого бизнеса:</b>\n\n"
        f"{cases}\n\n"
        f"<b>Стоимость:</b> {post.pricing_full}\n\n"
        f"{post.cta}\n\n"
        f"→ <a href=\"{post.url}\">{post.domain}</a>"
    )
    return _trim_to(text, 1024)


def render_instagram(post: Post) -> str:
    """Instagram: plain text, 8-10 hashtags at end, ≤2200, 'ты', link in bio."""
    cases = "\n".join(
        f"{e} {niche}: {scen}" for e, niche, scen in post.cases
    )
    tags = _build_hashtags(post, count=10)
    text = (
        f"{post.emoji} {post.tool_name} — {post.one_liner}. {post.pricing_short}.\n\n"
        f"{post.hook}\n\n"
        f"{post.description}\n\n"
        f"3 кейса для малого бизнеса:\n\n"
        f"{cases}\n\n"
        f"Стоимость: {post.pricing_full}\n\n"
        f"{post.cta}\n\n"
        f"Ссылка на инструмент — в био / story highlights\n\n"
        f"{tags}"
    )
    return _trim_to(text, 2200)


def render_pinterest(post: Post) -> dict:
    """Pinterest: title ≤100, description ≤500, hashtags in desc, clickable link.
    Returns dict so caller can post title separately."""
    title = f"{post.tool_name} — {post.one_liner} ({post.pricing_short})"
    title = _trim_to(title, 100)
    tags = _build_hashtags(post, count=5)
    cases_one_line = " · ".join(scen for _, _, scen in post.cases[:3])
    desc = (
        f"{post.hook}\n\n"
        f"3 кейса: {cases_one_line}.\n\n"
        f"{post.cta}\n\n"
        f"{tags}"
    )
    desc = _trim_to(desc, 500)
    return {"title": title, "description": desc, "link": post.url}


def render_linkedin_ru(post: Post) -> str:
    """LinkedIn RU: 'вы', B2B tone, 3-5 hashtags, ≤3000 chars."""
    cases = "\n".join(
        f"{e} {niche}: {scen}" for e, niche, scen in post.cases
    )
    # Convert "ты" → "вы" in hook/cta heuristically
    hook_vy = _ty_to_vy(post.hook)
    cta_vy = _ty_to_vy(post.cta)
    desc_vy = _ty_to_vy(post.description)
    tags = _build_hashtags(post, count=5)
    text = (
        f"{post.tool_name} — {post.one_liner}.\n\n"
        f"{hook_vy}\n\n"
        f"{desc_vy}\n\n"
        f"Где это работает в малом и среднем бизнесе:\n\n"
        f"{cases}\n\n"
        f"Стоимость: {post.pricing_full}\n\n"
        f"{cta_vy}\n\n"
        f"Подробнее: {post.url}\n\n"
        f"{tags}"
    )
    return _trim_to(text, 3000)


def render_linkedin_en(post: Post, en_overrides: dict | None = None) -> str:
    """LinkedIn EN: 'you', B2B, 3-5 hashtags, ≤3000.
    Mechanical mode: requires en_overrides dict with translated copy.
    Without it, returns a template that flags need for translation."""
    if en_overrides:
        return _render_en_from_overrides(post, en_overrides)
    # Otherwise: produce a TEMPLATE marked for human/GPT translation
    return (
        f"[NEEDS EN TRANSLATION — pass en_overrides dict]\n\n"
        f"Source RU:\n{render_linkedin_ru(post)}\n\n"
        f"Required en_overrides keys: one_liner, hook, description, cases (list of 3 dicts with 'niche'+'scenario'), "
        f"pricing_full, cta"
    )


def _render_en_from_overrides(post: Post, en: dict) -> str:
    cases_en = en.get("cases", [])
    cases_str = "\n".join(
        f"{c.get('emoji', '•')} {c.get('niche')}: {c.get('scenario')}" for c in cases_en
    )
    from app.config import BRAND_NAME
    brand_slug = re.sub(r"\W+", "", BRAND_NAME)
    tags_en = " ".join(f"#{t}" for t in en.get("hashtags", [brand_slug, "AItools", "SmallBusiness", "Productivity", post.tool_name.replace(" ", "")]))
    return _trim_to(
        f"{post.tool_name} — {en['one_liner']}.\n\n"
        f"{en['hook']}\n\n"
        f"{en['description']}\n\n"
        f"3 use cases for small business:\n\n"
        f"{cases_str}\n\n"
        f"Pricing: {en['pricing_full']}\n\n"
        f"{en['cta']}\n\n"
        f"Try it: {post.url}\n\n"
        f"{tags_en}",
        3000,
    )


def render_threads(post: Post) -> str:
    """Threads: ≤500 chars, plain, 'ты', no hashtags, link clickable."""
    cases_short = " · ".join(f"{niche}: {scen.split('—')[0].strip() if '—' in scen else scen.split(',')[0].strip()}"
                              for _, niche, scen in post.cases[:3])
    text = (
        f"{post.emoji} {post.tool_name} — {post.one_liner}. {post.pricing_short}.\n\n"
        f"{post.hook}\n\n"
        f"3 кейса: {cases_short}\n\n"
        f"{post.cta}\n\n"
        f"{post.url}"
    )
    return _trim_to(text, 500)


def render_twitter_thread(post: Post) -> list[str]:
    """X thread: list of tweets ≤280 each, 'ты', 1-2 hashtags total in last tweet."""
    tweets = []
    # Tweet 1: hook + emoji + name + price (the attention-grabber)
    t1 = f"{post.emoji} {post.tool_name} — {post.pricing_short}\n\n{post.hook}"
    tweets.append(_trim_to(t1, 270) + "\n\n🧵👇")
    # Tweet 2: what it does
    t2 = f"Что делает:\n\n{post.description}"
    tweets.append(_trim_to(t2, 280))
    # Tweet 3: cases
    for i, (e, niche, scen) in enumerate(post.cases[:3], 1):
        tweets.append(_trim_to(f"Кейс {i}/3 — {e} {niche}\n\n{scen}", 280))
    # Last tweet: pricing + CTA + link + hashtags
    tags = _build_hashtags(post, count=2)
    last = f"💰 {post.pricing_full}\n\n{post.cta}\n\n→ {post.url}\n\n{tags}"
    tweets.append(_trim_to(last, 280))
    return tweets


# ---- Helpers ----

def _trim_to(text: str, limit: int) -> str:
    """Trim to char limit, ending on word boundary if possible, with ellipsis."""
    if len(text) <= limit:
        return text
    cut = text[:limit - 1]
    # backtrack to last whitespace if mid-word
    if " " in cut[-30:]:
        cut = cut[:cut.rfind(" ")]
    return cut.rstrip() + "…"


def _ty_to_vy(text: str) -> str:
    """Heuristic ты→вы conversion. Imperfect — covers common patterns.
    For perfect quality, use GPT pass."""
    replacements = [
        # Imperative endings: установи → установите
        (r'\b([Уу]станови|[Сс]обери|[Пп]опроси|[Сс]кажи|[Зз]айди|[Зз]агрузи|[Вв]ыбери|[Пп]одмени|[Оо]публикуй|[Пп]одключи|[Пп]ройди)\b', lambda m: m.group(1) + 'те'),
        # ты → вы
        (r'\bты\b', 'вы'),
        (r'\bТы\b', 'Вы'),
        (r'\bтебя\b', 'вас'),
        (r'\bТебя\b', 'Вас'),
        (r'\bтебе\b', 'вам'),
        (r'\bТебе\b', 'Вам'),
        (r'\bтвой\b', 'ваш'),
        (r'\bТвой\b', 'Ваш'),
        (r'\bтвоё\b', 'ваше'),
        (r'\bтвоя\b', 'ваша'),
        (r'\bтвои\b', 'ваши'),
        (r'\bтвоих\b', 'ваших'),
        # Verb endings (rough): пишешь → пишете, делаешь → делаете
        (r'\b([а-я]+)ешь\b', lambda m: m.group(1) + 'ете'),
        (r'\b([а-я]+)ёшь\b', lambda m: m.group(1) + 'ёте'),
        # snail → snail
    ]
    for pattern, repl in replacements:
        text = re.sub(pattern, repl, text)
    return text


def _build_hashtags(post: Post, count: int = 8) -> str:
    """Build hashtag set for the post.
    Uses tool name + category + universal SMB tags."""
    from app.config import BRAND_NAME
    brand_slug = re.sub(r"\W+", "", BRAND_NAME)
    base = [brand_slug, "AIдляБизнеса", "SimpleAITools"]
    tool_tag = re.sub(r"\W+", "", post.tool_name)
    base.append(tool_tag)

    category_map = {
        "text-content": ["AIредактор", "копирайтинг", "AIтекст"],
        "design-visuals": ["дизайн", "соцсети", "контент"],
        "automation": ["автоматизация", "nocode", "workflow"],
        "video-reels": ["видеомонтаж", "reels", "соцсети"],
        "docs-ops": ["продуктивность", "встречи", "ИИтайпранскрипт"],
    }
    by_cat = category_map.get(post.category, ["автоматизация", "продуктивность"])
    base.extend(by_cat)

    universal = ["малыйБизнес", "smb", "продуктивность", "Telegram"]
    base.extend(universal)

    # Dedupe preserving order, take count
    seen = set()
    unique = []
    for t in base:
        if t.lower() not in seen:
            seen.add(t.lower())
            unique.append(t)
    return " ".join(f"#{t}" for t in unique[:count])


# ---- HTML→Post parser ----

def parse_telegram_html(html: str, hashtags: list[str] | None = None, category: str = "") -> Post:
    """Extract structured Post from existing Telegram HTML caption.
    Best-effort — designed for posts following the Starter AI template."""
    lines = [ln.strip() for ln in html.strip().split("\n") if ln.strip()]

    # Line 1: emoji + <b>Name</b> — one_liner. pricing_short.
    m = re.match(r'^(\S+)\s+<b>([^<]+)</b>\s*[—–-]\s*(.+?)\.\s*([^.]+)\.?\s*$', lines[0])
    if not m:
        raise ValueError(f"Can't parse header: {lines[0]!r}")
    emoji, name, one_liner, price = m.group(1), m.group(2), m.group(3), m.group(4)

    # Find <b>3 кейса...</b> section
    cases_idx = next((i for i, ln in enumerate(lines) if "<b>" in ln and "кейса" in ln.lower()), None)
    if cases_idx is None:
        raise ValueError("No '3 кейса' section found")

    # Hook + description = lines between header and cases section
    middle = lines[1:cases_idx]
    hook = middle[0] if middle else ""
    description = "\n\n".join(middle[1:]) if len(middle) > 1 else ""

    # Cases: lines after cases_idx until <b>Стоимость:</b>
    pricing_idx = next((i for i, ln in enumerate(lines) if "<b>Стоимость:</b>" in ln), None)
    if pricing_idx is None:
        raise ValueError("No <b>Стоимость:</b> found")

    cases = []
    for line in lines[cases_idx + 1:pricing_idx]:
        # "🛍 <b>Магазин:</b> описания товаров..."
        cm = re.match(r'^(\S+)\s+<b>([^<]+):</b>\s*(.+)$', line)
        if cm:
            cases.append((cm.group(1), cm.group(2), cm.group(3)))

    # Pricing full: from "Стоимость:" line, strip the prefix
    pricing_line = lines[pricing_idx]
    pricing_full = re.sub(r'^<b>Стоимость:</b>\s*', '', pricing_line)
    # Convert <b>X</b> markers to plain text for storage (renderers re-add)
    pricing_full = re.sub(r'<b>([^<]+)</b>', r'\1', pricing_full)

    # CTA: line after pricing
    cta_idx = pricing_idx + 1
    cta = lines[cta_idx] if cta_idx < len(lines) else ""

    # URL: from <a href="..."> in last line
    url_match = re.search(r'href="([^"]+)"', "\n".join(lines))
    url = url_match.group(1) if url_match else ""
    domain_match = re.search(r'>([^<]+)</a>', "\n".join(lines))
    domain = domain_match.group(1) if domain_match else url.replace("https://", "").replace("http://", "")

    return Post(
        tool_name=name,
        domain=domain,
        emoji=emoji,
        one_liner=one_liner,
        pricing_short=price,
        hook=hook,
        description=description,
        cases=cases,
        pricing_full=pricing_full,
        cta=cta,
        url=url,
        hashtags=hashtags or [],
        category=category,
    )


# ---- Demo / batch render ----

ALL_PLATFORMS = ["telegram", "instagram", "pinterest", "linkedin_ru", "linkedin_en", "threads", "twitter"]


def render_all(post: Post) -> dict:
    """Render post for all platforms. Returns dict {platform: rendered_text}."""
    return {
        "telegram":    render_telegram(post),
        "instagram":   render_instagram(post),
        "pinterest":   render_pinterest(post),  # dict (title+desc+link)
        "linkedin_ru": render_linkedin_ru(post),
        "linkedin_en": render_linkedin_en(post),  # template if no overrides
        "threads":     render_threads(post),
        "twitter":     render_twitter_thread(post),  # list of tweets
    }


if __name__ == "__main__":
    # Demo: parse Telegram post and render to all platforms
    import sys
    if len(sys.argv) > 1:
        with open(sys.argv[1]) as f:
            html = f.read()
        post = parse_telegram_html(html)
        out = render_all(post)
        for platform, content in out.items():
            print(f"\n===== {platform.upper()} =====")
            if isinstance(content, dict):
                for k, v in content.items():
                    print(f"--- {k} ---\n{v}")
            elif isinstance(content, list):
                for i, t in enumerate(content, 1):
                    print(f"--- Tweet {i}/{len(content)} ({len(t)} chars) ---\n{t}")
            else:
                print(f"({len(content)} chars)\n{content}")
