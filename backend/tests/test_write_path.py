"""Tests for presign_upload, create_complaint and health.

The write path has no authorizer, so these tests carry more weight than usual:
validation here is the only thing between the internet and the tables.
"""

from __future__ import annotations

import json
from decimal import Decimal

import pytest

from common.validation import validate_email, validate_photo_key, validate_text
from create_complaint import app as create_app
from health import app as health_app
from presign_upload import app as presign_app

VALID_KEY = "photos/2026/09/19/01K5ABCDEFGHJKMNPQRSTVWXYZ.jpg"


def _event(body, **extra):
    return {"body": json.dumps(body) if not isinstance(body, str) else body, **extra}


def _body(response):
    return json.loads(response["body"])


# ==========================================================================
# presign_upload
# ==========================================================================


@pytest.fixture
def presigned(monkeypatch):
    """Capture the params handed to S3 without calling AWS."""
    captured = {}

    class _S3:
        def generate_presigned_url(self, op, Params, ExpiresIn):  # noqa: N803
            captured.update(op=op, params=Params, expires=ExpiresIn)
            return "https://s3.example/signed"

    monkeypatch.setenv("PHOTOS_BUCKET", "meraward-photos-test")
    monkeypatch.setattr(presign_app, "s3_client", lambda: _S3())
    return captured


def test_presign_returns_a_url_and_a_key(presigned):
    res = presign_app.handler(_event({"content_type": "image/jpeg", "content_length": 500_000}))
    assert res["statusCode"] == 200
    body = _body(res)
    assert body["upload_url"] == "https://s3.example/signed"
    assert validate_photo_key(body["photo_key"]) == body["photo_key"]
    assert body["expires_in"] == presign_app.URL_TTL_SECONDS


def test_presigned_url_binds_content_type_and_length(presigned):
    """Both must be in the signature.

    Without ContentLength bound, a presigned PUT accepts an object of any size
    and the 8 MB cap is decorative.
    """
    presign_app.handler(_event({"content_type": "image/png", "content_length": 1_234_567}))
    assert presigned["params"]["ContentType"] == "image/png"
    assert presigned["params"]["ContentLength"] == 1_234_567
    assert presigned["params"]["Bucket"] == "meraward-photos-test"


def test_heic_is_accepted(presigned):
    """iOS defaults to HEIC; rejecting it would break reporting on half of phones."""
    res = presign_app.handler(_event({"content_type": "image/heic", "content_length": 900_000}))
    assert res["statusCode"] == 200
    assert _body(res)["photo_key"].endswith(".heic")


@pytest.mark.parametrize(
    "body,status,code",
    [
        ({"content_length": 1000}, 400, "missing_content_type"),
        ({"content_type": "application/pdf", "content_length": 5000}, 400, "unsupported_photo_type"),
        ({"content_type": "text/html", "content_length": 5000}, 400, "unsupported_photo_type"),
        ({"content_type": "image/jpeg"}, 400, "missing_content_length"),
        ({"content_type": "image/jpeg", "content_length": "big"}, 400, "invalid_content_length"),
        ({"content_type": "image/jpeg", "content_length": 10}, 400, "photo_too_small"),
        ({"content_type": "image/jpeg", "content_length": 99_000_000}, 413, "photo_too_large"),
    ],
)
def test_presign_rejects_bad_requests(presigned, body, status, code):
    res = presign_app.handler(_event(body))
    assert res["statusCode"] == status
    assert _body(res)["error"]["code"] == code


def test_presign_handles_malformed_json(presigned):
    res = presign_app.handler({"body": "{not json"})
    assert res["statusCode"] == 400
    assert _body(res)["error"]["code"] == "invalid_json"


def test_presign_content_type_with_charset_suffix(presigned):
    res = presign_app.handler(
        _event({"content_type": "image/jpeg; charset=binary", "content_length": 5000})
    )
    assert res["statusCode"] == 200


def test_presign_fails_cleanly_without_a_bucket(monkeypatch):
    monkeypatch.setenv("PHOTOS_BUCKET", "")
    res = presign_app.handler(_event({"content_type": "image/jpeg", "content_length": 5000}))
    assert res["statusCode"] == 500
    assert _body(res)["error"]["code"] == "upload_unavailable"


