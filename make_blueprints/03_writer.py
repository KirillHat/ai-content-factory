"""03_writer — single GPT call per tool, produces all 8 platform versions.

Trigger: cron 4h, picks rows with Stage=research_done from the Tools_Catalog DB.
Pipeline: read Notion row → GPT writes structured JSON → PATCH Notion → Stage=post_done.

Output JSON includes:
  - canonical fields: emoji, one_liner, pricing_short, hook, description, cases_json,
    pricing_full, cta, category, post_text_ru (HTML for Telegram)
  - per-platform pre-rendered versions: post_ig, post_linkedin_ru, post_linkedin_en,
    post_pinterest_title, post_pinterest_desc, post_threads, post_x_thread

Run:
    python -m make_blueprints.03_writer                    # create new
    SCENARIO_ID=4993619 python -m make_blueprints.03_writer  # patch existing
"""
from __future__ import annotations

import json
import os

from app.config import BRAND_NAME, BRAND_TAGLINE, NOTION_CONN, NOTION_TOOLS_DB, OPENAI_CONN
from make_blueprints._builder import (
    http_notion,
    patch_scenario,
    post_scenario,
    save_blueprint,
    scenario_metadata,
)

SCHEDULING_INTERVAL = 14400  # 4h cron

WRITER_PROMPT = f"""You are the Writer agent for the {BRAND_NAME} project.

{BRAND_NAME} — {BRAND_TAGLINE}.

STYLE RULES (CRITICAL):
- Write conversationally, like talking to a small-business owner friend.
- NO "What is it:" / "Best for:" labels — write as flowing prose, not a form.
- NO hype words: NOT "revolutionary", "unique", "best ever".
- Use specific scenarios in use cases (not "helps with marketing", but "writes 10 social
  posts for a pizzeria in a minute").
- Short sentences, no jargon.
- Telegram caption format with HTML <b> tags for bold.
- FACTS ONLY about what the tool does ITSELF. Do not attribute features that require
  user setup/integration as "automatic". Example: ChatGPT is a chat — it does not
  "answer customers" until you copy and paste.
- NO hashtags at the end of the post (#BrandName etc.)

HOOK RULE (second line, before 3 cases): pick ONE of 4 types per tool, rotate:
1. Counter-question: "Why do 80%% of small businesses still write all texts by hand?"
2. Comparison: "Designer at $500/project vs Canva at $15/mo — 33× cheaper, same result."
3. Specific pain: "How many times have you copied a website lead into Slack, then CRM,
   then written the first client email?"
4. Number hook: "5 minutes of setup for what used to take 2 hours per day."
FORBIDDEN: "Every morning manually...", "All meetings, documents..." (overused templates).

NICHE RULE (3 cases): never use all 3 from the same fixed set (e.g., restaurant + salon
+ event agency). Pick 3 DIFFERENT niches from 10:
- Restaurant / cafe
- Beauty salon
- Event agency
- E-commerce store
- Marketing / digital agency
- Local service (delivery, cleaning, repairs)
- Fitness studio / trainer
- Freelancer / solo entrepreneur
- School / courses / tutor
- Healthcare / clinic

Pick niches that match the tool's STRENGTH. Example:
- ChatGPT (text) → Store / Freelance / School
- Canva (visuals) → Restaurant / Salon / Fitness
- Make (automation) → Event / Healthcare / Local-service
- Notion AI (knowledge base) → Agency / Freelance / Team

CLOSING RULE: NOT a moral judgment ("Simplest start", "If you're still ..."). Use the
"Start:" format with a concrete first step.

Output ONLY this JSON:
{{
  "emoji": "📝",
  "one_liner": "short description (4-7 words)",
  "pricing_short": "Free → $X/mo",
  "hook": "1-2 sentences (counter-question / comparison / pain / number)",
  "description": "1 sentence about what the tool does, no hype",
  "cases_json": "[{{\\"emoji\\":\\"🛍\\",\\"niche\\":\\"Store\\",\\"scenario\\":\\"...\\"}},{{\\"emoji\\":\\"💆\\",\\"niche\\":\\"Local service\\",\\"scenario\\":\\"...\\"}},{{\\"emoji\\":\\"👥\\",\\"niche\\":\\"Team\\",\\"scenario\\":\\"...\\"}}]",
  "pricing_full": "Free — ..., $X/mo Tier — ...",
  "cta": "Start: first step — 1 sentence",
  "category": "text-content / design-visuals / automation / video-reels / docs-ops",
  "post_text_ru": "Full Telegram HTML post ≤1024 chars",
  "post_ig": "Instagram (plain text, ≤2200, 8-10 hashtags at end, 'you' singular, 'Link in bio')",
  "post_linkedin_ru": "LinkedIn RU (plain, 'вы' formal, 3-5 hashtags, ≤3000)",
  "post_linkedin_en": "LinkedIn EN — translated and adapted for US/EU SMB. 3-5 EN hashtags, ≤3000 chars.",
  "post_pinterest_title": "≤100 chars: Tool — one_liner (price)",
  "post_pinterest_desc": "≤500 chars: hook + 3 cases joined by ' · ' + CTA + 5 hashtags",
  "post_threads": "≤500 chars, plain, 'you', no hashtags, 3 very short cases",
  "post_x_thread": "X thread of 6 tweets ≤280 each, separated by '\\\\n\\\\n---\\\\n\\\\n', hashtags only in last tweet"
}}

CRITICAL:
- cases_json = STRINGIFIED JSON (escaped quotes), NOT an array of objects
- 3 cases in cases_json = 3 DIFFERENT niches (never restaurant + salon + event together)
- Every post_* field = ready to publish, no extra processing required
- LinkedIn EN = real translation, not "[NEEDS TRANSLATION]"
"""


