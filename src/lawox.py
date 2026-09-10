from __future__ import annotations

import json
import random
import re
from functools import lru_cache
from pathlib import Path

import requests

from src.precedent import DETAIL_URL, SEARCH_URL, _plain, official_law_link

BANK_PATH = Path(__file__).resolve().parents[1] / "data" / "processed" / "law_ox.json"
SECRETS = Path(__file__).resolve().parents[1] / ".streamlit" / "secrets.toml"
AREA_ID = "law_ox"
AREA_NAME = "실무역량평가 OX"

# 현장과 가까운 경찰 관련 법령. 조문·항·호 원문만 법제처에서 받는다.
LAW_SPECS: list[tuple[str, tuple[str, ...] | None]] = [
    ("경찰관 직무집행법", None),
    ("경찰관 직무집행법 시행령", None),
    (
        "도로교통법",
        ("음주", "술에", "사고", "무면허", "보행자", "개인형", "주차", "속도", "신호", "중앙선", "도주"),
    ),
    (
        "도로교통법 시행령",
        ("음주", "혈중", "호흡", "사고"),
    ),
    ("경범죄 처벌법", None),
    ("집회 및 시위에 관한 법률", None),
    ("스토킹범죄의 처벌 등에 관한 법률", None),
    (
        "가정폭력범죄의 처벌 등에 관한 특례법",
        ("응급", "신고", "임시조치", "접근", "신변", "현장", "제지", "동행"),
    ),
    (
        "성폭력범죄의 처벌 등에 관한 특례법",
        ("신고", "응급", "현장", "제지", "접근", "신변", "촬영", "카메라", "추행"),
    ),
    (
        "아동학대범죄의 처벌 등에 관한 특례법",
        ("신고", "응급", "현장", "제지", "접근", "신변"),
    ),
    ("전기통신금융사기 피해 방지 및 피해금 환급에 관한 특별법", ("신고", "지급정지", "사기", "피해", "계좌", "긴급")),
    ("특정범죄 가중처벌 등에 관한 법률", ("절도", "강도", "뇌물", "도주", "보복", "운전자", "음주", "유괴")),
    (
        "경찰수사규칙",
        ("체포", "구속", "현행범", "불심", "임의", "유치", "압수", "수색", "긴급", "영장", "피의자"),
    ),
    ("즉결심판에 관한 절차법", None),
    (
        "형법",
        (
            "폭행",
            "상해",
            "협박",
            "강요",
            "체포",
            "감금",
            "주거침입",
            "절도",
            "강도",
            "사기",
            "공갈",
            "손괴",
            "방화",
            "강간",
            "추행",
            "모욕",
            "명예",
            "공무집행방해",
            "위계",
            "도주",
            "유기",
            "학대",
            "횡령",
            "배임",
            "장물",
            "도박",
        ),
    ),
    (
        "형사소송법",
        ("체포", "구속", "압수", "수색", "현행범", "피의자", "신문", "영장", "임의", "긴급", "고소", "고발"),
    ),
]


def _oc() -> str:
    if not SECRETS.exists():
        return ""
    for line in SECRETS.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("law_oc"):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def _art_label(no: str, branch: str, title: str, hang: str = "", ho: str = "") -> str:
    try:
        base = f"제{int(no)}조"
    except ValueError:
        base = f"제{no}조"
    if branch and branch not in ("0", "00"):
        try:
            base = f"제{int(no)}조의{int(branch)}"
        except ValueError:
            base = f"{base}의{branch}"
    if hang:
        try:
            base = f"{base} 제{int(hang)}항"
        except ValueError:
            base = f"{base} 제{hang}항"
    if ho:
        try:
            base = f"{base} 제{int(ho)}호"
        except ValueError:
            base = f"{base} 제{ho}호"
    if title:
        return f"{base}({title})"
    return base


