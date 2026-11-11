# Phase 6 — innings phase, country conditions, and pressure portability

## Purpose

`scripts/profile_context.py` makes the existing context adjustment visible. It reports separate powerplay (overs 1–6), middle (7–15), and death (16–20) scores, plus country and country-condition performance. It adds a **pressure portability** diagnostic: whether a player's above-expectation pressure impact appears across several supported types of situation. The submitted top 10 still uses the Phase 4 score; the new profiles are evidence and do not award a second country bonus.

## Prior-only country conditions

Phase 3 already pools venue scoring and wicket rates toward country and format/phase history. Its delivery context now exposes the **country run factor** and **country wicket factor** separately. Both compare the country estimate with the corresponding format/year/phase baseline and use only earlier dates. The country estimate has a 1,000-ball or 1,000-delivery prior, so sparse countries remain close to the baseline. These factors vary with format, phase, and date; no country receives a permanent label.

`profile_context.py` calls a state *run-suppressing* if its prior country run factor is at most 0.97, and *high-scoring* if it is at least 1.03. It calls wickets *scarce* below 0.97 and *common* above 1.03. Each label also requires at least **500 prior country batter balls and 500 prior deliveries** for that format and phase. Other states are `typical` or `insufficient_prior`. These thresholds define descriptive groups, not extra points. A wicket taken where wickets were already common has a higher expected-wicket benchmark; a batter scoring in a run-suppressing setting has a lower expected-runs benchmark. Venue, opponent, bowling type, and batter hand remain in the delivery expectation.

`player_country_scores.csv` provides country-by-format rows with observed and expected runs/wickets, pressure exposure, mean prior factors, and how many effective balls carried each condition label. `player_country_condition_scores.csv` pools condition labels across countries on two separate axes, run environment and wicket environment. Rows from the two axes describe the same deliveries and must **not** be added together.

Examples from the scored medium/high-pressure deliveries:

| Player | Country/format | Prior country factor | Observed versus expected | Effective pressure balls |
| --- | --- | ---: | --- | ---: |
| Rinku Singh, batting | Zimbabwe, T20I | Run factor 0.963 | 79 batter runs versus 54.209 expected | 20.0 across 5 matches |
| Tim Southee, bowling | New Zealand, T20I | Wicket factor 1.055 | 14 credited wickets versus 9.898 expected | 97.0 across 13 matches |

These are phase- and date-weighted country summaries, not claims that every Zimbabwe or New Zealand ground always plays the same way. The raw outcomes are counted on all medium/high deliveries; the effective-ball denominator gives medium deliveries half weight. The main impact score also discounts the predefined mismatched fixtures and values wickets at five runs, so it is not a direct subtraction of the displayed raw totals.

## Powerplay and other phase scores

`player_phase_scores.csv` includes `ALL`, `IPL`, and `T20I` rows for each player and role, plus an `ALL/all_phases` total. The **all-ball phase score** is context-adjusted impact per 100 legal/faced balls, shrunk toward zero by `balls / (balls + 80)`. It is displayed only after 100 balls in that phase. The file also retains a separate pressure residual and usual-performance comparison when that phase has pressure exposure. This distinction matters: the current pressure rule yields almost no weighted powerplay exposure for the ranked players. Calling their all-ball powerplay score a pressure score would be misleading.

Selected all-ball phase scores, with ball counts in parentheses:

| Player | Powerplay | Middle | Death |
| --- | ---: | ---: | ---: |
| Virat Kohli, batting | +21.765 (1,110) | +7.856 (1,074) | +35.766 (207) |
| Suryakumar Yadav, batting | +8.801 (608) | +37.123 (1,668) | +44.005 (294) |
| Jasprit Bumrah, bowling | +9.250 (703) | +18.717 (341) | +44.669 (482) |
| Sunil Narine, bowling | -0.145 (198) | +17.605 (1,044) | +52.873 (192) |

Positive values mean better than the pre-match contextual expectation in that phase. Bowling values combine minimum run cost and credited wickets; exact extras are unavailable. These phase scores are **not** additional pressure points and do not make a specialist's unplayed phase count as a failure.

## Strike rate, dot balls, and pressure created

`player_dot_pressure.csv` gives each player's overall and medium/high-pressure batting strike rate, batter zero-run percentage, and strict scoreless-dot percentage. Phase and country tables carry the same fields. **Strike rate** is 100 times batter runs divided by faced balls, excluding wides. A **batter zero-run ball** has no personal runs; a bye, leg-bye, or no-ball may still move the team score, so this is a personal-scoring measure. A **strict scoreless dot** is a legal delivery with zero batter runs and no extras event. For a bowler, strict dots divided by legal balls give the dot percentage that can actually constrain the batting side's score.

Among the ranked players, Shreyas Iyer has an overall strike rate of **152.74** and a **29.70%** batter zero-run share; on medium/high-pressure balls his strike rate is **212.64** and strict scoreless-dot share **19.70%**. Abrar Ahmed has **42.00%** strict scoreless dots overall and **46.15%** on medium/high-pressure legal balls. These are descriptive raw rates; phase, opposition, venue, and batting hand still affect the expected outcome used in the primary score.

For a strict scoreless dot in a second-innings chase with at least two balls remaining, we calculate `required / (balls remaining - 1) - required / balls remaining` from the **pre-ball approximate** requirement. This is the increase in required runs per remaining ball caused by spending one ball without scoring. The same event is recorded as pressure absorbed by the striker and pressure generated by the bowler. The output shows dot counts, the sum and median of these changes, and the sum per 100 chase balls. Near the end, the sum can be dominated by a few deliveries, so the median and count should be read alongside it. This measure is unavailable in the first innings and inherits the source pack's extras uncertainty. It is **not** added to the main player rating because scoreless balls already influence batter runs and bowling cost.

## Unique diagnostic: pressure portability

`player_portability.csv` tests up to seven contexts: three innings phases, two bowling-style or batter-hand matchups, plus two conditions adverse to the player's role. For a batter those are run-suppressing and wickets-common states; for a bowler they are high-scoring and wickets-scarce states. A cell is supported only with **20 effective pressure balls in at least five matches**. A positive cell has positive context-adjusted pressure impact per 100 effective balls. The diagnostic is `(positive supported cells + 1) / (supported cells + 2) × 100`, shown only for at least three supported cells. It also reports the number of supported cells and the weakest supported cell, so a high score from narrow coverage is visible.

Shreyas Iyer and Jasprit Bumrah each score **87.5/100 across six supported contexts**; Rinku Singh scores **62.5/100 across six**. These values summarize the *breadth* of above-expectation pressure results, not another estimate of total runs or wickets. The contexts overlap, so the portability score is an explanatory diagnostic and is not added to the primary ranking. Its thresholds and two-cell prior are stated explicitly rather than tuned to familiar names.

## Reproducibility checks

The profiling script applies the same ±7-run label-stability and poor-score-match exclusions as Phase 4. `scripts/validate_pipeline.py` confirms that all-format phase rows, country rows, one condition axis, and the overall dot table reconcile to the primary player summary's pressure balls, pressure impact, and all-ball exposure. The five profile CSVs are compact and versioned.