def gpt_module(module_id: int, x_pos: int, model: str, messages: list, max_tokens: int, temperature: float) -> dict:
    return {
        "id": module_id,
        "module": "openai-gpt-3:CreateCompletion",
        "version": 1,
        "parameters": {"__IMTCONN__": OPENAI_CONN},
        "mapper": {
            "select": "chat",
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": 1,
            "n_completions": 1,
        },
        "metadata": {"designer": {"x": x_pos, "y": 0}},
    }


def make_blueprint() -> dict:
    properties_template: dict = {
        "PostTextRU":           {"rich_text": [{"text": {"content": "__POST__"}}]},
        "Emoji":                {"rich_text": [{"text": {"content": "__EMOJI__"}}]},
        "Hook":                 {"rich_text": [{"text": {"content": "__HOOK__"}}]},
        "Description Body":     {"rich_text": [{"text": {"content": "__DESC__"}}]},
        "Pricing Short":        {"rich_text": [{"text": {"content": "__PRICING_SHORT__"}}]},
        "Pricing Note":         {"rich_text": [{"text": {"content": "__PRICING_FULL__"}}]},
        "Cases JSON":           {"rich_text": [{"text": {"content": "__CASES_JSON__"}}]},
        "CTA":                  {"rich_text": [{"text": {"content": "__CTA__"}}]},
        "Post IG":              {"rich_text": [{"text": {"content": "__POST_IG__"}}]},
        "Post LinkedIn RU":     {"rich_text": [{"text": {"content": "__POST_LI_RU__"}}]},
        "Post LinkedIn EN":     {"rich_text": [{"text": {"content": "__POST_LI_EN__"}}]},
        "Post Pinterest Title": {"rich_text": [{"text": {"content": "__POST_PIN_T__"}}]},
        "Post Pinterest Desc":  {"rich_text": [{"text": {"content": "__POST_PIN_D__"}}]},
        "Post Threads":         {"rich_text": [{"text": {"content": "__POST_TH__"}}]},
        "Post X Thread":        {"rich_text": [{"text": {"content": "__POST_X__"}}]},
        "Stage":                {"select": {"name": "post_done"}},
    }
    update_body = json.dumps({"properties": properties_template})
    substitutions = {
        "__POST__":         "{{substring(3.post_text_ru; 0; 1900)}}",
        "__EMOJI__":        "{{3.emoji}}",
        "__HOOK__":         "{{3.hook}}",
        "__DESC__":         "{{3.description}}",
        "__PRICING_SHORT__": "{{3.pricing_short}}",
        "__PRICING_FULL__": "{{3.pricing_full}}",
        "__CASES_JSON__":   "{{3.cases_json}}",
        "__CTA__":          "{{3.cta}}",
        "__POST_IG__":      "{{substring(3.post_ig; 0; 1900)}}",
        "__POST_LI_RU__":   "{{substring(3.post_linkedin_ru; 0; 1900)}}",
        "__POST_LI_EN__":   "{{substring(3.post_linkedin_en; 0; 1900)}}",
        "__POST_PIN_T__":   "{{3.post_pinterest_title}}",
        "__POST_PIN_D__":   "{{3.post_pinterest_desc}}",
        "__POST_TH__":      "{{3.post_threads}}",
        "__POST_X__":       "{{substring(3.post_x_thread; 0; 1900)}}",
    }
    for placeholder, value in substitutions.items():
        update_body = update_body.replace(placeholder, value)

    user_msg = (
        "Tool: {{1.properties_value.`Tool Name`}}\n"
        "Category: {{1.properties_value.Category.name}}\n"
        "Short Description: {{1.properties_value.`Short Description`}}\n"
        "Features: {{1.properties_value.`Main Features`}}\n"
        "Free plan: {{1.properties_value.`Free Plan`}}\n"
        "Starting price: {{1.properties_value.`Starting Price`}}\n"
        "Pricing note: {{1.properties_value.`Pricing Note`}}\n"
        "Use case 1: {{1.properties_value.`Business Use Case 1`}}\n"
        "Use case 2: {{1.properties_value.`Business Use Case 2`}}\n"
        "Use case 3: {{1.properties_value.`Business Use Case 3`}}\n"
        "Best for: {{1.properties_value.`Best For`}}\n"
        "Link URL: {{ifempty(1.properties_value.AffiliateURL; 1.properties_value.`Official Website`)}}\n\n"
        "Write the post following the brand template. Use the Link URL exactly as given. Output JSON only."
    )

    return {
        "name": "03_writer",
        "flow": [
            {
                "id": 1,
                "module": "notion:searchObjects1",
                "version": 1,
                "parameters": {"__IMTCONN__": NOTION_CONN},
                "mapper": {"limit": "5", "select": "item", "database": NOTION_TOOLS_DB},
                "metadata": {
                    "designer": {"x": 0, "y": 0},
                    "restore": {
                        "parameters": {
                            "__IMTCONN__": {
                                "data": {"scoped": "true", "connection": "notion2"},
                                "label": "Notion connection",
                            }
                        }
                    },
                },
                "filter": {
                    "name": "research-done",
                    "conditions": [
                        [
                            {
                                "a": "{{1.properties_value.Stage.name}}",
                                "b": "research_done",
                                "o": "text:equal",
                            }
                        ]
                    ],
                },
            },
            gpt_module(
                module_id=2,
                x_pos=300,
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": WRITER_PROMPT},
                    {"role": "user", "content": user_msg},
                ],
                max_tokens=4000,
                temperature=0.5,
            ),
            {
                "id": 3,
                "module": "json:ParseJSON",
                "version": 1,
                "parameters": {"type": ""},
                "mapper": {"json": "{{2.choices[].message.content}}"},
                "metadata": {"designer": {"x": 600, "y": 0}},
            },
            http_notion(4, 900, "patch", "https://api.notion.com/v1/pages/{{1.id}}", update_body),
        ],
        "metadata": scenario_metadata(),
    }


if __name__ == "__main__":
    bp = make_blueprint()
    save_blueprint(bp, "03_writer.json")
    scenario_id = os.environ.get("SCENARIO_ID")
    if scenario_id:
        patch_scenario(int(scenario_id), bp)
    else:
        post_scenario(bp, scheduling_interval=SCHEDULING_INTERVAL)
