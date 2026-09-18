"""``status_update`` — move a complaint through its lifecycle.

    POST /complaints/{id}/status  {token, action}
                                → {status, timeline, ...}

There is no login anywhere in this product, so the token *is* the authorisation.
It is a random UUID stored on the complaint row, handed to the reporter in their
tracking link and to the ward office in the complaint email. Anyone holding it
may move the complaint; nobody else can.

Three actions, matching the three buttons on ``/u/:token``:

============  ==========================================================
acknowledge   OPEN → ACKNOWLEDGED. Someone has seen it.
resolve       → RESOLVED. It is fixed.
reopen        → OPEN. "Still broken" — the fix did not hold, or never came.
============  ==========================================================

Reopening is deliberately first-class. "Somebody marked this resolved and it was
not" is precisely the accountability signal the product exists to capture, so it
appends to the timeline rather than erasing the resolution.
"""

from __future__ import annotations

import json
import logging
import secrets
from datetime import datetime, timezone
from typing import Any, Final

from common.responses import ApiError, ok, server_error
from common.store import get_complaint, photo_url, update_complaint_status
from common.views import public_complaint

log = logging.getLogger()
log.setLevel(logging.INFO)

STATUS_OPEN: Final[str] = "OPEN"
STATUS_ACKNOWLEDGED: Final[str] = "ACKNOWLEDGED"
STATUS_RESOLVED: Final[str] = "RESOLVED"

#: action → (resulting status, timestamp field to set, fields to clear)
_ACTIONS: Final[dict[str, tuple[str, str, tuple[str, ...]]]] = {
    "acknowledge": (STATUS_ACKNOWLEDGED, "acknowledged_at", ()),
    "resolve": (STATUS_RESOLVED, "resolved_at", ()),
    # Clearing resolved_at is what makes the ward's open/resolved counts - and
    # therefore its Neglect Index - tell the truth again after a bad resolution.
    "reopen": (STATUS_OPEN, "reopened_at", ("resolved_at",)),
}

#: Which current statuses each action may be applied from.
_ALLOWED_FROM: Final[dict[str, tuple[str, ...]]] = {
    "acknowledge": (STATUS_OPEN,),
    "resolve": (STATUS_OPEN, STATUS_ACKNOWLEDGED),
    "reopen": (STATUS_ACKNOWLEDGED, STATUS_RESOLVED),
}


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


def _resolve_action(body: dict[str, Any]) -> str:
    """Accept either ``action`` or a ``new_status``, whichever the caller sends."""
    action = str(body.get("action") or "").strip().lower()
    if not action:
        status = str(body.get("new_status") or "").strip().upper()
        action = {
            STATUS_ACKNOWLEDGED: "acknowledge",
            STATUS_RESOLVED: "resolve",
            STATUS_OPEN: "reopen",
        }.get(status, "")
    if action not in _ACTIONS:
        raise ApiError(
            400, "invalid_action", f"action must be one of: {', '.join(_ACTIONS)}."
        )
    return action


def _check_token(supplied: Any, record: dict[str, Any]) -> None:
    token = str(supplied or "").strip()
    if not token:
        raise ApiError(400, "missing_token", "token is required.")
    stored = str(record.get("status_token") or "")
    # Constant-time: a plain == leaks the token prefix through timing, and this
    # endpoint is public and unauthenticated.
    if not stored or not secrets.compare_digest(token, stored):
        raise ApiError(403, "invalid_token", "That link is not valid for this complaint.")


def handler(event: dict[str, Any], context: Any = None) -> dict[str, Any]:
    try:
        complaint_id = (
            (event.get("pathParameters") or {}).get("id")
            or (event.get("pathParameters") or {}).get("complaint_id")
            or ""
        ).strip()
        if not complaint_id:
            raise ApiError(400, "missing_complaint_id", "A complaint id is required.")

        body = _parse_body(event)
        action = _resolve_action(body)

        record = get_complaint(complaint_id)
        if not record:
            raise ApiError(404, "complaint_not_found", "No complaint with that id.")

        _check_token(body.get("token"), record)

        current = str(record.get("status") or STATUS_OPEN)
        target, stamp_field, clear = _ACTIONS[action]

        # Magic links get clicked twice. Landing on the status you asked for is
        # success, not an error.
        if current == target:
            return ok(
                {
                    **public_complaint(record, photo=photo_url(record.get("photo_key"))),
                    "changed": False,
                }
            )

        if current not in _ALLOWED_FROM[action]:
            raise ApiError(
                409,
                "invalid_transition",
                f"A complaint that is {current} cannot be {action}d.",
            )

        now = datetime.now(timezone.utc).isoformat()
        try:
            result = update_complaint_status(
                complaint_id,
                new_status=target,
                expected_status=current,
                timestamps={stamp_field: now},
                clear=clear,
            )
        except Exception as exc:
            # The conditional write failed, so someone else moved it first.
            if "ConditionalCheckFailed" in type(exc).__name__ or "ConditionalCheckFailed" in str(exc):
                raise ApiError(
                    409, "status_changed", "Someone updated this complaint first."
                ) from None
            raise

        updated = result.get("Attributes") or {**record, "status": target, stamp_field: now}
        return ok(
            {
                **public_complaint(updated, photo=photo_url(updated.get("photo_key"))),
                "changed": True,
            }
        )

    except ApiError as exc:
        return exc.to_response()
    except Exception:
        log.exception("status_update failed")
        return server_error()


__all__ = ["handler"]
