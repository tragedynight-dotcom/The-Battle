from __future__ import annotations

import math
from pathlib import Path

import pandas as pd

from .constants import (
    COMMERCIAL_KEYWORDS,
    CROWD_KEYWORDS,
    DAY_KEYWORDS,
    MISSIONS,
    NIGHT_KEYWORDS,
    REGION_PRESETS,
    RURAL_KEYWORDS,
    TIME_SLOTS,
    WEATHER_WEIGHTS,
)

PROCESSED = Path(__file__).resolve().parents[1] / "data" / "processed"


def load_districts() -> pd.DataFrame:
    return pd.read_csv(PROCESSED / "districts.csv")


def load_spots() -> pd.DataFrame:
    return pd.read_csv(PROCESSED / "spots.csv")


def load_stations() -> pd.DataFrame:
    df = pd.read_csv(PROCESSED / "stations.csv")
    df["spot_name"] = df["unit_label"]
    df["catchment"] = df["catchment"].fillna("")
    return df


def filter_scope(
    df: pd.DataFrame,
    agency: str,
    preset: str,
    focus: str | None,
    station: str | None = None,
) -> pd.DataFrame:
    if agency == "광주·전남 광역":
        out = df[df["agency"].isin(["광주광역시경찰청", "전라남도경찰청"])].copy()
    else:
        out = df[df["agency"] == agency].copy()

    allowed = None
    presets = REGION_PRESETS.get(agency, {})
    if preset in presets:
        allowed = presets[preset]
    if allowed:
        out = out[out["sigungu"].isin(allowed)]
    if focus and focus not in {"권역 전체", "경찰서 전체"}:
        if "station" in out.columns:
            out = out[out["station"] == focus]
        else:
            out = out[out["sigungu"] == focus]
    if station and station != "경찰서 전체" and "station" in out.columns:
        out = out[out["station"] == station]
    return out


def _name_weight(name: str, time_label: str, mission: str) -> float:
    text = str(name)
    weight = 1.0
    night = time_label in {"야간", "심야"}
    day = time_label in {"주간", "등하교·퇴근"}
    if any(k in text for k in COMMERCIAL_KEYWORDS):
        weight += 0.55 if night else 0.20
    if night and any(k in text for k in NIGHT_KEYWORDS):
        weight += 1.15
    if day and any(k in text for k in DAY_KEYWORDS):
        weight += 0.85
    if mission == "다중운집·역세권" and any(k in text for k in CROWD_KEYWORDS):
        weight += 0.70
    if mission == "어린이·노인 보호" and any(k in text for k in DAY_KEYWORDS):
        weight += 0.80
    if night and any(k in text for k in RURAL_KEYWORDS):
        weight *= 0.45
    if day and any(k in text for k in NIGHT_KEYWORDS) and not any(k in text for k in DAY_KEYWORDS):
        weight *= 0.75
    return weight


def score_spots(
    spots: pd.DataFrame,
    time_key: str,
    weather: str,
    mission: str,
) -> pd.DataFrame:
    if spots.empty:
        return spots
    time_cfg = TIME_SLOTS[time_key]
    weather_w = WEATHER_WEIGHTS[weather]
    mission_keys = MISSIONS[mission]

    scored = spots.copy()
    # 사기·기타 입건은 순찰로 줄어들지 않아 점수에서 뺀다.
    scored["street"] = 0.0
    for key in mission_keys:
        if key in scored.columns:
            scored["street"] += scored[key] * time_cfg["weights"].get(key, 1.0)

    unit_col = "sigungu" if "sigungu" in scored.columns else "sido"
    scored["units_in_area"] = scored.groupby(["sido", unit_col])["spot_name"].transform("count").clip(lower=1)
    scored["per_unit"] = scored["street"] / scored["units_in_area"]
    scored["name_w"] = scored["spot_name"].map(lambda n: _name_weight(n, time_cfg["label"], mission))
    scored["raw"] = scored["per_unit"] * scored["name_w"] * weather_w
    peak = float(scored["raw"].max()) or 1.0
    scored["score"] = (100 * scored["raw"] / peak).round(1)
    scored["volume_rank"] = scored["total"].rank(ascending=False, method="min").astype(int)
    scored["patrol_rank"] = scored["score"].rank(ascending=False, method="min").astype(int)
    scored["flipped"] = scored["patrol_rank"] < scored["volume_rank"]
    scored = scored.sort_values(["score", "street"], ascending=False).reset_index(drop=True)
    return scored


def top_spots(scored: pd.DataFrame, limit: int = 12) -> pd.DataFrame:
    if scored.empty:
        return scored
    group_col = "station" if "station" in scored.columns else "sigungu"
    capped = scored.groupby(group_col, group_keys=False).head(3)
    return capped.head(limit).reset_index(drop=True)


def reasons(row: pd.Series, time_key: str, weather: str, mission: str) -> str:
    bits = []
    if row.get("flipped"):
        bits.append(f"입건총량 {int(row['volume_rank'])}위 → 오늘순찰 {int(row['patrol_rank'])}위")
    bits.append("사기·사이버 제외, 순찰로 막을 죄종만")
    if TIME_SLOTS[time_key]["label"] in {"야간", "심야"}:
        bits.append("야간 번화가 가산")
    elif TIME_SLOTS[time_key]["label"] in {"주간", "등하교·퇴근"}:
        bits.append("주간·등하교 가산")
    if weather == "비":
        bits.append("우천 가중")
    bits.append(mission)
    return " / ".join(bits[:4])
