"""DynamoDB access.

Thin on purpose: the access patterns are known exactly, so there is no ORM here,
just the handful of reads and writes the handlers actually perform.

Clients are created lazily and cached at module level. Creating a boto3 resource
costs real milliseconds, and a Lambda container serves many invocations.
"""

from __future__ import annotations

import logging
from typing import Any, Final

from .config import load_config

log = logging.getLogger(__name__)

__all__ = ["councillor_block", "get_ward_record", "ward_stats"]

_resource = None


def _table(name: str):
    global _resource
    if _resource is None:
        import boto3  # lazy: pure-logic tests must not need the AWS SDK

        _resource = boto3.resource("dynamodb", region_name=load_config().region)
    return _resource.Table(name)


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
