"""``draft_and_send`` — the slow half of filing a complaint.

SQS-triggered. ``create_complaint`` returns ``202`` the moment the row is
written; everything expensive happens here, so nobody waits on a model.

    SQS → read complaint → draft (Bedrock, else composer) → save
        → deliver (demo outbox / verified inbox) → record → CloudWatch

Three properties this worker is built around:

**It always produces a letter.** Bedrock is tried first and the deterministic
composer catches every failure mode. ``draft_status`` never sticks on
``PENDING`` because a model was unavailable.

**It is idempotent.** SQS delivers at least once, and a visibility timeout that
expires mid-draft will hand the same complaint over again. A complaint that is
already drafted is skipped rather than redrafted.

**It reports partial batch failures.** Only the records that genuinely failed go
back on the queue; the rest are not redelivered and redrafted. This needs
``FunctionResponseTypes: [ReportBatchItemFailures]`` on the event source mapping.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from common.bedrock import BedrockUnavailable, draft_with_bedrock
from common.composer import Draft, compose
from common.delivery import deliver, emit_drafted_metric
from common.store import get_complaint, record_delivery, update_complaint_draft

log = logging.getLogger()
log.setLevel(logging.INFO)

DRAFT_PENDING = "PENDING"
DRAFT_DRAFTED = "DRAFTED"
DRAFT_SENT = "SENT"

#: Already-finished states. Seeing one means this is a redelivery.
TERMINAL = {DRAFT_DRAFTED, DRAFT_SENT}


def _draft_for(complaint: dict[str, Any]) -> Draft:
    """Draft with Bedrock, falling back to the composer.

    The fallback is not an error path. Bedrock is optional in this project by
    design, and a templated letter is a complete, correct product.
    """
    issue_type = complaint.get("issue_type")
    ward_name = str(complaint.get("ward_name") or "")
    ward_id = complaint.get("ward_id")
    reference = complaint.get("complaint_id")
    landmark = complaint.get("landmark")
    reported_on = complaint.get("created_at")
    description = complaint.get("description")
    has_photo = bool(complaint.get("photo_key"))

    try:
        return draft_with_bedrock(
            issue_type,
            ward_name,
            ward_id=ward_id,
            reported_on=reported_on,
            landmark=landmark,
            reference=reference,
            description=description,
        )
    except BedrockUnavailable as exc:
        log.info("drafting with the template composer instead (%s)", exc)
    except Exception:  # noqa: BLE001 - never let drafting fail the complaint
        log.exception("unexpected error from the Bedrock path; using the composer")

    return compose(
        issue_type,
        ward_name,
        reported_on=reported_on,
        ward_id=ward_id,
        reference=reference,
        landmark=landmark,
        description=description,
        has_photo=has_photo,
    )


def _process(complaint_id: str) -> None:
    """Draft and deliver one complaint. Raises only on retryable failures."""
    complaint = get_complaint(complaint_id, consistent=True)

    if not complaint:
        # Not retryable. A strongly consistent read found nothing, so the row
        # genuinely is not there — a deleted complaint, or a message for a write
        # that never landed. Retrying would just fill the DLQ.
        log.error("no complaint %s; dropping the message", complaint_id)
        return

    if str(complaint.get("draft_status") or DRAFT_PENDING) in TERMINAL:
        log.info("%s is already drafted; skipping redelivery", complaint_id)
        return

    draft = _draft_for(complaint)

    # Save the draft before attempting delivery. If SES then fails, the user
    # still has their letter — the draft is the product, the email is the extra.
    update_complaint_draft(complaint_id, draft.to_dict())

    result = deliver(
        subject=draft.subject,
        body_en=draft.body_en,
        body_hi=draft.body_hi,
        ward_name=str(complaint.get("ward_name") or ""),
        ward_id=complaint.get("ward_id"),
    )

    record_delivery(
        complaint_id,
        draft_status=DRAFT_SENT if result.sent else DRAFT_DRAFTED,
        delivery_mode=result.mode,
        recipient=result.recipient,
        message_id=result.message_id,
        note=result.note,
    )

    emit_drafted_metric(draft.source)
    log.info(
        "drafted %s via %s; delivery=%s sent=%s",
        complaint_id,
        draft.source,
        result.mode,
        result.sent,
    )


def _complaint_id_from(record: dict[str, Any]) -> str | None:
    try:
        body = json.loads(record.get("body") or "{}")
    except ValueError:
        log.error("message body was not JSON; dropping")
        return None
    complaint_id = str(body.get("complaint_id") or "").strip()
    if not complaint_id:
        log.error("message had no complaint_id; dropping")
        return None
    return complaint_id


def handler(event: dict[str, Any], context: Any = None) -> dict[str, Any]:
    failures: list[dict[str, str]] = []

    for record in event.get("Records") or []:
        message_id = record.get("messageId", "")
        complaint_id = _complaint_id_from(record)

        # A malformed message will never succeed, so it is dropped rather than
        # retried three times into the dead-letter queue.
        if not complaint_id:
            continue

        try:
            _process(complaint_id)
        except Exception:
            log.exception("failed to process %s; will retry", complaint_id)
            failures.append({"itemIdentifier": message_id})

    return {"batchItemFailures": failures}


__all__ = ["handler"]
