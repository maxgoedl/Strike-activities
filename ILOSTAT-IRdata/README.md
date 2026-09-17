# ILOSTAT Industrial Relations Data (IRdata) — Industrial Disputes

Data pull for a cross-country panel on industrial disputes, based on ILOSTAT's
Industrial Relations Data (IRdata) collection:
<https://ilostat.ilo.org/methods/concepts-and-definitions/description-industrial-relations-data/>

## Indicators covered

ILOSTAT's strikes-and-lockouts tables (annual, by economic activity), from
which this pull uses the aggregate ("total") rows:

- **Number of strikes and lockouts** — count of disputes (the basic unit of
  measurement is the case of dispute).
- **Workers involved in strikes and lockouts** (thousands) — the maximum
  number of workers who took part at any point during the stoppage.
- **Days not worked due to strikes and lockouts** — total working days lost.

## How to run

```bash
pip install requests
python3 fetch_ilostat_irdata.py      # discovers indicator ids from the ILOSTAT
                                      # table of contents and downloads the
                                      # raw bulk CSVs into raw/
python3 build_panel.py               # reshapes raw/*.csv into one tidy
                                      # country-year file in processed/
```

`fetch_ilostat_irdata.py --list-only` prints the matched indicators without
downloading anything, which is useful for sanity-checking that ILOSTAT hasn't
renamed/restructured the tables before pulling the full data.

Output:
- `raw/<indicator_id>.csv` — one file per matched ILOSTAT indicator, in
  ILOSTAT's native long format (`ref_area`, `indicator`, `sex`, `classif1`,
  `classif2`, `time`, `obs_value`, ...).
- `raw/manifest.csv` — records which ILOSTAT indicator id was matched to
  which concept (number of disputes / workers involved / days not worked),
  so the mapping is auditable if ILOSTAT changes indicator codes later.
- `processed/industrial_disputes_panel.csv` — tidy panel with one row per
  `ref_area` (country) x `time` (year) and one column per concept.

## Known limitation: this environment's network access

This repository was scaffolded from a sandboxed session whose outbound
network policy blocks all `ilo.org` subdomains (`ilostat.ilo.org`,
`www.ilo.org`, `rplumber.ilo.org` all return `403` at the egress proxy).
As a result, `fetch_ilostat_irdata.py` could not actually be run to
completion here, and `raw/` and `processed/` are empty. The script itself
was tested up to the point of the network call and fails cleanly with a
clear error when the ILOSTAT hosts are unreachable.

**To actually populate this dataset, run the two scripts above from a
machine/environment that can reach ilostat.ilo.org / rplumber.ilo.org /
ilo.org** (e.g. your own laptop, or a Claude Code environment configured
with a less restrictive egress policy).

## Notes on indicator discovery

Indicator ids on ILOSTAT's bulk download facility
(<https://ilostat.ilo.org/data/bulk/>) can change over time, so rather than
hard-coding ids, `fetch_ilostat_irdata.py` downloads ILOSTAT's table of
contents and keyword-matches the industrial-disputes tables by their label
text. If ILOSTAT relabels these indicators, update the keyword rules in
`CONCEPTS`/`match_indicators()` in `fetch_ilostat_irdata.py`.
