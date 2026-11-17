"""Generate the final methodology report and dropdown order from final_rankings.csv."""

from __future__ import annotations

import csv
from pathlib import Path

from build_cumulative_dataset import DEFAULT_OUTPUT, ROOT

REPORT = ROOT / "docs" / "FINAL_SUBMISSION_REPORT.md"
TEMPLATE = ROOT / "docs" / "FINAL_SUBMISSION_REPORT.template.md"
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


def worked_example(final: dict[str, str], legacy: dict[str, str],
                   state: dict[str, str]) -> str:
    """Explain one final player's arithmetic using generated component results."""
    name, role = final["player_name"], final["role"]
    surname = name.split()[-1]
    label = "batters" if role == "batting" else "bowlers"
    exposure_label = "low-pressure balls" if role == "batting" else "low-pressure legal balls"
    old_e = float(legacy["pressure_effective_balls"])
    old_rate = float(legacy["pressure_rate_per_100"])
    old_low = float(legacy["low_rate_per_100"])
    adjusted = old_low + old_e / (old_e + 80) * (old_rate - old_low)
    uplift = adjusted - old_low
    new_e = float(state["pressure_effective_balls"])
    new_rate = float(state["pressure_rate_per_100"])
    new_point = float(state["shrunk_pressure_score"])
    old_rank, new_rank = int(final["legacy_rank"]), int(final["state_rank"])
    extra = (
        f" The state component file ranks him {state['rank']}th in its broader eligible pool; "
        f"the consensus reranks only the common pool. The {abs(old_rank - new_rank)}-place "
        "model gap signals sensitivity to the pressure definition and correction, "
        "without isolating which change caused it."
        if state["rank"] != final["state_rank"] else
        " The close component ranks support his selection across both pressure definitions."
    )
    return (
        f"Under the legacy rule, {surname} has {old_e:.1f} effective pressure balls "
        f"in {legacy['pressure_matches']} pressure matches and {int(legacy['low_balls']):,} "
        f"{exposure_label}. His pressure rate is {old_rate:+.3f} and low-pressure "
        f"rate is {old_low:+.3f} per 100 balls. Shrinking the difference by "
        f"`{old_e:g} / ({old_e:g} + 80)` gives an adjusted pressure rate of "
        f"about {adjusted:+.3f} and uplift of {uplift:+.3f}. The 65/35 blend "
        f"gives a {float(legacy['shrunk_score']):+.3f} point score. Averaging it "
        f"with the match-bootstrap 10th percentile of {float(legacy['bootstrap_p10']):+.3f} "
        f"gives a **{float(legacy['conservative_score']):+.3f} conservative score**, "
        f"ranked {old_rank} in the common pool of {label}.\n\n"
        f"Under the state rule, he has {new_e:.1f} effective pressure balls in "
        f"{state['pressure_matches']} pressure matches. His corrected pressure rate "
        f"is {new_rate:+.3f} per 100 effective balls; "
        f"`{new_rate:.3f} x {new_e:g} / ({new_e:g} + 80)` gives a "
        f"{new_point:+.3f} point score. Averaging it with the "
        f"{float(state['bootstrap_p10']):+.3f} bootstrap 10th percentile gives a "
        f"**{float(state['conservative_score']):+.3f} conservative score**. "
        f"His state rank is {new_rank} in the common pool, so "
        f"`{old_rank} + {new_rank} = {final['rank_sum']}` places him "
        f"at **final {role} rank {final['rank']}**. His state positive-match "
        f"share is {100*float(state['positive_match_share']):.1f}%. The state-model "
        f"10th-90th impact interval is {float(state['bootstrap_p10']):+.3f} "
        f"to {float(state['bootstrap_p90']):+.3f} per 100 effective balls."
        + extra
    )


def fill(template: str, key: str, value: str) -> str:
    marker = "{{" + key + "}}"
    if template.count(marker) != 1:
        raise ValueError(f"Expected one {marker} in report template")
    return template.replace(marker, value)


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

    legacy_summary = {(row["role"], row["player_id"]): row
                      for row in read("player_pressure_summary.csv")}
    state_summary = {(row["role"], row["player_id"]): row
                     for row in read("candidate_v2_player_summary.csv")}
    final_by_name = {row["player_name"]: row for row in ranked}

    report = TEMPLATE.read_text(encoding="utf-8")
    for key, value in (
        ("BATTERS_TABLE", selection_table(batting)),
        ("BOWLERS_TABLE", selection_table(bowling)),
        ("BACKTEST_TABLE", "\n".join(backtest_lines)),
    ):
        report = fill(report, key, value)
    for name, key in (("Virat Kohli", "VIRAT_EXAMPLE"),
                      ("Jasprit Bumrah", "BUMRAH_EXAMPLE")):
        player = final_by_name[name]
        player_key = player["role"], player["player_id"]
        report = fill(report, key, worked_example(
            player, legacy_summary[player_key], state_summary[player_key]
        ))
    if "{{" in report:
        raise ValueError("Unfilled report template marker")
    REPORT.write_text(report, encoding="utf-8")
    DROPDOWNS.parent.mkdir(parents=True, exist_ok=True)
    text = "SupeRR Selector Season 2 - final dropdown order\n\n"
    for heading, rows in (("Batters", batting), ("Bowlers", bowling)):
        text += heading + "\n"
        text += "\n".join(f"{row['rank']}. {row['player_name']}" for row in rows) + "\n\n"
    DROPDOWNS.write_text(text.rstrip() + "\n", encoding="utf-8")
    print(REPORT)
    print(DROPDOWNS)


if __name__ == "__main__":
    main()
