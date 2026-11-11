# SupeRR Selector Season 2: data and analysis plan

## Objective and submission

Rank the 10 most reliable batters and 10 most reliable bowlers in high-pressure situations, relative to their usual performance. Submit the ordered names through Unstop and a report explaining the pressure definition, metrics, comparisons, sample sizes, uncertainty, and the evidence behind each ranking. The problem statement is in `6af3166e7b922_data_pack/Round 1 Problem Statement _ SupeRR Selector Season 2.docx.pdf`.

The first cumulative player/series/venue datasets have been built. Pressure labels, opponent-strength weights, models, and final rankings have not been built yet. All development runs in the project virtual environment (`.venv`).

## Supplied data inspected

| File | Rows | Main grain and useful fields |
| --- | ---: | --- |
| `ball_by_ball.csv` | 200,999 | One delivery; match/innings/over, striker, bowler, batter runs, dismissal, extras type, batter hand, bowling type, pace/spin, delivery time. |
| `matches.csv` | 883 | One match; competition, date, stage, venue ID/country, teams, winner/result, revised overs/target. |
| `competitions.csv` | 141 | One competition; name, format, season. |
| `playing_eleven.csv` | 28,381 | Match/team/player squad record; played, batting order, captain, wicketkeeper, impact-player flags. |
| `competition_team_player_mapping.csv` | 6,413 | Competition/team/player identity and names. There is no standalone players file. |
| `teams.csv` | 353 | Competition/team identity and names. |

Dates span 2022-01-22 to 2026-11-01. There are ball records for 367 IPL matches, 470 T20Is, and 30 other T20 matches. The primary analysis will use IPL and T20I, matching the brief; other T20 matches will be a sensitivity check only. All delivery-to-match and match-to-competition joins resolve. Sixteen abandoned matches have no ball records. Six matches contain third/fourth innings (super overs). Thirty-four matches have revised-overs/target fields. These cases need separate handling or exclusion from the primary score.

There are 138 series with matches and 5,005 active series-team-player combinations (958 distinct players); all active combinations appear in the mapping. A repeatable batch analysis keyed by `comp_id`, `team_id`, and `player_id` can cover every active player in every series. It should distinguish mapped squad members from players who actually batted or bowled.

### Data issues that affect the model

- `extras1_runs` behaves as an extras-type code: all wides have value 2, leg-byes 3, byes 4, and ordinary balls 6. It must not be summed as runs. `extras_2_runs` is zero for 200,963 of 200,999 deliveries. Exact running totals and exact required run rates cannot be recovered from these fields alone.
- A provisional score using batter runs plus one run per extras event gave a median winning-margin error of 1 run across 399 non-DLS results decided by runs; the 95th percentile error was 7 and maximum 11. Near a pressure cutoff, this is material. We will audit score reconstruction and mark uncertain chase states rather than pretend scores are exact.
- `bowl_speed` has 77,861 zeroes and 20 values over 170, including a very large outlier. It is unsuitable for the main model. Use `pace_or_spin` and `bowling_type` instead.
- 41 of 98 venues have at most three listed matches. Ninety-four of 138 series have at most three matches. Direct venue/series rates will be unstable unless pooled toward broader context.
- Dismissal types include run-outs, retire-outs, and obstructing the field. These are not bowler wickets. Bowler-credited wickets need an explicit rule; catches, bowled, LBW, stumped, and hit wicket are candidates to credit. Confirm unusual records before finalizing.
- `playing_eleven.csv` includes non-playing squad members and some duplicate match/team/player records. Use deliveries as evidence of actual participation, and deduplicate roster records carefully.
- Avoid using `delivery_ist_time` as the sole match date: its date differs from `matches.match_date` on some rows. Use match metadata for chronology and ball order for within-innings sequence.

## Proposed analytical framework

### 1. Build a clean pre-delivery state

For each delivery, derive match format/season/series, innings, over, legal balls used and remaining, wickets already lost, batter hand, bowling class, venue, country, and prior batter-run total. Derive all state features *before* observing the current delivery, so the delivery's outcome cannot define its own pressure. Keep source fields and derived fields separate, and record exclusions and reasons.

Audit extras and score reconstruction against match results. If a chase score or target is uncertain enough to change a pressure label, either omit that label or flag it for sensitivity analysis. Revised matches and super overs will be excluded from the main pressure model unless their state can be reconstructed correctly.

### 2. Define pressure and test thresholds

Use a transparent index or rule combining:

1. **Game phase:** late overs have less time to recover.
2. **Wicket constraint:** fewer wickets remaining changes batting risk and bowling opportunity.
3. **Chase difficulty:** runs required relative to balls and wickets remaining, only where score reconstruction is reliable.
4. **Match stakes:** knockout matches as a separately reported modifier, not the only definition of pressure.

Distinguish *batting-side pressure* from *match leverage*. A chase can be difficult for the batters while comfortable for the bowlers; both sides can face high leverage when the game is close. Report the dimensions separately before combining them.

