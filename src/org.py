from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path

CSV_PATH = Path(__file__).resolve().parents[1] / "data" / "processed" / "stations.csv"

TEAMS = ["1팀", "2팀", "3팀", "4팀", "5팀", "6팀", "7팀", "8팀", "기타"]

AGENCY_ORDER = [
    "서울특별시경찰청",
    "부산광역시경찰청",
    "대구광역시경찰청",
    "인천광역시경찰청",
    "광주광역시경찰청",
    "대전광역시경찰청",
    "울산광역시경찰청",
    "경기남부경찰청",
    "경기북부경찰청",
    "강원특별자치도경찰청",
    "충청북도경찰청",
    "충청남도경찰청",
    "전북특별자치도경찰청",
    "전라남도경찰청",
    "경상북도경찰청",
    "경상남도경찰청",
    "제주특별자치도경찰청",
    "세종특별자치시경찰청",
]


@lru_cache(maxsize=1)
def tree() -> dict[str, dict[str, list[str]]]:
    """시도청 -> 경찰서 -> 지구대·파출소 이름."""
    out: dict[str, dict[str, list[str]]] = {}
    with CSV_PATH.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            agency = (row.get("agency") or "").strip()
            station = (row.get("station") or "").strip()
            unit = (row.get("unit_label") or row.get("unit_name") or "").strip()
            if not agency or not station or not unit:
                continue
            bucket = out.setdefault(agency, {}).setdefault(station, [])
            if unit not in bucket:
                bucket.append(unit)
    for st_map in out.values():
        for units in st_map.values():
            units.sort()
    return out


AGENCY_LABEL = {
    "광주광역시경찰청": "광주경찰청",
}


def agency_label(agency: str) -> str:
    return AGENCY_LABEL.get(agency, agency)


def agencies() -> list[str]:
    have = set(tree())
    ordered = [a for a in AGENCY_ORDER if a in have]
    extra = sorted(have - set(ordered))
    return ordered + extra


def stations(agency: str) -> list[str]:
    return sorted(tree().get(agency, {}))


def units(agency: str, station: str) -> list[str]:
    return list(tree().get(agency, {}).get(station, []))


def station_label(station: str) -> str:
    s = station.strip()
    if s.endswith("경찰서") or s.endswith("서"):
        return s if s.endswith("경찰서") else s + "경찰서"
    return s + "경찰서"


def path_text(org: dict) -> str:
    agency = agency_label(org.get("agency") or "")
    station = station_label(org.get("station") or "")
    unit = org.get("unit") or ""
    team = org.get("team") or ""
    return " · ".join(x for x in (agency, station, unit, team) if x)


def org_key(org: dict | None) -> str:
    if not org:
        return ""
    return "|".join(
        [
            org.get("agency") or "",
            org.get("station") or "",
            org.get("unit") or "",
            org.get("team") or "",
        ]
    )
