"""DynamoDB access.

Thin on purpose: the access patterns are known exactly, so there is no ORM here,
just the handful of reads and writes the handlers actually perform.

Clients are created lazily and cached at module level. Creating a boto3 resource
costs real milliseconds, and a Lambda container serves many invocations.
"""

from __future__ import annotations

import logging
from typing import Any, Final

from .aws import dynamodb_resource
from .config import load_config

log = logging.getLogger(__name__)

__all__ = [
    "councillor_block",
    "get_complaint",
    "get_ward_record",
    "photo_url",
    "put_complaint",
    "record_delivery",
    "query_complaints",
    "scan_wards",
    "update_complaint_draft",
    "update_complaint_status",
    "ward_stats",
]


def _table(name: str):
    return dynamodb_resource().Table(name)


def get_ward_record(ward_id: str) -> dict[str, Any] | None:
    """Fetch a ward's row from the ``Wards`` table.

    Returns ``None`` when the ward has no row yet — which is normal before the
    first index computation has run, and must render as "no data", never as a
    zero.
    """
    key = (ward_id or "").strip()
    if not key:
        return None
    try:
        item = _table(load_config().wards_table).get_item(Key={"ward_id": key}).get("Item")
    except Exception:
        # A dashboard that cannot reach DynamoDB should still show the ward name
        # from the polygon data rather than 500.
        log.exception("ward record lookup failed for %s", key)
        return None
    return item or None


def ward_stats(record: dict[str, Any] | None) -> dict[str, Any]:
    """Pull the four index inputs out of a ward row, with safe defaults."""
    record = record or {}
    return {
        "open_count": record.get("open_count") or 0,
        "resolved_count": record.get("resolved_count") or 0,
        "median_open_age_days": record.get("median_open_age_days") or 0,
        "median_resolution_days": record.get("median_resolution_days") or 0,
    }


def put_complaint(item: dict[str, Any]) -> None:
    """Write a new complaint.

    Conditional on the id not already existing: a retried invocation must not
    silently overwrite a complaint that already has a draft on it.
    """
    _table(load_config().complaints_table).put_item(
        Item=item, ConditionExpression="attribute_not_exists(complaint_id)"
    )


def get_complaint(complaint_id: str, *, consistent: bool = False) -> dict[str, Any] | None:
    """Fetch a complaint.

    ``consistent`` matters for the SQS worker: DynamoDB reads are eventually
    consistent by default, and the worker can pick up a message within
    milliseconds of the row being written. Without a strongly consistent read it
    would intermittently see nothing and treat a real complaint as missing.
    """
    key = (complaint_id or "").strip()
    if not key:
        return None
    item = (
        _table(load_config().complaints_table)
        .get_item(Key={"complaint_id": key}, ConsistentRead=consistent)
        .get("Item")
    )
    return item or None


#: Councillor fields we are willing to publish. Contact details are deliberately
#: absent: we do not email officials, so their addresses are not on the critical
#: path and we are not collecting them.
_COUNCILLOR_FIELDS: Final[tuple[str, ...]] = ("councillor_name", "party")


def councillor_block(record: dict[str, Any] | None) -> dict[str, Any] | None:
    """Build the councillor block, or ``None`` when we have not sourced it.

    Two rules from PRD §12, enforced here rather than trusted to the frontend:

    * Every populated councillor field **must** carry a ``contact_source``. If
      the source is missing, the whole block is withheld rather than published
      unattributed.
    * The block is identity only — name, party, provenance. It is never
      combined with the Neglect Index, which scores the ward and not the person.

    Returning ``None`` is meaningful: the UI renders an explicit "not available"
    badge, never a blank card and never a guess.
    """
    record = record or {}
    name = (record.get("councillor_name") or "").strip()
    source = (record.get("contact_source") or "").strip()

    if not name or not source:
        return None

    block: dict[str, Any] = {"name": name, "source": source}
    party = (record.get("party") or "").strip()
    block["party"] = party or None
    return block


def update_complaint_draft(complaint_id: str, draft: dict[str, Any]) -> None:
    """Attach a composed draft to an existing complaint.

    Conditional on the complaint existing, so a draft can never resurrect a row
    that was deleted, and so a late worker retry cannot create a headless one.
    """
    _table(load_config().complaints_table).update_item(
        Key={"complaint_id": complaint_id},
        UpdateExpression=(
            "SET subject = :s, body_en = :en, body_hi = :hi, "
            "draft_source = :src, draft_status = :status"
        ),
        ExpressionAttributeValues={
            ":s": draft["subject"],
            ":en": draft["body_en"],
            ":hi": draft["body_hi"],
            ":src": draft.get("source", "template"),
            ":status": "DRAFTED",
        },
        ConditionExpression="attribute_exists(complaint_id)",
    )


