# SupeRR Selector Season 2 - Round 1 final methodology

## Ordered dropdown selections

These are the **final selections in dropdown order**. Both lists come from the same 2022-2026 IPL and T20I analysis. We combine two pre-ball pressure models by adding each player's rank within the pool eligible under **both** models; the lowest rank sum wins. A smaller rank sum means stronger agreement, not cricket runs or an official rating. The state-model interval is a 10th-90th percentile range from 300 whole-match bootstrap draws of its runs-per-100-effective-ball score. It is **not** a confidence interval for the consensus rank.

### Batters

| Rank | Player | Legacy rank | State rank | Rank sum | State balls / matches | Positive matches | State bootstrap 10th-90th |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | Rinku Singh | 2 | 2 | 4 | 476.5 / 68 | 47.1% | 22.610-49.535 |
| 2 | Shreyas Iyer | 1 | 4 | 5 | 363.0 / 47 | 55.3% | 18.351-44.420 |
| 3 | Suryakumar Yadav | 7 | 1 | 8 | 551.5 / 63 | 60.3% | 25.514-43.795 |
| 4 | Tim David | 6 | 3 | 9 | 502.0 / 79 | 54.4% | 21.225-46.226 |
| 5 | Naman Dhir | 5 | 5 | 10 | 145.5 / 21 | 61.9% | 16.075-49.266 |
| 6 | Jos Buttler | 12 | 6 | 18 | 300.0 / 45 | 51.1% | 14.925-41.394 |
| 7 | Virat Kohli | 3 | 16 | 19 | 319.0 / 32 | 59.4% | 6.657-28.126 |
| 8 | Dinesh Karthik | 13 | 8 | 21 | 314.0 / 53 | 49.1% | 9.979-41.100 |
| 9 | Tristan Stubbs | 4 | 17 | 21 | 368.0 / 50 | 52.0% | 6.457-26.585 |
| 10 | Marcus Stoinis | 11 | 11 | 22 | 359.5 / 56 | 58.9% | 7.891-34.399 |

### Bowlers

| Rank | Player | Legacy rank | State rank | Rank sum | State balls / matches | Positive matches | State bootstrap 10th-90th |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | Sunil Narine | 1 | 1 | 2 | 366.5 / 51 | 72.5% | 21.436-37.743 |
| 2 | Abrar Ahmed | 2 | 3 | 5 | 220.0 / 26 | 80.8% | 14.036-36.506 |
| 3 | Jasprit Bumrah | 4 | 2 | 6 | 488.0 / 68 | 64.7% | 18.273-42.817 |
| 4 | Lungi Ngidi | 5 | 4 | 9 | 164.0 / 30 | 66.7% | 12.786-37.221 |
| 5 | Tim Southee | 3 | 6 | 9 | 235.5 / 31 | 64.5% | 10.018-33.313 |
| 6 | Rashid Khan | 7 | 5 | 12 | 751.5 / 94 | 64.9% | 11.304-29.958 |
| 7 | Varun Chakravarthy | 6 | 9 | 15 | 530.0 / 71 | 66.2% | 7.367-26.967 |
| 8 | Matheesha Pathirana | 8 | 8 | 16 | 445.0 / 45 | 53.3% | 6.633-28.690 |
| 9 | Shaheen Afridi | 9 | 11 | 20 | 272.0 / 38 | 60.5% | 2.933-25.461 |
| 10 | Kuldeep Yadav | 11 | 10 | 21 | 399.0 / 62 | 58.1% | 4.629-32.298 |

## Data and match-state preparation

The supplied pack has 883 matches and 200,999 delivery records. We analyse 785 eligible IPL/T20I matches and 187,509 first- or second-innings deliveries, excluding abandoned/no-result games, other competitions, revised/DLS games, and super overs. Every pressure feature is determined **before** the delivery: innings phase, wickets already lost, balls remaining, chase requirement, and knockout status. A rolling pre-match Elo proxy from earlier supplied results supplies team context. It is not an official historical ICC ranking.

The pack omits exact extras. We matched 526 of the 785 eligible games delivery by delivery to Cricsheet's IPL and men's T20I records. The state model uses exact first-innings totals and cumulative extras for those games. For the other 259 games it uses the pack's approximate requirement, drops a chase delivery if a seven-run shift changes its pressure tier, and excludes unverified games with large run-margin reconstruction errors. The verified subset is not a random sample of all matches.

## Two complementary pressure definitions

The **legacy model** scores innings phase, wickets already lost, second-innings chase difficulty/contestability, and knockout status. Phase points are 0/10/24/34 for overs 1-6/7-15/16-18/19-20; wicket points are 0/7/14/20 for 0-2/3-4/5-6/7+ prior wickets. A contestable chase adds 5-22 points according to required rate and balls left, an urgent chase with four or fewer wickets in hand adds eight, and a knockout adds ten. Low, medium, and high tiers are below 30, 30-49, and at least 50. Medium balls receive half pressure weight and high balls full weight.

