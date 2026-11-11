# Phase 4 — player scoring, reliability, and provisional rankings

## Purpose and inputs

`scripts/score_players.py` consumes Phase 3's `delivery_context.csv` and Phase 1's `match_quality.csv`. It produces `player_pressure_summary.csv`, `player_pressure_segments.csv`, `rankings.csv`, and `ranking_sensitivity.csv`. These are **provisional analytical rankings**, not submitted Unstop selections.

Before scoring, it skips the 4,776 chase deliveries whose pressure tier changes under the ±7-run score check. It also skips every delivery from the 13 run-margin matches with reconstruction error above 7. The underlying audit and context files retain those records.

## Delivery value and match weight

For a batter on a ball faced:

`bat_value = batter_runs - expected_batter_runs - 5 × (striker_out - expected_striker_out_probability)`

For a bowler on a delivery:

`bowl_value = expected_bowler_cost - (batter_runs + one_minimum_run_for_wide_or_no_ball) + 5 × (credited_wicket - expected_bowler_wicket_probability)`

The wicket value of **5 runs** is a provisional conversion used equally for credited wicket modes. A striker run-out counts in the batter's dismissal value but never as a bowler wicket. Non-striker dismissals are not charged to the striker. Exact extras are absent, so the bowling cost is a lower-bound proxy and not exact economy.

High-pressure deliveries have weight **1**, medium **0.5**, and low **0** for the pressure numerator. Low-pressure balls form the player's usual-performance baseline. A top-versus-bottom mismatch multiplies a delivery's value by **0.75**, while exposure denominators remain undiscounted; this actually reduces its points. A bowler's illegal deliveries contribute their cost or wicket value but do not add legal-ball exposure.

For each player, calculate pressure value per 100 effective balls and low-pressure value per 100 balls. Shrink the difference toward the player's low-pressure baseline with factor `pressure_effective_balls / (pressure_effective_balls + 80)`. The displayed point estimate is `0.65 × shrunk_pressure_rate + 0.35 × shrunk_pressure_uplift`. This rewards good pressure performance while retaining the comparison with usual performance.

## Eligibility and reliability

A player needs **40 effective pressure balls**, pressure in **8 matches**, and **30 low-pressure balls** to qualify. There are **130 eligible batters** and **172 eligible bowlers** after the score-quality exclusions. This gate ensures at least modest exposure; it does not make every eligible player's estimate equally reliable. The 40/8/30 choice should be compared with stricter 60/10/50 and 100/15/50 gates before external submission, especially for the lower-ranked selections.

The script resamples **whole matches** 300 times per eligible player, calculates a 10th and 90th percentile score, and ranks by the midpoint of the point estimate and its 10th-percentile bootstrap value. This is a conservative ranking rule, though the order of close players remains uncertain. `player_pressure_summary.csv` also reports share of pressure matches with positive contribution, largest positive match's share, pace/spin or RHB/LHB splits, and bowler dismissal modes.

`player_pressure_segments.csv` repeats the pressure-versus-usual comparison within IPL/T20I and each series. Series cells are descriptive because most series are short; they are not separately eligible rankings. The overall score is calculated from all qualifying deliveries, not by averaging the series scores.
The format split reveals material variation: Shreyas Iyer has 121.5 effective IPL pressure balls with a segment point estimate of 55.807, versus 44.5 T20I balls and 5.993. Tim David's two segment estimates are much closer (29.424 IPL and 30.217 T20I). The overall ranking does not require equal performance in both formats; review this distinction when choosing a final definition of “reliable.”

## Provisional top 10 batters

| Rank | Batter | Conservative score | Effective pressure balls | Pressure matches | Bootstrap 10th to 90th |
| ---: | --- | ---: | ---: | ---: | ---: |
| 1 | Shreyas Iyer | 37.391 | 166.0 | 29 | 28.195 to 64.073 |
| 2 | Rinku Singh | 28.283 | 369.5 | 57 | 20.935 to 48.860 |
| 3 | Virat Kohli | 23.959 | 110.0 | 21 | 17.679 to 44.804 |
| 4 | Tristan Stubbs | 23.607 | 229.5 | 42 | 16.309 to 43.999 |
| 5 | Naman Dhir | 22.638 | 141.5 | 21 | 12.303 to 47.677 |
| 6 | Babar Azam | 22.220 | 63.0 | 10 | 15.968 to 38.870 |
| 7 | Tim David | 21.376 | 377.0 | 66 | 14.665 to 43.327 |
| 8 | Suryakumar Yadav | 21.160 | 212.5 | 43 | 13.982 to 42.442 |
| 9 | Ashutosh Sharma | 20.732 | 191.0 | 24 | 11.933 to 45.497 |
| 10 | Glenn Phillips | 20.673 | 124.0 | 24 | 13.246 to 40.760 |

