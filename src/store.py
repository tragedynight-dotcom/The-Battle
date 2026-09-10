from __future__ import annotations

import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HIST = ROOT / "data" / "processed" / "edu_history.json"
SCORES = ROOT / "data" / "processed" / "team_scores.json"


def _load(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _save(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def recent_rows(n: int = 8) -> list[dict]:
    rows = _load(HIST, [])
    return list(rows[-n:])


def recent_topic_ids(n: int = 8) -> set[str]:
    return {r.get("topic_id") for r in recent_rows(n) if r.get("topic_id")}


def recent_cats(n: int = 4) -> list[str]:
    out: list[str] = []
    for r in reversed(recent_rows(n)):
        cat = r.get("cat")
        if cat and cat not in out:
            out.append(cat)
    return out


def log_topic(unit: str, topic_id: str, cat: str) -> None:
    rows = _load(HIST, [])
    today = date.today()
    rows.append(
        {
            "ym": f"{today.year}-{today.month:02d}",
            "date": today.isoformat(),
            "unit": unit,
            "topic_id": topic_id,
            "cat": cat,
        }
    )
    _save(HIST, rows)


def add_score(cat: str, team: str, points: int) -> dict:
    data = _load(SCORES, {})
    bucket = data.setdefault(cat, {})
    bucket[team] = int(bucket.get(team, 0)) + int(points)
    _save(SCORES, data)
    return data


def scores_for(cat: str) -> dict[str, int]:
    data = _load(SCORES, {})
    return {k: int(v) for k, v in (data.get(cat) or {}).items()}


def all_scores() -> dict:
    return _load(SCORES, {})
