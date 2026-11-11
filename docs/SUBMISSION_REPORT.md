# SupeRR Selector Season 2 — Round 1 methodology report

## Recommended ordered selections

The two tables below are the recommended dropdown order. They are generated from the supplied 2022–2026 IPL and T20I files with the reproducible pipeline in `scripts/run_pipeline.py`. The values are a **model-adjusted runs-per-100-ball index**, not observed runs or official ratings. The 10th–90th ranges come from 300 whole-match bootstrap draws; overlapping ranges mean close ranks are uncertain.

### Batters

| Rank | Player | Conservative score | Effective pressure balls | Pressure matches | Positive pressure matches | Bootstrap 10th–90th |
| ---: | --- | ---: | ---: | ---: | ---: | --- |
| 1 | Shreyas Iyer | 37.391 | 166.0 | 29 | 62.1% | 28.195–64.073 |
| 2 | Rinku Singh | 28.283 | 369.5 | 57 | 49.1% | 20.935–48.860 |
| 3 | Virat Kohli | 23.959 | 110.0 | 21 | 66.7% | 17.679–44.804 |
| 4 | Tristan Stubbs | 23.607 | 229.5 | 42 | 54.8% | 16.309–43.999 |
| 5 | Naman Dhir | 22.638 | 141.5 | 21 | 61.9% | 12.303–47.677 |
| 6 | Tim David | 21.376 | 377.0 | 66 | 62.1% | 14.665–43.327 |
| 7 | Suryakumar Yadav | 21.160 | 212.5 | 43 | 53.5% | 13.982–42.442 |
| 8 | Glenn Phillips | 20.673 | 124.0 | 24 | 66.7% | 13.246–40.760 |
| 9 | Rovman Powell | 18.557 | 386.5 | 58 | 56.9% | 11.126–39.362 |
| 10 | David Miller | 17.650 | 326.5 | 58 | 51.7% | 11.020–35.421 |

### Bowlers

| Rank | Player | Conservative score | Effective pressure balls | Pressure matches | Positive pressure matches | Bootstrap 10th–90th |
| ---: | --- | ---: | ---: | ---: | ---: | --- |
| 1 | Sunil Narine | 34.754 | 180.0 | 39 | 82.1% | 29.542–50.106 |
| 2 | Abrar Ahmed | 28.218 | 148.0 | 23 | 82.6% | 21.648–45.932 |
| 3 | Tim Southee | 27.631 | 196.0 | 30 | 70.0% | 21.837–46.288 |
| 4 | Jasprit Bumrah | 25.780 | 368.5 | 59 | 69.5% | 18.162–47.427 |
| 5 | Lungi Ngidi | 25.774 | 141.0 | 28 | 67.9% | 18.765–46.399 |
| 6 | Varun Chakravarthy | 23.554 | 293.0 | 62 | 66.1% | 16.764–43.709 |
| 7 | Rashid Khan | 21.241 | 474.0 | 88 | 63.6% | 14.422–40.888 |
| 8 | Matheesha Pathirana | 20.988 | 328.5 | 39 | 53.8% | 13.350–42.624 |
| 9 | Shaheen Afridi | 18.663 | 226.5 | 35 | 62.9% | 12.753–36.220 |
| 10 | Mitchell Starc | 17.241 | 130.0 | 27 | 55.6% | 4.944–55.555 |

## Data preparation and pressure definition

The supplied pack contains 883 matches and 200,999 delivery records. We kept 785 IPL/T20I matches and 187,509 first- or second-innings deliveries after excluding abandoned/no-result matches, other T20 competitions, and revised/DLS matches. Super-over innings are outside the primary analysis. A delivery's state is calculated **before** its outcome: legal balls remaining, wickets lost, approximate score and chase requirement, innings stage, and knockout status.

The pressure index adds four transparent components, capped at 100:

| Component | Points |
| --- | --- |
| Overs 1–6 / 7–15 / 16–18 / 19–20 | 0 / 10 / 24 / 34 |
| Wickets already lost 0–2 / 3–4 / 5–6 / 7+ | 0 / 7 / 14 / 20 |
| Second-innings contestability, based on approximate runs per ball required and balls left | 0–22 |
| At least 1.35 runs per ball required with at most four wickets in hand | +8 |
| Knockout match | +10 |

Low pressure is below 30, medium is 30–49, and high is at least 50. A still-contestable tight chase gets more chase points than an almost impossible one because the former has greater scope for an individual delivery to change the result. Medium deliveries count at half weight; high at full weight. Low deliveries establish each player's usual-performance baseline. The same pre-ball labels are applied to both roles, while their performance metrics differ.

The source extras fields do not recover exact innings totals. We approximate one run per extras event only for the chase state. Among 382 eligible run-margin matches, the reconstruction error has median 1 run and 95th percentile 7. We drop 4,776 chase deliveries whose pressure tier changes when the requirement moves by ±7 runs. We also omit all deliveries from 13 audited matches with margin error above 7 when scoring players. These checks reduce sensitivity to missing extras; they do not prove every retained chase label is exact.

