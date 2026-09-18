"""Tests for the SQS draft-and-send worker, Bedrock adapter and delivery."""

from __future__ import annotations

import json

import pytest

from common import bedrock as bedrock_mod
from common.bedrock import BedrockUnavailable, _extract_json, _validate
from common.config import DeliveryMode, load_config
from draft_and_send import app

CID = "CMP-01M2V3WRDT08DFMCJXVWRW9BKK"

HINDI = (
    "सेवा में, वार्ड कार्यालय। मैं इस वार्ड की एक सार्वजनिक सड़क पर बने गड्ढे की "
    "सूचना देना चाहता हूँ। कृपया मरम्मत करवाई जाए। भवदीय।"
)


def _complaint(**over):
    record = {
        "complaint_id": CID,
        "ward_id": "DEL-0042",
        "ward_name": "Sadar Bazar",
        "created_at": "2026-09-19T04:00:00+00:00",
        "status": "OPEN",
        "draft_status": "PENDING",
        "issue_type": "POTHOLE",
        "landmark": "the community park gate",
    }
    record.update(over)
    return record


def _event(*complaint_ids):
    return {
        "Records": [
            {"messageId": f"m{i}", "body": json.dumps({"complaint_id": cid})}
            for i, cid in enumerate(complaint_ids)
        ]
    }


@pytest.fixture
def worker(monkeypatch):
    """Stub every AWS edge; keep the real drafting logic."""
    state = {
        "complaint": _complaint(),
        "drafts": [],
        "deliveries": [],
        "metrics": [],
    }

    monkeypatch.setattr(
        app, "get_complaint",
        lambda cid, consistent=False: state["complaint"] if cid == CID else None,
    )
    monkeypatch.setattr(
        app, "update_complaint_draft",
        lambda cid, draft: state["drafts"].append((cid, draft)),
    )
    monkeypatch.setattr(
        app, "record_delivery",
        lambda cid, **kw: state["deliveries"].append({"id": cid, **kw}),
    )
    monkeypatch.setattr(app, "emit_drafted_metric", lambda source: state["metrics"].append(source))
    # Bedrock off by default: the composer path is the one that must always work.
    monkeypatch.setenv("BEDROCK_ENABLED", "false")
    load_config.cache_clear()
    return state


# ==========================================================================
# The worker always produces a letter
# ==========================================================================


def test_composer_path_drafts_and_delivers(worker):
    result = app.handler(_event(CID))

    assert result == {"batchItemFailures": []}
    cid, draft = worker["drafts"][0]
    assert cid == CID
    assert draft["source"] == "template"
    assert draft["body_en"].strip() and draft["body_hi"].strip()
    assert "Sadar Bazar" in draft["body_en"]
    assert worker["metrics"] == ["template"]


def test_bedrock_is_used_when_it_works(worker, monkeypatch):
    monkeypatch.setattr(
        app, "draft_with_bedrock",
        lambda *a, **kw: __import__('common.composer', fromlist=['Draft']).Draft(
            subject="AI subject", body_en="AI english body", body_hi=HINDI, source="bedrock"
        ),
    )
    app.handler(_event(CID))
    assert worker["drafts"][0][1]["source"] == "bedrock"
    assert worker["metrics"] == ["bedrock"]


@pytest.mark.parametrize(
    "boom",
    [
        BedrockUnavailable("no access"),
        RuntimeError("throttled"),
        KeyError("output"),
    ],
)
def test_every_bedrock_failure_falls_back_to_the_composer(worker, monkeypatch, boom):
    """Bedrock is optional by design; no failure of it may cost the user a draft."""
    def _raise(*a, **kw):
        raise boom

    monkeypatch.setattr(app, "draft_with_bedrock", _raise)
    result = app.handler(_event(CID))

    assert result == {"batchItemFailures": []}, "a model failure is not a retryable error"
    assert worker["drafts"][0][1]["source"] == "template"
    assert worker["drafts"][0][1]["body_hi"].strip()


def test_draft_is_saved_before_delivery_is_attempted(worker):
    """If SES then fails the user still has the letter, which is the product."""
    app.handler(_event(CID))
    assert worker["drafts"], "the draft must be written even if delivery fails"
    assert worker["deliveries"][0]["draft_status"] in ("DRAFTED", "SENT")


# ==========================================================================
# Idempotency and redelivery
# ==========================================================================


@pytest.mark.parametrize("already", ["DRAFTED", "SENT"])
def test_an_already_drafted_complaint_is_not_redrafted(worker, already):
    """SQS delivers at least once; a redelivery must not rewrite the letter."""
    worker["complaint"] = _complaint(draft_status=already)
    result = app.handler(_event(CID))

    assert result == {"batchItemFailures": []}
    assert worker["drafts"] == []
    assert worker["deliveries"] == []


def test_a_missing_complaint_is_dropped_not_retried(worker):
    """A strongly consistent read found nothing, so retrying only fills the DLQ."""
    result = app.handler(_event("CMP-DOESNOTEXIST"))
    assert result == {"batchItemFailures": []}
    assert worker["drafts"] == []


def test_the_worker_reads_consistently(worker, monkeypatch):
    """The worker can run within milliseconds of the write.

    An eventually consistent read would intermittently see nothing and treat a
    real complaint as missing.
    """
    seen = {}
    monkeypatch.setattr(
        app, "get_complaint",
        lambda cid, consistent=False: seen.update(consistent=consistent) or _complaint(),
    )
    app.handler(_event(CID))
    assert seen["consistent"] is True


