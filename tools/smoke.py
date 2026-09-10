"""화면과 방 로직을 브라우저 없이 한 바퀴 돌려 본다."""
from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from streamlit.testing.v1 import AppTest  # noqa: E402

from src import rooms  # noqa: E402
from src.exam import make_ox_quiz, make_quiz  # noqa: E402


def screens() -> None:
    for phase, kind in [
        ("hub", "exam"),
        ("enter", "exam"),
        ("host_setup", "exam"),
        ("host_setup", "ox"),
    ]:
        at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=90)
        at.session_state["unlocked"] = True
        at.session_state["phase"] = phase
        at.session_state["quiz_kind"] = kind
        if phase == "host_setup":
            at.session_state["host_draft"] = {
                "org": {"agency": "광주광역시경찰청", "station": "광주동부", "unit": "학동지구대", "team": "1팀"},
                "name": "김순경",
            }
        at.run()
        assert not at.exception, f"{phase}/{kind}: {at.exception}"
        print(f"  ok  {phase}/{kind}")


def live_screens(mode: str, kind: str) -> None:
    """대기실 · 카운트다운 · 문제 · 결과 화면을 실제로 그려 본다."""
    deck, aid, name = (make_ox_quiz if kind == "ox" else make_quiz)("rand_exam", 6, 11)
    for i, row in enumerate(deck):
        row["x2"] = i == 0
    org = {"agency": "광주광역시경찰청", "station": "광주동부", "unit": "학동지구대", "team": "1팀"}
    room = rooms.create("me", "김순경", aid, name, len(deck), deck, org=org,
                        mode=mode, team_battle=False, kind=kind)
    code = room["code"]
    rooms.join(code, "p2", "이경장")
    rooms.auto_sides(code, "me")

    def draw(phase: str, tag: str) -> None:
        at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=90)
        at.session_state["unlocked"] = True
        at.session_state["pid"] = "me"
        at.session_state["phase"] = phase
        at.session_state["code"] = code
        at.session_state["quiz_kind"] = kind
        at.run()
        assert not at.exception, f"{mode}/{kind} {tag}: {at.exception}"
        print(f"  ok  {mode}/{kind} {tag}")

    draw("lobby", "대기실")
    rooms.start(code, "me")
    draw("play", "카운트다운")
    r = rooms.load(code)
    r["status"] = "play"
    r["play_at"] = None
    rooms._write(r)
    draw("play", "문제")
    for who in ("me", "p2"):
        for i in range(len(deck)):
            live = rooms.load(code)
            if live["players"][who].get("done"):
                break
            rooms.touch(code, who, i)
            rooms.answer(code, who, 0, 0 if who == "me" else 9, ms=900, double=(i == 0))
            if not rooms.load(code)["players"][who].get("done"):
                rooms.seek(code, who, i + 1) if i + 1 < len(deck) else rooms.finish(code, who)
    draw("play", "결과")
    Path(rooms._path(code)).unlink(missing_ok=True)


def room_flow(mode: str, kind: str) -> None:
    deck, aid, name = (make_ox_quiz if kind == "ox" else make_quiz)("rand_exam", 20, 7)
    for i, row in enumerate(deck):
        row["x2"] = i % 6 == 0
    org = {"agency": "광주광역시경찰청", "station": "광주동부", "unit": "학동지구대", "team": "1팀"}
    room = rooms.create("h1", "방장", aid, name, len(deck), deck, org=org,
                        mode=mode, team_battle=False, kind=kind)
    code = room["code"]
    rooms.join(code, "p2", "이경장")
    rooms.join(code, "p3", "박경위")
    rooms.auto_sides(code, "h1")
    rooms.start(code, "h1")
    room = rooms.load(code)
    assert room["status"] == "countdown"
    room["play_at"] = None
    room["status"] = "play"
    rooms._write(room)

    for who, right in (("h1", True), ("p2", False), ("p3", True)):
        for step in range(len(deck)):
            live = rooms.load(code)
            p = live["players"][who]
            if p.get("done"):
                break
            i = int(p["idx"])
            item = deck[i]
            ans = int(item["a"]) if "a" in item else 0
            if "q" not in item:
                from src.exam import item_at
                ans = int(item_at(item["area_id"], item["i"])["a"])
            rooms.touch(code, who, i)
            pick = ans if (right or step % 3) else -1
            rooms.answer(code, who, pick, ans, ms=1200, double=bool(item.get("x2")))
            live = rooms.load(code)
            if live["players"][who].get("done"):
                break
            if i + 1 < len(deck):
                rooms.seek(code, who, i + 1)
            else:
                rooms.finish(code, who)

    final = rooms.load(code)
    rank = rooms.ranking(final)
    teams = rooms.team_ranking(final)
    bad = rooms.wrong_indices(final)
    print(f"  ok  {mode}/{kind}: 상태 {final['status']} · "
          f"1등 {rank[0]['name']} {rank[0]['points']}점 · 틀린 {len(bad)}개")
    assert len(rank) == 3
    rooms.restart(code, "h1", [deck[i] for i in bad] or deck[:3])
    assert rooms.load(code)["round"] == 2
    Path(rooms._path(code)).unlink(missing_ok=True)


