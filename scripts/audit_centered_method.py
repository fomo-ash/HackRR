"""Explore prior-only pressure-state centering without changing submission outputs."""

import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from score_players import add_score, bootstrap, score  # noqa: E402

DATA = ROOT / "data" / "processed"
with (DATA / "match_quality.csv").open(newline="", encoding="utf-8") as f:
    bad_matches = {
        r["match_id"] for r in csv.DictReader(f)
        if r["approx_margin_error"] and int(r["approx_margin_error"]) > 7
    }

prior = defaultdict(Counter)
daily = defaultdict(Counter)
last_date = None
groups = defaultdict(lambda: defaultdict(Counter))
names = {}

with (DATA / "delivery_context.csv").open(newline="", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        date = r["match_date"]
        if last_date and date != last_date:
            for key, stats in daily.items():
                prior[key].update(stats)
            daily.clear()
        last_date = date
        if r["match_id"] in bad_matches or r["tier_stable_with_7_run_shift"] != "1":
            continue
        for role, pid, name, unit, raw in (
            ("batting", r["striker_id"], r["striker_name"], r["extras_type"] != "wide",
             int(r["runs"]) - float(r["expected_bat_runs"])
             - 5 * (int(r["striker_out"]) - float(r["expected_bat_out"]))),
            ("bowling", r["bowler_id"], r["bowler_name"], r["is_legal"] == "1",
             float(r["expected_bowl_cost"]) - int(r["observed_bowl_cost"])
             + 5 * (int(r["bowler_wicket"]) - float(r["expected_bowl_wicket"]))),
        ):
            if role == "batting" and not unit:
                continue
            names[(role, pid)] = name
            state = (role, r["scope"], r["phase"], r["innings"], r["pressure_tier"])
            old = prior[state]
            correction = old["impact"] / (old["balls"] + 400)
            daily[state]["impact"] += raw
            daily[state]["balls"] += unit
            period = "train" if date[:4] <= "2024" else "test"
            for method, residual in (("raw", raw), ("centered", raw - correction)):
                key = (method, period, role, pid)
                add_score(groups[key][r["match_id"]], residual, int(unit),
                          int(r["pressure_score"]), 50, float(r["mismatch_weight"]))


def combine(matches):
    total = Counter()
    for s in matches.values():
        total.update(s)
    return total


def matches_for(method, role, pid, period=None):
    if period:
        return groups[(method, period, role, pid)]
    return {**groups[(method, "train", role, pid)], **groups[(method, "test", role, pid)]}


def eligible(total, matches, pressure=100, nmatch=20, low=50):
    return (total["pressure_effective_balls"] >= pressure
            and sum(s["pressure_effective_balls"] > 0 for s in matches.values()) >= nmatch
            and total["low_balls"] >= low)


players = set((role, pid) for _, _, role, pid in groups)
for role in ("batting", "bowling"):
    print("FULL LIST", role)
    for method in ("raw", "centered"):
        ranked = []
        for r, pid in players:
            if r != role:
                continue
            matches = matches_for(method, role, pid)
            total = combine(matches)
            if not eligible(total, matches):
                continue
            p10, _ = bootstrap(list(matches.values()), pid, role)
            value = (score(total)[3] + p10) / 2
            ranked.append((value, names[(role, pid)]))
        ranked.sort(reverse=True)
        print(method, "eligible", len(ranked), "TOP", ", ".join(f"{name} ({val:.1f})" for val, name in ranked[:10]))


def ranks(values):
    order = sorted(range(len(values)), key=lambda i: values[i])
    out = [0] * len(values)
    for rank, i in enumerate(order):
        out[i] = rank
    return out


def spearman(a, b):
    x, y = ranks(a), ranks(b)
    n = len(x)
    return 1 - 6 * sum((u - v) ** 2 for u, v in zip(x, y)) / (n * (n * n - 1))


for role in ("batting", "bowling"):
    rows = []
    for r, pid in players:
        if r != role:
            continue
        tr = matches_for("raw", role, pid, "train")
        te = matches_for("raw", role, pid, "test")
        raw_train, raw_test = combine(tr), combine(te)
        if not eligible(raw_train, tr, 40, 8, 20) or not eligible(raw_test, te, 20, 5, 0):
            continue
        ct = combine(matches_for("centered", role, pid, "train"))
        cf = combine(matches_for("centered", role, pid, "test"))
        rows.append((names[(role, pid)], score(raw_train)[3], score(ct)[3],
                     100 * cf["pressure_impact"] / cf["pressure_effective_balls"],
                     100 * raw_test["pressure_impact"] / raw_test["pressure_effective_balls"]))
    print("OUT OF TIME", role, "eligible", len(rows))
    for name, col in (("raw", 1), ("centered", 2)):
        top = sorted(rows, key=lambda x: -x[col])[:10]
        print(name, "vs_future_centered_pressure", round(spearman([x[col] for x in rows], [x[3] for x in rows]), 3),
              "top10_future_centered_pressure", round(sum(x[3] for x in top) / len(top), 2),
              "TOP", ", ".join(x[0] for x in top))
