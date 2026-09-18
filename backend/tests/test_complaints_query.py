"""Tests for complaints_query: detail, map markers and the leaderboard.

The complaint detail page is a deliberately shareable public URL, so the
redaction tests here are a security boundary rather than formatting checks.
"""

from __future__ import annotations

import json
from decimal import Decimal

import pytest

from common.views import (
    PRIVATE_COMPLAINT_FIELDS,
    UNPUBLISHED_BUT_EMBEDDED,
    map_marker,
    public_complaint,
    status_timeline,
)
from complaints_query import app


def _body(response):
    return json.loads(response["body"])


def _record(**over):
    record = {
        "complaint_id": "CMP-01M2V3WRDT08DFMCJXVWRW9BKK",
        "ward_id": "DEL-0001",
        "ward_name": "Westside",
        "created_at": "2026-09-19T04:00:00+00:00",
        "status": "OPEN",
        "draft_status": "DRAFTED",
        "draft_source": "template",
        "issue_type": "POTHOLE",
        "lat": Decimal("28.05"),
        "lng": Decimal("77.05"),
        "photo_key": "photos/2026/09/19/01K5ABCDEFGHJKMNPQRSTVWXYZ.jpg",
        "subject": "Pothole on a public road — Westside",
        "body_en": "To,\nThe Ward Office...",
        "body_hi": "सेवा में,\nवार्ड कार्यालय...",
        "is_demo": False,
        "delivery_mode": "DEMO_OUTBOX",
        # Private — must never be published.
        "status_token": "5f2b3c4d-0000-4000-8000-abcdefabcdef",
        "reporter_email": "someone@example.com",
        "ses_message_id": "0100018f-deadbeef",
    }
    record.update(over)
    return record


@pytest.fixture(autouse=True)
def _reset():
    app.reset_cache()
    yield
    app.reset_cache()


@pytest.fixture
def stubbed(monkeypatch, wards_file):
    state = {"complaints": [_record()], "wards": []}
    monkeypatch.setattr(
        app, "get_complaint",
        lambda cid: next((c for c in state["complaints"] if c["complaint_id"] == cid), None),
    )
    monkeypatch.setattr(
        app, "query_complaints",
        lambda **kw: [
            c for c in state["complaints"]
            if (not kw.get("status") or c["status"] == kw["status"])
            and (not kw.get("ward_id") or c["ward_id"] == kw["ward_id"])
        ],
    )
    monkeypatch.setattr(app, "scan_wards", lambda: state["wards"])
    monkeypatch.setattr(app, "photo_url", lambda key, **kw: f"https://s3.example/{key}?sig")
    return state


# ==========================================================================
# GET /complaints/{id} — redaction
# ==========================================================================


def test_detail_returns_the_complaint(stubbed):
    res = app.handler({"pathParameters": {"id": "CMP-01M2V3WRDT08DFMCJXVWRW9BKK"}})
    assert res["statusCode"] == 200
    body = _body(res)
    assert body["subject"].startswith("Pothole")
    assert body["body_hi"].startswith("सेवा में")
    assert body["ward"]["ward_name"] == "Westside"
    assert body["photo_url"].startswith("https://s3.example/")


@pytest.mark.parametrize("field", PRIVATE_COMPLAINT_FIELDS)
def test_secrets_never_reach_the_public_detail(stubbed, field):
    """The detail page is a shareable public URL.

    `status_token` is the magic link that changes the complaint's status —
    publishing it on the page it controls would make the lifecycle forgeable by
    anyone who opened the complaint. `reporter_email` belongs to a citizen who
    reported a problem on their own street.
    """
    raw = app.handler({"pathParameters": {"id": "CMP-01M2V3WRDT08DFMCJXVWRW9BKK"}})["body"]
    assert field not in raw, f"{field} was published as a field"
    assert _record()[field] not in raw, f"{field}'s value leaked into the response"


@pytest.mark.parametrize("field", UNPUBLISHED_BUT_EMBEDDED)
def test_photo_key_is_not_its_own_field_but_may_sit_inside_the_signed_url(stubbed, field):
    """The key is an opaque ULID path and is useless without the signature.

    It necessarily appears inside `photo_url` — that is what serving the photo
    means — so it is not a secret, but it is not published as a field either.
    """
    body = _body(app.handler({"pathParameters": {"id": "CMP-01M2V3WRDT08DFMCJXVWRW9BKK"}}))
    assert field not in body
    assert body["photo_url"]


def test_projection_is_an_allow_list_not_a_deny_list():
    """A field added to the table later must be private until named public."""
    out = public_complaint(_record(secret_new_column="leak me"))
    assert "secret_new_column" not in out
    assert "leak me" not in json.dumps(out, default=str)


def test_unknown_complaint_is_404(stubbed):
    res = app.handler({"pathParameters": {"id": "CMP-NOPE"}})
    assert res["statusCode"] == 404
    assert _body(res)["error"]["code"] == "complaint_not_found"


