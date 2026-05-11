"""Weekly export of all scenario blueprints — disaster-recovery backup.

Outputs one JSON snapshot per scenario into make_blueprints/exports/backup_YYYY-MM-DD/.
Run weekly (manually or via cron):

    python -m scripts.backup_blueprints

Scenario IDs are read from the MAKE_SCENARIO_IDS env var (comma-separated).
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from datetime import date

from app.config import MAKE_TEAM_ID, MAKE_TOKEN, MAKE_ZONE, require

UA = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko)"
    )
}


def _get_blueprint(sid: int) -> dict:
    req = urllib.request.Request(
        f"https://{MAKE_ZONE}.make.com/api/v2/scenarios/{sid}/blueprint?teamId={MAKE_TEAM_ID}",
        headers={"Authorization": f"Token {MAKE_TOKEN}", **UA},
    )
    return json.loads(urllib.request.urlopen(req).read())["response"]["blueprint"]


def _get_scenario_meta(sid: int) -> dict:
    req = urllib.request.Request(
        f"https://{MAKE_ZONE}.make.com/api/v2/scenarios/{sid}",
        headers={"Authorization": f"Token {MAKE_TOKEN}", **UA},
    )
    return json.loads(urllib.request.urlopen(req).read())["scenario"]


def main() -> None:
    require("MAKE_TOKEN")
    sid_env = os.environ.get("MAKE_SCENARIO_IDS", "").strip()
    if not sid_env:
        raise SystemExit(
            "Set MAKE_SCENARIO_IDS env var (comma-separated scenario IDs) before running."
        )
    scenarios = [int(s.strip()) for s in sid_env.split(",") if s.strip()]

    snapshot_dir = os.path.join(
        os.path.dirname(__file__),
        "..",
        "make_blueprints",
        "exports",
        f"backup_{date.today().isoformat()}",
    )
    snapshot_dir = os.path.abspath(snapshot_dir)
    os.makedirs(snapshot_dir, exist_ok=True)
    manifest: list[dict] = []

    for sid in scenarios:
        try:
            meta = _get_scenario_meta(sid)
            bp = _get_blueprint(sid)
        except urllib.error.HTTPError as exc:
            print(f"  {sid}: ERR {exc.code}")
            continue
        name = meta["name"]
        fname = f"{sid}_{name}.json"
        path = os.path.join(snapshot_dir, fname)
        with open(path, "w") as f:
            json.dump(bp, f, indent=2)
        manifest.append(
            {
                "id": sid,
                "name": name,
                "isActive": meta.get("isActive"),
                "scheduling": meta.get("scheduling"),
                "operations": meta.get("operations"),
                "errors": meta.get("errors"),
                "modules": [m["module"] for m in bp["flow"]],
            }
        )
        print(f"  {sid} {name}: saved")

    with open(os.path.join(snapshot_dir, "_manifest.json"), "w") as f:
        json.dump({"date": date.today().isoformat(), "scenarios": manifest}, f, indent=2)

    print(f"\nBackup saved: {snapshot_dir}")
    print(f"Total scenarios: {len(manifest)}")


if __name__ == "__main__":
    main()
