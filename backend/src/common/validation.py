"""Input validation for the write path.

The write path has no authorizer, by design: one-tap reporting *is* the product,
and a signup wall contradicts the pitch. That makes validation here the only
thing between the internet and our tables, so it is strict about shape and
generous about nothing.
"""

from __future__ import annotations

import re
from typing import Any, Final

from .responses import ApiError

__all__ = [
    "ALLOWED_PHOTO_TYPES",
    "PHOTO_KEY_PATTERN",
    "extension_for",
    "require_coords",
    "validate_content_type",
    "validate_email",
    "validate_photo_key",
    "validate_text",
]

#: What a phone camera actually produces. HEIC is included because iOS defaults
#: to it and rejecting it would silently break reporting on half of all phones.
ALLOWED_PHOTO_TYPES: Final[dict[str, str]] = {
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/heic": "heic",
    "image/heif": "heif",
}

#: Keys we issue, and therefore the only keys we accept back.
#: photos/YYYY/MM/DD/<26-char ULID>.<ext>
PHOTO_KEY_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^photos/\d{4}/\d{2}/\d{2}/[0-9A-HJKMNP-TV-Z]{26}\.(jpg|png|webp|heic|heif)$"
)

# Deliberately permissive: the only thing we do with a reporter's address is send
# them their own tracking link, so a strict RFC-5322 parser would reject real
# addresses for no benefit.
_EMAIL_PATTERN: Final[re.Pattern[str]] = re.compile(r"^[^@\s]+@[^@\s.]+\.[^@\s]+$")


def validate_content_type(raw: Any) -> str:
    value = str(raw or "").strip().lower().split(";")[0]
    if not value:
        raise ApiError(400, "missing_content_type", "content_type is required.")
    if value not in ALLOWED_PHOTO_TYPES:
        allowed = ", ".join(sorted(set(ALLOWED_PHOTO_TYPES)))
        raise ApiError(
            400, "unsupported_photo_type", f"Photo must be one of: {allowed}."
        )
    return value


def extension_for(content_type: str) -> str:
    return ALLOWED_PHOTO_TYPES[content_type]


def validate_photo_key(raw: Any) -> str:
    """Accept only keys matching the shape we issue.

    Without this, an unauthenticated caller could attach an arbitrary object in
    the bucket to a complaint, or point a complaint at a key that does not exist.
    """
    value = str(raw or "").strip()
    if not value:
        raise ApiError(400, "missing_photo_key", "photo_key is required.")
    if not PHOTO_KEY_PATTERN.match(value):
        raise ApiError(400, "invalid_photo_key", "photo_key is not a key we issued.")
    return value


def validate_email(raw: Any) -> str | None:
    """Optional. Used only to send the reporter their own tracking link."""
    value = str(raw or "").strip().lower()
    if not value:
        return None
    if len(value) > 254 or not _EMAIL_PATTERN.match(value):
        raise ApiError(400, "invalid_email", "reporter_email is not a valid address.")
    return value


def validate_text(raw: Any, field: str, *, max_length: int) -> str | None:
    """Free text from an unauthenticated caller: length-capped and stripped."""
    value = str(raw or "").strip()
    if not value:
        return None
    if len(value) > max_length:
        raise ApiError(
            400, "text_too_long", f"{field} must be {max_length} characters or fewer."
        )
    # Control characters have no business in a complaint letter and would render
    # badly in an email body.
    return "".join(ch for ch in value if ch == "\n" or ch >= " ")


def require_coords(payload: dict[str, Any]) -> tuple[float, float]:
    def _one(key: str, limit: float) -> float:
        if key not in payload or payload[key] is None or payload[key] == "":
            raise ApiError(400, "missing_coordinate", f"{key} is required.")
        try:
            value = float(payload[key])
        except (TypeError, ValueError):
            raise ApiError(400, "invalid_coordinate", f"{key} must be a number.") from None
        if value != value or value in (float("inf"), float("-inf")):
            raise ApiError(400, "invalid_coordinate", f"{key} must be a real number.")
        if not -limit <= value <= limit:
            raise ApiError(
                400,
                "coordinate_out_of_range",
                f"{key} must be between -{limit} and {limit}.",
            )
        return value

    return _one("lat", 90.0), _one("lng", 180.0)
