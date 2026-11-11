# Phase 5 — out-of-time chase win probability

## What this adds

`scripts/build_win_probability.py` predicts the batting side's chance of winning **before each second-innings delivery** and measures the potential change from one legal ball. It writes a delivery-level diagnostic and compact backtest, calibration, model, and calibrator tables. It does **not** change the submitted pressure labels or player rankings. The data pack has no exact extras, and the model has no prior-season training set for 2022, so automatically replacing the current index would mix incompatible labels and overstate precision.

## Inputs and chronology

The model reads the Phase 2 pre-ball state, Phase 1 score-quality audit, and Phase 3 pre-match Elo proxy. It excludes the 13 matches with audited run-margin error above seven, six matches decided by a Super Over after a tied regulation chase, and the one eligible match without a valid listed winning team. It covers IPL and T20I chases in 2023–2026: **67,770 deliveries**. First innings and 2022 chases have no out-of-time win-probability score.

For each predicted year, a regularized logistic model is fitted on **earlier calendar years only**. Training samples one legal state every three legal balls and gives each match equal total weight. Features are approximate runs required relative to balls remaining, their interaction with innings stage, wickets lost, a prior-only batting-minus-bowling Elo difference, IPL/T20I, approximate target size, and knockout status. Every pre-ball feature is known before the evaluated delivery. The model predicts all chase deliveries in the later year. No same-day results enter the online correction until that date has finished.

A separate format-specific logistic calibration layer is fitted on at least 100 earlier **out-of-time** matches. A bounded season offset uses completed matches on earlier dates of the current season, with a 12-match shrinkage prior. Both adjustments are recorded in `win_probability_calibrators.csv` and `win_probability_delivery.csv`. No evaluated delivery's outcome enters its prediction.

## Backtest

Brier score and ten-bin calibration error (ECE) give each match equal weight by averaging its legal deliveries. Lower is better. Elo-only Brier uses the pre-match team rating without chase state; constant 0.5 has Brier 0.25.

| Year | Format | Matches | Model Brier | Elo-only Brier | ECE |
| ---: | --- | ---: | ---: | ---: | ---: |
| 2023 | T20I | 55 | 0.1409 | 0.2671 | 0.0861 |
| 2023 | IPL | 71 | 0.1812 | 0.2554 | 0.0432 |
| 2024 | T20I | 92 | 0.1627 | 0.2268 | 0.0630 |
| 2024 | IPL | 70 | 0.1422 | 0.2642 | 0.1038 |
| 2025 | T20I | 109 | 0.1198 | 0.2170 | 0.0867 |
| 2025 | IPL | 66 | 0.1389 | 0.2601 | 0.1223 |
| 2026 | T20I | 63 | 0.1411 | 0.2342 | 0.0516 |
| 2026 | IPL | 70 | 0.1187 | 0.2451 | 0.1109 |

The chase-state model beats Elo alone in every held-out year/format cell. Calibration remains uneven: IPL 2024–2026 ECE is above 0.10. This is meaningful probability error, particularly for claiming that a small predicted swing is decisive.

## Potential one-ball leverage

For each pre-ball state, the model simulates the next legal ball as 0, 4, or 6 runs, or a scoreless wicket, and records the range of resulting win probabilities. It uses terminal probabilities of 1 after the approximate target is reached and 0 after balls or wickets are exhausted. This is a **potential six-run swing**, not the expected value of a real delivery or a player's contribution. An exploratory `0.08` cutoff flags a potentially high-leverage ball; it is close to the 2023 held-out 80th-percentile values and is held fixed for 2024–2026.

Across the held-out legal deliveries, **14,590** meet the 0.08 cutoff. **6,441** of those (44.1%) are low pressure under the original rule, mostly in overs 7–15. That disagreement is useful: the phase-based rule can overlook a contestable middle-overs chase. The cutoff is a diagnostic comparison, not a revised scoring tier.

The score-quality constraint is severe. Shifting approximate runs required by seven—the observed 95th-percentile run-margin reconstruction error—changes the predicted win probability by a median **0.164** among flagged high-leverage deliveries (including illegal deliveries in this median). The shift is larger than the 0.08 leverage threshold. The seven-run figure is an empirical sensitivity check, not a guaranteed bound for every chase. Without exact extras, these flags cannot safely replace the submission's pressure index. The delivery table exposes both `win_probability_shift_7_runs` and the original rule tier for further review.

## Promotion gate and reproducibility

Keep the current ranked selections until exact chase scores can be verified or the probability model has acceptably stable calibration across seasons and formats. A proposed gate for a replacement is ECE at most 0.08 in every held-out year/format cell, Brier better than Elo-only, and leverage-tier stability under the empirical score perturbation. The current model passes the Brier condition but fails the calibration and score-stability conditions.

Run `scripts/run_pipeline.py`; Phase 5 runs after team context and before the player score. `scripts/validate_pipeline.py` checks key uniqueness, bounds, the fixed leverage flag, and that each prediction was trained on earlier years. The delivery-level file is ignored by Git; the compact summaries are versioned.