## Provisional top 10 bowlers

| Rank | Bowler | Conservative score | Effective pressure balls | Pressure matches | Bootstrap 10th to 90th |
| ---: | --- | ---: | ---: | ---: | ---: |
| 1 | Sunil Narine | 34.754 | 180.0 | 39 | 29.542 to 50.106 |
| 2 | Abrar Ahmed | 28.218 | 148.0 | 23 | 21.648 to 45.932 |
| 3 | Tim Southee | 27.631 | 196.0 | 30 | 21.837 to 46.288 |
| 4 | Mark Wood | 26.895 | 70.0 | 11 | 18.553 to 49.972 |
| 5 | Jasprit Bumrah | 25.780 | 368.5 | 59 | 18.162 to 47.427 |
| 6 | Lungi Ngidi | 25.774 | 141.0 | 28 | 18.765 to 46.399 |
| 7 | Mohammad Nawaz | 25.143 | 87.5 | 17 | 18.584 to 46.213 |
| 8 | Varun Chakravarthy | 23.554 | 293.0 | 62 | 16.764 to 43.709 |
| 9 | Rashid Khan | 21.241 | 474.0 | 88 | 14.422 to 40.888 |
| 10 | Matheesha Pathirana | 20.988 | 328.5 | 39 | 13.350 to 42.624 |

Scores are in a *model-adjusted runs-per-100-ball index*, not observed cricket runs or ICC rating points. Effective pressure balls weight medium balls by 0.5. Bootstrap intervals overlap widely, so adjacent ranks should not be read as decisive head-to-head differences. Babar Azam and Mark Wood pass the gate but have relatively small pressure samples.

## Sensitivity result

`ranking_sensitivity.csv` tests high-pressure cutoffs **45, 50, 55** and mismatch weights **0.60, 0.75, 0.90**. It compares **point-estimate** top tens with the main point-estimate top tens, keeping the comparison method the same. At cutoff 50, weight 0.60 preserves 10/10 names for both roles; weight 0.90 preserves 8/10 batters and 9/10 bowlers. At cutoff 45, batting preserves 7/10 and bowling 9/10. At cutoff 55, batting preserves only 4–5/10 and bowling 8/10. The separate conservative bootstrap ranking overlaps the main point-estimate top ten by **8/10 batters** and **9/10 bowlers**.

The batting boundary is therefore **materially sensitive** to the pressure definition. These rankings are useful as a first result and for investigation, but should not be copied into the final submission without reviewing the alternative candidates and the score reconstruction limitation. The wicket conversion (5 runs) and minimum-sample gates also deserve a sensitivity run.

## Additional robustness checks

`scripts/check_robustness.py` reruns the **same conservative bootstrap ranking rule** with eligibility gates of 60 effective pressure balls / 10 pressure matches / 50 low balls and 100 / 15 / 50. It also changes the wicket-run conversion from 5 to 3 or 7, holding the baseline gate fixed. `ranking_robustness.csv` holds the top 20 for each scenario, and the script asserts that its baseline order exactly matches `rankings.csv`.

| Scenario | Eligible batters | Eligible bowlers | Baseline batting top 10 retained | Baseline bowling top 10 retained |
| --- | ---: | ---: | ---: | ---: |
| Baseline 40 / 8 / 30, wicket value 5 | 130 | 172 | 10 | 10 |
| Gate 60 / 10 / 50 | 91 | 140 | 9 | 10 |
| Gate 100 / 15 / 50 | 65 | 91 | 8 | 8 |
| Wicket value 3 | 130 | 172 | 8 | 9 |
| Wicket value 7 | 130 | 172 | 9 | 9 |

The [submission methodology report](SUBMISSION_REPORT.md) interprets these checks alongside the pressure-cutoff and mismatch sensitivity. The lower batting ranks remain sensitive, so all ordered selections should carry the stated uncertainty and score-reconstruction caveat.