_SKIP_TITLE = (
    "위임",
    "위탁",
    "서식",
    "별표",
    "별지",
    "위원",
    "통계",
    "포상",
    "표창",
    "예산",
    "정원",
    "직제",
    "국제협력",
    "국외 이전",
    "교육훈련",
    "연수",
    "과태료",
    "다른 법률의 개정",
    "벌칙 적용에서",
    "수수료",
    "경과조치",
    "시행일",
    "전산",
    "정보화",
    "공판",
    "항고",
    "상소",
    "속기",
    "적성",
    "보호관찰",
    "수강명령",
    "진술권",
    "선고",
    "보호명령",
    "손실보상",
    "공로자",
    "보상금",
    "피고인",
    "보석",
    "가석방",
    "증인",
    "고속도로",
    "갓길",
    "감정",
    "열람",
    "불송치",
    "해상",
    "적재",
    "감찰",
    "촉탁",
    "공소",
    "관할",
    "방지장치",
    "전용",
    "우선도로",
    "사용기록",
    "소송",
    "표시장",
    "무사고",
    "출입국",
    "심문",
    "강요된",
    "간수",
    "설치",
    "건조물",
)


def _plain_body(text: object) -> str:
    return _plain(text or "")


def _field_ok(title: str, text: str) -> bool:
    body = _plain_body(text)
    if not title or len(body) < 50:
        return False
    if any(s in title for s in _SKIP_TITLE):
        return False
    if title.strip() in ("보고", "목적") and "남용" not in body and "최소한" not in body:
        return False
    if re.match(r"^제\d+장", body) or "삭제" in body[:20]:
        return False
    if "별지" in body or "서식의" in body or "서식에" in body:
        return False
    if len(body) < 100 and any(
        x in body for x in ("대통령령으로 정한다", "부령으로 정한다", "총리령으로 정한다")
    ):
        return False
    return True


_CIRCLE = {chr(0x2460 + i): str(i + 1) for i in range(20)}


def _clause_no(raw: object) -> str:
    s = str(raw or "").strip()
    for src, dst in _CIRCLE.items():
        s = s.replace(src, dst)
    m = re.search(r"\d+", s)
    return m.group(0) if m else s


def _as_dicts(value: object) -> list[dict]:
    if isinstance(value, dict):
        return [value]
    if isinstance(value, list):
        return [x for x in value if isinstance(x, dict)]
    return []


def _ho_lines(hang: dict) -> list[str]:
    out: list[str] = []
    for ho in _as_dicts(hang.get("호")):
        text = _plain_body(ho.get("호내용"))
        if text and "삭제" not in text[:20]:
            out.append(text)
    return out


def _compose_hang(hang: dict) -> str:
    head = _plain_body(hang.get("항내용"))
    lines = _ho_lines(hang)
    if head and lines:
        probe = re.sub(r"^[0-9]+\.\s*", "", lines[0])[:18]
        if probe and probe in head:
            return head
        return head + "\n" + "\n".join(lines)
    return head or "\n".join(lines)


def _offense_list(title: str, lines: list[str]) -> bool:
    if not lines:
        return False
    if "종류" in (title or "") or "경범죄" in (title or ""):
        return len(lines) >= 5
    hit = sum(1 for t in lines if re.search(r"(한 사람|한 자)\s*$", _plain_body(t)))
    return hit >= 5 and hit >= len(lines) * 0.5


def _items_from_jomun(obj: dict, cur: dict) -> list[dict]:
    title = cur.get("title") or ""
    hangs = _as_dicts(obj.get("항"))
    rows: list[dict] = []
    if hangs:
        for hang in hangs:
            hno = _clause_no(hang.get("항번호"))
            lines = _ho_lines(hang)
            if _offense_list(title, lines):
                for ho in _as_dicts(hang.get("호")):
                    text = _plain_body(ho.get("호내용"))
                    if not _field_ok(title, text):
                        continue
                    if not re.search(r"(한 사람|한 자|해당하는 사람)", text):
                        continue
                    rows.append({**cur, "hang": hno, "ho": _clause_no(ho.get("호번호")), "text": text})
                continue
            text = _compose_hang(hang)
            if _field_ok(title, text):
                rows.append({**cur, "hang": hno, "ho": "", "text": text})
        if rows:
            return rows
    text = _plain_body(obj.get("조문내용"))
    if _field_ok(title, text):
        return [{**cur, "hang": "", "ho": "", "text": text}]
    return []


