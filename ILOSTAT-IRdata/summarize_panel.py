#!/usr/bin/env python3
"""
Print a first-look summary of the tidy country-year panel built by
build_panel.py: overall descriptive stats, reporting coverage by country
and by year, pairwise correlations between the four series, and the
biggest country-years on record (useful as an outlier/sanity check).

Also writes the same report to processed/summary_report.txt.
"""
from __future__ import annotations

import csv
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
PANEL_PATH = HERE / "processed" / "industrial_disputes_panel.csv"
REPORT_PATH = HERE / "processed" / "summary_report.txt"

VARS = ["n_strikes_lockouts", "workers_involved", "days_not_worked", "days_not_worked_rate"]
VAR_LABELS = {
    "n_strikes_lockouts": "Number of strikes/lockouts",
    "workers_involved": "Workers involved (thousands)",
    "days_not_worked": "Days not worked",
    "days_not_worked_rate": "Days not worked per 1000 workers",
}
VAR_SHORT = {
    "n_strikes_lockouts": "n_strikes",
    "workers_involved": "workers_inv",
    "days_not_worked": "days_notwkd",
    "days_not_worked_rate": "days_rate",
}


def load_panel() -> list[dict]:
    if not PANEL_PATH.exists():
        raise SystemExit(f"{PANEL_PATH} not found. Run build_panel.py first.")
    rows = []
    with PANEL_PATH.open(encoding="utf-8") as f:
        for raw in csv.DictReader(f):
            row = {"ref_area": raw["ref_area"], "time": int(raw["time"])}
            for col in VARS:
                v = raw.get(col)
                row[col] = float(v) if v not in (None, "") else None
            rows.append(row)
    return rows


def overall_stats(rows: list[dict], out: list[str]) -> None:
    out.append(f"Total country-year rows: {len(rows)}")
    out.append(f"Distinct countries/territories: {len(set(r['ref_area'] for r in rows))}")
    years = [r["time"] for r in rows]
    out.append(f"Year range: {min(years)}-{max(years)}")
    out.append("")

    header = f"{'variable':<24}{'N':>7}{'missing':>9}{'mean':>16}{'sd':>16}{'min':>10}{'median':>12}{'max':>16}"
    out.append(header)
    out.append("-" * len(header))
    for col in VARS:
        vals = sorted(v for v in (r[col] for r in rows) if v is not None)
        n = len(vals)
        missing = len(rows) - n
        if n:
            mean = sum(vals) / n
            sd = math.sqrt(sum((x - mean) ** 2 for x in vals) / (n - 1)) if n > 1 else float("nan")
            median = vals[n // 2] if n % 2 else (vals[n // 2 - 1] + vals[n // 2]) / 2
            mn, mx = vals[0], vals[-1]
        else:
            mean = sd = median = mn = mx = float("nan")
        out.append(
            f"{col:<24}{n:>7}{missing:>9}{mean:>16.2f}{sd:>16.2f}{mn:>10.2f}{median:>12.2f}{mx:>16.2f}"
        )
    out.append("")


def coverage_by_country(rows: list[dict], out: list[str], top_n: int = 10) -> None:
    by_country: dict[str, list[dict]] = {}
    for r in rows:
        by_country.setdefault(r["ref_area"], []).append(r)

    def reported_years(country_rows: list[dict]) -> int:
        return sum(1 for r in country_rows if any(r[c] is not None for c in VARS))

    summary = [
        (country, reported_years(rs), min(r["time"] for r in rs), max(r["time"] for r in rs))
        for country, rs in by_country.items()
    ]
    summary.sort(key=lambda x: x[1], reverse=True)

    out.append(f"Reporting coverage by country ({len(summary)} countries/territories):")
    out.append(f"  Top {top_n} by number of years with any data reported:")
    for country, n_years, ymin, ymax in summary[:top_n]:
        out.append(f"    {country:<30}{n_years:>4} years  ({ymin}-{ymax})")
    out.append(f"  Bottom {top_n} (least-covered):")
    for country, n_years, ymin, ymax in summary[-top_n:]:
        out.append(f"    {country:<30}{n_years:>4} years  ({ymin}-{ymax})")
    out.append("")


def coverage_by_year(rows: list[dict], out: list[str]) -> None:
    by_year: dict[int, set[str]] = {}
    for r in rows:
        if any(r[c] is not None for c in VARS):
            by_year.setdefault(r["time"], set()).add(r["ref_area"])

    out.append("Reporting coverage by year (countries reporting any data, every 5th year):")
    for year in sorted(by_year):
        if year % 5 == 0:
            out.append(f"    {year}: {len(by_year[year]):>4} countries")
    last_year = max(by_year)
    out.append(f"    {last_year} (latest): {len(by_year[last_year]):>4} countries")
    out.append("")


def pearson(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    denx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    deny = math.sqrt(sum((y - my) ** 2 for y in ys))
    return num / (denx * deny) if denx and deny else float("nan")


def correlations(rows: list[dict], out: list[str]) -> None:
    out.append("Pairwise correlations (pairwise-complete observations):")
    col_width = 13
    header = f"{'':<14}" + "".join(f"{VAR_SHORT[c]:>{col_width}}" for c in VARS)
    out.append(header)
    for c1 in VARS:
        line = f"{VAR_SHORT[c1]:<14}"
        for c2 in VARS:
            paired = [(r[c1], r[c2]) for r in rows if r[c1] is not None and r[c2] is not None]
            if len(paired) < 2:
                line += f"{'n/a':>{col_width}}"
                continue
            xs, ys = zip(*paired)
            r = pearson(list(xs), list(ys))
            line += f"{r:>{col_width}.2f}"
        out.append(line)
    out.append("")
    out.append("Key: " + ", ".join(f"{short}={VAR_LABELS[c]}" for c, short in VAR_SHORT.items()))
    out.append("")


def top_country_years(rows: list[dict], out: list[str], top_n: int = 10) -> None:
    for col in ["n_strikes_lockouts", "days_not_worked"]:
        out.append(f"Top {top_n} country-years by {VAR_LABELS[col]}:")
        ranked = sorted((r for r in rows if r[col] is not None), key=lambda r: r[col], reverse=True)
        for r in ranked[:top_n]:
            out.append(f"    {r['ref_area']:<30}{r['time']:>6}  {r[col]:>16,.0f}")
        out.append("")


def main() -> int:
    rows = load_panel()
    out: list[str] = []

    out.append("=== Overall descriptive statistics ===")
    overall_stats(rows, out)

    out.append("=== Coverage ===")
    coverage_by_country(rows, out)
    coverage_by_year(rows, out)

    out.append("=== Correlations ===")
    correlations(rows, out)

    out.append("=== Outliers / biggest recorded disputes ===")
    top_country_years(rows, out)

    report = "\n".join(out)
    print(report)

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report + "\n", encoding="utf-8")
    print(f"\nWrote report to {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
