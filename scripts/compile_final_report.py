"""Generate the final methodology report and dropdown order from final_rankings.csv."""

from __future__ import annotations

import csv
from pathlib import Path

from build_cumulative_dataset import DEFAULT_OUTPUT, ROOT

REPORT = ROOT / "docs" / "FINAL_SUBMISSION_REPORT.md"
DROPDOWNS = ROOT / "output" / "final_dropdown_order.txt"


def read(name: str) -> list[dict[str, str]]:
    with (DEFAULT_OUTPUT / name).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def selection_table(rows: list[dict[str, str]]) -> str:
    lines = [
        "| Rank | Player | Legacy rank | State rank | Rank sum | State balls / matches | Positive matches | State bootstrap 10th-90th |",
        "| ---: | --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in rows:
        interval = f"{float(row['state_bootstrap_p10']):.3f}-{float(row['state_bootstrap_p90']):.3f}"
        lines.append(
            f"| {row['rank']} | {row['player_name']} | {row['legacy_rank']} | {row['state_rank']} | "
            f"{row['rank_sum']} | {float(row['state_effective_balls']):.1f} / "
            f"{row['state_pressure_matches']} | {100*float(row['state_positive_match_share']):.1f}% | {interval} |"
        )
    return "\n".join(lines)


def main() -> None:
    ranked = read("final_rankings.csv")
    if len(ranked) != 20:
        raise ValueError("Final ranking must contain 20 players")
    batting = [row for row in ranked if row["role"] == "batting"]
    bowling = [row for row in ranked if row["role"] == "bowling"]
    if len(batting) != 10 or len(bowling) != 10:
        raise ValueError("Final ranking must contain 10 players per role")
    folds = [row for row in read("candidate_v2_backtest.csv") if row["gate"] == "final"]
    fold_lookup = {(row["test_year"], row["role"], row["method"]): row for row in folds}
    backtest_lines = [
        "| Test year | Role | Players | Legacy top-10 impact | State top-10 impact | Consensus top-10 impact |",
        "| ---: | --- | ---: | ---: | ---: | ---: |",
    ]
    for year in ("2025", "2026"):
        for role in ("batting", "bowling"):
            old = fold_lookup[(year, role, "old")]
            state = fold_lookup[(year, role, "v2")]
            consensus = fold_lookup[(year, role, "consensus")]
            backtest_lines.append(
                f"| {year} | {role.title()} | {old['players']} | "
                f"{float(old['top10_future_rate']):+.3f} | "
                f"{float(state['top10_future_rate']):+.3f} | "
                f"{float(consensus['top10_future_rate']):+.3f} |"
            )

    report = f"""# SupeRR Selector Season 2 - Round 1 final methodology

## Ordered dropdown selections

These are the **final selections in dropdown order**. Both lists come from the same 2022-2026 IPL and T20I analysis. We combine two pre-ball pressure models by adding each player's rank within the pool eligible under **both** models; the lowest rank sum wins. A smaller rank sum means stronger agreement, not cricket runs or an official rating. The state-model interval is a 10th-90th percentile range from 300 whole-match bootstrap draws of its runs-per-100-effective-ball score. It is **not** a confidence interval for the consensus rank.

### Batters

{selection_table(batting)}

### Bowlers

{selection_table(bowling)}

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

{chr(10).join(backtest_lines)}

The consensus gives the strongest batting top-10 impact in both final-gate checks. Bowling is mixed: the legacy list is stronger in 2025 and the state list in 2026, while consensus reduces dependence on either pressure rule. These are small, survival-selected cohorts, and the same years were used to inspect the candidate methods. The results support a robust compromise, not a claim of universal optimality.

Across year/format/role high-pressure death-over cells, the state correction reduces the ball-weighted mean absolute residual from **21.58 to 6.19 runs per 100 balls**. On verified held-out chases, the state pressure score improves alignment with a win-probability leverage diagnostic in 2025-2026 (AUC 0.756 versus 0.730), but is slightly lower in 2023-2024 (0.836 versus 0.844). That win-probability model misses its 0.08 calibration-error gate in six of eight year/format cells and is not used to rank players. Exact extras remain unavailable in 259 games; venue and matchup samples can be thin; T20I coverage is incomplete; and the five-run wicket conversion and pressure thresholds are modelling choices. The consensus partly guards against those choices but cannot remove their uncertainty.

## Reproduction and source attribution

Run `scripts/run_pipeline.py` from the repository root. It rebuilds both component rankings, `data/processed/final_rankings.csv`, and this Markdown report. Run `scripts/render_submission_report.py --final` to regenerate the uploadable PDF; the renderer verifies all 20 displayed names, ranks, and rank sums against the CSV. The score-quality audit and source attribution for the matched extras are in `data/external/README.md`. Credit: Cricsheet (cricsheet.org), whose transformed extras data is used under its attributed license. The supplied contest data provides the primary player and match records.
"""
    REPORT.write_text(report, encoding="utf-8")
    DROPDOWNS.parent.mkdir(parents=True, exist_ok=True)
    text = "SupeRR Selector Season 2 - final dropdown order\n\n"
    for heading, rows in (("Batters", batting), ("Bowlers", bowling)):
        text += heading + "\n"
        text += "\n".join(f"{row['rank']}. {row['player_name']}" for row in rows) + "\n\n"
    DROPDOWNS.write_text(text, encoding="utf-8")
    print(REPORT)
    print(DROPDOWNS)


if __name__ == "__main__":
    main()
