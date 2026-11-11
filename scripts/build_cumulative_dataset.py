"""Build auditable player, series, and venue aggregates from the supplied CSVs.

Run with the project's virtual-environment Python. This stage intentionally does
not assign pressure labels or player ranks.
"""

from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "6af3166e7b922_data_pack"
DEFAULT_OUTPUT = ROOT / "data" / "processed"

META_FIELDS = [
    "match_date", "match_id", "comp_id", "comp_name", "match_format", "season",
    "venue_id", "venue_country", "knock_out", "result", "analysis_eligible",
    "exclusion_reason", "team_id", "opponent_team_id", "player_id",
    "player_name", "role",
]
METRICS = [
    "bat_deliveries_seen", "bat_balls_faced", "bat_runs", "bat_fours",
    "bat_sixes", "bat_zero_run_balls", "bat_outs", "bat_pace_balls",
    "bat_pace_runs", "bat_pace_outs", "bat_spin_balls", "bat_spin_runs",
    "bat_spin_outs", "bowl_deliveries", "bowl_legal_balls",
    "bowl_batter_runs_allowed", "bowl_zero_batter_run_legal_balls",
    "bowl_fours_allowed", "bowl_sixes_allowed", "bowl_wides", "bowl_no_balls",
    "bowl_wickets", "bowl_wicket_caught", "bowl_wicket_bowled",
    "bowl_wicket_lbw", "bowl_wicket_stumped", "bowl_wicket_hit_wicket",
    "bowl_rhb_legal_balls", "bowl_rhb_batter_runs_allowed",
    "bowl_rhb_wickets", "bowl_lhb_legal_balls",
    "bowl_lhb_batter_runs_allowed", "bowl_lhb_wickets",
]
CUMULATIVE_METRICS = [
    "bat_balls_faced", "bat_runs", "bat_fours", "bat_sixes", "bat_outs",
    "bat_pace_balls", "bat_pace_runs", "bat_spin_balls", "bat_spin_runs",
    "bowl_legal_balls", "bowl_batter_runs_allowed", "bowl_wickets",
    "bowl_wides", "bowl_no_balls", "bowl_rhb_legal_balls",
    "bowl_rhb_batter_runs_allowed", "bowl_rhb_wickets",
    "bowl_lhb_legal_balls", "bowl_lhb_batter_runs_allowed",
    "bowl_lhb_wickets",
]
BOWLER_WICKET_TYPES = {
    "Caught": "bowl_wicket_caught",
    "Bowled": "bowl_wicket_bowled",
    "LBW": "bowl_wicket_lbw",
    "Stump": "bowl_wicket_stumped",
    "Hit Wicket": "bowl_wicket_hit_wicket",
}


