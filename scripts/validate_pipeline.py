"""Validate the linked phase outputs and their main data invariants."""

from __future__ import annotations

import csv
from collections import Counter, defaultdict

from build_cumulative_dataset import DEFAULT_OUTPUT
from build_match_state import has_extra
from label_pressure import pressure_parts, tier
from build_win_probability import LEVERAGE_THRESHOLD


def read(name: str) -> list[dict[str, str]]:
    with (DEFAULT_OUTPUT / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def key(row: dict[str, str]) -> tuple[str, str, str, str]:
    return row["match_id"], row["innings"], row["overid"], row["over_ball_num"]


def main() -> None:
    quality = {row["match_id"]: row for row in read("match_quality.csv")}
    teams = {row["match_id"]: row for row in read("team_strength.csv")}
    assert len(teams) == sum(row["eligible"] == "1" for row in quality.values())

    innings_state: dict[tuple[str, str], Counter] = defaultdict(Counter)
    state_keys = set()
    with (DEFAULT_OUTPUT / "match_state.csv").open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            state_keys.add(key(row))
            assert quality[row["match_id"]]["eligible"] == "1"
            current = innings_state[(row["match_id"], row["innings"])]
            assert int(row["legal_before"]) == current["legal"]
            assert int(row["wickets_before"]) == current["wickets"]
            assert int(row["bat_runs_before"]) == current["bat_runs"]
            assert int(row["extra_events_before"]) == current["extras"]
            assert int(row["approx_score_before"]) == current["bat_runs"] + current["extras"]
            assert int(row["balls_remaining"]) == max(0, 120 - current["legal"])
            if row["innings"] == "2":
                target = int(quality[row["match_id"]]["first_approx_total"]) + 1
                assert int(row["approx_target"]) == target
                assert int(row["runs_required_approx"]) == max(0, target - int(row["approx_score_before"]))
            current["legal"] += int(row["is_legal"])
            current["wickets"] += row["is_wicket"].lower() == "true"
            current["bat_runs"] += int(row["runs"])
            current["extras"] += has_extra(row["extras_type"])
    assert len(state_keys) == 187509

    unstable = 0
    pressure_keys = set()
    with (DEFAULT_OUTPUT / "pressure_delivery.csv").open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            pressure_keys.add(key(row))
            expected_score = min(100, sum(pressure_parts(row)))
            assert int(row["pressure_score"]) == expected_score
            assert row["pressure_tier"] == tier(expected_score)
            unstable += row["tier_stable_with_7_run_shift"] == "0"
    assert pressure_keys == state_keys
    del pressure_keys
    assert unstable == 4776

    context_keys = set()
    with (DEFAULT_OUTPUT / "delivery_context.csv").open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            context_keys.add(key(row))
            team = teams[row["match_id"]]
            assert float(row["mismatch_weight"]) == float(team["mismatch_weight"])
            assert all(float(row[field]) > 0 for field in (
                "expected_bat_runs", "expected_bat_out", "expected_bowl_cost",
                "expected_bowl_wicket", "country_run_factor",
                "country_wicket_factor",
            ))
    assert context_keys == state_keys

    win_prob_keys = set()
    with (DEFAULT_OUTPUT / "win_probability_delivery.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        for row in csv.DictReader(handle):
            delivery_key = key(row)
            assert delivery_key in state_keys
            assert delivery_key not in win_prob_keys
            win_prob_keys.add(delivery_key)
            assert row["innings"] == "2"
            assert int(row["trained_through_year"]) < int(row["match_date"][:4])
            probability = float(row["win_probability"])
            leverage = float(row["potential_six_run_leverage"])
            assert 0 <= probability <= 1 and 0 <= leverage <= 1
            if abs(leverage - LEVERAGE_THRESHOLD) > 0.000001:
                assert int(row["win_prob_high_leverage"]) == int(
                    leverage >= LEVERAGE_THRESHOLD
                )
    assert len(win_prob_keys) == 67770
    win_summary = read("win_probability_summary.csv")
    assert len(win_summary) == 8
    assert len(read("win_probability_calibrators.csv")) == 8
    assert len(read("win_probability_models.csv")) == 40

    reports = read("player_pressure_summary.csv")
    segments = read("player_pressure_segments.csv")
    rankings = read("rankings.csv")
    assert len(rankings) == 20
    assert len({(row["role"], row["player_id"]) for row in rankings}) == 20
    report_index = {(row["role"], row["player_id"]): row for row in reports}
    for filename, select in (
        ("player_phase_scores.csv",
         lambda row: row["scope"] == "ALL" and row["phase"] != "all_phases"),
        ("player_country_scores.csv", lambda row: True),
        ("player_country_condition_scores.csv",
         lambda row: row["condition_axis"] == "run"),
    ):
        grouped: dict[tuple[str, str], Counter] = defaultdict(Counter)
        for row in read(filename):
            if not select(row):
                continue
            totals = grouped[(row["role"], row["player_id"])]
            totals["pressure_effective_balls"] += float(row["pressure_effective_balls"])
            totals["pressure_impact"] += float(row["pressure_impact"])
            totals["all_balls"] += int(row["all_balls"])
        assert grouped.keys() == report_index.keys()
        for player_key, totals in grouped.items():
            report = report_index[player_key]
            assert abs(totals["pressure_effective_balls"] - float(
                report["pressure_effective_balls"]
            )) < 0.01
            assert abs(totals["pressure_impact"] - float(
                report["pressure_impact"]
            )) < 0.05
            assert totals["all_balls"] == int(report["pressure_balls"]) + int(
                report["low_balls"]
            )
    portability = read("player_portability.csv")
    assert {(row["role"], row["player_id"]) for row in portability} == report_index.keys()
    dot_pressure = read("player_dot_pressure.csv")
    assert {(row["role"], row["player_id"]) for row in dot_pressure} == report_index.keys()
    for row in dot_pressure:
        report = report_index[(row["role"], row["player_id"])]
        assert row["rank"] == report["rank"]
        assert abs(float(row["pressure_effective_balls"]) - float(
            report["pressure_effective_balls"]
        )) < 0.01
        assert int(row["all_balls"]) == int(report["pressure_balls"]) + int(
            report["low_balls"]
        )
        assert int(row["chase_scoreless_dots"]) <= int(row["chase_balls"])
        for field in (
            "all_batter_zero_run_pct", "all_scoreless_dot_pct",
            "pressure_batter_zero_run_pct", "pressure_scoreless_dot_pct",
        ):
            if row[field]:
                assert 0 <= float(row[field]) <= 100
        if row["role"] == "batting":
            assert float(row["all_batter_zero_run_pct"]) + 0.01 >= float(
                row["all_scoreless_dot_pct"]
            )
            if row["pressure_batter_zero_run_pct"]:
                assert float(row["pressure_batter_zero_run_pct"]) + 0.01 >= float(
                    row["pressure_scoreless_dot_pct"]
                )
    for segment_type in ("format", "series"):
        grouped: dict[tuple[str, str], Counter] = defaultdict(Counter)
        for row in segments:
            if row["segment_type"] == segment_type:
                grouped[(row["role"], row["player_id"])]["balls"] += float(
                    row["pressure_effective_balls"]
                )
                grouped[(row["role"], row["player_id"])]["impact"] += float(
                    row["pressure_impact"]
                )
        for player_key, totals in grouped.items():
            report = report_index[player_key]
            assert abs(totals["balls"] - float(report["pressure_effective_balls"])) < 0.01
            assert abs(totals["impact"] - float(report["pressure_impact"])) < 0.05
    for role in ("batting", "bowling"):
        ranked = [row for row in rankings if row["role"] == role]
        assert [int(row["rank"]) for row in ranked] == list(range(1, 11))
        for row in ranked:
            report = report_index[(role, row["player_id"])]
            assert report["eligible"] == "1"
            assert report["rank"] == row["rank"]
    with (DEFAULT_OUTPUT / "icc_t20i_snapshot.csv").open(newline="", encoding="utf-8") as handle:
        official = list(csv.DictReader(handle))
    assert len(official) == 20
    assert all(row["snapshot_date"] == "2026-11-03" for row in official)
    assert all(row["player_id_in_pack"] for row in official)
    with (DEFAULT_OUTPUT / "elite_monthly_top10.csv").open(newline="", encoding="utf-8") as handle:
        monthly = list(csv.DictReader(handle))
    monthly_counts = Counter((row["role"], row["player_id"]) for row in monthly)
    monthly_ranks: dict[tuple[str, str], set[int]] = defaultdict(set)
    for row in monthly:
        month_role = (row["snapshot_month"], row["role"])
        assert int(row["rank"]) not in monthly_ranks[month_role]
        monthly_ranks[month_role].add(int(row["rank"]))
        assert int(row["rolling_balls"]) >= 120
        assert int(row["rolling_matches"]) >= 8
    assert all(ranks == set(range(1, len(ranks) + 1)) and len(ranks) <= 10
               for ranks in monthly_ranks.values())
    with (DEFAULT_OUTPUT / "elite_tenure_rankings.csv").open(newline="", encoding="utf-8") as handle:
        tenure = list(csv.DictReader(handle))
    assert all(monthly_counts[(row["role"], row["player_id"])] == int(row["top10_months"])
               for row in tenure)
    with (DEFAULT_OUTPUT / "elite_phase_matchups.csv").open(newline="", encoding="utf-8") as handle:
        elite_matchups = list(csv.DictReader(handle))
    for row in elite_matchups:
        supported = int(row["balls"]) >= 30 and int(row["matches"]) >= 5
        assert int(row["supported"]) == int(supported)
        assert bool(row["shrunk_score"]) == supported
        if supported:
            assert abs(float(row["shrunk_score"]) -
                       100 * float(row["impact"]) / (int(row["balls"]) + 80)) < 0.002
    print(f"PASS: {len(state_keys)} linked deliveries, {len(teams)} eligible matches")
    print(f"PASS: {unstable} unstable chase labels flagged, 20 unique ranked players")
    print(f"PASS: {len(win_prob_keys)} out-of-time chase probabilities validated")
    print(f"PASS: phase, country, and condition profiles reconcile for {len(reports)} player roles")
    print(f"PASS: {len(monthly)} historical proxy top-10 cells and {len(elite_matchups)} elite matchup cells")


if __name__ == "__main__":
    main()
