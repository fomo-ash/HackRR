# Phase 3 — pre-match team strength and contextual expectations

## Purpose

Set a fair expectation for a delivery before awarding above-expectation runs or wickets. Script: `scripts/build_context.py`. It writes `team_strength.csv`, `venue_pre_match.csv`, `delivery_context.csv`, and `context_calibration.csv`.

## Team strength and mismatch discount

Official historical ICC rankings are not in the supplied pack, so the current build uses a **rolling Elo proxy derived only from earlier supplied results**. Each IPL or T20I team starts at 1500; the update constant is 24. Matches on one date use the same pre-day snapshot, then all their changes are applied after that date. This avoids using a team's result later that day to assess an earlier match.

For each match, teams receive a pre-match rating and rank within IPL or T20I. A match has `mismatch_weight=0.75` if one team ranks in the top six, the other is IPL rank 7–10 or T20I rank 13+, the rating gap is at least 75, and both teams have at least five prior listed matches. Otherwise the weight is 1.00. **144 of 785** eligible matches receive the discount: 52 IPL and 92 T20I. This proxy is limited by the pack's incomplete international schedule and is **not an ICC ranking**. Replacing it with verified dated ICC snapshots is a later enhancement.

The match weight reduces player scoring points for a one-sided fixture. Contextual expectations also adjust for opponent performance, so the sensitivity output tests whether the extra discount over-penalizes those matches.

## Expected outcomes

The model reads eligible deliveries in match-date order. It predicts every match on a given date using only **earlier dates**, then updates its history. Its base cells are format, year, innings phase (powerplay 1–6, middle 7–15, death 16–20), pace/spin, and batter hand. Sparse cells shrink toward year-phase, all-years phase, and format averages. Initial priors are 1.20 batter runs per ball, 1.25 minimum bowler cost per delivery, 0.05 striker dismissals per faced ball, and 0.045 bowler wickets per delivery; the shrinkage pseudo-counts are 200–400 balls in the base hierarchy.

Venue scoring and wicket factors pool venue to country to format-phase history, with 300 prior balls for venue and 1,000 for country. Run factors are capped at 0.80–1.20 and wicket factors at 0.75–1.25. Opponent bowling and batting-team scoring factors use 500 prior balls and caps of 0.85–1.15. These numbers are documented design choices; they limit unstable extremes at thin venues. `venue_pre_match.csv` shows the prior venue factors for each match and phase.

The four predicted outcomes on `delivery_context.csv` are batter runs per faced ball, striker-dismissal probability, bowler minimum run cost per delivery, and bowler-credited wicket probability. Bowler cost is batter runs plus **one** for a wide or `Overstep` no-ball; it excludes unknown extra-run magnitudes and byes/leg-byes. Credited wicket types are caught, bowled, LBW, stumped, and hit wicket. The model also stores its factors and prior sample sizes for audit.

## Calibration and limitations

`context_calibration.csv` groups actual and predicted outcomes by format, year, and phase. Overall wicket counts track predictions closely, while some later batting seasons remain underpredicted. For example, IPL 2024 batter runs are **1.067×** predicted and T20I 2026 are **1.056×** predicted. Thus some late-season player residuals may receive too much credit. The year-phase baseline reduces, but does not eliminate, scoring-era drift. The model is deliberately simple for 785 eligible matches; it is a reproducible starting point, not a fully calibrated win-probability model.

Venue and opponent factors are drawn from earlier matches, but small countries, grounds, and teams still have uncertain estimates. The CSV pack has venue IDs and countries, not ground names or pitch/weather observations. A country-level rate is a pooling prior, not a statement that all its pitches play alike.
