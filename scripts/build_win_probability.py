"""Out-of-time chase win probabilities and potential one-ball leverage.

This diagnostic is deliberately separate from the submitted pressure index. A
season is predicted only by models fitted to earlier seasons, and matches have
equal weight during fitting and validation.
"""

from __future__ import annotations

import csv
import math
from collections import Counter, defaultdict

from build_cumulative_dataset import DEFAULT_INPUT, DEFAULT_OUTPUT, read_index


DELIVERY_FIELDS = [
    "match_id", "match_date", "scope", "innings", "overid",
    "over_ball_num", "legal_before", "balls_remaining", "wickets_before",
    "runs_required_approx", "pressure_score", "pressure_tier",
    "raw_win_probability", "win_probability", "season_log_odds_offset",
    "potential_six_run_leverage", "win_prob_high_leverage",
    "win_probability_shift_7_runs", "chase_won", "trained_through_year",
]
SUMMARY_FIELDS = [
    "year", "scope", "matches", "legal_deliveries", "training_matches",
    "training_through_year", "brier", "raw_brier", "elo_only_brier", "half_brier",
    "log_loss", "calibration_error", "mean_predicted", "observed_win_share",
    "mean_leverage", "high_leverage_cutoff", "high_leverage_balls",
    "high_leverage_also_rule_high", "high_leverage_rule_low",
]
CALIBRATION_FIELDS = [
    "year", "scope", "probability_bin", "weighted_deliveries",
    "mean_predicted", "observed_win_share",
]
MODEL_FIELDS = ["predicted_year", "training_matches", "feature", "coefficient"]
CALIBRATOR_FIELDS = [
    "predicted_year", "scope", "prior_out_of_time_matches",
    "intercept", "slope",
]
FEATURE_NAMES = [
    "intercept", "log_required_rate_ratio", "log_rate_x_late", "late",
    "wickets_lost_fraction", "wickets_x_late", "batting_elo_minus_bowling_elo",
    "ipl", "target_relative_to_180", "knockout",
]
LEVERAGE_THRESHOLD = 0.08


def sigmoid(value: float) -> float:
    if value >= 0:
        exp = math.exp(-value)
        return 1 / (1 + exp)
    exp = math.exp(value)
    return exp / (1 + exp)


def features(remaining: int, wickets: int, required: int, target: int,
             elo_diff: float, scope: str, knockout: bool) -> tuple[float, ...]:
    late = 1 - max(0, min(120, remaining)) / 120
    spent = max(0, min(10, wickets)) / 10
    rate = math.log((max(0, required) + 1) / (max(0, remaining) * 1.3 + 1))
    rate = max(-2.5, min(2.5, rate))
    return (
        1.0, rate, rate * late, late, spent, spent * late,
        max(-2, min(2, elo_diff / 400)), int(scope == "IPL"),
        max(-0.8, min(1.0, target / 180 - 1)), int(knockout),
    )


def predict(coefficients: list[float], remaining: int, wickets: int,
            required: int, target: int, elo_diff: float, scope: str,
            knockout: bool, terminal: bool = False) -> float:
    if terminal:
        if required <= 0:
            return 1.0
        if remaining <= 0 or wickets >= 10:
            return 0.0
    vector = features(remaining, wickets, required, target, elo_diff, scope, knockout)
    return sigmoid(sum(a * b for a, b in zip(coefficients, vector)))


def calibrate(probability: float, intercept: float, slope: float) -> float:
    if probability in (0.0, 1.0):
        return probability
    log_odds = math.log(probability / (1 - probability))
    return sigmoid(intercept + slope * log_odds)


def fit_calibrator(samples: list[tuple[float, int, float]]) -> tuple[float, float]:
    if sum(weight for _, _, weight in samples) < 100:
        return 0.0, 1.0
    intercept, slope = 0.0, 1.0
    total_weight = sum(weight for _, _, weight in samples)
    for _ in range(250):
        intercept_gradient = 0.0
        slope_gradient = 0.0
        for raw_probability, outcome, weight in samples:
            clipped = max(1e-5, min(1 - 1e-5, raw_probability))
            log_odds = math.log(clipped / (1 - clipped))
            error = weight * (sigmoid(intercept + slope * log_odds) - outcome)
            intercept_gradient += error
            slope_gradient += error * log_odds
        intercept -= 0.08 * (intercept_gradient / total_weight + 0.025 * intercept)
        slope -= 0.025 * (slope_gradient / total_weight + 0.025 * (slope - 1))
        slope = max(0.5, min(2.5, slope))
    return intercept, slope


