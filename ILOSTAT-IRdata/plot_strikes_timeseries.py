#!/usr/bin/env python3
"""
Plot the number of strikes/lockouts over time for a set of countries, from
the tidy panel built by build_panel.py.

Usage:
    python3 plot_strikes_timeseries.py
    python3 plot_strikes_timeseries.py --countries Germany France Japan
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
]

# Categorical palette, slots 1-4 (blue, orange, aqua, yellow) from the
# project's validated data-viz palette; assign by fixed order, never cycled.
SERIES_COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]

# Short direct-label text for line ends (kept distinct from the legend, which
# carries the full country name).
SHORT_LABELS = {
    "Germany": "DE",
    "France": "FR",
    "United Kingdom of Great Britain and Northern Ireland": "UK",
    "United States of America": "US",
}

CHART_BG = "#fcfcfb"
INK_PRIMARY = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRIDLINE = "#e1e0d9"
AXIS_LINE = "#c3c2b7"


def load_series(countries: list[str]) -> dict[str, list[tuple[int, float]]]:
    if not PANEL_PATH.exists():
        raise SystemExit(f"{PANEL_PATH} not found. Run build_panel.py first.")

    series: dict[str, list[tuple[int, float]]] = {c: [] for c in countries}
    with PANEL_PATH.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            country = row["ref_area"]
            if country not in series:
                continue
            value = row["n_strikes_lockouts"]
            if value == "":
                continue
            series[country].append((int(row["time"]), float(value)))

    for country, points in series.items():
        if not points:
            print(f"WARNING: no data found for '{country}'")
        points.sort()
    return series


def plot(series: dict[str, list[tuple[int, float]]], out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(10, 6), dpi=150)
    fig.patch.set_facecolor(CHART_BG)
    ax.set_facecolor(CHART_BG)

    for (country, points), color in zip(series.items(), SERIES_COLORS):
        if not points:
            continue
        years = [p[0] for p in points]
        values = [p[1] for p in points]
        ax.plot(
            years,
            values,
            label=country,
            color=color,
            linewidth=2,
            solid_capstyle="round",
            marker="o",
            markersize=3,
        )
        last_year, last_value = points[-1]
        ax.annotate(
            SHORT_LABELS.get(country, country),
            xy=(last_year, last_value),
            xytext=(6, 0),
            textcoords="offset points",
            fontsize=9,
            color=INK_SECONDARY,
            va="center",
        )

    ax.set_title("Number of strikes and lockouts", color=INK_PRIMARY, fontsize=14, loc="left", pad=12)
    ax.set_ylabel("Number of strikes/lockouts", color=INK_SECONDARY, fontsize=10)

    ax.grid(axis="y", color=GRIDLINE, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    for spine_name, spine in ax.spines.items():
        if spine_name == "bottom":
            spine.set_color(AXIS_LINE)
        else:
            spine.set_visible(False)
    ax.tick_params(axis="x", colors=INK_MUTED, labelsize=9)
    ax.tick_params(axis="y", colors=INK_MUTED, labelsize=9, length=0)

    legend = ax.legend(
        loc="upper left",
        bbox_to_anchor=(0, -0.12),
        ncol=2,
        frameon=False,
        fontsize=9,
        labelcolor=INK_SECONDARY,
    )

    fig.tight_layout()
    fig.savefig(out_path, facecolor=CHART_BG, bbox_extra_artists=(legend,), bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--countries",
        nargs="+",
        default=DEFAULT_COUNTRIES,
        help="ILOSTAT ref_area names to plot (default: Germany, France, UK, US).",
    )
    parser.add_argument(
        "--out",
        default=str(OUT_DIR / "strikes_timeseries_de_fr_uk_us.png"),
        help="Output image path.",
    )
    args = parser.parse_args()

    series = load_series(args.countries)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    plot(series, out_path)
    print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
