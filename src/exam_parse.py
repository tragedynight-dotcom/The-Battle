from __future__ import annotations

import json
import re
from pathlib import Path

CIRCLE = "①②③④⑤"
CIRCLE_TO_IDX = {c: i for i, c in enumerate(CIRCLE)}
IDX_TO_CIRCLE = {i: c for i, c in enumerate(CIRCLE)}

PAGE_RE = re.compile(r"===== PAGE \d+ =====")
PAGE_NUM_RE = re.compile(r"(?m)^-\s*\d+\s*-\s*$")
Q_SPLIT_RE = re.compile(r"(?m)^(\d{1,3})\.\s+")
ANS_RE = re.compile(r"(?:\(정답\)|정답)\s*[:：]?\s*([①②③④⑤1-5])")
EXP_RE = re.compile(r"(?:\(해설\)|해설)\s*[:：]?\s*(.*)", re.S)
SRC_RE = re.compile(r"(?:\(출처\)|출처)\s*[:：]?\s*(.*)", re.S)
ANS_BEFORE_RE = re.compile(r"(?:\(정답\)|정답)\s*[:：]?\s*$")
BULLET_RE = re.compile(r"^[•·ㆍ]\s*$", re.M)

MANUAL_ANSWERS = {
    # PDF에서 문항 3 정답이 다음 문항 뒤로 밀림. 보기 ③이 명백히 오류.
    ("가정폭력", 3): 2,
}

EXPECTED = {
    "경범죄·즉심": 19,  # 원문 10번 없음(9 다음 11)
    "정신질환자 응급입원": 25,
    "현행범·긴급체포": 20,
    "수배자": 20,
    "압수물": 20,
    "보이스피싱": 10,
    "불법체류자": 20,
    "가정폭력": 18,
    "교제폭력": 10,
    "스토킹": 25,
    "아동학대": 25,
    "성폭력": 20,
    "음주감지 거부 등": 20,
    "개인형이동장치": 20,
}

AREA_FROM_NAME = [
    (re.compile(r"^1\."), "경범죄·즉심"),
    (re.compile(r"^2\."), "정신질환자 응급입원"),
    (re.compile(r"^3\."), "현행범·긴급체포"),
    (re.compile(r"^4\."), "수배자"),
    (re.compile(r"^5\."), "압수물"),
    (re.compile(r"^6\."), "보이스피싱"),
    (re.compile(r"^7\."), "불법체류자"),
    (re.compile(r"^8\."), "가정폭력"),
    (re.compile(r"^9\."), "교제폭력"),
    (re.compile(r"^10\."), "스토킹"),
    (re.compile(r"^11\."), "아동학대"),
    (re.compile(r"^12\."), "성폭력"),
    (re.compile(r"^13\."), "음주감지 거부 등"),
    (re.compile(r"^14\."), "개인형이동장치"),
]


