"""Load MCD councillor identity onto ward rows.

    python data/load_councillors.py --profile meraward
    python data/load_councillors.py --dry-run

**Matching is by ward NAME, never by ward number, and that is the whole point of
this script.**

Our polygons are the pre-2022 delimitation; the councillor list is the post-2022
one. The 2022 re-delimitation renumbered the wards, so the two numbering schemes
do not correspond: joining on ``ward_number`` agrees with the ward name in only
**5 of 250** cases. Doing it that way would attach a real, named, elected person
to a ward they do not represent, 98% of the time. That is not a data-quality
nuisance, it is defamation-shaped, and it is exactly what the project's own rules
forbid.

Name matching resolves roughly half the polygons. The rest are left with no
councillor, which the API already renders as an explicit "not available" — a
deliberate blank rather than a guess.

Every row written carries a ``contact_source`` that states the source *and the
matching method*, because the join is the part a reader would want to question.
The API withholds the whole councillor block when ``contact_source`` is missing,
so an unattributed name cannot reach the page even by accident.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

#: Recorded on every ward we populate. It names the source and, just as
#: importantly, admits how the row was matched.
CONTACT_SOURCE = (
    "MCD 2022 election results and subsequent bye-elections, via the State "
    "Election Commission, NCT of Delhi. Matched to this boundary by ward name; "
    "the boundary shown is the pre-2022 delimitation, so the match is by name "
    "and not by identical geography."
)


def normalise(value: object) -> str:
    """Collapse a ward name to a comparable key.

    Source names differ in case, spacing and punctuation — "Bakhtawar PUR" and
    "Bakhtawarpur" are the same ward written twice.
    """
    return re.sub(r"[^a-z0-9]", "", str(value or "").lower())


def load_polygons(path: Path) -> dict[str, dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, dict] = {}
    for feature in data.get("features") or []:
        props = feature.get("properties") or {}
        ward_id = str(props.get("ward_id") or "").strip()
        if not ward_id:
            continue
        out.setdefault(normalise(props.get("ward_name")), {
            "ward_id": ward_id,
            "ward_name": props.get("ward_name"),
        })
    return out


def load_representatives(path: Path) -> tuple[dict[str, dict], dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    reps: dict[str, dict] = {}
    for ward in data.get("wards") or []:
        councillor = str(ward.get("councillor") or "").strip()
        if not councillor:
            continue
        reps[normalise(ward.get("ward_name"))] = {
            "councillor_name": councillor,
            "party": str(ward.get("party") or "").strip() or None,
            "ward_name": ward.get("ward_name"),
        }
    return reps, data


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wards", type=Path, default=REPO / "data" / "wards.geojson")
    parser.add_argument(
        "--representatives",
        type=Path,
        default=REPO / "data" / "delhi_mcd_ward_representatives.json",
    )
    parser.add_argument("--table", default="meraward-wards")
    parser.add_argument("--region", default="ap-south-1")
    parser.add_argument("--profile", default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    for path in (args.wards, args.representatives):
        if not path.exists():
            print(f"not found: {path}", file=sys.stderr)
            return 1

    polygons = load_polygons(args.wards)
    reps, meta = load_representatives(args.representatives)

    matched = sorted(set(polygons) & set(reps))
    unmatched_polygons = sorted(set(polygons) - set(reps))
    unused_councillors = sorted(set(reps) - set(polygons))

    print(f"source      : {meta.get('dataset')} (as of {meta.get('as_of')})")
    print(f"polygons    : {len(polygons)}")
    print(f"councillors : {len(reps)}")
    print(f"matched     : {len(matched)}  ({100 * len(matched) // max(len(polygons), 1)}% of polygons)")
    print(f"  no councillor for {len(unmatched_polygons)} polygons -> stays 'not available'")
    print(f"  {len(unused_councillors)} councillors have no polygon of that name")

    if args.dry_run:
        print("\nsample of what would be written:")
        for key in matched[:5]:
            print(f"  {polygons[key]['ward_id']:<14} {polygons[key]['ward_name']:<22} "
                  f"-> {reps[key]['councillor_name']} ({reps[key]['party']})")
        print("\ndry run: nothing written")
        return 0

    import boto3

    table = (
        boto3.Session(profile_name=args.profile, region_name=args.region)
        .resource("dynamodb")
        .Table(args.table)
    )

    written = 0
    for key in matched:
        ward = polygons[key]
        rep = reps[key]
        # An update, not a put: the hourly index job owns the statistics on this
        # same row and must not be clobbered.
        table.update_item(
            Key={"ward_id": ward["ward_id"]},
            UpdateExpression=(
                "SET councillor_name = :n, party = :p, contact_source = :s, "
                "councillor_matched_by = :m"
            ),
            ExpressionAttributeValues={
                ":n": rep["councillor_name"],
                ":p": rep["party"],
                ":s": CONTACT_SOURCE,
                ":m": "ward_name",
            },
        )
        written += 1

    print(f"\nwrote councillor identity to {written} ward rows")
    print("every row carries contact_source naming the source and the match method")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
