# Verified Cricsheet extras cache

`cricsheet_extras.csv.gz` is a compact, transformed subset of [Cricsheet](https://cricsheet.org/) match data, downloaded from its [IPL JSON archive](https://cricsheet.org/downloads/ipl_json.zip) and [men's T20I JSON archive](https://cricsheet.org/downloads/t20s_male_json.zip) on 12 November 2026. Cricsheet supplies each delivery's batter runs, extras runs, and total runs in its [JSON format](https://cricsheet.org/format/json/). The archive's original ODC Attribution License is preserved in `CRICSHEET_LICENSE.txt`; [Cricsheet's licensing page](https://cricsheet.org/licensing/) explains attribution requirements. Credit: Cricsheet, https://cricsheet.org/. This derivative contains only the match ID mapping and extras runs needed to audit the supplied pack.

`scripts/import_cricsheet_extras.py` matches a game by date (allowing a one-day time-zone difference) and both team names. It then requires both innings to agree on delivery count, batter runs, legal-ball status, and wicket occurrence **for every delivery**. The importer also checks every matched run-margin result against the exact innings totals. Any ambiguous or conflicting game is excluded from the cache. Its match-level audit is `data/processed/exact_score_coverage.csv`.

The two original archives are intentionally not included here. To rebuild the cache from freshly downloaded archives:

```powershell
.\.venv\Scripts\python.exe scripts\import_cricsheet_extras.py --ipl-zip path\to\ipl_json.zip --t20i-zip path\to\t20s_male_json.zip
```

The committed cache makes `scripts/run_pipeline.py` reproduce the exact-score chase diagnostic without a network request. Archive updates may change match coverage; inspect the audit and rerun validation before replacing this pinned cache.
