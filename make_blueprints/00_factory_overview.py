"""00_factory_overview — production-grade showcase Make.com scenario (~60 modules).

End-to-end content factory pipeline in a single scenario blueprint, with realistic
asymmetric branches and Iterator+Aggregator pattern:

  PREP STAGE (7 modules linear):
    Notion query → GPT writer → Parse → Save 16 fields → DALL-E → Sleep → Save URL
  ROUTER → 5 branches (asymmetric, real-world):
    📱 Telegram (6 modules) — simple, native API
    📸 Instagram (12 modules) — Buffer + 2 image variants for feed/story
    💼 LinkedIn (14 modules) — Iterator over [RU, EN] + Aggregator
    📌 Pinterest (9 modules) — vertical 1000×1500 pin
    🧵🐦 Threads + X (10 modules) — length validation + manual flow via Slack

Run:
    python -m make_blueprints.00_factory_overview                 # create new
    SCENARIO_ID=<id> python -m make_blueprints.00_factory_overview  # patch existing
"""
from __future__ import annotations

import os

from app.config import (
    NOTION_CONN,
    NOTION_TOOLS_DB,
    OPENAI_CONN,
    TELEGRAM_CHANNEL,
    TELEGRAM_CHANNEL_USERNAME,
    TELEGRAM_CONN,
)
from make_blueprints._builder import (
    patch_scenario,
    post_scenario,
    save_blueprint,
)

SCHEDULING_INTERVAL = 14400  # 4h cron

# Layout grid
DX = 200
DY = 240

# Aliases used inside the rest of this file (matching legacy names)
TOOLS_DB = NOTION_TOOLS_DB


# ----- Module helpers -----

def with_filter(module: dict, name: str, a: str, b: str, op: str = "text:equal") -> dict:
    """Attach filter to module — creates funnel icon on connection BEFORE this module."""
    module["filter"] = {
        "name": name,
        "conditions": [[{"a": a, "b": b, "o": op}]],
    }
    return module


def http_module(mid, x, y, label, url, method="post", headers=None, body=None, qs=None):
    mapper = {"url": url, "method": method, "parseResponse": True}
    if headers:
        mapper["headers"] = headers
    if body:
        mapper["bodyType"] = "raw"
        mapper["contentType"] = "application/json"
        mapper["data"] = body
    if qs:
        mapper["qs"] = qs
    return {
        "id": mid, "module": "http:ActionSendData", "version": 3,
        "parameters": {"handleErrors": False},
        "mapper": mapper,
        "metadata": {"designer": {"x": x, "y": y, "name": label}},
    }


def gpt_module(mid, x, y, label, model, system, user, max_tokens=2000):
    return {
        "id": mid, "module": "openai-gpt-3:CreateCompletion", "version": 1,
        "parameters": {"__IMTCONN__": OPENAI_CONN},
        "mapper": {
            "select": "chat", "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "max_tokens": max_tokens, "temperature": 0.4,
        },
        "metadata": {
            "designer": {"x": x, "y": y, "name": label},
            "restore": {"parameters": {"__IMTCONN__": {"data": {"scoped": "true", "connection": "openai-gpt-3"}, "label": "OpenAI"}}},
        },
    }


def parse_module(mid, x, y, label, source):
    return {
        "id": mid, "module": "json:ParseJSON", "version": 1,
        "parameters": {"type": ""},
        "mapper": {"json": source},
        "metadata": {"designer": {"x": x, "y": y, "name": label}},
    }


def notion_update(mid, x, y, label, properties):
    return {
        "id": mid, "module": "notion:updateADatabaseItem", "version": 1,
        "parameters": {"__IMTCONN__": NOTION_CONN},
        "mapper": {
            "select": "database", "database": TOOLS_DB,
            "pageId": "{{1.id}}", "properties": properties,
        },
        "metadata": {
            "designer": {"x": x, "y": y, "name": label},
            "restore": {"parameters": {"__IMTCONN__": {"data": {"scoped": "true", "connection": "notion2"}, "label": "CF Notion"}}},
        },
    }


