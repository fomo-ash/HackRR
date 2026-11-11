# Phase 2 — pressure labels and threshold checks

## Purpose

Label each delivery from information available before it occurs. Script: `scripts/label_pressure.py`. Inputs are Phase 1's `match_state.csv` and `match_quality.csv`; outputs are `pressure_delivery.csv` and `pressure_coverage.csv`.

## Transparent starting index

| Component | Points |
| --- | --- |
| Overs 1–6 / 7–15 / 16–18 / 19–20 | 0 / 10 / 24 / 34 |
| Wickets lost 0–2 / 3–4 / 5–6 / 7+ | 0 / 7 / 14 / 20 |
| Second innings: approximate required runs per remaining legal ball below 0.8 | 0 |
| Second innings: rate 0.8–2.3 with 61+ / 37–60 / 1–36 balls left | 5 / 12 / 22 |
| Second innings: rate above 2.3 with 37+ / 1–36 balls left | 7 / 15 |
| Second innings: rate at least 1.35 with four or fewer wickets left | +8 |
| Knockout match | +10 |

The score is the sum, capped at 100. **Low** is below 30, **medium** is 30–49, and **high** is 50 or above. A nearly impossible chase receives fewer chase points than a still-contestable tight chase: the latter offers more opportunity to change the match. First-innings pressure depends on late phase, wickets, and knockout stakes because no chase target yet exists. This index is a contest-specific modelling choice, not a learned law of cricket.

## Score uncertainty gate

For each second-innings delivery, the script recomputes its tier with runs required shifted down and up by **7**, the Phase 1 audit's 95th-percentile margin error. If either alternative changes the tier, `tier_stable_with_7_run_shift=0`. There are **4,776** such deliveries. The primary score skips them; the CSV retains them for review. First-innings labels are unaffected by this chase-score check.

| Tier | Deliveries | Stable under ±7 runs |
| --- | ---: | ---: |
| Low | 137,102 | 136,533 |
| Medium | 31,706 | 29,582 |
| High | 18,701 | 16,618 |

`pressure_coverage.csv` reports each player-role-format's low, medium, and high *raw* ball counts and matches. Batting counts exclude wides; bowling counts use legal balls. Its counts include unstable chase labels, so Phase 4's scored exposure will be lower.

## Threshold sensitivity

The primary high cutoff is 50. Phase 4 recalculates rankings at high cutoffs **45, 50, and 55**, each with medium starting 20 points lower. It also tests mismatch weights 0.60, 0.75, and 0.90. The top-10 lists, especially batting, are sensitive to the pressure cutoff; see `docs/PHASE_4_RANKINGS.md`. These thresholds should be revisited before an external submission if a stronger pressure definition or exact score data becomes available.
