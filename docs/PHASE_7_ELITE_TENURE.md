# Phase 7 — elite-opponent tenure and phase matchups

## Source and two distinct cohorts

The [ICC men's T20I batting table](https://www.icc-cricket.com/rankings/batting/mens/t20i) and [bowling table](https://www.icc-cricket.com/rankings/bowling/mens/t20i) dated **3 November 2026** supply a verified top-10 snapshot. `icc_t20i_snapshot.csv` records the ten names in each table, their official ranks (including ties), source links, and their IDs in the supplied data. The source site's `?at=` date parameter returned the current table for requested historical dates during this build. Therefore these names are used only as a **retrospective current-elite cohort** when describing earlier IPL and T20I matchups. They are not represented as historical ICC members.

For a time-at-top estimate, `elite_monthly_top10.csv` and `elite_tenure_rankings.csv` instead derive a **within-pack T20I proxy** from earlier supplied matches. This is not an ICC ranking. Each first-of-month snapshot starts after 180 days of warmup, looks back 365 days, and considers only T20I deliveries strictly before the snapshot. A player needs at least 120 batting/bowling balls across eight matches in that window. Their context-adjusted delivery impact is weighted by the existing mismatch factor, divided by `balls + 200`, and expressed per 100 balls. The top ten by this shrunk score in each role make the monthly table. The tenure ranking orders players by **number of top-10 months**, then by mean top-10 rank. It reports first/last month, best rank, and overlap with the current official ICC table. A month without appearances may still count while prior performances remain in the trailing-year window; this measures sustained estimated standing, not continuous play.

The supplied pack is a subset of world cricket, so neither the monthly proxy nor its tenure count estimates true historical ICC top-10 tenure. The 120-ball/eight-match rolling gate controls small windows; it is separate from the main ranking's **100 effective pressure balls in 20 pressure matches and 50 low-pressure balls**. The main ordered selections remain in `rankings.csv`.

## Powerplay and death-over matchups

`elite_phase_matchups.csv` scores each batter against a bowler in either elite cohort and each bowler against a batter in either cohort, separately for powerplay (overs 1–6) and death (16–20). For the historical proxy cohort, the opponent must be in the **latest monthly top ten strictly before that match** and already have **at least three prior top-10 months**. The current ICC cohort is retrospective by design. Both IPL and T20I deliveries can contribute to the matchup; ICC rankings themselves are T20I-only.

The score uses the same earlier-date contextual run, dismissal, cost, and wicket expectations and the same poor-score-match and ±7-run pressure-label stability exclusions as the primary rating. Batter impact is `runs - expected runs - 5 × (dismissal - expected dismissal)`. Bowler impact is `expected minimum cost - observed minimum cost + 5 × (credited wickets - expected wickets)`. The matchup score is `100 × weighted impact / (balls + 80)` and is shown only with **30 balls in five matches**. The table also shows balls, matches, batting strike rate, strict scoreless-dot share, minimum bowler cost, and credited wickets. These are all-ball phase comparisons, including low-pressure balls; the current pressure labels have little powerplay exposure. A positive score means better than the prior-only context expectation. It is descriptive and is not added to the main ranking, because the same outcomes already contribute to that ranking.

Illustrative supported results against the historical, tenure-filtered cohort:

| Player and role | Phase | Balls | Matches | Shrunk impact per 100 |
| --- | --- | ---: | ---: | ---: |
| Yashasvi Jaiswal, batting | Powerplay | 49 | 7 | +25.137 |
| Tim David, batting | Death | 63 | 12 | +32.090 |
| Jason Behrendorff, bowling | Powerplay | 46 | 8 | +20.795 |
| Patrick Cummins, bowling | Death | 38 | 10 | -3.437 |

These cells are too small to establish a general head-to-head ordering. In particular, a bowler can have excellent overall death-over pressure performance but no supported death-over sample against the elite cohort. Missing cells are missing evidence, not zero performance.

## Rebuild

`scripts/rank_elite_matchups.py` is included in `scripts/run_pipeline.py`. The ICC snapshot is pinned in code to its cited **3 November 2026** publication, so rebuilds do not silently substitute a later live table. To update it, recheck both ICC pages, update the dated names/ranks, and regenerate the files.
