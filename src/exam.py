from __future__ import annotations

import json
import random
import re
from functools import lru_cache
from pathlib import Path

BANK_PATH = Path(__file__).resolve().parents[1] / "data" / "processed" / "exam_bank.json"
CIRCLE = "①②③④⑤"
RAND_TOPIC = "rand_topic"
RAND_EXAM = "rand_exam"
EXAM_COUNT = 20
KEEP_LINE = re.compile(r"^[㉠㉡㉢㉣㉤㉥㉦㉧①②③④⑤]")
ATTACH = re.compile(
    r"^([은는이가을를의과와로에도만며면니다고요여]|으로|에서|에게|하여|하였|했다|한다|되는|하지|하는|된|될|한|할|함)"
)


def tidy(text: str) -> str:
    """PDF 추출 때 잘린 줄을 이어 붙인다. ㉠·① 같은 항목만 줄을 남긴다."""
    if not text:
        return ""
    text = text.replace("\r\n", "\n").replace("\u00a0", " ").replace("\t", " ")
    lines = [ln.strip() for ln in text.split("\n")]
    out: list[str] = []
    for line in lines:
        if not line:
            if out and out[-1] != "":
                out.append("")
            continue
        if KEEP_LINE.match(line) or not out or out[-1] == "":
            out.append(line)
            continue
        prev = out[-1]
        if re.search(r"[가-힣]$", prev) and re.match(r"[가-힣]", line) and ATTACH.match(line):
            out[-1] = prev + line
        else:
            out[-1] = prev + " " + line
    cleaned: list[str] = []
    for x in out:
        if x == "" and (not cleaned or cleaned[-1] == ""):
            continue
        cleaned.append(x)
    while cleaned and cleaned[-1] == "":
        cleaned.pop()
    text = "\n".join(cleaned)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


@lru_cache(maxsize=1)
def load_areas() -> list[dict]:
    return json.loads(BANK_PATH.read_text(encoding="utf-8"))


def all_items(areas: list[dict] | None = None) -> list[dict]:
    areas = areas if areas is not None else load_areas()
    out: list[dict] = []
    for area in areas:
        for it in area["items"]:
            row = dict(it)
            row["area_id"] = area["id"]
            row["area"] = area["name"]
            out.append(row)
    return out


def circle(i: int) -> str:
    if 0 <= i < len(CIRCLE):
        return CIRCLE[i]
    return str(i + 1)


def area_by_id(area_id: str) -> dict | None:
    for area in load_areas():
        if area["id"] == area_id:
            return area
    return None


def area_choices() -> list[tuple[str, str, int]]:
    """(id, 화면 이름, 문항 수). 맨 위는 랜덤 출제."""
    areas = load_areas()
    rows = [
        (RAND_TOPIC, "랜덤문제 출제(주제별)", 0),
        (RAND_EXAM, "랜덤문제 출제(모의고사)", EXAM_COUNT),
    ]
    for a in areas:
        n = len(a["items"])
        rows.append((a["id"], f"{a['name']} ({n}문제)", n))
    return rows


def item_at(area_id: str, index: int) -> dict:
    area = area_by_id(area_id)
    if area is None:
        raise KeyError(area_id)
    row = dict(area["items"][index])
    row["q"] = tidy(row.get("q") or "")
    row["choices"] = [tidy(c) for c in (row.get("choices") or [])]
    row["exp"] = tidy(row.get("exp") or "")
    row["src"] = tidy(row.get("src") or "")
    row["area_id"] = area["id"]
    row["area"] = area["name"]
    return row


def _pool(area_id: str) -> list[dict]:
    pool: list[dict] = []
    for area in load_areas():
        if area_id and area["id"] != area_id:
            continue
        for i, _it in enumerate(area["items"]):
            pool.append({"area_id": area["id"], "i": i})
    return pool


def build_deck(area_id: str, count: int, seed: int) -> list[dict]:
    """주제 문항을 한 번 섞는다. 방 안에서는 모두가 같은 순서를 본다."""
    deck, _aid, _name = make_quiz(area_id, count, seed)
    return deck


def make_quiz(choice_id: str, count: int, seed: int) -> tuple[list[dict], str, str]:
    """(덱, 저장용 area_id, 화면 이름)."""
    rng = random.Random(seed)
    areas = load_areas()
    if not areas:
        return [], choice_id, "문제 없음"
    if choice_id == RAND_TOPIC:
        area = rng.choice(areas)
        pool = _pool(area["id"])
        rng.shuffle(pool)
        name = f"랜덤문제 출제(주제별) · {area['name']}"
        return pool, area["id"], name
    if choice_id == RAND_EXAM:
        picked: list[dict] = []
        leftover: list[dict] = []
        for area in areas:
            idxs = list(range(len(area["items"])))
            rng.shuffle(idxs)
            if not idxs:
                continue
            picked.append({"area_id": area["id"], "i": idxs[0]})
            leftover.extend({"area_id": area["id"], "i": i} for i in idxs[1:])
        rng.shuffle(leftover)
        need = max(0, EXAM_COUNT - len(picked))
        deck = picked + leftover[:need]
        rng.shuffle(deck)
        return deck[:EXAM_COUNT], RAND_EXAM, "랜덤문제 출제(모의고사)"
    pool = _pool(choice_id)
    rng.shuffle(pool)
    n = max(1, min(int(count) if count else len(pool), len(pool)))
    area = area_by_id(choice_id)
    name = f"{area['name']} ({n}문제)" if area else f"섞기 ({n}문제)"
    return pool[:n], choice_id, name


