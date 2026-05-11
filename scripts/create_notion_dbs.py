#!/usr/bin/env python3
"""Create all Notion databases for AI Content Factory under a parent page.

Run once per environment:
    NOTION_PARENT_PAGE_ID=<parent_page_id> python -m scripts.create_notion_dbs

Stores the resulting DB IDs in data/state/notion_db_ids.json for follow-up scripts.
"""
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

from app.config import NOTION_TOKEN

NOTION_VERSION = "2022-06-28"
PARENT_PAGE_ID = os.environ.get("NOTION_PARENT_PAGE_ID", "")

STATE_DIR = Path(__file__).parent.parent / "data" / "state"
STATE_DIR.mkdir(parents=True, exist_ok=True)
DB_IDS_FILE = STATE_DIR / "notion_db_ids.json"

token = NOTION_TOKEN


def notion_request(method, path, body=None):
    url = f"https://api.notion.com{path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body_resp = e.read().decode()
        print(f"ERROR {e.code} on {method} {path}: {body_resp}", file=sys.stderr)
        raise


def create_db(name, icon_emoji, properties, parent_id=PARENT_PAGE_ID):
    body = {
        "parent": {"type": "page_id", "page_id": parent_id},
        "icon": {"type": "emoji", "emoji": icon_emoji},
        "title": [{"type": "text", "text": {"content": name}}],
        "properties": properties,
    }
    result = notion_request("POST", "/v1/databases", body)
    db_id = result["id"]
    print(f"  ✓ Created: {name} (id: {db_id})")
    return db_id


def title_prop():
    return {"title": {}}


def rt():  # rich_text
    return {"rich_text": {}}


def url_prop():
    return {"url": {}}


def num(fmt="number"):
    return {"number": {"format": fmt}}


def select(*opts):
    return {"select": {"options": [{"name": o} for o in opts]}}


def multi(*opts):
    return {"multi_select": {"options": [{"name": o} for o in opts]}}


def date_prop():
    return {"date": {}}


def checkbox():
    return {"checkbox": {}}


def relation(target_db_id):
    return {
        "relation": {
            "database_id": target_db_id,
            "single_property": {},
        }
    }


# Load existing IDs if any
db_ids = {}
if DB_IDS_FILE.exists():
    db_ids = json.loads(DB_IDS_FILE.read_text())


def save_ids():
    DB_IDS_FILE.write_text(json.dumps(db_ids, indent=2))


# ============== Phase 1: Create Sources (no deps) ==============
print("\n=== Phase 1: Create Sources ===")
db_ids["Sources"] = create_db(
    "Sources",
    "📥",
    {
        "name": title_prop(),
        "url": url_prop(),
        "type": select("rss", "api", "scrape", "email"),
        "category": multi("reddit", "blog", "newsletter", "hn", "producthunt", "youtube", "github", "vc", "habr"),
        "status": select("active", "paused", "dead"),
        "last_pulled_at": date_prop(),
        "consecutive_failures": num(),
        "priority": num(),
        "notes": rt(),
    },
)
save_ids()

# ============== Phase 2: Topics_Raw (refs Sources) ==============
print("\n=== Phase 2: Create Topics_Raw ===")
db_ids["Topics_Raw"] = create_db(
    "Topics_Raw",
    "📝",
    {
        "topic_id": title_prop(),
        "title_text": rt(),  # title is reserved for page title
        "source": relation(db_ids["Sources"]),
        "source_url": url_prop(),
        "source_score": num(),
        "raw_content": rt(),
        "tags": multi("AI", "automation", "no-code", "marketing", "sales", "ops", "finance"),
        "captured_at": date_prop(),
        "hash": rt(),
        "status": select("raw", "dedup_processed", "scored", "archived", "duplicate"),
    },
)
save_ids()

# ============== Phase 3: Topics_Scored (refs Topics_Raw) ==============
print("\n=== Phase 3: Create Topics_Scored ===")
db_ids["Topics_Scored"] = create_db(
    "Topics_Scored",
    "🎯",
    {
        "topic_score_id": title_prop(),
        "topic_ref": relation(db_ids["Topics_Raw"]),
        "score_total": num(),
        "score_freshness": num(),
        "score_icp_fit": num(),
        "score_tool_mention": num(),
        "score_novelty": num(),
        "score_engagement": num(),
        "rank_today": num(),
        "icp_segment": select("owner", "freelancer", "agency", "solo"),
        "primary_format": select("guide", "review", "case", "listicle"),
        "scored_at": date_prop(),
        "status": select("pending_review", "approved", "rejected"),
        "reject_reason": rt(),
    },
)
save_ids()

# ============== Phase 4: Briefs (refs Topics_Scored) ==============
print("\n=== Phase 4: Create Briefs ===")
db_ids["Briefs"] = create_db(
    "Briefs",
    "🧭",
    {
        "brief_id": title_prop(),
        "topic_ref": relation(db_ids["Topics_Scored"]),
        "headline": rt(),
        "hook": rt(),
        "angle": select("how-to", "comparison", "case-study", "listicle", "deep-dive"),
        "key_points": rt(),
        "tools_to_mention": rt(),
        "target_keyword": rt(),
        "secondary_keywords": multi("AI", "automation", "no-code", "marketing", "sales"),
        "expected_length_words": num(),
        "concrete_numbers": rt(),
        "cta": rt(),
        "must_avoid": rt(),
        "approval_status": select("draft", "approved", "revising"),
        "created_at": date_prop(),
        "approved_at": date_prop(),
    },
)
save_ids()

