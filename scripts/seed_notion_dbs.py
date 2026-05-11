#!/usr/bin/env python3
"""Seed Notion databases with initial data after create_notion_dbs.py.

Run:
    python -m scripts.seed_notion_dbs

Reads DB IDs from data/state/notion_db_ids.json and the CSV in seeds/sources_seed.csv.
"""
import csv
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from app.config import NOTION_TOKEN

NOTION_VERSION = "2022-06-28"
PROJECT_ROOT = Path(__file__).parent.parent
DB_IDS_PATH = PROJECT_ROOT / "data" / "state" / "notion_db_ids.json"
SEEDS_PATH = PROJECT_ROOT / "seeds" / "sources_seed.csv"
DB_IDS = json.loads(DB_IDS_PATH.read_text()) if DB_IDS_PATH.exists() else {}

token = NOTION_TOKEN
NOW = datetime.now(timezone.utc).isoformat()


def notion(method, path, body=None):
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
        print(f"ERROR {e.code} on {method} {path}: {body_resp[:300]}", file=sys.stderr)
        raise


def title_value(text):
    return {"title": [{"type": "text", "text": {"content": text[:2000]}}]}


def rt_value(text):
    return {"rich_text": [{"type": "text", "text": {"content": text[:2000]}}]} if text else {"rich_text": []}


def url_value(url):
    return {"url": url} if url else {"url": None}


def num_value(n):
    return {"number": n} if n is not None else {"number": None}


def select_value(name):
    return {"select": {"name": name}} if name else {"select": None}


def multi_value(names):
    return {"multi_select": [{"name": n} for n in names]}


def date_value(iso):
    return {"date": {"start": iso}} if iso else {"date": None}


def relation_value(ids):
    return {"relation": [{"id": i} for i in ids]}


def checkbox_value(b):
    return {"checkbox": bool(b)}


def create_page(db_id, properties):
    body = {
        "parent": {"database_id": db_id},
        "properties": properties,
    }
    return notion("POST", "/v1/pages", body)


# ============== Phase A: Seed Sources from CSV ==============
print("\n=== Seeding Sources from CSV ===")
csv_path = SEEDS_PATH
sources_db = DB_IDS["Sources"]
created_sources = 0
with open(csv_path) as f:
    reader = csv.DictReader(f)
    for row in reader:
        category = [c.strip() for c in row["category"].split(",")] if row.get("category") else []
        priority = int(row["priority"]) if row.get("priority") else 5

        props = {
            "name": title_value(row["name"]),
            "url": url_value(row["url"]),
            "type": select_value(row["type"]),
            "category": multi_value(category),
            "status": select_value(row["status"]),
            "priority": num_value(priority),
            "consecutive_failures": num_value(0),
            "notes": rt_value(row.get("notes", "")),
        }
        try:
            create_page(sources_db, props)
            created_sources += 1
            print(f"  ✓ {row['name']}")
        except Exception as e:
            print(f"  ✗ {row['name']}: {e}")

print(f"Total Sources created: {created_sources}")

# ============== Phase B: Seed Brand_Voice_Examples ==============
print("\n=== Seeding Brand_Voice_Examples ===")
bve_db = DB_IDS["Brand_Voice_Examples"]

