"""Historical in-pack top-ten tenure and phase matchups against elite opponents.

The tenure table is a prior-only T20I proxy, not an archived ICC ranking.
The ICC cohort is a dated current snapshot and is retrospective for matchups.
"""

from __future__ import annotations

import csv
from collections import Counter, defaultdict
from datetime import date, timedelta

from build_cumulative_dataset import DEFAULT_OUTPUT
from score_players import WICKET_RUN_VALUE


ICC_BATTING = [
    "Abhishek Sharma", "Sahibzada Farhan", "Ishan Kishan", "Harry Brook",
    "Jos Buttler", "Dewald Brevis", "Shreyas Iyer", "Phil Salt",
    "Shai Hope", "Pathum Nissanka",
]
ICC_BOWLING = [
    "Rashid Khan", "Adam Zampa", "Adil Rashid", "Abrar Ahmed",
    "Mitchell Santner", "Nathan Ellis", "Jamie Overton", "Nasum Ahmed",
    "Mahedi Hasan", "Liam Dawson",
]
ICC_URL = {
    "batting": "https://www.icc-cricket.com/rankings/batting/mens/t20i",
    "bowling": "https://www.icc-cricket.com/rankings/bowling/mens/t20i",
}
SNAPSHOT_DATE = "2026-11-03"
MIN_ROLLING_BALLS = 120
MIN_ROLLING_MATCHES = 8
MIN_MATCHUP_BALLS = 30
MIN_MATCHUP_MATCHES = 5
PRIOR_BALLS = 200


def month_starts(first: date, last: date):
    current = date(first.year, first.month, 1)
    while current <= last:
        yield current
        current = date(current.year + (current.month == 12), current.month % 12 + 1, 1)


