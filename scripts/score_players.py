"""Phase 4: score pressure performance, bootstrap by match, and rank players."""

from __future__ import annotations

import csv
import random
from collections import Counter, defaultdict

from build_cumulative_dataset import DEFAULT_OUTPUT


WICKET_RUN_VALUE = 5.0
MIN_PRESSURE_EFFECTIVE_BALLS = 40.0
MIN_PRESSURE_MATCHES = 8
MIN_LOW_BALLS = 30
BOOTSTRAP_DRAWS = 300
REPORT_FIELDS = [
    "player_id", "player_name", "role", "eligible", "rank",
    "total_matches", "pressure_matches", "pressure_balls",
    "pressure_effective_balls", "high_pressure_balls", "low_balls",
    "pressure_impact", "low_impact", "pressure_rate_per_100",
    "low_rate_per_100", "pressure_uplift_per_100", "shrunk_score",
    "bootstrap_p10", "bootstrap_p90", "conservative_score",
    "positive_pressure_match_share", "largest_positive_match_share",
    "pace_pressure_balls", "pace_pressure_runs", "pace_pressure_outs",
    "spin_pressure_balls", "spin_pressure_runs", "spin_pressure_outs",
    "rhb_pressure_legal_balls", "rhb_pressure_batter_runs_allowed",
    "rhb_pressure_wickets", "lhb_pressure_legal_balls",
    "lhb_pressure_batter_runs_allowed", "lhb_pressure_wickets",
    "pressure_wicket_caught", "pressure_wicket_bowled",
    "pressure_wicket_lbw", "pressure_wicket_stumped",
    "pressure_wicket_hit_wicket", "unstable_chase_deliveries_skipped",
    "poor_score_match_deliveries_skipped",
]
RANK_FIELDS = [
    "rank", "role", "player_id", "player_name", "conservative_score",
    "shrunk_score", "bootstrap_p10", "bootstrap_p90",
    "pressure_effective_balls", "pressure_matches",
    "positive_pressure_match_share",
]
SENSITIVITY_FIELDS = [
    "high_cutoff", "mismatch_weight", "role", "player_id", "player_name",
    "rank", "score", "eligible_candidates", "in_main_top_10",
    "in_main_point_top_10",
]
SEGMENT_FIELDS = [
    "segment_type", "segment_id", "player_id", "player_name", "role",
    "matches", "pressure_matches", "pressure_effective_balls", "low_balls",
    "pressure_impact", "low_impact", "pressure_rate_per_100",
    "low_rate_per_100", "pressure_uplift_per_100", "shrunk_score",
]
BOWLER_WICKET_TYPES = {
    "Caught": "caught", "Bowled": "bowled", "LBW": "lbw",
    "Stump": "stumped", "Hit Wicket": "hit_wicket",
}


def add_score(stats: Counter, residual: float, unit: int, pressure_score: int,
              high_cutoff: int, match_weight: float) -> None:
    tier_weight = (
        1.0 if pressure_score >= high_cutoff
        else 0.5 if pressure_score >= high_cutoff - 20 else 0.0
    )
    if tier_weight:
        stats["pressure_effective_balls"] += tier_weight * unit
        stats["pressure_impact"] += tier_weight * match_weight * residual
        if unit:
            stats["pressure_balls"] += 1
            if tier_weight == 1:
                stats["high_pressure_balls"] += 1
    else:
        stats["low_balls"] += unit
        stats["low_impact"] += match_weight * residual


def score(stats: Counter) -> tuple[float, float, float, float]:
    pballs = stats["pressure_effective_balls"]
    lowballs = stats["low_balls"]
    pressure_rate = 100 * stats["pressure_impact"] / pballs if pballs else 0.0
    low_rate = 100 * stats["low_impact"] / lowballs if lowballs else 0.0
    shrink = pballs / (pballs + 80.0)
    adjusted = low_rate + shrink * (pressure_rate - low_rate)
    uplift = adjusted - low_rate
    points = 0.65 * adjusted + 0.35 * uplift
    return pressure_rate, low_rate, uplift, points