GOOD_EXAMPLES = [
    {
        "id": "GOOD-001-hook-double-incident",
        "tag": "hook",
        "text": "Я записывал на Granola и Otter одни и те же 12 продажных звонков за прошлый месяц. Один инструмент пропустил критическое возражение клиента в коммите на $4 800. Второй спутал озвученную цену в 3 раза.",
        "context": "Hook абзаца blog-поста; specific numbers + personal voice + contrast",
        "score": 0.85,
    },
    {
        "id": "GOOD-002-honest-failures",
        "tag": "structure",
        "text": "На 4 русских звонках точность транскрипта была ~67%. Имена контрагентов превратились в «Алисон» из «Алексея», цифры — в произвольный ряд. Granola официально поддерживает русский, но на практике это поддержка для пары фраз, не для серьёзной работы.",
        "context": "Subsection «что не зашло»; конкретные failures с примерами и числом",
        "score": 0.78,
    },
    {
        "id": "GOOD-003-anti-recommendation",
        "tag": "verdict",
        "text": "Не бери ни то ни другое, если основной язык — русский. Тут оба провальные. Бесплатная альтернатива (Whisper local) даст 88-92% точность за $0.",
        "context": "Verdict-секция в comparison-посте; редкая anti-promo",
        "score": 0.65,
    },
    {
        "id": "GOOD-004-workflow-with-timing",
        "tag": "actionable",
        "text": "QuickTime запись audio-only → Whisper.cpp с large-v3 (5-7 минут на 40-минутный звонок) → ChatGPT Free с промптом «Резюме встречи в 5 пунктах: тема, аргументы клиента, возражения, договорённости, action items». Setup занимает один раз 30 минут.",
        "context": "End-to-end workflow с timing-оценкой и конкретным prompt",
        "score": 0.70,
    },
    {
        "id": "GOOD-005-anti-promo-cta",
        "tag": "cta",
        "text": "Раз в неделю в моём канале «AI для малого бизнеса» я разбираю один такой инструмент с цифрами и собственным тестом. Никакого хайпа, никаких партнёрских ссылок — только honest opinion и pricing на момент публикации.",
        "context": "Closing CTA блог-поста; meta-aware anti-promo как trust-builder",
        "score": 0.60,
    },
]

BAD_EXAMPLES = [
    {
        "id": "BAD-001-hype-intro",
        "tag": "tone",
        "text": "AI революционизирует то, как малый бизнес работает. Представьте, если бы вы могли автоматизировать весь маркетинг и сосредоточиться на стратегии. Game-changing tools прямо сейчас доступны для вас!",
        "context": "Хайп-вступление; banned words «революционизирует», «представьте», «game-changing» + восклицание",
        "score": 0.10,
    },
    {
        "id": "BAD-002-vague-claim",
        "tag": "tone",
        "text": "Этот инструмент значительно ускоряет работу с клиентами и существенно повышает конверсию.",
        "context": "Pустые усилители «значительно», «существенно» без чисел; нет имени инструмента",
        "score": 0.15,
    },
    {
        "id": "BAD-003-pseudo-case",
        "tag": "structure",
        "text": "Одна из наших клиентских компаний внедрила AI и добилась впечатляющих результатов в продажах.",
        "context": "Pseudo-case без конкретики; «одна из», «впечатляющих» без числа",
        "score": 0.12,
    },
    {
        "id": "BAD-004-question-hook-with-emoji",
        "tag": "hook",
        "text": "🚀 Почему AI это будущее малого бизнеса? 🔥",
        "context": "Эмодзи в заголовке + вопрос-кликбейт + общий стейтмент",
        "score": 0.05,
    },
    {
        "id": "BAD-005-promo-without-proof",
        "tag": "cta",
        "text": "Запишитесь на наш курс по AI для бизнеса, чтобы научиться применять эти технологии и масштабировать ваш бизнес!",
        "context": "Pure promo без доказательств; «масштабировать» — buzzword; восклицание",
        "score": 0.08,
    },
]


def seed_voice(items, type_value):
    count = 0
    for ex in items:
        props = {
            "example_id": title_value(ex["id"]),
            "type": select_value(type_value),
            "text": rt_value(ex["text"]),
            "context": rt_value(ex["context"]),
            "performance_score": num_value(ex["score"]),
            "tag": select_value(ex["tag"]),
            "added_at": date_value(NOW),
        }
        try:
            create_page(bve_db, props)
            count += 1
            print(f"  ✓ [{type_value}] {ex['id']}")
        except Exception as e:
            print(f"  ✗ {ex['id']}: {e}")
    return count


good_count = seed_voice(GOOD_EXAMPLES, "good")
bad_count = seed_voice(BAD_EXAMPLES, "bad")
print(f"Total examples: {good_count} good + {bad_count} bad")