def write_csv(name: str, fields: list[str], rows: list[dict]) -> None:
    with (DEFAULT_OUTPUT / name).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    with (DEFAULT_OUTPUT / "match_quality.csv").open(newline="", encoding="utf-8") as handle:
        poor = {
            row["match_id"] for row in csv.DictReader(handle)
            if row["approx_margin_error"] and int(row["approx_margin_error"]) > 7
        }
    with (DEFAULT_OUTPUT / "delivery_context.csv").open(newline="", encoding="utf-8") as handle:
        deliveries = [
            row for row in csv.DictReader(handle)
            if row["match_id"] not in poor
            and row["tier_stable_with_7_run_shift"] == "1"
        ]
    deliveries.sort(key=lambda row: (row["match_date"], row["match_id"],
                                     int(row["innings"]), int(row["innings_ball_num"])))
    names = defaultdict(set)
    for row in deliveries:
        names[("batting", row["striker_name"])].add(row["striker_id"])
        names[("bowling", row["bowler_name"])].add(row["bowler_id"])

    official_ids = {}
    snapshot_rows = []
    tied_ranks = {"batting": {6: 5}, "bowling": {4: 3}}
    for role, players in (("batting", ICC_BATTING), ("bowling", ICC_BOWLING)):
        for position, name in enumerate(players, 1):
            ids = names[(role, name)]
            if len(ids) > 1:
                raise ValueError(f"Ambiguous ICC name: {role} {name}: {ids}")
            pid = next(iter(ids), "")
            if pid:
                official_ids[(role, pid)] = position
            snapshot_rows.append({
                "snapshot_date": SNAPSHOT_DATE, "role": role,
                "table_order": position,
                "icc_rank": tied_ranks[role].get(position, position),
                "player_name": name, "player_id_in_pack": pid,
                "source_url": ICC_URL[role],
            })
    write_csv("icc_t20i_snapshot.csv", ["snapshot_date", "role", "table_order", "icc_rank",
              "player_name", "player_id_in_pack", "source_url"], snapshot_rows)

    # Monthly rank uses only the preceding 365 days. No delivery from the
    # snapshot month or later can determine that month's elite status.
    first = date.fromisoformat(deliveries[0]["match_date"])
    last = date.fromisoformat(deliveries[-1]["match_date"])
    monthly_rows = []
    by_month = {}
    tenure_at_month = {}
    tenure = defaultdict(lambda: {"months": 0, "rank_sum": 0, "best": 11,
                                  "first": "", "last": ""})
    t20 = [row for row in deliveries if row["scope"] == "T20I"]
    for snapshot in month_starts(first + timedelta(days=180), last):
        start = snapshot - timedelta(days=365)
        stats = defaultdict(Counter)
        match_sets = defaultdict(set)
        display = {}
        for row in t20:
            when = date.fromisoformat(row["match_date"])
            if when < start or when >= snapshot:
                continue
            for role, pid, name, unit, residual in outcomes(row):
                if not unit:
                    continue
                key = (role, pid)
                stats[key]["balls"] += unit
                stats[key]["impact"] += float(row["mismatch_weight"]) * residual
                match_sets[key].add(row["match_id"])
                display[key] = name
        selected = {}
        for role in ("batting", "bowling"):
            candidates = [
                (key, value) for key, value in stats.items()
                if key[0] == role and value["balls"] >= MIN_ROLLING_BALLS
                and len(match_sets[key]) >= MIN_ROLLING_MATCHES
            ]
            candidates.sort(key=lambda item: (
                -100 * item[1]["impact"] / (item[1]["balls"] + PRIOR_BALLS),
                -item[1]["balls"], item[0][1]
            ))
            for rank, (key, value) in enumerate(candidates[:10], 1):
                score = 100 * value["impact"] / (value["balls"] + PRIOR_BALLS)
                selected[key] = rank
                monthly_rows.append({
                    "snapshot_month": snapshot.isoformat(), "role": role,
                    "rank": rank, "player_id": key[1],
                    "player_name": display[key], "rolling_matches": len(match_sets[key]),
                    "rolling_balls": value["balls"], "rolling_proxy_score": round(score, 3),
                })
                rec = tenure[key]
                rec["months"] += 1
                rec["rank_sum"] += rank
                rec["best"] = min(rec["best"], rank)
                rec["first"] = rec["first"] or snapshot.isoformat()
                rec["last"] = snapshot.isoformat()
        by_month[snapshot.isoformat()] = selected
        tenure_at_month[snapshot.isoformat()] = {
            key: tenure[key]["months"] for key in selected
        }
    write_csv("elite_monthly_top10.csv", ["snapshot_month", "role", "rank",
              "player_id", "player_name", "rolling_matches", "rolling_balls",
              "rolling_proxy_score"], monthly_rows)

    tenure_rows = []
    for role in ("batting", "bowling"):
        peers = [(key, value) for key, value in tenure.items() if key[0] == role]
        peers.sort(key=lambda item: (-item[1]["months"],
                    item[1]["rank_sum"] / item[1]["months"], item[0][1]))
        for rank, (key, rec) in enumerate(peers, 1):
            tenure_rows.append({
                "role": role, "tenure_rank": rank, "player_id": key[1],
                "player_name": next(row["player_name"] for row in monthly_rows
                                    if row["role"] == role and row["player_id"] == key[1]),
                "top10_months": rec["months"],
                "mean_top10_rank": round(rec["rank_sum"] / rec["months"], 2),
                "best_rank": rec["best"], "first_top10_month": rec["first"],
                "last_top10_month": rec["last"],
                "in_current_icc_top10": int(key in official_ids),
            })
    write_csv("elite_tenure_rankings.csv", ["role", "tenure_rank", "player_id",
              "player_name", "top10_months", "mean_top10_rank", "best_rank",
              "first_top10_month", "last_top10_month", "in_current_icc_top10"], tenure_rows)

    # The historical cohort is assigned from the latest monthly snapshot
    # strictly before the match. The official cohort is retrospective only.
    matchups = defaultdict(Counter)
    matchup_matches = defaultdict(set)
    matchup_names = {}
    months = sorted(by_month)
    month_index = 0
    prior_month = None
    for row in deliveries:
        while month_index < len(months) and months[month_index] < row["match_date"]:
            prior_month = months[month_index]
            month_index += 1
        for role, pid, name, unit, residual in outcomes(row):
            if not unit or row["phase"] not in ("powerplay", "death"):
                continue
            opponent_role = "bowling" if role == "batting" else "batting"
            opponent_id = row["bowler_id"] if role == "batting" else row["striker_id"]
            cohorts = []
            if (opponent_role, opponent_id) in official_ids:
                cohorts.append("icc_2026_snapshot_retrospective")
            if (prior_month and (opponent_role, opponent_id) in by_month[prior_month]
                    and tenure_at_month[prior_month][(opponent_role, opponent_id)] >= 3):
                cohorts.append("prior_month_t20i_proxy_top10")
            for cohort in cohorts:
                key = (cohort, role, pid, row["phase"])
                stat = matchups[key]
                stat["balls"] += unit
                stat["impact"] += float(row["mismatch_weight"]) * residual
                stat["batter_runs"] += int(row["runs"]) if role == "batting" else 0
                stat["bowler_cost"] += int(row["observed_bowl_cost"]) if role == "bowling" else 0
                stat["wickets"] += int(row["bowler_wicket"]) if role == "bowling" else 0
                stat["scoreless_dots"] += int(row["runs"] == "0" and row["extras_type"] == "None" and row["is_legal"] == "1")
                matchup_matches[key].add(row["match_id"])
                matchup_names[key] = name
    matchup_rows = []
    for key, stat in matchups.items():
        cohort, role, pid, phase = key
        balls = stat["balls"]
        count = len(matchup_matches[key])
        score = 100 * stat["impact"] / (balls + 80)
        matchup_rows.append({
            "cohort": cohort, "role": role, "player_id": pid,
            "player_name": matchup_names[key], "phase": phase,
            "matches": count, "balls": balls, "impact": round(stat["impact"], 3),
            "residual_per_100": round(100 * stat["impact"] / balls, 3),
            "shrunk_score": round(score, 3) if balls >= MIN_MATCHUP_BALLS and count >= MIN_MATCHUP_MATCHES else "",
            "supported": int(balls >= MIN_MATCHUP_BALLS and count >= MIN_MATCHUP_MATCHES),
            "batting_strike_rate": round(100 * stat["batter_runs"] / balls, 2) if role == "batting" else "",
            "scoreless_dot_pct": round(100 * stat["scoreless_dots"] / balls, 2),
            "minimum_bowler_cost": stat["bowler_cost"] if role == "bowling" else "",
            "credited_wickets": stat["wickets"] if role == "bowling" else "",
        })
    matchup_rows.sort(key=lambda row: (row["cohort"], row["role"], row["phase"],
                                      -float(row["shrunk_score"] or -9999), row["player_name"]))
    write_csv("elite_phase_matchups.csv", ["cohort", "role", "player_id",
              "player_name", "phase", "matches", "balls", "impact",
              "residual_per_100", "shrunk_score", "supported",
              "batting_strike_rate", "scoreless_dot_pct",
              "minimum_bowler_cost", "credited_wickets"], matchup_rows)
    print(f"Historical monthly top-10 cells: {len(monthly_rows)}; tenure players: {len(tenure_rows)}")
    print(f"Elite phase matchup cells: {len(matchup_rows)}; supported: {sum(int(row['supported']) for row in matchup_rows)}")


def outcomes(row: dict[str, str]):
    runs = int(row["runs"])
    yield ("batting", row["striker_id"], row["striker_name"],
           int(row["extras_type"] != "wide"),
           runs - float(row["expected_bat_runs"])
           - WICKET_RUN_VALUE * (int(row["striker_out"]) - float(row["expected_bat_out"])))
    yield ("bowling", row["bowler_id"], row["bowler_name"], int(row["is_legal"]),
           float(row["expected_bowl_cost"]) - int(row["observed_bowl_cost"])
           + WICKET_RUN_VALUE * (int(row["bowler_wicket"]) - float(row["expected_bowl_wicket"])))


if __name__ == "__main__":
    main()
