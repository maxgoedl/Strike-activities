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
- **Days not worked due to strikes and lockouts per 1000 workers** — the
  rate ILOSTAT itself recommends for cross-country comparison, since it
  normalizes for the size of each country's employed population.

## How to run

```bash
pip install requests
python3 fetch_ilostat_irdata.py      # discovers indicator ids from the ILOSTAT
                                      # table of contents and downloads the
                                      # raw bulk CSVs into raw/
python3 build_panel.py               # reshapes raw/*.csv into one tidy
                                      # country-year file in processed/
python3 summarize_panel.py           # prints descriptive stats, coverage,
                                      # correlations and outliers; also
                                      # writes processed/summary_report.txt
python3 plot_strikes_timeseries.py   # plots number of strikes/lockouts over
                                      # time for a set of countries (default:
                                      # Germany, France, UK, US) into
                                      # processed/strikes_timeseries_*.png
```

`plot_strikes_timeseries.py --countries "Germany" "Japan"` plots any other
countries by their ILOSTAT `ref_area` name (check `processed/industrial_disputes_panel.csv`
for exact spellings, e.g. "United States of America", "United Kingdom of
Great Britain and Northern Ireland"). Requires `matplotlib` in addition to
`requests` (see `requirements.txt`).

`fetch_ilostat_irdata.py --list-only` prints the matched indicators without
downloading anything, which is useful for sanity-checking that ILOSTAT hasn't
renamed/restructured the tables before pulling the full data.

Data comes from ILOSTAT's REST API at `rplumber.ilo.org` (the API behind
<https://ilostat.ilo.org/data/bulk/>; see <https://rplumber.ilo.org/__docs__/>
for the full docs), not the old static bulk-download files.

Output:
- `raw/<indicator_id>.csv` — one file per matched ILOSTAT indicator, in
  ILOSTAT's native long format (`ref_area`, `indicator`, `sex`, `classif1`,
  `classif2`, `time`, `obs_value`, ...).
- `raw/manifest.csv` — records which ILOSTAT indicator id was matched to
  which concept (number of disputes / workers involved / days not worked /
  days-not-worked rate), so the mapping is auditable if ILOSTAT changes
  indicator codes later.
- `processed/industrial_disputes_panel.csv` — tidy panel with one row per
  `ref_area` (country) x `time` (year) and one column per concept.

## Known limitation: this environment's network access

This repository was scaffolded from a sandboxed session whose outbound
network policy blocks all `ilo.org` subdomains (`ilostat.ilo.org`,
`www.ilo.org`, `rplumber.ilo.org` all return `403` at the egress proxy).
As a result `fetch_ilostat_irdata.py` could not be run to completion there,
and `raw/`/`processed/` in that environment stayed empty — but the script's
requests are correctly formed and work from a normal internet connection
(e.g. a personal computer), which is how this was actually run and verified.

## Notes on indicator discovery

Indicator ids on ILOSTAT's bulk download facility can change over time, so
rather than hard-coding ids, `fetch_ilostat_irdata.py` downloads ILOSTAT's
table of contents (`GET rplumber.ilo.org/metadata/toc/indicator/`) and
keyword-matches the industrial-disputes tables by their label text. If
ILOSTAT relabels these indicators, update the keyword rules in
`CONCEPTS`/`match_indicators()` in `fetch_ilostat_irdata.py`.