def _page(fn, **kwargs) -> list[dict[str, Any]]:
    """Run a query/scan to completion.

    Paging matters even at demo scale: DynamoDB caps a page at 1 MB, and a
    dashboard that silently showed the first page would under-report the map.
    """
    items: list[dict[str, Any]] = []
    while True:
        result = fn(**kwargs)
        items.extend(result.get("Items") or [])
        token = result.get("LastEvaluatedKey")
        if not token:
            return items
        kwargs["ExclusiveStartKey"] = token


def query_complaints(
    *, status: str | None = None, ward_id: str | None = None
) -> list[dict[str, Any]]:
    """Fetch complaints, using whichever index the filter allows.

    GSI2 is ``status + created_at`` and GSI1 is ``ward_id + created_at``, so a
    filtered dashboard query hits an index. An unfiltered map view falls back to
    a scan, which is the right call for a few hundred rows: the alternative is a
    search cluster we deliberately did not buy.
    """
    from boto3.dynamodb.conditions import Key

    table = _table(load_config().complaints_table)

    if status:
        return _page(
            table.query, IndexName="GSI2", KeyConditionExpression=Key("status").eq(status)
        )
    if ward_id:
        return _page(
            table.query, IndexName="GSI1", KeyConditionExpression=Key("ward_id").eq(ward_id)
        )
    return _page(table.scan)


def scan_wards() -> list[dict[str, Any]]:
    """Every ward row. ~250 items, so this is a scan and that is fine."""
    return _page(_table(load_config().wards_table).scan)


def photo_url(photo_key: str | None, *, expires_in: int = 3600) -> str | None:
    """Presigned GET for a complaint photo.

    The bucket blocks public ACLs, so photos are served through short-lived
    signed URLs rather than being made world-readable.
    """
    key = (photo_key or "").strip()
    cfg = load_config()
    if not key or not cfg.photos_bucket:
        return None
    try:
        from .aws import s3_client

        return s3_client().generate_presigned_url(
            "get_object",
            Params={"Bucket": cfg.photos_bucket, "Key": key},
            ExpiresIn=expires_in,
        )
    except Exception:
        log.exception("could not sign photo url for %s", key)
        return None


def update_complaint_status(
    complaint_id: str,
    *,
    new_status: str,
    expected_status: str,
    timestamps: dict[str, Any] | None = None,
    clear: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Move a complaint to a new status, conditional on its current one.

    The condition is what makes two people clicking the same magic link at the
    same time safe: the second write fails rather than overwriting the first.
    Raises ``ConditionalCheckFailedException`` when the row has moved on.
    """
    sets = ["#s = :new"]
    names: dict[str, str] = {"#s": "status"}
    values: dict[str, Any] = {":new": new_status, ":expected": expected_status}

    for i, (field, value) in enumerate((timestamps or {}).items()):
        sets.append(f"#t{i} = :t{i}")
        names[f"#t{i}"] = field
        values[f":t{i}"] = value

    expression = "SET " + ", ".join(sets)
    if clear:
        removes = []
        for i, field in enumerate(clear):
            removes.append(f"#r{i}")
            names[f"#r{i}"] = field
        expression += " REMOVE " + ", ".join(removes)

    return _table(load_config().complaints_table).update_item(
        Key={"complaint_id": complaint_id},
        UpdateExpression=expression,
        ExpressionAttributeNames=names,
        ExpressionAttributeValues=values,
        ConditionExpression="attribute_exists(complaint_id) AND #s = :expected",
        ReturnValues="ALL_NEW",
    )


def record_delivery(
    complaint_id: str,
    *,
    draft_status: str,
    delivery_mode: str,
    recipient: str,
    message_id: str | None = None,
    note: str | None = None,
) -> None:
    """Record what happened when we tried to deliver a drafted complaint."""
    names = {"#ds": "draft_status", "#dm": "delivery_mode", "#r": "delivery_recipient"}
    values: dict[str, Any] = {
        ":ds": draft_status,
        ":dm": delivery_mode,
        ":r": recipient,
    }
    sets = ["#ds = :ds", "#dm = :dm", "#r = :r"]

    if message_id:
        names["#mid"] = "ses_message_id"
        values[":mid"] = message_id
        sets.append("#mid = :mid")
    if note:
        names["#n"] = "delivery_note"
        values[":n"] = note
        sets.append("#n = :n")

    _table(load_config().complaints_table).update_item(
        Key={"complaint_id": complaint_id},
        UpdateExpression="SET " + ", ".join(sets),
        ExpressionAttributeNames=names,
        ExpressionAttributeValues=values,
        ConditionExpression="attribute_exists(complaint_id)",
    )
