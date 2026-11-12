"""Match supplied deliveries to Cricsheet JSON and cache verified extras.

Run with downloaded ipl_json.zip and t20s_male_json.zip from cricsheet.org.
Only complete, delivery-for-delivery matches are imported. The compact gzip
cache makes later pipeline builds independent of live archive downloads.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import io
import json
import re
import zipfile
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

from build_cumulative_dataset import DEFAULT_INPUT, DEFAULT_OUTPUT, ROOT, match_reason, read_index


DEFAULT_EXTRAS = ROOT / "data" / "external" / "cricsheet_extras.csv.gz"
AUDIT_FIELDS = ["match_id", "match_date", "match_format", "source_match_id",
                "source_date", "date_gap_days", "source_archive", "status",
                "pack_deliveries", "verified_deliveries", "first_verified_extras",
                "second_verified_extras", "first_verified_total", "second_verified_total"]


def team_key(name: str) -> str:
    normalized = " ".join(name.casefold().replace("bengaluru", "bangalore").split())
    return normalized.replace("usa", "united states of america") if normalized == "usa" else normalized


def flatten(innings: dict) -> list[dict]:
    return [delivery for over in innings["overs"] for delivery in over["deliveries"]]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ipl-zip", type=Path, required=True)
    parser.add_argument("--t20i-zip", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_EXTRAS)
    args = parser.parse_args()
    competitions = read_index(DEFAULT_INPUT / "competitions.csv", "comp_id")
    matches = read_index(DEFAULT_INPUT / "matches.csv", "match_id")
    eligible = {
        mid: match for mid, match in matches.items()
        if not match_reason(match, competitions[match["comp_id"]])
    }
    pack = defaultdict(lambda: defaultdict(list))
    with (DEFAULT_INPUT / "ball_by_ball.csv").open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            if row["match_id"] in eligible and row["innings"] in ("1", "2"):
                pack[row["match_id"]][row["innings"]].append(row)
    index = defaultdict(list)
    archives = {"IPL": args.ipl_zip, "T20I": args.t20i_zip}
    for scope, path in archives.items():
        with zipfile.ZipFile(path) as archive:
            for filename in archive.namelist():
                if not filename.endswith(".json"):
                    continue
                obj = json.loads(archive.read(filename))
                info = obj["info"]
                if len(info.get("teams", [])) != 2 or not info.get("dates"):
                    continue
                day = date.fromisoformat(info["dates"][0])
                teams = frozenset(team_key(name) for name in info["teams"])
                index[(scope, day, teams)].append((Path(filename).stem, obj))

    audits = []
    verified = []
    statuses = Counter()
    for mid, match in sorted(eligible.items(), key=lambda item: (item[1]["match_date"], int(item[0]))):
        scope = "IPL" if competitions[match["comp_id"]]["match_format"] == "T20" else "T20I"
        day = date.fromisoformat(match["match_date"])
        teams = frozenset(team_key(name) for name in (match["home_team"], match["away_team"]))
        candidates = []
        for gap in (-1, 0, 1):
            candidates.extend((gap, sid, obj) for sid, obj in
                              index.get((scope, day + timedelta(days=gap), teams), []))
        rows = pack[mid]
        selected = None
        for gap, sid, obj in sorted(candidates, key=lambda item: (abs(item[0]), item[1])):
            if len(obj.get("innings", [])) < 2:
                continue
            if any(innings.get("penalty_runs") for innings in obj["innings"][:2]):
                continue
            external = [flatten(obj["innings"][i]) for i in (0, 1)]
            if any(len(rows[str(i + 1)]) != len(external[i]) for i in (0, 1)):
                continue
            aligned = True
            for i in (0, 1):
                for source, target in zip(rows[str(i + 1)], external[i]):
                    extras = target.get("extras", {})
                    legal = not ("wides" in extras or "noballs" in extras)
                    if (int(source["runs"]) != int(target["runs"]["batter"])
                            or (source["extras_type"] not in ("wide", "Overstep")) != legal
                            or (source["is_wicket"].lower() == "true") != bool(target.get("wickets"))):
                        aligned = False
                        break
                if not aligned:
                    break
            if aligned:
                selected = (gap, sid, external)
                break
        audit = {
            "match_id": mid, "match_date": match["match_date"],
            "match_format": scope, "source_match_id": "", "source_date": "",
            "date_gap_days": "", "source_archive": "", "status": "",
            "pack_deliveries": sum(len(rows[str(i)]) for i in (1, 2)),
            "verified_deliveries": 0, "first_verified_extras": "",
            "second_verified_extras": "", "first_verified_total": "",
            "second_verified_total": "",
        }
        if selected is None:
            audit["status"] = "no_candidate" if not candidates else "delivery_conflict"
        else:
            gap, sid, external = selected
            audit.update({
                "status": "verified", "source_match_id": sid,
                "source_date": (day + timedelta(days=gap)).isoformat(),
                "date_gap_days": gap, "source_archive": archives[scope].name,
                "verified_deliveries": audit["pack_deliveries"],
            })
            for i in (0, 1):
                extra_sum = 0
                total = 0
                for source, target in zip(rows[str(i + 1)], external[i]):
                    extras = int(target["runs"]["extras"])
                    extra_sum += extras
                    total += int(target["runs"]["total"])
                    verified.append((mid, str(i + 1), source["innings_ball_num"], extras, sid))
                audit[("first" if i == 0 else "second") + "_verified_extras"] = extra_sum
                audit[("first" if i == 0 else "second") + "_verified_total"] = total
            margin = re.search(r"won by\s+(\d+)\s+runs?\b", match["result"], re.I)
            if margin and (int(audit["first_verified_total"])
                           - int(audit["second_verified_total"])) != int(margin.group(1)):
                raise ValueError(f"Matched score conflicts with declared run margin: {mid}")
        audits.append(audit)
        statuses[audit["status"]] += 1
    DEFAULT_OUTPUT.mkdir(parents=True, exist_ok=True)
    with (DEFAULT_OUTPUT / "exact_score_coverage.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=AUDIT_FIELDS)
        writer.writeheader()
        writer.writerows(audits)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("wb") as binary:
        with gzip.GzipFile(fileobj=binary, mode="wb", filename="", mtime=0,
                           compresslevel=9) as compressed:
            with io.TextIOWrapper(compressed, encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(["match_id", "innings", "innings_ball_num", "extras_runs", "source_match_id"])
                writer.writerows(verified)
    print(f"Cricsheet match audit: {dict(statuses)}; verified deliveries: {len(verified)}")
    print(args.output)


if __name__ == "__main__":
    main()
