"""``create_complaint`` — the fast path. Must stay under about a second.

    POST /complaints  {photo_key, issue_type, lat, lng, reporter_email?, landmark?}
                    → 202 {complaint_id, status_token, ward, draft_status}

What happens here: validate, resolve the ward by point-in-polygon, write the row,
enqueue, return. What does *not* happen here: the AI draft and the email. Those
take seconds, so they run on the SQS worker and the UI polls. The user never
waits on a model.

If SQS is unreachable we do not fail the request. The complaint is already
written and the deterministic composer runs in microseconds, so we draft inline
and return a complete complaint rather than a 500. That is precisely what the
composer was written first for.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from common.aws import sqs_client
from common.composer import compose, normalise_issue_type
from common.config import load_config
from common.ids import complaint_id as new_complaint_id
from common.ids import status_token as new_status_token
from common.responses import ApiError, accepted, server_error
from common.store import put_complaint, update_complaint_draft
from common.validation import (
    require_coords,
    require_evidence,
    validate_description,
    validate_email,
    validate_photo_key,
    validate_text,
)
from common.wards import get_index

log = logging.getLogger()
log.setLevel(logging.INFO)

MAX_LANDMARK_CHARS = 140

STATUS_OPEN = "OPEN"
DRAFT_PENDING = "PENDING"
DRAFT_DRAFTED = "DRAFTED"


def _parse_body(event: dict[str, Any]) -> dict[str, Any]:
    raw = event.get("body")
    if raw is None:
        raise ApiError(400, "missing_body", "A JSON body is required.")
    if event.get("isBase64Encoded"):
        import base64

        raw = base64.b64decode(raw).decode("utf-8")
    try:
        parsed = json.loads(raw) if isinstance(raw, str) else raw
    except (ValueError, TypeError):
        raise ApiError(400, "invalid_json", "Request body must be valid JSON.") from None
    if not isinstance(parsed, dict):
        raise ApiError(400, "invalid_json", "Request body must be a JSON object.")
    return parsed


def _enqueue(complaint_id: str) -> bool:
    """Best-effort enqueue. Returns False rather than raising."""
    cfg = load_config()
    if not cfg.draft_queue_url:
        log.warning("DRAFT_QUEUE_URL is not configured; drafting inline")
        return False
    try:
        sqs_client().send_message(
            QueueUrl=cfg.draft_queue_url,
            MessageBody=json.dumps({"complaint_id": complaint_id}),
        )
        return True
    except Exception:
        log.exception("failed to enqueue %s; drafting inline", complaint_id)
        return False


def handler(event: dict[str, Any], context: Any = None) -> dict[str, Any]:
    try:
        body = _parse_body(event)

        # Photo and description are each optional so that a spoken, written or
        # photographed report can all take the route that suits it — but a
        # complaint carrying neither is not a report, and require_evidence says so.
        photo_key = validate_photo_key(body.get("photo_key"), required=False)
        description = validate_description(body.get("description"))
        require_evidence(photo_key, description)

        issue_type = normalise_issue_type(body.get("issue_type"))
        lat, lng = require_coords(body)
        reporter_email = validate_email(body.get("reporter_email"))
        landmark = validate_text(body.get("landmark"), "landmark", max_length=MAX_LANDMARK_CHARS)

        ward = get_index().lookup(lat, lng)
        if ward is None:
            raise ApiError(
                404,
                "outside_coverage",
                "That location is outside the area this deployment covers.",
            )

        now = datetime.now(timezone.utc)
        complaint_id = new_complaint_id(int(now.timestamp() * 1000))
        status_token = new_status_token()
        cfg = load_config()

        item: dict[str, Any] = {
            "complaint_id": complaint_id,
            "ward_id": ward.ward_id,
            "ward_name": ward.ward_name,
            "created_at": now.isoformat(),
            "status": STATUS_OPEN,
            "draft_status": DRAFT_PENDING,
            "issue_type": issue_type,
            "lat": Decimal(str(lat)),
            "lng": Decimal(str(lng)),
            # Real citizen reports are never demo rows. The seed script sets this
            # true; nothing else ever does.
            "is_demo": False,
            "delivery_mode": cfg.delivery_mode,
            "status_token": status_token,
        }
        if photo_key:
            item["photo_key"] = photo_key
        if description:
            item["description"] = description
        if reporter_email:
            item["reporter_email"] = reporter_email
        if landmark:
            item["landmark"] = landmark

        # Write first, then enqueue. The other order races: the worker can pick
        # the message up and find no row to draft against.
        put_complaint(item)

        queued = _enqueue(complaint_id)
        if not queued:
            _draft_inline(item, now)

        return accepted(
            {
                "complaint_id": complaint_id,
                "status_token": status_token,
                "status": STATUS_OPEN,
                "draft_status": item["draft_status"],
                "queued": queued,
                "ward": {
                    "ward_id": ward.ward_id,
                    "ward_name": ward.ward_name,
                    "zone": ward.zone,
                },
                "tracking_url": f"/c/{complaint_id}",
            }
        )

    except ApiError as exc:
        return exc.to_response()
    except Exception:
        log.exception("create_complaint failed")
        return server_error()


def _draft_inline(item: dict[str, Any], now: datetime) -> None:
    """Compose the letter here and now, because the queue is unavailable.

    The composer is pure Python and runs in microseconds, so this costs the
    request nothing measurable and the user still gets a complete complaint
    instead of one stuck on PENDING forever. Mutates ``item`` so the response
    reports the real state.

    Everything it needs is already on ``item``, so it reads from there rather
    than taking a parameter per field.
    """
    complaint_id = item["complaint_id"]
    draft = compose(
        item["issue_type"],
        item.get("ward_name") or "",
        reported_on=now,
        ward_id=item["ward_id"],
        reference=complaint_id,
        landmark=item.get("landmark"),
        description=item.get("description"),
        has_photo=bool(item.get("photo_key")),
    )
    item.update(
        subject=draft.subject,
        body_en=draft.body_en,
        body_hi=draft.body_hi,
        draft_source=draft.source,
        draft_status=DRAFT_DRAFTED,
    )
    try:
        update_complaint_draft(complaint_id, draft.to_dict())
    except Exception:
        # The row exists and is OPEN; only the draft is missing. The hourly job
        # and a manual retry can both still fix it, and the UI shows PENDING.
        log.exception("inline draft write failed for %s", complaint_id)
        item["draft_status"] = DRAFT_PENDING


__all__ = ["handler"]