def relay_flow() -> None:
    """홍 2명 · 청 1명. 문항마다 편이 바뀌고, 홍은 방장→박경위→방장 순으로 돈다."""
    deck, aid, name = make_quiz("rand_exam", 6, 7)
    org = {"agency": "광주광역시경찰청", "station": "광주동부", "unit": "학동지구대", "team": "1팀"}
    room = rooms.create("h1", "방장", aid, name, len(deck), deck, org=org,
                        mode="classic", team_battle=True, kind="exam")
    code = room["code"]
    rooms.join(code, "p2", "이경장")
    rooms.join(code, "p3", "박경위")
    rooms.auto_sides(code, "h1")
    rooms.start(code, "h1")
    r = rooms.load(code)
    r["status"] = "play"
    r["play_at"] = None
    rooms._deal_turn(r)
    rooms._write(r)
    seen: list[tuple[str, str]] = []
    for _ in range(len(deck) + 1):
        live = rooms.load(code)
        if live is None or live.get("status") == "done":
            break
        rel = live.get("relay") or {}
        who = rel.get("pid") or ""
        if not who:
            break
        seen.append((rel.get("side") or "", live["players"][who]["name"]))
        item = deck[int(rel.get("idx") or 0)]
        ans = int(item["a"]) if "a" in item else 0
        if "q" not in item:
            from src.exam import item_at
            ans = int(item_at(item["area_id"], item["i"])["a"])
        rooms.answer(code, who, ans, ans, ms=400)
    sides = [s for s, _ in seen]
    hong = [n for s, n in seen if s == "홍팀"]
    chung = [n for s, n in seen if s == "청팀"]
    print(f"  ok  돌아가기: {seen}")
    assert sides[:2] == ["홍팀", "청팀"]
    assert hong[:2] == ["방장", "박경위"]
    assert set(chung) == {"이경장"}
    final = rooms.load(code)
    assert final["status"] == "done"
    Path(rooms._path(code)).unlink(missing_ok=True)


def timeout_flow() -> None:
    deck, aid, name = make_quiz("rand_exam", 5, 3)
    room = rooms.create("h1", "방장", aid, name, len(deck), deck, mode="speed", kind="exam",
                        org={"agency": "광주광역시경찰청", "station": "광주동부", "unit": "학동지구대", "team": "1팀"})
    code = room["code"]
    rooms.start(code, "h1")
    r = rooms.load(code)
    r["status"] = "play"
    r["play_at"] = None
    rooms._write(r)
    rooms.touch(code, "h1", 0)
    dl = rooms.deadline(rooms.load(code), rooms.load(code)["players"]["h1"])
    assert dl > time.time(), "제한시간이 잡히지 않았다"
    rooms.answer(code, "h1", -1, 0, ms=30_000)
    p = rooms.load(code)["players"]["h1"]
    assert p["score"] == 0 and p["history"][0]["pts"] == 0
    print(f"  ok  시간초과: 남은 {int(dl - time.time())}초, 무응답 0점")
    Path(rooms._path(code)).unlink(missing_ok=True)


if __name__ == "__main__":
    print("화면")
    screens()
    print("실제 화면")
    for m in ("classic", "speed", "survival"):
        live_screens(m, "exam")
    live_screens("speed", "ox")
    print("방 진행")
    for m in ("classic", "speed", "survival"):
        room_flow(m, "exam")
    room_flow("speed", "ox")
    print("돌아가기")
    relay_flow()
    print("제한시간")
    timeout_flow()
    print("전부 통과")
