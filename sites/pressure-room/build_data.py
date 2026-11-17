"""Export only the twenty final selections for the public dashboard."""

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "data" / "processed" / "final_rankings.csv"
DEST = Path(__file__).resolve().parent / "dist" / "rankings.json"

FIELDS = (
    "rank",
    "role",
    "player_name",
    "legacy_rank",
    "state_rank",
    "rank_sum",
    "legacy_conservative_score",
    "state_conservative_score",
    "state_effective_balls",
    "state_pressure_matches",
    "state_positive_match_share",
    "state_bootstrap_p10",
    "state_bootstrap_p90",
)
INTS = {"rank", "legacy_rank", "state_rank", "rank_sum", "state_pressure_matches"}
STRINGS = {"role", "player_name"}

with SOURCE.open(newline="", encoding="utf-8") as handle:
    rows = list(csv.DictReader(handle))

assert len(rows) == 20
assert {row["role"] for row in rows} == {"batting", "bowling"}
assert all(sum(row["role"] == role for row in rows) == 10 for role in ("batting", "bowling"))

public_rows = []
for row in rows:
    public_rows.append({
        field: row[field] if field in STRINGS else int(row[field]) if field in INTS else float(row[field])
        for field in FIELDS
    })

DEST.write_text(json.dumps(public_rows, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
print(f"Exported {len(public_rows)} summary rows to {DEST}")