# ==========================================================================
# Batch handling
# ==========================================================================


def test_only_the_failing_record_is_returned_for_retry(worker, monkeypatch):
    calls = {"n": 0}

    def _sometimes(cid, draft):
        calls["n"] += 1
        if calls["n"] == 2:
            raise RuntimeError("dynamodb unavailable")

    monkeypatch.setattr(app, "update_complaint_draft", _sometimes)
    result = app.handler(_event(CID, CID, CID))

    assert result == {"batchItemFailures": [{"itemIdentifier": "m1"}]}, (
        "the other two records must not be redelivered and redrafted"
    )


@pytest.mark.parametrize(
    "body", ["{not json", json.dumps({}), json.dumps({"complaint_id": "  "})]
)
def test_malformed_messages_are_dropped_rather_than_retried(worker, body):
    """These can never succeed, so retrying them three times is pure waste."""
    result = app.handler({"Records": [{"messageId": "m0", "body": body}]})
    assert result == {"batchItemFailures": []}
    assert worker["drafts"] == []


def test_empty_event_is_handled():
    assert app.handler({}) == {"batchItemFailures": []}


# ==========================================================================
# Delivery — PRD §12
# ==========================================================================


def test_demo_outbox_is_the_default_and_sends_nothing(worker):
    app.handler(_event(CID))
    delivery = worker["deliveries"][0]
    assert delivery["delivery_mode"] == DeliveryMode.DEMO_OUTBOX
    assert delivery["draft_status"] == "DRAFTED"
    assert "demo recipient" in delivery["recipient"]


def test_ses_live_is_refused_at_runtime(worker, monkeypatch):
    """Turning this on requires editing the source, which is the point."""
    monkeypatch.setenv("DELIVERY_MODE", "SES_LIVE")
    load_config.cache_clear()

    app.handler(_event(CID))
    delivery = worker["deliveries"][0]
    assert delivery["delivery_mode"] == DeliveryMode.DEMO_OUTBOX
    assert "disabled" in (delivery["note"] or "").lower()


def test_ses_verified_without_configuration_degrades_to_the_outbox(worker, monkeypatch):
    monkeypatch.setenv("DELIVERY_MODE", "SES_VERIFIED")
    monkeypatch.setenv("SES_SENDER", "")
    load_config.cache_clear()

    app.handler(_event(CID))
    assert worker["deliveries"][0]["delivery_mode"] == DeliveryMode.DEMO_OUTBOX


def test_the_recipient_line_never_looks_like_a_real_official(worker):
    app.handler(_event(CID))
    recipient = worker["deliveries"][0]["recipient"]
    assert "@" not in recipient
    assert "demo" in recipient.lower()


# ==========================================================================
# Bedrock reply parsing
# ==========================================================================


def test_json_in_a_markdown_fence_is_parsed():
    parsed = _extract_json('```json\n{"subject":"s","body_en":"e","body_hi":"h"}\n```')
    assert parsed["subject"] == "s"


def test_json_with_surrounding_prose_is_recovered():
    parsed = _extract_json('Sure! {"subject":"s","body_en":"e","body_hi":"h"} Hope that helps.')
    assert parsed["body_en"] == "e"


@pytest.mark.parametrize("reply", ["not json at all", "", "[1,2,3]"])
def test_unparseable_replies_raise_so_the_caller_falls_back(reply):
    with pytest.raises(BedrockUnavailable):
        _validate(_extract_json(reply))


@pytest.mark.parametrize(
    "payload",
    [
        {"subject": "s", "body_en": "e"},
        {"subject": "", "body_en": "e", "body_hi": HINDI},
        {"subject": "s", "body_en": "  ", "body_hi": HINDI},
    ],
)
def test_incomplete_replies_are_rejected(payload):
    """A half-filled draft is worse than the composer's complete one."""
    with pytest.raises(BedrockUnavailable):
        _validate(payload)


def test_english_in_the_hindi_field_is_rejected():
    """The bilingual claim is a real feature, not decoration."""
    with pytest.raises(BedrockUnavailable):
        _validate({"subject": "s", "body_en": "english", "body_hi": "also english text here"})


def test_a_real_hindi_reply_is_accepted():
    draft = _validate({"subject": "s", "body_en": "english body", "body_hi": HINDI})
    assert draft.source == "bedrock"


def test_bedrock_is_skipped_entirely_when_disabled(monkeypatch):
    monkeypatch.setenv("BEDROCK_ENABLED", "false")
    load_config.cache_clear()
    with pytest.raises(BedrockUnavailable):
        bedrock_mod.draft_with_bedrock("POTHOLE", "Sadar Bazar")


def test_bedrock_is_skipped_when_no_profile_id_is_configured(monkeypatch):
    """Never hardcode a model id — no id means no Bedrock."""
    monkeypatch.setenv("BEDROCK_ENABLED", "true")
    monkeypatch.setenv("BEDROCK_INFERENCE_PROFILE_ID", "")
    load_config.cache_clear()
    with pytest.raises(BedrockUnavailable):
        bedrock_mod.draft_with_bedrock("POTHOLE", "Sadar Bazar")


def test_the_system_prompt_forbids_the_things_that_matter():
    prompt = bedrock_mod.SYSTEM_PROMPT.lower()
    assert "never name or address an individual" in prompt
    assert "never threaten legal action" in prompt
    assert "do not invent facts" in prompt
