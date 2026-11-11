"""Phase 3: derive pre-match team strength and prior-only expected outcomes."""

from __future__ import annotations

import csv
from collections import Counter, defaultdict

from build_cumulative_dataset import DEFAULT_INPUT, DEFAULT_OUTPUT, read_index
from build_match_state import STATE_FIELDS
from label_pressure import EXTRA_FIELDS


TEAM_FIELDS = [
    "match_id", "match_date", "scope", "home_team_id", "away_team_id",
    "home_elo_pre", "away_elo_pre", "home_rank_pre", "away_rank_pre",
    "home_games_pre", "away_games_pre", "elo_gap_pre", "mismatch_weight",
    "rating_source",
]
CONTEXT_FIELDS = [
    "scope", "phase", "home_elo_pre", "away_elo_pre", "home_rank_pre",
    "away_rank_pre", "mismatch_weight", "context_balls_prior",
    "venue_balls_prior", "country_balls_prior", "country_deliveries_prior",
    "country_run_factor", "country_wicket_factor",
    "venue_run_factor", "venue_wicket_factor",
    "opponent_bowling_factor", "batting_team_factor",
    "expected_bat_runs", "expected_bat_out", "expected_bowl_cost",
    "expected_bowl_wicket", "observed_bowl_cost", "striker_out",
    "bowler_wicket",
]
VENUE_FIELDS = [
    "match_id", "match_date", "scope", "venue_id", "venue_country",
    "phase", "venue_balls_prior", "country_balls_prior",
    "country_deliveries_prior", "country_run_factor", "country_wicket_factor",
    "venue_run_factor",
    "venue_wicket_factor",
]
CALIBRATION_FIELDS = [
    "scope", "year", "phase", "deliveries", "bat_balls", "actual_bat_runs",
    "expected_bat_runs", "actual_striker_outs", "expected_striker_outs",
    "actual_bowl_cost", "expected_bowl_cost", "actual_bowler_wickets",
    "expected_bowler_wickets",
]
BOWLER_WICKET_TYPES = {"Caught", "Bowled", "LBW", "Stump", "Hit Wicket"}


def scope_of(comp_name: str) -> str:
    return "IPL" if comp_name.startswith("IPL ") else "T20I"


def phase_of(overid: str) -> str:
    over = int(overid)
    return "powerplay" if over <= 6 else "middle" if over <= 15 else "death"


def rate(stats: Counter, numerator: str, denominator: str, prior: float, strength: int) -> float:
    return (stats[numerator] + strength * prior) / (stats[denominator] + strength)


