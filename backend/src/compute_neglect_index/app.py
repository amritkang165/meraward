"""``compute_neglect_index`` — recompute every ward's statistics, hourly.

EventBridge-scheduled. Scans the complaints table, groups by ward, and writes
the four raw inputs the API reads back:

    open_count · resolved_count · median_open_age_days · median_resolution_days

Two deliberate choices.

**The formula is not reimplemented here.** It lives in :mod:`common.index` and is
called from here, so the scheduled job and the read path can never disagree. An
earlier standalone version of this Lambda had its own copy of the weights; two
implementations of one formula is a drift bug waiting to happen.

**Raw inputs are the stored truth, not the score.** The score is written too,
but only so a human can eyeball the table — every reader recomputes from the
raw fields. That way a change to the formula takes effect immediately instead of
waiting for the next scheduled run to rewrite hundreds of rows.

Hourly, not daily: a daily job may never fire inside a demo window.
"""

from __future__ import annotations

import logging
import statistics
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from common.aws import dynamodb_resource
from common.config import load_config
from common.index import compute_neglect_index

log = logging.getLogger()
log.setLevel(logging.INFO)

RESOLVED = "RESOLVED"


def _parse_time(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _scan_all(table) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    kwargs: dict[str, Any] = {}
    while True:
        result = table.scan(**kwargs)
        items.extend(result.get("Items") or [])
        token = result.get("LastEvaluatedKey")
        if not token:
            return items
        kwargs["ExclusiveStartKey"] = token


def _ward_stats(complaints: list[dict[str, Any]], now: datetime) -> dict[str, Any]:
    """Reduce one ward's complaints to the four numbers the index needs."""
    open_rows = [c for c in complaints if str(c.get("status") or "") != RESOLVED]
    resolved_rows = [c for c in complaints if str(c.get("status") or "") == RESOLVED]

    open_ages: list[float] = []
    for row in open_rows:
        created = _parse_time(row.get("created_at"))
        if created:
            open_ages.append(max((now - created).total_seconds() / 86400.0, 0.0))

    resolution_days: list[float] = []
    for row in resolved_rows:
        created = _parse_time(row.get("created_at"))
        resolved = _parse_time(row.get("resolved_at"))
        if created and resolved and resolved >= created:
            resolution_days.append((resolved - created).total_seconds() / 86400.0)

    return {
        "open_count": len(open_rows),
        "resolved_count": len(resolved_rows),
        "median_open_age_days": statistics.median(open_ages) if open_ages else 0.0,
        "median_resolution_days": (
            statistics.median(resolution_days) if resolution_days else 0.0
        ),
    }


def handler(event: dict[str, Any] | None = None, context: Any = None) -> dict[str, Any]:
    cfg = load_config()
    resource = dynamodb_resource()
    complaints_table = resource.Table(cfg.complaints_table)
    wards_table = resource.Table(cfg.wards_table)

    now = datetime.now(timezone.utc)
    by_ward: dict[str, list[dict[str, Any]]] = {}

    for complaint in _scan_all(complaints_table):
        ward_id = str(complaint.get("ward_id") or "").strip()
        if ward_id:
            by_ward.setdefault(ward_id, []).append(complaint)

    ranked = unranked = 0

    with wards_table.batch_writer() as batch:
        for ward_id, complaints in by_ward.items():
            stats = _ward_stats(complaints, now)
            result = compute_neglect_index(**stats)

            item: dict[str, Any] = {
                "ward_id": ward_id,
                # The four raw inputs. Readers recompute the score from these.
                "open_count": stats["open_count"],
                "resolved_count": stats["resolved_count"],
                "median_open_age_days": Decimal(str(round(stats["median_open_age_days"], 2))),
                "median_resolution_days": Decimal(
                    str(round(stats["median_resolution_days"], 2))
                ),
                # Denormalised for eyeballing the table; not read back.
                "neglect_index": Decimal(str(result.score)) if result.has_score else None,
                "index_band": result.band,
                "index_updated_at": now.isoformat(),
            }
            batch.put_item(Item=item)

            if result.has_score:
                ranked += 1
            else:
                unranked += 1

    log.info(
        "recomputed %d wards (%d ranked, %d below the minimum sample)",
        len(by_ward),
        ranked,
        unranked,
    )
    return {"wards": len(by_ward), "ranked": ranked, "unranked": unranked}


__all__ = ["handler"]
