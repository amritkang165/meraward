"""``health`` — GET /health.

A real Lambda rather than a mock integration, because this is the first thing
anyone pings and the first thing that tells us whether a deploy actually worked.

It reports what is *configured* and whether the ward index loads. It deliberately
does not report secrets, bucket names or queue URLs: this endpoint is public.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any

from common.config import load_config
from common.responses import ok

log = logging.getLogger()
log.setLevel(logging.INFO)


def _ward_index_status() -> dict[str, Any]:
    """Load the index if it is not already loaded, and report what happened.

    Worth doing eagerly: a `/health` that says "ok" while the geometry source is
    missing is worse than no health check at all.
    """
    try:
        from common.wards import get_index

        index = get_index()
        return {"loaded": True, "wards": len(index)}
    except Exception as exc:  # noqa: BLE001 - the reason is the whole point here
        log.exception("ward index unavailable")
        return {"loaded": False, "reason": type(exc).__name__}


def handler(event: dict[str, Any] | None = None, context: Any = None) -> dict[str, Any]:
    cfg = load_config()
    wards = _ward_index_status()

    return ok(
        {
            "status": "ok" if wards["loaded"] else "degraded",
            "service": "meraward",
            "time": datetime.now(timezone.utc).isoformat(),
            "region": cfg.region,
            "version": os.environ.get("AWS_LAMBDA_FUNCTION_VERSION", "local"),
            "ward_index": wards,
            "drafting": {
                # Which path will actually draft a complaint right now. Bedrock
                # is optional by design, so "template" is a healthy answer.
                "mode": "bedrock" if cfg.use_bedrock else "template",
            },
            "delivery_mode": cfg.delivery_mode,
        }
    )


__all__ = ["handler"]