def _walk_articles(obj: object, found: list[dict], parent: dict | None = None) -> None:
    if isinstance(obj, dict):
        cur = parent
        no = str(obj.get("조문번호") or "").strip()
        if no:
            cur = {
                "no": no,
                "branch": str(obj.get("조문가지번호") or "").strip(),
                "title": str(obj.get("조문제목") or "").strip(),
            }
            found.extend(_items_from_jomun(obj, cur))
        for k, v in obj.items():
            if no and k in ("항", "호"):
                continue
            _walk_articles(v, found, cur)
    elif isinstance(obj, list):
        for v in obj:
            _walk_articles(v, found, parent)


def _find_law(oc: str, name: str) -> dict | None:
    r = requests.get(
        SEARCH_URL,
        params={"OC": oc, "target": "law", "type": "JSON", "query": name, "display": 10, "page": 1},
        timeout=25,
    )
    r.raise_for_status()
    r.encoding = "utf-8"
    data = r.json()
    block = data.get("LawSearch") if isinstance(data, dict) else None
    if not isinstance(block, dict):
        return None
    rows = block.get("law")
    if isinstance(rows, dict):
        rows = [rows]
    if not isinstance(rows, list):
        return None
    for row in rows:
        if isinstance(row, dict) and str(row.get("법령명한글") or "").strip() == name:
            return row
    return None


_KEEP_ALL_HANG = {
    "경찰관 직무집행법",
    "경범죄 처벌법",
    "스토킹범죄의 처벌 등에 관한 법률",
}
_LATE_HANG_KEYS = (
    "측정",
    "거부",
    "현행범",
    "긴급",
    "동행",
    "거절",
    "증표",
    "변호인",
    "영장 없이",
    "임의",
    "유치",
    "24시간",
    "6시간",
    "음주",
)


def _keep_hang(name: str, art: dict) -> bool:
    if name in _KEEP_ALL_HANG:
        return True
    hang = str(art.get("hang") or "")
    try:
        n = int(hang) if hang else 1
    except ValueError:
        n = 1
    if n <= 3:
        return True
    text = str(art.get("text") or "")
    return any(k in text for k in _LATE_HANG_KEYS)


def _fetch_articles(oc: str, mst: str, keep: tuple[str, ...] | None, name: str, limit: int = 100) -> list[dict]:
    r = requests.get(
        DETAIL_URL,
        params={"OC": oc, "target": "law", "type": "JSON", "MST": mst},
        timeout=90,
    )
    r.raise_for_status()
    r.encoding = "utf-8"
    data = r.json()
    raw: list[dict] = []
    _walk_articles(data, raw)
    out: list[dict] = []
    seen: set[str] = set()
    for art in raw:
        key = f"{art['no']}-{art.get('branch')}-{art.get('hang')}-{art.get('ho')}-{art['title']}"
        if key in seen:
            continue
        seen.add(key)
        blob_title = str(art.get("title") or "")
        if keep and not any(k in blob_title for k in keep):
            continue
        if not _keep_hang(name, art):
            continue
        out.append(art)
        if len(out) >= limit:
            break
    return out


def build_bank(oc: str | None = None) -> dict:
    oc = (oc or _oc()).strip()
    if not oc:
        raise RuntimeError("법제처 OC가 없습니다.")
    laws: list[dict] = []
    for name, keep in LAW_SPECS:
        row = _find_law(oc, name)
        if not row:
            continue
        mst = str(row.get("법령일련번호") or "").strip()
        if not mst:
            continue
        arts = _fetch_articles(oc, mst, keep, name)
        if len(arts) < 2:
            continue
        laws.append({"name": name, "mst": mst, "articles": arts})
    bank = {"laws": laws}
    BANK_PATH.parent.mkdir(parents=True, exist_ok=True)
    BANK_PATH.write_text(json.dumps(bank, ensure_ascii=False, indent=2), encoding="utf-8")
    return bank


