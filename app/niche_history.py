"""niche_history — counts niche frequency across published rows.

Used by the writer to enforce rotation:
    python -m app.niche_history
    → outputs sorted niche counter (most-used → least-used) + a hint string

Exposes for Make scenario integration:
    get_niche_hint() → "Used often: Restaurant (3), Freelancer (2). Use: clinic, fitness, school."
"""
import json
import urllib.request
from collections import Counter

from app.config import NOTION_TOKEN
from app.config import NOTION_TOOLS_DB as TOOLS_DB

# Canonical 10 niches
NICHES = [
    "Ресторан", "Салон красоты", "Event-агентство", "Магазин",
    "Маркетинг-агентство", "Локальный сервис", "Фитнес-студия",
    "Фриланс", "Школа / курсы", "Медицина",
]


def get_published_rows():
    """Fetch all rows with Stage=published or post_done."""
    body = json.dumps({
        "filter": {
            "or": [
                {"property": "Stage", "select": {"equals": "published"}},
                {"property": "Stage", "select": {"equals": "ready_for_review"}},
                {"property": "Stage", "select": {"equals": "post_done"}},
            ]
        },
        "page_size": 100,
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


def get_text(p, field):
    rt = p.get(field, {}).get("rich_text", [])
    return "".join(b.get("plain_text", "") for b in rt)


def count_niches() -> Counter:
    counter = Counter()
    rows = get_published_rows()
    for row in rows:
        cases_raw = get_text(row["properties"], "Cases JSON")
        if not cases_raw:
            continue
        try:
            cases = json.loads(cases_raw)
        except Exception:
            continue
        for c in cases:
            niche = c.get("niche", "").strip()
            # Canonicalize: lowercase, basic match against canonical list
            for canonical in NICHES:
                if canonical.lower() in niche.lower() or niche.lower() in canonical.lower():
                    counter[canonical] += 1
                    break
            else:
                counter[niche] += 1  # unknown niche — track as-is
    return counter


def get_niche_hint() -> str:
    """Return a short hint for writer prompt indicating which niches are over-used.

    Example output:
      "Часто используются: Магазин (3), Фриланс (3), Школа / курсы (2).
       Реже: Медицина (1), Фитнес-студия (1).
       Не использованы: Маркетинг-агентство, Локальный сервис.
       ВЫБЕРИ 3 ниши из реже-используемых."
    """
    counter = count_niches()
    used = {n: counter.get(n, 0) for n in NICHES}
    sorted_used = sorted(used.items(), key=lambda x: -x[1])

    high = [f"{n} ({c})" for n, c in sorted_used if c >= 3]
    mid = [f"{n} ({c})" for n, c in sorted_used if 1 <= c < 3]
    low = [n for n, c in sorted_used if c == 0]

    lines = []
    if high:
        lines.append(f"Часто использованы: {', '.join(high)}.")
    if mid:
        lines.append(f"Реже: {', '.join(mid)}.")
    if low:
        lines.append(f"НЕ использованы: {', '.join(low)}.")
    lines.append("ВЫБЕРИ 3 ниши с приоритетом на «не использованы» и «реже». Не повторяй частые.")
    return "\n".join(lines)


if __name__ == "__main__":
    counter = count_niches()
    print("=== Niche frequency ===")
    for n in NICHES:
        print(f"  {n:25} {counter.get(n, 0)}")
    print("\n=== Hint for writer ===")
    print(get_niche_hint())
