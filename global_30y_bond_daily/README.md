# global_30y_bond_daily

Builds a daily history chart for 30Y sovereign yields in the US, Japan, Korea, the UK, and mainland China.

## Usage

```powershell
python global_30y_bond_daily\cli.py --refresh-cache
```

The chart writes:

- `site\charts\global-rates\global-30y-bond-daily-history.html`
- `site\data\global-rates\global-30y-bond-daily-history.csv`
- `site\data\global-rates\global-30y-bond-daily-summary.csv`

## Data Source Notes

The default provider uses TradingView daily bars for these symbols:

- `TVC:US30Y`
- `TVC:JP30Y`
- `TVC:KR30Y`
- `TVC:GB30Y`
- `TVC:CN30Y`

TradingView is a free web data source, but it does not provide a formal public API for this endpoint. The downloader therefore keeps a local CSV cache under `data\global_30y_bond_daily\cache`. If a live request fails, the build uses cached data for optional markets.

Daily bars are not forward filled. Missing holidays and missing source rows remain absent. Weekends are hidden on the Plotly date axis.
