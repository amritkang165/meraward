"""``presign_upload`` — hand the browser a short-lived S3 PUT URL.

    POST /complaints/presign  {content_type, content_length}
                            → {upload_url, photo_key, expires_in, max_bytes}

The photo goes straight from the phone to S3 and never passes through Lambda or
API Gateway. That keeps us under API Gateway's 10 MB payload limit, keeps the
request fast on a phone on mobile data, and means a large upload costs us no
compute.

Both ``ContentType`` and ``ContentLength`` are baked into the signature, so the
URL can only be used for the exact upload that was requested. Without
``ContentLength`` bound, a presigned PUT accepts an object of any size and the
8 MB cap would be decorative.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from common.aws import s3_client
from common.config import load_config
from common.ids import new_ulid
from common.responses import ApiError, ok, server_error
from common.validation import extension_for, validate_content_type

log = logging.getLogger()
log.setLevel(logging.INFO)

URL_TTL_SECONDS = 900  # 15 minutes: long enough to retake a photo, short enough to matter
MIN_PHOTO_BYTES = 1024  # anything smaller is not a photograph


def _parse_body(event: dict[str, Any]) -> dict[str, Any]:
    raw = event.get("body")
    if raw is None:
        return {}
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


def _validate_length(raw: Any, max_bytes: int) -> int:
    if raw is None or raw == "":
        raise ApiError(400, "missing_content_length", "content_length is required.")
    try:
        value = int(raw)
    except (TypeError, ValueError):
        raise ApiError(400, "invalid_content_length", "content_length must be an integer.") from None
    if value < MIN_PHOTO_BYTES:
        raise ApiError(400, "photo_too_small", "That file is too small to be a photo.")
    if value > max_bytes:
        mb = max_bytes // (1024 * 1024)
        raise ApiError(413, "photo_too_large", f"Photos must be {mb} MB or smaller.")
    return value


def _photo_key(content_type: str) -> str:
    now = datetime.now(timezone.utc)
    return (
        f"photos/{now:%Y/%m/%d}/{new_ulid(int(now.timestamp() * 1000))}"
        f".{extension_for(content_type)}"
    )


def handler(event: dict[str, Any], context: Any = None) -> dict[str, Any]:
    try:
        cfg = load_config()
        if not cfg.photos_bucket:
            log.error("PHOTOS_BUCKET is not configured")
            return server_error("upload_unavailable", "Photo upload is not available.")

        body = _parse_body(event)
        content_type = validate_content_type(body.get("content_type"))
        content_length = _validate_length(body.get("content_length"), cfg.max_photo_bytes)
        photo_key = _photo_key(content_type)

        upload_url = s3_client().generate_presigned_url(
            "put_object",
            Params={
                "Bucket": cfg.photos_bucket,
                "Key": photo_key,
                "ContentType": content_type,
                "ContentLength": content_length,
            },
            ExpiresIn=URL_TTL_SECONDS,
        )

        return ok(
            {
                "upload_url": upload_url,
                "photo_key": photo_key,
                "expires_in": URL_TTL_SECONDS,
                "max_bytes": cfg.max_photo_bytes,
                # The browser must send exactly these on the PUT or the
                # signature will not match.
                "required_headers": {
                    "Content-Type": content_type,
                    "Content-Length": str(content_length),
                },
            }
        )

    except ApiError as exc:
        return exc.to_response()
    except Exception:
        log.exception("presign_upload failed")
        return server_error()


__all__ = ["handler"]