def test_detail_is_not_cached_because_the_ui_polls_it(stubbed):
    res = app.handler({"pathParameters": {"id": "CMP-01M2V3WRDT08DFMCJXVWRW9BKK"}})
    assert res["headers"]["cache-control"] == "no-store"


def test_demo_flag_is_always_present_and_boolean(stubbed):
    body = public_complaint({"complaint_id": "X"})
    assert body["is_demo"] is False
    assert public_complaint(_record(is_demo=True))["is_demo"] is True


# ---------------------------------------------------------------- timeline

def test_timeline_only_contains_steps_that_happened():
    steps = status_timeline(_record())
    assert [s["status"] for s in steps] == ["OPEN"]


def test_timeline_grows_with_the_lifecycle():
    record = _record(
        status="RESOLVED",
        acknowledged_at="2026-09-19T06:00:00+00:00",
        resolved_at="2026-09-19T09:00:00+00:00",
    )
    steps = status_timeline(record)
    assert [s["status"] for s in steps] == ["OPEN", "ACKNOWLEDGED", "RESOLVED"]
    assert all(s["at"] and s["label"] for s in steps)


# ==========================================================================
# GET /complaints — map markers
# ==========================================================================


def test_markers_are_lightweight(stubbed):
    """The letter bodies are the biggest attribute on the row.

    Sending them to render a dot would be hundreds of kilobytes for nothing.
    """
    marker = map_marker(_record())
    assert "body_en" not in marker and "body_hi" not in marker and "subject" not in marker
    assert set(marker) == {
        "complaint_id", "ward_id", "lat", "lng", "issue_type", "status",
        "created_at", "is_demo",
    }


def test_marker_without_coordinates_is_dropped():
    assert map_marker({"complaint_id": "X"}) is None


def test_list_returns_markers(stubbed):
    body = _body(app.handler({"rawPath": "/complaints"}))
    assert body["count"] == 1
    assert body["complaints"][0]["complaint_id"].startswith("CMP-")


def test_status_filter_is_validated(stubbed):
    res = app.handler({"rawPath": "/complaints", "queryStringParameters": {"status": "BANANA"}})
    assert res["statusCode"] == 400
    assert _body(res)["error"]["code"] == "invalid_status"


def test_status_filter_is_applied(stubbed):
    stubbed["complaints"].append(_record(complaint_id="CMP-B", status="RESOLVED"))
    body = _body(app.handler({"rawPath": "/complaints", "queryStringParameters": {"status": "resolved"}}))
    assert body["count"] == 1
    assert body["complaints"][0]["complaint_id"] == "CMP-B"


def test_issue_type_filter_is_applied(stubbed):
    stubbed["complaints"].append(_record(complaint_id="CMP-G", issue_type="GARBAGE"))
    body = _body(
        app.handler({"rawPath": "/complaints", "queryStringParameters": {"issue_type": "garbage"}})
    )
    assert [c["complaint_id"] for c in body["complaints"]] == ["CMP-G"]


def test_bbox_filters_by_location(stubbed):
    stubbed["complaints"].append(
        _record(complaint_id="CMP-FAR", lat=Decimal("19.07"), lng=Decimal("72.87"))
    )
    body = _body(
        app.handler(
            {"rawPath": "/complaints", "queryStringParameters": {"bbox": "77.0,28.0,77.1,28.1"}}
        )
    )
    assert [c["complaint_id"] for c in body["complaints"]] == [
        "CMP-01M2V3WRDT08DFMCJXVWRW9BKK"
    ]


@pytest.mark.parametrize(
    "bbox", ["1,2,3", "a,b,c,d", "77.1,28.0,77.0,28.1", "77.0,28.5,77.1,28.1"]
)
def test_malformed_bbox_is_400(stubbed, bbox):
    res = app.handler({"rawPath": "/complaints", "queryStringParameters": {"bbox": bbox}})
    assert res["statusCode"] == 400
    assert _body(res)["error"]["code"] == "invalid_bbox"


def test_markers_are_newest_first(stubbed):
    stubbed["complaints"].append(
        _record(complaint_id="CMP-NEW", created_at="2026-09-19T23:00:00+00:00")
    )
    body = _body(app.handler({"rawPath": "/complaints"}))
    assert body["complaints"][0]["complaint_id"] == "CMP-NEW"


# ==========================================================================
# GET /leaderboard
# ==========================================================================


def _ward_row(ward_id, open_n, resolved_n, age=30, res_days=20):
    return {
        "ward_id": ward_id,
        "open_count": open_n,
        "resolved_count": resolved_n,
        "median_open_age_days": age,
        "median_resolution_days": res_days,
    }


def test_leaderboard_ranks_worst_first(stubbed):
    stubbed["wards"] = [
        _ward_row("DEL-0001", 2, 40, age=5, res_days=3),      # low
        _ward_row("DEL-0002", 40, 2, age=85, res_days=55),    # high
    ]
    body = _body(app.handler({"rawPath": "/leaderboard"}))
    assert [w["ward_id"] for w in body["wards"]] == ["DEL-0002", "DEL-0001"]
    assert body["wards"][0]["rank"] == 1
    assert body["wards"][0]["neglect_index"] > body["wards"][1]["neglect_index"]


