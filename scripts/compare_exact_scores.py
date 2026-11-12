"""Compare two out-of-time chase models on the same verified-score matches."""

from __future__ import annotations

import csv
from collections import Counter, defaultdict

from build_cumulative_dataset import DEFAULT_OUTPUT
from score_players import percentile


FIELDS = [
    "year", "scope", "matches", "legal_deliveries", "approx_model_brier",
    "exact_model_brier", "approx_model_ece", "exact_model_ece",
    "median_abs_required_run_difference", "p95_abs_required_run_difference",
    "share_required_difference_over_7", "high_leverage_flag_disagreement_share",
]


def key(row: dict[str, str]) -> tuple[str, str, str, str]:
    return row["match_id"], row["innings"], row["overid"], row["over_ball_num"]


def metrics(rows: list[dict], field: str) -> tuple[float, float]:
    total = sum(row["weight"] for row in rows)
    brier = sum(row["weight"] * (float(row[field]) - int(row["chase_won"])) ** 2
                for row in rows) / total
    bins = defaultdict(Counter)
    for row in rows:
        probability = float(row[field])
        bucket = min(9, int(probability * 10))
        bins[bucket]["predicted"] += row["weight"] * probability
        bins[bucket]["observed"] += row["weight"] * int(row["chase_won"])
    ece = sum(abs(cell["predicted"] - cell["observed"])
              for cell in bins.values()) / total
    return brier, ece


def main() -> None:
    with (DEFAULT_OUTPUT / "win_probability_exact_delivery.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        exact = {key(row): row for row in csv.DictReader(handle)}
    with (DEFAULT_OUTPUT / "win_probability_delivery.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        approx = {delivery_key: row for row in csv.DictReader(handle)
                  if (delivery_key := key(row)) in exact}
    # The original model excluded some matches for approximate-margin error;
    # compare only deliveries that both held-out runs actually evaluated.
    exact = {delivery_key: row for delivery_key, row in exact.items()
             if delivery_key in approx}
    legal = set()
    with (DEFAULT_OUTPUT / "pressure_delivery.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        for row in csv.DictReader(handle):
            delivery_key = key(row)
            if delivery_key in exact and row["is_legal"] == "1":
                legal.add(delivery_key)
    by_group = defaultdict(list)
    counts = Counter(delivery_key[0] for delivery_key in legal)
    for delivery_key in legal:
        current = exact[delivery_key]
        old = approx[delivery_key]
        assert old["chase_won"] == current["chase_won"]
        row = {
            "year": current["match_date"][:4], "scope": current["scope"],
            "match_id": delivery_key[0], "weight": 1 / counts[delivery_key[0]],
            "chase_won": current["chase_won"],
            "approx_probability": old["win_probability"],
            "exact_probability": current["win_probability"],
            "abs_required_difference": abs(int(current["exact_minus_approx_required"])),
            "flag_disagreement": int(old["win_prob_high_leverage"] !=
                                     current["win_prob_high_leverage"]),
        }
        by_group[(row["year"], row["scope"])].append(row)
    summaries = []
    for (year, scope), rows in sorted(by_group.items()):
        old_brier, old_ece = metrics(rows, "approx_probability")
        new_brier, new_ece = metrics(rows, "exact_probability")
        differences = [row["abs_required_difference"] for row in rows]
        summaries.append({
            "year": year, "scope": scope,
            "matches": len({row["match_id"] for row in rows}),
            "legal_deliveries": len(rows),
            "approx_model_brier": round(old_brier, 4),
            "exact_model_brier": round(new_brier, 4),
            "approx_model_ece": round(old_ece, 4),
            "exact_model_ece": round(new_ece, 4),
            "median_abs_required_run_difference": round(percentile(differences, 0.5), 2),
            "p95_abs_required_run_difference": round(percentile(differences, 0.95), 2),
            "share_required_difference_over_7": round(
                sum(value > 7 for value in differences) / len(differences), 4
            ),
            "high_leverage_flag_disagreement_share": round(
                sum(row["flag_disagreement"] for row in rows) / len(rows), 4
            ),
        })
    with (DEFAULT_OUTPUT / "win_probability_exact_comparison.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(summaries)
    print(f"Compared {sum(row['legal_deliveries'] for row in summaries)} legal balls in {len(summaries)} held-out cells")


if __name__ == "__main__":
    main()
