"""Compile the final equal-rank consensus from two independently eligible methods."""

from __future__ import annotations

import csv

from build_cumulative_dataset import DEFAULT_OUTPUT

FIELDS = [
    "rank", "role", "player_id", "player_name", "legacy_rank", "state_rank",
    "rank_sum", "legacy_conservative_score", "state_conservative_score",
    "legacy_effective_balls", "state_effective_balls", "legacy_pressure_matches",
    "state_pressure_matches", "legacy_positive_match_share",
    "state_positive_match_share", "state_bootstrap_p10", "state_bootstrap_p90",
]


def read(name: str) -> dict[tuple[str, str], dict[str, str]]:
    with (DEFAULT_OUTPUT / name).open(newline="", encoding="utf-8") as stream:
        return {(row["role"], row["player_id"]): row for row in csv.DictReader(stream)
                if row["eligible"] == "1"}


def main() -> None:
    legacy = read("player_pressure_summary.csv")
    state = read("candidate_v2_player_summary.csv")
    common = legacy.keys() & state.keys()
    output = []
    for role in ("batting", "bowling"):
        players = sorted((key for key in common if key[0] == role), key=lambda key: int(key[1]))
        if len(players) < 10:
            raise ValueError(f"Too few jointly eligible {role} players")
        old_order = sorted(players, key=lambda key: (-float(legacy[key]["conservative_score"]), int(key[1])))
        new_order = sorted(players, key=lambda key: (-float(state[key]["conservative_score"]), int(key[1])))
        old_rank = {key: place for place, key in enumerate(old_order, 1)}
        new_rank = {key: place for place, key in enumerate(new_order, 1)}
        players.sort(key=lambda key: (
            old_rank[key] + new_rank[key], max(old_rank[key], new_rank[key]),
            -float(state[key]["conservative_score"]), int(key[1]),
        ))
        for place, key in enumerate(players[:10], 1):
            a, b = legacy[key], state[key]
            output.append({
                "rank": place, "role": role, "player_id": key[1],
                "player_name": a["player_name"], "legacy_rank": old_rank[key],
                "state_rank": new_rank[key], "rank_sum": old_rank[key] + new_rank[key],
                "legacy_conservative_score": a["conservative_score"],
                "state_conservative_score": b["conservative_score"],
                "legacy_effective_balls": a["pressure_effective_balls"],
                "state_effective_balls": b["pressure_effective_balls"],
                "legacy_pressure_matches": a["pressure_matches"],
                "state_pressure_matches": b["pressure_matches"],
                "legacy_positive_match_share": a["positive_pressure_match_share"],
                "state_positive_match_share": b["positive_match_share"],
                "state_bootstrap_p10": b["bootstrap_p10"],
                "state_bootstrap_p90": b["bootstrap_p90"],
            })
        print(role, "jointly eligible", len(old_order),
              "top 10", ", ".join(legacy[key]["player_name"] for key in players[:10]))
    path = DEFAULT_OUTPUT / "final_rankings.csv"
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(output)
    print(path)


if __name__ == "__main__":
    main()
