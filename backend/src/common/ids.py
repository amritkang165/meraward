"""Identifier generation.

ULIDs rather than UUIDs for complaint ids: the leading 48 bits are a millisecond
timestamp, so ids sort chronologically as plain strings. That makes a complaint
id useful in a sort key and readable in a log, and it costs nothing.

Implemented here rather than pulled from PyPI so the Lambda has one fewer
dependency to get right on a cold start.
"""

from __future__ import annotations

import os
import secrets
import time
import uuid
from typing import Final

__all__ = ["complaint_id", "new_ulid", "status_token", "ulid_timestamp_ms"]

# Crockford base32: no I, L, O or U, so ids survive being read aloud or
# transcribed from a screenshot.
_ALPHABET: Final[str] = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
_ENCODE_LEN: Final[int] = 26
_TIME_LEN: Final[int] = 10


def _encode(value: int, length: int) -> str:
    out = []
    for _ in range(length):
        value, rem = divmod(value, 32)
        out.append(_ALPHABET[rem])
    return "".join(reversed(out))


def new_ulid(timestamp_ms: int | None = None) -> str:
    """Generate a 26-character, lexicographically sortable ULID."""
    ts = int(time.time() * 1000) if timestamp_ms is None else int(timestamp_ms)
    if ts < 0:
        raise ValueError("timestamp must not be negative")
    randomness = int.from_bytes(os.urandom(10), "big")
    return _encode(ts, _TIME_LEN) + _encode(randomness, _ENCODE_LEN - _TIME_LEN)


def ulid_timestamp_ms(value: str) -> int:
    """Recover the millisecond timestamp encoded in a ULID's first 10 chars."""
    head = value.strip().upper()[:_TIME_LEN]
    if len(head) != _TIME_LEN:
        raise ValueError("not a ULID")
    total = 0
    for ch in head:
        index = _ALPHABET.find(ch)
        if index < 0:
            raise ValueError(f"invalid ULID character: {ch!r}")
        total = total * 32 + index
    return total


def complaint_id(timestamp_ms: int | None = None) -> str:
    """``CMP-<ulid>`` — prefixed so it is self-describing in a log line."""
    return f"CMP-{new_ulid(timestamp_ms)}"


def status_token() -> str:
    """Unguessable token for the magic-link status update.

    A plain random UUID, not an HMAC: the token is stored on the complaint row
    and compared directly, so there is no key to manage and nothing to get
    subtly wrong. The PRD's data model and API spec disagreed on this; the row
    is the source of truth, so it is a UUID.
    """
    return str(uuid.UUID(bytes=secrets.token_bytes(16), version=4))
