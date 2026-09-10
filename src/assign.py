from __future__ import annotations

import pandas as pd


def assign_cars(spots: pd.DataFrame, n_cars: int) -> pd.DataFrame:
    if spots.empty:
        return spots
    out = spots.copy()
    n_cars = max(1, min(int(n_cars), len(out)))
    if n_cars == 1 or len(out) == 1:
        out["car"] = "1호차"
        out["order"] = range(1, len(out) + 1)
        return out

    # 경도 기준으로 권역을 나눠 차량이 서로 겹치지 않게 한다.
    ordered = out.sort_values("lon").reset_index(drop=True)
    size = len(ordered)
    labels = []
    for i in range(size):
        labels.append(int(i * n_cars / size))
    ordered["cluster"] = labels

    rank = (
        ordered.groupby("cluster")["score"]
        .sum()
        .sort_values(ascending=False)
        .index.tolist()
    )
    mapping = {cluster: f"{i}호차" for i, cluster in enumerate(rank, start=1)}
    ordered["car"] = ordered["cluster"].map(mapping)
    ordered = ordered.sort_values(["car", "score"], ascending=[True, False])
    ordered["order"] = ordered.groupby("car").cumcount() + 1
    return ordered.drop(columns=["cluster"])
