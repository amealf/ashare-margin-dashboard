from __future__ import annotations

import pandas as pd


def convert_yield_to_percent(values, market: dict) -> pd.Series:
    series = pd.to_numeric(values, errors="coerce") * float(market.get("value_scale", 1.0))
    unit = str(market.get("yield_unit", "percent")).lower()
    if unit in {"percent", "pct", "%"}:
        return series
    if unit in {"decimal", "ratio"}:
        return series * 100
    if unit in {"bp", "bps", "basis_points"}:
        return series / 100
    raise ValueError(f"Unsupported yield_unit: {unit}")


def standardize_market(raw: pd.DataFrame, market: dict) -> pd.DataFrame:
    if raw.empty:
        return pd.DataFrame(columns=output_columns())

    frame = raw.copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce").dt.date
    frame["close_yield_pct"] = convert_yield_to_percent(frame["close"], market)
    frame["open_yield_pct"] = convert_yield_to_percent(frame["open"], market)
    frame["high_yield_pct"] = convert_yield_to_percent(frame["high"], market)
    frame["low_yield_pct"] = convert_yield_to_percent(frame["low"], market)
    frame = frame.dropna(subset=["date", "close_yield_pct"])
    if frame.empty:
        return pd.DataFrame(columns=output_columns())

    frame = frame.sort_values("date").drop_duplicates("date", keep="last")
    frame["daily_change_bp"] = frame["close_yield_pct"].diff() * 100
    frame["first_yield_pct"] = frame["close_yield_pct"].dropna().iloc[0]
    frame["change_from_first_bp"] = (frame["close_yield_pct"] - frame["first_yield_pct"]) * 100
    year_start = frame.groupby(pd.to_datetime(frame["date"]).dt.year)["close_yield_pct"].transform("first")
    frame["ytd_change_bp"] = (frame["close_yield_pct"] - year_start) * 100
    frame["region"] = market["region"]
    frame["label"] = market["label"]
    frame["source"] = market["source_name"]
    frame["symbol"] = market["symbol"]
    return frame[output_columns()]


def output_columns() -> list[str]:
    return [
        "date",
        "region",
        "label",
        "symbol",
        "source",
        "open_yield_pct",
        "high_yield_pct",
        "low_yield_pct",
        "close_yield_pct",
        "daily_change_bp",
        "ytd_change_bp",
        "change_from_first_bp",
    ]
