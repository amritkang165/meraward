"""HTTP responses for API Gateway HTTP API (payload format 2.0).

One place that decides status codes, CORS and JSON encoding, so a handler never
hand-rolls a dict and quietly omits a header.

Errors carry a stable machine-readable ``code`` alongside the human message. The
frontend branches on the code; the message is for the developer console and for
us at 3am.
"""

from __future__ import annotations

import decimal
import json
from typing import Any, Final, Mapping

__all__ = [
    "ApiError",
    "accepted",
    "bad_request",
    "error",
    "json_encode",
    "not_found",
    "ok",
    "server_error",
]

# The write path has no authorizer and no cookies, so a permissive origin is
# correct here rather than lazy: this is a public read/write civic API.
_CORS: Final[dict[str, str]] = {
    "access-control-allow-origin": "*",
    "access-control-allow-headers": "content-type",
    "access-control-allow-methods": "GET,POST,OPTIONS",
}


class _Encoder(json.JSONEncoder):
    """Handles the types DynamoDB and geometry hand back.

    ``Decimal`` is what boto3 returns for every number; letting it reach
    ``json.dumps`` unhandled is the classic first 500 of a DynamoDB-backed API.
    """

    def default(self, o: Any) -> Any:
        if isinstance(o, decimal.Decimal):
            # DynamoDB stores all numbers as Decimal. Integral values should not
            # render as "23.0" in the API response.
            return int(o) if o == o.to_integral_value() else float(o)
        if isinstance(o, (set, frozenset)):
            return sorted(o)
        if hasattr(o, "isoformat"):
            return o.isoformat()
        return super().default(o)


def json_encode(body: Any) -> str:
    return json.dumps(body, cls=_Encoder, ensure_ascii=False, separators=(",", ":"))


def _response(
    status: int,
    body: Any,
    *,
    cache_seconds: int = 0,
    extra_headers: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    headers = {
        "content-type": "application/json; charset=utf-8",
        **_CORS,
    }
    if cache_seconds > 0:
        headers["cache-control"] = f"public, max-age={cache_seconds}"
    else:
        headers["cache-control"] = "no-store"
    if extra_headers:
        headers.update({k.lower(): v for k, v in extra_headers.items()})

    return {"statusCode": status, "headers": headers, "body": json_encode(body)}


def ok(body: Any, *, cache_seconds: int = 0) -> dict[str, Any]:
    return _response(200, body, cache_seconds=cache_seconds)


def accepted(body: Any) -> dict[str, Any]:
    """202 — the work is queued, not done.

    ``create_complaint`` returns this: the AI draft and the send happen on the
    SQS worker, and the user should never wait on them.
    """
    return _response(202, body)


def error(status: int, code: str, message: str) -> dict[str, Any]:
    return _response(status, {"error": {"code": code, "message": message}})


def bad_request(code: str, message: str) -> dict[str, Any]:
    return error(400, code, message)


def not_found(code: str, message: str) -> dict[str, Any]:
    return error(404, code, message)


def server_error(code: str = "internal_error", message: str = "Something went wrong.") -> dict[str, Any]:
    return error(500, code, message)


class ApiError(Exception):
    """Raise from anywhere in a handler to return a specific HTTP error.

    Saves threading error returns back up through helper functions.
    """

    def __init__(self, status: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message

    def to_response(self) -> dict[str, Any]:
        return error(self.status, self.code, self.message)
