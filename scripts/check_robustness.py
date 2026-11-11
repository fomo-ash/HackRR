"""Check ranking stability under wicket values and stricter sample gates."""

from __future__ import annotations

import csv
from collections import Counter, defaultdict

from build_cumulative_dataset import DEFAULT_OUTPUT
from score_players import add_score, bootstrap, score


SCENARIOS = (
    ("baseline", 5.0, 100.0, 20, 50),
    ("legacy_40_8_30", 5.0, 40.0, 8, 30),
    ("gate_80_20_50", 5.0, 80.0, 20, 50),
    ("gate_120_30_60", 5.0, 120.0, 30, 60),
    ("wicket_value_3", 3.0, 100.0, 20, 50),
    ("wicket_value_7", 7.0, 100.0, 20, 50),
)
FIELDS = (
    "scenario", "wicket_run_value", "min_pressure_effective_balls",
    "min_pressure_matches", "min_low_balls", "role", "eligible_candidates",
    "rank", "player_id", "player_name", "conservative_score",
    "shrunk_score", "bootstrap_p10", "bootstrap_p90",
    "pressure_effective_balls", "pressure_matches", "low_balls",
    "in_baseline_top_10",
)


def main() -> None:
    with (DEFAULT_OUTPUT / "match_quality.csv").open(newline="", encoding="utf-8") as handle:
        poor_matches = {
            row["match_id"] for row in csv.DictReader(handle)
            if row["approx_margin_error"] and int(row["approx_margin_error"]) > 7
        }
    groups: dict[tuple[str, str, float], dict[str, Counter]] = defaultdict(
        lambda: defaultdict(Counter)
    )
    names: dict[tuple[str, str], str] = {}
    with (DEFAULT_OUTPUT / "delivery_context.csv").open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if (row["match_id"] in poor_matches
                    or row["tier_stable_with_7_run_shift"] != "1"):
                continue
            runs = int(row["runs"])
            for role, pid, name, unit, run_residual, wicket_residual in (
                (
                    "batting", row["striker_id"], row["striker_name"],
                    int(row["extras_type"] != "wide"),
                    runs - float(row["expected_bat_runs"]),
                    -(int(row["striker_out"]) - float(row["expected_bat_out"])),
                ),
                (
                    "bowling", row["bowler_id"], row["bowler_name"],
                    int(row["is_legal"]),
                    float(row["expected_bowl_cost"]) - int(row["observed_bowl_cost"]),
                    int(row["bowler_wicket"]) - float(row["expected_bowl_wicket"]),
                ),
            ):
                if role == "batting" and not unit:
                    continue
                names[(role, pid)] = name
                for wicket_value in (3.0, 5.0, 7.0):
                    add_score(
                        groups[(role, pid, wicket_value)][row["match_id"]],
                        run_residual + wicket_value * wicket_residual,
                        unit, int(row["pressure_score"]), 50,
                        float(row["mismatch_weight"]),
                    )

    aggregates = {}
    for key, matches in groups.items():
        total = Counter()
        for stats in matches.values():
            total.update(stats)
        pressure_matches = sum(
            stats["pressure_effective_balls"] > 0 for stats in matches.values()
        )
        aggregates[key] = (total, pressure_matches, list(matches.values()))

    bootstrap_cache: dict[tuple[str, str, float], tuple[float, float]] = {}
    scenario_rankings = {}
    for label, wicket_value, min_balls, min_matches, min_low in SCENARIOS:
        for role in ("batting", "bowling"):
            candidates = []
            for (candidate_role, pid, value), (total, pressure_matches, match_list) in aggregates.items():
                if candidate_role != role or value != wicket_value:
                    continue
                if (total["pressure_effective_balls"] < min_balls
                        or pressure_matches < min_matches
                        or total["low_balls"] < min_low):
                    continue
                key = (role, pid, value)
                if key not in bootstrap_cache:
                    bootstrap_cache[key] = bootstrap(match_list, pid, role)
                p10, p90 = bootstrap_cache[key]
                points = score(total)[3]
                candidates.append((pid, (points + p10) / 2, points, p10,
                                   p90, total, pressure_matches))
            candidates.sort(key=lambda item: (-item[1], int(item[0])))
            scenario_rankings[(label, role)] = candidates
            print(f"{label} {role}: {len(candidates)} candidates")

    baseline_ids = {
        role: {row[0] for row in scenario_rankings[("baseline", role)][:10]}
        for role in ("batting", "bowling")
    }
    with (DEFAULT_OUTPUT / "rankings.csv").open(newline="", encoding="utf-8") as handle:
        published = list(csv.DictReader(handle))
    for role in ("batting", "bowling"):
        expected = [row["player_id"] for row in published if row["role"] == role]
        actual = [row[0] for row in scenario_rankings[("baseline", role)][:10]]
        if actual != expected:
            raise AssertionError(f"Baseline {role} order differs from rankings.csv")

    output = DEFAULT_OUTPUT / "ranking_robustness.csv"
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for label, wicket_value, min_balls, min_matches, min_low in SCENARIOS:
            for role in ("batting", "bowling"):
                candidates = scenario_rankings[(label, role)]
                top_ids = {row[0] for row in candidates[:10]}
                print(
                    f"{label} {role}: {len(top_ids & baseline_ids[role])}/10 "
                    "baseline names retained"
                )
                for rank, (pid, conservative, points, p10, p90, total,
                           pressure_matches) in enumerate(candidates[:20], 1):
                    writer.writerow({
                        "scenario": label, "wicket_run_value": wicket_value,
                        "min_pressure_effective_balls": min_balls,
                        "min_pressure_matches": min_matches,
                        "min_low_balls": min_low, "role": role,
                        "eligible_candidates": len(candidates), "rank": rank,
                        "player_id": pid, "player_name": names[(role, pid)],
                        "conservative_score": round(conservative, 3),
                        "shrunk_score": round(points, 3),
                        "bootstrap_p10": round(p10, 3),
                        "bootstrap_p90": round(p90, 3),
                        "pressure_effective_balls": total["pressure_effective_balls"],
                        "pressure_matches": pressure_matches,
                        "low_balls": total["low_balls"],
                        "in_baseline_top_10": int(pid in baseline_ids[role]),
                    })
    print(f"Wrote {output}")


if __name__ == "__main__":
    main()
