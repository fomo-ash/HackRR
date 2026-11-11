# Phase 1 — pre-delivery match state and score audit

## Purpose

Create a reproducible state for every eligible delivery without treating the current ball's result as information available before that ball. Script: `scripts/build_match_state.py`.

## Inputs and exclusions

The script joins `ball_by_ball.csv` to `matches.csv` and `competitions.csv` by IDs. It keeps IPL and T20I matches with no abandonment/no-result or revised/D/L/DLS target. Of 883 listed matches, **785** meet those rules. Exclusions are 40 abandoned/no-result, 30 other T20, and 28 revised matches. It uses innings 1 and 2; super-over innings 3 and 4 are outside the state dataset. The output `data/processed/match_state.csv` has **187,509** rows.

The key is `(match_id, innings, overid, over_ball_num)`. `legal_before`, `wickets_before`, `bat_runs_before`, and `extra_events_before` describe the innings immediately **before** the delivery. Wides and `Overstep` no-balls do not consume a legal ball. `balls_remaining` is `120 - legal_before`, capped at zero. The second-innings approximate target is `first_approx_total + 1`.

## Extras and score quality

The CSV encodes a missing extras type as the literal text `None`. `extras1_runs` is an extras-category code, not extra runs. The builder therefore uses **one run per extras event** only as a provisional score reconstruction. It does not claim this equals the scorecard total. This approximation cannot reliably identify a close chase near a threshold.

`match_quality.csv` stores batter runs, extras-event counts, approximate totals, declared run margins, and errors. Across **382 eligible matches decided by runs** with a comparable declared margin, the absolute reconstruction error has median **1 run**, 95th percentile **7 runs**, and maximum **11 runs**. The later scoring phase excludes the **13** audited matches above 7 runs of error. The ±7-run chase sensitivity check in Phase 2 is empirical; it is not a mathematical upper bound on score error.

## Checks and limitations

`scripts/validate_pipeline.py` recomputes pre-ball legal balls, wickets, runs, extras events, remaining balls, and targets in delivery order, then checks all output keys. Wicket counts follow `is_wicket`, including non-bowler dismissals, because they reduce batting resources. Exact extras, revised targets, and super-over pressure need separate data or handling before they can enter the primary score.

## Next handoff

`match_state.csv` feeds Phase 2. `match_quality.csv` also feeds the score-quality gate in Phase 4.
