# Cumulative cricket dataset (first build)

Built from the supplied CSV pack by the scripts in `scripts/`. The cumulative files are the base; later files contain pre-ball pressure, context estimates, and provisional rankings.

Run from the repository root with the project virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe scripts\run_pipeline.py
```

The scripts use only the Python standard library. They do not edit the source CSVs. Phase-by-phase methods and limitations are in `docs/`.

## Files and grain

| File | One row per | Purpose |
| --- | --- | --- |
| `player_match_cumulative.csv` | Match, player, team, role | Match metrics and running totals through that match date. `cum_` is across eligible IPL and T20I matches; `cum_format_` is within that match's format. |
| `player_series_summary.csv` | Competition, team, player, role | Metrics across eligible matches within each series, plus all-match and eligible-match counts. Includes every player who batted or bowled, but not unused squad members. |
| `player_cumulative_summary.csv` | Player, role, scope | Final totals over eligible matches. Scope is `ALL`, `IPL`, or `T20I`. |
| `venue_context.csv` | Venue ID, match format | Raw scoring and wicket aggregates over eligible matches. These are inputs to a later pooled venue adjustment, not a batting/bowling-friendly verdict. |
| `match_quality.csv` | Match | Eligibility, approximate innings totals, and score-reconstruction error where a declared run margin allows comparison. |
| `match_state.csv` | Eligible delivery | Pre-ball legal balls, wickets, approximate score and chase requirement. Large local intermediate, ignored by Git. |
| `pressure_delivery.csv` | Eligible delivery | Pre-ball pressure score and tier with a ±7-run chase sensitivity flag. Large local intermediate, ignored by Git. |
| `pressure_coverage.csv` | Player, role, format | Raw low/medium/high pressure exposure and unstable chase counts. |
| `team_strength.csv` | Eligible match | Pre-match rolling Elo ratings/ranks and the top-versus-bottom mismatch weight. |
| `venue_pre_match.csv` | Match, phase | Prior-only pooled venue scoring and wicket factors. |
| `delivery_context.csv` | Eligible delivery | Prior-only expected runs, dismissals, minimum bowling cost, wickets, and context factors. Large local intermediate, ignored by Git. |
| `context_calibration.csv` | Format, year, phase | Actual and expected outcome totals for calibration review. |
| `player_pressure_summary.csv` | Player, role | Pressure/baseline scores, exposure, bootstrap range, consistency, matchup and dismissal-mode splits. |
| `player_pressure_segments.csv` | Player, role, format or series | Descriptive pressure and baseline scores within IPL/T20I or one series. Thin series cells are not independently eligible rankings. |
| `rankings.csv` | Rank, role | Provisional ordered top-10 lists for batters and bowlers. |
| `ranking_sensitivity.csv` | Threshold, mismatch weight, player | Alternative point-estimate ranks and candidate counts. |
| `ranking_robustness.csv` | Scenario, role, rank | Top 20 conservative bootstrap ranks under stricter eligibility gates and 3/5/7-run wicket values. Baseline order is checked against `rankings.csv`. |

The source pack has venue IDs and countries but no venue names. The series table uses `comp_id` as its stable series key. Player identities use `player_id`; names are display labels.

## Eligibility and cumulative convention

Only innings 1 and 2 are processed; 38 third/fourth-innings super-over deliveries are excluded. A match is eligible for cumulative totals when it is IPL or T20I, is not abandoned or marked no-result, and has no revised-overs/target field or D/L/DLS result. Ineligible match rows remain in `player_match_cumulative.csv` with `analysis_eligible=0` and `exclusion_reason`; their `cum_` values stay at the prior eligible total. `player_series_summary.csv` reports their presence in `matches`, while its performance metrics count eligible matches only.

Rows are ordered by match date, match ID, player ID, and role. The cumulative value on a row includes the eligible match on that row. It is therefore an **as-of-after-match** total. Pressure or venue models needing a pre-match baseline must use the previous total, never the current row's total.

## Metric definitions

- `bat_runs` is the source `runs` value credited to the striker. `bat_balls_faced` excludes wides; no-balls count as balls faced. `bat_outs` follows `dismissed_player_id`, including non-striker run-outs when identified. `bat_zero_run_balls` means zero *batter* runs, which can include byes/leg-byes.
- `bat_pace_*` and `bat_spin_*` split by `pace_or_spin`. Pace/spin outs are attributed only when the dismissed player was on strike; a non-striker run-out remains in overall outs.
- `bowl_legal_balls` excludes wides and `Overstep` no-balls. `bowl_batter_runs_allowed` sums source batter runs across every delivered ball. It **excludes extras** and is not exact bowling economy. `bowl_zero_batter_run_legal_balls` can include byes/leg-byes and is not a strict scoreless-ball count.
- `bowl_wickets` credits only `Caught`, `Bowled`, `LBW`, `Stump`, and `Hit Wicket`. Run-outs, retire-outs, and obstructing-the-field dismissals are not bowler wickets. Mode fields partition credited wickets. `bowl_rhb_*` and `bowl_lhb_*` split by the striker's `batting_type`.
- `venue_context` reports batter runs and bowler wickets by format and pace/spin. Raw venue rates should not be used as direct player point multipliers; the plan calls for season/format/innings adjustments and pooling small venues toward country and global baselines.

`extras1_runs` is an extras-category code in this pack, and `extras_2_runs` is zero on nearly every delivery. No output presents exact full innings totals or exact required run rates. The pressure labels and ratings are model-derived, with uncertainty flags and dated team-strength proxies, not official ICC rankings. Details are in `docs/PHASE_1_MATCH_STATE.md` through `docs/PHASE_4_RANKINGS.md`.

## Build checks

The builder rejects duplicate `(match_id, innings, overid, over_ball_num)` delivery keys and unknown match IDs. It reconciles eligible batter runs, bowler-allowed batter runs, batter balls faced, and bowler legal balls from aggregated match rows against the source-delivery totals before writing output.
