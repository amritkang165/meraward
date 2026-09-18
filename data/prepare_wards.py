"""Turn a raw ward boundary export into the ``wards.geojson`` the Lambda loads.

    python data/prepare_wards.py data/raw/delhi_wards_datameet.geojson data/wards.geojson

What it does:

* normalises properties onto ``ward_id`` / ``ward_name`` / ``zone``
* repairs invalid rings and drops features with no usable geometry
* simplifies each polygon to at most :data:`MAX_POINTS` vertices, adaptively, so
  the whole file stays small enough to parse on a Lambda cold start
* reports what it did, loudly, so the numbers can be checked against the source

**It never invents a boundary.** Every output feature comes from an input
feature; nothing is synthesised, interpolated, or filled in.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from shapely.geometry import mapping, shape
from shapely.geometry.base import BaseGeometry

#: Simplification target. The Lambda parses this file on every cold start, so
#: vertex count is latency. 500 is well below the point where a ward outline
#: looks wrong at city zoom.
MAX_POINTS = 500

#: Degrees. ~1.1 m at Delhi's latitude — below the accuracy of the source data,
#: so starting here costs no real fidelity.
START_TOLERANCE = 0.00001
MAX_TOLERANCE = 0.005


def count_points(geom: BaseGeometry) -> int:
    data = mapping(geom)
    total = 0
    stack: list[Any] = [data["coordinates"]]
    while stack:
        item = stack.pop()
        if not item:
            continue
        if isinstance(item[0], (int, float)):
            total += 1
        else:
            stack.extend(item)
    return total


def simplify_to_budget(geom: BaseGeometry, budget: int = MAX_POINTS) -> tuple[BaseGeometry, float]:
    """Simplify until the vertex budget is met, preserving topology.

    Returns the geometry and the tolerance used. If the budget cannot be met
    before the tolerance would visibly distort the shape, the geometry is
    returned at ``MAX_TOLERANCE`` rather than mangled further — a slightly
    heavier polygon beats a wrong one.
    """
    if count_points(geom) <= budget:
        return geom, 0.0

    tolerance = START_TOLERANCE
    while tolerance <= MAX_TOLERANCE:
        candidate = geom.simplify(tolerance, preserve_topology=True)
        if not candidate.is_empty and candidate.is_valid and count_points(candidate) <= budget:
            return candidate, tolerance
        tolerance *= 2

    fallback = geom.simplify(MAX_TOLERANCE, preserve_topology=True)
    return (fallback if fallback.is_valid and not fallback.is_empty else geom), MAX_TOLERANCE


def normalise_id(raw: Any, name: str) -> str | None:
    """Map a source ward number onto our ``DEL-*`` id space.

    The source mixes three numbering systems, so they are kept distinguishable
    rather than renumbered into one sequence: renumbering would silently break
    any cross-reference to the source data.
    """
    value = str(raw or "").strip().upper()
    if not value:
        return None
    if value.isdigit():
        return f"DEL-{int(value):04d}"
    match = re.match(r"^([A-Z]+)[_\-]?(\d+)$", value)
    if match:
        prefix, number = match.groups()
        return f"DEL-{prefix}-{int(number):02d}"
    return f"DEL-{re.sub(r'[^A-Z0-9]+', '-', value).strip('-')}"


def zone_for(ward_id: str) -> str:
    if ward_id.startswith("DEL-NDMC"):
        return "New Delhi Municipal Council"
    if ward_id.startswith("DEL-CANT"):
        return "Delhi Cantonment Board"
    return "Municipal Corporation of Delhi"


def titlecase(name: str) -> str:
    """Source names are SHOUTED. Title-case them, keeping short acronyms."""
    cleaned = re.sub(r"\s+", " ", str(name or "").strip())
    if not cleaned:
        return ""
    words = []
    for word in cleaned.split(" "):
        if len(word) <= 3 and word.isupper() and word.isalpha():
            words.append(word)  # NDMC, JJ, etc.
        else:
            words.append(word.capitalize())
    return " ".join(words)


def prepare(source: Path, destination: Path) -> dict[str, Any]:
    raw = json.loads(source.read_text(encoding="utf-8"))
    features = raw.get("features") or []

    out: list[dict[str, Any]] = []
    skipped: list[str] = []
    repaired = 0
    simplified = 0
    seen: set[str] = set()
    points_before = points_after = 0

    for feature in features:
        props = feature.get("properties") or {}
        name_raw = props.get("Ward_Name") or props.get("ward_name") or ""
        ward_id = normalise_id(
            props.get("Ward_No") or props.get("ward_no") or props.get("ward_id"), name_raw
        )
        geometry = feature.get("geometry")

        if not ward_id:
            skipped.append(f"no ward number ({name_raw or 'unnamed'})")
            continue
        if not geometry:
            skipped.append(f"{ward_id}: no geometry")
            continue
        if ward_id in seen:
            skipped.append(f"{ward_id}: duplicate id")
            continue

        try:
            geom = shape(geometry)
        except Exception as exc:
            skipped.append(f"{ward_id}: unreadable geometry ({exc})")
            continue

        if geom.is_empty:
            skipped.append(f"{ward_id}: empty geometry")
            continue

        if not geom.is_valid:
            geom = geom.buffer(0)
            repaired += 1
            if geom.is_empty or not geom.is_valid:
                skipped.append(f"{ward_id}: unrepairable geometry")
                continue

        before = count_points(geom)
        geom, tolerance = simplify_to_budget(geom)
        after = count_points(geom)
        points_before += before
        points_after += after
        if tolerance:
            simplified += 1

        seen.add(ward_id)
        out.append(
            {
                "type": "Feature",
                "properties": {
                    "ward_id": ward_id,
                    "ward_name": titlecase(name_raw) or ward_id,
                    "zone": zone_for(ward_id),
                },
                "geometry": mapping(geom),
            }
        )

    out.sort(key=lambda f: f["properties"]["ward_id"])
    collection = {"type": "FeatureCollection", "features": out}
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(collection, separators=(",", ":")), encoding="utf-8"
    )

    return {
        "input_features": len(features),
        "output_features": len(out),
        "skipped": skipped,
        "repaired": repaired,
        "simplified": simplified,
        "points_before": points_before,
        "points_after": points_after,
        "zones": Counter(f["properties"]["zone"] for f in out),
        "bytes": destination.stat().st_size,
        "max_points": max((count_points(shape(f["geometry"])) for f in out), default=0),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()

    if not args.source.exists():
        print(f"source not found: {args.source}", file=sys.stderr)
        return 1

    report = prepare(args.source, args.destination)

    print(f"in  : {report['input_features']} features   {args.source}")
    print(f"out : {report['output_features']} features   {args.destination}")
    print(f"      {report['bytes'] / 1024:.0f} KB, largest polygon {report['max_points']} points")
    print(
        f"      vertices {report['points_before']} -> {report['points_after']} "
        f"({100 - report['points_after'] * 100 // max(report['points_before'], 1)}% smaller)"
    )
    print(f"      repaired {report['repaired']}, simplified {report['simplified']}")
    for zone, count in report["zones"].most_common():
        print(f"      {count:>4}  {zone}")
    if report["skipped"]:
        print(f"skip: {len(report['skipped'])}")
        for reason in report["skipped"][:10]:
            print(f"      - {reason}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
