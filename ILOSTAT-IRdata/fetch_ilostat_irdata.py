#!/usr/bin/env python3
"""
Download ILOSTAT Industrial Relations data (IRdata) on industrial disputes:
number of strikes/lockouts, workers involved, and days not worked.

Source: https://ilostat.ilo.org/methods/concepts-and-definitions/description-industrial-relations-data/
Bulk download facility: https://ilostat.ilo.org/data/bulk/

ILOSTAT publishes each indicator as a gzipped CSV keyed by an indicator id
(e.g. "STR_DYNE_ECO_NB_A"). Indicator ids can change over time, so rather than
hard-coding them this script:
  1. downloads the indicator table of contents,
  2. keyword-matches the industrial-disputes indicators (strikes/lockouts:
     number of cases, workers involved, days not worked),
  3. downloads the raw bulk CSV for each match into raw/,
  4. writes a manifest (raw/manifest.csv) recording which indicator id was
     matched to which concept.

Requires network access to ILOSTAT's servers (ilostat.ilo.org / rplumber.ilo.org).
"""
from __future__ import annotations

import argparse
import csv
import gzip
import io
import sys
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
RAW_DIR = HERE / "raw"

# ILOSTAT has served its bulk download facility from more than one host over
# time; try each until one works.
TOC_URL_CANDIDATES = [
    "https://rplumber.ilo.org/files/indicator/table_of_contents_en.csv",
    "https://www.ilo.org/ilostat-files/WEB_bulk_download/indicator/table_of_contents_en.csv",
]
CSV_BASE_CANDIDATES = [
    "https://rplumber.ilo.org/files/indicator/{id}.csv.gz",
    "https://www.ilo.org/ilostat-files/WEB_bulk_download/indicator/{id}.csv.gz",
]

# Keyword rules used to pick out the three industrial-disputes indicators
# from the full ILOSTAT table of contents. Matched case-insensitively against
# the indicator label/name column.
CONCEPTS = {
    "n_strikes_lockouts": ["strikes and lockouts"],  # number of cases (further filtered below)
    "workers_involved": ["workers involved"],
    "days_not_worked": ["days not worked"],
}

HEADERS = {"User-Agent": "Mozilla/5.0 (research data pull; contact via repo issues)"}
TIMEOUT = 60


def fetch(url: str) -> requests.Response:
    resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp


def get_toc() -> list[dict]:
    last_err = None
    for url in TOC_URL_CANDIDATES:
        try:
            print(f"Fetching table of contents from {url} ...")
            resp = fetch(url)
            text = resp.content.decode("utf-8-sig")
            reader = csv.DictReader(io.StringIO(text))
            rows = list(reader)
            if rows:
                return rows
        except requests.RequestException as exc:
            print(f"  failed: {exc}")
            last_err = exc
    raise RuntimeError(
        "Could not retrieve the ILOSTAT table of contents from any known URL. "
        f"Last error: {last_err}"
    )


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
    for base in CSV_BASE_CANDIDATES:
        url = base.format(id=indicator_id)
        try:
            print(f"  downloading {indicator_id} from {url} ...")
            resp = fetch(url)
            data = gzip.decompress(resp.content) if url.endswith(".gz") else resp.content
            dest.write_bytes(data)
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