def _norm(s: str) -> str:
    s = s.replace("\u00a0", " ")
    s = BULLET_RE.sub("", s)
    s = re.sub(r"[ \t]+\n", "\n", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    s = re.sub(r"[ \t]{2,}", " ", s)
    return s.strip(" \n\t.?？")


def _answer_idx(token: str) -> int | None:
    token = token.strip()
    if token in CIRCLE_TO_IDX:
        return CIRCLE_TO_IDX[token]
    if token.isdigit():
        n = int(token)
        if 1 <= n <= 5:
            return n - 1
    return None


def _first_choice_pos(block: str) -> int | None:
    for m in re.finditer("①", block):
        before = block[max(0, m.start() - 12) : m.start()]
        if ANS_BEFORE_RE.search(before):
            continue
        return m.start()
    return None


def _split_choices(block: str) -> tuple[str, list[str], str]:
    """Return (stem, choices, tail_after_choices)."""
    first = _first_choice_pos(block)
    if first is None:
        return _norm(block), [], ""

    stem = _norm(block[:first])
    rest = block[first:]
    parts = re.split(r"((?:\(정답\)|정답)\s*[:：]?)", rest, maxsplit=1)
    if len(parts) == 3:
        head, sep, after = parts
        tail = sep + after
    else:
        head = rest
        tail = ""

    choices = _parse_choice_texts(head)
    return stem, choices, tail


def _parse_choice_texts(head: str) -> list[str]:
    line_chunks = re.split(r"(?m)(?=^[ \t]*[①②③④⑤])", head.strip())
    by_line: list[str] = []
    for p in line_chunks:
        m = re.match(r"^[ \t]*([①②③④⑤])\s*(.*)$", p, re.S)
        if m:
            t = _norm(m.group(2))
            if t:
                by_line.append(t)
    if len(by_line) >= 4:
        return by_line
    by_all: list[str] = []
    for p in re.split(r"(?=[①②③④⑤])", head):
        m = re.match(r"^([①②③④⑤])\s*(.*)$", p, re.S)
        if not m:
            continue
        t = _norm(m.group(2))
        if t:
            by_all.append(t)
    return by_all if len(by_all) >= len(by_line) else by_line


def _looks_like_question(text: str, start: int) -> bool:
    window = text[start : start + 700]
    if "①" not in text[start : start + 1200]:
        return False
    stem_end = window.find("①")
    stem = window if stem_end < 0 else window[:stem_end]
    if ("?" in stem) or ("？" in stem):
        return True
    return bool(re.search(r"(것은|경우는|설명|요령|처리|조치|해당|아닌|옳은|잘못된|적절|숫자는)", stem))


def parse_area_text(area: str, raw: str) -> list[dict]:
    text = PAGE_RE.sub("\n", raw)
    text = PAGE_NUM_RE.sub("", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    raw_matches = list(Q_SPLIT_RE.finditer(text))
    matches: list[re.Match[str]] = []
    last = 0
    for m in raw_matches:
        num = int(m.group(1))
        if num <= last or num > 40:
            continue
        if not _looks_like_question(text, m.end()):
            continue
        matches.append(m)
        last = num
    items: list[dict] = []
    bodies: list[str] = []
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        bodies.append(text[start:end].strip())

    for i, m in enumerate(matches):
        num = int(m.group(1))
        body = bodies[i]
        first = _first_choice_pos(body)
        prefix = body[: first if first is not None else 0]
        orphan = ANS_RE.search(prefix)
        if orphan and first is not None:
            target = next((prev for prev in reversed(items) if prev["a"] is None), None)
            if target is not None:
                target["a"] = _answer_idx(orphan.group(1))
                src_m = SRC_RE.search(prefix)
                if src_m and not target["src"]:
                    target["src"] = _norm(src_m.group(1))
                    prefix_exp = prefix[: src_m.start()]
                else:
                    prefix_exp = prefix
                exp_m = EXP_RE.search(prefix_exp)
                if exp_m and not target["exp"]:
                    target["exp"] = _norm(exp_m.group(1))
            body = body[: orphan.start()] + body[first:]

        stem, choices, tail = _split_choices(body)
        ans_m = ANS_RE.search(tail if tail else body)
        a = _answer_idx(ans_m.group(1)) if ans_m else None
        if a is None:
            a = MANUAL_ANSWERS.get((area, num))

        exp = ""
        src = ""
        search_in = tail if tail else body
        src_m = SRC_RE.search(search_in)
        if src_m:
            src = _norm(src_m.group(1))
            search_in = search_in[: src_m.start()]
        exp_m = EXP_RE.search(search_in)
        if exp_m:
            exp = _norm(exp_m.group(1))
        elif ans_m:
            after = (tail or body)[ans_m.end() :]
            after = SRC_RE.sub("", after)
            after = re.sub(r"^\s*[①②③④⑤1-5]\s*", "", after)
            exp = _norm(after)

        items.append(
            {
                "n": num,
                "q": stem,
                "choices": choices,
                "a": a,
                "exp": exp,
                "src": src,
            }
        )
    return items


def area_name_from_filename(name: str) -> str:
    for pat, area in AREA_FROM_NAME:
        if pat.search(name):
            return area
    return Path(name).stem


def parse_folder(folder: Path) -> list[dict]:
    areas: list[dict] = []
    files = sorted(folder.glob("*.txt")) + sorted(folder.glob("*.pdf"))
    # Prefer already-extracted txt; if only pdf, caller should extract first
    txts = sorted(folder.glob("*.txt"))
    if not txts:
        raise FileNotFoundError(f"추출 텍스트가 없습니다: {folder}")
    seen: set[str] = set()
    for p in txts:
        area = area_name_from_filename(p.name)
        if area in seen:
            continue
        seen.add(area)
        items = parse_area_text(area, p.read_text(encoding="utf-8"))
        aid = {
            "경범죄·즉심": "misdemeanor",
            "정신질환자 응급입원": "mental",
            "현행범·긴급체포": "arrest",
            "수배자": "wanted",
            "압수물": "seize",
            "보이스피싱": "phishing",
            "불법체류자": "immigration",
            "가정폭력": "dv",
            "교제폭력": "dating",
            "스토킹": "stalking",
            "아동학대": "child",
            "성폭력": "sexual",
            "음주감지 거부 등": "dui",
            "개인형이동장치": "pm",
        }.get(area, area)
        areas.append({"id": aid, "name": area, "file": p.name, "items": items})
    # Sort by original file number
    order = [a for _, a in AREA_FROM_NAME]
    areas.sort(key=lambda x: order.index(x["name"]) if x["name"] in order else 99)
    return areas


def validate(areas: list[dict]) -> list[str]:
    problems: list[str] = []
    for area in areas:
        name = area["name"]
        items = area["items"]
        exp_n = EXPECTED.get(name)
        if exp_n and len(items) != exp_n:
            problems.append(f"{name}: 문항 {len(items)}개 (기대 {exp_n})")
        nums = [it["n"] for it in items]
        if nums != list(range(1, len(items) + 1)) and nums != sorted(set(nums)):
            problems.append(f"{name}: 번호 이상 {nums}")
        for it in items:
            tag = f"{name} {it['n']}번"
            if not it["q"]:
                problems.append(f"{tag}: 문제 없음")
            if len(it["choices"]) < 4:
                problems.append(f"{tag}: 보기 {len(it['choices'])}개")
            if it["a"] is None:
                problems.append(f"{tag}: 정답 없음")
            elif it["a"] < 0 or it["a"] >= len(it["choices"]):
                problems.append(f"{tag}: 정답 인덱스 {it['a']}")
    return problems


def main() -> None:
    extract = Path(__file__).resolve().parents[1] / "data" / "processed" / "exam_extract"
    out = Path(__file__).resolve().parents[1] / "data" / "processed" / "exam_bank.json"
    areas = parse_folder(extract)
    problems = validate(areas)
    out.write_text(json.dumps(areas, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {out}")
    total = sum(len(a["items"]) for a in areas)
    print(f"areas {len(areas)} items {total}")
    for a in areas:
        print(f"  {a['name']}: {len(a['items'])}")
    if problems:
        print("PROBLEMS")
        for p in problems:
            print(" ", p)


if __name__ == "__main__":
    main()