## Fair comparison and rating

Before evaluating each date, a model trained on **earlier dates only** estimates batter runs, striker-dismissal probability, minimum bowler run cost, and credited-wicket probability. It pools sparse format/year/innings-phase, pace/spin, batter-hand, venue/country, and opponent cells toward broader averages. Venue effects are estimated from prior matches, so a player's own match cannot set its expectation. A rolling pre-match Elo proxy from supplied results estimates team strength. It is not an official historical ICC table. Top-six-versus-bottom fixtures with at least a 75-point Elo gap and five prior matches on both sides receive a 0.75 match weight; 144 of 785 eligible fixtures meet that rule.

For a batter, delivery value equals **batter runs minus expected batter runs minus 5 times (striker dismissed minus expected dismissal probability)**. For a bowler, value equals **expected minimum bowler cost minus observed minimum cost plus 5 times (credited wicket minus expected credited-wicket probability)**. The minimum cost includes batter runs and one run for a wide or no-ball; unknown extras prevent exact economy. Run-outs and other non-bowler dismissals never count as bowler wickets. The five-run wicket conversion is tested below.

We sum weighted values in medium and high pressure, divide by effective pressure balls, and compare that rate with the player's low-pressure rate. The pressure difference is shrunk with factor `effective pressure balls / (effective pressure balls + 80)`. The point score is `0.65 × shrunk pressure rate + 0.35 × shrunk pressure uplift`, expressed per 100 balls. The final conservative score averages the point score with its bootstrap 10th percentile. To qualify, a player needs at least **100 effective pressure balls in 20 matches and 50 low-pressure balls**. This yields **59 eligible batters and 83 eligible bowlers**. The 20-match floor prevents a short exceptional spell from carrying a reliability ranking.

## Evidence, consistency, and sensitivity

Shreyas Iyer leads the batting index by 9.108 points over Rinku Singh. His 29 pressure matches and 62.1% positive-match share support the lead, though his IPL segment is much stronger than his T20I segment. Rinku Singh has 369.5 effective balls over 57 matches, but only 49.1% of his pressure matches are positive; his aggregate score reflects large positive contributions and should not be described as success in most matches. Tim David has 377 effective balls over 66 matches and similar IPL/T20I segment scores. Babar Azam's 10 pressure matches no longer meet the eligibility floor; Ashutosh Sharma has only 36 low-pressure balls, below the baseline requirement.

Sunil Narine leads bowling by 6.536 points over Abrar Ahmed and has positive contributions in 82.1% of 39 pressure matches. Jasprit Bumrah, Varun Chakravarthy, Rashid Khan, and Matheesha Pathirana bring much larger pressure exposure. Mark Wood's 11 pressure matches and 70 effective balls no longer qualify. The exact ordering of adjacent players is uncertain because bootstrap ranges overlap widely.

| Check | Batting names retained | Bowling names retained | Interpretation |
| --- | ---: | ---: | --- |
| Legacy gate 40 balls / 8 matches / 30 low balls | 8/10 | 8/10 | Short samples re-enter both lists. |
| Relaxed gate 80 / 20 / 50 | 9/10 | 10/10 | A modest ball change has little effect. |
| Stricter gate 120 / 30 / 60 | 6/10 | 7/10 | Exposure requirements affect the boundary. |
| Wicket conversion 3 rather than 5 runs | 9/10 | 9/10 | One name changes in each list. |
| Wicket conversion 7 rather than 5 runs | 10/10 | 10/10 | Membership stays fixed. |
| High-pressure cutoff 45 rather than 50, point-score comparison | 7/10 | 8/10 | The pressure definition remains consequential. |
| High-pressure cutoff 55 rather than 50, point-score comparison | 6/10 | 8/10 | Several batters near the boundary change. |
| Mismatch weight 0.60 rather than 0.75 at cutoff 50, point-score comparison | 9/10 | 9/10 | Stronger fixture discount changes one name each. |
| Mismatch weight 0.90 rather than 0.75 at cutoff 50, point-score comparison | 10/10 | 10/10 | Membership stays fixed. |

The gate and wicket checks recompute the same conservative bootstrap ranking; cutoff and mismatch checks use point scores throughout their comparison. They should not be interpreted as directly comparable rank uncertainty measures. The top names are relatively stable, while several lower batting selections are sensitive to modelling choices.

## Phase, country, and dot-ball evidence

The supplied records also support **all-ball** powerplay (overs 1–6), middle (7–15), and death (16–20) scores. Each is above-expectation impact per 100 balls, shrunk by `phase balls / (phase balls + 80)` and shown only after 100 balls in that phase. They describe phase skill separately from the pressure rating: the current pressure rule yields almost no weighted powerplay balls for the ranked players. The full player-by-phase table is `data/processed/player_phase_scores.csv`.

