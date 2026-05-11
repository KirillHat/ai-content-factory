"""Shared helpers for Make.com scenario blueprint builders.

All builders import from here to avoid duplicating HTTP module construction,
scenario metadata, and POST/PATCH endpoints.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from app.config import (
    MAKE_TEAM_ID,
    MAKE_TOKEN,
    MAKE_ZONE,
    NOTION_TOKEN,
)

UA = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko)"
    )
}


def scenario_metadata(*, interval_seconds: int = 14400) -> dict[str, Any]:
    """Default scenario metadata with given cron interval."""
    return {
        "instant": False,
        "version": 1,
        "scenario": {
            "roundtrips": 1,
            "maxErrors": 5,
            "autoCommit": True,
            "autoCommitTriggerLast": True,
            "sequential": False,
            "confidential": False,
            "dataloss": False,
            "dlq": False,
            "freshVariables": False,
            "slots": None,
        },
        "designer": {"orphans": [], "notes": []},
        "customVariables": [],
    }


def http_notion(
    module_id: int,
    x_pos: int,
    method: str,
    url: str,
    body: str,
) -> dict[str, Any]:
    """Generic HTTP module pre-configured with Notion auth headers."""
    return {
        "id": module_id,
        "module": "http:ActionSendData",
        "version": 3,
        "parameters": {"handleErrors": False, "useNewZLibDeCompress": True},
        "mapper": {
            "url": url,
            "serializeUrl": False,
            "method": method,
            "headers": [
                {"name": "Authorization", "value": f"Bearer {NOTION_TOKEN}"},
                {"name": "Notion-Version", "value": "2022-06-28"},
                {"name": "Content-Type", "value": "application/json"},
            ],
            "qs": [],
            "bodyType": "raw",
            "contentType": "application/json",
            "data": body,
            "gzip": True,
            "timeout": "",
            "useMtls": False,
            "useQuerystring": False,
            "shareCookies": False,
            "parseResponse": True,
            "followRedirect": True,
            "rejectUnauthorized": True,
            "followAllRedirects": False,
        },
        "metadata": {"designer": {"x": x_pos, "y": 0}},
    }


def post_scenario(blueprint: dict[str, Any], *, scheduling_interval: int) -> int | None:
    """POST a new scenario to Make. Returns scenario_id or None on error."""
    payload = {
        "blueprint": json.dumps(blueprint),
        "teamId": MAKE_TEAM_ID,
        "scheduling": json.dumps(
            {"type": "indefinitely", "interval": scheduling_interval}
        ),
        "name": blueprint["name"],
    }
    req = urllib.request.Request(
        f"https://{MAKE_ZONE}.make.com/api/v2/scenarios?confirmed=true",
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Token {MAKE_TOKEN}",
            "Content-Type": "application/json",
            **UA,
        },
        method="POST",
    )
    try:
        out = json.loads(urllib.request.urlopen(req).read())
        sid = out["scenario"]["id"]
        print(f"Created scenario id={sid}")
        return sid
    except urllib.error.HTTPError as exc:
        print(f"ERROR {exc.code}: {exc.read().decode()[:500]}")
        return None


def patch_scenario(scenario_id: int, blueprint: dict[str, Any]) -> bool:
    """PATCH an existing scenario with updated blueprint."""
    payload = {"blueprint": json.dumps(blueprint), "name": blueprint["name"]}
    req = urllib.request.Request(
        f"https://{MAKE_ZONE}.make.com/api/v2/scenarios/{scenario_id}?confirmed=true",
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Token {MAKE_TOKEN}",
            "Content-Type": "application/json",
            **UA,
        },
        method="PATCH",
    )
    try:
        urllib.request.urlopen(req).read()
        print(f"PATCHED scenario id={scenario_id}")
        return True
    except urllib.error.HTTPError as exc:
        print(f"ERROR {exc.code}: {exc.read().decode()[:500]}")
        return False


def save_blueprint(blueprint: dict[str, Any], filename: str) -> str:
    """Save blueprint JSON to make_blueprints/exports/<filename>.json."""
    out_dir = os.path.join(os.path.dirname(__file__), "exports")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, filename)
    with open(out_path, "w") as f:
        json.dump(blueprint, f, indent=2)
    print(f"Saved: {out_path}")
    return out_path
