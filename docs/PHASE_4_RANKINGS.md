# Phase 4 — player scoring, reliability, and ordered rankings

## Scoring and exclusions

`scripts/score_players.py` consumes Phase 3's `delivery_context.csv` and Phase 1's `match_quality.csv`. It skips 4,776 chase deliveries whose pressure tier changes under a ±7-run score check and every delivery from the 13 audited run-margin matches with reconstruction error above seven. The underlying files retain those records for audit.

For a batter on a faced ball, `value = batter runs - expected batter runs - 5 × (striker out - expected striker-out probability)`. For a bowler on a delivery, `value = expected minimum bowling cost - observed minimum cost + 5 × (credited wicket - expected bowler-wicket probability)`. The wicket conversion is provisional and is tested below. The bowling cost includes batter runs and a minimum of one for a wide or no-ball; exact extras and economy are unavailable. Run-outs are never bowler wickets.

High-pressure deliveries have weight 1, medium 0.5, and low 0 for the pressure numerator. Low-pressure balls form each player's usual-performance baseline. The predefined top-versus-bottom match discount multiplies a delivery's value by 0.75; raw exposure denominators are unchanged. A bowler's illegal deliveries contribute value but no legal-ball exposure.

The pressure rate and low-pressure rate are both expressed per 100 balls. The pressure difference is shrunk by `pressure effective balls / (pressure effective balls + 80)`. The point score is `0.65 × shrunk pressure rate + 0.35 × shrunk pressure uplift`. Three hundred whole-match bootstrap draws give the 10th and 90th score percentiles. The **conservative score**, used for ordering, is the mean of the point score and its bootstrap 10th percentile.

## Eligibility

The primary gate requires **100 effective pressure balls, pressure exposure in at least 20 matches, and 50 low-pressure balls**. There are **59 eligible batters and 83 eligible bowlers**. The 20-match floor was chosen to keep short exceptional samples such as Babar Azam's 10 pressure matches or Mark Wood's 11 out of a reliability ranking. Ashutosh Sharma has 24 pressure matches but only 36 low-pressure balls, so his usual-performance comparison is too thin for this gate. The thresholds are tested against relaxed, stricter, and legacy alternatives in `ranking_robustness.csv`.

## Ordered batters

| Rank | Player | Conservative score | Effective pressure balls | Pressure matches | Bootstrap 10th–90th |
| ---: | --- | ---: | ---: | ---: | ---: |
| 1 | Shreyas Iyer | 37.391 | 166.0 | 29 | 28.195–64.073 |
| 2 | Rinku Singh | 28.283 | 369.5 | 57 | 20.935–48.860 |
| 3 | Virat Kohli | 23.959 | 110.0 | 21 | 17.679–44.804 |
| 4 | Tristan Stubbs | 23.607 | 229.5 | 42 | 16.309–43.999 |
| 5 | Naman Dhir | 22.638 | 141.5 | 21 | 12.303–47.677 |
| 6 | Tim David | 21.376 | 377.0 | 66 | 14.665–43.327 |
| 7 | Suryakumar Yadav | 21.160 | 212.5 | 43 | 13.982–42.442 |
| 8 | Glenn Phillips | 20.673 | 124.0 | 24 | 13.246–40.760 |
| 9 | Rovman Powell | 18.557 | 386.5 | 58 | 11.126–39.362 |
| 10 | David Miller | 17.650 | 326.5 | 58 | 11.020–35.421 |

## Ordered bowlers

| Rank | Player | Conservative score | Effective pressure balls | Pressure matches | Bootstrap 10th–90th |
| ---: | --- | ---: | ---: | ---: | ---: |
| 1 | Sunil Narine | 34.754 | 180.0 | 39 | 29.542–50.106 |
| 2 | Abrar Ahmed | 28.218 | 148.0 | 23 | 21.648–45.932 |
| 3 | Tim Southee | 27.631 | 196.0 | 30 | 21.837–46.288 |
| 4 | Jasprit Bumrah | 25.780 | 368.5 | 59 | 18.162–47.427 |
| 5 | Lungi Ngidi | 25.774 | 141.0 | 28 | 18.765–46.399 |
| 6 | Varun Chakravarthy | 23.554 | 293.0 | 62 | 16.764–43.709 |
| 7 | Rashid Khan | 21.241 | 474.0 | 88 | 14.422–40.888 |
| 8 | Matheesha Pathirana | 20.988 | 328.5 | 39 | 13.350–42.624 |
| 9 | Shaheen Afridi | 18.663 | 226.5 | 35 | 12.753–36.220 |
| 10 | Mitchell Starc | 17.241 | 130.0 | 27 | 4.944–55.555 |

Scores are model-adjusted runs per 100 balls, not observed cricket runs or ICC rating points. Effective pressure balls count medium balls at half weight. Adjacent bootstrap ranges overlap widely, so close head-to-head ranks should not be treated as decisive. Mitchell Starc's broad bootstrap range flags substantial uncertainty despite clearing the match gate.

## Sensitivity

`ranking_robustness.csv` reruns the same conservative bootstrap rule under alternative exposure gates and wicket values. Its baseline order is asserted to match `rankings.csv` exactly.

| Scenario | Eligible batters | Eligible bowlers | Baseline batting top 10 retained | Baseline bowling top 10 retained |
| --- | ---: | ---: | ---: | ---: |
| Primary 100 / 20 / 50, wicket value 5 | 59 | 83 | 10 | 10 |
| Legacy 40 / 8 / 30 | 130 | 172 | 8 | 8 |
| Relaxed 80 / 20 / 50 | 64 | 88 | 9 | 10 |
| Stricter 120 / 30 / 60 | 36 | 53 | 6 | 7 |
| Wicket value 3 | 59 | 83 | 9 | 9 |
| Wicket value 7 | 59 | 83 | 10 | 10 |

`ranking_sensitivity.csv` varies the high-pressure cutoff (45, 50, 55) and mismatch weight (0.60, 0.75, 0.90) using **point scores** for both the baseline and alternative lists. At weight 0.75, cutoff 45 retains 7/10 batting and 8/10 bowling baseline point-score names; cutoff 55 retains 6/10 and 8/10. At cutoff 50, mismatch weight 0.60 retains 9/10 in both roles, while weight 0.90 retains 10/10. The separate conservative bootstrap ranking overlaps the main point-score top 10 by 9/10 in each role. The batting boundary remains materially sensitive to the pressure definition.

## Additional evidence

`player_pressure_summary.csv` reports pressure and low-pressure impact, exposure, match-level consistency, pace/spin or RHB/LHB splits, and bowler dismissal modes. `player_pressure_segments.csv` repeats the comparison within IPL/T20I and individual series; thin series cells are descriptive. [Phase 6](PHASE_6_CONTEXT_PROFILES.md) adds powerplay/middle/death, country-condition, dot-ball, and portability profiles without adding correlated bonus points to the primary score. The [submission report](SUBMISSION_REPORT.md) contains the ordered dropdown lists and the main evidence.