| Player | Powerplay score (balls) | Middle score (balls) | Death score (balls) |
| --- | ---: | ---: | ---: |
| Virat Kohli, batter | +21.765 (1,110) | +7.856 (1,074) | +35.766 (207) |
| Suryakumar Yadav, batter | +8.801 (608) | +37.123 (1,668) | +44.005 (294) |
| Jasprit Bumrah, bowler | +9.250 (703) | +18.717 (341) | +44.669 (482) |
| Sunil Narine, bowler | -0.145 (198) | +17.605 (1,044) | +52.873 (192) |

We infer country conditions from **earlier matches in the same format and innings phase**, pooled toward a broad baseline. A prior run factor at most 0.97 marks run-suppressing conditions; a wicket factor at least 1.03 marks wickets-common conditions, with at least 500 prior balls and deliveries for a label. These are time-varying estimates, not permanent descriptions of a country. In Zimbabwe T20Is, Rinku Singh scored 79 batter runs versus 54.209 contextually expected over 20 effective pressure balls; the mean prior country run factor was 0.963. In New Zealand T20Is, Tim Southee took 14 credited wickets versus 9.898 expected over 97 effective pressure balls; the mean prior wicket factor was 1.055. The expectation already accounts for venue and opponent, so these results receive no additional country bonus. Full country and condition profiles are in `data/processed/player_country_scores.csv` and `player_country_condition_scores.csv`.

A batter's zero-batter-run percentage counts faced deliveries with no personal runs, including some balls where extras score. A stricter **scoreless dot** requires a legal ball, zero batter runs, and no extras event; it measures scoreboard pressure. Strike rate is `100 × batter runs / faced balls`. Shreyas Iyer's overall strike rate is 152.74 with 29.70% zero-batter-run balls; in medium/high pressure his strike rate is 212.64 and strict scoreless-dot share 19.70%. Abrar Ahmed's strict scoreless-dot share is 42.00% on all legal balls and 46.15% in medium/high pressure. On a scoreless chase dot, we also record the resulting increase in approximate required runs per remaining ball; this is a pressure-creation diagnostic for the bowler and a pressure-absorption diagnostic for the batter. It is sensitive to missing extras and late-ball denominators, so it is not added to the main rating. All players' strike, dot, and chase-dot figures are in `data/processed/player_dot_pressure.csv`.

For a distinct reliability check, **pressure portability** counts positive, above-expectation impact across supported phase, matchup, and adverse-condition cells. A cell requires 20 effective pressure balls in five matches. A score of `(positive supported cells + 1) / (supported cells + 2) × 100` is shown only with at least three supported cells. Shreyas Iyer and Jasprit Bumrah each score 87.5 across six supported contexts; Rinku Singh scores 62.5 across six. The contexts overlap, so this diagnostic explains breadth and does not change the ranking. Full coverage and weak cells are in `data/processed/player_portability.csv`.

## Elite opponents and time at top

The official ICC men's T20I batting and bowling top-10 tables dated **3 November 2026** define a retrospective elite-opponent cohort. The ICC historical-date parameter returned the current table, so our new `elite_tenure_rankings.csv` uses a separate **prior-only, within-pack T20I proxy**: monthly top-ten appearances from a trailing-year contextual score, with a 120-ball/eight-match window gate. Jos Buttler leads batting with 33 top-ten months; Arshdeep Singh leads bowling with 29. These are not official historical ICC ranks.

`elite_phase_matchups.csv` reports powerplay and death-over scores against both the current ICC cohort and **prior-month proxy top-ten opponents with at least three top-ten months**. Scores require 30 balls in five matches. Against the historical cohort, Tim David's death-over batting score is **+32.090** over 63 balls in 12 matches; Jason Behrendorff's powerplay bowling score is **+20.795** over 46 balls in eight matches. These are all-ball phase scores, separate from the main pressure ranking. Methods and ICC links are in `docs/PHASE_7_ELITE_TENURE.md`.

## Limitations and reproducibility

Exact extras and required run rates are absent. The available T20I results are not a complete international schedule, so the pre-match team rating is a proxy. Some scoring seasons remain underpredicted: IPL 2024 batter runs were 1.067 times the model prediction, and T20I 2026 were 1.056 times. Thin venues, countries, matchups, and player samples remain uncertain despite pooling and bootstrap. The out-of-time chase win-probability diagnostic beats Elo alone but has uneven calibration and high score-reconstruction sensitivity, so it is not used to change these rankings. Official dated team rankings and verified scorecards would strengthen the analysis.

Run `scripts/run_pipeline.py` from the project virtual environment to rebuild the cumulative, pressure, context, win-probability, ranking, robustness, profile, and elite-matchup files. The linked delivery-level intermediate files and compact CSV outputs are documented in `data/processed/README.md`. The validator checks delivery keys, pre-ball state, model links, segment and context-profile totals, and exact agreement between the ordered CSV and player summary. The ordered dropdown selections should match `data/processed/rankings.csv` and the two tables at the start of this report.
