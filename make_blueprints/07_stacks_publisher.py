"""07_stacks_publisher — cron 3 days, publishes Stacks_Catalog rows to Telegram.

Filter: Status=Done AND Stage=ready_for_review.
1 stack per run (page_size=1) so cron runs once every 3 days = 1 stack per 3 days.

Pipeline:
  1. http POST Notion /databases/{stacks_db}/query
  2. builtin:BasicFeeder iterator
  3. telegram:SendPhoto sendType=send_byurl, photo from ImageURL, caption from PostTextRU
  4. http PATCH /pages/{id} → Stage=published, Published To=telegram

Run:
    python -m make_blueprints.07_stacks_publisher                 # create new
    SCENARIO_ID=5005451 python -m make_blueprints.07_stacks_publisher  # patch existing
"""
from __future__ import annotations

import json
import os

from app.config import (
    NOTION_STACKS_DB,
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

SCHEDULING_INTERVAL = 259200  # 3 days


def make_blueprint() -> dict:
    query_body = json.dumps(
        {
            "filter": {
                "and": [
                    {"property": "Status", "status": {"equals": "Done"}},
                    {"property": "Stage", "select": {"equals": "ready_for_review"}},
                ]
            },
            "sorts": [{"timestamp": "created_time", "direction": "ascending"}],
            "page_size": 1,
        }
    )
    update_body = json.dumps(
        {
            "properties": {
                "Stage": {"select": {"name": "published"}},
                "Published To": {"multi_select": [{"name": "telegram"}]},
            }
        }
    )

    return {
        "name": "07_stacks_publisher",
        "flow": [
            http_notion(
                1,
                0,
                "post",
                f"https://api.notion.com/v1/databases/{NOTION_STACKS_DB}/query",
                query_body,
            ),
            {
                "id": 2,
                "module": "builtin:BasicFeeder",
                "version": 1,
                "parameters": {},
                "mapper": {"array": "{{1.data.results}}"},
                "metadata": {"designer": {"x": 300, "y": 0, "name": "Iterate"}},
            },
            {
                "id": 3,
                "module": "telegram:SendPhoto",
                "version": 1,
                "parameters": {"__IMTCONN__": TELEGRAM_CONN},
                "mapper": {
                    "chatId": TELEGRAM_CHANNEL,
                    "sendType": "send_byurl",
                    "httpUrl": "{{2.properties.ImageURL.url}}",
                    "caption": "{{substring(2.properties.PostTextRU.rich_text[].plain_text; 0; 1024)}}",
                    "parseMode": "HTML",
                    "disableNotification": False,
                    "replyMarkupAssembleType": "",
                },
                "metadata": {
                    "designer": {"x": 600, "y": 0, "name": "Send to Telegram"},
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
                4,
                900,
                "patch",
                "https://api.notion.com/v1/pages/{{2.id}}",
                update_body,
            ),
        ],
        "metadata": scenario_metadata(),
    }


if __name__ == "__main__":
    bp = make_blueprint()
    save_blueprint(bp, "07_stacks_publisher.json")
    scenario_id = os.environ.get("SCENARIO_ID")
    if scenario_id:
        patch_scenario(int(scenario_id), bp)
    else:
        post_scenario(bp, scheduling_interval=SCHEDULING_INTERVAL)
