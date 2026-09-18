"""Delivering a drafted complaint.

The ethical constraint of this project lives here, so it is worth stating plainly:

**We never send to a real official's address.**

Unsolicited, AI-drafted mail sent to named public servants, generated partly from
demonstration data by a weekend project, is spam regardless of intent. Three modes
exist:

``DEMO_OUTBOX``
    The default. Nothing is sent. The complaint is rendered in a visible in-app
    ward outbox showing exactly what *would* go out.

``SES_VERIFIED``
    A real SES send to a verified demo inbox we control. The integration is
    genuinely real and the recipient line says so.

``SES_LIVE``
    Exists so the code path is reviewable, and is refused at runtime. Turning it
    on requires editing this file, which is the point.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from .config import DeliveryMode, load_config

log = logging.getLogger(__name__)

__all__ = ["DeliveryResult", "deliver"]

#: What the recipient line reads in the outbox and in the email itself. It never
#: resolves to a real councillor's address.
DEMO_RECIPIENT_LABEL = "Ward {ward} Office (demo recipient)"


@dataclass(frozen=True)
class DeliveryResult:
    mode: str
    sent: bool
    recipient: str
    message_id: str | None = None
    note: str | None = None


def _recipient_label(ward_name: str, ward_id: str | None) -> str:
    return DEMO_RECIPIENT_LABEL.format(ward=ward_id or ward_name or "office")


def deliver(
    *,
    subject: str,
    body_en: str,
    body_hi: str,
    ward_name: str,
    ward_id: str | None = None,
) -> DeliveryResult:
    """Deliver a drafted complaint according to the configured mode.

    Never raises: a delivery failure must not lose the draft, which is already
    saved and visible. The result records what actually happened.
    """
    cfg = load_config()
    recipient_label = _recipient_label(ward_name, ward_id)

    if cfg.delivery_mode == DeliveryMode.SES_LIVE:
        # Deliberate and permanent. See the module docstring.
        log.error("SES_LIVE requested and refused; falling back to the demo outbox")
        return DeliveryResult(
            mode=DeliveryMode.DEMO_OUTBOX,
            sent=False,
            recipient=recipient_label,
            note="Live sending to real officials is disabled in this deployment.",
        )

    if cfg.delivery_mode == DeliveryMode.DEMO_OUTBOX:
        return DeliveryResult(
            mode=DeliveryMode.DEMO_OUTBOX,
            sent=False,
            recipient=recipient_label,
            note="Queued to the ward outbox. Nothing was emailed.",
        )

    # SES_VERIFIED — a real send, to an inbox we own.
    if not cfg.ses_sender or not cfg.ses_demo_recipient:
        log.warning("SES_VERIFIED requested but sender/recipient are unset")
        return DeliveryResult(
            mode=DeliveryMode.DEMO_OUTBOX,
            sent=False,
            recipient=recipient_label,
            note="SES is not configured; queued to the ward outbox instead.",
        )

    body = (
        f"{body_en}\n\n"
        f"{'-' * 60}\n\n"
        f"{body_hi}\n\n"
        f"{'-' * 60}\n"
        f"Intended recipient: {recipient_label}\n"
        "Sent by MERAWARD, a civic reporting demonstration. This message was "
        "delivered to a demo inbox, not to a public official.\n"
    )

    try:
        import boto3

        response = boto3.client("ses", region_name=cfg.region).send_email(
            Source=cfg.ses_sender,
            Destination={"ToAddresses": [cfg.ses_demo_recipient]},
            Message={
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": {"Text": {"Data": body, "Charset": "UTF-8"}},
            },
        )
        return DeliveryResult(
            mode=DeliveryMode.SES_VERIFIED,
            sent=True,
            recipient=cfg.ses_demo_recipient,
            message_id=response.get("MessageId"),
        )
    except Exception as exc:  # noqa: BLE001
        # Sandbox rejection, unverified identity, throttling: the draft stands.
        log.exception("SES send failed")
        return DeliveryResult(
            mode=DeliveryMode.DEMO_OUTBOX,
            sent=False,
            recipient=recipient_label,
            note=f"Email delivery failed ({type(exc).__name__}); the draft is saved.",
        )


def emit_drafted_metric(source: str) -> None:
    """One CloudWatch datapoint per drafted complaint.

    Cheap, and it is the thing that ticks upward on camera while the demo runs.
    Never raises: telemetry must not break delivery.
    """
    try:
        import boto3

        boto3.client("cloudwatch", region_name=load_config().region).put_metric_data(
            Namespace="MERAWARD",
            MetricData=[
                {
                    "MetricName": "ComplaintsDrafted",
                    "Value": 1,
                    "Unit": "Count",
                    "Dimensions": [{"Name": "Source", "Value": source}],
                }
            ],
        )
    except Exception:  # noqa: BLE001
        log.debug("could not emit ComplaintsDrafted metric", exc_info=True)
