from __future__ import annotations

import base64
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

from src.org import path_text

ROOT = Path(__file__).resolve().parents[1]
# 로컬 캐시. 깃에 안 넣음 → 코드만 다시 올려도 랭킹 파일이 덮이지 않음.
PATH = ROOT / "data" / "runtime" / "standings.json"


def _empty() -> dict:
    return {"matches": [], "people": {}}


def _normalize(data: Any) -> dict:
    if not isinstance(data, dict):
        return _empty()
    data.setdefault("matches", [])
    data.setdefault("people", {})
    if not isinstance(data["matches"], list):
        data["matches"] = []
    if not isinstance(data["people"], dict):
        data["people"] = {}
    return data


def _secret(name: str, default: str = "") -> str:
    env = (os.environ.get(name) or "").strip()
    if env:
        return env
    try:
        import streamlit as st

        val = st.secrets.get(name)
        if val is None and "standings" in st.secrets:
            val = st.secrets["standings"].get(name)
        return str(val or "").strip()
    except Exception:
        return default


def _remote_cfg() -> dict[str, str] | None:
    """Streamlit Cloud에서도 랭킹이 남도록 GitHub 파일에 저장한다."""
    token = _secret("github_token") or _secret("GITHUB_TOKEN")
    repo = _secret("github_repo") or _secret("GITHUB_REPO")
    path = _secret("github_standings_path") or _secret("GITHUB_STANDINGS_PATH") or "data/persisted/standings.json"
    if not token or not repo or "/" not in repo:
        return None
    return {"token": token, "repo": repo, "path": path.lstrip("/")}


def _api_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "police-battle-standings",
    }


def _remote_meta(cfg: dict[str, str]) -> tuple[dict | None, str | None]:
    url = f"https://api.github.com/repos/{cfg['repo']}/contents/{cfg['path']}"
    try:
        r = requests.get(url, headers=_api_headers(cfg["token"]), params={"ref": "main"}, timeout=20)
        if r.status_code == 404:
            r = requests.get(url, headers=_api_headers(cfg["token"]), timeout=20)
        if r.status_code == 404:
            return None, None
        if r.status_code >= 400:
            return None, None
        body = r.json()
        raw = base64.b64decode(body.get("content") or "").decode("utf-8")
        return _normalize(json.loads(raw)), body.get("sha")
    except Exception:
        return None, None


def _push_remote(data: dict) -> None:
    cfg = _remote_cfg()
    if not cfg:
        return
    _existing, sha = _remote_meta(cfg)
    payload = {
        "message": f"standings: update {datetime.now().isoformat(timespec='seconds')}",
        "content": base64.b64encode(
            json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        ).decode("ascii"),
    }
    if sha:
        payload["sha"] = sha
    url = f"https://api.github.com/repos/{cfg['repo']}/contents/{cfg['path']}"
    try:
        requests.put(url, headers=_api_headers(cfg["token"]), json=payload, timeout=30)
    except Exception:
        pass


def _load_local() -> dict:
    if not PATH.exists():
        return _empty()
    try:
        return _normalize(json.loads(PATH.read_text(encoding="utf-8")))
    except Exception:
        return _empty()


def _save_local(data: dict) -> None:
    PATH.parent.mkdir(parents=True, exist_ok=True)
    PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _load() -> dict:
    cfg = _remote_cfg()
    if cfg:
        remote, _sha = _remote_meta(cfg)
        if remote is not None:
            _save_local(remote)
            return remote
    return _load_local()


def _save(data: dict) -> None:
    data = _normalize(data)
    _save_local(data)
    _push_remote(data)


def _bucket(kind: str, mode: str) -> str:
    return f"{kind or 'exam'}|{mode or 'classic'}"


def _pid_key(org: dict, name: str) -> str:
    bits = [
        org.get("agency") or "",
        org.get("station") or "",
        org.get("unit") or "",
        org.get("team") or "",
        (name or "").strip(),
    ]
    return "|".join(bits)


