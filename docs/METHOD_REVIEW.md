# Method review before submission

**Historical audit:** The final jointly eligible consensus and upload methodology are now in [the final report](FINAL_SUBMISSION_REPORT.md). The findings below motivated the state-model component.

The current ranked PDF is a reproducible **candidate**, not a validated best method. This review uses the existing `delivery_context.csv`, the same score-quality exclusions as `score_players.py`, and two read-only audit scripts. It does not change `rankings.csv` or the upload PDF.

[Candidate v2](CANDIDATE_V2.md) implements exact verified chase scores, a broader pressure rule, prior-date pressure-state correction, and chronological ranking checks. Its state calibration is better, while its standalone player backtest is mixed. The final report combines both component rankings among jointly eligible players.

Run from the repository root:

```powershell
.\.venv\Scripts\python.exe scripts\audit_method.py
.\.venv\Scripts\python.exe scripts\audit_centered_method.py
```

## What the audit found

1. **The pressure rule is almost entirely about later overs.** After the scoring exclusions, it labels 16,255 deliveries high pressure: 15,210 in death overs and 1,045 in middle overs; none in the powerplay. Only one powerplay delivery receives even a medium label. This is a narrow interpretation of pressure, especially for early collapses or decisive powerplay contests.
2. **The contextual expectation is not calibrated within pressure states.** In high-pressure death overs, the average batting residual is **-21.04 runs per 100 faced balls** over 14,363 balls; the bowling residual is **+20.61 per 100 legal balls** over 14,301 balls. The same directional gap appears in each year from 2022 through 2026. It can reward or penalize players for their mix of pressure states before isolating individual performance. The expectation model conditions on innings phase but not the current chase requirement, wickets already lost, or pressure tier.
3. **The rating partly measures general skill.** `score_players.py` computes `adjusted = low_rate + shrink * (pressure_rate - low_rate)` and `points = 0.65 * adjusted + 0.35 * uplift`. Algebraically, `points = 0.65 * low_rate + shrink * (pressure_rate - low_rate)`. This is a valid blend if general skill is part of the goal, but the challenge emphasizes performance *relative to usual levels*. Match-to-match positive share is reported but does not enter the ranking. Rinku Singh's current rank 2 comes with a 49.1% positive pressure-match share, which illustrates that high aggregate impact and repeatability can disagree.
4. **The current rank score has weak out-of-time evidence.** An exploratory split trains on 2022-2024 and checks 2025-2026 among players with at least 40 effective pressure balls, eight pressure matches, and 20 low balls in training, plus 20 effective pressure balls and five matches later. There are 61 batters and 77 bowlers. Spearman correlation between the training point score and later pressure residual rate is **0.189 for batting** and **0.052 for bowling**. These are single-split diagnostics, not definitive estimates of future performance.

## A first alternative did not win

`audit_centered_method.py` subtracts a pressure-state residual correction learned from **earlier dates only**, within role, IPL/T20I, innings phase, innings, and pressure tier, shrunk with 400 prior balls. It retains the current eligibility, score formula, and bootstrap ordering. It replaces Glenn Phillips with Marcus Stoinis in the batting top 10, and Shaheen Afridi with Kuldeep Yadav in the bowling top 10.

On the same 2022-2024 to 2025-2026 split, rank correlation with later *centered* pressure impact changes from **0.164 to 0.151** for batters and **0.072 to 0.112** for bowlers. The mean later centered impact of the training top 10 is lower for the corrected method in both roles: batting **19.40 versus 23.28**, bowling **14.75 versus 17.12** runs per 100 effective balls. This simple correction addresses the state calibration gap but has not earned promotion to the submitted ranking.

## Decision before submission

Build and compare a pressure-aware expectation using pre-ball balls remaining, wickets lost, required rate, innings, and match context, with exact chase scores where verified. Use past seasons to train and later seasons to evaluate. Check residual calibration within pressure states, then compare candidate ranking rules on later-match pressure impact **and** the share of positive pressure matches. Use several chronological folds, bootstrap matches for uncertainty, and record roster changes under pressure and eligibility thresholds. Choose the final scoring rule from those results, regenerate the report and PDF, and only then enter the Unstop selections.

The 526 verified-score matches are useful for an exact-score sensitivity check. They are not a random full replacement for the 785-match pack, and the current exact-score win-probability model misses its own calibration gate in six of eight held-out year/format cells. It should remain diagnostic until it passes that gate.
