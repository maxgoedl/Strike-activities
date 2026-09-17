#!/usr/bin/env python3
"""
Download ILOSTAT Industrial Relations data (IRdata) on industrial disputes:
number of strikes/lockouts, workers involved, days not worked, and the
days-not-worked rate per 1000 workers.

Source: https://ilostat.ilo.org/methods/concepts-and-definitions/description-industrial-relations-data/
Bulk download facility: https://ilostat.ilo.org/data/bulk/ (served via the
REST API at https://rplumber.ilo.org/__docs__/)

Each ILOSTAT indicator has an id (e.g. "STR_DWRK_ECO_NB_A"). Indicator ids
can change over time, so rather than hard-coding them this script:
  1. downloads the indicator table of contents,
  2. keyword-matches the industrial-disputes indicators (strikes/lockouts:
     number of cases, workers involved, days not worked, days-not-worked
     rate per 1000 workers),
  3. downloads the full data for each match into raw/,
  4. writes a manifest (raw/manifest.csv) recording which indicator id was
     matched to which concept.

Requires network access to ILOSTAT's servers (rplumber.ilo.org).
"""
from __future__ import annotations

import argparse
import csv
import io
import sys
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
RAW_DIR = HERE / "raw"

# ILOSTAT's current bulk-download facility is a REST API served from
# rplumber.ilo.org (the old static WEB_bulk_download file paths have been
# retired). See https://rplumber.ilo.org/__docs__/ for the full API.
TOC_URL = "https://rplumber.ilo.org/metadata/toc/indicator/"
DATA_URL = "https://rplumber.ilo.org/data/indicator/"

# Keyword rules used to pick out the three industrial-disputes indicators
# from the full ILOSTAT table of contents. Matched case-insensitively against
# the indicator label/name column.
CONCEPTS = {
    "n_strikes_lockouts": ["strikes and lockouts"],  # number of cases (further filtered below)
    "workers_involved": ["workers involved"],
    "days_not_worked": ["days not worked"],
    "days_not_worked_rate": ["days not worked", "per 1000"],
}

HEADERS = {"User-Agent": "Mozilla/5.0 (research data pull; contact via repo issues)"}
TIMEOUT = 60


def fetch(url: str, params: dict | None = None) -> requests.Response:
    resp = requests.get(url, params=params, headers=HEADERS, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp


def get_toc() -> list[dict]:
    params = {"lang": "en", "format": ".csv"}
    print(f"Fetching table of contents from {TOC_URL} ...")
    try:
        resp = fetch(TOC_URL, params=params)
    except requests.RequestException as exc:
        raise RuntimeError(f"Could not retrieve the ILOSTAT table of contents: {exc}")

    text = resp.content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)
    if not rows:
        preview = text[:300].replace("\n", " ")
        raise RuntimeError(
            "ILOSTAT table of contents came back empty. "
            f"Response preview: {preview!r}"
        )
    return rows


def label_column(toc_rows: list[dict]) -> str:
    for candidate in ("indicator.label", "indicator_label", "label", "name"):
        if candidate in toc_rows[0]:
            return candidate
    raise RuntimeError(f"Could not find a label column in TOC columns: {list(toc_rows[0])}")


def id_column(toc_rows: list[dict]) -> str:
    for candidate in ("id", "indicator", "indicator.id", "indicator_id"):
        if candidate in toc_rows[0]:
            return candidate
    raise RuntimeError(f"Could not find an id column in TOC columns: {list(toc_rows[0])}")


def match_indicators(toc_rows: list[dict]) -> dict[str, list[dict]]:
    lbl_col = label_column(toc_rows)
    matches: dict[str, list[dict]] = {k: [] for k in CONCEPTS}
    for row in toc_rows:
        label = (row.get(lbl_col) or "").lower()
        if "strikes and lockouts" not in label:
            continue
        if "days not worked" in label:
            if "per 1000" in label or "rate" in label:
                matches["days_not_worked_rate"].append(row)
            else:
                matches["days_not_worked"].append(row)
        elif "workers involved" in label:
            matches["workers_involved"].append(row)
        elif "number of strikes and lockouts" in label or label.startswith("strikes and lockouts"):
            matches["n_strikes_lockouts"].append(row)
        elif "strikes and lockouts" in label and "rate" not in label:
            # catch-all bucket for "Number of strikes and lockouts by ..." variants
            matches["n_strikes_lockouts"].append(row)
    return matches


def download_indicator(indicator_id: str, dest: Path) -> bool:
    params = {"id": indicator_id, "type": "label", "format": ".csv"}
    print(f"  downloading {indicator_id} ...")
    try:
        resp = fetch(DATA_URL, params=params)
        dest.write_bytes(resp.content)
        return True
    except (requests.RequestException, OSError) as exc:
        print(f"    failed: {exc}")
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--list-only",
        action="store_true",
        help="Only print matched indicators, do not download the data.",
    )
    args = parser.parse_args()

    RAW_DIR.mkdir(parents=True, exist_ok=True)

    try:
        toc_rows = get_toc()
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    id_col = id_column(toc_rows)
    matches = match_indicators(toc_rows)

    manifest_rows = []
    for concept, rows in matches.items():
        if not rows:
            print(f"WARNING: no ILOSTAT indicator matched concept '{concept}'")
        for row in rows:
            manifest_rows.append({"concept": concept, **row})

    if not manifest_rows:
        print("ERROR: no matching indicators found in the table of contents.", file=sys.stderr)
        return 1

    print(f"\nMatched {len(manifest_rows)} indicator(s):")
    for row in manifest_rows:
        print(f"  [{row['concept']}] {row[id_col]}: {row.get(label_column(toc_rows))}")

    if args.list_only:
        return 0

    ok = True
    for row in manifest_rows:
        indicator_id = row[id_col]
        dest = RAW_DIR / f"{indicator_id}.csv"
        if not download_indicator(indicator_id, dest):
            ok = False

    manifest_path = RAW_DIR / "manifest.csv"
    with manifest_path.open("w", newline="", encoding="utf-8") as f:
        fieldnames = list(manifest_rows[0].keys())
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(manifest_rows)
    print(f"\nWrote manifest to {manifest_path}")

    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