def percentile(values: list[float], p: float) -> float:
    values = sorted(values)
    index = (len(values) - 1) * p
    lower = int(index)
    upper = min(lower + 1, len(values) - 1)
    return values[lower] + (values[upper] - values[lower]) * (index - lower)


def bootstrap(match_stats: list[Counter], pid: str, role: str) -> tuple[float, float]:
    seed = 42 + int(pid) + (100000 if role == "bowling" else 0)
    rng = random.Random(seed)
    draws = []
    n = len(match_stats)
    for _ in range(BOOTSTRAP_DRAWS):
        sampled = Counter()
        for _ in range(n):
            sampled.update(match_stats[rng.randrange(n)])
        draws.append(score(sampled)[3])
    return percentile(draws, 0.10), percentile(draws, 0.90)


def main() -> None:
    with (DEFAULT_OUTPUT / "match_quality.csv").open(newline="", encoding="utf-8") as handle:
        poor_score_matches = {
            row["match_id"] for row in csv.DictReader(handle)
            if row["approx_margin_error"] and int(row["approx_margin_error"]) > 7
        }
    match_groups: dict[tuple[str, str], dict[str, Counter]] = defaultdict(
        lambda: defaultdict(Counter)
    )
    segment_groups: dict[tuple[str, str, str, str], dict[str, Counter]] = defaultdict(
        lambda: defaultdict(Counter)
    )
    names: dict[tuple[str, str], str] = {}
    unstable_counts: Counter = Counter()
    poor_match_counts: Counter = Counter()
    scenarios = [(cutoff, weight) for cutoff in (45, 50, 55) for weight in (0.60, 0.75, 0.90)]
    scenario_stats: dict[tuple[int, float, str, str], Counter] = defaultdict(Counter)
    scenario_matches: dict[tuple[int, float, str, str], set[str]] = defaultdict(set)

    with (DEFAULT_OUTPUT / "delivery_context.csv").open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            stable = row["tier_stable_with_7_run_shift"] == "1"
            pscore = int(row["pressure_score"])
            mid = row["match_id"]
            mismatch = float(row["mismatch_weight"]) < 1.0
            match_weight = float(row["mismatch_weight"])
            runs = int(row["runs"])
            is_wide = row["extras_type"] == "wide"
            legal = int(row["is_legal"])
            for role, pid, name, unit, residual in (
                (
                    "batting", row["striker_id"], row["striker_name"],
                    int(not is_wide),
                    runs - float(row["expected_bat_runs"]) - WICKET_RUN_VALUE * (
                        int(row["striker_out"]) - float(row["expected_bat_out"])
                    ),
                ),
                (
                    "bowling", row["bowler_id"], row["bowler_name"], legal,
                    float(row["expected_bowl_cost"]) - int(row["observed_bowl_cost"])
                    + WICKET_RUN_VALUE * (
                        int(row["bowler_wicket"]) - float(row["expected_bowl_wicket"])
                    ),
                ),
            ):
                if role == "batting" and not unit:
                    continue
                key = (pid, role)
                names[key] = name
                if mid in poor_score_matches:
                    poor_match_counts[key] += 1
                    continue
                if not stable:
                    unstable_counts[key] += 1
                    continue
                stats = match_groups[key][mid]
                add_score(stats, residual, unit, pscore, 50, match_weight)
                for segment_type, segment_id in (
                    ("format", row["scope"]), ("series", row["comp_id"])
                ):
                    add_score(
                        segment_groups[(segment_type, segment_id, pid, role)][mid],
                        residual, unit, pscore, 50, match_weight,
                    )
                if pscore >= 30:
                    if role == "batting":
                        style = row["pace_or_spin"].lower()
                        if style in ("pace", "spin"):
                            stats[f"{style}_pressure_balls"] += 1
                            stats[f"{style}_pressure_runs"] += runs
                            stats[f"{style}_pressure_outs"] += int(row["striker_out"])
                    else:
                        hand = row["batting_type"].lower()
                        if hand in ("rhb", "lhb"):
                            stats[f"{hand}_pressure_legal_balls"] += legal
                            stats[f"{hand}_pressure_batter_runs_allowed"] += runs
                            stats[f"{hand}_pressure_wickets"] += int(row["bowler_wicket"])
                        mode = BOWLER_WICKET_TYPES.get(row["dismissal_type"])
                        if int(row["bowler_wicket"]) and mode:
                            stats[f"pressure_wicket_{mode}"] += 1
                for cutoff, alternate_weight in scenarios:
                    scenario_key = (cutoff, alternate_weight, role, pid)
                    sstats = scenario_stats[scenario_key]
                    weight = alternate_weight if mismatch else 1.0
                    add_score(sstats, residual, unit, pscore, cutoff, weight)
                    if pscore >= cutoff - 20 and unit:
                        scenario_matches[scenario_key].add(mid)

    reports = []
    for key, matches in sorted(match_groups.items(), key=lambda item: (
        item[0][1], int(item[0][0])
    )):
        pid, role = key
        total = Counter()
        for stats in matches.values():
            total.update(stats)
        pressure_matches = sum(s["pressure_effective_balls"] > 0 for s in matches.values())
        eligible = (
            total["pressure_effective_balls"] >= MIN_PRESSURE_EFFECTIVE_BALLS
            and pressure_matches >= MIN_PRESSURE_MATCHES
            and total["low_balls"] >= MIN_LOW_BALLS
        )
        pressure_rate, low_rate, uplift, points = score(total)
        p10, p90 = bootstrap(list(matches.values()), pid, role) if eligible else (0.0, 0.0)
        positive = [s["pressure_impact"] for s in matches.values() if s["pressure_effective_balls"]]
        positive_count = sum(value > 0 for value in positive)
        positive_sum = sum(value for value in positive if value > 0)
        largest_share = max((value for value in positive if value > 0), default=0) / positive_sum if positive_sum else 0.0
        report = {
            "player_id": pid, "player_name": names[key], "role": role,
            "eligible": int(eligible), "rank": "", "total_matches": len(matches),
            "pressure_matches": pressure_matches,
            "pressure_balls": total["pressure_balls"],
            "pressure_effective_balls": round(total["pressure_effective_balls"], 2),
            "high_pressure_balls": total["high_pressure_balls"],
            "low_balls": total["low_balls"],
            "pressure_impact": round(total["pressure_impact"], 3),
            "low_impact": round(total["low_impact"], 3),
            "pressure_rate_per_100": round(pressure_rate, 3),
            "low_rate_per_100": round(low_rate, 3),
            "pressure_uplift_per_100": round(uplift, 3),
            "shrunk_score": round(points, 3),
            "bootstrap_p10": round(p10, 3) if eligible else "",
            "bootstrap_p90": round(p90, 3) if eligible else "",
            "conservative_score": round((points + p10) / 2, 3) if eligible else "",
            "positive_pressure_match_share": round(positive_count / len(positive), 3) if positive else 0,
            "largest_positive_match_share": round(largest_share, 3),
            "unstable_chase_deliveries_skipped": unstable_counts[key],
            "poor_score_match_deliveries_skipped": poor_match_counts[key],
        }
        for field in REPORT_FIELDS:
            if field not in report:
                report[field] = total[field]
        reports.append(report)

    rankings = []
    main_top_ids: dict[str, set[str]] = {}
    main_point_top_ids: dict[str, set[str]] = {}
    for role in ("batting", "bowling"):
        eligible_rows = [r for r in reports if r["role"] == role and r["eligible"]]
        point_rows = sorted(eligible_rows, key=lambda r: (
            -float(r["shrunk_score"]), int(r["player_id"])
        ))
        main_point_top_ids[role] = {r["player_id"] for r in point_rows[:10]}
        eligible_rows.sort(key=lambda r: (-float(r["conservative_score"]), int(r["player_id"])))
        print(f"{role} eligible candidates: {len(eligible_rows)}")
        if len(eligible_rows) < 10:
            raise ValueError(f"Fewer than 10 eligible {role} players; inspect thresholds")
        for rank, report in enumerate(eligible_rows, 1):
            report["rank"] = rank
        top = eligible_rows[:10]
        main_top_ids[role] = {r["player_id"] for r in top}
        rankings.extend({field: row[field] for field in RANK_FIELDS} for row in top)
    reports.sort(key=lambda r: (r["role"], int(r["rank"]) if r["rank"] else 9999, int(r["player_id"])))
    with (DEFAULT_OUTPUT / "player_pressure_summary.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=REPORT_FIELDS)
        writer.writeheader()
        writer.writerows(reports)
    with (DEFAULT_OUTPUT / "rankings.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=RANK_FIELDS)
        writer.writeheader()
        writer.writerows(rankings)

    segment_rows = []
    for (segment_type, segment_id, pid, role), matches in sorted(
        segment_groups.items(), key=lambda item: (
            item[0][0], item[0][1], int(item[0][2]), item[0][3]
        )
    ):
        total = Counter()
        for stats in matches.values():
            total.update(stats)
        p_rate, low_rate, uplift, points = score(total)
        segment_rows.append({
            "segment_type": segment_type, "segment_id": segment_id,
            "player_id": pid, "player_name": names[(pid, role)], "role": role,
            "matches": len(matches),
            "pressure_matches": sum(
                stats["pressure_effective_balls"] > 0 for stats in matches.values()
            ),
            "pressure_effective_balls": round(total["pressure_effective_balls"], 2),
            "low_balls": total["low_balls"],
            "pressure_impact": round(total["pressure_impact"], 3),
            "low_impact": round(total["low_impact"], 3),
            "pressure_rate_per_100": round(p_rate, 3),
            "low_rate_per_100": round(low_rate, 3),
            "pressure_uplift_per_100": round(uplift, 3),
            "shrunk_score": round(points, 3),
        })
    with (DEFAULT_OUTPUT / "player_pressure_segments.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=SEGMENT_FIELDS)
        writer.writeheader()
        writer.writerows(segment_rows)

    sensitivity_rows = []
    for cutoff, alternate_weight in scenarios:
        for role in ("batting", "bowling"):
            candidates = []
            for (t, weight, candidate_role, pid), stats in scenario_stats.items():
                if (t, weight, candidate_role) != (cutoff, alternate_weight, role):
                    continue
                key = (t, weight, role, pid)
                if (stats["pressure_effective_balls"] >= MIN_PRESSURE_EFFECTIVE_BALLS
                    and len(scenario_matches[key]) >= MIN_PRESSURE_MATCHES
                    and stats["low_balls"] >= MIN_LOW_BALLS):
                    candidates.append((pid, score(stats)[3]))
            candidates.sort(key=lambda item: (-item[1], int(item[0])))
            for rank, (pid, points) in enumerate(candidates, 1):
                if (rank > 20 and pid not in main_top_ids[role]
                    and pid not in main_point_top_ids[role]):
                    continue
                sensitivity_rows.append({
                    "high_cutoff": cutoff, "mismatch_weight": alternate_weight,
                    "role": role, "player_id": pid,
                    "player_name": names[(pid, role)], "rank": rank,
                    "score": round(points, 3),
                    "eligible_candidates": len(candidates),
                    "in_main_top_10": int(pid in main_top_ids[role]),
                    "in_main_point_top_10": int(pid in main_point_top_ids[role]),
                })
    with (DEFAULT_OUTPUT / "ranking_sensitivity.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=SENSITIVITY_FIELDS)
        writer.writeheader()
        writer.writerows(sensitivity_rows)
    for row in rankings:
        print(f"{row['role']} #{row['rank']}: {row['player_name']} ({row['conservative_score']})")
    print(f"Poor-score matches excluded from player scoring: {len(poor_score_matches)}")
    print(f"Player format/series pressure rows: {len(segment_rows)}")


if __name__ == "__main__":
    main()