def read_index(path: Path, key: str) -> dict[str, dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return {row[key]: row for row in csv.DictReader(handle)}


def as_int(value: str) -> int:
    return int(value) if value else 0


def player_id(value: str) -> str:
    # dismissed_player_id is encoded as a decimal-looking field in the CSV.
    return str(int(float(value))) if value else ""


def match_reason(match: dict[str, str], comp: dict[str, str]) -> str:
    result = match["result"].lower()
    if "abandon" in result or "no result" in result:
        return "abandoned_or_no_result"
    if any(match[field] for field in (
        "first_inn_revised_overs", "second_inn_revised_overs", "revised_target"
    )) or "d/l" in result or "dls" in result:
        return "revised_match"
    if comp["match_format"] == "T20I" or comp["comp_name"].startswith("IPL "):
        return ""
    return "outside_ipl_t20i_scope"


def write_rows(path: Path, fields: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def build(input_dir: Path, output_dir: Path) -> None:
    competitions = read_index(input_dir / "competitions.csv", "comp_id")
    matches = read_index(input_dir / "matches.csv", "match_id")
    names: dict[str, str] = {}
    with (input_dir / "competition_team_player_mapping.csv").open(
        newline="", encoding="utf-8-sig"
    ) as handle:
        for row in csv.DictReader(handle):
            names.setdefault(row["player_id"], row["player_name"])

    match_context: dict[str, dict[str, str]] = {}
    for match_id, match in matches.items():
        comp = competitions[match["comp_id"]]
        reason = match_reason(match, comp)
        match_context[match_id] = {
            "match_date": match["match_date"],
            "match_id": match_id,
            "comp_id": match["comp_id"],
            "comp_name": comp["comp_name"],
            "match_format": comp["match_format"],
            "season": comp["season"],
            "venue_id": match["venue_id"],
            "venue_country": match["venue_country"],
            "knock_out": match["knock_out"],
            "result": match["result"],
            "analysis_eligible": "1" if not reason else "0",
            "exclusion_reason": reason,
        }

    player_match: dict[tuple[str, str, str, str], dict] = {}
    venue_stats: dict[tuple[str, str, str], dict] = defaultdict(
        lambda: {"matches": set(), "stats": Counter()}
    )
    seen_delivery_keys: set[tuple[str, str, str, str]] = set()
    source_totals = Counter()

    def get_player_row(
        match_id: str, role: str, pid: str, name: str, team_id: str,
        opponent_team_id: str,
    ) -> dict:
        key = (match_id, role, pid, team_id)
        if key not in player_match:
            player_match[key] = {
                **match_context[match_id],
                "team_id": team_id,
                "opponent_team_id": opponent_team_id,
                "player_id": pid,
                "player_name": names.get(pid, name),
                "role": role,
                "stats": Counter(),
            }
        return player_match[key]

    with (input_dir / "ball_by_ball.csv").open(
        newline="", encoding="utf-8-sig"
    ) as handle:
        for ball in csv.DictReader(handle):
            mid = ball["match_id"]
            if mid not in match_context:
                raise ValueError(f"Delivery references unknown match {mid}")
            ball_key = (mid, ball["innings"], ball["overid"], ball["over_ball_num"])
            if ball_key in seen_delivery_keys:
                raise ValueError(f"Duplicate delivery key {ball_key}")
            seen_delivery_keys.add(ball_key)
            source_totals["all_deliveries"] += 1
            if as_int(ball["innings"]) > 2:
                source_totals["super_over_deliveries_excluded"] += 1
                continue

            context = match_context[mid]
            eligible = context["analysis_eligible"] == "1"
            runs = as_int(ball["runs"])
            extra = ball["extras_type"]
            is_wide = extra == "wide"
            is_no_ball = extra == "Overstep"
            is_legal = not (is_wide or is_no_ball)
            is_wicket = ball["is_wicket"].lower() == "true"
            bowling_class = ball["pace_or_spin"].lower()
            hand = ball["batting_type"].lower()

            batter = get_player_row(
                mid, "batting", ball["striker_id"], ball["striker_name"],
                ball["batting_team_id"], ball["bowling_team_id"],
            )["stats"]
            batter["bat_deliveries_seen"] += 1
            batter["bat_runs"] += runs
            if not is_wide:
                batter["bat_balls_faced"] += 1
                if runs == 0:
                    batter["bat_zero_run_balls"] += 1
                if bowling_class in ("pace", "spin"):
                    batter[f"bat_{bowling_class}_balls"] += 1
            if bowling_class in ("pace", "spin"):
                batter[f"bat_{bowling_class}_runs"] += runs
            if ball["is_four"].lower() == "true":
                batter["bat_fours"] += 1
            if ball["is_six"].lower() == "true":
                batter["bat_sixes"] += 1

            bowler = get_player_row(
                mid, "bowling", ball["bowler_id"], ball["bowler_name"],
                ball["bowling_team_id"], ball["batting_team_id"],
            )["stats"]
            bowler["bowl_deliveries"] += 1
            bowler["bowl_batter_runs_allowed"] += runs
            if is_legal:
                bowler["bowl_legal_balls"] += 1
                if runs == 0:
                    bowler["bowl_zero_batter_run_legal_balls"] += 1
                if hand in ("rhb", "lhb"):
                    bowler[f"bowl_{hand}_legal_balls"] += 1
            if hand in ("rhb", "lhb"):
                bowler[f"bowl_{hand}_batter_runs_allowed"] += runs
            if ball["is_four"].lower() == "true":
                bowler["bowl_fours_allowed"] += 1
            if ball["is_six"].lower() == "true":
                bowler["bowl_sixes_allowed"] += 1
            if is_wide:
                bowler["bowl_wides"] += 1
            if is_no_ball:
                bowler["bowl_no_balls"] += 1

            if is_wicket:
                dismissed = player_id(ball["dismissed_player_id"])
                if dismissed:
                    dismissed_name = (
                        ball["striker_name"] if dismissed == ball["striker_id"]
                        else ball["non_striker_name"] if dismissed == ball["non_striker_id"]
                        else names.get(dismissed, "")
                    )
                    out = get_player_row(
                        mid, "batting", dismissed, dismissed_name,
                        ball["batting_team_id"], ball["bowling_team_id"],
                    )["stats"]
                    out["bat_outs"] += 1
                    if dismissed == ball["striker_id"] and bowling_class in ("pace", "spin"):
                        out[f"bat_{bowling_class}_outs"] += 1
                else:
                    source_totals["wickets_without_dismissed_player"] += 1
                wicket_metric = BOWLER_WICKET_TYPES.get(ball["dismissal_type"])
                if wicket_metric:
                    bowler["bowl_wickets"] += 1
                    bowler[wicket_metric] += 1
                    if hand in ("rhb", "lhb"):
                        bowler[f"bowl_{hand}_wickets"] += 1

            if eligible:
                source_totals["eligible_deliveries"] += 1
                source_totals["eligible_bat_runs"] += runs
                source_totals["eligible_bowl_batter_runs_allowed"] += runs
                source_totals["eligible_bat_balls_faced"] += not is_wide
                source_totals["eligible_bowl_legal_balls"] += is_legal
                vkey = (context["venue_id"], context["venue_country"], context["match_format"])
                venue = venue_stats[vkey]
                venue["matches"].add(mid)
                vstats = venue["stats"]
                vstats["deliveries"] += 1
                vstats["legal_balls"] += is_legal
                vstats["batter_runs"] += runs
                vstats["bowler_wickets"] += is_wicket and ball["dismissal_type"] in BOWLER_WICKET_TYPES
                if bowling_class in ("pace", "spin"):
                    vstats[f"{bowling_class}_legal_balls"] += is_legal
                    vstats[f"{bowling_class}_batter_runs"] += runs
                    vstats[f"{bowling_class}_bowler_wickets"] += (
                        is_wicket and ball["dismissal_type"] in BOWLER_WICKET_TYPES
                    )

    rows = sorted(
        player_match.values(),
        key=lambda row: (
            row["match_date"], int(row["match_id"]), int(row["player_id"]), row["role"],
        ),
    )
    career_totals: dict[tuple[str, str], Counter] = defaultdict(Counter)
    format_totals: dict[tuple[str, str, str], Counter] = defaultdict(Counter)
    series_totals: dict[tuple[str, str, str, str], dict] = {}
    output_rows: list[dict] = []
    for row in rows:
        stats = row.pop("stats")
        role_key = (row["player_id"], row["role"])
        format_key = (*role_key, row["match_format"])
        ctotal = career_totals[role_key]
        ftotal = format_totals[format_key]
        series_key = (row["comp_id"], row["team_id"], row["player_id"], row["role"])
        if series_key not in series_totals:
            series_totals[series_key] = {
                "comp_id": row["comp_id"], "comp_name": row["comp_name"],
                "match_format": row["match_format"], "season": row["season"],
                "team_id": row["team_id"], "player_id": row["player_id"],
                "player_name": row["player_name"], "role": row["role"],
                "matches": 0, "eligible_matches": 0, "stats": Counter(),
            }
        srow = series_totals[series_key]
        srow["matches"] += 1
        if row["analysis_eligible"] == "1":
            ctotal["matches"] += 1
            ftotal["matches"] += 1
            srow["eligible_matches"] += 1
            for metric in METRICS:
                ctotal[metric] += stats[metric]
                ftotal[metric] += stats[metric]
                srow["stats"][metric] += stats[metric]
        flat = {**row, **{metric: stats[metric] for metric in METRICS}}
        flat["cum_matches"] = ctotal["matches"]
        flat["cum_format_matches"] = ftotal["matches"]
        for metric in CUMULATIVE_METRICS:
            flat[f"cum_{metric}"] = ctotal[metric]
            flat[f"cum_format_{metric}"] = ftotal[metric]
        output_rows.append(flat)

    eligible_rows = [row for row in output_rows if row["analysis_eligible"] == "1"]
    for metric, source_metric in (
        ("bat_runs", "eligible_bat_runs"),
        ("bowl_batter_runs_allowed", "eligible_bowl_batter_runs_allowed"),
        ("bat_balls_faced", "eligible_bat_balls_faced"),
        ("bowl_legal_balls", "eligible_bowl_legal_balls"),
    ):
        actual = sum(row[metric] for row in eligible_rows)
        expected = source_totals[source_metric]
        if actual != expected:
            raise AssertionError(f"{metric}: aggregate {actual} != source {expected}")

    output_dir.mkdir(parents=True, exist_ok=True)
    cumulative_fields = (
        META_FIELDS + METRICS + ["cum_matches", "cum_format_matches"]
        + [item for metric in CUMULATIVE_METRICS for item in (
            f"cum_{metric}", f"cum_format_{metric}"
        )]
    )
    write_rows(output_dir / "player_match_cumulative.csv", cumulative_fields, output_rows)

    series_fields = [
        "comp_id", "comp_name", "match_format", "season", "team_id",
        "player_id", "player_name", "role", "matches", "eligible_matches",
    ] + METRICS
    series_rows = []
    for srow in sorted(series_totals.values(), key=lambda r: (
        int(r["comp_id"]), int(r["team_id"]), int(r["player_id"]), r["role"]
    )):
        stats = srow.pop("stats")
        series_rows.append({**srow, **{metric: stats[metric] for metric in METRICS}})
    write_rows(output_dir / "player_series_summary.csv", series_fields, series_rows)

    summary_fields = [
        "player_id", "player_name", "role", "scope", "matches",
    ] + METRICS
    summary_rows = []
    for (pid, role), stats in sorted(
        career_totals.items(), key=lambda item: (int(item[0][0]), item[0][1])
    ):
        if stats["matches"]:
            summary_rows.append({
                "player_id": pid, "player_name": names.get(pid, ""),
                "role": role, "scope": "ALL", "matches": stats["matches"],
                **{metric: stats[metric] for metric in METRICS},
            })
    for (pid, role, fmt), stats in sorted(
        format_totals.items(),
        key=lambda item: (int(item[0][0]), item[0][1], item[0][2]),
    ):
        if stats["matches"]:
            summary_rows.append({
                "player_id": pid, "player_name": names.get(pid, ""),
                "role": role, "scope": "IPL" if fmt == "T20" else fmt,
                "matches": stats["matches"],
                **{metric: stats[metric] for metric in METRICS},
            })
    write_rows(output_dir / "player_cumulative_summary.csv", summary_fields, summary_rows)

    venue_fields = [
        "venue_id", "venue_country", "match_format", "matches", "deliveries",
        "legal_balls", "batter_runs", "bowler_wickets", "pace_legal_balls",
        "pace_batter_runs", "pace_bowler_wickets", "spin_legal_balls",
        "spin_batter_runs", "spin_bowler_wickets",
    ]
    venue_rows = []
    for (venue_id, country, fmt), venue in sorted(
        venue_stats.items(), key=lambda item: (int(item[0][0]), item[0][2])
    ):
        stats = venue["stats"]
        venue_rows.append({
            "venue_id": venue_id, "venue_country": country, "match_format": fmt,
            "matches": len(venue["matches"]),
            **{metric: stats[metric] for metric in venue_fields[4:]},
        })
    write_rows(output_dir / "venue_context.csv", venue_fields, venue_rows)

    print(f"Source deliveries: {source_totals['all_deliveries']}")
    print(f"Super-over deliveries excluded: {source_totals['super_over_deliveries_excluded']}")
    print(f"Eligible deliveries: {source_totals['eligible_deliveries']}")
    print(f"Wickets without dismissed player ID: {source_totals['wickets_without_dismissed_player']}")
    print(f"Player-match rows: {len(output_rows)} ({len(eligible_rows)} eligible)")
    print(f"Player-series rows: {len(series_rows)}")
    print(f"Player cumulative summary rows: {len(summary_rows)}")
    print(f"Venue-format rows: {len(venue_rows)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    build(args.input, args.output)
