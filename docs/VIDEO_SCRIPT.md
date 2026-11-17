# Video script: how we selected players for pressure moments

**Target length:** about four minutes at a natural pace. The bracketed text is for visuals, not narration.

## 0:00–0:30 — The question

“A top scorer is not automatically the best player for a tense chase or a collapsing innings. Our question was: *who adds the most value when the match state puts real pressure on a player?* We built a shortlist of ten batters and ten bowlers for SupeRR Selector Season 2 by measuring performance against what each ball demanded, and by checking that the answer survives two reasonable definitions of pressure.”

[Show the dashboard hero, then the twenty-player ranking board.]

## 0:30–1:05 — Prepare the evidence

“We started with the supplied 2022–2026 IPL and T20I records. After excluding abandoned or no-result games, other competitions, revised targets, and super overs, we analysed 785 matches and 187,509 first- or second-innings deliveries. The pack did not record exact extras. We verified 526 games delivery by delivery against Cricsheet, and treated the remaining games cautiously: uncertain chase deliveries and games with large score-reconstruction errors were excluded from the affected calculations.”

[Show the four headline metrics and a small ‘526 verified / 259 unverified’ split.]

## 1:05–1:40 — Define pressure before the ball

“For every delivery, we describe the state *before* it happens: the innings phase, wickets already lost, balls remaining, the chase requirement, and whether it is a knockout. Our original pressure model emphasises late overs, wickets down, and demanding but still contestable chases. A second, state-aware model also recognises early collapses and close middle-over chases. Both classify deliveries as low, medium, or high pressure. Medium pressure gets half weight; high pressure gets full weight.”

[Show the method cards and the model-agreement scatter plot.]

## 1:40–2:20 — Measure value fairly

“A boundary against an easy ball should not count the same as a boundary in a difficult state. So we estimate the runs and wicket probability expected from comparable situations, using only matches from *earlier dates*. We pool thin format, phase, venue, opponent, and matchup samples toward broader averages. For a batter, value is runs above expectation, with a five-run adjustment for being dismissed. For a bowler, value is expected run cost minus observed minimum run cost, plus a five-run adjustment for credited wickets. Run-outs are never credited to the bowler. We also reduce value weight in clear top-six-versus-bottom fixtures identified with a prior-results Elo proxy.”

[Show ‘Observed contribution − earlier-date expectation = ball value’.]

## 2:20–3:05 — Prevent a lucky sample from winning

“We aggregate pressure-ball values in two ways. The original model blends shrunk pressure performance with uplift over that player's low-pressure rate. The state model first removes league-wide bias for similar pressure states, then shrinks the pressure impact per 100 effective balls. In both methods we resample *whole matches*, and make the score conservative by averaging its point estimate with the bootstrap tenth percentile. A player must have at least 100 effective pressure balls across 20 pressure matches, plus 50 low-pressure balls, **in each model**. That leaves a common pool of 58 batters and 83 bowlers.”

[Show sample gates, then ‘58 batters / 83 bowlers eligible’.]

## 3:05–3:35 — Make the final decision

“Within each role, we rank that common pool under both models. We add the two ranks, and the lowest sum wins. Ties go to the better worst rank, then the higher state-model conservative score. Rinku Singh ranks second under both batting methods; Sunil Narine ranks first under both bowling methods. We show pressure-match positive share and bootstrap ranges alongside the ranks, but positive share is evidence, not a hidden third ranking weight.”

[Click Rinku and Sunil on the dashboard. Show the two ranks and selection reasoning.]

## 3:35–4:15 — Check and qualify the claim

“The state correction cut mean absolute high-pressure death-over bias from 21.58 to 6.19 runs per 100 balls. In later-year checks, the consensus batting top ten had the strongest measured impact in both 2025 and 2026. Bowling was mixed: the original method led in 2025, the state method in 2026. These are small, survival-selected cohorts, and the same years helped us review the methods. Exact extras remain unavailable in 259 eligible games, and T20I coverage is incomplete. So this is an evidence-led, transparent shortlist—not a claim that a single ranking is certain or universally optimal.”

[Show the filtered later-impact chart and the limitations box. End on the final twenty.]

## One-sentence answer for questions

“We scored each ball against an earlier-date expectation, weighted it by two pre-ball pressure definitions, required enough match exposure, and selected the players whose conservative ranks agreed most strongly across both models.”
