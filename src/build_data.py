from __future__ import annotations

import csv
import json
import math
import re
from pathlib import Path

from .constants import (
    AGENCY_BY_SIDO,
    CHEONG_TO_AGENCY,
    GYEONGGI_NORTH,
    GYEONGGI_SOUTH,
    SIDO_ALIAS,
    SIDO_PREFIXES,
)

ADDRESS_SIDO_NORM = {
    "강원도": "강원특별자치도",
    "전라북도": "전북특별자치도",
}

CRIME_SIGUNGU_ALIAS = {
    ("대구광역시", "군위군"): ("경상북도", "군위군"),
    ("세종특별자치시", "세종"): ("세종특별자치시", "세종시"),
    ("세종특별자치시", "세종시"): ("세종특별자치시", "세종시"),
}


def city_key(sigungu: str) -> str:
    parts = sigungu.split()
    if len(parts) >= 2 and parts[0].endswith(("시", "군")):
        return parts[0]
    return sigungu

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"

SKIP_PREFIXES = ("외국",)


def parse_crime_column(col: str) -> tuple[str, str] | None:
    col = col.strip()
    if not col or col.startswith(SKIP_PREFIXES):
        return None
    parts = col.split()
    if len(parts) < 2:
        return None
    token, sigungu = parts[0], " ".join(parts[1:])
    if token in {"경기도"} and sigungu == "광주시":
        sido = "경기도"
    elif token == "광주":
        sido = "광주광역시"
    else:
        sido = SIDO_ALIAS.get(token)
    if not sido:
        return None
    return sido, sigungu


def agency_of(sido: str, sigungu: str) -> str:
    if sido == "경기도":
        key = sigungu.split()[0]
        if key in GYEONGGI_NORTH:
            return "경기북부경찰청"
        return "경기남부경찰청"
    return AGENCY_BY_SIDO.get(sido, f"{sido}경찰청")


def classify_crime(major: str, mid: str) -> str:
    text = f"{major} {mid}"
    if any(k in text for k in ("강간", "추행", "성풍속")):
        return "sexual"
    if any(k in text for k in ("폭력", "상해", "폭행", "협박", "공갈", "손괴", "체포")):
        return "violent"
    if "절도" in text:
        return "theft"
    if any(k in text for k in ("사기", "횡령", "배임")):
        return "fraud"
    if any(k in text for k in ("교통",)):
        return "traffic"
    if any(k in text for k in ("강도", "살인", "방화")):
        return "violent"
    if any(k in text for k in ("도박", "풍속", "마약")):
        return "night"
    return "other"


def load_address() -> dict:
    return json.loads((RAW / "address2.json").read_text(encoding="utf-8"))


def iter_sigungu(addr: dict):
    for raw_sido, s_val in addr.items():
        sido = ADDRESS_SIDO_NORM.get(raw_sido, raw_sido)
        children = s_val.get("children") or {}
        if not children:
            yield sido, sido, float(s_val["lat"]), float(s_val["lng"]), {}
            continue
        sample = next(iter(children.values()))
        if "children" in sample:
            for sigungu, g_val in children.items():
                yield sido, sigungu, float(g_val["lat"]), float(g_val["lng"]), g_val.get("children") or {}
        else:
            yield sido, sido, float(s_val["lat"]), float(s_val["lng"]), children