NUM_Q = re.compile(
    r"(모두\s*몇\s*개|몇\s*개인가|몇\s*개인가요|몇\s*개\s*일까요|괄호\s*안에\s*들어갈\s*숫자|몇\s*시간)"
)
OX_FALSE = re.compile(
    r"(옳지\s*않은|틀린|잘못된|적절하지\s*않은|해당하지\s*않는|아닌\s*것은|아닌\s*항목)"
)
OX_TAIL = re.compile(
    r"\s*(으로|에 대한 설명으로|에 대한|에 대해)?\s*(가장\s*)?"
    r"(옳|맞|적절하지 않은|적절|해당하지 않는|해당|아닌)\s*(은|는|지 않은)?\s*것은\s*\??\s*$"
)
OX_HEAD = re.compile(r"^다음( 중| 보기 중)?\s*")
OX_CASE = re.compile(r"[㉠㉡㉢㉣㉤]|[ㄱㄴㄷㄹ]\s*[.．)]|[ㄱㄴㄷㄹ]\s*,")
OX_PICK = re.compile(r"올바르게 고른|알맞게 고른|바르게 고른")
OX_COMBO = re.compile(r"^[㉠㉡㉢㉣ㄱㄴㄷㄹ,\s와과·]+$")


def _first_int(text: str) -> int | None:
    m = re.search(r"\d+", text or "")
    return int(m.group(0)) if m else None


def _ox_context(q: str) -> str:
    """'옳은 것은' 꼬리만 걷어, 보기 한 줄을 판단할 짧은 맥락을 남긴다."""
    t = (q or "").strip()
    t = re.split(r"[?？]", t)[0]
    t = OX_TAIL.sub("", t)
    t = OX_HEAD.sub("", t)
    t = re.sub(r"^(은|는)\s+", "", t)
    t = re.sub(r"\s*이$", "", t)
    return t.strip(" .")


def _ox_skip(item: dict) -> bool:
    """사례·ㄱㄴ 고르기는 O/X로 내면 보기가 'ㄱ, ㄴ'만 남아 어색하다."""
    q = item.get("q") or ""
    choices = item.get("choices") or []
    blob = q + "\n" + "\n".join(str(c) for c in choices)
    if OX_CASE.search(blob) or OX_PICK.search(q):
        return True
    if any(OX_COMBO.match(str(c or "").strip()) for c in choices):
        return True
    if q.count("\n") >= 3 or len(q) > 220:
        return True
    return False


def as_ox_item(item: dict, rng: random.Random) -> dict:
    """공식 보기 원문 한 줄이 맞는지 O/X로 묻는다. 조문을 새로 짓지 않는다."""
    q = item.get("q") or ""
    choices = [c for c in (item.get("choices") or []) if str(c).strip()]
    try:
        ans_i = int(item.get("a") or 0)
    except (TypeError, ValueError):
        ans_i = 0
    row = {
        "area_id": item.get("area_id") or "",
        "area": item.get("area") or "",
        "exp": item.get("exp") or "",
        "src": item.get("src") or "",
        "i": item.get("i") if item.get("i") is not None else item.get("n"),
    }
    if NUM_Q.search(q) and 0 <= ans_i < len(choices):
        num = _first_int(choices[ans_i])
        if num is not None:
            row["q"] = q
            row["kind"] = "num"
            row["a"] = num
            row["choices"] = []
            return row
    if not choices:
        return item
    use_key = rng.random() < 0.5
    if use_key and 0 <= ans_i < len(choices):
        shown = choices[ans_i]
        key = True
    else:
        others = [c for i, c in enumerate(choices) if i != ans_i]
        if others:
            shown = rng.choice(others)
            key = False
        else:
            shown = choices[ans_i]
            key = True
    # 원 문제가 '옳지 않은 것'이면 정답 보기는 틀린 설명이다.
    false_ask = bool(OX_FALSE.search(q))
    true_statement = (not key) if false_ask else key
    row["ox"] = True
    row["q"] = shown
    row["ctx"] = _ox_context(q)
    row["ask"] = "아래 설명이 맞으면 O, 틀리면 X."
    row["choices"] = ["O", "X"]
    row["a"] = 0 if true_statement else 1
    return row


def make_ox_quiz(choice_id: str, count: int, seed: int) -> tuple[list[dict], str, str]:
    want = max(1, int(count) if count else 20)
    _, stored_id, shown = make_quiz(choice_id, min(want, EXAM_COUNT), seed)
    if choice_id == RAND_TOPIC:
        refs = _pool(stored_id)
    elif choice_id == RAND_EXAM:
        refs = _pool("")
    else:
        refs = _pool(stored_id)
        area = area_by_id(stored_id)
        shown = area["name"] if area else shown
    rng = random.Random(seed)
    rng.shuffle(refs)
    ox_rng = random.Random(seed + 17)
    deck: list[dict] = []
    for ref in refs:
        item = item_at(ref["area_id"], ref["i"])
        if _ox_skip(item) and not NUM_Q.search(item.get("q") or ""):
            continue
        deck.append(as_ox_item(item, ox_rng))
        if len(deck) >= want:
            break
    return deck[:want], stored_id, f"실무역량평가 OX · {shown}"
