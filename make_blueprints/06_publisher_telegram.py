"""06_publisher_telegram — publishes ready_for_review rows to Telegram channel.

Pipeline:
  1. http POST /databases/{tools_db}/query  — filter Status=Done AND Stage=ready_for_review
  2. builtin:BasicFeeder iterator — expand response.results
  3. http GET ImageURL — download image bytes
  4. telegram:SendPhoto with caption from PostTextRU
  5. http PATCH /pages/{id} — flip Stage=published, add Published To=telegram

Run as a CLI:
    python -m make_blueprints.06_publisher_telegram                  # create new
    SCENARIO_ID=4987940 python -m make_blueprints.06_publisher_telegram  # patch existing
"""
from __future__ import annotations

import json
import os

from app.config import (
    NOTION_TOOLS_DB,
    TELEGRAM_CHANNEL,
    TELEGRAM_CONN,
)
from make_blueprints._builder import (
    http_notion,
    patch_scenario,
    post_scenario,
    save_blueprint,
    scenario_metadata,
)

SCHEDULING_INTERVAL = 14400  # 4h cron


def make_blueprint() -> dict:
    query_body = json.dumps(
        {
            "filter": {
                "and": [
                    {"property": "Status", "status": {"equals": "Done"}},
                    {"property": "Stage", "select": {"equals": "ready_for_review"}},
                ]
            },
            "page_size": 5,
        }
    )
    update_body = json.dumps(
        {
            "properties": {
                "Published To": {"multi_select": [{"name": "telegram"}]},
                "Stage": {"select": {"name": "published"}},
            }
        }
    )

    return {
        "name": "06_publisher_telegram",
        "flow": [
            http_notion(
                1,
                0,
                "post",
                f"https://api.notion.com/v1/databases/{NOTION_TOOLS_DB}/query",
                query_body,
            ),
            {
                "id": 2,
                "module": "builtin:BasicFeeder",
                "version": 1,
                "parameters": {},
                "mapper": {"array": "{{1.data.results}}"},
                "metadata": {"designer": {"x": 300, "y": 0, "name": "Iterate results"}},
            },
            {
                "id": 3,
                "module": "http:ActionGetFile",
                "version": 3,
                "parameters": {"handleErrors": False},
                "mapper": {
                    "url": "{{2.properties.ImageURL.url}}",
                    "serializeUrl": False,
                    "method": "get",
                    "shareCookies": False,
                },
                "metadata": {"designer": {"x": 600, "y": 0, "name": "Download image"}},
            },
            {
                "id": 4,
                "module": "telegram:SendPhoto",
                "version": 1,
                "parameters": {"__IMTCONN__": TELEGRAM_CONN},
                "mapper": {
                    "chatId": TELEGRAM_CHANNEL,
                    "sendType": "send_bydata",
                    "filename": "image.png",
                    "data": "{{3.data}}",
                    "contentType": "image/png",
                    "caption": "{{substring(2.properties.PostTextRU.rich_text[].plain_text; 0; 1000)}}",
                    "parseMode": "",
                    "disableNotification": False,
                    "replyMarkupAssembleType": "",
                },
                "metadata": {
                    "designer": {"x": 900, "y": 0, "name": "Send to Telegram"},
                    "restore": {
                        "parameters": {
                            "__IMTCONN__": {
                                "data": {"scoped": "true", "connection": "telegram"},
                                "label": "Telegram bot connection",
                            }
                        }
                    },
                },
            },
            http_notion(
                5,
                1200,
                "patch",
                "https://api.notion.com/v1/pages/{{2.id}}",
                update_body,
            ),
        ],
        "metadata": scenario_metadata(),
    }


if __name__ == "__main__":
    bp = make_blueprint()
    save_blueprint(bp, "06_publisher_telegram.json")
    scenario_id = os.environ.get("SCENARIO_ID")
    if scenario_id:
        patch_scenario(int(scenario_id), bp)
    else:
        post_scenario(bp, scheduling_interval=SCHEDULING_INTERVAL)
