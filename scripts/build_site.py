from __future__ import annotations

import argparse
import html
import importlib
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import yaml


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
SITE_DIR = ROOT / "site"
CONFIG_PATH = ROOT / "charts.yml"


def load_config() -> dict:
    with CONFIG_PATH.open("r", encoding="utf-8") as fp:
        return yaml.safe_load(fp)


def site_path(relative_path: str) -> Path:
    return SITE_DIR.joinpath(*relative_path.split("/"))


def ensure_site_dirs() -> None:
    SITE_DIR.mkdir(parents=True, exist_ok=True)
    (SITE_DIR / ".nojekyll").write_text("", encoding="utf-8")


def build_margin_csi500(chart: dict) -> dict:
    sys.path.insert(0, str(SCRIPTS_DIR))
    module = importlib.import_module(chart["module"])

    margin = module.fetch_margin_balance()
    csi500 = module.fetch_csi500()
    chinext = module.fetch_chinext()
    data = pd.merge(margin, csi500, on="date", how="outer").sort_values("date")
    data = pd.merge(data, chinext, on="date", how="outer").sort_values("date")
    data = module.add_index_ratios(data)

    csv_path = site_path(chart["output_csv"])
    html_path = site_path(chart["output_html"])
    png_path = site_path(chart["output_png"])
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.parent.mkdir(parents=True, exist_ok=True)
    png_path.parent.mkdir(parents=True, exist_ok=True)

    data.to_csv(csv_path, index=False, encoding="utf-8-sig")
    module.plot_overlay(data, png_path)
    module.write_interactive_html(data, html_path)

    meta = module.chart_meta(data)
    return {
        "latest_margin_date": meta["latestMarginDate"],
        "latest_margin": meta["latestMargin"],
        "latest_csi_date": meta["latestCsiDate"],
        "latest_csi": meta["latestCsi"],
        "latest_chinext_date": meta["latestChinextDate"],
        "latest_chinext": meta["latestChinext"],
    }


BUILDERS = {
    "margin_csi500": build_margin_csi500,
}


def render_page(title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>
    :root {{ color-scheme: light; }}
    body {{
      margin: 0;
      color: #111827;
      background: #f5f7fb;
      font-family: "Microsoft YaHei", "Noto Sans CJK SC", Arial, sans-serif;
    }}
    a {{ color: inherit; text-decoration: none; }}
    .shell {{ max-width: 1180px; margin: 0 auto; padding: 28px 22px 44px; }}
    .top {{ display: flex; align-items: flex-end; justify-content: space-between; gap: 16px; margin-bottom: 22px; }}
    h1 {{ margin: 0; font-size: 28px; line-height: 1.2; }}
    h2 {{ margin: 28px 0 12px; font-size: 20px; }}
    .muted {{ color: #5b6472; font-size: 14px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 14px; }}
    .card {{
      background: #fff;
      border: 1px solid #dbe1ea;
      border-radius: 8px;
      padding: 16px;
      box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
    }}
    .card h3 {{ margin: 0 0 8px; font-size: 17px; }}
    .card p {{ margin: 0 0 12px; color: #4b5563; line-height: 1.6; font-size: 14px; }}
    .meta {{ color: #475569; font-size: 13px; line-height: 1.7; }}
    .button {{
      display: inline-flex;
      align-items: center;
      margin-top: 12px;
      padding: 8px 11px;
      border: 1px solid #cbd5e1;
      border-radius: 6px;
      background: #f8fafc;
      font-size: 14px;
    }}
    .button:hover {{ background: #eef2f7; }}
    footer {{ margin-top: 32px; color: #64748b; font-size: 12px; }}
  </style>
</head>
<body>
  <main class="shell">
    {body}
  </main>
</body>
</html>
"""


def chart_card(chart: dict, category: dict, generated: dict, prefix: str = "") -> str:
    chart_id = chart["id"]
    info = generated.get(chart_id, {})
    chart_url = prefix + chart["output_html"].replace("\\", "/")
    csv_url = prefix + chart["output_csv"].replace("\\", "/")
    return f"""
<article class="card">
  <h3>{html.escape(chart["title"])}</h3>
  <p>{html.escape(chart["description"])}</p>
  <div class="meta">
    栏目：{html.escape(category["title"])}<br>
    融资余额：{html.escape(str(info.get("latest_margin_date", "-")))}，{info.get("latest_margin", "-")} 万亿元<br>
    中证500：{html.escape(str(info.get("latest_csi_date", "-")))}，{info.get("latest_csi", "-")}<br>
    创业板指：{html.escape(str(info.get("latest_chinext_date", "-")))}，{info.get("latest_chinext", "-")}
  </div>
  <a class="button" href="{html.escape(chart_url)}">打开图表</a>
  <a class="button" href="{html.escape(csv_url)}">下载 CSV</a>
</article>
"""


def write_index(config: dict, generated: dict, selected_ids: set[str]) -> None:
    categories = {item["id"]: item for item in config["categories"]}
    charts = [chart for chart in config["charts"] if chart["id"] in selected_ids]
    now = datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d %H:%M:%S")
    sections = []
    for category in config["categories"]:
        category_charts = [chart for chart in charts if chart["category"] == category["id"]]
        if not category_charts:
            continue
        category_cards = "".join(
            chart_card(chart, category, generated, prefix="../") for chart in category_charts
        )
        index_cards = "".join(chart_card(chart, category, generated) for chart in category_charts)
        category_dir = SITE_DIR / category["id"]
        category_dir.mkdir(parents=True, exist_ok=True)
        category_body = f"""
<div class="top">
  <div>
    <h1>{html.escape(category["title"])}</h1>
    <div class="muted">{html.escape(category["description"])}</div>
  </div>
  <a class="button" href="../index.html">返回首页</a>
</div>
<div class="grid">{category_cards}</div>
<footer>更新时间：{now}（北京时间）</footer>
"""
        (category_dir / "index.html").write_text(
            render_page(category["title"], category_body),
            encoding="utf-8",
        )
        sections.append(
            f"""
<section>
  <h2>{html.escape(category["title"])}</h2>
  <p class="muted">{html.escape(category["description"])}</p>
  <div class="grid">{index_cards}</div>
</section>
"""
        )

    body = f"""
<div class="top">
  <div>
    <h1>{html.escape(config["site"]["title"])}</h1>
    <div class="muted">{html.escape(config["site"]["description"])}</div>
  </div>
  <div class="muted">北京时间 {now}</div>
</div>
{''.join(sections)}
<footer>数据源：东方财富、新浪财经。页面由 GitHub Actions 自动生成。</footer>
"""
    (SITE_DIR / "index.html").write_text(
        render_page(config["site"]["title"], body),
        encoding="utf-8",
    )


def build(selected_chart: str | None) -> None:
    config = load_config()
    ensure_site_dirs()

    if selected_chart:
        charts = [chart for chart in config["charts"] if chart["id"] == selected_chart]
        if not charts:
            raise SystemExit(f"未找到图表：{selected_chart}")
    else:
        charts = config["charts"]

    generated: dict[str, dict] = {}
    for chart in charts:
        builder = BUILDERS.get(chart["builder"])
        if not builder:
            raise SystemExit(f"未注册图表生成器：{chart['builder']}")
        generated[chart["id"]] = builder(chart)

    selected_ids = {chart["id"] for chart in charts}
    write_index(config, generated, selected_ids)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="生成 A 股图表静态站点")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--all", action="store_true", help="生成全部图表")
    group.add_argument("--chart", help="只生成指定图表 id")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    build(None if args.all else args.chart)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