def test_quiet_wards_are_unranked_not_ranked_best(stubbed):
    """The single most important property of the board.

    A ward with almost no reports must not appear at the top of a
    "best-run wards" reading of the list.
    """
    stubbed["wards"] = [_ward_row("DEL-0001", 1, 0), _ward_row("DEL-0002", 30, 5)]
    body = _body(app.handler({"rawPath": "/leaderboard"}))
    assert [w["ward_id"] for w in body["wards"]] == ["DEL-0002"]
    assert [w["ward_id"] for w in body["unranked"]] == ["DEL-0001"]
    assert body["unranked"][0]["neglect_index"] is None
    assert body["unranked"][0]["note"] == "Not enough reports yet"


def test_leaderboard_uses_polygon_ward_names(stubbed):
    stubbed["wards"] = [_ward_row("DEL-0001", 10, 10)]
    body = _body(app.handler({"rawPath": "/leaderboard"}))
    assert body["wards"][0]["ward_name"] == "Westside"


def test_leaderboard_carries_the_disclosure_and_explanation(stubbed):
    stubbed["wards"] = [_ward_row("DEL-0001", 10, 10)]
    body = _body(app.handler({"rawPath": "/leaderboard"}))
    assert "demo data" in body["data_notice"].lower()
    assert "never an individual" in body["data_notice"]
    assert "still open" in body["index_explanation"]


def test_leaderboard_never_names_a_councillor(stubbed):
    """The index scores a ward. It is never attached to a person."""
    stubbed["wards"] = [
        {**_ward_row("DEL-0001", 30, 5), "councillor_name": "A. Person", "party": "Some Party"}
    ]
    raw = app.handler({"rawPath": "/leaderboard"})["body"]
    assert "A. Person" not in raw
    assert "Some Party" not in raw


def test_leaderboard_is_cached_for_a_minute(stubbed):
    calls = {"n": 0}

    def _counted():
        calls["n"] += 1
        return [_ward_row("DEL-0001", 10, 10)]

    app.scan_wards = _counted
    app.handler({"rawPath": "/leaderboard"})
    app.handler({"rawPath": "/leaderboard"})
    app.handler({"rawPath": "/leaderboard"})
    assert calls["n"] == 1, "the leaderboard should be computed once per TTL"


def test_ward_row_without_an_id_is_skipped(stubbed):
    stubbed["wards"] = [{"open_count": 5, "resolved_count": 5}, _ward_row("DEL-0001", 10, 10)]
    body = _body(app.handler({"rawPath": "/leaderboard"}))
    assert body["ranked_count"] == 1


def test_empty_leaderboard_does_not_break(stubbed):
    stubbed["wards"] = []
    body = _body(app.handler({"rawPath": "/leaderboard"}))
    assert body["wards"] == [] and body["ranked_count"] == 0


# ==========================================================================


def test_datastore_failure_is_a_500_not_a_stack_trace(stubbed, monkeypatch):
    monkeypatch.setattr(app, "query_complaints", lambda **kw: 1 / 0)
    res = app.handler({"rawPath": "/complaints"})
    assert res["statusCode"] == 500
    assert "ZeroDivision" not in res["body"]


# ==========================================================================
# GSI names are deployment configuration
# ==========================================================================


def test_index_names_come_from_configuration(monkeypatch):
    """A GSI cannot be renamed in place, so the code must bend to the deployment.

    The live stack deploys `ward-created-index` and `status-created-index`; an
    earlier version of this code hardcoded `GSI1`/`GSI2` and would have failed
    at runtime against it.
    """
    from common.config import load_config

    monkeypatch.setenv("WARD_INDEX_NAME", "ward-created-index")
    monkeypatch.setenv("STATUS_INDEX_NAME", "status-created-index")
    load_config.cache_clear()

    cfg = load_config()
    assert cfg.ward_index_name == "ward-created-index"
    assert cfg.status_index_name == "status-created-index"


def test_queries_use_the_configured_index_names(monkeypatch):
    from common import store
    from common.config import load_config

    monkeypatch.setenv("WARD_INDEX_NAME", "custom-ward-idx")
    monkeypatch.setenv("STATUS_INDEX_NAME", "custom-status-idx")
    load_config.cache_clear()

    used = []

    class _Table:
        def query(self, **kw):
            used.append(kw.get("IndexName"))
            return {"Items": []}

        def scan(self, **kw):
            used.append(None)
            return {"Items": []}

    monkeypatch.setattr(store, "_table", lambda name: _Table())

    store.query_complaints(status="OPEN")
    store.query_complaints(ward_id="DEL-0001")
    store.query_complaints()

    assert used == ["custom-status-idx", "custom-ward-idx", None]