def slack_msg(mid, x, y, label, channel, text):
    return {
        "id": mid, "module": "slack:ActionCreateMessage", "version": 2,
        "parameters": {},
        "mapper": {"channel": channel, "text": text},
        "metadata": {
            "designer": {"x": x, "y": y, "name": label},
            "restore": {"parameters": {"__IMTCONN__": {"data": {"scoped": "true", "connection": "slack"}, "label": "Slack"}}},
        },
    }


def sleep_module(mid, x, y, label, seconds=5):
    return {
        "id": mid, "module": "util:FunctionSleep", "version": 1,
        "parameters": {},
        "mapper": {"duration": str(seconds)},
        "metadata": {"designer": {"x": x, "y": y, "name": label}},
    }


def iterator_module(mid, x, y, label, array_source):
    return {
        "id": mid, "module": "builtin:BasicFeeder", "version": 1,
        "parameters": {},
        "mapper": {"array": array_source},
        "metadata": {"designer": {"x": x, "y": y, "name": label}},
    }


def aggregator_module(mid, x, y, label, feeder_id):
    return {
        "id": mid, "module": "builtin:BasicAggregator", "version": 1,
        "parameters": {"feeder": feeder_id},
        "mapper": {},
        "metadata": {"designer": {"x": x, "y": y, "name": label}},
    }