def build() -> None:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    with open(RAW / "crime_by_region.csv", encoding="cp949", newline="") as f:
        crime_rows = list(csv.reader(f))
    header = crime_rows[0]
    categories = [(r[0], r[1], classify_crime(r[0], r[1])) for r in crime_rows[1:]]

    col_map = {}
    for idx, col in enumerate(header[2:], start=2):
        parsed = parse_crime_column(col)
        if parsed:
            col_map[idx] = parsed

    stats = {}
    for row, (major, mid, bucket) in zip(crime_rows[1:], categories):
        for idx, (sido, sigungu) in col_map.items():
            try:
                value = int(float(row[idx] or 0))
            except ValueError:
                value = 0
            key = (sido, sigungu)
            rec = stats.setdefault(
                key,
                {
                    "sido": sido,
                    "sigungu": sigungu,
                    "agency": agency_of(sido, sigungu),
                    "total": 0,
                    "violent": 0,
                    "theft": 0,
                    "sexual": 0,
                    "fraud": 0,
                    "traffic": 0,
                    "night": 0,
                    "other": 0,
                },
            )
            rec["total"] += value
            rec[bucket] += value

    addr = load_address()
    coord = {}
    dongs = []
    for sido, sigungu, lat, lon, children in iter_sigungu(addr):
        coord[(sido, sigungu)] = (lat, lon)
        coord[(sido, city_key(sigungu))] = (lat, lon)
        if not children:
            dongs.append((sido, city_key(sigungu), sigungu, lat, lon))
            continue
        for dong, d_val in children.items():
            try:
                dongs.append((sido, city_key(sigungu), dong, float(d_val["lat"]), float(d_val["lng"])))
            except (KeyError, TypeError, ValueError):
                continue

    def find_coord(sido: str, sigungu: str):
        alias = CRIME_SIGUNGU_ALIAS.get((sido, sigungu))
        for key in [(sido, sigungu), alias, (sido, city_key(sigungu)), (sido, sido)]:
            if key and key in coord:
                return coord[key]
        # 군위처럼 시도가 바뀐 경우
        for (a, b), latlon in coord.items():
            if b == sigungu or city_key(b) == sigungu:
                return latlon
        return None

    district_rows = []
    for (sido, sigungu), rec in sorted(stats.items()):
        latlon = find_coord(sido, sigungu)
        if not latlon:
            continue
        rec = {**rec, "lat": latlon[0], "lon": latlon[1]}
        district_rows.append(rec)

    spots = []
    district_lookup = {(r["sido"], r["sigungu"]): r for r in district_rows}
    by_city = {(r["sido"], city_key(r["sigungu"])): r for r in district_rows}

    def find_district(sido: str, sigungu: str):
        return (
            district_lookup.get((sido, sigungu))
            or by_city.get((sido, city_key(sigungu)))
            or district_lookup.get((sido, sido))
        )

    for sido, sigungu, dong, lat, lon in dongs:
        rec = find_district(sido, sigungu)
        if not rec:
            continue
        spots.append(
            {
                "agency": rec["agency"],
                "sido": rec["sido"],
                "sigungu": rec["sigungu"],
                "spot_name": dong,
                "lat": lat,
                "lon": lon,
                "total": rec["total"],
                "violent": rec["violent"],
                "theft": rec["theft"],
                "sexual": rec["sexual"],
                "fraud": rec["fraud"],
                "traffic": rec["traffic"],
                "night": rec["night"],
                "other": rec["other"],
            }
        )

    def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
        with path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    write_csv(
        PROCESSED / "districts.csv",
        district_rows,
        [
            "agency",
            "sido",
            "sigungu",
            "lat",
            "lon",
            "total",
            "violent",
            "theft",
            "sexual",
            "fraud",
            "traffic",
            "night",
            "other",
        ],
    )
    write_csv(
        PROCESSED / "spots.csv",
        spots,
        [
            "agency",
            "sido",
            "sigungu",
            "spot_name",
            "lat",
            "lon",
            "total",
            "violent",
            "theft",
            "sexual",
            "fraud",
            "traffic",
            "night",
            "other",
        ],
    )
    station_rows = build_stations(district_rows, spots)
    write_csv(
        PROCESSED / "stations.csv",
        station_rows,
        [
            "agency",
            "station",
            "unit_name",
            "unit_label",
            "kind",
            "address",
            "sido",
            "sigungu",
            "lat",
            "lon",
            "catchment",
            "total",
            "violent",
            "theft",
            "sexual",
            "fraud",
            "traffic",
            "night",
            "other",
        ],
    )
    summary = {
        "districts": len(district_rows),
        "spots": len(spots),
        "stations": len(station_rows),
        "agencies": sorted({r["agency"] for r in district_rows}),
        "gwangju_donggu": any(r["sido"] == "광주광역시" and r["sigungu"] == "동구" for r in district_rows),
        "gwangju_dongbu": sum(1 for r in station_rows if r["station"] == "광주동부"),
    }
    (PROCESSED / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_station_address(addr: str) -> tuple[str, str, str | None] | None:
    addr = re.sub(r"\s+", " ", addr or "").strip()
    sido = None
    rest = addr
    for name in sorted(SIDO_PREFIXES, key=len, reverse=True):
        if addr.startswith(name):
            sido = ADDRESS_SIDO_NORM.get(name, name)
            if name == "제주도":
                sido = "제주특별자치도"
            rest = addr[len(name) :].strip()
            break
    if not sido:
        return None
    tokens = rest.split()
    if not tokens:
        return None
    sigungu = tokens[0]
    start = 1
    if sigungu.endswith("시") and len(tokens) > 1 and tokens[1].endswith("구"):
        start = 2
    elif not sigungu.endswith(("시", "군", "구")):
        return None
    hint = None
    for token in tokens[start:]:
        clean = token.strip(",")
        if clean.endswith(("동", "읍", "면", "가", "리")):
            hint = clean
            break
    return sido, sigungu, hint


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def build_stations(district_rows: list[dict], spots: list[dict]) -> list[dict]:
    district_lookup = {(r["sido"], r["sigungu"]): r for r in district_rows}
    dong_index: dict[tuple[str, str], list[tuple[str, float, float]]] = {}
    for spot in spots:
        dong_index.setdefault((spot["sido"], spot["sigungu"]), []).append(
            (spot["spot_name"], float(spot["lat"]), float(spot["lon"]))
        )

    path = RAW / "stations.csv"
    raw_rows = list(csv.DictReader(path.open(encoding="cp949")))
    built = []
    for row in raw_rows:
        agency = CHEONG_TO_AGENCY.get(row["시도청"])
        parsed = parse_station_address(row["주소"])
        if not agency or not parsed:
            continue
        sido, sigungu, hint = parsed
        rec = district_lookup.get((sido, sigungu))
        if not rec:
            continue
        candidates = dong_index.get((sido, sigungu), [])
        latlon = None
        if hint:
            for name, lat, lon in candidates:
                if hint in name or name in hint:
                    latlon = (lat, lon)
                    break
        if not latlon:
            for name, lat, lon in candidates:
                if row["관서명"] and row["관서명"] in name:
                    latlon = (lat, lon)
                    break
        if not latlon:
            latlon = (rec["lat"], rec["lon"])
        label = f"{row['관서명']}{row['구분']}" if row["구분"] not in row["관서명"] else row["관서명"]
        built.append(
            {
                "agency": agency,
                "station": row["경찰서"],
                "unit_name": row["관서명"],
                "unit_label": label,
                "kind": row["구분"],
                "address": re.sub(r"\s+", " ", row["주소"]).strip(),
                "sido": sido,
                "sigungu": sigungu,
                "lat": latlon[0],
                "lon": latlon[1],
                "catchment": "",
                "total": rec["total"],
                "violent": rec["violent"],
                "theft": rec["theft"],
                "sexual": rec["sexual"],
                "fraud": rec["fraud"],
                "traffic": rec["traffic"],
                "night": rec["night"],
                "other": rec["other"],
            }
        )

    # 같은 시군구 안 가장 가까운 지구대·파출소에 행정동을 붙인다.
    by_area: dict[tuple[str, str], list[int]] = {}
    for i, st in enumerate(built):
        by_area.setdefault((st["sido"], st["sigungu"]), []).append(i)
    catchment = [[] for _ in built]
    for spot in spots:
        idxs = by_area.get((spot["sido"], spot["sigungu"]))
        if not idxs:
            continue
        best = min(
            idxs,
            key=lambda i: _haversine(spot["lat"], spot["lon"], built[i]["lat"], built[i]["lon"]),
        )
        catchment[best].append(spot["spot_name"])
    for st, names in zip(built, catchment):
        st["catchment"] = ", ".join(names[:8])
    return built


if __name__ == "__main__":
    build()
    print((PROCESSED / "summary.json").read_text(encoding="utf-8"))
