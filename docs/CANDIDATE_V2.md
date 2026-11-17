# Pressure-aware candidate v2

**Component status:** The v2 method improves match-state comparison and broadens pressure coverage, but its standalone top 10 does not win every chronological check. The [final report](FINAL_SUBMISSION_REPORT.md) combines it with the original method. `candidate_v2_rankings.csv` remains a component list; `final_rankings.csv` is the dropdown order.

Run `scripts/build_candidate_v2.py` after the normal context and exact-score audit. The complete `scripts/run_pipeline.py` now includes it. `scripts/audit_pressure_rule.py` repeats the exact-score leverage comparison.

## Changes from the current method

1. For the **526 delivery-verified games**, use Cricsheet's exact first-innings total and cumulative extras to calculate the pre-ball chase requirement. For the other games, use the supplied pack's approximate requirement and skip a chase delivery if moving that requirement by seven runs changes its v2 pressure tier. Thirteen games with poor approximate-margin reconstruction are omitted unless their exact deliveries were verified.
2. Keep the original phase, wicket, and knockout points; add 15 points for two or more wickets lost in the powerplay, and raise chase points in still-contestable middle-over chases. A 0.8-1.6 required runs-per-ball chase gets 26/28/22 points with more than 60 / 37-60 / at most 36 balls left. A 1.6-2.3 chase gets 13/19/22. An easier chase gets zero; a requirement above 2.3 gets 7 or 15. The existing eight-point late-wicket add-on remains. Scores below 30 are low, 30-49 medium, and at least 50 high. Medium deliveries count at half weight.
3. Before each date, estimate the average composite batting or bowling residual in earlier matching states. The hierarchy pools role/format/phase/innings toward zero with 1,000 balls, pressure tier toward that mean with 400, and a wicket/required-rate/balls-left cell toward the tier with 150. Subtract this **prior-only** state correction from each observed residual. Today's outcomes update the history only after all of today's predictions.
4. Rank by pressure impact per 100 effective balls, shrunk with `balls / (balls + 80)`, then average the point estimate with its 10th percentile from 300 match bootstrap draws. The low-pressure rate and pressure uplift are shown separately. The gate remains 100 effective pressure balls in 20 matches and 50 low-pressure balls.

## What improved

| Check | Current candidate | V2 candidate |
| --- | ---: | ---: |
| High-pressure powerplay deliveries | 0 after original scoring exclusions | 80 |
| Medium-pressure powerplay deliveries | 1 | 4,341 |
| Medium-pressure middle-over deliveries | 8,174 | 28,746 |
| High-pressure middle-over deliveries | 1,045 | 2,572 |

For the deliveries v2 labels high-pressure death overs, the ball-weighted mean absolute residual across year/format/role cells falls from **21.58 before its state correction to 6.19 runs per 100 balls after**. This is a calibration check on the v2 state definition, not a direct player-ranking win.

On the matched exact-score chase diagnostic, the pressure score's ability to order model-flagged high-leverage deliveries, measured by AUC, is **0.844 current versus 0.836 v2** in 2023-2024 and **0.730 versus 0.756** in 2025-2026. In the top quarter of pressure-score deliveries, high-leverage recall is **0.580 versus 0.595** in the earlier years and **0.416 versus 0.460** in the later years. This is supporting evidence, not a ground-truth pressure label: the exact-score win-probability model misses its calibration gate in six of eight year/format cells. The v2 rule was designed after reviewing the current rule's missed middle-over cases, so the later comparison is not a pristine untouched test.

## What did not improve consistently

`candidate_v2_backtest.csv` trains **conservative bootstrap scores** through 2023, 2024, or 2025 and evaluates players in the next year. The relaxed common gate requires at least 40 training effective pressure balls in eight matches and 20 low balls **under both methods**, plus 15 v2 pressure balls in four later matches. Its future target is the v2 state-adjusted pressure impact. The three relaxed tests involve 42/59/58 batters and 58/77/73 bowlers. Two further tests use the final 100/20/50 gate. All cohorts are survival-selected: players without later exposure cannot be evaluated.

| Role | Method | Mean rank correlation with later impact | Mean later impact of training top 10 | Mean later positive-match share of training top 10 |
| --- | --- | ---: | ---: | ---: |
| Batting | Current score | 0.165 | +19.403 | 0.501 |
| Batting | V2 pressure score | 0.192 | +19.966 | 0.497 |
| Batting | Equal-rank consensus | 0.179 | +22.206 | 0.509 |
| Bowling | Current score | 0.077 | +3.781 | 0.540 |
| Bowling | V2 pressure score | 0.042 | +7.068 | 0.582 |
| Bowling | Equal-rank consensus | 0.063 | +8.984 | 0.567 |

The consensus has a better mean top-10 impact on the relaxed folds but does not dominate every year. With the stricter final gate, consensus batting has the best top-10 impact in both 2025 and 2026; bowling remains mixed. A third rank based on positive-match share did not consistently improve top-10 impact. These rules were inspected on the same years, so the final consensus is the **best supported compromise in this pack**, not an untouched-test winner.

## Ordered candidate lists

**Batters:** Suryakumar Yadav, Rinku Singh, Tim David, Shreyas Iyer, Naman Dhir, Jos Buttler, Shashank Singh, Dinesh Karthik, Heinrich Klaasen, Sikandar Raza.

**Bowlers:** Sunil Narine, Jasprit Bumrah, Abrar Ahmed, Lungi Ngidi, Mohammad Nawaz, Rashid Khan, Tim Southee, Mitchell Santner, Matheesha Pathirana, Varun Chakravarthy.

The v2 batting list retains **5 of 10** names from the earlier component PDF; the bowling list retains **8 of 10**. The full scores, exposure, bootstrap ranges, and positive-match shares are in `data/processed/candidate_v2_rankings.csv`. The calibration, pressure coverage, and fold-level audit tables sit beside it. These names are **not** the final dropdown order.

## Remaining methodological choice

The jointly eligible equal-rank consensus is documented in [the final report](FINAL_SUBMISSION_REPORT.md). A larger independent season or an external validated leverage label would strengthen future revisions. The final report discloses the mixed bowling backtest and the fact that the method choice was inspected on these same folds.