# ============== Phase 5: Content_Pieces (refs Briefs, self-ref) ==============
print("\n=== Phase 5: Create Content_Pieces ===")
db_ids["Content_Pieces"] = create_db(
    "Content_Pieces",
    "📰",
    {
        "piece_id": title_prop(),
        "brief_ref": relation(db_ids["Briefs"]),
        "master_text": rt(),
        "word_count": num(),
        "reading_time_min": num(),
        "originality_score": num(),
        "brand_voice_score": num(),
        "facts_verified": num(),
        "facts_uncertain": num(),
        "generation_cost_usd": num("dollar"),
        "tokens_total": num(),
        "iterations_used": num(),
        "formats_json": rt(),
        "status": select("idea", "brief", "drafting", "review", "revisions", "approved", "localizing", "scheduled", "published", "analyzing"),
        "language": select("ru", "en", "es"),
        "created_at": date_prop(),
        "approved_at": date_prop(),
        "published_at": date_prop(),
        "cover_image_url": url_prop(),
    },
)
save_ids()

# ============== Phase 6: Assets (refs Content_Pieces) ==============
print("\n=== Phase 6: Create Assets ===")
db_ids["Assets"] = create_db(
    "Assets",
    "🎨",
    {
        "asset_id": title_prop(),
        "piece_ref": relation(db_ids["Content_Pieces"]),
        "type": select("cover", "slide", "video", "audio", "diagram"),
        "platform": select("instagram", "youtube", "tiktok", "linkedin", "twitter", "telegram", "blog", "all"),
        "cdn_url": url_prop(),
        "thumbnail_url": url_prop(),
        "width": num(),
        "height": num(),
        "duration_s": num(),
        "ab_variant": select("A", "B", "none"),
        "generation_service": select("higgsfield", "midjourney", "dalle", "runway", "heygen", "elevenlabs", "bannerbear"),
        "generation_model": rt(),
        "generation_cost_credits": num(),
        "generation_cost_usd": num("dollar"),
        "created_at": date_prop(),
    },
)
save_ids()

# ============== Phase 7: Performance_Metrics (refs Content_Pieces) ==============
print("\n=== Phase 7: Create Performance_Metrics ===")
db_ids["Performance_Metrics"] = create_db(
    "Performance_Metrics",
    "📊",
    {
        "metric_id": title_prop(),
        "piece_ref": relation(db_ids["Content_Pieces"]),
        "channel": select("twitter", "linkedin", "telegram", "instagram", "youtube", "tiktok", "email", "blog", "medium", "reddit", "substack"),
        "captured_at": date_prop(),
        "reach": num(),
        "impressions": num(),
        "engagements": num(),
        "engagement_rate": num("percent"),
        "ctr": num("percent"),
        "comments_count": num(),
        "comments_sentiment": num(),
        "saves": num(),
        "shares": num(),
        "leads_attributed": num(),
        "revenue_usd": num("dollar"),
    },
)
save_ids()

# ============== Phase 8: Brand_Voice_Examples (refs Content_Pieces) ==============
print("\n=== Phase 8: Create Brand_Voice_Examples ===")
db_ids["Brand_Voice_Examples"] = create_db(
    "Brand_Voice_Examples",
    "🗣️",
    {
        "example_id": title_prop(),
        "type": select("good", "bad", "archived"),
        "text": rt(),
        "context": rt(),
        "embedding_id": rt(),
        "performance_score": num(),
        "tag": select("hook", "structure", "verdict", "actionable", "cta", "tone", "other"),
        "added_at": date_prop(),
        "source_piece": relation(db_ids["Content_Pieces"]),
    },
)
save_ids()

# ============== Phase 9: Prompts_Versions (no deps) ==============
print("\n=== Phase 9: Create Prompts_Versions ===")
db_ids["Prompts_Versions"] = create_db(
    "Prompts_Versions",
    "📚",
    {
        "version_id": title_prop(),
        "prompt_name": select(
            "Topic_Scorer", "Brief_Generator", "Researcher", "Outliner",
            "Writer", "Critic", "Editor", "SEO_Optimizer",
            "Anti_Hype_Filter", "Brand_Voice_Validator", "Fact_Checker",
            "Twitter_Adapter", "LinkedIn_Adapter", "Telegram_Adapter",
            "Instagram_Adapter", "Shorts_Adapter", "TikTok_Adapter",
            "Email_Adapter", "Blog_Adapter", "Medium_Adapter",
            "Reddit_Adapter", "Substack_Adapter",
            "Comment_Classifier", "Comment_Response_Drafter",
            "Weekly_Learning_Analyzer",
        ),
        "version_number": rt(),
        "system_prompt": rt(),
        "user_prompt_template": rt(),
        "is_active": checkbox(),
        "ab_test_winner": checkbox(),
        "created_at": date_prop(),
        "quality_score_avg": num(),
    },
)
save_ids()

print("\n=== ALL DONE ===")
print(f"DB IDs saved to: {DB_IDS_FILE}")
print("\nSummary:")
for name, did in db_ids.items():
    print(f"  {name}: {did}")
