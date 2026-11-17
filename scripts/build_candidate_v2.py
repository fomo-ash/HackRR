"""Build a separate pressure-aware ranking candidate and chronological audit.

This does not replace the submitted Phase 4 rankings. It uses exact chase scores
where the independently matched Cricsheet cache is available, prior-date
pressure-state residual calibration, and a conservative pressure-only score.
"""

from __future__ import annotations

import csv
import gzip
import random
from collections import Counter, defaultdict
from pathlib import Path

from build_cumulative_dataset import DEFAULT_OUTPUT
from score_players import add_score, bootstrap as old_bootstrap, percentile, score as old_score

ROOT = Path(__file__).resolve().parents[1]
EXTRAS = ROOT / "data" / "external" / "cricsheet_extras.csv.gz"
SUMMARY_FIELDS = [
    "role", "player_id", "player_name", "eligible", "rank", "pressure_effective_balls",
    "pressure_matches", "high_pressure_balls", "low_balls", "pressure_rate_per_100",
    "low_rate_per_100", "pressure_uplift_per_100", "shrunk_pressure_score",
    "bootstrap_p10", "bootstrap_p90", "conservative_score", "positive_match_share",
]
CAL_FIELDS = ["year", "scope", "role", "phase", "tier", "balls", "raw_residual_per_100", "adjusted_residual_per_100"]
PRESSURE_FIELDS = ["year", "scope", "innings", "phase", "tier", "deliveries"]
BACKTEST_FIELDS = ["train_through", "test_year", "gate", "role", "players", "method", "rank_correlation", "top10_future_rate", "top10_future_positive_share"]


def read_bad_matches() -> set[str]:
    with (DEFAULT_OUTPUT / "match_quality.csv").open(newline="", encoding="utf-8") as stream:
        return {row["match_id"] for row in csv.DictReader(stream)
                if row["approx_margin_error"] and int(row["approx_margin_error"]) > 7}


