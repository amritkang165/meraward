"""``complaints_query`` — everything the app reads.

    GET /complaints/{id}                          → detail + timeline (the UI polls this)
    GET /complaints?bbox=&status=&issue_type=     → map markers
    GET /leaderboard                              → wards ranked by Neglect Index

Aggregation happens in this Lambda. It is a few hundred rows: a ``for`` loop, not
a search cluster. The leaderboard is cached in the container for 60 seconds,
which is what makes a dashboard refresh during a demo free.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from common.index import EXPLANATION, compute_neglect_index
from common.responses import ApiError, ok, server_error
from common.store import (
    get_complaint,
    photo_url,
    query_complaints,
    scan_wards,
    ward_stats,
)
from common.views import map_marker, public_complaint
from common.wards import get_index

log = logging.getLogger()
log.setLevel(logging.INFO)

VALID_STATUSES = ("OPEN", "ACKNOWLEDGED", "RESOLVED")
LEADERBOARD_TTL_SECONDS = 60
MAX_MARKERS = 2000

_leaderboard_cache: dict[str, Any] = {"at": 0.0, "payload": None}


# --------------------------------------------------------------------------
# GET /complaints/{id}
# --------------------------------------------------------------------------


def _detail(complaint_id: str) -> dict[str, Any]:
    record = get_complaint(complaint_id)
    if not record:
        raise ApiError(404, "complaint_not_found", "No complaint with that id.")

    body = public_complaint(record, photo=photo_url(record.get("photo_key")))

    ward = get_index().get(record.get("ward_id") or "")
    if ward is not None:
        body["ward"] = ward.to_dict()

    return body


# --------------------------------------------------------------------------
# GET /complaints
# --------------------------------------------------------------------------


def _parse_bbox(raw: str | None) -> tuple[float, float, float, float] | None:
    """``minLng,minLat,maxLng,maxLat`` — the order MapLibre hands us."""
    if not raw or not raw.strip():
        return None
    parts = raw.split(",")
    if len(parts) != 4:
        raise ApiError(400, "invalid_bbox", "bbox must be minLng,minLat,maxLng,maxLat.")
    try:
        min_lng, min_lat, max_lng, max_lat = (float(p) for p in parts)
    except ValueError:
        raise ApiError(400, "invalid_bbox", "bbox values must be numbers.") from None
    if min_lng > max_lng or min_lat > max_lat:
        raise ApiError(400, "invalid_bbox", "bbox minimums must not exceed maximums.")
    return min_lng, min_lat, max_lng, max_lat


def _in_bbox(marker: dict[str, Any], box: tuple[float, float, float, float]) -> bool:
    min_lng, min_lat, max_lng, max_lat = box
    return min_lng <= float(marker["lng"]) <= max_lng and min_lat <= float(marker["lat"]) <= max_lat


def _markers(params: dict[str, Any]) -> dict[str, Any]:
    status = (params.get("status") or "").strip().upper() or None
    if status and status not in VALID_STATUSES:
        raise ApiError(
            400, "invalid_status", f"status must be one of: {', '.join(VALID_STATUSES)}."
        )

    issue_type = (params.get("issue_type") or "").strip().upper() or None
    ward_id = (params.get("ward_id") or "").strip() or None
    box = _parse_bbox(params.get("bbox"))

    records = query_complaints(status=status, ward_id=ward_id)

    markers: list[dict[str, Any]] = []
    for record in records:
        marker = map_marker(record)
        if marker is None:
            continue
        if issue_type and marker["issue_type"] != issue_type:
            continue
        if box and not _in_bbox(marker, box):
            continue
        markers.append(marker)

    markers.sort(key=lambda m: m.get("created_at") or "", reverse=True)
    truncated = len(markers) > MAX_MARKERS

    return {
        "complaints": markers[:MAX_MARKERS],
        "count": min(len(markers), MAX_MARKERS),
        "truncated": truncated,
        "filters": {
            "status": status,
            "issue_type": issue_type,
            "ward_id": ward_id,
            "bbox": list(box) if box else None,
        },
    }


# --------------------------------------------------------------------------
# GET /leaderboard
# --------------------------------------------------------------------------


def _leaderboard() -> dict[str, Any]:
    cached = _leaderboard_cache
    if cached["payload"] is not None and (time.time() - cached["at"]) < LEADERBOARD_TTL_SECONDS:
        return cached["payload"]

    index = get_index()
    rows: list[dict[str, Any]] = []
    unranked: list[dict[str, Any]] = []

    for record in scan_wards():
        ward_id = record.get("ward_id")
        if not ward_id:
            continue
        ward = index.get(ward_id)
        result = compute_neglect_index(**ward_stats(record))

        row = {
            "ward_id": ward_id,
            "ward_name": (ward.ward_name if ward else record.get("ward_name") or ward_id),
            "zone": ward.zone if ward else record.get("zone"),
            "neglect_index": result.score,
            "index_band": result.band,
            "index_basis": result.basis,
            "note": result.note,
        }
        (rows if result.has_score else unranked).append(row)

    # Worst first: the point of the board is which wards are being ignored.
    rows.sort(key=lambda r: (-r["neglect_index"], r["ward_name"]))
    for position, row in enumerate(rows, start=1):
        row["rank"] = position

    payload = {
        "wards": rows,
        "unranked": sorted(unranked, key=lambda r: r["ward_name"]),
        "ranked_count": len(rows),
        "unranked_count": len(unranked),
        "index_explanation": EXPLANATION,
        "data_notice": (
            "Complaint data on this deployment is demo data. The index scores a "
            "ward, never an individual. See /about."
        ),
    }

    _leaderboard_cache.update(at=time.time(), payload=payload)
    return payload


def reset_cache() -> None:
    """Tests only."""
    _leaderboard_cache.update(at=0.0, payload=None)


# --------------------------------------------------------------------------


def handler(event: dict[str, Any], context: Any = None) -> dict[str, Any]:
    try:
        path = (event.get("rawPath") or event.get("routeKey") or "").lower()
        path_params = event.get("pathParameters") or {}
        query = event.get("queryStringParameters") or {}

        if "leaderboard" in path:
            return ok(_leaderboard(), cache_seconds=LEADERBOARD_TTL_SECONDS)

        complaint_id = (path_params.get("id") or path_params.get("complaint_id") or "").strip()
        if complaint_id:
            # Not cached: the UI polls this while the draft is still PENDING.
            return ok(_detail(complaint_id))

        return ok(_markers(query), cache_seconds=30)

    except ApiError as exc:
        return exc.to_response()
    except Exception:
        log.exception("complaints_query failed")
        return server_error()


__all__ = ["handler", "reset_cache"]
