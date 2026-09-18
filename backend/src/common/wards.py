"""Ward polygons and point-in-polygon lookup.

This is the piece that decides which ward a citizen is standing in, and it runs
**inside the Lambda**. Delhi has ~250 wards; the polygon set is a few megabytes,
and an R-tree query over it is sub-millisecond. A managed search cluster for
this would have been cost and operational surface we cannot afford in a weekend,
and it would have made the "under $10" claim in the demo video false.

The index is built once per cold start and held at module level, so only the
first invocation on a container pays for the parse.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from dataclasses import dataclass
from typing import Any, Final, Iterable

from shapely.geometry import Point, shape
from shapely.strtree import STRtree

from .config import load_config

log = logging.getLogger(__name__)

__all__ = ["Ward", "WardIndex", "get_index", "reset_index"]

_MAX_LAT: Final[float] = 90.0
_MAX_LNG: Final[float] = 180.0


@dataclass(frozen=True)
class Ward:
    """Identity of a ward. Statistics live in DynamoDB, not here."""

    ward_id: str
    ward_name: str
    zone: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"ward_id": self.ward_id, "ward_name": self.ward_name, "zone": self.zone}


class WardIndex:
    """An STRtree over ward polygons, plus the ward metadata alongside it."""

    def __init__(self, wards: list[Ward], geometries: list[Any]) -> None:
        if len(wards) != len(geometries):
            raise ValueError("wards and geometries must be the same length")
        self._wards = wards
        self._geometries = geometries
        self._tree = STRtree(geometries) if geometries else None
        self._by_id = {w.ward_id: w for w in wards}

    def __len__(self) -> int:
        return len(self._wards)

    @property
    def wards(self) -> list[Ward]:
        return list(self._wards)

    def get(self, ward_id: str) -> Ward | None:
        return self._by_id.get((ward_id or "").strip())

    def lookup(self, lat: float, lng: float) -> Ward | None:
        """Return the ward containing the point, or ``None`` if outside coverage."""
        if self._tree is None:
            return None
        if not (-_MAX_LAT <= lat <= _MAX_LAT) or not (-_MAX_LNG <= lng <= _MAX_LNG):
            raise ValueError("coordinates out of range")

        point = Point(lng, lat)  # GeoJSON is (x, y) = (lng, lat)
        candidates = self._tree.query(point, predicate="intersects")

        # The tree narrows by bounding box; confirm real containment. Strict
        # containment wins, so a point on a shared edge does not beat the ward
        # that actually contains it.
        first_touch: int | None = None
        for i in candidates:
            idx = int(i)
            geom = self._geometries[idx]
            if geom.contains(point):
                return self._wards[idx]
            if first_touch is None:
                first_touch = idx

        # Exactly on a boundary: pick deterministically rather than return None.
        return self._wards[first_touch] if first_touch is not None else None

    # ---------------------------------------------------------------- loading

    @classmethod
    def from_geojson(cls, data: dict[str, Any]) -> "WardIndex":
        features: Iterable[dict[str, Any]] = data.get("features") or []
        wards: list[Ward] = []
        geometries: list[Any] = []
        skipped = 0

        for feature in features:
            props = feature.get("properties") or {}
            geometry = feature.get("geometry")
            ward_id = str(props.get("ward_id") or "").strip()

            if not ward_id or not geometry:
                skipped += 1
                continue
            try:
                geom = shape(geometry)
            except Exception:  # malformed geometry in the source data
                skipped += 1
                continue
            if geom.is_empty:
                skipped += 1
                continue
            if not geom.is_valid:
                # buffer(0) is the standard repair for self-intersecting rings,
                # which real-world boundary exports frequently contain.
                geom = geom.buffer(0)
                if geom.is_empty or not geom.is_valid:
                    skipped += 1
                    continue

            wards.append(
                Ward(
                    ward_id=ward_id,
                    ward_name=str(props.get("ward_name") or ward_id).strip(),
                    zone=(str(props["zone"]).strip() if props.get("zone") else None),
                )
            )
            geometries.append(geom)

        if skipped:
            log.warning("ward index: skipped %d unusable feature(s)", skipped)
        return cls(wards, geometries)


# ------------------------------------------------------------------ cold start

_index: WardIndex | None = None
_lock = threading.Lock()


def _read_source() -> dict[str, Any]:
    """Read the GeoJSON from a local path if given, else from S3.

    ``WARDS_GEOJSON_PATH`` exists so tests and ``sam local`` do not need S3.
    """
    local = (os.environ.get("WARDS_GEOJSON_PATH") or "").strip()
    if local:
        with open(local, encoding="utf-8") as fh:
            return json.load(fh)

    cfg = load_config()
    if not cfg.data_bucket:
        raise RuntimeError("DATA_BUCKET is not configured and WARDS_GEOJSON_PATH is unset")

    import boto3  # imported lazily so pure-logic tests need no AWS SDK

    body = (
        boto3.client("s3", region_name=cfg.region)
        .get_object(Bucket=cfg.data_bucket, Key=cfg.wards_geojson_key)["Body"]
        .read()
    )
    return json.loads(body)


def get_index() -> WardIndex:
    """Return the process-wide ward index, building it on first use."""
    global _index
    if _index is not None:
        return _index
    with _lock:
        if _index is None:
            started = time.perf_counter()
            _index = WardIndex.from_geojson(_read_source())
            log.info(
                "ward index built: %d wards in %.0f ms",
                len(_index),
                (time.perf_counter() - started) * 1000,
            )
    return _index


def reset_index() -> None:
    """Drop the cached index. Tests only."""
    global _index
    with _lock:
        _index = None
