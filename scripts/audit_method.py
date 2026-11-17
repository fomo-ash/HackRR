"""Exploratory, read-only audit of the current pressure ranking design."""

import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from score_players import score  # noqa: E402

DATA = ROOT / "data" / "processed"
with (DATA / "match_quality.csv").open(newline="", encoding="utf-8") as f:
    bad_matches = {
        r["match_id"] for r in csv.DictReader(f)
        if r["approx_margin_error"] and int(r["approx_margin_error"]) > 7
    }

exposure = Counter()
residuals = defaultdict(Counter)
annual = defaultdict(Counter)
player_match = defaultdict(Counter)
names = {}
with (DATA / "delivery_context.csv").open(newline="", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        if r["match_id"] in bad_matches or r["tier_stable_with_7_run_shift"] != "1":
            continue
        phase = r["phase"]
        tier = r["pressure_tier"]
        exposure[(tier, phase, r["innings"])] += 1
        year_group = "train" if int(r["match_date"][:4]) <= 2024 else "test"
        weight = float(r["mismatch_weight"])
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
            cell = residuals[(role, tier, phase)]
            cell["impact"] += weight * raw
            cell["balls"] += unit
            year_cell = annual[(role, r["match_date"][:4], tier, phase)]
            year_cell["impact"] += weight * raw
            year_cell["balls"] += unit
            mid = r["match_id"]
            s = player_match[(role, pid, year_group, mid)]
            if tier == "high":
                pw = 1
            elif tier == "medium":
                pw = 0.5
            else:
                pw = 0
            if pw:
                s["pressure_impact"] += pw * weight * raw
                s["pressure_effective_balls"] += pw * unit
            else:
                s["low_impact"] += weight * raw
                s["low_balls"] += unit

print("EXPOSURE BY TIER / PHASE / INNINGS")
for key, count in sorted(exposure.items()):
    print(*key, count, sep=",")
print("RESIDUALS BY TIER / PHASE (RUNS PER 100 BALLS)")
for key, s in sorted(residuals.items()):
    print(*key, s["balls"], round(100 * s["impact"] / s["balls"], 2), sep=",")
print("ANNUAL HIGH DEATH RESIDUALS (RUNS PER 100 BALLS)")
for key, s in sorted(annual.items()):
    if key[2:] == ("high", "death"):
        print(*key, s["balls"], round(100 * s["impact"] / s["balls"], 2), sep=",")

by_player = defaultdict(lambda: defaultdict(list))
for (role, pid, part, mid), s in player_match.items():
    by_player[(role, pid)][part].append(s)

rows = defaultdict(list)
for (role, pid), splits in by_player.items():
    train = Counter()
    test = Counter()
    for s in splits["train"]:
        train.update(s)
    for s in splits["test"]:
        test.update(s)
    tr_matches = sum(s["pressure_effective_balls"] > 0 for s in splits["train"])
    te_matches = sum(s["pressure_effective_balls"] > 0 for s in splits["test"])
    if not (train["pressure_effective_balls"] >= 40 and tr_matches >= 8 and train["low_balls"] >= 20
            and test["pressure_effective_balls"] >= 20 and te_matches >= 5):
        continue
    p = 100 * train["pressure_impact"] / train["pressure_effective_balls"]
    low = 100 * train["low_impact"] / train["low_balls"]
    shrink = train["pressure_effective_balls"] / (train["pressure_effective_balls"] + 80)
    adjusted = low + shrink * (p - low)
    uplift = shrink * (p - low)
    positives = sum(s["pressure_impact"] > 0 for s in splits["train"] if s["pressure_effective_balls"])
    share = (positives + 1) / (tr_matches + 2)
    future_p = 100 * test["pressure_impact"] / test["pressure_effective_balls"]
    future_low = 100 * test["low_impact"] / test["low_balls"] if test["low_balls"] else 0
    future_share = sum(s["pressure_impact"] > 0 for s in splits["test"] if s["pressure_effective_balls"]) / te_matches
    rows[role].append({"name": names[(role, pid)], "pballs": train["pressure_effective_balls"],
                       "matches": tr_matches, "current": .65 * adjusted + .35 * uplift,
                       "pressure": p * shrink, "uplift": uplift, "share": share,
                       "future_pressure": future_p, "future_uplift": future_p - future_low,
                       "future_share": future_share})

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

for role, group in rows.items():
    print("OUT-OF-TIME", role, "eligible", len(group))
    for candidate in ("current", "pressure", "uplift", "share"):
        top = sorted(group, key=lambda r: -r[candidate])[:10]
        print(candidate, "spearman_future_pressure", round(spearman([r[candidate] for r in group], [r["future_pressure"] for r in group]), 3),
              "spearman_future_uplift", round(spearman([r[candidate] for r in group], [r["future_uplift"] for r in group]), 3),
              "top10_future_pressure", round(sum(r["future_pressure"] for r in top) / len(top), 2),
              "top10_future_positive_share", round(sum(r["future_share"] for r in top) / len(top), 3))
        print("TOP", ", ".join(r["name"] for r in top))