@lru_cache(maxsize=1)
def load_bank() -> dict:
    if not BANK_PATH.exists():
        return {"laws": []}
    return json.loads(BANK_PATH.read_text(encoding="utf-8"))


def all_articles(law_name: str = "") -> list[dict]:
    out: list[dict] = []
    want = (law_name or "").strip()
    if want == "all":
        want = ""
    for law in load_bank().get("laws") or []:
        name = str(law.get("name") or "")
        if want and name != want:
            continue
        mst = str(law.get("mst") or "")
        src = official_law_link(mst, name)
        for art in law.get("articles") or []:
            row = dict(art)
            row["law"] = name
            row["src"] = src
            row["label"] = _art_label(
                str(art.get("no") or ""),
                str(art.get("branch") or ""),
                str(art.get("title") or ""),
            )
            out.append(row)
    return out


def law_choices() -> list[tuple[str, str, int]]:
    total = usable_count()
    rows = [("all", f"전 법령 섞기 ({total}문제)", total)]
    for law in load_bank().get("laws") or []:
        name = str(law.get("name") or "")
        n = len(law.get("articles") or [])
        if n:
            rows.append((name, f"{name} ({n}문제)", n))
    return rows


def usable_count(law_name: str = "") -> int:
    return len(all_articles(law_name))


def _jomun_key(art: dict) -> tuple[str, str, str]:
    return (str(art.get("law") or ""), str(art.get("no") or ""), str(art.get("branch") or ""))


def _pick_wrong(art: dict, others: list[dict], rng: random.Random) -> dict:
    target = len(art.get("text") or "")
    ranked = sorted(others, key=lambda x: abs(len(x.get("text") or "") - target))
    pool = ranked[: max(10, min(20, len(ranked)))]
    diff_law = [x for x in pool if x.get("law") != art.get("law")]
    if diff_law and rng.random() < 0.7:
        return rng.choice(diff_law)
    return rng.choice(pool or others)


def make_quiz(count: int, seed: int, law_name: str = "") -> tuple[list[dict], str, str]:
    arts = all_articles(law_name)
    if len(arts) < 2:
        return [], AREA_ID, AREA_NAME
    rng = random.Random(seed)
    pool = arts[:]
    rng.shuffle(pool)
    n = max(1, min(int(count) if count else 10, len(pool)))
    want = (law_name or "").strip()
    shown_name = AREA_NAME if not want or want == "all" else f"{AREA_NAME} · {want}"
    deck: list[dict] = []
    for i, art in enumerate(pool[:n]):
        others = [x for x in arts if _jomun_key(x) != _jomun_key(art)]
        if not others:
            continue
        true_q = rng.random() < 0.5
        shown = art if true_q else _pick_wrong(art, others, rng)
        stem = f"「{art['law']}」 {art['label']}의 내용은 다음과 같다.\n\n{shown['text']}"
        if true_q:
            exp = f"맞다. 「{art['law']}」 {art['label']} 법제처 원문이다."
            ans = 0
        else:
            exp = (
                f"아니다. 위 원문은 「{shown['law']}」 {shown['label']}이다. "
                f"「{art['law']}」 {art['label']}의 원문은 다음과 같다.\n\n{art['text']}"
            )
            ans = 1
        deck.append(
            {
                "area_id": AREA_ID,
                "i": i,
                "area": shown_name,
                "ox": True,
                "q": stem,
                "choices": ["O", "X"],
                "a": ans,
                "exp": exp,
                "src": art["src"],
            }
        )
    return deck, AREA_ID, f"{shown_name} ({len(deck)}문제)"
