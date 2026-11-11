"""Phase 1: reconstruct auditable pre-delivery state without exact extras."""

from __future__ import annotations

import csv
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

from build_cumulative_dataset import DEFAULT_INPUT, DEFAULT_OUTPUT, match_reason, read_index


STATE_FIELDS = [
    "match_id", "match_date", "comp_id", "comp_name", "match_format",
    "season", "venue_id", "venue_country", "knock_out", "innings",
    "overid", "over_ball_num", "innings_ball_num", "legal_before",
    "balls_remaining", "wickets_before", "bat_runs_before",
    "extra_events_before", "approx_score_before", "approx_target",
    "runs_required_approx", "batting_team_id", "bowling_team_id",
    "striker_id", "striker_name", "bowler_id", "bowler_name",
    "batting_type", "pace_or_spin", "bowling_type", "runs",
    "extras_type", "is_legal", "is_wicket", "dismissal_type",
    "dismissed_player_id", "is_four", "is_six",
]
QUALITY_FIELDS = [
    "match_id", "match_date", "comp_name", "match_format", "eligible",
    "exclusion_reason", "first_batter_runs", "first_extra_events",
    "second_batter_runs", "second_extra_events", "first_approx_total",
    "second_approx_total", "declared_run_margin", "approx_margin_error",
]


def has_extra(value: str) -> bool:
    # The CSV writes absent extras as the literal string "None".
    return value not in ("", "None", "nan", "NULL")


def main() -> None:
    competitions = read_index(DEFAULT_INPUT / "competitions.csv", "comp_id")
    matches = read_index(DEFAULT_INPUT / "matches.csv", "match_id")
    innings_totals: dict[tuple[str, str], Counter] = defaultdict(Counter)
    with (DEFAULT_INPUT / "ball_by_ball.csv").open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            if row["innings"] not in ("1", "2"):
                continue
            totals = innings_totals[(row["match_id"], row["innings"])]
            totals["batter_runs"] += int(row["runs"])
            totals["extra_events"] += has_extra(row["extras_type"])

    quality_rows = []
    margin_errors = []
    eligible_match_ids = set()
    for mid, match in matches.items():
        comp = competitions[match["comp_id"]]
        reason = match_reason(match, comp)
        if mid not in {key[0] for key in innings_totals}:
            reason = reason or "no_deliveries"
        if not reason:
            eligible_match_ids.add(mid)
        first = innings_totals[(mid, "1")]
        second = innings_totals[(mid, "2")]
        first_total = first["batter_runs"] + first["extra_events"]
        second_total = second["batter_runs"] + second["extra_events"]
        margin_match = re.search(r"won by\s+(\d+)\s+runs?\b", match["result"], re.I)
        margin = int(margin_match.group(1)) if margin_match else None
        error = abs(first_total - second_total - margin) if margin is not None and not reason else None
        if error is not None:
            margin_errors.append(error)
        quality_rows.append({
            "match_id": mid, "match_date": match["match_date"],
            "comp_name": comp["comp_name"], "match_format": comp["match_format"],
            "eligible": int(not reason), "exclusion_reason": reason,
            "first_batter_runs": first["batter_runs"],
            "first_extra_events": first["extra_events"],
            "second_batter_runs": second["batter_runs"],
            "second_extra_events": second["extra_events"],
            "first_approx_total": first_total, "second_approx_total": second_total,
            "declared_run_margin": "" if margin is None else margin,
            "approx_margin_error": "" if error is None else error,
        })

    DEFAULT_OUTPUT.mkdir(parents=True, exist_ok=True)
    with (DEFAULT_OUTPUT / "match_quality.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=QUALITY_FIELDS)
        writer.writeheader()
        writer.writerows(sorted(quality_rows, key=lambda r: (r["match_date"], int(r["match_id"]))))

    states: dict[tuple[str, str], Counter] = defaultdict(Counter)
    previous_ball: dict[tuple[str, str], int] = {}
    count = 0
    with (DEFAULT_INPUT / "ball_by_ball.csv").open(newline="", encoding="utf-8-sig") as source, (
        DEFAULT_OUTPUT / "match_state.csv"
    ).open("w", newline="", encoding="utf-8") as target:
        writer = csv.DictWriter(target, fieldnames=STATE_FIELDS)
        writer.writeheader()
        for ball in csv.DictReader(source):
            mid, innings = ball["match_id"], ball["innings"]
            if mid not in eligible_match_ids or innings not in ("1", "2"):
                continue
            key = (mid, innings)
            sequence = int(ball["innings_ball_num"])
            if sequence <= previous_ball.get(key, 0):
                raise ValueError(f"Non-increasing innings ball number at {key}")
            previous_ball[key] = sequence
            match = matches[mid]
            comp = competitions[match["comp_id"]]
            pre = states[key]
            extra = ball["extras_type"]
            legal = extra not in ("wide", "Overstep")
            approx_target = (
                innings_totals[(mid, "1")]["batter_runs"]
                + innings_totals[(mid, "1")]["extra_events"] + 1
                if innings == "2" else ""
            )
            approx_before = pre["batter_runs"] + pre["extra_events"]
            writer.writerow({
                "match_id": mid, "match_date": match["match_date"],
                "comp_id": match["comp_id"], "comp_name": comp["comp_name"],
                "match_format": comp["match_format"], "season": comp["season"],
                "venue_id": match["venue_id"], "venue_country": match["venue_country"],
                "knock_out": match["knock_out"], "innings": innings,
                "overid": ball["overid"], "over_ball_num": ball["over_ball_num"],
                "innings_ball_num": sequence, "legal_before": pre["legal"],
                "balls_remaining": max(0, 120 - pre["legal"]),
                "wickets_before": pre["wickets"],
                "bat_runs_before": pre["batter_runs"],
                "extra_events_before": pre["extra_events"],
                "approx_score_before": approx_before,
                "approx_target": approx_target,
                "runs_required_approx": max(0, approx_target - approx_before)
                if innings == "2" else "",
                **{field: ball[field] for field in (
                    "batting_team_id", "bowling_team_id", "striker_id", "striker_name",
                    "bowler_id", "bowler_name", "batting_type", "pace_or_spin",
                    "bowling_type", "runs", "extras_type", "is_wicket",
                    "dismissal_type", "dismissed_player_id", "is_four", "is_six",
                )},
                "is_legal": int(legal),
            })
            pre["legal"] += legal
            pre["batter_runs"] += int(ball["runs"])
            pre["extra_events"] += has_extra(extra)
            pre["wickets"] += ball["is_wicket"].lower() == "true"
            count += 1

    margin_errors.sort()
    p95 = margin_errors[math.ceil(0.95 * len(margin_errors)) - 1]
    print(f"Eligible matches: {len(eligible_match_ids)}; state rows: {count}")
    print(f"Run-margin audit: n={len(margin_errors)}, median={margin_errors[len(margin_errors)//2]}, p95={p95}, max={max(margin_errors)}")


if __name__ == "__main__":
    main()