# ============== Phase C: Seed Prompts_Versions (skeleton entries) ==============
print("\n=== Seeding Prompts_Versions skeleton ===")
pv_db = DB_IDS["Prompts_Versions"]

PROMPTS = [
    ("Topic_Scorer", "GPT-4o, t=0.2, evaluates topics 0-1 on 5 dimensions"),
    ("Brief_Generator", "GPT-4o, t=0.4, converts approved topic to detailed brief"),
    ("Researcher", "Perplexity sonar-large-online, t=0.1, produces research dossier"),
    ("Outliner", "GPT-4o, t=0.3, structures article from brief + research"),
    ("Writer", "Claude Opus 4.7, t=0.7, writes master draft"),
    ("Critic", "GPT-4o, t=0.5, critiques first draft"),
    ("Editor", "Claude Sonnet 4.6, t=0.5, revises draft per critique"),
    ("SEO_Optimizer", "GPT-4o-mini, t=0.3, applies SEO optimization"),
    ("Anti_Hype_Filter", "GPT-4o-mini, t=0.0, detects banned words/phrases"),
    ("Brand_Voice_Validator", "GPT-4o, t=0.0, RAG-based voice match check"),
    ("Fact_Checker", "Perplexity sonar-large-online, t=0.0, verifies numeric claims"),
    ("Twitter_Adapter", "GPT-4o-mini, t=0.7, converts master to Twitter thread"),
    ("LinkedIn_Adapter", "GPT-4o-mini, t=0.7, case story format"),
    ("Telegram_Adapter", "GPT-4o-mini, t=0.7, with TG markdown"),
    ("Instagram_Adapter", "GPT-4o, t=0.6, 10-slide carousel"),
    ("Shorts_Adapter", "GPT-4o, t=0.6, YouTube Shorts script"),
    ("TikTok_Adapter", "GPT-4o, t=0.7, TikTok script"),
    ("Email_Adapter", "GPT-4o-mini, t=0.6, weekly newsletter"),
    ("Blog_Adapter", "Claude Sonnet 4.6, t=0.5, SEO long-form"),
    ("Medium_Adapter", "GPT-4o-mini, t=0.5, storytelling adaptation"),
    ("Reddit_Adapter", "GPT-4o, t=0.7, subreddit-specific first-person"),
    ("Substack_Adapter", "Claude Sonnet 4.6, t=0.6, premium deep-dive"),
    ("Comment_Classifier", "GPT-4o-mini, t=0.0, classifies comments"),
    ("Comment_Response_Drafter", "GPT-4o, t=0.5, drafts replies to comments"),
    ("Weekly_Learning_Analyzer", "GPT-4o, t=0.3, analyzes performance for self-learning"),
]

prompt_count = 0
for prompt_name, description in PROMPTS:
    props = {
        "version_id": title_value(f"{prompt_name}-v1.0.0"),
        "prompt_name": select_value(prompt_name),
        "version_number": rt_value("1.0.0"),
        "system_prompt": rt_value(f"[Source: 02_PROMPTS.md] {description}. Full system prompt stored in spec doc; this entry is a metadata skeleton for tracking."),
        "user_prompt_template": rt_value("[See 02_PROMPTS.md for variable schema]"),
        "is_active": checkbox_value(True),
        "ab_test_winner": checkbox_value(False),
        "created_at": date_value(NOW),
        "quality_score_avg": num_value(None),
    }
    try:
        create_page(pv_db, props)
        prompt_count += 1
        print(f"  ✓ {prompt_name}")
    except Exception as e:
        print(f"  ✗ {prompt_name}: {e}")

print(f"\nTotal prompts seeded: {prompt_count}")

# ============== Summary ==============
print("\n=== ALL SEEDING DONE ===")
print(f"Sources: {created_sources} entries")
print(f"Brand_Voice_Examples: {good_count + bad_count} entries (5 good + 5 bad)")
print(f"Prompts_Versions: {prompt_count} entries")
