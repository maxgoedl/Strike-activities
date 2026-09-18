#!/usr/bin/env python3
"""
Plot time series for all four industrial-disputes indicators (number of
strikes/lockouts, workers involved, days not worked, days-not-worked rate)
for a set of countries, as a 2x2 small-multiples figure. Each indicator gets
its own panel/y-scale (the four series are on very different scales, so they
are never combined on one axis); country colors are consistent across panels.

Usage:
    python3 plot_all_series_timeseries.py
    python3 plot_all_series_timeseries.py --countries Germany Japan
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
PANEL_PATH = HERE / "processed" / "industrial_disputes_panel.csv"
OUT_DIR = HERE / "processed"

DEFAULT_COUNTRIES = [
    "Germany",
    "France",
    "United Kingdom of Great Britain and Northern Ireland",
    "United States of America",
    "Mexico",
]

VARS = ["n_strikes_lockouts", "workers_involved", "days_not_worked", "days_not_worked_rate"]
VAR_LABELS = {
    "n_strikes_lockouts": "Number of strikes/lockouts",
    "workers_involved": "Workers involved (thousands)",
    "days_not_worked": "Days not worked",
    "days_not_worked_rate": "Days not worked per 1000 workers",
}

# Categorical palette, slots 1-5 (blue, orange, aqua, yellow, magenta) from
# the project's validated data-viz palette; assign by fixed order, never
# cycled, and kept the same across all four panels so color always means
# the same country.
SERIES_COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]

CHART_BG = "#fcfcfb"
INK_PRIMARY = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRIDLINE = "#e1e0d9"
AXIS_LINE = "#c3c2b7"


def load_data(countries: list[str]) -> dict[str, dict[str, list[tuple[int, float]]]]:
    if not PANEL_PATH.exists():
        raise SystemExit(f"{PANEL_PATH} not found. Run build_panel.py first.")

    data: dict[str, dict[str, list[tuple[int, float]]]] = {
        c: {v: [] for v in VARS} for c in countries
    }
    with PANEL_PATH.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            country = row["ref_area"]
            if country not in data:
                continue
            year = int(row["time"])
            for var in VARS:
                value = row[var]
                if value != "":
                    data[country][var].append((year, float(value)))

    for country in countries:
        for var in VARS:
            data[country][var].sort()
        if not any(data[country][v] for v in VARS):
            print(f"WARNING: no data found for '{country}'")
    return data


def style_axes(ax) -> None:
    ax.grid(axis="y", color=GRIDLINE, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    for spine_name, spine in ax.spines.items():
        if spine_name == "bottom":
            spine.set_color(AXIS_LINE)
        else:
            spine.set_visible(False)
    ax.tick_params(axis="x", colors=INK_MUTED, labelsize=8)
    ax.tick_params(axis="y", colors=INK_MUTED, labelsize=8, length=0)
    ax.set_facecolor(CHART_BG)


def plot(data: dict[str, dict[str, list[tuple[int, float]]]], countries: list[str], out_path: Path) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(14, 9), dpi=150)
    fig.patch.set_facecolor(CHART_BG)

    country_colors = dict(zip(countries, SERIES_COLORS))
    lines_for_legend = []

    for ax, var in zip(axes.flat, VARS):
        for country in countries:
            points = data[country][var]
            if not points:
                continue
            years = [p[0] for p in points]
            values = [p[1] for p in points]
            (line,) = ax.plot(
                years,
                values,
                color=country_colors[country],
                linewidth=2,
                solid_capstyle="round",
                marker="o",
                markersize=2.5,
                label=country,
            )
            if var == VARS[0]:
                lines_for_legend.append(line)
        ax.set_title(VAR_LABELS[var], color=INK_PRIMARY, fontsize=11, loc="left", pad=8)
        style_axes(ax)

    legend = fig.legend(
        handles=lines_for_legend,
        labels=countries,
        loc="lower center",
        bbox_to_anchor=(0.5, -0.02),
        ncol=len(countries),
        frameon=False,
        fontsize=9,
        labelcolor=INK_SECONDARY,
    )

    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(out_path, facecolor=CHART_BG, bbox_extra_artists=(legend,), bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--countries",
        nargs="+",
        default=DEFAULT_COUNTRIES,
        help="ILOSTAT ref_area names to plot (default: Germany, France, UK, US, Mexico).",
    )
    parser.add_argument(
        "--out",
        default=str(OUT_DIR / "timeseries_all_indicators.png"),
        help="Output image path.",
    )
    args = parser.parse_args()

    data = load_data(args.countries)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    plot(data, args.countries, out_path)
    print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
