"""08_publisher_multi — Buffer-based auto-posting to Instagram / LinkedIn / Pinterest.

Pipeline:
  1. Notion query — Stage=published, "Published To" missing the target platform
  2. For each row → read pre-rendered "Post {Platform}" field from Notion
  3. POST to Buffer API → schedule on profile (IG / LinkedIn / Pinterest)
  4. PATCH Notion → add platform to "Published To"

Buffer API docs:
  https://buffer.com/developers/api/createupdate
  Auth: OAuth2 access_token (Buffer dashboard → Apps → Create App)

Setup (one-time):
  1. Sign up at buffer.com (free tier = 3 channels)
  2. Connect Instagram Business, LinkedIn Page, Pinterest Board
  3. Generate Access Token at https://buffer.com/developers/apps
  4. Set BUFFER_TOKEN in your .env file
  5. Get profile_ids via GET /profiles, set them in .env
  6. Run: python -m make_blueprints.08_publisher_multi
"""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request

from app.config import (
    BUFFER_IG_PROFILE,
    BUFFER_LINKEDIN_EN_PROFILE,
    BUFFER_LINKEDIN_RU_PROFILE,
    BUFFER_PINTEREST_PROFILE,
    BUFFER_TOKEN,
    NOTION_TOKEN,
)
from app.config import (
    NOTION_TOOLS_DB as TOOLS_DB,
)

# Buffer profile IDs from env (configurable per-platform)
PROFILE_IDS = {
    "instagram":   BUFFER_IG_PROFILE,
    "linkedin_ru": BUFFER_LINKEDIN_RU_PROFILE,
    "linkedin_en": BUFFER_LINKEDIN_EN_PROFILE,
    "pinterest":   BUFFER_PINTEREST_PROFILE,
}

# Какие платформы публикуем (можно отключить отдельные)
ENABLED_PLATFORMS = ["instagram", "linkedin_ru", "linkedin_en", "pinterest"]

# Маппинг Notion field → Buffer platform
PLATFORM_TO_FIELD = {
    "instagram":    "Post IG",
    "linkedin_ru":  "Post LinkedIn RU",
    "linkedin_en":  "Post LinkedIn EN",
    "pinterest_t":  "Post Pinterest Title",
    "pinterest_d":  "Post Pinterest Desc",
}


def get_buffer_token() -> str:
    if not BUFFER_TOKEN:
        raise RuntimeError(
            "BUFFER_TOKEN env var is not set.\n"
            "Setup:\n"
            "  1. https://buffer.com/developers/apps → Create App\n"
            "  2. Generate Access Token\n"
            "  3. Add BUFFER_TOKEN=... to your .env file"
        )
    return BUFFER_TOKEN


def query_published_rows():
    """Get all rows with Stage=published that haven't been auto-published yet."""
    body = json.dumps({
        "filter": {
            "and": [
                {"property": "Stage", "select": {"equals": "published"}},
                # Optional: filter rows missing one of the platforms in Published To
            ]
        },
        "page_size": 50,
    })
    req = urllib.request.Request(
        f"https://api.notion.com/v1/databases/{TOOLS_DB}/query",
        data=body.encode(),
        method="POST",
        headers={
            "Authorization": f"Bearer {NOTION_TOKEN}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0",
        },
    )
    return json.loads(urllib.request.urlopen(req).read()).get("results", [])


def buffer_create_update(profile_id, text, image_url=None, link=None):
    """POST /updates/create.json — schedule a Buffer update."""
    token = get_buffer_token()
    payload = {
        "profile_ids[]": profile_id,
        "text": text,
        "now": "true",  # post immediately; or use "scheduled_at" for queueing
    }
    if image_url:
        payload["media[link]"] = image_url
        payload["media[picture]"] = image_url
        payload["media[thumbnail]"] = image_url
    if link:
        payload["media[link]"] = link

    data = "&".join(f"{k}={urllib.parse.quote_plus(str(v))}" for k, v in payload.items()).encode()
    req = urllib.request.Request(
        "https://api.bufferapp.com/1/updates/create.json",
        data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    try:
        return json.loads(urllib.request.urlopen(req).read())
    except urllib.error.HTTPError as e:
        return {"success": False, "message": e.read().decode()[:200]}


def mark_published_in_notion(page_id, platforms_added: list[str]):
    """Add platform names to Published To multi_select."""
    # First read existing Published To
    page = json.loads(urllib.request.urlopen(urllib.request.Request(
        f"https://api.notion.com/v1/pages/{page_id}",
        headers={
            "Authorization": f"Bearer {NOTION_TOKEN}",
            "Notion-Version": "2022-06-28",
            "User-Agent": "Mozilla/5.0",
        },
    )).read())
    current = [s["name"] for s in page["properties"].get("Published To", {}).get("multi_select", [])]
    new = list(set(current + platforms_added))

    body = json.dumps({
        "properties": {
            "Published To": {"multi_select": [{"name": p} for p in new]}
        }
    })
    req = urllib.request.Request(
        f"https://api.notion.com/v1/pages/{page_id}",
        data=body.encode(),
        method="PATCH",
        headers={
            "Authorization": f"Bearer {NOTION_TOKEN}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0",
        },
    )
    return json.loads(urllib.request.urlopen(req).read())


def get_text(properties, field):
    rt = properties.get(field, {}).get("rich_text", [])
    return "".join(b.get("plain_text", "") for b in rt)


def publish_row(row):
    """Publish single row to all enabled platforms."""
    p = row["properties"]
    (p.get("Tool Name", {}).get("title") or [{}])[0].get("plain_text", "")
    image_url = p.get("ImageURL", {}).get("url", "")
    affiliate = p.get("AffiliateURL", {}).get("url", "") or p.get("Official Website", {}).get("url", "")
    already_published = [s["name"] for s in p.get("Published To", {}).get("multi_select", [])]
    new_platforms = []

    for plat in ENABLED_PLATFORMS:
        if plat in already_published:
            print(f"  skip {plat} (already published)")
            continue
        if not PROFILE_IDS.get(plat):
            print(f"  skip {plat} (PROFILE_ID env var not set)")
            continue
        text_field = PLATFORM_TO_FIELD.get(plat) or f"Post {plat.upper()}"
        text = get_text(p, text_field)
        if not text:
            print(f"  skip {plat} (no rendered text)")
            continue
        res = buffer_create_update(PROFILE_IDS[plat], text, image_url=image_url, link=affiliate)
        if res.get("success"):
            print(f"  ✓ {plat} → posted")
            new_platforms.append(plat)
        else:
            print(f"  ✗ {plat}: {res.get('message')}")

    if new_platforms:
        mark_published_in_notion(row["id"], new_platforms)


def main():
    try:
        get_buffer_token()
    except RuntimeError as e:
        print(e)
        return

    rows = query_published_rows()
    print(f"Found {len(rows)} published rows")
    for row in rows:
        name = (row["properties"].get("Tool Name", {}).get("title") or [{}])[0].get("plain_text", "")
        print(f"\n→ {name}")
        publish_row(row)


if __name__ == "__main__":
    main()
