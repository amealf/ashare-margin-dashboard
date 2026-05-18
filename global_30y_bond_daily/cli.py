from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    __package__ = "global_30y_bond_daily"

from .config import DEFAULT_CONFIG_PATH, load_config, resolve_config_path
from .plot import write_plot
from .providers import tradingview_provider
from .summary import build_summary, chart_meta, write_csv
from .transform import standardize_market


PROVIDERS = {
    "tradingview": tradingview_provider.fetch,
}


def build(
    config_path: str | Path | None = None,
    output_html: str | Path | None = None,
    data_csv: str | Path | None = None,
    summary_csv: str | Path | None = None,
    refresh_cache: bool = False,
    strict: bool = False,
) -> dict:
    config = load_config(config_path)
    html_path = Path(output_html) if output_html else resolve_config_path(config, config["output"]["html"])
    data_path = Path(data_csv) if data_csv else resolve_config_path(config, config["output"]["data_csv"])
    summary_path = Path(summary_csv) if summary_csv else resolve_config_path(config, config["output"]["summary_csv"])
    warnings: list[str] = []
    frames = []

    for market in config["markets"]:
        raw, market_warnings = fetch_market_with_cache(config, market, refresh_cache, strict)
        warnings.extend(market_warnings)
        frames.append(standardize_market(raw, market))

    data = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    summary = build_summary(data, config["markets"])
    write_csv(data, data_path)
    write_csv(summary, summary_path)
    write_plot(data, config["markets"], html_path)

    meta = chart_meta(summary)
    meta["output_html"] = str(html_path)
    meta["data_csv"] = str(data_path)
    meta["summary_csv"] = str(summary_path)
    meta["warnings"] = warnings
    return meta


def fetch_market_with_cache(
    config: dict,
    market: dict,
    refresh_cache: bool = False,
    strict: bool = False,
) -> tuple[pd.DataFrame, list[str]]:
    warnings: list[str] = []
    cache_path = market_cache_path(config, market)
    cached = read_cache(cache_path)
    if not cached.empty and not refresh_cache:
        return cached, warnings

    provider = PROVIDERS.get(market["provider"])
    if provider is None:
        raise ValueError(f"Unsupported provider: {market['provider']}")
    try:
        raw = provider(market, config)
    except Exception as exc:
        if strict or not market.get("optional", False):
            raise
        if not cached.empty:
            warnings.append(f"{market['label']}: provider failed, using cache: {exc}")
            return cached, warnings
        warnings.append(f"{market['label']}: {exc}")
        return pd.DataFrame(columns=["date", "open", "high", "low", "close"]), warnings

    if raw.empty:
        if not cached.empty:
            warnings.append(f"{market['label']}: provider returned no rows, using cache")
            return cached, warnings
        return raw, warnings
    write_cache(cache_path, raw)
    return raw, warnings


def market_cache_path(config: dict, market: dict) -> Path:
    cache_dir = resolve_config_path(config, (config.get("history") or {}).get("cache_dir", "../data/global_30y_bond_daily/cache"))
    return cache_dir / f"{market['region']}.csv"


def read_cache(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=["date", "open", "high", "low", "close"])
    return pd.read_csv(path, parse_dates=["date"])


def write_cache(path: Path, data: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame = data.copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce").dt.date
    frame = frame.dropna(subset=["date"]).sort_values("date").drop_duplicates("date", keep="last")
    frame.to_csv(path, index=False, encoding="utf-8-sig")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build global 30Y sovereign yield daily history chart")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH), help="Path to config.yaml")
    parser.add_argument("--output-html", help="Output Plotly HTML path")
    parser.add_argument("--data-csv", help="Output history CSV path")
    parser.add_argument("--summary-csv", help="Output summary CSV path")
    parser.add_argument("--refresh-cache", action="store_true", help="Fetch providers even when cache exists")
    parser.add_argument("--strict", action="store_true", help="Fail on optional provider errors")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    meta = build(
        config_path=args.config,
        output_html=args.output_html,
        data_csv=args.data_csv,
        summary_csv=args.summary_csv,
        refresh_cache=args.refresh_cache,
        strict=args.strict,
    )
    print(f"HTML: {meta['output_html']}")
    print(f"CSV: {meta['data_csv']}")
    print(f"Summary CSV: {meta['summary_csv']}")
    for warning in meta.get("warnings", []):
        print(f"Warning: {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
