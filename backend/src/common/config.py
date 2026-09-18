"""Environment configuration, read once per cold start.

Every knob the Lambdas need lives here so no handler reaches into ``os.environ``
directly. That matters most for the Bedrock model id: it is discovered at deploy
time and injected, never hardcoded, because current Claude models are not served
regionally from ``ap-south-1`` and the profile id is not knowable at write time.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Final

__all__ = ["Config", "DeliveryMode", "load_config"]


class DeliveryMode:
    """How a drafted complaint is delivered.

    ``SES_LIVE`` exists so the code path is real and reviewable, and is off. We
    do not put unsolicited AI-drafted mail in a public servant's inbox (PRD §12).
    """

    DEMO_OUTBOX: Final[str] = "DEMO_OUTBOX"
    SES_VERIFIED: Final[str] = "SES_VERIFIED"
    SES_LIVE: Final[str] = "SES_LIVE"

    ALL: Final[tuple[str, ...]] = (DEMO_OUTBOX, SES_VERIFIED, SES_LIVE)


def _env(name: str, default: str = "") -> str:
    return (os.environ.get(name) or default).strip()


def _env_int(name: str, default: int) -> int:
    try:
        return int(_env(name) or default)
    except ValueError:
        return default


def _env_bool(name: str, default: bool = False) -> bool:
    raw = _env(name).lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Config:
    region: str
    complaints_table: str
    wards_table: str
    ward_index_name: str
    status_index_name: str
    photos_bucket: str
    data_bucket: str
    wards_geojson_key: str
    draft_queue_url: str
    delivery_mode: str
    ses_sender: str
    ses_demo_recipient: str
    bedrock_profile_id: str
    bedrock_enabled: bool
    max_photo_bytes: int

    @property
    def use_bedrock(self) -> bool:
        """Bedrock is used only when explicitly enabled *and* given a profile id.

        Either half missing means the deterministic composer runs instead. This
        is the switch that keeps the product demoable without model access.
        """
        return self.bedrock_enabled and bool(self.bedrock_profile_id)


@lru_cache(maxsize=1)
def load_config() -> Config:
    """Read configuration from the environment. Cached for the container's life."""
    mode = _env("DELIVERY_MODE", DeliveryMode.DEMO_OUTBOX).upper()
    if mode not in DeliveryMode.ALL:
        mode = DeliveryMode.DEMO_OUTBOX

    return Config(
        region=_env("AWS_REGION", "ap-south-1"),
        complaints_table=_env("COMPLAINTS_TABLE", "MeraWardComplaints"),
        wards_table=_env("WARDS_TABLE", "MeraWardWards"),
        # GSI names are deployment configuration, not constants. A GSI cannot be
        # renamed in place - changing one means recreating the table - so the
        # code bends to the infrastructure here rather than the other way round.
        ward_index_name=_env("WARD_INDEX_NAME", "ward-created-index"),
        status_index_name=_env("STATUS_INDEX_NAME", "status-created-index"),
        photos_bucket=_env("PHOTOS_BUCKET"),
        data_bucket=_env("DATA_BUCKET"),
        wards_geojson_key=_env("WARDS_GEOJSON_KEY", "wards.geojson"),
        draft_queue_url=_env("DRAFT_QUEUE_URL"),
        delivery_mode=mode,
        ses_sender=_env("SES_SENDER"),
        ses_demo_recipient=_env("SES_DEMO_RECIPIENT"),
        bedrock_profile_id=_env("BEDROCK_INFERENCE_PROFILE_ID"),
        bedrock_enabled=_env_bool("BEDROCK_ENABLED", False),
        max_photo_bytes=_env_int("MAX_PHOTO_BYTES", 8 * 1024 * 1024),
    )
