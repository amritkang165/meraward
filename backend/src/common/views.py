"""Public projections of stored records.

Everything the API returns about a complaint passes through here. The complaint
detail page is a *shareable public URL* — that is the point of it — so deciding
what is publishable is a security boundary, not formatting.

Three attributes must never leave the database:

* ``status_token`` is the magic link that lets anyone change a complaint's
  status. Publishing it on the page the token controls would make the whole
  lifecycle forgeable by anyone who opened the complaint.
* ``reporter_email`` belongs to a citizen who filed a complaint about their
  street. It is used once, to send them their own tracking link.
* ``ses_message_id`` is delivery plumbing and tells a reader nothing.

``photo_key`` is a separate case: it is not published as a field, but it is
necessarily embedded in the presigned ``photo_url``, because that is what
serving the photo means. It is an opaque ULID path and useless unsigned.

Allow-list rather than deny-list: a field added to the table later is private by
default and has to be named here to become public.
"""

from __future__ import annotations

from typing import Any, Final

__all__ = [
    "PRIVATE_COMPLAINT_FIELDS",
    "PUBLIC_COMPLAINT_FIELDS",
    "UNPUBLISHED_BUT_EMBEDDED",
    "map_marker",
    "public_complaint",
    "status_timeline",
]

#: Every complaint attribute that may be published. Nothing else is.
PUBLIC_COMPLAINT_FIELDS: Final[tuple[str, ...]] = (
    "complaint_id",
    "ward_id",
    "ward_name",
    "created_at",
    "status",
    "draft_status",
    "draft_source",
    "issue_type",
    "lat",
    "lng",
    "landmark",
    # The reporter's own account. Public on purpose: it is the substance of the
    # complaint, and the detail page is meant to be shareable.
    "description",
    "subject",
    "body_en",
    "body_hi",
    "is_demo",
    "delivery_mode",
    "acknowledged_at",
    "resolved_at",
    "reopened_at",
)

#: Secrets. These strings must not appear *anywhere* in a response, not as a
#: field and not embedded in one. Asserted in tests.
PRIVATE_COMPLAINT_FIELDS: Final[tuple[str, ...]] = (
    "status_token",
    "reporter_email",
    "ses_message_id",
)

#: Not published as its own field, but deliberately embedded in the presigned
#: ``photo_url``. The key is an opaque ULID path and is useless without the
#: signature, so this is not a leak — but it is the reason ``photo_key`` is not
#: in the list above.
UNPUBLISHED_BUT_EMBEDDED: Final[tuple[str, ...]] = ("photo_key",)

_STATUS_LABELS: Final[dict[str, str]] = {
    "OPEN": "Reported",
    "ACKNOWLEDGED": "Acknowledged by ward office",
    "RESOLVED": "Marked resolved",
    "REOPENED": "Reported still broken",
}


def status_timeline(record: dict[str, Any]) -> list[dict[str, Any]]:
    """Build the status timeline from the timestamps actually on the record.

    Only steps that really happened are returned, each with its timestamp. The
    UI renders the remaining steps as pending, so a complaint that is still open
    shows a timeline rather than an empty box.
    """
    steps: list[dict[str, Any]] = []

    created = record.get("created_at")
    if created:
        steps.append({"status": "OPEN", "label": _STATUS_LABELS["OPEN"], "at": created})

    acknowledged = record.get("acknowledged_at")
    if acknowledged:
        steps.append(
            {
                "status": "ACKNOWLEDGED",
                "label": _STATUS_LABELS["ACKNOWLEDGED"],
                "at": acknowledged,
            }
        )

    resolved = record.get("resolved_at")
    if resolved:
        steps.append(
            {"status": "RESOLVED", "label": _STATUS_LABELS["RESOLVED"], "at": resolved}
        )

    # A reopen is part of the story, not an erasure of it: "someone marked this
    # fixed and it was not" is exactly the accountability signal we are after.
    reopened = record.get("reopened_at")
    if reopened:
        steps.append(
            {"status": "OPEN", "label": _STATUS_LABELS["REOPENED"], "at": reopened}
        )

    steps.sort(key=lambda s: s["at"] or "")
    return steps


def public_complaint(
    record: dict[str, Any], *, photo: str | None = None
) -> dict[str, Any]:
    """Project a stored complaint onto its public shape."""
    out: dict[str, Any] = {
        field: record.get(field) for field in PUBLIC_COMPLAINT_FIELDS
    }
    out["photo_url"] = photo
    out["timeline"] = status_timeline(record)
    # A reader must always be able to tell demo data from a real report.
    out["is_demo"] = bool(record.get("is_demo", False))
    return out


def map_marker(record: dict[str, Any]) -> dict[str, Any] | None:
    """The minimum a map pin needs.

    Deliberately narrow: the map can hold hundreds of these, and the letter
    bodies are the largest attribute on the row. Sending them to render a dot
    would be several hundred kilobytes for nothing.
    """
    lat, lng = record.get("lat"), record.get("lng")
    if lat is None or lng is None:
        return None
    return {
        "complaint_id": record.get("complaint_id"),
        "ward_id": record.get("ward_id"),
        "lat": lat,
        "lng": lng,
        "issue_type": record.get("issue_type"),
        "status": record.get("status"),
        "created_at": record.get("created_at"),
        "is_demo": bool(record.get("is_demo", False)),
    }
