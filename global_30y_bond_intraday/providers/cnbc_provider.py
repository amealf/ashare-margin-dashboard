from __future__ import annotations

import json
import time
from datetime import datetime, time as dt_time, timezone
from http.client import IncompleteRead, RemoteDisconnected
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

import pandas as pd

from ..transform import convert_yield_to_percent


CNBC_BAR_URL = "https://ts-api.cnbc.com/harmony/app/bars"
CNBC_QUERY_TIMEZONE = ZoneInfo("America/New_York")


def fetch(market: dict, target_date, config: dict | None = None) -> pd.DataFrame:
    start_utc = datetime.combine(target_date, dt_time.min, tzinfo=timezone.utc)
    end_utc = start_utc + pd.Timedelta(days=1)
    start_text = start_utc.astimezone(CNBC_QUERY_TIMEZONE).strftime("%Y%m%d%H%M%S")
    end_text = end_utc.astimezone(CNBC_QUERY_TIMEZONE).strftime("%Y%m%d%H%M%S")
    symbol = market["symbol"]
    url = f"{CNBC_BAR_URL}/{symbol}/1M/{start_text}/{end_text}/adjusted/EST5EDT.json"

    payload = request_json(url)
    bars = ((payload.get("barData") or {}).get("priceBars") or []) if isinstance(payload, dict) else []
    if not bars:
        return pd.DataFrame(columns=["timestamp_utc", "yield_pct", "source"])

    frame = pd.DataFrame(bars)
    frame["timestamp_utc"] = pd.to_datetime(pd.to_numeric(frame["tradeTimeinMills"], errors="coerce"), unit="ms", utc=True)
    frame["yield_pct"] = convert_yield_to_percent(frame["close"], market)
    frame["source"] = market["source_name"]
    return frame.dropna(subset=["timestamp_utc", "yield_pct"]).sort_values("timestamp_utc")


def request_json(url: str, retries: int = 3, pause: float = 0.8) -> dict:
    last_error: Exception | None = None
    for attempt in range(retries):
        request = Request(
            url,
            headers={
                "Accept": "application/json,text/plain,*/*",
                "Connection": "close",
                "User-Agent": "Mozilla/5.0",
            },
        )
        try:
            with urlopen(request, timeout=45) as response:
                return json.loads(response.read().decode("utf-8", errors="replace"))
        except (HTTPError, URLError, TimeoutError, IncompleteRead, RemoteDisconnected, OSError, json.JSONDecodeError) as exc:
            last_error = exc
            time.sleep(pause * (attempt + 1))
    raise RuntimeError(f"CNBC request failed: {url}") from last_error