def read_exact() -> tuple[dict[str, int], dict[tuple[str, str, str], int]]:
    with (DEFAULT_OUTPUT / "exact_score_coverage.csv").open(newline="", encoding="utf-8") as stream:
        totals = {row["match_id"]: int(row["first_verified_total"])
                  for row in csv.DictReader(stream) if row["status"] == "verified"}
    extras = {}
    with gzip.open(EXTRAS, "rt", newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            if row["match_id"] in totals:
                extras[(row["match_id"], row["innings"], row["innings_ball_num"])] = int(row["extras_runs"])
    return totals, extras


def pressure_score(row: dict[str, str], required: int) -> int:
    over = int(row["overid"])
    wickets = int(row["wickets_before"])
    remaining = max(1, int(row["balls_remaining"]))
    phase = 0 if over <= 6 else 10 if over <= 15 else 24 if over <= 18 else 34
    wicket = 0 if wickets <= 2 else 7 if wickets <= 4 else 14 if wickets <= 6 else 20
    collapse = 15 if over <= 6 and wickets >= 2 else 0
    chase = 0
    if row["innings"] == "2" and required > 0:
        rate = required / remaining
        if rate < 0.8:
            chase = 0
        elif rate <= 1.6:
            chase = 26 if remaining > 60 else 28 if remaining > 36 else 22
        elif rate <= 2.3:
            chase = 13 if remaining > 60 else 19 if remaining > 36 else 22
        else:
            chase = 7 if remaining > 36 else 15
        if rate >= 1.35 and wickets >= 6:
            chase += 8
    return min(100, phase + wicket + collapse + chase + 10 * (row["knock_out"] == "1"))


def tier(points: int) -> str:
    return "high" if points >= 50 else "medium" if points >= 30 else "low"


def pressure_point(stats: Counter) -> float:
    balls = stats["pressure_effective_balls"]
    if not balls:
        return 0.0
    return 100 * stats["pressure_impact"] / (balls + 80)


def combine(match_stats: list[Counter]) -> Counter:
    total = Counter()
    for stats in match_stats:
        total.update(stats)
    return total


def eligible(stats: Counter, matches: list[Counter], pballs=100, pmatches=20, low=50) -> bool:
    return (stats["pressure_effective_balls"] >= pballs
            and sum(s["pressure_effective_balls"] > 0 for s in matches) >= pmatches
            and stats["low_balls"] >= low)


def bootstrap(matches: list[Counter], pid: str, role: str) -> tuple[float, float]:
    rng = random.Random(422 + int(pid) + (100000 if role == "bowling" else 0))
    samples = []
    for _ in range(300):
        samples.append(pressure_point(combine([matches[rng.randrange(len(matches))]
                                                for _ in matches])))
    return percentile(samples, .10), percentile(samples, .90)


def rank(values: list[float]) -> list[int]:
    ordered = sorted(range(len(values)), key=lambda pos: values[pos])
    out = [0] * len(values)
    for place, pos in enumerate(ordered):
        out[pos] = place
    return out


def spearman(x: list[float], y: list[float]) -> float:
    left, right = rank(x), rank(y)
    n = len(x)
    return 1 - 6 * sum((a-b)**2 for a, b in zip(left, right)) / (n * (n*n-1))


def main() -> None:
    bad_matches = read_bad_matches()
    exact_totals, exact_extras = read_exact()
    seen_extras: Counter = Counter()
    prior: dict[tuple, Counter] = defaultdict(Counter)
    pending: dict[tuple, Counter] = defaultdict(Counter)
    last_date = ""
    names: dict[tuple[str, str], str] = {}
    groups: dict[tuple[str, str, int, str], Counter] = defaultdict(Counter)
    old_groups: dict[tuple[str, str, int, str], Counter] = defaultdict(Counter)
    calibration: dict[tuple, Counter] = defaultdict(Counter)
    pressure_counts: Counter = Counter()
    skipped_unstable = 0
    skipped_bad = 0
    seen_exact_keys = 0

    with (DEFAULT_OUTPUT / "delivery_context.csv").open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            date = row["match_date"]
            if last_date and date != last_date:
                for key, stats in pending.items():
                    prior[key].update(stats)
                pending.clear()
            last_date = date
            mid, innings, seq = row["match_id"], row["innings"], row["innings_ball_num"]
            year, scope, phase = int(date[:4]), row["scope"], row["phase"]
            verified = mid in exact_totals
            exact_key = (mid, innings, seq)
            if verified and exact_key not in exact_extras:
                raise ValueError(f"Verified delivery missing extras: {exact_key}")
            if verified and innings == "2":
                required = max(0, exact_totals[mid] + 1 - int(row["bat_runs_before"])
                               - seen_extras[(mid, innings)])
            else:
                required = int(row["runs_required_approx"]) if innings == "2" else 0
            if verified:
                seen_extras[(mid, innings)] += exact_extras[exact_key]
                seen_exact_keys += 1

            old_valid = mid not in bad_matches and row["tier_stable_with_7_run_shift"] == "1"
            new_points = pressure_score(row, required)
            new_tier = tier(new_points)
            if innings == "2" and not verified:
                stable = (tier(pressure_score(row, max(0, required - 7))) == new_tier
                          and tier(pressure_score(row, required + 7)) == new_tier)
            else:
                stable = True
            if not stable:
                skipped_unstable += 1
            if mid in bad_matches and not verified:
                skipped_bad += 1
            new_valid = stable and (mid not in bad_matches or verified)
            if new_valid:
                pressure_counts[(year, scope, innings, phase, new_tier)] += 1

            for role, pid, name, unit, raw in (
                ("batting", row["striker_id"], row["striker_name"], row["extras_type"] != "wide",
                 int(row["runs"]) - float(row["expected_bat_runs"])
                 - 5 * (int(row["striker_out"]) - float(row["expected_bat_out"]))),
                ("bowling", row["bowler_id"], row["bowler_name"], row["is_legal"] == "1",
                 float(row["expected_bowl_cost"]) - int(row["observed_bowl_cost"])
                 + 5 * (int(row["bowler_wicket"]) - float(row["expected_bowl_wicket"]))),
            ):
                if role == "batting" and not unit:
                    continue
                names[(role, pid)] = name
                if old_valid:
                    add_score(old_groups[(role, pid, year, mid)], raw, int(unit),
                              int(row["pressure_score"]), 50, float(row["mismatch_weight"]))
                if not new_valid:
                    continue
                base = (role, scope, phase, innings)
                label = (*base, new_tier)
                wickets = int(row["wickets_before"])
                wicket_band = 0 if wickets <= 2 else 1 if wickets <= 4 else 2 if wickets <= 6 else 3
                if innings == "2":
                    rate = required / max(1, int(row["balls_remaining"]))
                    rate_band = 0 if rate < .8 else 1 if rate < 1.2 else 2 if rate < 1.6 else 3 if rate <= 2.3 else 4
                    remaining = int(row["balls_remaining"])
                    remaining_band = 0 if remaining > 60 else 1 if remaining > 36 else 2
                else:
                    rate_band = remaining_band = -1
                fine = (*label, wicket_band, rate_band, remaining_band)
                broad, coarse, detailed = prior[base], prior[label], prior[fine]
                broad_mean = broad["impact"] / (broad["balls"] + 1000)
                coarse_mean = (coarse["impact"] + 400*broad_mean) / (coarse["balls"] + 400)
                correction = (detailed["impact"] + 150*coarse_mean) / (detailed["balls"] + 150)
                for state in (base, label, fine):
                    pending[state]["impact"] += raw
                    pending[state]["balls"] += unit
                adjusted = raw - correction
                cell = calibration[(year, scope, role, phase, new_tier)]
                cell["balls"] += unit
                cell["raw"] += raw
                cell["adjusted"] += adjusted
                add_score(groups[(role, pid, year, mid)], adjusted, int(unit), new_points,
                          50, float(row["mismatch_weight"]))

    if seen_exact_keys != len(exact_extras):
        raise ValueError(f"Verified extras coverage mismatch: {seen_exact_keys} of {len(exact_extras)}")

    by_player = defaultdict(list)
    by_old_player = defaultdict(list)
    for (role, pid, year, mid), stats in groups.items():
        by_player[(role, pid)].append((year, mid, stats))
    for (role, pid, year, mid), stats in old_groups.items():
        by_old_player[(role, pid)].append((year, mid, stats))

    summaries = []
    for (role, pid), entries in by_player.items():
        matches = [s for _, _, s in entries]
        total = combine(matches)
        good = eligible(total, matches)
        pballs, lowballs = total["pressure_effective_balls"], total["low_balls"]
        p_rate = 100*total["pressure_impact"]/pballs if pballs else 0
        low_rate = 100*total["low_impact"]/lowballs if lowballs else 0
        p10, p90 = bootstrap(matches, pid, role) if good else (0, 0)
        positive = [s["pressure_impact"] for s in matches if s["pressure_effective_balls"] > 0]
        point = pressure_point(total)
        summaries.append({
            "role": role, "player_id": pid, "player_name": names[(role, pid)],
            "eligible": int(good), "rank": "", "pressure_effective_balls": round(pballs,2),
            "pressure_matches": len(positive), "high_pressure_balls": total["high_pressure_balls"],
            "low_balls": lowballs, "pressure_rate_per_100": round(p_rate,3),
            "low_rate_per_100": round(low_rate,3),
            "pressure_uplift_per_100": round(p_rate-low_rate,3),
            "shrunk_pressure_score": round(point,3), "bootstrap_p10": round(p10,3) if good else "",
            "bootstrap_p90": round(p90,3) if good else "",
            "conservative_score": round((point+p10)/2,3) if good else "",
            "positive_match_share": round(sum(x>0 for x in positive)/len(positive),3) if positive else 0,
        })
    rankings = []
    for role in ("batting", "bowling"):
        qualified = [s for s in summaries if s["role"] == role and s["eligible"]]
        qualified.sort(key=lambda s: (-float(s["conservative_score"]), int(s["player_id"])))
        for place, item in enumerate(qualified,1):
            item["rank"] = place
        rankings += qualified[:10]
        print(role,"eligible",len(qualified),"top 10",", ".join(x["player_name"] for x in qualified[:10]))
    summaries.sort(key=lambda s: (s["role"],int(s["rank"]) if s["rank"] else 99999,int(s["player_id"])))

    with (DEFAULT_OUTPUT / "candidate_v2_player_summary.csv").open("w",newline="",encoding="utf-8") as stream:
        writer = csv.DictWriter(stream,fieldnames=SUMMARY_FIELDS)
        writer.writeheader(); writer.writerows(summaries)
    with (DEFAULT_OUTPUT / "candidate_v2_rankings.csv").open("w",newline="",encoding="utf-8") as stream:
        writer = csv.DictWriter(stream,fieldnames=SUMMARY_FIELDS)
        writer.writeheader(); writer.writerows(rankings)
    with (DEFAULT_OUTPUT / "candidate_v2_calibration.csv").open("w",newline="",encoding="utf-8") as stream:
        writer = csv.DictWriter(stream,fieldnames=CAL_FIELDS)
        writer.writeheader()
        for (year,scope,role,phase,label),cell in sorted(calibration.items()):
            balls = cell["balls"]
            if not balls: continue
            writer.writerow({"year":year,"scope":scope,"role":role,"phase":phase,"tier":label,
                             "balls":balls,"raw_residual_per_100":round(100*cell["raw"]/balls,3),
                             "adjusted_residual_per_100":round(100*cell["adjusted"]/balls,3)})
    with (DEFAULT_OUTPUT / "candidate_v2_pressure_coverage.csv").open("w",newline="",encoding="utf-8") as stream:
        writer = csv.DictWriter(stream,fieldnames=PRESSURE_FIELDS)
        writer.writeheader()
        for (year,scope,innings,phase,label),count in sorted(pressure_counts.items()):
            writer.writerow({"year":year,"scope":scope,"innings":innings,"phase":phase,
                             "tier":label,"deliveries":count})

    backtest = []
    score_cache = {}
    folds = ((2023,2024,"relaxed",40,8,20),
             (2024,2025,"relaxed",40,8,20),
             (2025,2026,"relaxed",40,8,20),
             (2024,2025,"final",100,20,50),
             (2025,2026,"final",100,20,50))
    for through, later, gate, min_balls, min_matches, min_low in folds:
        for role in ("batting", "bowling"):
            rows = []
            for (r,pid),entries in by_player.items():
                if r != role: continue
                train = [s for year,_,s in entries if year <= through]
                test = [s for year,_,s in entries if year == later]
                total, future = combine(train), combine(test)
                if not eligible(total,train,min_balls,min_matches,min_low) or not eligible(future,test,15,4,0):
                    continue
                old_entries = by_old_player[(role,pid)]
                old_train_matches = [s for year,_,s in old_entries if year <= through]
                old_train = combine(old_train_matches)
                if not eligible(old_train, old_train_matches, min_balls, min_matches, min_low):
                    continue
                v2_key = ("v2",role,pid,through)
                old_key = ("old",role,pid,through)
                if v2_key not in score_cache:
                    score_cache[v2_key] = (pressure_point(total) + bootstrap(train,pid,role)[0]) / 2
                if old_key not in score_cache:
                    score_cache[old_key] = (old_score(old_train)[3] + old_bootstrap(old_train_matches,pid,role)[0]) / 2
                v2, old = score_cache[v2_key], score_cache[old_key]
                old_positive = [s["pressure_impact"] > 0 for s in old_train_matches
                                if s["pressure_effective_balls"] > 0]
                new_positive = [s["pressure_impact"] > 0 for s in train
                                if s["pressure_effective_balls"] > 0]
                old_consistency = (sum(old_positive)+1)/(len(old_positive)+2)
                new_consistency = (sum(new_positive)+1)/(len(new_positive)+2)
                consistency = (old_consistency+new_consistency)/2
                future_rate = 100*future["pressure_impact"]/future["pressure_effective_balls"]
                future_matches = [s for s in test if s["pressure_effective_balls"]]
                future_share = sum(s["pressure_impact"]>0 for s in future_matches)/len(future_matches)
                rows.append((old,v2,future_rate,future_share,consistency))
            if len(rows) < 11: continue
            old_ranks = rank([x[0] for x in rows])
            v2_ranks = rank([x[1] for x in rows])
            consistency_ranks = rank([x[4] for x in rows])
            candidates = [("old",[x[0] for x in rows]),
                          ("v2",[x[1] for x in rows]),
                          ("consensus",[old_ranks[i]+v2_ranks[i] for i in range(len(rows))]),
                          ("consistency_consensus",[old_ranks[i]+v2_ranks[i]+consistency_ranks[i]
                                                     for i in range(len(rows))])]
            for method,values in candidates:
                top = sorted(range(len(rows)),key=lambda i:-values[i])[:10]
                backtest.append({"train_through":through,"test_year":later,"gate":gate,"role":role,
                                 "players":len(rows),"method":method,
                                 "rank_correlation":round(spearman(values,[x[2] for x in rows]),3),
                                 "top10_future_rate":round(sum(rows[i][2] for i in top)/10,3),
                                 "top10_future_positive_share":round(sum(rows[i][3] for i in top)/10,3)})
    with (DEFAULT_OUTPUT / "candidate_v2_backtest.csv").open("w",newline="",encoding="utf-8") as stream:
        writer = csv.DictWriter(stream,fieldnames=BACKTEST_FIELDS)
        writer.writeheader(); writer.writerows(backtest)
    print("v2 pressure counts",dict(Counter({tier:sum(n for key,n in pressure_counts.items() if key[-1]==tier)
                                           for tier in ("low","medium","high")})))
    print("unstable chase deliveries skipped",skipped_unstable,"unverified poor-match deliveries skipped",skipped_bad)


if __name__ == "__main__":
    main()