Pre-register low/medium/high pressure tiers after examining their sample sizes, for example by within-format pressure percentiles, and sweep nearby cutoffs. Do not pick a threshold because it produces familiar names. As a stronger optional method, fit a calibrated win-probability model using pre-delivery state and match outcome; validate by season and match, and use it only if reconstructed scores and calibration pass. High leverage means a delivery can materially change win probability, not merely that the game is late.

### 3. Compare batters by bowling matchup

For every batter, calculate overall and pressure-specific performance against:

- Pace versus spin (`pace_or_spin`), with finer bowling types where enough balls exist.
- Right-arm/left-arm and spin subtypes inferred from `bowling_type`.
- Match phase, IPL versus T20I, innings, opposition, and venue context.

Report runs per legal ball/strike rate, boundary rate, dot rate, and dismissal risk. For the main score, compare each delivery with a *contextual expected* batter outcome, then compare the batter's pressure residual with their own usual residual. Include a pressure-by-bowling-class interaction: does the player retain or improve performance against pace and spin under pressure? Do not let a tiny pace/spin split dominate the rank; display sample sizes and shrink sparse splits.

### 4. Compare bowlers by batter matchup and dismissal mode

For every bowler, split overall and pressure performance against right- and left-handed batters (`batting_type`), plus phase, format, venue, and opposition. Measure batter runs allowed per legal ball, dot/boundary rates, extras-event rates, and bowler-credited wicket rate. Exact economy including extras cannot be calculated from the supplied fields, so label any run-concession metric precisely.

Show dismissal modes (caught, bowled, LBW, stumped, etc.) as an explanatory profile. Credit legitimate bowler wickets equally in the headline score unless a defensible, validated wicket-value model supports differing values. A catch still counts as a wicket; a run-out must not be credited to the bowler. Check whether a bowler's pressure advantage holds against both RHB and LHB, or depends on one matchup, and show the number of balls faced in each split.

### 5. Adjust for venue, country, series, and opponent

Estimate scoring-friendliness and wicket-friendliness from observed deliveries at each `venue_id`, controlling for format, season, innings, phase, teams/opponents, and pace/spin where possible. Use runs per legal ball and wicket rate as separate indicators. A country is a *pooling level*, not a blanket claim that every ground in that country favours batting or bowling. Sparse venues should shrink toward country and format averages; sparse countries toward the global format average. Estimate venue conditions from prior matches or leave the evaluated match out, so a player's own performance does not set the benchmark they are judged against.

Adjust **expected performance** for venue conditions rather than assigning arbitrary bonus points. A batter who scores well at a difficult venue, or a bowler who suppresses runs at a high-scoring venue, then earns a larger above-expectation result. Report venue sample size and uncertainty. The files contain venue IDs and countries but no venue-name mapping, so any external stadium description must first be matched and verified; it is optional context, not a substitute for the observed data.

For each series, run one reproducible aggregation over *all* active players and produce batting/bowling profiles and coverage logs. Series-level effects should be pooled because most series are short. Avoid a separate external web query for each player unless a specific missing field requires it; those lookups would be difficult to verify and unnecessary for fields already supplied.

### 6. Discount top-versus-bottom mismatches

Give a lower match weight to games between a top-six team and a substantially weaker team, as requested. This prevents one-sided fixtures from contributing as much to a player's final pressure points. Define the bottom group and the size of the strength gap *before* viewing player ranks. An initial rule to test is T20I rank 1-6 versus rank 13 or lower; for the 10-team IPL, top six versus bottom four **only if** the pre-match strength gap is substantial. A provisional mismatch weight is `0.75` versus `1.00` for peer games; compare results at `0.60`, `0.75`, `0.90`, and no discount before fixing it. Keep raw match/ball counts unchanged for eligibility and report the weighted exposure separately.

Rankings must be **as of the match date**. The current ICC T20I table cannot be copied onto 2022-2025 games. Seek dated ICC rankings for T20Is; if complete historical snapshots are unavailable, construct a clearly labelled pre-match team-strength proxy from earlier results only. For IPL, use pre-match season-to-date standings or a rolling team rating, with a prior-season starting value. Do not use final-season standings to rate earlier matches. The `matches.csv` file has outcomes and dates but no pre-match ranking column, so this requires a separate, documented team-strength table.

The match discount applies to both teams because the fixture is less competitive, while the contextual expected-outcome model still distinguishes facing an elite opponent from facing a weak one. Check the combination for double-counting: if opponent adjustment already explains the mismatch, report how the added discount changes the top 10 and retain it only as a transparent robustness choice.

### 7. Convert outcomes into fair player scores

Start with context-adjusted runs above expectation and a separate wicket/dismissal component. Compare pressure performance with each player's general baseline, so the ranking reflects both **absolute contribution under pressure** and **change from usual level**. Also measure consistency across matches: number of pressure appearances, share of positive match contributions, and dependence on the best single match. Avoid double-counting correlated indicators such as runs, strike rate, and boundary rate.

