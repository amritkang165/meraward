"""Seed demonstration complaints that the rest of the system can actually read.

    python data/seed_complaints.py --count 240 --profile meraward

Every row is generated to satisfy the real contract, because a seed row that the
API cannot read is worse than no seed row at all:

* **``ward_id`` comes from ``wards.geojson``**, so it matches a polygon the
  lookup can resolve — not an invented ``W001``.
* **Coordinates fall inside that ward's polygon**, by rejection sampling. A
  marker outside its own ward would make the map contradict the ward card.
* **``issue_type`` is one of the five enum values** the composer and the filters
  understand, not free text.
* **The bilingual letter is composed for real**, so the dashboard and complaint
  pages show actual Hindi and English rather than empty panels.

> Every row carries ``is_demo = True``. The UI surfaces it and ``/about``
> explains it. Reviewers understand demo data; they do not forgive being misled
> about which is which.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "backend" / "src"))

from common.composer import compose  # noqa: E402
from common.ids import complaint_id as new_complaint_id  # noqa: E402
from common.ids import status_token as new_status_token  # noqa: E402

ISSUE_TYPES = ["POTHOLE", "STREETLIGHT", "GARBAGE", "WATER", "OTHER"]
#: Potholes and garbage dominate real civic reporting; "other" is a long tail.
ISSUE_WEIGHTS = [34, 22, 26, 12, 6]

STATUSES = ["OPEN", "ACKNOWLEDGED", "RESOLVED"]
STATUS_WEIGHTS = [48, 18, 34]


def load_wards(path: Path) -> list[dict]:
    from shapely.geometry import shape

    data = json.loads(path.read_text(encoding="utf-8"))
    wards = []
    for feature in data.get("features") or []:
        props = feature.get("properties") or {}
        if not props.get("ward_id") or not feature.get("geometry"):
            continue
        geom = shape(feature["geometry"])
        if geom.is_empty:
            continue
        wards.append(
            {
                "ward_id": props["ward_id"],
                "ward_name": props.get("ward_name") or props["ward_id"],
                "geom": geom,
            }
        )
    return wards


def point_in(geom, rng: random.Random, attempts: int = 200):
    """A random point genuinely inside the polygon, by rejection sampling.

    Returns ``None`` rather than a wrong point if the shape is too awkward to
    hit — a marker in the wrong ward would make the map contradict the ward card.
    """
    from shapely.geometry import Point

    min_lng, min_lat, max_lng, max_lat = geom.bounds
    for _ in range(attempts):
        p = Point(rng.uniform(min_lng, max_lng), rng.uniform(min_lat, max_lat))
        if geom.contains(p):
            return p
    return None


def build_rows(wards: list[dict], count: int, rng: random.Random) -> list[dict]:
    now = datetime.now(timezone.utc)
    rows: list[dict] = []
    skipped = 0

    # Concentrate reports in a subset of wards. Spreading them evenly would make
    # every ward score identically and the leaderboard meaningless.
    hot = rng.sample(wards, k=min(len(wards), max(8, len(wards) // 6)))

    for _ in range(count):
        ward = rng.choice(hot if rng.random() < 0.72 else wards)
        point = point_in(ward["geom"], rng)
        if point is None:
            skipped += 1
            continue

        issue = rng.choices(ISSUE_TYPES, weights=ISSUE_WEIGHTS, k=1)[0]
        status = rng.choices(STATUSES, weights=STATUS_WEIGHTS, k=1)[0]
        created = now - timedelta(days=rng.randint(10, 120), hours=rng.randint(0, 23))

        cid = new_complaint_id(int(created.timestamp() * 1000))
        draft = compose(
            issue,
            ward["ward_name"],
            reported_on=created,
            ward_id=ward["ward_id"],
            reference=cid,
        )

        row: dict = {
            "complaint_id": cid,
            "ward_id": ward["ward_id"],
            "ward_name": ward["ward_name"],
            "created_at": created.isoformat(),
            "status": status,
            "draft_status": "DRAFTED",
            "draft_source": draft.source,
            "issue_type": issue,
            "lat": Decimal(str(round(point.y, 6))),
            "lng": Decimal(str(round(point.x, 6))),
            "subject": draft.subject,
            "body_en": draft.body_en,
            "body_hi": draft.body_hi,
            "is_demo": True,
            "delivery_mode": "DEMO_OUTBOX",
            "status_token": new_status_token(),
        }

        if status in ("ACKNOWLEDGED", "RESOLVED"):
            acknowledged = created + timedelta(days=rng.randint(1, 6))
            row["acknowledged_at"] = acknowledged.isoformat()
            if status == "RESOLVED":
                resolved = acknowledged + timedelta(days=rng.randint(2, 40))
                row["resolved_at"] = min(resolved, now).isoformat()

        rows.append(row)

    if skipped:
        print(f"  skipped {skipped} row(s) whose polygon resisted sampling")
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=240)
    parser.add_argument("--wards", type=Path, default=REPO / "data" / "wards.geojson")
    parser.add_argument("--table", default="meraward-complaints")
    parser.add_argument("--region", default="ap-south-1")
    parser.add_argument("--profile", default=None)
    parser.add_argument("--seed", type=int, default=42, help="reproducible output")
    parser.add_argument("--dry-run", action="store_true", help="build rows, write nothing")
    args = parser.parse_args()

    if not args.wards.exists():
        print(f"ward file not found: {args.wards}", file=sys.stderr)
        return 1

    rng = random.Random(args.seed)
    wards = load_wards(args.wards)
    print(f"loaded {len(wards)} wards from {args.wards.name}")

    rows = build_rows(wards, args.count, rng)
    touched = {r["ward_id"] for r in rows}
    resolved = sum(1 for r in rows if r["status"] == "RESOLVED")
    print(f"built {len(rows)} complaints across {len(touched)} wards ({resolved} resolved)")

    if args.dry_run:
        sample = rows[0]
        print("\n--- sample row ---")
        for key in ("complaint_id", "ward_id", "ward_name", "status", "issue_type", "lat", "lng"):
            print(f"  {key:16} {sample[key]}")
        print(f"  {'subject':16} {sample['subject']}")
        print("\ndry run: nothing written")
        return 0

    import boto3

    session = boto3.Session(profile_name=args.profile, region_name=args.region)
    table = session.resource("dynamodb").Table(args.table)
    with table.batch_writer() as batch:
        for row in rows:
            batch.put_item(Item=row)

    print(f"wrote {len(rows)} rows to {args.table}")
    print("every row carries is_demo = True")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