def clip(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def team_strength() -> dict[str, dict]:
    matches = read_index(DEFAULT_INPUT / "matches.csv", "match_id")
    comps = read_index(DEFAULT_INPUT / "competitions.csv", "comp_id")
    quality = read_index(DEFAULT_OUTPUT / "match_quality.csv", "match_id")
    eligible = [m for mid, m in matches.items() if quality[mid]["eligible"] == "1"]
    eligible.sort(key=lambda m: (m["match_date"], int(m["match_id"])))
    universe: dict[str, set[str]] = defaultdict(set)
    for match in eligible:
        scope = scope_of(comps[match["comp_id"]]["comp_name"])
        universe[scope].update((match["home_team_id"], match["away_team_id"]))
    ratings: dict[tuple[str, str], float] = defaultdict(lambda: 1500.0)
    games: Counter = Counter()
    output: dict[str, dict] = {}
    by_date: dict[str, list[dict]] = defaultdict(list)
    for match in eligible:
        by_date[match["match_date"]].append(match)
    for date in sorted(by_date):
        rank_map = {}
        for scope, teams in universe.items():
            ordered = sorted(teams, key=lambda tid: (-ratings[(scope, tid)], int(tid)))
            rank_map[scope] = {tid: pos + 1 for pos, tid in enumerate(ordered)}
        daily_delta: Counter = Counter()
        daily_games: Counter = Counter()
        for match in by_date[date]:
            mid = match["match_id"]
            scope = scope_of(comps[match["comp_id"]]["comp_name"])
            home, away = match["home_team_id"], match["away_team_id"]
            hr, ar = ratings[(scope, home)], ratings[(scope, away)]
            hg, ag = games[(scope, home)], games[(scope, away)]
            h_rank, a_rank = rank_map[scope][home], rank_map[scope][away]
            best, worst = min(h_rank, a_rank), max(h_rank, a_rank)
            bottom_cutoff = 7 if scope == "IPL" else 13
            mismatch = (
                best <= 6 and worst >= bottom_cutoff and abs(hr - ar) >= 75
                and min(hg, ag) >= 5
            )
            output[mid] = {
                "match_id": mid, "match_date": date, "scope": scope,
                "home_team_id": home, "away_team_id": away,
                "home_elo_pre": round(hr, 3), "away_elo_pre": round(ar, 3),
                "home_rank_pre": h_rank, "away_rank_pre": a_rank,
                "home_games_pre": hg, "away_games_pre": ag,
                "elo_gap_pre": round(abs(hr - ar), 3),
                "mismatch_weight": 0.75 if mismatch else 1.0,
                "rating_source": "prior_dataset_results_elo_not_icc",
            }
            winner = match["win_team_id"]
            if winner not in (home, away):
                outcome = 0.5
            else:
                outcome = 1.0 if winner == home else 0.0
            expected_home = 1.0 / (1.0 + 10 ** ((ar - hr) / 400.0))
            delta = 24.0 * (outcome - expected_home)
            daily_delta[(scope, home)] += delta
            daily_delta[(scope, away)] -= delta
            daily_games[(scope, home)] += 1
            daily_games[(scope, away)] += 1
        for key, delta in daily_delta.items():
            ratings[key] += delta
        games.update(daily_games)
    with (DEFAULT_OUTPUT / "team_strength.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=TEAM_FIELDS)
        writer.writeheader()
        writer.writerows(output[mid] for mid in sorted(output, key=lambda x: (
            output[x]["match_date"], int(x)
        )))
    return output


def expected_context(teams: dict[str, dict]) -> None:
    with (DEFAULT_OUTPUT / "pressure_delivery.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    rows.sort(key=lambda r: (
        r["match_date"], int(r["match_id"]), int(r["innings"]),
        int(r["innings_ball_num"]),
    ))
    global_stats: dict[str, Counter] = defaultdict(Counter)
    phase_stats: dict[tuple[str, str], Counter] = defaultdict(Counter)
    year_phase_stats: dict[tuple[str, str, str], Counter] = defaultdict(Counter)
    year_exact_stats: dict[tuple[str, str, str, str, str], Counter] = defaultdict(Counter)
    country_stats: dict[tuple[str, str, str], Counter] = defaultdict(Counter)
    venue_stats: dict[tuple[str, str, str], Counter] = defaultdict(Counter)
    batting_team_stats: dict[tuple[str, str], Counter] = defaultdict(Counter)
    bowling_team_stats: dict[tuple[str, str], Counter] = defaultdict(Counter)
    venue_rows: dict[tuple[str, str], dict] = {}
    calibration: dict[tuple[str, str, str], Counter] = defaultdict(Counter)
    date_groups: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        date_groups[row["match_date"]].append(row)
    count = 0
    with (DEFAULT_OUTPUT / "delivery_context.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=STATE_FIELDS + EXTRA_FIELDS + CONTEXT_FIELDS)
        writer.writeheader()
        for date in sorted(date_groups):
            daily = date_groups[date]
            for row in daily:
                mid = row["match_id"]
                scope = teams[mid]["scope"]
                phase = phase_of(row["overid"])
                year = date[:4]
                style = row["pace_or_spin"]
                hand = row["batting_type"]
                fmt = global_stats[scope]
                stage_all = phase_stats[(scope, phase)]
                stage = year_phase_stats[(scope, year, phase)]
                exact = year_exact_stats[(scope, year, phase, style, hand)]
                country = country_stats[(scope, row["venue_country"], phase)]
                venue = venue_stats[(scope, row["venue_id"], phase)]
                batting_team = batting_team_stats[(scope, row["batting_team_id"])]
                bowling_team = bowling_team_stats[(scope, row["bowling_team_id"])]

                global_bat = rate(fmt, "bat_runs", "bat_balls", 1.20, 300)
                stage_bat_prior = rate(stage_all, "bat_runs", "bat_balls", global_bat, 200)
                stage_bat = rate(stage, "bat_runs", "bat_balls", stage_bat_prior, 400)
                exact_bat = rate(exact, "bat_runs", "bat_balls", stage_bat, 300)
                global_out = rate(fmt, "bat_outs", "bat_balls", 0.05, 300)
                stage_out_prior = rate(stage_all, "bat_outs", "bat_balls", global_out, 200)
                stage_out = rate(stage, "bat_outs", "bat_balls", stage_out_prior, 400)
                exact_out = rate(exact, "bat_outs", "bat_balls", stage_out, 300)
                global_cost = rate(fmt, "bowl_cost", "deliveries", 1.25, 300)
                stage_cost_prior = rate(stage_all, "bowl_cost", "deliveries", global_cost, 200)
                stage_cost = rate(stage, "bowl_cost", "deliveries", stage_cost_prior, 400)
                exact_cost = rate(exact, "bowl_cost", "deliveries", stage_cost, 300)
                global_wicket = rate(fmt, "bowler_wickets", "deliveries", 0.045, 300)
                stage_wicket_prior = rate(stage_all, "bowler_wickets", "deliveries", global_wicket, 200)
                stage_wicket = rate(stage, "bowler_wickets", "deliveries", stage_wicket_prior, 400)
                exact_wicket = rate(exact, "bowler_wickets", "deliveries", stage_wicket, 300)

                country_bat = rate(country, "bat_runs", "bat_balls", stage_bat, 1000)
                country_run_factor = clip(country_bat / stage_bat, 0.8, 1.2)
                venue_bat = rate(venue, "bat_runs", "bat_balls", country_bat, 300)
                venue_run_factor = clip(venue_bat / stage_bat, 0.8, 1.2)
                country_wicket = rate(country, "bowler_wickets", "deliveries", stage_wicket, 1000)
                country_wicket_factor = clip(country_wicket / stage_wicket, 0.75, 1.25)
                venue_wicket = rate(venue, "bowler_wickets", "deliveries", country_wicket, 300)
                venue_wicket_factor = clip(venue_wicket / stage_wicket, 0.75, 1.25)
                opponent_rate = rate(bowling_team, "bat_runs", "bat_balls", global_bat, 500)
                opponent_factor = clip(opponent_rate / global_bat, 0.85, 1.15)
                batting_rate = rate(batting_team, "bat_runs", "bat_balls", global_bat, 500)
                batting_factor = clip(batting_rate / global_bat, 0.85, 1.15)
                opponent_wicket = rate(
                    bowling_team, "bowler_wickets", "deliveries", global_wicket, 500
                )
                opponent_wicket_factor = clip(opponent_wicket / global_wicket, 0.75, 1.25)
                batting_out = rate(batting_team, "bat_outs", "bat_balls", global_out, 500)
                batting_out_factor = clip(batting_out / global_out, 0.75, 1.25)

                bat_expected = exact_bat * venue_run_factor * opponent_factor
                bat_out_expected = clip(
                    exact_out * venue_wicket_factor * opponent_wicket_factor, 0.005, 0.20
                )
                bowl_expected = exact_cost * venue_run_factor * batting_factor
                wicket_expected = clip(
                    exact_wicket * venue_wicket_factor * batting_out_factor, 0.005, 0.20
                )
                extra = row["extras_type"]
                observed_cost = int(row["runs"]) + int(extra in ("wide", "Overstep"))
                striker_out = int(
                    row["is_wicket"].lower() == "true"
                    and row["dismissed_player_id"] not in ("", "None")
                    and int(float(row["dismissed_player_id"])) == int(row["striker_id"])
                )
                credited_wicket = int(
                    row["is_wicket"].lower() == "true"
                    and row["dismissal_type"] in BOWLER_WICKET_TYPES
                )
                cal = calibration[(scope, date[:4], phase)]
                cal["deliveries"] += 1
                cal["actual_bowl_cost"] += observed_cost
                cal["expected_bowl_cost"] += bowl_expected
                cal["actual_bowler_wickets"] += credited_wicket
                cal["expected_bowler_wickets"] += wicket_expected
                if extra != "wide":
                    cal["bat_balls"] += 1
                    cal["actual_bat_runs"] += int(row["runs"])
                    cal["expected_bat_runs"] += bat_expected
                    cal["actual_striker_outs"] += striker_out
                    cal["expected_striker_outs"] += bat_out_expected
                t = teams[mid]
                writer.writerow({
                    **row, "scope": scope, "phase": phase,
                    "home_elo_pre": t["home_elo_pre"], "away_elo_pre": t["away_elo_pre"],
                    "home_rank_pre": t["home_rank_pre"],
                    "away_rank_pre": t["away_rank_pre"],
                    "mismatch_weight": t["mismatch_weight"],
                    "context_balls_prior": exact["bat_balls"],
                    "venue_balls_prior": venue["bat_balls"],
                    "country_balls_prior": country["bat_balls"],
                    "country_deliveries_prior": country["deliveries"],
                    "country_run_factor": round(country_run_factor, 6),
                    "country_wicket_factor": round(country_wicket_factor, 6),
                    "venue_run_factor": round(venue_run_factor, 6),
                    "venue_wicket_factor": round(venue_wicket_factor, 6),
                    "opponent_bowling_factor": round(opponent_factor, 6),
                    "batting_team_factor": round(batting_factor, 6),
                    "expected_bat_runs": round(bat_expected, 6),
                    "expected_bat_out": round(bat_out_expected, 6),
                    "expected_bowl_cost": round(bowl_expected, 6),
                    "expected_bowl_wicket": round(wicket_expected, 6),
                    "observed_bowl_cost": observed_cost,
                    "striker_out": striker_out, "bowler_wicket": credited_wicket,
                })
                venue_key = (mid, phase)
                if venue_key not in venue_rows:
                    venue_rows[venue_key] = {
                        "match_id": mid, "match_date": date, "scope": scope,
                        "venue_id": row["venue_id"],
                        "venue_country": row["venue_country"], "phase": phase,
                        "venue_balls_prior": venue["bat_balls"],
                        "country_balls_prior": country["bat_balls"],
                        "country_deliveries_prior": country["deliveries"],
                        "country_run_factor": round(country_run_factor, 6),
                        "country_wicket_factor": round(country_wicket_factor, 6),
                        "venue_run_factor": round(venue_run_factor, 6),
                        "venue_wicket_factor": round(venue_wicket_factor, 6),
                    }
                count += 1

            # Learn from the whole day only after every prediction for that day.
            for row in daily:
                scope = teams[row["match_id"]]["scope"]
                phase = phase_of(row["overid"])
                year = date[:4]
                style, hand = row["pace_or_spin"], row["batting_type"]
                runs = int(row["runs"])
                faced = row["extras_type"] != "wide"
                cost = runs + int(row["extras_type"] in ("wide", "Overstep"))
                striker_out = int(
                    row["is_wicket"].lower() == "true"
                    and row["dismissed_player_id"] not in ("", "None")
                    and int(float(row["dismissed_player_id"])) == int(row["striker_id"])
                )
                wicket = int(
                    row["is_wicket"].lower() == "true"
                    and row["dismissal_type"] in BOWLER_WICKET_TYPES
                )
                for cell in (
                    global_stats[scope], phase_stats[(scope, phase)],
                    year_phase_stats[(scope, year, phase)],
                    year_exact_stats[(scope, year, phase, style, hand)],
                    country_stats[(scope, row["venue_country"], phase)],
                    venue_stats[(scope, row["venue_id"], phase)],
                ):
                    cell["bat_runs"] += runs
                    cell["bat_balls"] += faced
                    cell["bat_outs"] += striker_out
                    cell["bowl_cost"] += cost
                    cell["deliveries"] += 1
                    cell["bowler_wickets"] += wicket
                for cell in (
                    batting_team_stats[(scope, row["batting_team_id"])],
                    bowling_team_stats[(scope, row["bowling_team_id"])],
                ):
                    cell["bat_runs"] += runs
                    cell["bat_balls"] += faced
                    cell["bat_outs"] += striker_out
                    cell["deliveries"] += 1
                    cell["bowler_wickets"] += wicket
    with (DEFAULT_OUTPUT / "venue_pre_match.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=VENUE_FIELDS)
        writer.writeheader()
        writer.writerows(sorted(venue_rows.values(), key=lambda r: (
            r["match_date"], int(r["match_id"]), r["phase"]
        )))
    with (DEFAULT_OUTPUT / "context_calibration.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CALIBRATION_FIELDS)
        writer.writeheader()
        for (scope, year, phase), stats in sorted(calibration.items()):
            writer.writerow({
                "scope": scope, "year": year, "phase": phase,
                **{field: round(stats[field], 3) for field in CALIBRATION_FIELDS[3:]},
            })
    print(f"Team-strength matches: {len(teams)}; discounted: {sum(float(x['mismatch_weight']) < 1 for x in teams.values())}")
    print(f"Delivery context rows: {count}; venue-match-phase rows: {len(venue_rows)}")


def main() -> None:
    teams = team_strength()
    expected_context(teams)


if __name__ == "__main__":
    main()