# ==========================================================================
# create_complaint
# ==========================================================================


@pytest.fixture
def created(monkeypatch, wards_file):
    """Capture the DynamoDB write and the SQS send."""
    state = {"items": [], "messages": [], "updates": []}

    monkeypatch.setattr(create_app, "put_complaint", lambda item: state["items"].append(item))
    monkeypatch.setattr(
        create_app,
        "update_complaint_draft",
        lambda cid, draft: state["updates"].append((cid, draft)),
    )

    class _SQS:
        def send_message(self, QueueUrl, MessageBody):  # noqa: N803
            state["messages"].append(json.loads(MessageBody))

    monkeypatch.setenv("DRAFT_QUEUE_URL", "https://sqs.example/q")
    monkeypatch.setattr(create_app, "sqs_client", lambda: _SQS())
    return state


def _valid_complaint(**over):
    payload = {
        "photo_key": VALID_KEY,
        "issue_type": "POTHOLE",
        "lat": 28.05,
        "lng": 77.05,
    }
    payload.update(over)
    return payload


def test_create_returns_202_with_a_tracking_token(created):
    res = create_app.handler(_event(_valid_complaint()))
    assert res["statusCode"] == 202
    body = _body(res)
    assert body["complaint_id"].startswith("CMP-")
    assert body["status"] == "OPEN"
    assert body["draft_status"] == "PENDING"
    assert body["queued"] is True
    assert body["ward"]["ward_id"] == "DEL-0001"
    assert body["tracking_url"] == f"/c/{body['complaint_id']}"
    assert len(body["status_token"]) == 36


def test_create_writes_the_row_before_enqueuing(created):
    """The other order races: the worker can find no row to draft against."""
    create_app.handler(_event(_valid_complaint()))
    assert len(created["items"]) == 1
    assert len(created["messages"]) == 1
    assert created["messages"][0]["complaint_id"] == created["items"][0]["complaint_id"]


def test_stored_row_has_the_documented_shape(created):
    create_app.handler(_event(_valid_complaint(reporter_email="A@Example.COM ", landmark="  by the park  ")))
    item = created["items"][0]
    assert item["status"] == "OPEN"
    assert item["draft_status"] == "PENDING"
    assert item["ward_id"] == "DEL-0001"
    assert isinstance(item["lat"], Decimal)
    assert item["reporter_email"] == "a@example.com", "email should be normalised"
    assert item["landmark"] == "by the park"


def test_real_reports_are_never_marked_demo(created):
    """`is_demo` distinguishes seeded rows from citizen reports. Never omit it."""
    create_app.handler(_event(_valid_complaint()))
    assert created["items"][0]["is_demo"] is False


def test_unknown_issue_type_becomes_other_rather_than_failing(created):
    res = create_app.handler(_event(_valid_complaint(issue_type="BANANA")))
    assert res["statusCode"] == 202
    assert created["items"][0]["issue_type"] == "OTHER"


def test_optional_fields_are_omitted_when_absent(created):
    create_app.handler(_event(_valid_complaint()))
    item = created["items"][0]
    assert "reporter_email" not in item
    assert "landmark" not in item


# ------------------------------------------------- the queue-down failure mode

def test_queue_failure_still_produces_a_complete_complaint(created, monkeypatch):
    """SQS being down must not cost the user their draft.

    This is what the deterministic composer was written first for.
    """
    class _Broken:
        def send_message(self, **_):
            raise RuntimeError("sqs unavailable")

    monkeypatch.setattr(create_app, "sqs_client", lambda: _Broken())
    res = create_app.handler(_event(_valid_complaint()))

    assert res["statusCode"] == 202
    body = _body(res)
    assert body["queued"] is False
    assert body["draft_status"] == "DRAFTED"

    cid, draft = created["updates"][0]
    assert cid == body["complaint_id"]
    assert draft["body_en"].strip() and draft["body_hi"].strip()
    assert cid in draft["body_en"], "the reference number should appear in the letter"