Set eligibility before inspecting the final top 10. Evaluate provisional minimums such as 30/60/100 pressure balls and 5/8/12 pressure matches; choose thresholds that retain a meaningful candidate pool and report sensitivity. Shrink small player and matchup samples toward their relevant peer group. Bootstrap by match to quantify score and rank uncertainty. Keep IPL and T20I standardized results visible separately, then combine only after verifying that their scales and role mix are comparable.

### 8. Use unsupervised learning as a diagnostic

Cluster pre-delivery match states (phase, wickets, score/chase pressure where reliable, format) to see whether the rule-based pressure tiers overlook a distinct type of difficult situation. Inspect cricket meaning and stability of clusters. Do not treat cluster membership or an outlier score as proof of pressure or player quality. Isolation Forest is an anomaly detector and is not the main ranking algorithm.

## Cumulative dataset design for the implementation stage

Create linked, versioned outputs instead of one wide table that repeats every aggregate on every ball:

**Current build:** `scripts/build_cumulative_dataset.py` produces `data/processed/player_match_cumulative.csv`, `player_series_summary.csv`, `player_cumulative_summary.csv`, and `venue_context.csv`. The [processed-data README](data/processed/README.md) documents their grain, eligibility, and metric definitions. These are baseline aggregates; pressure scores and rankings remain future work.

1. **`delivery_fact`**: one row per source delivery; original IDs/values, derived legal-ball and pre-delivery state, pressure tier, score-quality flag, exclusion reason, and contextual expected/actual outcomes. Primary key: `match_id, innings, overid, over_ball_num` after uniqueness verification.
2. **`match_context`**: one row per match with competition, season, venue/country, format, result, revised/abandoned/super-over flags, score-reconciliation diagnostics, pre-match team ranks/ratings, ranking source/date, and mismatch weight.
3. **`venue_context`**: venue-season-format estimates for scoring and wickets, pace/spin differences, country prior, match count, and uncertainty.
4. **`player_series`**: one row per `comp_id, team_id, player_id, role` with matches, total and pressure balls, matchup splits, observed and expected outcomes, baseline, and quality flags. Include roster-only members with zero active balls only in a separate coverage view.
5. **`player_cumulative`**: one row per `player_id, role` with pooled and IPL/T20I results, pressure uplift, consistency, uncertainty, threshold sensitivity, raw and weighted match exposure, eligibility, and final rank. Match-level contributions should remain available underneath for audit and charts.

For a truly cumulative time series, add an `as_of_match_date` dimension and calculate each player's totals using only matches up to that date. Never use future matches to calculate a historical baseline or venue expectation. Store a data dictionary and transformation log with the outputs. Parquet is a good working format if available in `.venv`; export review tables as CSV.

## Execution order and acceptance checks

1. Create `.venv`, pin dependencies, and build repeatable source profiling/validation scripts.
2. Build and reconcile clean delivery/match facts; document exclusions and extras uncertainty.
3. Produce all-series/all-player and venue coverage tables; inspect sparse cells. Build dated pre-match team-strength and mismatch-weight tables.
4. Freeze pressure definition, eligibility rule, mismatch rule, and context-adjustment method before looking at rankings.
5. Fit baseline/expected-outcome estimates and player scores; inspect matchup and venue splits.
6. Run threshold, mismatch-weight, score-reconstruction, format, and match-bootstrap sensitivity checks. A credible top 10 should not depend on a few borderline balls or one match.
7. Generate the cumulative datasets, ordered lists, and report tables/charts; verify every report rank matches the Unstop selections.

## Research inputs and why they matter

- [cricWAR (Rafique et al., 2022)](https://www.stat.cmu.edu/cmsac/conference/2022/assets/pdf/HassanRafique.pdf) adjusts player value for venue, innings, bowling pace, and batting/bowling matchup, and uses resampling for uncertainty. It supports modelling context rather than handing out fixed venue points.
- [A pressure index for the team batting second in T20I cricket (2024)](https://journals.sagepub.com/doi/10.3233/JSA-240792) uses pre-ball required run rate and remaining resources. Our extras issue means this exact idea needs a reconstruction gate and sensitivity test.
- [Context-adjusted player evaluation for T20 cricket (2026)](https://arxiv.org/abs/2608.18020) illustrates runs above expectation, wicket value, and shrinkage for sparse contexts. Its much larger dataset is a reminder to keep our model simpler and pool thin matchup/venue cells.
- [ICC pitch and outfield monitoring process](https://images.icc-cricket.com/image/upload/prd/tv0xsnwchd1l8zgp0aba.pdf) explicitly treats conditions as varying by venue and pitch. Country alone is too coarse to label every stadium.
- [ICC team-ranking methodology](https://www.icc-cricket.com/rankings/about) and [ICC ranking update schedule](https://www.icc-cricket.com/news/when-are-the-rankings-updated) explain why the T20I opponent-strength input needs a dated pre-match value rather than today's table.