The **state model** retains those phase, wicket, knockout, and urgent low-wicket points, adds 15 for two or more powerplay wickets already lost, and raises chase points in still-contestable middle-over situations. When 0.8-1.6 runs per ball are needed, the chase adds 26/28/22 points with more than 60 / 37-60 / at most 36 balls left; at 1.6-2.3 it adds 13/19/22. Easier chases add zero; more than 2.3 runs per ball adds 7 or 15 depending on time left. The same tier cutoffs and half/full weights apply to batters and bowlers. Under the state rule, 4,341 powerplay deliveries are medium pressure and 80 high pressure, versus one medium and none high under the legacy rule after scoring exclusions. The state rule also includes more close middle-over chases.

## Performance, fair comparison, and reliability

The legacy expectation estimates batter runs and striker-dismissal probability, plus minimum bowler run cost and credited-wicket probability, from **earlier dates only**. It pools sparse IPL/T20I, year, phase, pace/spin, batter-hand, country/venue, and opposing-team cells toward broader averages. A batter's delivery value is `runs - expected runs - 5 x (striker out - expected out probability)`. A bowler's value is `expected minimum cost - observed minimum cost + 5 x (credited wicket - expected wicket probability)`. The minimum cost includes batter runs and one run for a wide or no-ball; it is not exact economy. Run-outs never count as bowler wickets. Top-six-versus-bottom fixtures with a substantial prior Elo gap receive 0.75 value weight; all other fixtures receive 1.0. Exposure denominators remain raw.

The legacy player score combines 65% shrunk pressure performance and 35% shrunk pressure uplift versus that player's low-pressure rate. The **state model** first subtracts a prior-date average residual for similar pressure states, pooling format/phase/innings, pressure tier, and wickets/required rate/balls left in three levels. This removes much of the league-wide bias where high-pressure death-over batters appeared about 21 runs per 100 balls below the original expectation and bowlers about 21 above it. Its player score is pressure impact per 100 effective balls, shrunk by `effective balls / (effective balls + 80)`. Both methods use the average of their point score and match-bootstrap 10th percentile as a conservative score.

To enter the final pool, a player must have at least **100 effective pressure balls across 20 pressure matches and 50 low-pressure balls in each method**. This leaves 58 batters and 83 bowlers. We rank each role separately within that common pool under each method, add the two ranks, and break a tie by the better worst rank, then the higher state conservative score, then player ID. Match-to-match positive share is shown in the tables and audited as an alternative ranking signal. Adding it as a third rank did not consistently improve later top-10 impact, so it is evidence, not a hidden weight.

Rinku Singh is batting rank 2 in both methods and has 476.5 state-model effective pressure balls in 68 matches. His positive-match share is **47.1%**: his high aggregate impact is driven by the size of positive contributions, not a majority of matches. Shreyas Iyer has a stronger legacy score but falls from legacy rank 1 to state rank 4. Sunil Narine ranks first under both bowling methods, with 366.5 state pressure balls in 51 matches and a 72.5% positive-match share. The overlapping bootstrap ranges in the tables warn against treating adjacent ranks as certain.

## Out-of-time checks and limitations

The table tests the actual conservative scores and common eligibility pool. Training ends before the test year; a player also needs at least 15 state pressure balls in four later matches to be evaluated. Values are the **mean later state-adjusted pressure impact per 100 effective balls** of the training top 10, not a prediction of team wins. The 2024 training cutoff has 25 evaluable batters and 38 bowlers in 2025; the 2025 cutoff has 33 and 45 in 2026.

| Test year | Role | Players | Legacy top-10 impact | State top-10 impact | Consensus top-10 impact |
| ---: | --- | ---: | ---: | ---: | ---: |
| 2025 | Batting | 25 | +27.950 | +22.497 | +28.901 |
| 2025 | Bowling | 38 | +19.029 | +8.803 | +18.003 |
| 2026 | Batting | 33 | +7.717 | +8.275 | +14.260 |
| 2026 | Bowling | 45 | -14.804 | +11.893 | -5.746 |

The consensus gives the strongest batting top-10 impact in both final-gate checks. Bowling is mixed: the legacy list is stronger in 2025 and the state list in 2026, while consensus reduces dependence on either pressure rule. These are small, survival-selected cohorts, and the same years were used to inspect the candidate methods. The results support a robust compromise, not a claim of universal optimality.

Across year/format/role high-pressure death-over cells, the state correction reduces the ball-weighted mean absolute residual from **21.58 to 6.19 runs per 100 balls**. On verified held-out chases, the state pressure score improves alignment with a win-probability leverage diagnostic in 2025-2026 (AUC 0.756 versus 0.730), but is slightly lower in 2023-2024 (0.836 versus 0.844). That win-probability model misses its 0.08 calibration-error gate in six of eight year/format cells and is not used to rank players. Exact extras remain unavailable in 259 games; venue and matchup samples can be thin; T20I coverage is incomplete; and the five-run wicket conversion and pressure thresholds are modelling choices. The consensus partly guards against those choices but cannot remove their uncertainty.

## Reproduction and source attribution

Run `scripts/run_pipeline.py` from the repository root. It rebuilds both component rankings, `data/processed/final_rankings.csv`, and this Markdown report. Run `scripts/render_submission_report.py --final` to regenerate the uploadable PDF; the renderer verifies all 20 displayed names, ranks, and rank sums against the CSV. The score-quality audit and source attribution for the matched extras are in `data/external/README.md`. Credit: Cricsheet (cricsheet.org), whose transformed extras data is used under its attributed license. The supplied contest data provides the primary player and match records.
