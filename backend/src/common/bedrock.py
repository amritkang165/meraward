"""Bedrock drafting — a strict upgrade over the template composer, never a dependency.

Everything here is written so that failure is ordinary. If model access was never
granted, if the profile id is wrong, if the model returns prose instead of JSON,
or if the call times out, the caller falls back to
:func:`common.composer.compose` and the user still gets a complete bilingual
letter. The organisers confirmed on 2026-09-18 that Bedrock is not mandatory;
only deploying on AWS is.

The model id is **never hardcoded**. Current Claude models are not served
regionally from ``ap-south-1``; access goes through a global cross-region
inference profile whose id is discovered at deploy time and injected as
``BEDROCK_INFERENCE_PROFILE_ID``.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from .composer import Draft, normalise_issue_type
from .config import load_config

log = logging.getLogger(__name__)

__all__ = ["BedrockUnavailable", "draft_with_bedrock"]

MAX_TOKENS = 1600
TEMPERATURE = 0.3

#: The editorial rules are in the prompt *and* enforced by tests on the output.
#: A prompt is a request, not a guarantee.
SYSTEM_PROMPT = """You draft civic complaint letters for residents of Delhi.

Write a formal, respectful, first-person complaint from a resident to their ward
office. Reference the ward by name and describe the issue type concretely.

Hard rules:
- Address the WARD OFFICE as an institution. Never name or address an individual.
- Never accuse anyone of negligence, corruption or incompetence.
- Never threaten legal action, escalation, media, or any consequence.
- Do not invent facts: no dates, measurements, injuries, case numbers or
  counts that were not given to you.
- Keep each letter to three or four short paragraphs.

Return ONLY a JSON object, with no markdown fence and no commentary:
{"subject": "...", "body_en": "...", "body_hi": "..."}

"body_en" is the letter in English. "body_hi" is the SAME letter in formal Hindi
(Devanagari) - a real translation, not a transliteration, and not English text
with a Hindi heading."""


class BedrockUnavailable(RuntimeError):
    """Bedrock could not produce a usable draft. The caller should fall back."""


def _user_prompt(
    issue_type: str,
    ward_name: str,
    *,
    ward_id: str | None,
    reported_on: str | None,
    landmark: str | None,
    reference: str | None,
) -> str:
    lines = [
        f"Issue type: {issue_type}",
        f"Ward: {ward_name}" + (f" (Ward {ward_id})" if ward_id else ""),
    ]
    if reported_on:
        lines.append(f"Reported on: {reported_on}")
    if landmark:
        lines.append(f"Nearest landmark: {landmark}")
    if reference:
        lines.append(f"Reference number: {reference}")
    lines.append(
        "\nA photograph and location coordinates accompany this report. "
        "Write the complaint."
    )
    return "\n".join(lines)


def _extract_json(text: str) -> dict[str, Any]:
    """Parse the model's reply into a dict.

    Models wrap JSON in markdown fences often enough that handling it is
    cheaper than retrying. Anything still unparseable raises, and the caller
    falls back to the composer.
    """
    cleaned = (text or "").strip()
    fenced = re.match(r"^```(?:json)?\s*(.*?)\s*```$", cleaned, re.S)
    if fenced:
        cleaned = fenced.group(1).strip()

    try:
        parsed = json.loads(cleaned)
    except ValueError:
        # Last resort: the first balanced-looking object in the reply.
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start == -1 or end <= start:
            raise BedrockUnavailable("model reply was not JSON") from None
        try:
            parsed = json.loads(cleaned[start : end + 1])
        except ValueError:
            raise BedrockUnavailable("model reply was not JSON") from None

    if not isinstance(parsed, dict):
        raise BedrockUnavailable("model reply was not a JSON object")
    return parsed


def _validate(parsed: dict[str, Any]) -> Draft:
    """Reject a reply that is missing a field or has an empty one.

    A half-filled draft is worse than no draft: the composer fallback produces a
    complete letter, so a partial model reply should never win over it.
    """
    subject = str(parsed.get("subject") or "").strip()
    body_en = str(parsed.get("body_en") or "").strip()
    body_hi = str(parsed.get("body_hi") or "").strip()

    if not subject or not body_en or not body_hi:
        raise BedrockUnavailable("model reply was missing a required field")

    devanagari = sum(1 for ch in body_hi if "ऀ" <= ch <= "ॿ")
    letters = sum(1 for ch in body_hi if ch.isalpha())
    if not letters or devanagari / letters < 0.5:
        # The bilingual claim is a real product feature, not decoration. English
        # text in the Hindi field is a failed draft, not a usable one.
        raise BedrockUnavailable("body_hi was not Hindi")

    return Draft(subject=subject, body_en=body_en, body_hi=body_hi, source="bedrock")


def draft_with_bedrock(
    issue_type: object,
    ward_name: str,
    *,
    ward_id: str | None = None,
    reported_on: str | None = None,
    landmark: str | None = None,
    reference: str | None = None,
) -> Draft:
    """Draft a complaint with Bedrock.

    Raises :class:`BedrockUnavailable` for every failure mode — not configured,
    access denied, throttled, timed out, or an unusable reply — so the caller
    has exactly one thing to catch.
    """
    cfg = load_config()
    if not cfg.use_bedrock:
        raise BedrockUnavailable("bedrock is not enabled or has no profile id")

    prompt = _user_prompt(
        normalise_issue_type(issue_type),
        (ward_name or "").strip() or "this ward",
        ward_id=ward_id,
        reported_on=reported_on,
        landmark=landmark,
        reference=reference,
    )

    try:
        import boto3

        client = boto3.client("bedrock-runtime", region_name=cfg.region)
        response = client.converse(
            modelId=cfg.bedrock_profile_id,
            system=[{"text": SYSTEM_PROMPT}],
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            inferenceConfig={"maxTokens": MAX_TOKENS, "temperature": TEMPERATURE},
        )
        text = response["output"]["message"]["content"][0]["text"]
    except BedrockUnavailable:
        raise
    except Exception as exc:  # noqa: BLE001 - every failure is the same failure here
        log.warning("bedrock call failed (%s); falling back", type(exc).__name__)
        raise BedrockUnavailable(str(exc)) from exc

    return _validate(_extract_json(text))
