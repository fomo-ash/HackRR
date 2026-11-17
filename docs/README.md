# Analysis phases

**Final submission:** Use the ordered selections in [the final methodology report](FINAL_SUBMISSION_REPORT.md), [the final ranking CSV](../data/processed/final_rankings.csv), and [the upload PDF](../output/pdf/superr_selector_final_methodology.pdf). The earlier [submission report](SUBMISSION_REPORT.md) and [candidate v2](CANDIDATE_V2.md) document component methods; neither has the final dropdown order.

The public [Pressure Room dashboard](https://ashutosh-superr-pressure-room-2026.linedhotel1.chatgpt.site) presents the final twenty, interactive comparisons, and player-level selection reasoning. [The video script](VIDEO_SCRIPT.md) explains the method for a spoken presentation. The dashboard contains only final rankings and aggregate evidence, not the supplied data pack.

Run the complete reproducible pipeline from the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe scripts\run_pipeline.py
```

The pipeline uses only Python's standard library and writes linked outputs under `data/processed/`. The large delivery-level intermediates remain local and are ignored by Git; compact audit tables, player scores, and rankings are versioned. The raw data pack and `.venv` are also ignored. The verified-score diagnostic uses the committed, attributed [Cricsheet extras cache](../data/external/README.md); the original archives are not needed for a normal rebuild.

1. [Phase 1: match state and score audit](PHASE_1_MATCH_STATE.md)
2. [Phase 2: pressure labels](PHASE_2_PRESSURE.md)
3. [Phase 3: team and venue context](PHASE_3_CONTEXT.md)
4. [Phase 4: player scoring and rankings](PHASE_4_RANKINGS.md)
5. [Phase 5: out-of-time chase win probability](PHASE_5_WIN_PROBABILITY.md)
6. [Phase 6: phase and country context profiles](PHASE_6_CONTEXT_PROFILES.md)
7. [Phase 7: elite-opponent tenure and phase matchups](PHASE_7_ELITE_TENURE.md)

The earlier [component methodology report](SUBMISSION_REPORT.md) contains its ordered selections and eligibility and wicket-value robustness checks. `scripts/check_robustness.py` writes `ranking_robustness.csv` and is included in the complete pipeline.

The [final report](FINAL_SUBMISSION_REPORT.md) compiles the jointly eligible consensus. `scripts/compile_final_rankings.py` and `scripts/compile_final_report.py` are included in the complete pipeline. `output/final_dropdown_order.txt` gives the 20 selections in copyable order.

To regenerate the uploadable PDF after running the pipeline:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-report.txt
.\.venv\Scripts\python.exe scripts\render_submission_report.py --final
```

The final renderer checks all 20 names, ranks, and rank sums against `final_rankings.csv` before writing `output/pdf/superr_selector_final_methodology.pdf`.

The [overall plan](../PRESSURE_RANKINGS_PLAN.md) records the intended methodology. The [processed-data dictionary](../data/processed/README.md) explains the file grains and base metrics.