def fit(samples: list[tuple[tuple[float, ...], int, float]]) -> list[float]:
    coefficients = [0.0] * len(FEATURE_NAMES)
    first_moment = [0.0] * len(coefficients)
    second_moment = [0.0] * len(coefficients)
    total_weight = sum(weight for _, _, weight in samples)
    for iteration in range(1, 151):
        gradient = [0.0] * len(coefficients)
        for vector, outcome, weight in samples:
            error = weight * (sigmoid(sum(a * b for a, b in zip(coefficients, vector))) - outcome)
            for index, value in enumerate(vector):
                gradient[index] += error * value
        for index in range(len(coefficients)):
            gradient[index] = gradient[index] / total_weight + (
                0.008 * coefficients[index] if index else 0
            )
            first_moment[index] = 0.9 * first_moment[index] + 0.1 * gradient[index]
            second_moment[index] = 0.999 * second_moment[index] + 0.001 * gradient[index] ** 2
            corrected_first = first_moment[index] / (1 - 0.9 ** iteration)
            corrected_second = second_moment[index] / (1 - 0.999 ** iteration)
            coefficients[index] -= 0.04 * corrected_first / (math.sqrt(corrected_second) + 1e-8)
    return coefficients


def write_csv(name: str, fields: list[str], rows: list[dict]) -> None:
    with (DEFAULT_OUTPUT / name).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    matches = read_index(DEFAULT_INPUT / "matches.csv", "match_id")
    teams = read_index(DEFAULT_OUTPUT / "team_strength.csv", "match_id")
    quality = read_index(DEFAULT_OUTPUT / "match_quality.csv", "match_id")
    states: dict[str, list[dict]] = defaultdict(list)
    with (DEFAULT_OUTPUT / "pressure_delivery.csv").open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["innings"] != "2":
                continue
            mid = row["match_id"]
            if (quality[mid]["approx_margin_error"]
                    and int(quality[mid]["approx_margin_error"]) > 7):
                continue
            if "super over" in matches[mid]["result"].lower():
                continue
            winner = matches[mid]["win_team_id"]
            if winner not in (row["batting_team_id"], row["bowling_team_id"]):
                continue
            team = teams[mid]
            bat_elo = float(team["home_elo_pre"] if row["batting_team_id"] == team["home_team_id"]
                            else team["away_elo_pre"])
            bowl_elo = float(team["away_elo_pre"] if row["batting_team_id"] == team["home_team_id"]
                             else team["home_elo_pre"])
            states[mid].append({
                "row": row, "year": int(row["match_date"][:4]), "scope": team["scope"],
                "outcome": int(winner == row["batting_team_id"]),
                "elo_diff": bat_elo - bowl_elo,
                "target": int(row["approx_target"]),
                "required": int(row["runs_required_approx"]),
                "remaining": int(row["balls_remaining"]),
                "wickets": int(row["wickets_before"]),
                "knockout": row["knock_out"] == "1",
            })

    by_year: dict[int, list[str]] = defaultdict(list)
    for mid, rows in states.items():
        by_year[rows[0]["year"]].append(mid)
    if len(by_year) < 3:
        raise ValueError("At least three seasons are needed for out-of-time validation")
    for year in by_year:
        by_year[year].sort(key=lambda mid: (states[mid][0]["row"]["match_date"], int(mid)))

    delivery_rows = []
    summary_rows = []
    calibration_rows = []
    model_rows = []
    calibrator_rows = []
    calibration_history: dict[str, list[tuple[float, int, float]]] = defaultdict(list)
    calibration_match_ids: dict[str, set[str]] = defaultdict(set)
    for year in sorted(by_year)[1:]:
        train_ids = [mid for earlier in sorted(by_year) if earlier < year for mid in by_year[earlier]]
        samples = []
        for mid in train_ids:
            selected = [state for state in states[mid]
                        if state["row"]["is_legal"] == "1"
                        and state["remaining"] > 0
                        and int(state["row"]["legal_before"]) % 3 == 0]
            if not selected:
                continue
            for state in selected:
                samples.append((
                    features(state["remaining"], state["wickets"],
                             state["required"], state["target"],
                             state["elo_diff"], state["scope"], state["knockout"]),
                    state["outcome"], 1 / len(selected),
                ))
        coefficients = fit(samples)
        model_rows.extend({
            "predicted_year": year, "training_matches": len(train_ids),
            "feature": name, "coefficient": round(value, 8),
        } for name, value in zip(FEATURE_NAMES, coefficients))
        calibrators = {
            scope: fit_calibrator(calibration_history[scope])
            for scope in ("IPL", "T20I")
        }
        calibrator_rows.extend({
            "predicted_year": year, "scope": scope,
            "prior_out_of_time_matches": len(calibration_match_ids[scope]),
            "intercept": round(calibrators[scope][0], 6),
            "slope": round(calibrators[scope][1], 6),
        } for scope in ("IPL", "T20I"))
        evaluation: dict[str, list[dict]] = defaultdict(list)
        season_history: dict[str, list[tuple[float, int]]] = defaultdict(list)
        pending_history: dict[str, list[tuple[float, int]]] = defaultdict(list)
        current_date = ""
        for mid in by_year[year]:
            match_rows = states[mid]
            match_date = match_rows[0]["row"]["match_date"]
            if match_date != current_date:
                for prior_scope, history in pending_history.items():
                    season_history[prior_scope].extend(history)
                pending_history.clear()
                current_date = match_date
            match_scope = match_rows[0]["scope"]
            season_offset = max(-0.6, min(0.6, 4 * sum(
                outcome - predicted for predicted, outcome in season_history[match_scope]
            ) / (len(season_history[match_scope]) + 12)))
            base_probability_sum = 0.0
            legal_count = sum(state["row"]["is_legal"] == "1" for state in match_rows)
            for state in match_rows:
                remaining, wickets, required = (
                    state["remaining"], state["wickets"], state["required"]
                )
                target, elo_diff, scope, knockout = (
                    state["target"], state["elo_diff"], state["scope"], state["knockout"]
                )
                raw_probability = predict(coefficients, remaining, wickets, required,
                                          target, elo_diff, scope, knockout)
                calibration_intercept, calibration_slope = calibrators[scope]
                base_probability = calibrate(raw_probability, calibration_intercept,
                                             calibration_slope)
                if state["row"]["is_legal"] == "1":
                    base_probability_sum += base_probability
                calibration_intercept += season_offset
                probability = calibrate(raw_probability, calibration_intercept,
                                        calibration_slope)
                next_remaining = max(0, remaining - 1)
                outcomes = [
                    calibrate(predict(
                        coefficients, next_remaining, wickets, max(0, required - runs),
                        target, elo_diff, scope, knockout, terminal=True,
                    ), calibration_intercept, calibration_slope)
                    for runs in (0, 4, 6)
                ]
                outcomes.append(calibrate(predict(
                    coefficients, next_remaining, wickets + 1, required,
                    target, elo_diff, scope, knockout, terminal=True,
                ), calibration_intercept, calibration_slope))
                leverage = max(outcomes) - min(outcomes)
                low_requirement = calibrate(predict(
                    coefficients, remaining, wickets, max(0, required - 7),
                    target, elo_diff, scope, knockout,
                ), calibration_intercept, calibration_slope)
                high_requirement = calibrate(predict(
                    coefficients, remaining, wickets, required + 7,
                    target, elo_diff, scope, knockout,
                ), calibration_intercept, calibration_slope)
                row = state["row"]
                delivery_rows.append({
                    "match_id": mid, "match_date": row["match_date"],
                    "scope": scope, "innings": 2, "overid": row["overid"],
                    "over_ball_num": row["over_ball_num"],
                    "legal_before": row["legal_before"],
                    "balls_remaining": remaining, "wickets_before": wickets,
                    "runs_required_approx": required,
                    "pressure_score": row["pressure_score"],
                    "pressure_tier": row["pressure_tier"],
                    "raw_win_probability": round(raw_probability, 6),
                    "win_probability": round(probability, 6),
                    "season_log_odds_offset": round(season_offset, 6),
                    "potential_six_run_leverage": round(leverage, 6),
                    "win_prob_high_leverage": int(leverage >= LEVERAGE_THRESHOLD),
                    "win_probability_shift_7_runs": round(low_requirement - high_requirement, 6),
                    "chase_won": state["outcome"],
                    "trained_through_year": year - 1,
                })
                if row["is_legal"] == "1":
                    evaluation[scope].append({
                        "mid": mid, "weight": 1 / legal_count,
                        "legal_before": int(row["legal_before"]),
                        "raw_probability": raw_probability,
                        "probability": probability, "outcome": state["outcome"],
                        "leverage": leverage,
                        "rule_tier": row["pressure_tier"],
                        "elo_probability": sigmoid(elo_diff * math.log(10) / 400),
                    })
            pending_history[match_scope].append((
                base_probability_sum / legal_count, match_rows[0]["outcome"]
            ))
        for scope, records in evaluation.items():
            total_weight = sum(record["weight"] for record in records)
            brier = sum(r["weight"] * (r["probability"] - r["outcome"]) ** 2
                        for r in records) / total_weight
            raw_brier = sum(r["weight"] * (r["raw_probability"] - r["outcome"]) ** 2
                            for r in records) / total_weight
            elo_brier = sum(r["weight"] * (r["elo_probability"] - r["outcome"]) ** 2
                            for r in records) / total_weight
            log_loss = -sum(
                r["weight"] * (r["outcome"] * math.log(max(1e-6, r["probability"]))
                               + (1 - r["outcome"]) * math.log(max(1e-6, 1 - r["probability"])))
                for r in records
            ) / total_weight
            bins: dict[int, Counter] = defaultdict(Counter)
            for record in records:
                bucket = min(9, int(record["probability"] * 10))
                bins[bucket]["weight"] += record["weight"]
                bins[bucket]["predicted"] += record["weight"] * record["probability"]
                bins[bucket]["observed"] += record["weight"] * record["outcome"]
            calibration_error = sum(
                abs(stats["predicted"] - stats["observed"]) for stats in bins.values()
            ) / total_weight
            for bucket, stats in sorted(bins.items()):
                calibration_rows.append({
                    "year": year, "scope": scope, "probability_bin": f"{bucket / 10:.1f}-{(bucket + 1) / 10:.1f}",
                    "weighted_deliveries": round(stats["weight"], 3),
                    "mean_predicted": round(stats["predicted"] / stats["weight"], 4),
                    "observed_win_share": round(stats["observed"] / stats["weight"], 4),
                })
            high = [r for r in records if r["leverage"] >= LEVERAGE_THRESHOLD]
            summary_rows.append({
                "year": year, "scope": scope,
                "matches": len({r["mid"] for r in records}),
                "legal_deliveries": len(records),
                "training_matches": len(train_ids),
                "training_through_year": year - 1,
                "brier": round(brier, 4),
                "raw_brier": round(raw_brier, 4),
                "elo_only_brier": round(elo_brier, 4),
                "half_brier": 0.25,
                "log_loss": round(log_loss, 4),
                "calibration_error": round(calibration_error, 4),
                "mean_predicted": round(sum(r["weight"] * r["probability"] for r in records) / total_weight, 4),
                "observed_win_share": round(sum(r["weight"] * r["outcome"] for r in records) / total_weight, 4),
                "mean_leverage": round(sum(r["leverage"] for r in records) / len(records), 4),
                "high_leverage_cutoff": LEVERAGE_THRESHOLD,
                "high_leverage_balls": len(high),
                "high_leverage_also_rule_high": sum(r["rule_tier"] == "high" for r in high),
                "high_leverage_rule_low": sum(r["rule_tier"] == "low" for r in high),
            })
            print(
                f"{year} {scope}: {len({r['mid'] for r in records})} matches, "
                f"Brier {brier:.4f} (raw {raw_brier:.4f}) vs Elo {elo_brier:.4f}, "
                f"ECE {calibration_error:.4f}"
            )
            selected_by_match: dict[str, list[dict]] = defaultdict(list)
            for record in records:
                if record["legal_before"] % 3 == 0:
                    selected_by_match[record["mid"]].append(record)
            for mid, selected in selected_by_match.items():
                calibration_match_ids[scope].add(mid)
                calibration_history[scope].extend(
                    (r["raw_probability"], r["outcome"], 1 / len(selected))
                    for r in selected
                )
    write_csv("win_probability_delivery.csv", DELIVERY_FIELDS, delivery_rows)
    write_csv("win_probability_summary.csv", SUMMARY_FIELDS, summary_rows)
    write_csv("win_probability_calibration.csv", CALIBRATION_FIELDS, calibration_rows)
    write_csv("win_probability_models.csv", MODEL_FIELDS, model_rows)
    write_csv("win_probability_calibrators.csv", CALIBRATOR_FIELDS, calibrator_rows)
    print(f"Out-of-time chase probabilities: {len(delivery_rows)} deliveries")


if __name__ == "__main__":
    main()
