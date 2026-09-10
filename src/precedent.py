from __future__ import annotations

import re
from typing import Any
from urllib.parse import quote, urlencode

import requests

SEARCH_URL = "https://www.law.go.kr/DRF/lawSearch.do"
DETAIL_URL = "https://www.law.go.kr/DRF/lawService.do"

# 법원이 경찰 전용 태그를 주지 않으므로, 현장 법령·쟁점으로만 공식 검색한다.
FIELD_TOPICS: list[tuple[str, dict[str, str]]] = [
    ("직무 · 경찰관직무집행법", {"jo": "경찰관직무집행법", "query": ""}),
    ("직무 · 불심검문", {"jo": "경찰관직무집행법", "query": "불심검문"}),
    ("직무 · 현행범 체포", {"query": "현행범인"}),
    ("직무 · 긴급체포", {"query": "긴급체포"}),
    ("직무 · 압수·수색", {"query": "압수 수색"}),
    ("직무 · 공무집행방해", {"query": "공무집행방해"}),
    ("교통 · 음주운전", {"jo": "도로교통법", "query": "음주운전"}),
    ("교통 · 음주측정", {"jo": "도로교통법", "query": "음주측정"}),
    ("교통 · 무면허운전", {"jo": "도로교통법", "query": "무면허"}),
    ("교통 · 사고 후 미조치", {"query": "사고후미조치"}),
    ("교통 · 신호위반", {"jo": "도로교통법", "query": "신호위반"}),
    ("교통 · 중앙선 침범", {"query": "중앙선침범"}),
    ("교통 · 보행자 사고", {"query": "보행자"}),
    ("교통 · 개인형 이동장치", {"query": "개인형 이동장치"}),
    ("형사 · 폭행", {"query": "폭행"}),
    ("형사 · 특수폭행", {"query": "특수폭행"}),
    ("형사 · 협박", {"query": "협박"}),
    ("형사 · 주거침입", {"query": "주거침입"}),
    ("형사 · 재물손괴", {"query": "재물손괴"}),
    ("형사 · 절도", {"query": "절도"}),
    ("형사 · 카메라등이용촬영", {"query": "카메라등이용촬영"}),
    ("형사 · 성폭력", {"query": "성폭력"}),
    ("형사 · 마약류", {"query": "마약류관리"}),
    ("형사 · 보이스피싱", {"query": "보이스피싱"}),
    ("형사 · 정당방위", {"query": "정당방위"}),
    ("보호 · 가정폭력", {"query": "가정폭력"}),
    ("보호 · 교제폭력", {"query": "교제폭력"}),
    ("보호 · 스토킹", {"query": "스토킹범죄"}),
    ("보호 · 아동학대", {"query": "아동학대"}),
    ("보호 · 정신질환자 응급", {"query": "정신건강증진"}),
]


def _as_list(node: Any) -> list[dict]:
    if node is None:
        return []
    if isinstance(node, list):
        return [x for x in node if isinstance(x, dict)]
    if isinstance(node, dict):
        return [node]
    return []


def _walk_prec(obj: Any) -> list[dict]:
    found: list[dict] = []
    if isinstance(obj, dict):
        if obj.get("사건번호") or obj.get("판례일련번호") or obj.get("precSeq"):
            found.append(obj)
        for v in obj.values():
            found.extend(_walk_prec(v))
    elif isinstance(obj, list):
        for v in obj:
            found.extend(_walk_prec(v))
    return found


def _walk_law(obj: Any) -> list[dict]:
    found: list[dict] = []
    if isinstance(obj, dict):
        if obj.get("법령명") or obj.get("lawShortNm") or obj.get("법령일련번호"):
            found.append(obj)
        for v in obj.values():
            found.extend(_walk_law(v))
    elif isinstance(obj, list):
        for v in obj:
            found.extend(_walk_law(v))
    return found


def search_precedents(
    oc: str,
    query: str = "",
    display: int = 20,
    jo: str = "",
    page: int = 1,
) -> tuple[list[dict], int]:
    if not oc.strip() or (not query.strip() and not jo.strip()):
        return [], 0
    params: dict[str, str | int] = {
        "OC": oc.strip(),
        "target": "prec",
        "type": "JSON",
        "display": max(1, min(int(display), 100)),
        "page": max(1, int(page)),
        "sort": "ddes",
        "datSrcNm": "대법원",
    }
    if jo.strip():
        params["JO"] = jo.strip()
    if query.strip():
        params["search"] = 2
        params["query"] = query.strip()
    r = requests.get(SEARCH_URL, params=params, timeout=20)
    r.raise_for_status()
    r.encoding = "utf-8"
    try:
        data = r.json()
    except Exception:
        return [], 0
    block = data.get("PrecSearch") if isinstance(data, dict) else None
    if not isinstance(block, dict):
        return [], 0
    try:
        total = int(block.get("totalCnt") or 0)
    except (TypeError, ValueError):
        total = 0
    rows = _as_list(block.get("prec"))
    out: list[dict] = []
    seen: set[str] = set()
    for row in rows:
        seq = str(row.get("판례일련번호") or "").strip()
        nb = str(row.get("사건번호") or "").strip()
        key = seq or nb
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(
            {
                "id": seq,
                "사건번호": nb,
                "사건명": str(row.get("사건명") or "").strip(),
                "선고일자": str(row.get("선고일자") or "").strip(),
                "법원명": str(row.get("법원명") or "").strip(),
                "사건종류명": str(row.get("사건종류명") or "").strip(),
            }
        )
    return out, total