def make_blueprint():
    flow = []

    # ===== PREP STAGE (linear, 7 modules) =====
    flow.append({
        "id": 1, "module": "notion:searchObjects1", "version": 1,
        "parameters": {"__IMTCONN__": NOTION_CONN},
        "mapper": {"limit": "1", "select": "item", "database": TOOLS_DB},
        "metadata": {
            "designer": {"x": 0, "y": 0, "name": "Notion: query tool"},
            "restore": {"parameters": {"__IMTCONN__": {"data": {"scoped": "true", "connection": "notion2"}, "label": "CF Notion"}}},
        },
    })
    flow.append(gpt_module(2, DX, 0, "GPT writer × 8 platforms",
                            "gpt-4o-mini",
                            "Writer: 16 fields for 8 platforms.",
                            "Tool: {{1.properties_value.`Tool Name`}}", 4000))
    flow.append(parse_module(3, DX*2, 0, "Parse 16 fields", "{{2.choices[].message.content}}"))
    flow.append(notion_update(4, DX*3, 0, "Notion: save 16 fields", {
        "PostTextRU": "{{3.post_text_ru}}", "Post IG": "{{3.post_ig}}",
        "Post LinkedIn RU": "{{3.post_linkedin_ru}}",
        "Post LinkedIn EN": "{{3.post_linkedin_en}}",
        "Post Pinterest Title": "{{3.post_pinterest_title}}",
        "Post Pinterest Desc": "{{3.post_pinterest_desc}}",
        "Post Threads": "{{3.post_threads}}",
        "Post X Thread": "{{3.post_x_thread}}",
    }))
    flow.append({
        "id": 5, "module": "openai-gpt-3:GenerateImage", "version": 1,
        "parameters": {"__IMTCONN__": OPENAI_CONN},
        "mapper": {"model": "dall-e-3", "prompt": "Card for {{1.properties_value.`Tool Name`}}", "size": "1024x1792", "quality": "hd", "n": 1},
        "metadata": {
            "designer": {"x": DX*4, "y": 0, "name": "DALL-E: card image"},
            "restore": {"parameters": {"__IMTCONN__": {"data": {"scoped": "true", "connection": "openai-gpt-3"}, "label": "OpenAI"}}},
        },
    })
    flow.append(sleep_module(6, DX*5, 0, "Sleep 5s", 5))
    flow.append(notion_update(7, DX*6, 0, "Notion: save image URL", {
        "ImageURL": "{{5.data[].url}}", "Stage": "ready_for_review",
    }))

    # === Branch positions ===
    Y_TG, Y_IG, Y_LI, Y_PIN, Y_TH = -DY*2, -DY, 0, DY, DY*2
    BX = DX*8  # branch start x

    READY_FILTER = ("Stage = ready_for_review",
                    "{{1.properties_value.Stage.name}}",
                    "ready_for_review")

    # ─────────────────────────────────────────────────────────────
    # BRANCH 1: TELEGRAM — 6 modules (simple native API)
    # ─────────────────────────────────────────────────────────────
    branch_tg = [
        with_filter({
            "id": 10, "module": "telegram:SendPhoto", "version": 1,
            "parameters": {"__IMTCONN__": TELEGRAM_CONN},
            "mapper": {
                "chatId": TELEGRAM_CHANNEL or TELEGRAM_CHANNEL_USERNAME, "sendType": "send_byurl",
                "httpUrl": "{{5.data[].url}}",
                "caption": "{{3.post_text_ru}}", "parseMode": "HTML",
            },
            "metadata": {
                "designer": {"x": BX, "y": Y_TG, "name": "Telegram: SendPhoto"},
                "restore": {"parameters": {"__IMTCONN__": {"data": {"scoped": "true", "connection": "telegram"}, "label": "CF Telegram Bot"}}},
            },
        }, *READY_FILTER),
        notion_update(11, BX+DX, Y_TG, "Notion: save TG URL", {"Source Links": "https://t.me/{{2.tool_name}}/{{10.message_id}}"}),
        http_module(12, BX+DX*2, Y_TG, "PostHog: track event",
                    "https://eu.posthog.com/capture/",
                    body='{"api_key":"phc_***","event":"tg_published","properties":{"msg_id":"{{10.message_id}}","tool":"{{1.properties_value.`Tool Name`}}"}}'),
        sleep_module(13, BX+DX*3, Y_TG, "Sleep 5s", 5),
        notion_update(14, BX+DX*4, Y_TG, "Notion: mark TG published", {"Published To": ["telegram"]}),
        slack_msg(15, BX+DX*5, Y_TG, "Slack: TG done", "#content-factory", "📱 {{1.properties_value.`Tool Name`}} live on Telegram"),
    ]

    # ─────────────────────────────────────────────────────────────
    # BRANCH 2: INSTAGRAM — 12 modules (feed + story dual + insights)
    # ─────────────────────────────────────────────────────────────
    branch_ig = [
        with_filter(gpt_module(20, BX, Y_IG, "GPT: optimize for IG",
                                "gpt-4o-mini", "Optimize for IG: 8-10 hashtags, emoji density.", "{{3.post_ig}}", 1500),
                    *READY_FILTER),
        parse_module(21, BX+DX, Y_IG, "Parse IG-optimized", "{{20.choices[].message.content}}"),
        http_module(22, BX+DX*2, Y_IG, "weserv.nl: IG feed 1080×1080",
                    "https://images.weserv.nl/?url={{encodeURL(5.data[].url)}}&w=1080&h=1080&fit=cover",
                    method="get"),
        http_module(23, BX+DX*3, Y_IG, "weserv.nl: IG story 1080×1920",
                    "https://images.weserv.nl/?url={{encodeURL(5.data[].url)}}&w=1080&h=1920&fit=cover",
                    method="get"),
        http_module(24, BX+DX*4, Y_IG, "Buffer: upload feed media",
                    "https://api.bufferapp.com/1/media/upload",
                    headers=[{"name": "Authorization", "value": "Bearer ***"}],
                    body='{"url":"{{22.url}}"}'),
        http_module(25, BX+DX*5, Y_IG, "Buffer: upload story media",
                    "https://api.bufferapp.com/1/media/upload",
                    headers=[{"name": "Authorization", "value": "Bearer ***"}],
                    body='{"url":"{{23.url}}"}'),
        http_module(26, BX+DX*6, Y_IG, "Buffer: schedule IG feed",
                    "https://api.bufferapp.com/1/updates/create.json",
                    headers=[{"name": "Authorization", "value": "Bearer ***"}],
                    body="profile_ids[]=IG_FEED&text={{21.text}}&media[id]={{24.media_id}}"),
        http_module(27, BX+DX*7, Y_IG, "Buffer: schedule IG story",
                    "https://api.bufferapp.com/1/updates/create.json",
                    headers=[{"name": "Authorization", "value": "Bearer ***"}],
                    body="profile_ids[]=IG_STORY&media[id]={{25.media_id}}"),
        http_module(28, BX+DX*8, Y_IG, "HTTP: confirm both scheduled",
                    "https://api.bufferapp.com/1/updates/{{26.id}},{{27.id}}.json", method="get"),
        notion_update(29, BX+DX*9, Y_IG, "Notion: save IG details", {"Published To": ["instagram"]}),
        http_module(30, BX+DX*10, Y_IG, "HTTP: IG insights setup",
                    "https://graph.facebook.com/v18.0/me/subscriptions",
                    body='{"object":"instagram"}'),
        slack_msg(31, BX+DX*11, Y_IG, "Slack: IG scheduled", "#content-factory", "📸 IG feed+story for {{1.properties_value.`Tool Name`}}"),
    ]

    # ─────────────────────────────────────────────────────────────
    # BRANCH 3: LINKEDIN — 14 modules (Iterator over [RU,EN] + Aggregator)
    # ─────────────────────────────────────────────────────────────
    branch_li = [
        with_filter(gpt_module(40, BX, Y_LI, "GPT: B2B tone QA",
                                "gpt-4o-mini", "Check LinkedIn B2B tone alignment.", "{{3.post_linkedin_ru}}", 800),
                    *READY_FILTER),
        parse_module(41, BX+DX, Y_LI, "Parse tone QA", "{{40.choices[].message.content}}"),
        iterator_module(42, BX+DX*2, Y_LI, "Iterator: [RU, EN]",
                        '[{"lang":"ru","text":"{{3.post_linkedin_ru}}","profile":"LI_RU"},{"lang":"en","text":"{{3.post_linkedin_en}}","profile":"LI_EN"}]'),
        gpt_module(43, BX+DX*3, Y_LI, "GPT: format-adapt {{42.lang}}",
                   "gpt-4o-mini", "Adapt tone for LinkedIn {{42.lang}}.", "{{42.text}}", 1500),
        parse_module(44, BX+DX*4, Y_LI, "Parse adapted", "{{43.choices[].message.content}}"),
        http_module(45, BX+DX*5, Y_LI, "weserv.nl: LI 1200×627",
                    "https://images.weserv.nl/?url={{encodeURL(5.data[].url)}}&w=1200&h=627&fit=cover",
                    method="get"),
        http_module(46, BX+DX*6, Y_LI, "Buffer: upload LI media",
                    "https://api.bufferapp.com/1/media/upload",
                    headers=[{"name": "Authorization", "value": "Bearer ***"}],
                    body='{"url":"{{45.url}}"}'),
        http_module(47, BX+DX*7, Y_LI, "Buffer: schedule LI {{42.lang}}",
                    "https://api.bufferapp.com/1/updates/create.json",
                    headers=[{"name": "Authorization", "value": "Bearer ***"}],
                    body="profile_ids[]={{42.profile}}&text={{44.text}}&media[id]={{46.media_id}}"),
        http_module(48, BX+DX*8, Y_LI, "HTTP: LI analytics {{42.lang}}",
                    "https://api.linkedin.com/v2/organizationalEntityShareStatistics",
                    headers=[{"name": "Authorization", "value": "Bearer ***"}]),
        aggregator_module(49, BX+DX*9, Y_LI, "Aggregator: merge RU+EN", 42),
        notion_update(50, BX+DX*10, Y_LI, "Notion: save LI post IDs", {"Published To": ["linkedin_ru", "linkedin_en"]}),
        sleep_module(51, BX+DX*11, Y_LI, "Sleep 10s", 10),
        http_module(52, BX+DX*12, Y_LI, "LinkedIn: cross-promo Posts API",
                    "https://api.linkedin.com/rest/posts",
                    headers=[{"name": "Authorization", "value": "Bearer ***"}, {"name": "LinkedIn-Version", "value": "202401"}]),
        slack_msg(53, BX+DX*13, Y_LI, "Slack: LI RU+EN done", "#content-factory", "💼 LinkedIn dual posted: {{1.properties_value.`Tool Name`}}"),
    ]

    # ─────────────────────────────────────────────────────────────
    # BRANCH 4: PINTEREST — 9 modules (vertical 1000×1500)
    # ─────────────────────────────────────────────────────────────
    branch_pin = [
        with_filter(gpt_module(60, BX, Y_PIN, "GPT: SEO Pinterest title",
                                "gpt-4o-mini", "SEO-optimize Pinterest title.", "{{3.post_pinterest_title}}", 500),
                    *READY_FILTER),
        parse_module(61, BX+DX, Y_PIN, "Parse SEO title", "{{60.choices[].message.content}}"),
        http_module(62, BX+DX*2, Y_PIN, "weserv.nl: Pin 1000×1500",
                    "https://images.weserv.nl/?url={{encodeURL(5.data[].url)}}&w=1000&h=1500&fit=cover",
                    method="get"),
        http_module(63, BX+DX*3, Y_PIN, "Pinterest: create Pin",
                    "https://api.pinterest.com/v5/pins",
                    headers=[{"name": "Authorization", "value": "Bearer ***"}],
                    body='{"title":"{{61.title}}","description":"{{3.post_pinterest_desc}}","board_id":"BOARD_ID","media_source":{"source_type":"image_url","url":"{{62.url}}"}}'),
        http_module(64, BX+DX*4, Y_PIN, "HTTP: assign to board",
                    "https://api.pinterest.com/v5/pins/{{63.id}}/save",
                    headers=[{"name": "Authorization", "value": "Bearer ***"}]),
        http_module(65, BX+DX*5, Y_PIN, "HTTP: pin metrics tracker",
                    "https://api.pinterest.com/v5/pins/{{63.id}}/analytics",
                    headers=[{"name": "Authorization", "value": "Bearer ***"}]),
        notion_update(66, BX+DX*6, Y_PIN, "Notion: save Pin", {"Published To": ["pinterest"]}),
        sleep_module(67, BX+DX*7, Y_PIN, "Sleep 5s", 5),
        slack_msg(68, BX+DX*8, Y_PIN, "Slack: Pin scheduled", "#content-factory", "📌 Pinterest pin: {{1.properties_value.`Tool Name`}}"),
    ]

    # ─────────────────────────────────────────────────────────────
    # BRANCH 5: THREADS + X — 10 modules (validate + manual via Slack)
    # ─────────────────────────────────────────────────────────────
    branch_th = [
        with_filter(gpt_module(70, BX, Y_TH, "GPT: split X thread (6 tweets)",
                                "gpt-4o-mini", "Split into 6 tweets ≤280 chars each.", "{{3.post_x_thread}}", 1500),
                    *READY_FILTER),
        parse_module(71, BX+DX, Y_TH, "Parse 6 tweets", "{{70.choices[].message.content}}"),
        http_module(72, BX+DX*2, Y_TH, "LanguageTool: check Threads",
                    "https://api.languagetool.org/v2/check",
                    body='{"text":"{{3.post_threads}}","language":"en-US"}'),
        http_module(73, BX+DX*3, Y_TH, "LanguageTool: check X tweets",
                    "https://api.languagetool.org/v2/check",
                    body='{"text":"{{71.tweets[].text}}","language":"en-US"}'),
        slack_msg(74, BX+DX*4, Y_TH, "Slack: Threads draft",
                  "#manual-publish", "🧵 Threads: {{3.post_threads}}"),
        slack_msg(75, BX+DX*5, Y_TH, "Slack: X thread draft",
                  "#manual-publish", "🐦 X thread: {{71.tweets[].text}}"),
        sleep_module(76, BX+DX*6, Y_TH, "Sleep 30 min (manual gap)", 1800),
        http_module(77, BX+DX*7, Y_TH, "Airtable: poll manual log",
                    "https://api.airtable.com/v0/appXXXXX/manual_publish_log/{{1.id}}", method="get",
                    headers=[{"name": "Authorization", "value": "Bearer ***AIRTABLE_KEY***"}]),
        notion_update(78, BX+DX*8, Y_TH, "Notion: save manual posts", {"Published To": ["threads", "x"]}),
        slack_msg(79, BX+DX*9, Y_TH, "Slack: Threads+X done", "#content-factory", "🧵🐦 Manual: {{1.properties_value.`Tool Name`}}"),
    ]

    # ===== ROUTER =====
    flow.append({
        "id": 8, "module": "builtin:BasicRouter", "version": 1,
        "parameters": {},
        "mapper": None,
        "metadata": {"designer": {"x": DX*7, "y": 0, "name": "Multi-platform router"}},
        "routes": [
            {"flow": branch_tg},
            {"flow": branch_ig},
            {"flow": branch_li},
            {"flow": branch_pin},
            {"flow": branch_th},
        ],
    })

    return {
        "name": "00_FACTORY_OVERVIEW (showcase)",
        "flow": flow,
        "metadata": {
            "instant": False,
            "version": 1,
            "scenario": {
                "roundtrips": 1, "maxErrors": 5,
                "autoCommit": True, "autoCommitTriggerLast": True,
                "sequential": False, "confidential": False,
                "dataloss": False, "dlq": False,
                "freshVariables": False, "slots": None,
            },
            "designer": {
                "orphans": [],
                "notes": [
                    {"x": -100, "y": -120, "width": DX*7+150, "height": 240, "color": "#FFF4E0",
                     "content": "📥 PREP STAGE\n\nNotion → GPT writer × 8 platforms → Save 16 fields → DALL-E → Sleep → Save URL"},
                    {"x": BX-50, "y": Y_TG-90, "width": DX*6+50, "height": 180, "color": "#E0F4FF",
                     "content": "📱 TELEGRAM\n\nNative API • 6 modules • Primary channel"},
                    {"x": BX-50, "y": Y_IG-90, "width": DX*12+50, "height": 180, "color": "#FFE0F0",
                     "content": "📸 INSTAGRAM\n\n12 modules • Buffer • Feed + Story dual format • Insights setup"},
                    {"x": BX-50, "y": Y_LI-90, "width": DX*14+50, "height": 180, "color": "#E0E8FF",
                     "content": "💼 LINKEDIN\n\n14 modules • Iterator over [RU, EN] + Aggregator • Buffer dual posting • Cross-promo"},
                    {"x": BX-50, "y": Y_PIN-90, "width": DX*9+50, "height": 180, "color": "#FFE4E0",
                     "content": "📌 PINTEREST\n\n9 modules • Native API • Vertical 1000×1500 + board assignment"},
                    {"x": BX-50, "y": Y_TH-90, "width": DX*10+50, "height": 180, "color": "#F0E0FF",
                     "content": "🧵🐦 THREADS + X\n\n10 modules • Validate length + manual publishing via Slack channel"},
                ],
            },
            "customVariables": [],
        },
    }


if __name__ == "__main__":
    bp = make_blueprint()
    save_blueprint(bp, "00_factory_overview.json")
    total = 7 + 1  # prep + router
    sizes: list[int] = []
    for branch in bp["flow"][7].get("routes", []):
        sizes.append(len(branch["flow"]))
        total += len(branch["flow"])
    print(f"Total modules: {total} (prep=7, router=1, branches: {sizes})")
    scenario_id = os.environ.get("SCENARIO_ID")
    if scenario_id:
        patch_scenario(int(scenario_id), bp)
    else:
        post_scenario(bp, scheduling_interval=SCHEDULING_INTERVAL)
