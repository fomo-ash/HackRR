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
| 6 | Babar Azam | 22.220 | 63.0 | 10 | 90.0% | 15.968–38.870 |
| 7 | Tim David | 21.376 | 377.0 | 66 | 62.1% | 14.665–43.327 |
| 8 | Suryakumar Yadav | 21.160 | 212.5 | 43 | 53.5% | 13.982–42.442 |
| 9 | Ashutosh Sharma | 20.732 | 191.0 | 24 | 66.7% | 11.933–45.497 |
| 10 | Glenn Phillips | 20.673 | 124.0 | 24 | 66.7% | 13.246–40.760 |

### Bowlers

| Rank | Player | Conservative score | Effective pressure balls | Pressure matches | Positive pressure matches | Bootstrap 10th–90th |
| ---: | --- | ---: | ---: | ---: | ---: | --- |
| 1 | Sunil Narine | 34.754 | 180.0 | 39 | 82.1% | 29.542–50.106 |
| 2 | Abrar Ahmed | 28.218 | 148.0 | 23 | 82.6% | 21.648–45.932 |
| 3 | Tim Southee | 27.631 | 196.0 | 30 | 70.0% | 21.837–46.288 |
| 4 | Mark Wood | 26.895 | 70.0 | 11 | 63.6% | 18.553–49.972 |
| 5 | Jasprit Bumrah | 25.780 | 368.5 | 59 | 69.5% | 18.162–47.427 |
| 6 | Lungi Ngidi | 25.774 | 141.0 | 28 | 67.9% | 18.765–46.399 |
| 7 | Mohammad Nawaz | 25.143 | 87.5 | 17 | 82.4% | 18.584–46.213 |
| 8 | Varun Chakravarthy | 23.554 | 293.0 | 62 | 66.1% | 16.764–43.709 |
| 9 | Rashid Khan | 21.241 | 474.0 | 88 | 63.6% | 14.422–40.888 |
| 10 | Matheesha Pathirana | 20.988 | 328.5 | 39 | 53.8% | 13.350–42.624 |

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

We sum weighted values in medium and high pressure, divide by effective pressure balls, and compare that rate with the player's low-pressure rate. The pressure difference is shrunk with factor `effective pressure balls / (effective pressure balls + 80)`. The point score is `0.65 × shrunk pressure rate + 0.35 × shrunk pressure uplift`, expressed per 100 balls. The final conservative score averages the point score with its bootstrap 10th percentile. To qualify, a player needs at least 40 effective pressure balls in eight matches and 30 low-pressure balls. This yields 130 eligible batters and 172 eligible bowlers.

## Evidence, consistency, and sensitivity

Shreyas Iyer leads the batting index by 9.108 points over Rinku Singh. His 29 pressure matches and 62.1% positive-match share support the lead, though his IPL segment is much stronger than his T20I segment. Rinku Singh has the largest pressure sample near the top, at 369.5 effective balls over 57 matches, but only 49.1% of his pressure matches are positive; his aggregate score reflects large positive contributions and should not be described as success in most matches. Tim David has 377 effective balls over 66 matches and similar IPL/T20I segment scores. Babar Azam passes the gate with only 63 effective balls in 10 matches, so his rank is sensitive to a stricter gate.

Sunil Narine leads bowling by 6.536 points over Abrar Ahmed and has positive contributions in 82.1% of 39 pressure matches. Jasprit Bumrah, Varun Chakravarthy, Rashid Khan, and Matheesha Pathirana bring much larger pressure exposure. Mark Wood's 70 effective balls in 11 matches make his fourth-place estimate more fragile. The exact ordering of adjacent players is uncertain because bootstrap ranges overlap widely.

| Check | Batting names retained | Bowling names retained | Interpretation |
| --- | ---: | ---: | --- |
| At least 60 effective balls / 10 matches / 50 low balls | 9/10 | 10/10 | Ashutosh Sharma leaves batting top 10. |
| At least 100 effective balls / 15 matches / 50 low balls | 8/10 | 8/10 | Babar Azam and Mark Wood no longer qualify. |
| Wicket conversion 3 rather than 5 runs | 8/10 | 9/10 | Batting and bowling boundary names change. |
| Wicket conversion 7 rather than 5 runs | 9/10 | 9/10 | Boundary remains somewhat sensitive. |
| High-pressure cutoff 45 rather than 50, point-score comparison | 7/10 | 9/10 | Batting pressure definition materially affects selection. |
| High-pressure cutoff 55 rather than 50, point-score comparison | 5/10 | 8/10 | Several batters near the boundary change. |
| Mismatch weight 0.60 rather than 0.75 at cutoff 50, point-score comparison | 10/10 | 10/10 | Stronger fixture discount barely changes membership. |
| Mismatch weight 0.90 rather than 0.75 at cutoff 50, point-score comparison | 8/10 | 9/10 | Weaker discount changes some boundary names. |

The gate and wicket checks recompute the same conservative bootstrap ranking; cutoff and mismatch checks use point scores throughout their comparison. They should not be interpreted as directly comparable rank uncertainty measures. The top names are relatively stable, while several lower batting selections are sensitive to modelling choices.

## Limitations and reproducibility

Exact extras and required run rates are absent. The available T20I results are not a complete international schedule, so the pre-match team rating is a proxy. Some scoring seasons remain underpredicted: IPL 2024 batter runs were 1.067 times the model prediction, and T20I 2026 were 1.056 times. Thin venues, countries, matchups, and player samples remain uncertain despite pooling and bootstrap. A model of match win probability, official dated team rankings, and verified scorecards would support a stronger pressure definition and calibration.

Run `scripts/run_pipeline.py` from the project virtual environment to rebuild the cumulative, pressure, context, and ranking files, then run `scripts/check_robustness.py` for the gate and wicket checks. The linked delivery-level intermediate files and compact CSV outputs are documented in `data/processed/README.md`. The validator checks delivery keys, pre-ball state, model links, segment totals, and exact agreement between the ordered CSV and player summary. The ordered dropdown selections should match `data/processed/rankings.csv` and the two tables at the start of this report.
