from __future__ import annotations

from pathlib import Path

import pandas as pd


def build_summary(data: pd.DataFrame, markets: list[dict]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for market in markets:
        frame = data[data["region"] == market["region"]].copy()
        frame = frame.dropna(subset=["close_yield_pct"]).sort_values("date")
        if frame.empty:
            rows.append(
                {
                    "region": market["region"],
                    "label": market["label"],
                    "symbol": market["symbol"],
                    "source": market["source_name"],
                    "status": "missing",
                    "latest_date": "",
                    "latest_yield_pct": "",
                    "daily_change_bp": "",
                    "ytd_change_bp": "",
                    "first_date": "",
                    "row_count": 0,
                }
            )
            continue
        latest = frame.iloc[-1]
        rows.append(
            {
                "region": market["region"],
                "label": market["label"],
                "symbol": market["symbol"],
                "source": market["source_name"],
                "status": "ok",
                "latest_date": latest["date"],
                "latest_yield_pct": round(float(latest["close_yield_pct"]), 3),
                "daily_change_bp": round_number(latest["daily_change_bp"]),
                "ytd_change_bp": round_number(latest["ytd_change_bp"]),
                "first_date": frame.iloc[0]["date"],
                "row_count": int(len(frame)),
            }
        )
    return pd.DataFrame(rows)


def write_csv(data: pd.DataFrame, output_csv: str | Path) -> None:
    path = Path(output_csv)
    path.parent.mkdir(parents=True, exist_ok=True)
    data.to_csv(path, index=False, encoding="utf-8-sig")


def chart_meta(summary: pd.DataFrame) -> dict:
    metrics = []
    for row in summary.itertuples(index=False):
        if row.status == "ok":
            daily = "" if pd.isna(row.daily_change_bp) else f" / {float(row.daily_change_bp):+.1f} bp"
            value = f"{float(row.latest_yield_pct):.3f}%{daily}"
            date_text = str(row.latest_date)
        else:
            value = "No data"
            date_text = ""
        metrics.append({"label": row.label, "value": value, "date": date_text})
    return {"metrics": metrics}


def round_number(value: object) -> float | str:
    if pd.isna(value):
        return ""
    return round(float(value), 1)
