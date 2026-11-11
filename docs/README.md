# Analysis phases

Run the complete reproducible pipeline from the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe scripts\run_pipeline.py
```

The pipeline uses only Python's standard library and writes linked outputs under `data/processed/`. The large delivery-level intermediates remain local and are ignored by Git; compact audit tables, player scores, and rankings are versioned. The raw data pack and `.venv` are also ignored.

1. [Phase 1: match state and score audit](PHASE_1_MATCH_STATE.md)
2. [Phase 2: pressure labels](PHASE_2_PRESSURE.md)
3. [Phase 3: team and venue context](PHASE_3_CONTEXT.md)
4. [Phase 4: player scoring and rankings](PHASE_4_RANKINGS.md)

The [submission methodology report](SUBMISSION_REPORT.md) contains the recommended ordered selections, their evidence, and the additional eligibility and wicket-value robustness checks. `scripts/check_robustness.py` writes `ranking_robustness.csv` and is included in the complete pipeline.

To regenerate the uploadable PDF after running the pipeline:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-report.txt
.\.venv\Scripts\python.exe scripts\render_submission_report.py
```

The renderer checks that all 20 names, ranks, and conservative scores in the report agree with `rankings.csv` before writing `output/pdf/superr_selector_methodology.pdf`.

The [overall plan](../PRESSURE_RANKINGS_PLAN.md) records the intended methodology. The [processed-data dictionary](../data/processed/README.md) explains the file grains and base metrics.
