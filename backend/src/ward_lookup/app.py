"""``ward_lookup`` — which ward is this point in, and how neglected is it?

Routes:
    GET /wards/lookup?lat=&lng=   → ward for a coordinate
    GET /wards/{ward_id}          → ward detail

This is the first thing a user touches and the first thing a judge clicks, so it
has one job and does it in under three seconds: point-in-polygon against the
in-Lambda STRtree, one DynamoDB read for the statistics, index computed in
process.
"""

from __future__ import annotations

import logging
from typing import Any

from common.index import EXPLANATION, compute_neglect_index
from common.responses import ApiError, bad_request, not_found, ok, server_error
from common.store import councillor_block, get_ward_record, ward_stats
from common.wards import Ward, get_index

log = logging.getLogger()
log.setLevel(logging.INFO)

#: Shown on every ward card and index display. The deployment's complaint data
#: is generated for demonstration, and saying so is not optional (PRD §12).
DATA_NOTICE = (
    "Complaint data on this deployment is demo data. See /about for sources, "
    "licences and how the index is computed."
)

_CACHE_SECONDS = 60


def _parse_coord(raw: str | None, name: str, limit: float) -> float:
    if raw is None or not str(raw).strip():
        raise ApiError(400, "missing_coordinate", f"{name} is required.")
    try:
        value = float(str(raw).strip())
    except (TypeError, ValueError):
        raise ApiError(400, "invalid_coordinate", f"{name} must be a number.") from None
    if value != value or value in (float("inf"), float("-inf")):
        raise ApiError(400, "invalid_coordinate", f"{name} must be a real number.")
    if not -limit <= value <= limit:
        raise ApiError(
            400, "coordinate_out_of_range", f"{name} must be between -{limit} and {limit}."
        )
    return value


def _payload(ward: Ward) -> dict[str, Any]:
    record = get_ward_record(ward.ward_id)
    stats = ward_stats(record)
    index = compute_neglect_index(**stats)

    return {
        "ward_id": ward.ward_id,
        "ward_name": ward.ward_name,
        "zone": ward.zone,
        "neglect_index": index.score,
        "index_band": index.band,
        "index_note": index.note,
        "index_basis": index.basis,
        "index_explanation": EXPLANATION,
        # Identity only, and withheld entirely unless we sourced it.
        "councillor": councillor_block(record),
        "data_notice": DATA_NOTICE,
    }


def _lookup_by_coords(params: dict[str, Any]) -> dict[str, Any]:
    lat = _parse_coord(params.get("lat"), "lat", 90.0)
    lng = _parse_coord(params.get("lng"), "lng", 180.0)

    ward = get_index().lookup(lat, lng)
    if ward is None:
        raise ApiError(
            404,
            "outside_coverage",
            "That location is outside the area this deployment covers.",
        )
    body = _payload(ward)
    body["query"] = {"lat": lat, "lng": lng}
    return body


def _lookup_by_id(ward_id: str) -> dict[str, Any]:
    ward = get_index().get(ward_id)
    if ward is None:
        raise ApiError(404, "ward_not_found", f"No ward with id {ward_id!r}.")
    return _payload(ward)


def handler(event: dict[str, Any], context: Any = None) -> dict[str, Any]:
    try:
        path_params = event.get("pathParameters") or {}
        query = event.get("queryStringParameters") or {}

        ward_id = (path_params.get("ward_id") or "").strip()
        body = _lookup_by_id(ward_id) if ward_id else _lookup_by_coords(query)
        return ok(body, cache_seconds=_CACHE_SECONDS)

    except ApiError as exc:
        return exc.to_response()
    except ValueError as exc:
        return bad_request("invalid_request", str(exc))
    except FileNotFoundError:
        log.exception("ward geometry source is missing")
        return server_error("ward_data_unavailable", "Ward boundary data is unavailable.")
    except Exception:
        log.exception("ward_lookup failed")
        return server_error()


__all__ = ["handler", "not_found"]