def _fmt_ymd(value: str) -> str:
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    if len(digits) == 8:
        return f"{digits[:4]}.{digits[4:6]}.{digits[6:]}"
    return str(value or "").strip()


def _join_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return "\n".join(x for x in (_join_text(v) for v in value) if x)
    return _plain(value)


def _first_field(obj: Any, key: str) -> Any:
    if isinstance(obj, dict):
        if obj.get(key):
            return obj[key]
        for v in obj.values():
            got = _first_field(v, key)
            if got:
                return got
    elif isinstance(obj, list):
        for v in obj:
            got = _first_field(v, key)
            if got:
                return got
    return None


POLICE_ORG = "1320000"


def search_police_laws(oc: str, display: int = 30) -> tuple[list[dict], int]:
    if not oc.strip():
        return [], 0
    params = {
        "OC": oc.strip(),
        "target": "law",
        "type": "JSON",
        "org": POLICE_ORG,
        "sort": "ddes",
        "display": max(1, min(int(display), 100)),
        "page": 1,
    }
    r = requests.get(SEARCH_URL, params=params, timeout=20)
    r.raise_for_status()
    r.encoding = "utf-8"
    try:
        data = r.json()
    except Exception:
        return [], 0
    block = data.get("LawSearch") if isinstance(data, dict) else None
    if not isinstance(block, dict):
        return [], 0
    try:
        total = int(block.get("totalCnt") or 0)
    except (TypeError, ValueError):
        total = 0
    out: list[dict] = []
    seen: set[str] = set()
    for row in _as_list(block.get("law")):
        mst = str(row.get("법령일련번호") or "").strip()
        name = str(row.get("법령명한글") or row.get("법령명") or "").strip()
        key = mst or name
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(
            {
                "id": mst,
                "법령ID": str(row.get("법령ID") or "").strip(),
                "법령명": name,
                "약칭": str(row.get("법령약칭명") or "").strip(),
                "제개정": str(row.get("제개정구분명") or "").strip(),
                "법령구분": str(row.get("법령구분명") or "").strip(),
                "소관부처": str(row.get("소관부처명") or "").strip(),
                "공포일자": _fmt_ymd(str(row.get("공포일자") or "")),
                "시행일자": _fmt_ymd(str(row.get("시행일자") or "")),
            }
        )
    return out, total


def fetch_amend_reason(oc: str, mst: str) -> dict[str, str]:
    if not oc.strip() or not mst.strip():
        return {}
    params = {
        "OC": oc.strip(),
        "target": "law",
        "type": "JSON",
        "MST": mst.strip(),
    }
    r = requests.get(DETAIL_URL, params=params, timeout=30)
    r.raise_for_status()
    r.encoding = "utf-8"
    try:
        data = r.json()
    except Exception:
        return {}
    return {
        "제개정이유": _join_text(_first_field(data, "제개정이유내용")),
        "개정문": _join_text(_first_field(data, "개정문내용")),
    }


def official_law_link(mst: str, name: str = "") -> str:
    if mst:
        return f"https://www.law.go.kr/lsInfoP.do?lsiSeq={mst}"
    if name:
        return law_search_link(name)
    return "https://www.law.go.kr/lsSc.do"


def fetch_detail(oc: str, prec_id: str) -> dict[str, str]:
    if not oc.strip() or not prec_id.strip():
        return {}
    params = {
        "OC": oc.strip(),
        "target": "prec",
        "ID": prec_id.strip(),
        "type": "JSON",
    }
    r = requests.get(DETAIL_URL, params=params, timeout=20)
    r.raise_for_status()
    r.encoding = "utf-8"
    try:
        data = r.json()
    except Exception:
        return {}
    rows = _walk_prec(data)
    row = rows[0] if rows else (data if isinstance(data, dict) else {})
    if not isinstance(row, dict):
        return {}
    return {
        "id": str(row.get("판례정보일련번호") or row.get("판례일련번호") or prec_id),
        "사건번호": str(row.get("사건번호") or ""),
        "사건명": str(row.get("사건명") or ""),
        "선고일자": str(row.get("선고일자") or ""),
        "법원명": str(row.get("법원명") or ""),
        "판시사항": _plain(row.get("판시사항")),
        "판결요지": _plain(row.get("판결요지")),
        "참조조문": _plain(row.get("참조조문")),
        "판례내용": _plain(row.get("판례내용")),
    }


def official_link(prec_id: str, case_no: str = "") -> str:
    if prec_id:
        return f"https://www.law.go.kr/precInfoP.do?precSeq={prec_id}"
    if case_no:
        return prec_search_link(case_no)
    return "https://www.law.go.kr/precSc.do"


def law_search_link(query: str) -> str:
    return f"https://www.law.go.kr/lsSc.do?menuId=1&query={quote(query)}"


def prec_search_link(query: str) -> str:
    return f"https://www.law.go.kr/precSc.do?tabMenuId=tab67&query={quote(query)}"


def _plain(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    text = re.sub(r"<[^>]+>", "\n", text)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def find_terms(text: str, terms: list[str]) -> list[tuple[str, bool]]:
    return [(term, term in text) for term in terms]