def test_unconfigured_queue_drafts_inline(created, monkeypatch):
    monkeypatch.setenv("DRAFT_QUEUE_URL", "")
    res = create_app.handler(_event(_valid_complaint()))
    assert _body(res)["draft_status"] == "DRAFTED"


def test_inline_draft_write_failure_degrades_to_pending(created, monkeypatch):
    class _Broken:
        def send_message(self, **_):
            raise RuntimeError("sqs down")

    def _boom(cid, draft):
        raise RuntimeError("dynamo down")

    monkeypatch.setattr(create_app, "sqs_client", lambda: _Broken())
    monkeypatch.setattr(create_app, "update_complaint_draft", _boom)

    res = create_app.handler(_event(_valid_complaint()))
    assert res["statusCode"] == 202, "the complaint is saved; only the draft is missing"
    assert _body(res)["draft_status"] == "PENDING"


# ------------------------------------------------------------------ validation

@pytest.mark.parametrize(
    "over,code",
    [
        ({"photo_key": ""}, "empty_complaint"),  # no photo AND no description
        ({"photo_key": "../../etc/passwd"}, "invalid_photo_key"),
        ({"photo_key": "photos/2026/09/19/evil.jpg"}, "invalid_photo_key"),
        ({"photo_key": "other-prefix/2026/09/19/01K5ABCDEFGHJKMNPQRSTVWXYZ.jpg"}, "invalid_photo_key"),
        ({"lat": None}, "missing_coordinate"),
        ({"lat": "abc"}, "invalid_coordinate"),
        ({"lat": 91}, "coordinate_out_of_range"),
        ({"reporter_email": "not-an-email"}, "invalid_email"),
        ({"landmark": "x" * 500}, "text_too_long"),
    ],
)
def test_create_rejects_bad_input(created, over, code):
    res = create_app.handler(_event(_valid_complaint(**over)))
    assert res["statusCode"] == 400
    assert _body(res)["error"]["code"] == code


def test_nothing_is_written_when_validation_fails(created):
    create_app.handler(_event(_valid_complaint(photo_key="nope")))
    assert created["items"] == []
    assert created["messages"] == []


def test_location_outside_coverage_is_404(created):
    res = create_app.handler(_event(_valid_complaint(lat=19.07, lng=72.87)))
    assert res["statusCode"] == 404
    assert _body(res)["error"]["code"] == "outside_coverage"
    assert created["items"] == []


def test_missing_body_is_400(created):
    assert create_app.handler({})["statusCode"] == 400


def test_dynamodb_failure_is_500_not_a_silent_202(created, monkeypatch):
    def _boom(item):
        raise RuntimeError("table missing")

    monkeypatch.setattr(create_app, "put_complaint", _boom)
    res = create_app.handler(_event(_valid_complaint()))
    assert res["statusCode"] == 500


# ---------------------------------------------------------- validator units

def test_photo_key_pattern_rejects_traversal_and_wrong_extensions():
    for bad in [
        "photos/2026/09/19/01K5ABCDEFGHJKMNPQRSTVWXYZ.exe",
        "photos/2026/09/19/01K5ABCDEFGHJKMNPQRSTVWXYZ.jpg/../x",
        "photos/26/9/19/01K5ABCDEFGHJKMNPQRSTVWXYZ.jpg",
        "photos/2026/09/19/SHORT.jpg",
    ]:
        with pytest.raises(Exception):
            validate_photo_key(bad)


def test_email_is_optional_but_validated():
    assert validate_email(None) is None
    assert validate_email("  ") is None
    assert validate_email("Person@Example.com") == "person@example.com"


def test_control_characters_are_stripped_from_free_text():
    assert validate_text("a\x00b\x07c", "landmark", max_length=50) == "abc"


# ==========================================================================
# health
# ==========================================================================


def test_health_reports_ok_when_the_ward_index_loads(wards_file):
    body = _body(health_app.handler({}))
    assert body["status"] == "ok"
    assert body["ward_index"] == {"loaded": True, "wards": 2}


def test_health_reports_degraded_when_geometry_is_missing(monkeypatch):
    from common.wards import reset_index

    monkeypatch.delenv("WARDS_GEOJSON_PATH", raising=False)
    monkeypatch.setenv("DATA_BUCKET", "")
    reset_index()
    body = _body(health_app.handler({}))
    assert body["status"] == "degraded"
    assert body["ward_index"]["loaded"] is False
    reset_index()


