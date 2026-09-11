from __future__ import annotations

import hashlib
import json
import math
import os
import random
import time
from datetime import datetime, timedelta
from pathlib import Path

COUNTDOWN_SEC = 10

# 게임 모드. (이름, 설명, 문항 제한시간 초. 0이면 무제한)
MODES: dict[str, tuple[str, str, int]] = {
    "classic": ("기본전", "각자 속도로 끝까지 풉니다. 맞힌 개수로 VS합니다.", 0),
    "speed": ("스피드전", "문항마다 제한시간이 있습니다. 빨리 맞힐수록 점수가 큽니다.", 30),
    "survival": ("서바이벌", "한 문제라도 틀리면 그 자리에서 탈락합니다.", 45),
}
SIDES = ["홍팀", "청팀"]

from src.org import org_key

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / "data" / "runtime" / "rooms"


def _path(code: str) -> Path:
    return DIR / f"{code}.json"


def _lock_path(code: str) -> Path:
    return DIR / f"{code}.lock"


def _with_lock(code: str, fn):
    DIR.mkdir(parents=True, exist_ok=True)
    lock = _lock_path(code)
    for _ in range(40):
        try:
            fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_RDWR)
            os.close(fd)
            try:
                return fn()
            finally:
                lock.unlink(missing_ok=True)
        except FileExistsError:
            time.sleep(0.05)
    return fn()


