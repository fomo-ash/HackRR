"""Profile pressure impact by innings phase, country conditions, and matchup."""

from __future__ import annotations

import csv
from collections import Counter, defaultdict

from build_cumulative_dataset import DEFAULT_OUTPUT
from score_players import WICKET_RUN_VALUE, add_score, percentile, score


MIN_COUNTRY_PRIOR = 500
LOW_FACTOR = 0.97
HIGH_FACTOR = 1.03
MIN_CONTEXT_BALLS = 20
MIN_CONTEXT_MATCHES = 5

COMMON_FIELDS = [
    "player_id", "player_name", "role", "all_matches", "all_balls",
    "all_impact", "all_residual_per_100", "all_context_score",
    "all_batter_runs", "all_expected_batter_runs", "all_striker_outs",
    "all_expected_striker_outs", "all_bowler_cost", "all_expected_bowler_cost",
    "all_bowler_wickets", "all_expected_bowler_wickets", "pressure_matches",
    "all_batting_strike_rate", "all_batter_zero_run_pct",
    "all_scoreless_dot_pct", "pressure_batting_strike_rate",
    "pressure_batter_zero_run_pct", "pressure_scoreless_dot_pct",
    "chase_balls", "chase_scoreless_dots",
    "chase_dot_required_rate_increase_sum",
    "chase_dot_required_rate_increase_per_100_balls",
    "chase_dot_required_rate_increase_median",
    "pressure_effective_balls", "low_balls", "pressure_impact",
    "low_impact", "pressure_residual_per_100", "low_residual_per_100",
    "shrunk_context_score", "supported_context", "pressure_deliveries",
    "pressure_batter_runs", "expected_pressure_batter_runs",
    "pressure_striker_outs", "expected_pressure_striker_outs",
    "pressure_bowler_cost", "expected_pressure_bowler_cost",
    "pressure_bowler_wickets", "expected_pressure_bowler_wickets",
    "mean_country_run_factor", "mean_country_wicket_factor",
    "mean_country_prior_balls",
]
PHASE_FIELDS = ["scope", "phase"] + COMMON_FIELDS
COUNTRY_FIELDS = ["scope", "venue_country"] + COMMON_FIELDS + [
    "run_suppressing_effective_balls", "high_scoring_effective_balls",
    "wickets_scarce_effective_balls", "wickets_common_effective_balls",
]
CONDITION_FIELDS = ["condition_axis", "condition"] + COMMON_FIELDS
PORTABILITY_FIELDS = [
    "player_id", "player_name", "role", "eligible_primary",
    "supported_contexts", "positive_supported_contexts", "portability_score",
    "worst_supported_residual_per_100", "phase_contexts_supported",
    "matchup_contexts_supported", "adverse_contexts_supported",
    "context_details",
]
DOT_FIELDS = [
    "player_id", "player_name", "role", "eligible_primary", "rank",
    "all_balls", "all_batting_strike_rate", "all_batter_zero_run_pct",
    "all_scoreless_dot_pct", "pressure_effective_balls",
    "pressure_batting_strike_rate", "pressure_batter_zero_run_pct",
    "pressure_scoreless_dot_pct", "chase_balls", "chase_scoreless_dots",
    "chase_dot_required_rate_increase_sum",
    "chase_dot_required_rate_increase_per_100_balls",
    "chase_dot_required_rate_increase_median",
]


def condition(value: float, prior: int, low: str, high: str) -> str:
    if prior < MIN_COUNTRY_PRIOR:
        return "insufficient_prior"
    if value <= LOW_FACTOR:
        return low
    if value >= HIGH_FACTOR:
        return high
    return "typical"


