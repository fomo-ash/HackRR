"""Compare fixed pressure rules with held-out exact-score leverage diagnostics."""

import csv
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_candidate_v2 import pressure_score as proposed  # noqa: E402

DATA = ROOT / "data" / "processed"
heldout = {}
with (DATA / "win_probability_exact_delivery.csv").open(newline="", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        if r["over_ball_num"] and r["win_prob_high_leverage"]:
            key = (r["match_id"], r["innings"], r["overid"], r["over_ball_num"])
            heldout[key] = r

by_period = defaultdict(list)
with (DATA / "pressure_delivery.csv").open(newline="", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        key = (r["match_id"],r["innings"],r["overid"],r["over_ball_num"])
        h = heldout.get(key)
        if not h or r["is_legal"] != "1":
            continue
        period = "early" if int(r["match_date"][:4]) <= 2024 else "late"
        label = int(h["win_prob_high_leverage"])
        by_period[period].append((label,int(r["pressure_score"]),
                                  proposed(r,int(h["runs_required_approx"]))))

def auc(rows, col):
    vals = sorted((r[col],r[0]) for r in rows)
    npos = sum(r[0] for r in rows)
    nneg = len(rows)-npos
    wins = 0
    neg_before = 0
    k = 0
    while k < len(vals):
        j = k
        while j < len(vals) and vals[j][0] == vals[k][0]:
            j += 1
        n = sum(1-x[1] for x in vals[k:j])
        p = j-k-n
        wins += p*(neg_before+n/2)
        neg_before += n
        k = j
    return wins/(npos*nneg)

for period, rows in by_period.items():
    print(period,"balls",len(rows),"high_leverage",sum(r[0] for r in rows))
    for name,col in (("current",1),("proposed",2)):
        score_auc = auc(rows,col)
        top = sorted(rows,key=lambda r:-r[col])[:round(.25*len(rows))]
        recall = sum(r[0] for r in top)/sum(r[0] for r in rows)
        precision = sum(r[0] for r in top)/len(top)
        medium = [r for r in rows if r[col]>=30]
        high = [r for r in rows if r[col]>=50]
        print(name,"auc",round(score_auc,3),"top_quarter_recall",round(recall,3),
              "top_quarter_precision",round(precision,3),
              "medium_plus_count",len(medium),"high_count",len(high))
