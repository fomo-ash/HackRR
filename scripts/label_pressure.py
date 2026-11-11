"""Phase 2: assign pre-ball pressure tiers and audit chase sensitivity."""

from __future__ import annotations

import csv
import math
from collections import Counter, defaultdict

from build_cumulative_dataset import DEFAULT_OUTPUT
from build_match_state import STATE_FIELDS


EXTRA_FIELDS = [
    "phase_points", "wicket_points", "chase_points", "knockout_points",
    "pressure_score", "pressure_tier", "chase_runs_per_ball_approx",
    "tier_stable_with_7_run_shift",
]
COVERAGE_FIELDS = [
    "player_id", "player_name", "role", "match_format", "balls",
    "low_balls", "medium_balls", "high_balls", "pressure_matches",
    "unstable_chase_balls",
]


def tier(score: int) -> str:
    if score >= 50:
        return "high"
    if score >= 30:
        return "medium"
    return "low"


def pressure_parts(row: dict[str, str], required: int | None = None) -> tuple[int, int, int, int]:
    over = int(row["overid"])
    wickets = int(row["wickets_before"])
    phase = 0 if over <= 6 else 10 if over <= 15 else 24 if over <= 18 else 34
    wicket = 0 if wickets <= 2 else 7 if wickets <= 4 else 14 if wickets <= 6 else 20
    chase = 0
    if row["innings"] == "2":
        remaining = max(1, int(row["balls_remaining"]))
        runs_needed = int(row["runs_required_approx"]) if required is None else required
        rate = max(0, runs_needed) / remaining
        if runs_needed > 0:
            if rate < 0.8:
                chase = 0
            elif rate <= 2.3:
                chase = 22 if remaining <= 36 else 12 if remaining <= 60 else 5
            else:
                # An almost impossible chase is strain, but less match leverage.
                chase = 15 if remaining <= 36 else 7
            if rate >= 1.35 and 10 - wickets <= 4:
                chase += 8
    knockout = 10 if row["knock_out"] == "1" else 0
    return phase, wicket, chase, knockout


def main() -> None:
    quality = list(csv.DictReader(
        (DEFAULT_OUTPUT / "match_quality.csv").open(newline="", encoding="utf-8")
    ))
    errors = sorted(int(row["approx_margin_error"]) for row in quality if row["approx_margin_error"])
    tolerance = errors[math.ceil(0.95 * len(errors)) - 1]
    coverage: dict[tuple[str, str, str], dict] = defaultdict(
        lambda: {"counts": Counter(), "matches": set(), "name": ""}
    )
    tier_counts = Counter()
    unstable = 0
    with (DEFAULT_OUTPUT / "match_state.csv").open(newline="", encoding="utf-8") as source, (
        DEFAULT_OUTPUT / "pressure_delivery.csv"
    ).open("w", newline="", encoding="utf-8") as target:
        writer = csv.DictWriter(target, fieldnames=STATE_FIELDS + EXTRA_FIELDS)
        writer.writeheader()
        for row in csv.DictReader(source):
            phase, wicket, chase, knockout = pressure_parts(row)
            score = min(100, phase + wicket + chase + knockout)
            label = tier(score)
            stable = True
            rate = ""
            if row["innings"] == "2":
                required = int(row["runs_required_approx"])
                remaining = max(1, int(row["balls_remaining"]))
                rate = round(required / remaining, 4)
                scores = []
                for shifted in (required - tolerance, required + tolerance):
                    scores.append(min(100, sum(pressure_parts(row, max(0, shifted)))))
                stable = all(tier(other) == label for other in scores)
            if not stable:
                unstable += 1
            writer.writerow({
                **row,
                "phase_points": phase, "wicket_points": wicket,
                "chase_points": chase, "knockout_points": knockout,
                "pressure_score": score, "pressure_tier": label,
                "chase_runs_per_ball_approx": rate,
                "tier_stable_with_7_run_shift": int(stable),
            })
            tier_counts[label] += 1
            for role, pid, name, countable in (
                ("batting", row["striker_id"], row["striker_name"], row["extras_type"] != "wide"),
                ("bowling", row["bowler_id"], row["bowler_name"], row["is_legal"] == "1"),
            ):
                if not countable:
                    continue
                key = (pid, role, row["match_format"])
                cell = coverage[key]
                cell["name"] = name
                cell["counts"][label] += 1
                cell["counts"]["balls"] += 1
                if label in ("medium", "high"):
                    cell["matches"].add(row["match_id"])
                if not stable:
                    cell["counts"]["unstable"] += 1

    coverage_rows = []
    for (pid, role, fmt), cell in sorted(
        coverage.items(), key=lambda item: (int(item[0][0]), item[0][1], item[0][2])
    ):
        counts = cell["counts"]
        coverage_rows.append({
            "player_id": pid, "player_name": cell["name"], "role": role,
            "match_format": fmt, "balls": counts["balls"],
            "low_balls": counts["low"], "medium_balls": counts["medium"],
            "high_balls": counts["high"],
            "pressure_matches": len(cell["matches"]),
            "unstable_chase_balls": counts["unstable"],
        })
    with (DEFAULT_OUTPUT / "pressure_coverage.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=COVERAGE_FIELDS)
        writer.writeheader()
        writer.writerows(coverage_rows)
    print(f"Pressure tiers: {dict(tier_counts)}")
    print(f"Chase tier unstable under +/-{tolerance} runs: {unstable}")
    print(f"Player-role-format coverage rows: {len(coverage_rows)}")


if __name__ == "__main__":
    main()
