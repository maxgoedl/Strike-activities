#!/usr/bin/env python3
"""
Combine the raw ILOSTAT industrial-disputes CSVs (downloaded by
fetch_ilostat_irdata.py into raw/) into a single tidy country-year panel.

ILOSTAT's data API (requested with type=label) returns a long SDMX-style
layout with columns such as ref_area.label, indicator.label, source.label,
sex.label, classif1.label, classif2.label, time, obs_value, obs_status.label,
note_*.label (exact columns can vary slightly by indicator). This script
keeps the total/aggregate rows (no sex or economic-activity breakdown, i.e.
classif/sex columns are empty or say "Total") and reshapes to one row per
country-year with one column per concept (number of strikes/lockouts,
workers involved, days not worked).
"""
from __future__ import annotations

import csv
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW_DIR = HERE / "raw"
OUT_DIR = HERE / "processed"
OUT_PATH = OUT_DIR / "industrial_disputes_panel.csv"


def find_column(fieldnames: list[str], candidates: tuple[str, ...]) -> str:
    for candidate in candidates:
        if candidate in fieldnames:
            return candidate
    raise RuntimeError(f"None of {candidates} found in columns: {fieldnames}")


def is_total_row(row: dict) -> bool:
    for col, val in row.items():
        if not val:
            continue
        if (col.startswith("classif") or col in ("sex", "sex.label")) and "total" not in val.lower():
            return False
    return True


def load_manifest() -> list[dict]:
    manifest_path = RAW_DIR / "manifest.csv"
    if not manifest_path.exists():
        raise SystemExit(
            f"{manifest_path} not found. Run fetch_ilostat_irdata.py first."
        )
    with manifest_path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main() -> int:
    manifest = load_manifest()
    panel: dict[tuple[str, str], dict[str, str]] = {}

    for entry in manifest:
        concept = entry["concept"]
        indicator_id = entry.get("id") or entry.get("indicator") or entry.get("indicator.id")
        raw_path = RAW_DIR / f"{indicator_id}.csv"
        if not raw_path.exists():
            print(f"WARNING: {raw_path} missing, skipping {concept}")
            continue

        with raw_path.open(encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames or []
            country_col = find_column(fieldnames, ("ref_area.label", "ref_area"))
            time_col = find_column(fieldnames, ("time",))
            value_col = find_column(fieldnames, ("obs_value",))

            for row in reader:
                if not is_total_row(row):
                    continue
                country = row.get(country_col)
                year = row.get(time_col)
                value = row.get(value_col)
                if not country or not year or value in (None, ""):
                    continue
                key = (country, year)
                panel.setdefault(key, {"ref_area": country, "time": year})
                # Some indicators report the same total under more than one
                # classification breakdown (e.g. both a "broad sector" and an
                # "aggregate" total); keep the first one seen for stability.
                panel[key].setdefault(concept, value)

    if not panel:
        print("No data rows assembled; nothing to write.")
        return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_fieldnames = ["ref_area", "time", "n_strikes_lockouts", "workers_involved", "days_not_worked"]
    with OUT_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=out_fieldnames)
        writer.writeheader()
        for key in sorted(panel):
            row = panel[key]
            writer.writerow({fn: row.get(fn, "") for fn in out_fieldnames})

    print(f"Wrote {len(panel)} country-year rows to {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