def _read(code: str) -> dict | None:
    p = _path(code)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def _write(room: dict) -> None:
    DIR.mkdir(parents=True, exist_ok=True)
    p = _path(room["code"])
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(room, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(p)


def load(code: str) -> dict | None:
    code = "".join(ch for ch in (code or "") if ch.isdigit())[:4]
    if len(code) != 4:
        return None
    return _read(code)


def list_open(org: dict | None) -> list[dict]:
    key = org_key(org)
    if not key or not DIR.exists():
        return []
    out: list[dict] = []
    for p in DIR.glob("*.json"):
        try:
            room = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if org_key(room.get("org")) != key:
            continue
        if room.get("status") in ("lobby", "countdown", "play"):
            out.append(room)
    out.sort(key=lambda r: r.get("created") or "", reverse=True)
    return out


def new_code() -> str:
    for _ in range(30):
        code = f"{random.randint(1000, 9999)}"
        if not _path(code).exists():
            return code
    return f"{int(time.time()) % 10000:04d}"


def create(
    host_id: str,
    host_name: str,
    area_id: str,
    area_name: str,
    count: int,
    deck: list[dict],
    org: dict | None = None,
    mode: str = "classic",
    team_battle: bool = False,
    kind: str = "exam",
) -> dict:
    _cleanup()
    code = new_code()
    org = org or {}
    mode = mode if mode in MODES else "classic"
    limit = MODES[mode][2]
    if kind == "ox" and limit:
        limit = max(12, limit - 12)

    def inner():
        room = {
            "code": code,
            "created": datetime.now().isoformat(),
            "host_id": host_id,
            "org": org,
            "area_id": area_id,
            "area_name": area_name,
            "count": count,
            "mode": mode,
            "kind": kind,
            "limit_sec": limit,
            "team_battle": bool(team_battle),
            "round": 1,
            "status": "lobby",
            "play_at": None,
            "deck": deck,
            "players": {
                host_id: _player(host_name, SIDES[0] if team_battle else "", org),
            },
        }
        _write(room)
        return room

    return _with_lock(code, inner)


def mode_of(room: dict | None) -> str:
    m = (room or {}).get("mode") or "classic"
    return m if m in MODES else "classic"


def limit_sec(room: dict | None) -> int:
    return int((room or {}).get("limit_sec") or 0)


def set_side(code: str, pid: str, side: str) -> dict | None:
    def inner():
        room = _read(code)
        if room is None or pid not in room["players"]:
            return room
        room["players"][pid]["side"] = side if side in SIDES else ""
        _write(room)
        return room

    return _with_lock(code, inner)


def auto_sides(code: str, host_id: str) -> dict | None:
    """들어온 순서대로 홍·청을 번갈아 붙인다."""

    def inner():
        room = _read(code)
        if room is None or room.get("host_id") != host_id:
            return room
        for i, p in enumerate(room["players"].values()):
            p["side"] = SIDES[i % len(SIDES)]
        _write(room)
        return room

    return _with_lock(code, inner)


def touch(code: str, pid: str, idx: int) -> dict | None:
    """문항이 바뀐 순간을 기록한다. 제한시간은 여기서부터 센다."""

    def inner():
        room = _read(code)
        if room is None or pid not in room["players"]:
            return room
        p = room["players"][pid]
        if p.get("done") or room.get("status") != "play":
            return room
        if int(p.get("q_idx") if p.get("q_idx") is not None else -1) == int(idx) and p.get("q_at"):
            return room
        p["q_idx"] = int(idx)
        p["q_at"] = datetime.now().isoformat()
        _write(room)
        return room

    return _with_lock(code, inner)


def deadline(room: dict | None, p: dict | None = None) -> float:
    """이 문항이 끝나는 시각(epoch 초). 제한이 없으면 0."""
    lim = limit_sec(room)
    at = ""
    if relay_on(room) and p:
        side = p.get("side") or ""
        if side in SIDES:
            at = (_lane(room, side).get("q_at") or "")
    elif p:
        at = p.get("q_at") or ""
    if not lim or not at:
        return 0.0
    try:
        t = datetime.fromisoformat(at)
    except Exception:
        return 0.0
    return t.timestamp() + lim


def enter(
    org: dict,
    pid: str,
    name: str,
    area_id: str,
    area_name: str,
    count: int,
    deck: list[dict],
) -> dict | None:
    """같은 팀에 대기·진행 중인 방이 있으면 들어가고, 없으면 대기실을 연다."""
    key = org_key(org)
    if not key:
        return None
    lock_id = "g" + hashlib.md5(key.encode("utf-8")).hexdigest()[:11]

    def inner():
        _cleanup()
        open_rooms = list_open(org)
        if open_rooms:
            code = open_rooms[0]["code"]
            room = _read(code)
            if room is None:
                return None
            if pid not in room["players"]:
                room["players"][pid] = _player(name, org=org)
            else:
                room["players"][pid]["name"] = name
                if org:
                    room["players"][pid]["org"] = dict(org)
            _write(room)
            return room
        code = new_code()
        room = {
            "code": code,
            "created": datetime.now().isoformat(),
            "host_id": pid,
            "org": org,
            "area_id": area_id,
            "area_name": area_name,
            "count": count,
            "status": "lobby",
            "play_at": None,
            "deck": deck,
            "players": {pid: _player(name, org=org)},
        }
        _write(room)
        return room

    return _with_lock(lock_id, inner)


def ensure_play(code: str) -> dict | None:
    def inner():
        room = _read(code)
        if room is None:
            return None
        if room.get("status") == "lobby":
            room["status"] = "play"
            _write(room)
        return room

    return _with_lock(code, inner)


def _player(name: str, side: str = "", org: dict | None = None) -> dict:
    return {
        "name": name,
        "side": side,
        "org": dict(org or {}),
        "score": 0,
        "points": 0,
        "streak": 0,
        "best": 0,
        "out": False,
        "idx": 0,
        "q_idx": -1,
        "q_at": None,
        "done": False,
        "history": [],
        "done_at": None,
        "ms": 0,
    }


def player_org(room: dict | None, pid: str | None = None, p: dict | None = None) -> dict:
    """참가자 본인 소속. 없으면 방(방장) 소속으로 본다."""
    if p is None and room and pid:
        p = (room.get("players") or {}).get(pid) or {}
    o = (p or {}).get("org")
    if isinstance(o, dict) and (o.get("unit") or o.get("agency") or o.get("station")):
        return o
    return (room or {}).get("org") or {}


def _reset_player(p: dict) -> None:
    p["score"] = 0
    p["points"] = 0
    p["streak"] = 0
    p["best"] = 0
    p["out"] = False
    p["idx"] = 0
    p["q_idx"] = -1
    p["q_at"] = None
    p["done"] = False
    p["history"] = []
    p["done_at"] = None
    p["ms"] = 0


def _spent_ms(p: dict, ms: int) -> int:
    if int(ms or 0) > 0:
        return int(ms)
    at = p.get("q_at")
    if not at:
        return 0
    try:
        return int(max(0.0, (datetime.now() - datetime.fromisoformat(at)).total_seconds()) * 1000)
    except Exception:
        return 0


def _time_key(ms: int, at: str) -> tuple:
    """작을수록 더 빠름. 시간 기록이 없으면 뒤로 밀린다."""
    n = int(ms or 0)
    if n > 0:
        return (0, n)
    return (1, at or "9999")


def _award(mode: str, ok: bool, ms: int, limit_sec: int, streak: int, double: bool) -> int:
    """맞히면 기본 10점. 스피드전은 남은 시간만큼 최대 10점을 더 얹는다."""
    if not ok:
        return 0
    pts = 10
    if mode == "speed" and limit_sec > 0:
        left = 1.0 - (max(0, int(ms)) / (limit_sec * 1000.0))
        pts += int(round(10 * max(0.0, min(1.0, left))))
    if streak >= 3:
        pts += 2 * min(streak - 2, 5)
    if double:
        pts *= 2
    return pts


def seconds_left(room: dict | None) -> int:
    if not room or not room.get("play_at"):
        return 0
    try:
        t = datetime.fromisoformat(room["play_at"])
    except Exception:
        return 0
    return max(0, math.ceil((t - datetime.now()).total_seconds()))


def relay_on(room: dict | None) -> bool:
    return bool(room and room.get("team_battle"))


def _empty_lane() -> dict:
    return {"idx": 0, "pid": "", "q_at": None, "done": False, "done_at": None}


def _empty_relay() -> dict:
    return {
        "asked": {},
        "last": {},
        "cursor": {SIDES[0]: 0, SIDES[1]: 0},
        "order": {SIDES[0]: [], SIDES[1]: []},
        "lanes": {SIDES[0]: _empty_lane(), SIDES[1]: _empty_lane()},
    }


def _lane(room: dict, side: str) -> dict:
    """팀별 진행 칸. 홍·청이 같은 문제를 동시에 각자 푼다."""
    rel = room.setdefault("relay", _empty_relay())
    lanes = rel.setdefault("lanes", {})
    if side not in lanes or not isinstance(lanes.get(side), dict):
        lanes[side] = _empty_lane()
    return lanes[side]


def lane_of(room: dict | None, side: str) -> dict:
    if not room or side not in SIDES:
        return _empty_lane()
    return dict(_lane(room, side))


def _other_side(side: str) -> str:
    return SIDES[1] if side == SIDES[0] else SIDES[0]


def lineup(room: dict, side: str) -> list[str]:
    """그 편에 들어온 순서. 나중에 온 사람은 맨 뒤에 붙인다."""
    rel = room.setdefault("relay", _empty_relay())
    order = list((rel.get("order") or {}).get(side) or [])
    have = set(order)
    for pid, p in (room.get("players") or {}).items():
        if p.get("side") == side and pid not in have:
            order.append(pid)
    order = [pid for pid in order if pid in room["players"] and room["players"][pid].get("side") == side]
    rel.setdefault("order", {})[side] = order
    return order


def _next_in_line(room: dict, side: str) -> str:
    """그 편에서 다음 차례. 한 바퀴 돌면 다시 처음부터."""
    row = lineup(room, side)
    if not row:
        return ""
    rel = room.setdefault("relay", _empty_relay())
    cur = int((rel.get("cursor") or {}).get(side) or 0)
    n = len(row)
    for i in range(n):
        at = (cur + i) % n
        pid = row[at]
        if room["players"][pid].get("out"):
            continue
        rel.setdefault("cursor", {})[side] = (at + 1) % n
        return pid
    return ""


def _active_sides(room: dict) -> list[str]:
    got = []
    for s in SIDES:
        if any(p.get("side") == s for p in (room.get("players") or {}).values()):
            got.append(s)
    return got


def _close_relay(room: dict) -> None:
    room["status"] = "done"
    now = datetime.now().isoformat()
    for p in room["players"].values():
        p["done"] = True
        p["done_at"] = p.get("done_at") or now
    for s in SIDES:
        lane = _lane(room, s)
        lane["pid"] = ""
        lane["done"] = True
        lane["done_at"] = lane.get("done_at") or now
        lane["idx"] = len(room.get("deck") or [])
    _log_done(room)


def _finish_side(room: dict, side: str) -> None:
    lane = _lane(room, side)
    now = datetime.now().isoformat()
    lane["done"] = True
    lane["pid"] = ""
    lane["q_at"] = None
    lane["done_at"] = lane.get("done_at") or now
    lane["idx"] = len(room.get("deck") or [])
    for p in (room.get("players") or {}).values():
        if p.get("side") == side:
            p["done"] = True
            p["done_at"] = p.get("done_at") or now
            p["idx"] = len(room.get("deck") or [])
    if all(_lane(room, s).get("done") for s in _active_sides(room) or SIDES):
        _close_relay(room)


def _deal_side(room: dict, side: str) -> None:
    """한 팀이 덱을 끝까지 푼다. 팀 안에서는 들어온 순서대로 한 명씩."""
    if side not in SIDES:
        return
    deck = room.get("deck") or []
    lane = _lane(room, side)
    if lane.get("done"):
        return
    idx = int(lane.get("idx") or 0)
    if idx >= len(deck):
        _finish_side(room, side)
        return
    pid = _next_in_line(room, side)
    if not pid:
        _finish_side(room, side)
        return
    now = datetime.now().isoformat()
    lane["pid"] = pid
    lane["q_at"] = now
    p = room["players"][pid]
    p["idx"] = idx
    p["q_idx"] = idx
    p["q_at"] = now


def _deal_all_sides(room: dict) -> None:
    sides = _active_sides(room) or list(SIDES)
    for s in sides:
        lane = _lane(room, s)
        if not lane.get("done") and not lane.get("pid"):
            _deal_side(room, s)


def begin_if_due(code: str) -> dict | None:
    def inner():
        room = _read(code)
        if room is None:
            return None
        if room.get("status") == "countdown" and seconds_left(room) <= 0:
            room["status"] = "play"
            if relay_on(room):
                room["relay"] = room.get("relay") or _empty_relay()
                _deal_all_sides(room)
            _write(room)
        return room

    return _with_lock(code, inner)


def _thin_side(room: dict) -> str:
    """사람이 적은 편. 편 대항이 켜져 있으면 들어오는 대로 여기에 붙인다."""
    tally = {s: 0 for s in SIDES}
    for p in room["players"].values():
        if p.get("side") in tally:
            tally[p["side"]] += 1
    return min(SIDES, key=lambda s: tally[s])


def join(code: str, pid: str, name: str, org: dict | None = None) -> tuple[dict | None, str]:
    """방에 합류한다. 같은 별명·소속 자리가 있으면 그 id를 이어받는다. (room, 실제 pid)"""
    code = "".join(ch for ch in (code or "") if ch.isdigit())[:4]
    pid = (pid or "").strip()
    name = (name or "").strip()
    if len(code) != 4 or not pid:
        return None, pid

    def inner():
        room = _read(code)
        if room is None:
            return None, pid
        use = resolve_pid(room, pid, name, org)
        if use not in room["players"]:
            side = _thin_side(room) if room.get("team_battle") else ""
            room["players"][use] = _player(name, side, org)
        else:
            room["players"][use]["name"] = name or room["players"][use].get("name") or ""
            if org:
                room["players"][use]["org"] = dict(org)
            if room.get("team_battle") and not room["players"][use].get("side"):
                room["players"][use]["side"] = _thin_side(room)
        _write(room)
        return room, use

    return _with_lock(code, inner)


def resolve_pid(room: dict | None, pid: str, name: str, org: dict | None = None) -> str:
    """쿠키가 바뀌어도 같은 별명(+소속)이면 기존 참가 자리를 다시 잡는다."""
    pid = (pid or "").strip()
    players = (room or {}).get("players") or {}
    if pid and pid in players:
        return pid
    want = (name or "").strip()
    if not room or not want:
        return pid
    hits = [p for p, row in players.items() if (row.get("name") or "").strip() == want]
    if not hits:
        return pid
    if len(hits) == 1:
        return hits[0]
    key = org_key(org)
    keyed = [p for p in hits if org_key(player_org(room, p, players.get(p))) == key] if key else []
    pool = keyed if keyed else []
    if len(pool) == 1:
        return pool[0]
    if len(pool) > 1:
        lanes = ((room.get("relay") or {}).get("lanes") or {})
        for s in SIDES:
            bat = (lanes.get(s) or {}).get("pid") or ""
            if bat in pool:
                return bat
        return pool[0]
    # 동명이인·소속 불명이면 새 자리
    return pid


def start(code: str, host_id: str) -> dict | None:
    def inner():
        room = _read(code)
        if room is None or room.get("host_id") != host_id:
            return room
        if room.get("status") not in ("lobby", "done"):
            return room
        room["status"] = "countdown"
        room["play_at"] = (datetime.now() + timedelta(seconds=COUNTDOWN_SEC)).isoformat()
        room["relay"] = _empty_relay()
        for p in room["players"].values():
            _reset_player(p)
        _write(room)
        return room

    return _with_lock(code, inner)


def _history_map(p: dict) -> dict[int, dict]:
    return {int(h["idx"]): h for h in p.get("history") or []}


def _all_answered(p: dict, n: int) -> bool:
    got = set(_history_map(p))
    return n > 0 and all(i in got for i in range(n))


def _mark_answer(room: dict, pid: str, idx: int, choice: int, answer: int, ms: int, double: bool) -> tuple[bool, int]:
    p = room["players"][pid]
    mode = mode_of(room)
    ok = int(choice) == int(answer)
    streak = (int(p.get("streak") or 0) + 1) if ok else 0
    p["streak"] = streak
    p["best"] = max(int(p.get("best") or 0), streak)
    used = _spent_ms(p, ms)
    pts = _award(mode, ok, used, limit_sec(room), streak, bool(double))
    by = _history_map(p)
    by[idx] = {
        "idx": idx,
        "choice": int(choice),
        "answer": int(answer),
        "ok": ok,
        "ms": used,
        "pts": pts,
    }
    p["history"] = [by[i] for i in sorted(by)]
    p["score"] = sum(1 for h in p["history"] if h.get("ok"))
    p["points"] = sum(int(h.get("pts") or 0) for h in p["history"])
    p["ms"] = sum(int(h.get("ms") or 0) for h in p["history"])
    if mode == "survival" and not ok:
        p["out"] = True
        if not relay_on(room):
            p["done"] = True
            p["idx"] = len(room.get("deck") or [])
            p["done_at"] = datetime.now().isoformat()
    return ok, pts


def answer(code: str, pid: str, choice: int, answer: int, ms: int = 0, double: bool = False) -> dict | None:
    def inner():
        room = _read(code)
        if room is None or pid not in room["players"]:
            return room
        if room.get("status") == "countdown" and seconds_left(room) <= 0:
            room["status"] = "play"
            if relay_on(room):
                room["relay"] = room.get("relay") or _empty_relay()
                _deal_all_sides(room)
        if room.get("status") != "play":
            return room
        p = room["players"][pid]
        if p.get("done") or p.get("out"):
            return room
        deck = room.get("deck") or []
        if relay_on(room):
            side = p.get("side") or ""
            if side not in SIDES:
                return room
            rel = room.setdefault("relay", _empty_relay())
            lane = _lane(room, side)
            if lane.get("done") or lane.get("pid") != pid:
                return room
            idx = int(lane.get("idx") or 0)
            if idx < 0 or idx >= len(deck):
                return room
            ok, pts = _mark_answer(room, pid, idx, choice, answer, ms, double)
            asked = rel.setdefault("asked", {})
            asked[pid] = int(asked.get(pid, 0)) + 1
            last = rel.setdefault("last", {})
            if not isinstance(last, dict):
                last = {}
                rel["last"] = last
            last[side] = {
                "idx": idx,
                "pid": pid,
                "name": p.get("name") or "",
                "side": side,
                "ok": ok,
                "pts": pts,
            }
            lane["idx"] = idx + 1
            lane["pid"] = ""
            lane["q_at"] = None
            _deal_side(room, side)
            _write(room)
            return room
        idx = int(p.get("idx") or 0)
        if idx < 0 or idx >= len(deck):
            return room
        _mark_answer(room, pid, idx, choice, answer, ms, double)
        if mode_of(room) == "survival" and p.get("out"):
            if all(x.get("done") for x in room["players"].values()):
                room["status"] = "done"
        _write(room)
        return room

    return _with_lock(code, inner)


def expire_turn(code: str, answer: int, double: bool = False, side: str = "") -> dict | None:
    """팀 차례에서 제한시간이 지났으면 지금 푸는 사람을 틀린 것으로 처리한다."""

    def inner():
        room = _read(code)
        if room is None or not relay_on(room) or room.get("status") != "play":
            return room
        want = side if side in SIDES else ""
        targets = [want] if want else list(SIDES)
        for s in targets:
            lane = _lane(room, s)
            pid = lane.get("pid") or ""
            if not pid or pid not in room["players"]:
                continue
            p = room["players"][pid]
            lim = limit_sec(room)
            dl = deadline(room, p)
            if lim and dl and time.time() < dl:
                continue
            return None
        return room

    caught = _with_lock(code, inner)
    if caught is None:
        room = _read(code) or {}
        want = side if side in SIDES else ""
        for s in ([want] if want else list(SIDES)):
            lane = _lane(room, s) if room else {}
            pid = (lane or {}).get("pid") or ""
            if not pid:
                continue
            p = ((room.get("players") or {}).get(pid) or {})
            lim = limit_sec(room)
            dl = deadline(room, p)
            if lim and dl and time.time() >= dl:
                return answer(code, pid, -1, answer, ms=lim * 1000, double=double)
        return room
    return caught


def seek(code: str, pid: str, idx: int) -> dict | None:
    def inner():
        room = _read(code)
        if room is None or pid not in room["players"]:
            return room
        p = room["players"][pid]
        if p.get("done") or room.get("status") != "play":
            return room
        n = len(room.get("deck") or [])
        if n <= 0:
            return room
        want = max(0, min(int(idx), n - 1))
        # 스피드전·서바이벌은 되돌아가지 못한다.
        if mode_of(room) != "classic" and want < int(p.get("idx") or 0):
            return room
        p["idx"] = want
        _write(room)
        return room

    return _with_lock(code, inner)


def finish(code: str, pid: str) -> dict | None:
    def inner():
        room = _read(code)
        if room is None or pid not in room["players"]:
            return room
        p = room["players"][pid]
        if p.get("done") or room.get("status") != "play":
            return room
        deck = room.get("deck") or []
        if not _all_answered(p, len(deck)):
            return room
        p["done"] = True
        p["idx"] = len(deck)
        p["done_at"] = datetime.now().isoformat()
        if room["players"] and all(x.get("done") for x in room["players"].values()):
            room["status"] = "done"
            _log_done(room)
        _write(room)
        return room

    return _with_lock(code, inner)


def _log_done(room: dict) -> None:
    if room.get("logged"):
        return
    from src import standings

    standings.record(room)
    room["logged"] = True


def ranking(room: dict) -> list[dict]:
    mode = mode_of(room)
    rows: list[dict] = []
    for pid, p in (room.get("players") or {}).items():
        rows.append(
            {
                "pid": pid,
                "name": p.get("name") or "",
                "side": p.get("side") or "",
                "org": player_org(room, pid, p),
                "score": int(p.get("score") or 0),
                "points": int(p.get("points") or 0),
                "best": int(p.get("best") or 0),
                "idx": int(p.get("idx") or 0),
                "done": bool(p.get("done")),
                "out": bool(p.get("out")),
                "at": p.get("done_at") or "9999",
                "ms": int(p.get("ms") or 0),
            }
        )
    if mode == "speed":
        rows.sort(key=lambda r: (-r["points"], _time_key(r["ms"], r["at"]), r["name"]))
    elif mode == "survival":
        rows.sort(key=lambda r: (r["out"], -r["score"], _time_key(r["ms"], r["at"]), r["name"]))
    else:
        rows.sort(key=lambda r: (-r["score"], -r["points"], _time_key(r["ms"], r["at"]), r["name"]))
    return rows


def team_ranking(room: dict) -> list[dict]:
    agg: dict[str, dict] = {}
    for p in (room.get("players") or {}).values():
        side = p.get("side") or ""
        if side not in SIDES:
            continue
        a = agg.setdefault(
            side,
            {"side": side, "n": 0, "score": 0, "points": 0, "alive": 0, "ms": 0, "at": "9999", "prog": 0},
        )
        a["n"] += 1
        a["score"] += int(p.get("score") or 0)
        a["points"] += int(p.get("points") or 0)
        a["ms"] += int(p.get("ms") or 0)
        if not p.get("out"):
            a["alive"] += 1
    for s, a in agg.items():
        lane = _lane(room, s)
        a["prog"] = int(lane.get("idx") or 0)
        if lane.get("done"):
            a["at"] = lane.get("done_at") or a["at"]
            a["prog"] = len(room.get("deck") or [])
    key = "points" if mode_of(room) == "speed" else "score"
    rows = sorted(agg.values(), key=lambda r: (-r[key], _time_key(r["ms"], r["at"]), r["side"]))
    return rows


def wrong_indices(room: dict) -> list[int]:
    """방 안 누군가 한 명이라도 틀린 문항 번호."""
    bad: set[int] = set()
    for p in (room.get("players") or {}).values():
        for h in p.get("history") or []:
            if not h.get("ok"):
                bad.add(int(h.get("idx") or 0))
    n = len(room.get("deck") or [])
    return sorted(i for i in bad if 0 <= i < n)


def restart(code: str, host_id: str, deck: list[dict]) -> dict | None:
    def inner():
        room = _read(code)
        if room is None or room.get("host_id") != host_id:
            return room
        room["deck"] = deck
        room["count"] = len(deck)
        room["round"] = int(room.get("round") or 1) + 1
        room["status"] = "countdown"
        room["play_at"] = (datetime.now() + timedelta(seconds=COUNTDOWN_SEC)).isoformat()
        room["relay"] = _empty_relay()
        for p in room["players"].values():
            _reset_player(p)
        _write(room)
        return room

    return _with_lock(code, inner)


def _cleanup() -> None:
    if not DIR.exists():
        return
    cut = datetime.now() - timedelta(hours=12)
    for p in DIR.glob("*.json"):
        try:
            room = json.loads(p.read_text(encoding="utf-8"))
            created = datetime.fromisoformat(room.get("created") or "")
            if created < cut:
                p.unlink(missing_ok=True)
        except Exception:
            continue