def test_health_reports_the_drafting_path(wards_file, monkeypatch):
    """Bedrock is optional, so "template" is a healthy answer, not an error."""
    assert _body(health_app.handler({}))["drafting"]["mode"] == "template"

    monkeypatch.setenv("BEDROCK_ENABLED", "true")
    monkeypatch.setenv("BEDROCK_INFERENCE_PROFILE_ID", "global.anthropic.some-profile")
    from common.config import load_config

    load_config.cache_clear()
    assert _body(health_app.handler({}))["drafting"]["mode"] == "bedrock"


def test_health_leaks_no_infrastructure_details(wards_file, monkeypatch):
    """This endpoint is public."""
    monkeypatch.setenv("DRAFT_QUEUE_URL", "https://sqs.ap-south-1.amazonaws.com/123/secret-q")
    monkeypatch.setenv("PHOTOS_BUCKET", "meraward-photos-123456789")
    from common.config import load_config

    load_config.cache_clear()
    raw = health_app.handler({})["body"]
    assert "secret-q" not in raw
    assert "123456789" not in raw


# ==========================================================================
# Three ways in: photo, description, or both
# ==========================================================================


def test_a_description_only_complaint_is_accepted(created):
    """Spoken and written reports have no photograph.

    Requiring one would make two of the three reporting routes impossible.
    """
    res = create_app.handler(
        _event({
            "issue_type": "GARBAGE",
            "lat": 28.05,
            "lng": 77.05,
            "description": "The bins outside the school have not been emptied for nine days.",
        })
    )
    assert res["statusCode"] == 202
    item = created["items"][0]
    assert "photo_key" not in item, "no photo was sent, so none should be stored"
    assert item["description"].startswith("The bins outside the school")


def test_a_complaint_with_neither_photo_nor_description_is_rejected(created):
    """Evidence or words. Neither is not a report."""
    res = create_app.handler(_event({"issue_type": "OTHER", "lat": 28.05, "lng": 77.05}))
    assert res["statusCode"] == 400
    assert _body(res)["error"]["code"] == "empty_complaint"
    assert created["items"] == []


def test_photo_and_description_together_are_both_kept(created):
    res = create_app.handler(
        _event(_valid_complaint(description="Deep pothole right at the crossing."))
    )
    assert res["statusCode"] == 202
    item = created["items"][0]
    assert item["photo_key"] == VALID_KEY
    assert item["description"] == "Deep pothole right at the crossing."


def test_an_overlong_description_is_rejected(created):
    res = create_app.handler(_event(_valid_complaint(description="x" * 2500)))
    assert res["statusCode"] == 400
    assert _body(res)["error"]["code"] == "text_too_long"


def test_the_letter_quotes_the_reporters_own_words(created, monkeypatch):
    """Their testimony is the part of the letter that is actually theirs."""
    class _Broken:
        def send_message(self, **_):
            raise RuntimeError("sqs down")

    monkeypatch.setattr(create_app, "sqs_client", lambda: _Broken())
    said = "Water has been standing outside the clinic since Tuesday."
    create_app.handler(_event(_valid_complaint(description=said)))

    _, draft = created["updates"][0]
    assert said in draft["body_en"]
    assert said in draft["body_hi"], (
        "the description is quoted verbatim in both languages - inventing a "
        "translation of someone's own testimony would put words in their mouth"
    )


def test_the_letter_only_claims_a_photograph_when_there_is_one(created, monkeypatch):
    class _Broken:
        def send_message(self, **_):
            raise RuntimeError("sqs down")

    monkeypatch.setattr(create_app, "sqs_client", lambda: _Broken())

    create_app.handler(_event({
        "issue_type": "WATER", "lat": 28.05, "lng": 77.05,
        "description": "Drain blocked.",
    }))
    _, no_photo = created["updates"][0]
    assert "photograph" not in no_photo["body_en"]

    created["updates"].clear()
    create_app.handler(_event(_valid_complaint()))
    _, with_photo = created["updates"][0]
    assert "photograph" in with_photo["body_en"]
