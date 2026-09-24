#!/usr/bin/env python3
"""Build a static HTML dashboard from data_wells.json for GitHub Pages.

Reads the local data_wells.json (produced by fetch_data_wells.py) and renders
a self-contained report to docs/index.html, ready to be served by GitHub
Pages configured to publish from the /docs folder.

Usage:
    python generate_report.py [--input data_wells.json] [--output docs/index.html]
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
from plotly.subplots import make_subplots

DEFAULT_INPUT = "data_wells.json"
DEFAULT_OUTPUT = "docs/index.html"


def load_dataframe(input_path: str) -> pd.DataFrame:
    with open(input_path, encoding="utf-8") as f:
        records: list[dict[str, Any]] = json.load(f)

    df = pd.DataFrame(records)
    df["records"] = pd.to_numeric(df["records"], errors="coerce").fillna(0).astype(int)
    df["is_sensitive"] = df["is_sensitive"].fillna(False).astype(bool)
    df["parsed_date"] = pd.to_datetime(df["date"], errors="coerce")
    return df


def data_type_counts(df: pd.DataFrame) -> Counter[str]:
    counts: Counter[str] = Counter()
    for value in df["data"].dropna():
        for field in str(value).split(","):
            field = field.strip()
            if field:
                counts[field] += 1
    return counts


def build_top_breaches_figure(df: pd.DataFrame, top_n: int = 20) -> go.Figure:
    top = df.nlargest(top_n, "records").sort_values("records")
    fig = go.Figure(
        go.Bar(
            x=top["records"],
            y=top["name"],
            orientation="h",
            marker_color=top["is_sensitive"].map({True: "#d62728", False: "#1f77b4"}),
            text=top["records"],
            texttemplate="%{text:,}",
            textposition="outside",
        )
    )
    fig.update_layout(
        title=f"Top {top_n} Breaches by Records Exposed",
        xaxis_title="Records",
        yaxis_title=None,
        margin=dict(l=10, r=10, t=50, b=10),
        height=650,
    )
    return fig


def build_timeline_figure(df: pd.DataFrame) -> go.Figure:
    yearly = (
        df.dropna(subset=["parsed_date"])
        .assign(year=lambda d: d["parsed_date"].dt.year)
        .groupby("year")
        .agg(breaches=("name", "count"), records=("records", "sum"))
        .reset_index()
    )
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Bar(x=yearly["year"], y=yearly["breaches"], name="Breach Count", marker_color="#1f77b4"),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=yearly["year"],
            y=yearly["records"],
            name="Records Exposed",
            mode="lines+markers",
            marker_color="#d62728",
        ),
        secondary_y=True,
    )
    fig.update_layout(
        title="Breaches and Records Exposed by Year",
        margin=dict(l=10, r=10, t=50, b=10),
        height=450,
    )
    fig.update_yaxes(title_text="Breach Count", secondary_y=False)
    fig.update_yaxes(title_text="Records Exposed", secondary_y=True)
    return fig


def build_sensitivity_figure(df: pd.DataFrame) -> go.Figure:
    counts = df["is_sensitive"].value_counts()
    fig = go.Figure(
        go.Pie(
            labels=["Sensitive" if v else "Not Sensitive" for v in counts.index],
            values=counts.values,
            marker_colors=["#d62728" if v else "#1f77b4" for v in counts.index],
            hole=0.4,
        )
    )
    fig.update_layout(title="Sensitive vs. Non-Sensitive Breaches", margin=dict(l=10, r=10, t=50, b=10), height=420)
    return fig


def build_data_type_figure(df: pd.DataFrame, top_n: int = 20) -> go.Figure:
    counts = data_type_counts(df)
    top = counts.most_common(top_n)
    labels = [label for label, _ in reversed(top)]
    values = [value for _, value in reversed(top)]
    fig = go.Figure(go.Bar(x=values, y=labels, orientation="h", marker_color="#2ca02c"))
    fig.update_layout(
        title=f"Most Common Exposed Data Types (Top {top_n})",
        xaxis_title="Number of Breaches",
        margin=dict(l=10, r=10, t=50, b=10),
        height=650,
    )
    return fig


def build_summary_html(df: pd.DataFrame) -> str:
    total_breaches = len(df)
    total_records = int(df["records"].sum())
    sensitive_pct = 100 * df["is_sensitive"].mean() if total_breaches else 0
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return f"""
    <div class="summary">
      <div class="stat"><span class="value">{total_breaches:,}</span><span class="label">Data Wells</span></div>
      <div class="stat"><span class="value">{total_records:,}</span><span class="label">Total Records Exposed</span></div>
      <div class="stat"><span class="value">{sensitive_pct:.1f}%</span><span class="label">Marked Sensitive</span></div>
    </div>
    <p class="generated">Last updated: {generated_at}</p>
    """


PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>DeHashed Data Wells Dashboard</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  body {{ font-family: -apple-system, Segoe UI, Roboto, sans-serif; margin: 0; padding: 0 20px 40px; background: #f7f7f9; color: #222; }}
  h1 {{ padding-top: 30px; }}
  .summary {{ display: flex; gap: 30px; flex-wrap: wrap; margin: 20px 0; }}
  .stat {{ background: white; border-radius: 8px; padding: 16px 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
  .stat .value {{ display: block; font-size: 28px; font-weight: 700; }}
  .stat .label {{ display: block; font-size: 13px; color: #666; }}
  .generated {{ color: #888; font-size: 13px; }}
  .chart {{ background: white; border-radius: 8px; padding: 10px; margin-bottom: 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
</style>
</head>
<body>
<h1>DeHashed Data Wells Dashboard</h1>
{summary}
<div class="chart">{top_breaches}</div>
<div class="chart">{timeline}</div>
<div class="chart">{sensitivity}</div>
<div class="chart">{data_types}</div>
</body>
</html>
"""


def render_report(df: pd.DataFrame) -> str:
    figures = {
        "top_breaches": build_top_breaches_figure(df),
        "timeline": build_timeline_figure(df),
        "sensitivity": build_sensitivity_figure(df),
        "data_types": build_data_type_figure(df),
    }

    html_parts: dict[str, str] = {}
    first = True
    for key, fig in figures.items():
        html_parts[key] = pio.to_html(
            fig,
            include_plotlyjs="cdn" if first else False,
            full_html=False,
            config={"displaylogo": False},
        )
        first = False

    return PAGE_TEMPLATE.format(summary=build_summary_html(df), **html_parts)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default=DEFAULT_INPUT, help=f"Path to input JSON (default: {DEFAULT_INPUT})")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help=f"Path to output HTML (default: {DEFAULT_OUTPUT})")
    args = parser.parse_args()

    df = load_dataframe(args.input)
    html = render_report(df)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")

    print(f"Wrote dashboard for {len(df):,} data wells to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