def record(room: dict) -> None:
    """한 판이 끝나면 서버에 한 번만 적는다. 같은 링크로 들어온 사람이 같이 본다."""
    if not room or room.get("logged"):
        return
    players = room.get("players") or {}
    if not players or not all(p.get("done") for p in players.values()):
        return
    mid = f"{room.get('code')}-{room.get('round') or 1}-{room.get('created') or ''}"
    data = _load()
    if any(m.get("id") == mid for m in data["matches"]):
        return
    from src.rooms import player_org, ranking

    order = ranking(room)
    host_line = path_text(room.get("org") or {})
    when = datetime.now().isoformat(timespec="seconds")
    data["matches"].append(
        {
            "id": mid,
            "at": when,
            "code": room.get("code") or "",
            "org": host_line,
            "area": room.get("area_name") or "",
            "mode": room.get("mode") or "classic",
            "kind": room.get("kind") or "exam",
            "team": bool(room.get("team_battle")),
            "n": len(order),
            "top": order[0]["name"] if order else "",
        }
    )
    data["matches"] = data["matches"][-300:]
    for i, row in enumerate(order, 1):
        porg = row.get("org") if isinstance(row.get("org"), dict) else None
        if not porg:
            porg = player_org(room, row.get("pid"), players.get(row.get("pid") or ""))
        org_line = path_text(porg)
        key = _pid_key(porg, row["name"])
        p = data["people"].setdefault(
            key,
            {
                "name": row["name"],
                "org": org_line,
                "games": 0,
                "wins": 0,
                "score": 0,
                "points": 0,
            },
        )
        p["name"] = row["name"]
        p["org"] = org_line
        p["games"] = int(p.get("games") or 0) + 1
        if i == 1:
            p["wins"] = int(p.get("wins") or 0) + 1
        add_score = int(row.get("score") or 0)
        add_pts = int(row.get("points") or 0)
        p["score"] = int(p.get("score") or 0) + add_score
        p["points"] = int(p.get("points") or 0) + add_pts
        p["last"] = when
        by = p.setdefault("by", {})
        b = by.setdefault(
            _bucket(room.get("kind") or "exam", room.get("mode") or "classic"),
            {"games": 0, "wins": 0, "score": 0, "points": 0},
        )
        b["games"] = int(b.get("games") or 0) + 1
        if i == 1:
            b["wins"] = int(b.get("wins") or 0) + 1
        b["score"] = int(b.get("score") or 0) + add_score
        b["points"] = int(b.get("points") or 0) + add_pts
    _save(data)


def _row_from_bucket(p: dict, bucket: dict | None) -> dict:
    b = bucket or {}
    return {
        "name": p.get("name") or "",
        "org": p.get("org") or "",
        "games": int(b.get("games") or 0),
        "wins": int(b.get("wins") or 0),
        "score": int(b.get("score") or 0),
        "points": int(b.get("points") or 0),
    }


def people(limit: int = 12, kind: str | None = None, mode: str | None = None) -> list[dict]:
    rows: list[dict] = []
    for p in (_load().get("people") or {}).values():
        if kind or mode:
            row = _row_from_bucket(p, (p.get("by") or {}).get(_bucket(kind or "exam", mode or "classic")))
            if row["games"] <= 0:
                continue
        else:
            row = {
                "name": p.get("name") or "",
                "org": p.get("org") or "",
                "games": int(p.get("games") or 0),
                "wins": int(p.get("wins") or 0),
                "score": int(p.get("score") or 0),
                "points": int(p.get("points") or 0),
            }
        rows.append(row)
    rows.sort(key=lambda r: (-int(r.get("points") or 0), -int(r.get("wins") or 0), r.get("name") or ""))
    if limit > 0:
        return rows[:limit]
    return rows


def board(
    kind: str | None = None,
    mode: str | None = None,
    limit: int = 10,
    viewer: tuple[str, str] | None = None,
) -> list[dict]:
    """공개는 limit위까지. viewer가 그 밖이면 그 한 줄만 뒤에 붙인다."""
    rows = people(0, kind=kind, mode=mode)
    out: list[dict] = []
    mine: dict | None = None
    want_name = (viewer[0] if viewer else "") or ""
    want_org = (viewer[1] if viewer else "") or ""
    for i, r in enumerate(rows, 1):
        item = {**r, "rank": i, "self": False}
        if want_name and r.get("name") == want_name and (r.get("org") or "") == want_org:
            item["self"] = True
            mine = item
        if i <= limit:
            out.append(item)
    if mine and int(mine.get("rank") or 0) > limit:
        out.append(mine)
    return out


def recent(limit: int = 8, kind: str | None = None, mode: str | None = None) -> list[dict]:
    rows = list(_load().get("matches") or [])
    if kind:
        rows = [m for m in rows if (m.get("kind") or "exam") == kind]
    if mode:
        rows = [m for m in rows if (m.get("mode") or "classic") == mode]
    rows.sort(key=lambda r: r.get("at") or "", reverse=True)
    return rows[:limit]


def clear() -> None:
    """누적 랭킹·최근 판을 모두 비웁니다."""
    _save(_empty())


def persistence_ready() -> bool:
    """배포 환경에서 랭킹이 재배포 후에도 남는지."""
    return _remote_cfg() is not None