def write_csv(name: str, fields: list[str], rows: list[dict]) -> None:
    with (DEFAULT_OUTPUT / name).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    with (DEFAULT_OUTPUT / "match_quality.csv").open(newline="", encoding="utf-8") as handle:
        poor_matches = {
            row["match_id"] for row in csv.DictReader(handle)
            if row["approx_margin_error"] and int(row["approx_margin_error"]) > 7
        }
    with (DEFAULT_OUTPUT / "player_pressure_summary.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        reports = {
            (row["role"], row["player_id"]): row for row in csv.DictReader(handle)
        }

    phase_stats: dict[tuple, Counter] = defaultdict(Counter)
    country_stats: dict[tuple, Counter] = defaultdict(Counter)
    condition_stats: dict[tuple, Counter] = defaultdict(Counter)
    matchup_stats: dict[tuple, Counter] = defaultdict(Counter)
    matches: dict[tuple, set[str]] = defaultdict(set)
    all_matches: dict[tuple, set[str]] = defaultdict(set)
    dot_deltas: dict[tuple, list[float]] = defaultdict(list)
    names: dict[tuple[str, str], str] = {}

    def record(key: tuple, stats: Counter, row: dict[str, str], role: str,
               residual: float, unit: int, tier_weight: float,
               run_condition: str, wicket_condition: str) -> None:
        match_weight = float(row["mismatch_weight"])
        stats["all_balls"] += unit
        stats["all_impact"] += match_weight * residual
        runs = int(row["runs"])
        scoreless = int(
            runs == 0 and row["extras_type"] == "None"
            and row["is_legal"] == "1"
        )
        stats["all_scoreless_dots"] += scoreless
        if role == "batting":
            stats["all_batter_zero_runs"] += int(runs == 0)
        if row["innings"] == "2":
            stats["chase_balls"] += unit
            remaining = int(row["balls_remaining"])
            required = int(row["runs_required_approx"])
            if scoreless and remaining > 1 and required > 0:
                stats["chase_scoreless_dots"] += 1
                increase = required / (remaining - 1) - required / remaining
                stats["chase_dot_required_rate_increase_sum"] += increase
                dot_deltas[key].append(increase)
        if unit:
            all_matches[key].add(row["match_id"])
        if role == "batting":
            stats["all_batter_runs"] += int(row["runs"])
            stats["all_expected_batter_runs"] += float(row["expected_bat_runs"])
            stats["all_striker_outs"] += int(row["striker_out"])
            stats["all_expected_striker_outs"] += float(row["expected_bat_out"])
        else:
            stats["all_bowler_cost"] += int(row["observed_bowl_cost"])
            stats["all_expected_bowler_cost"] += float(row["expected_bowl_cost"])
            stats["all_bowler_wickets"] += int(row["bowler_wicket"])
            stats["all_expected_bowler_wickets"] += float(row["expected_bowl_wicket"])
        add_score(stats, residual, unit, int(row["pressure_score"]), 50, match_weight)
        if not tier_weight:
            return
        if unit:
            matches[key].add(row["match_id"])
        stats["pressure_deliveries"] += 1
        stats["pressure_scoreless_dots"] += scoreless
        if role == "batting":
            stats["pressure_batter_zero_runs"] += int(runs == 0)
            stats["pressure_batting_balls"] += unit
        else:
            stats["pressure_bowling_legal_balls"] += unit
        stats["country_factor_weight"] += tier_weight
        stats["country_run_factor_sum"] += tier_weight * float(row["country_run_factor"])
        stats["country_wicket_factor_sum"] += tier_weight * float(row["country_wicket_factor"])
        stats["country_prior_balls_sum"] += tier_weight * int(row["country_balls_prior"])
        stats[f"run_{run_condition}_effective_balls"] += tier_weight * unit
        stats[f"wicket_{wicket_condition}_effective_balls"] += tier_weight * unit
        if role == "batting":
            stats["pressure_batter_runs"] += int(row["runs"])
            stats["expected_pressure_batter_runs"] += float(row["expected_bat_runs"])
            stats["pressure_striker_outs"] += int(row["striker_out"])
            stats["expected_pressure_striker_outs"] += float(row["expected_bat_out"])
        else:
            stats["pressure_bowler_cost"] += int(row["observed_bowl_cost"])
            stats["expected_pressure_bowler_cost"] += float(row["expected_bowl_cost"])
            stats["pressure_bowler_wickets"] += int(row["bowler_wicket"])
            stats["expected_pressure_bowler_wickets"] += float(row["expected_bowl_wicket"])

    with (DEFAULT_OUTPUT / "delivery_context.csv").open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if (row["match_id"] in poor_matches
                    or row["tier_stable_with_7_run_shift"] != "1"):
                continue
            pscore = int(row["pressure_score"])
            tier_weight = 1.0 if pscore >= 50 else 0.5 if pscore >= 30 else 0.0
            prior = min(int(row["country_balls_prior"]),
                        int(row["country_deliveries_prior"]))
            run_condition = condition(float(row["country_run_factor"]), prior,
                                      "run_suppressing", "high_scoring")
            wicket_condition = condition(float(row["country_wicket_factor"]), prior,
                                         "wickets_scarce", "wickets_common")
            for role, pid, name, unit, residual, matchup in (
                (
                    "batting", row["striker_id"], row["striker_name"],
                    int(row["extras_type"] != "wide"),
                    int(row["runs"]) - float(row["expected_bat_runs"])
                    - WICKET_RUN_VALUE * (
                        int(row["striker_out"]) - float(row["expected_bat_out"])
                    ), row["pace_or_spin"].lower(),
                ),
                (
                    "bowling", row["bowler_id"], row["bowler_name"],
                    int(row["is_legal"]),
                    float(row["expected_bowl_cost"]) - int(row["observed_bowl_cost"])
                    + WICKET_RUN_VALUE * (
                        int(row["bowler_wicket"]) - float(row["expected_bowl_wicket"])
                    ), row["batting_type"].lower(),
                ),
            ):
                if role == "batting" and not unit:
                    continue
                names[(role, pid)] = name
                keys = [
                    (("phase", "ALL", "all_phases", role, pid), phase_stats),
                    (("phase", "ALL", row["phase"], role, pid), phase_stats),
                    (("phase", row["scope"], row["phase"], role, pid), phase_stats),
                    (("country", row["scope"], row["venue_country"], role, pid), country_stats),
                    (("condition", "run", run_condition, role, pid), condition_stats),
                    (("condition", "wicket", wicket_condition, role, pid), condition_stats),
                    (("matchup", matchup, role, pid), matchup_stats),
                ]
                for key, group in keys:
                    record(key, group[key], row, role, residual, unit, tier_weight,
                           run_condition, wicket_condition)

    def common(key: tuple, stats: Counter) -> dict:
        role, pid = key[-2:]
        p_rate, low_rate, _, points = score(stats)
        pballs = stats["pressure_effective_balls"]
        lowballs = stats["low_balls"]
        all_balls = stats["all_balls"]
        all_rate = 100 * stats["all_impact"] / all_balls if all_balls else 0.0
        pressure_batting_balls = stats["pressure_batting_balls"]
        pressure_bowling_balls = stats["pressure_bowling_legal_balls"]
        pressure_dot_denominator = (
            pressure_batting_balls if role == "batting" else pressure_bowling_balls
        )
        pressure_matches = len(matches[key])
        factor_weight = stats["country_factor_weight"]
        supported = pballs >= MIN_CONTEXT_BALLS and pressure_matches >= MIN_CONTEXT_MATCHES
        return {
            "player_id": pid, "player_name": names[(role, pid)], "role": role,
            "all_matches": len(all_matches[key]),
            "all_balls": all_balls,
            "all_impact": round(stats["all_impact"], 3),
            "all_residual_per_100": round(all_rate, 3) if all_balls else "",
            "all_context_score": round(
                all_rate * all_balls / (all_balls + 80), 3
            ) if all_balls >= 100 else "",
            "all_batter_runs": stats["all_batter_runs"],
            "all_expected_batter_runs": round(stats["all_expected_batter_runs"], 3),
            "all_striker_outs": stats["all_striker_outs"],
            "all_expected_striker_outs": round(stats["all_expected_striker_outs"], 3),
            "all_bowler_cost": stats["all_bowler_cost"],
            "all_expected_bowler_cost": round(stats["all_expected_bowler_cost"], 3),
            "all_bowler_wickets": stats["all_bowler_wickets"],
            "all_expected_bowler_wickets": round(stats["all_expected_bowler_wickets"], 3),
            "all_batting_strike_rate": round(
                100 * stats["all_batter_runs"] / all_balls, 2
            ) if role == "batting" and all_balls else "",
            "all_batter_zero_run_pct": round(
                100 * stats["all_batter_zero_runs"] / all_balls, 2
            ) if role == "batting" and all_balls else "",
            "all_scoreless_dot_pct": round(
                100 * stats["all_scoreless_dots"] / all_balls, 2
            ) if all_balls else "",
            "pressure_batting_strike_rate": round(
                100 * stats["pressure_batter_runs"] / pressure_batting_balls, 2
            ) if role == "batting" and pressure_batting_balls else "",
            "pressure_batter_zero_run_pct": round(
                100 * stats["pressure_batter_zero_runs"] / pressure_batting_balls, 2
            ) if role == "batting" and pressure_batting_balls else "",
            "pressure_scoreless_dot_pct": round(
                100 * stats["pressure_scoreless_dots"] / pressure_dot_denominator, 2
            ) if pressure_dot_denominator else "",
            "chase_balls": stats["chase_balls"],
            "chase_scoreless_dots": stats["chase_scoreless_dots"],
            "chase_dot_required_rate_increase_sum": round(
                stats["chase_dot_required_rate_increase_sum"], 4
            ),
            "chase_dot_required_rate_increase_per_100_balls": round(
                100 * stats["chase_dot_required_rate_increase_sum"] / stats["chase_balls"], 4
            ) if stats["chase_balls"] else "",
            "chase_dot_required_rate_increase_median": round(
                percentile(dot_deltas[key], 0.5), 4
            ) if dot_deltas[key] else "",
            "pressure_matches": pressure_matches,
            "pressure_effective_balls": round(pballs, 2),
            "low_balls": lowballs,
            "pressure_impact": round(stats["pressure_impact"], 3),
            "low_impact": round(stats["low_impact"], 3),
            "pressure_residual_per_100": round(p_rate, 3) if pballs else "",
            "low_residual_per_100": round(low_rate, 3) if lowballs else "",
            "shrunk_context_score": round(points, 3) if supported and lowballs >= 20 else "",
            "supported_context": int(supported),
            "pressure_deliveries": stats["pressure_deliveries"],
            "pressure_batter_runs": stats["pressure_batter_runs"],
            "expected_pressure_batter_runs": round(stats["expected_pressure_batter_runs"], 3),
            "pressure_striker_outs": stats["pressure_striker_outs"],
            "expected_pressure_striker_outs": round(stats["expected_pressure_striker_outs"], 3),
            "pressure_bowler_cost": stats["pressure_bowler_cost"],
            "expected_pressure_bowler_cost": round(stats["expected_pressure_bowler_cost"], 3),
            "pressure_bowler_wickets": stats["pressure_bowler_wickets"],
            "expected_pressure_bowler_wickets": round(stats["expected_pressure_bowler_wickets"], 3),
            "mean_country_run_factor": round(
                stats["country_run_factor_sum"] / factor_weight, 4
            ) if factor_weight else "",
            "mean_country_wicket_factor": round(
                stats["country_wicket_factor_sum"] / factor_weight, 4
            ) if factor_weight else "",
            "mean_country_prior_balls": round(
                stats["country_prior_balls_sum"] / factor_weight, 1
            ) if factor_weight else "",
        }

    phase_rows = [
        {"scope": key[1], "phase": key[2], **common(key, stats)}
        for key, stats in sorted(phase_stats.items())
    ]
    country_rows = [
        {
            "scope": key[1], "venue_country": key[2], **common(key, stats),
            "run_suppressing_effective_balls": round(
                stats["run_run_suppressing_effective_balls"], 2
            ),
            "high_scoring_effective_balls": round(
                stats["run_high_scoring_effective_balls"], 2
            ),
            "wickets_scarce_effective_balls": round(
                stats["wicket_wickets_scarce_effective_balls"], 2
            ),
            "wickets_common_effective_balls": round(
                stats["wicket_wickets_common_effective_balls"], 2
            ),
        }
        for key, stats in sorted(country_stats.items())
    ]
    condition_rows = [
        {"condition_axis": key[1], "condition": key[2], **common(key, stats)}
        for key, stats in sorted(condition_stats.items())
    ]

    dot_rows = []
    for (role, pid), report in sorted(reports.items()):
        key = ("phase", "ALL", "all_phases", role, pid)
        profile = common(key, phase_stats[key])
        dot_rows.append({
            **{field: profile[field] for field in DOT_FIELDS if field in profile},
            "eligible_primary": report["eligible"], "rank": report["rank"],
        })

    portability_rows = []
    for (role, pid), report in sorted(reports.items()):
        contexts = []
        for phase in ("powerplay", "middle", "death"):
            key = ("phase", "ALL", phase, role, pid)
            contexts.append((f"phase:{phase}", key, phase_stats.get(key, Counter())))
        for matchup in (("pace", "spin") if role == "batting" else ("rhb", "lhb")):
            key = ("matchup", matchup, role, pid)
            contexts.append((f"matchup:{matchup}", key, matchup_stats.get(key, Counter())))
        adverse_run = "run_suppressing" if role == "batting" else "high_scoring"
        contexts.append((
            f"adverse_run:{adverse_run}",
            ("condition", "run", adverse_run, role, pid),
            condition_stats.get(("condition", "run", adverse_run, role, pid), Counter()),
        ))
        adverse_wicket = "wickets_common" if role == "batting" else "wickets_scarce"
        contexts.append((
            f"adverse_wicket:{adverse_wicket}",
            ("condition", "wicket", adverse_wicket, role, pid),
            condition_stats.get(("condition", "wicket", adverse_wicket, role, pid), Counter()),
        ))
        supported = []
        for label, key, stats in contexts:
            if (stats["pressure_effective_balls"] >= MIN_CONTEXT_BALLS
                    and len(matches[key]) >= MIN_CONTEXT_MATCHES):
                p_rate = 100 * stats["pressure_impact"] / stats["pressure_effective_balls"]
                supported.append((label, p_rate))
        positive = sum(value > 0 for _, value in supported)
        portability_rows.append({
            "player_id": pid, "player_name": report["player_name"],
            "role": role, "eligible_primary": report["eligible"],
            "supported_contexts": len(supported),
            "positive_supported_contexts": positive,
            "portability_score": round(100 * (positive + 1) / (len(supported) + 2), 2)
            if len(supported) >= 3 else "",
            "worst_supported_residual_per_100": round(
                min((value for _, value in supported), default=0), 3
            ) if supported else "",
            "phase_contexts_supported": sum(label.startswith("phase:") for label, _ in supported),
            "matchup_contexts_supported": sum(label.startswith("matchup:") for label, _ in supported),
            "adverse_contexts_supported": sum(label.startswith("adverse_") for label, _ in supported),
            "context_details": "; ".join(f"{label}={value:.2f}" for label, value in supported),
        })

    write_csv("player_phase_scores.csv", PHASE_FIELDS, phase_rows)
    write_csv("player_country_scores.csv", COUNTRY_FIELDS, country_rows)
    write_csv("player_country_condition_scores.csv", CONDITION_FIELDS, condition_rows)
    write_csv("player_portability.csv", PORTABILITY_FIELDS, portability_rows)
    write_csv("player_dot_pressure.csv", DOT_FIELDS, dot_rows)
    print(
        f"Context profiles: {len(phase_rows)} phase, {len(country_rows)} country, "
        f"{len(condition_rows)} condition, {len(portability_rows)} portability, "
        f"{len(dot_rows)} dot-pressure rows"
    )


if __name__ == "__main__":
    main()
