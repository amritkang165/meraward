"""Atomic, per-client fixed-minute write budgets shared across Lambda containers.

Only API Gateway's source address is trusted, never a caller-supplied forwarding
header. Counter keys contain a digest, scope and minute, not a raw address.
TTL cleans up old counters; correctness does not depend on prompt TTL deletion.
"""

from __future__ import annotations

import hashlib
import logging
import time

from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError

from .aws import dynamodb_resource
from .config import load_config
from .responses import ApiError

log = logging.getLogger(__name__)


def enforce_write_budget(event: dict, scope: str) -> None:
    cfg = load_config()
    if not cfg.rate_limit_table:
        # Existing deployments must provision the table through SAM before
        # enabling this setting. The local runner provisions it too.
        return
    source = (event.get("requestContext") or {}).get("http", {}).get("sourceIp")
    if not isinstance(source, str) or not source.strip():
        raise ApiError(400, "missing_client_address", "The request has no client address.")
    limits = {"report": cfg.report_limit, "upload": cfg.upload_limit, "status": cfg.status_limit}
    limit = limits[scope]
    now = int(time.time())
    minute = now // 60
    digest = hashlib.sha256(source.strip().encode("utf-8")).hexdigest()
    try:
        dynamodb_resource().Table(cfg.rate_limit_table).update_item(
            Key={"client_window": f"{scope}:{minute}:{digest}"},
            UpdateExpression="SET expires_at = :expiry ADD hits :one",
            ExpressionAttributeValues={":expiry": (minute + 2) * 60, ":one": 1},
            ConditionExpression=Attr("hits").not_exists() | Attr("hits").lt(limit),
        )
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
            raise ApiError(429, "rate_limited", "Too many requests. Please wait a minute and try again.",
                           headers={"Retry-After": str(60 - now % 60)}) from None
        log.exception("write budget unavailable")
        raise ApiError(503, "write_unavailable", "Reporting is temporarily unavailable. Please try again.") from None
    except Exception:
        log.exception("write budget unavailable")
        raise ApiError(503, "write_unavailable", "Reporting is temporarily unavailable. Please try again.") from None
