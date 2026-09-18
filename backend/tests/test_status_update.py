"""Tests for the magic-link status lifecycle.

There is no login in this product, so the token is the entire authorisation
story for this endpoint. These tests are the proof that it holds.
"""

from __future__ import annotations

import json

import pytest

from status_update import app

TOKEN = "5f2b3c4d-0000-4000-8000-abcdefabcdef"
CID = "CMP-01M2V3WRDT08DFMCJXVWRW9BKK"


def _record(status="OPEN", **over):
    record = {
        "complaint_id": CID,
        "ward_id": "DEL-0001",
        "ward_name": "Westside",
        "created_at": "2026-09-15T04:00:00+00:00",
        "status": status,
        "draft_status": "DRAFTED",
        "issue_type": "POTHOLE",
        "lat": 28.05,
        "lng": 77.05,
        "status_token": TOKEN,
        "reporter_email": "someone@example.com",
        "is_demo": False,
    }
    record.update(over)
    return record


def _event(action=None, token=TOKEN, cid=CID, **body_over):
    body = {}
    if action is not None:
        body["action"] = action
    if token is not None:
        body["token"] = token
    body.update(body_over)
    return {"pathParameters": {"id": cid}, "body": json.dumps(body)}


def _body(res):
    return json.loads(res["body"])


@pytest.fixture
def store(monkeypatch):
    state = {"record": _record(), "writes": []}

    monkeypatch.setattr(
        app, "get_complaint",
        lambda cid: state["record"] if cid == state["record"]["complaint_id"] else None,
    )
    monkeypatch.setattr(app, "photo_url", lambda key, **kw: None)

    def _update(complaint_id, *, new_status, expected_status, timestamps=None, clear=()):
        state["writes"].append(
            {
                "id": complaint_id,
                "new_status": new_status,
                "expected": expected_status,
                "timestamps": timestamps or {},
                "clear": clear,
            }
        )
        updated = {**state["record"], "status": new_status, **(timestamps or {})}
        for field in clear:
            updated.pop(field, None)
        state["record"] = updated
        return {"Attributes": updated}

    monkeypatch.setattr(app, "update_complaint_status", _update)
    return state


# ==========================================================================
# The token is the authorisation
# ==========================================================================


def test_correct_token_moves_the_complaint(store):
    res = app.handler(_event("acknowledge"))
    assert res["statusCode"] == 200
    body = _body(res)
    assert body["status"] == "ACKNOWLEDGED"
    assert body["changed"] is True
    assert body["acknowledged_at"]


def test_wrong_token_is_rejected(store):
    res = app.handler(_event("resolve", token="5f2b3c4d-0000-4000-8000-000000000000"))
    assert res["statusCode"] == 403
    assert _body(res)["error"]["code"] == "invalid_token"
    assert store["writes"] == [], "nothing may be written without a valid token"


@pytest.mark.parametrize("token", ["", "   ", None])
def test_missing_token_is_rejected(store, token):
    res = app.handler(_event("resolve", token=token))
    assert res["statusCode"] in (400, 403)
    assert store["writes"] == []


def test_token_prefix_does_not_authorise(store):
    """Guards the constant-time comparison against a truncated token."""
    res = app.handler(_event("resolve", token=TOKEN[:20]))
    assert res["statusCode"] == 403
    assert store["writes"] == []


def test_response_never_echoes_the_token_back(store):
    """The endpoint that consumes the secret must not republish it."""
    raw = app.handler(_event("acknowledge"))["body"]
    assert TOKEN not in raw
    assert "status_token" not in raw
    assert "someone@example.com" not in raw


def test_a_complaint_with_no_stored_token_cannot_be_moved(store):
    store["record"] = _record(status_token="")
    res = app.handler(_event("resolve", token="anything"))
    assert res["statusCode"] == 403
    assert store["writes"] == []


# ==========================================================================
# Transitions
# ==========================================================================


@pytest.mark.parametrize(
    "start,action,expected",
    [
        ("OPEN", "acknowledge", "ACKNOWLEDGED"),
        ("OPEN", "resolve", "RESOLVED"),
        ("ACKNOWLEDGED", "resolve", "RESOLVED"),
        ("ACKNOWLEDGED", "reopen", "OPEN"),
        ("RESOLVED", "reopen", "OPEN"),
    ],
)
def test_valid_transitions(store, start, action, expected):
    store["record"] = _record(status=start)
    res = app.handler(_event(action))
    assert res["statusCode"] == 200
    assert _body(res)["status"] == expected


@pytest.mark.parametrize("start,action", [("RESOLVED", "acknowledge")])
def test_invalid_transitions_are_409(store, start, action):
    store["record"] = _record(status=start)
    res = app.handler(_event(action))
    assert res["statusCode"] == 409
    assert _body(res)["error"]["code"] in ("invalid_transition", "status_changed")


def test_repeating_an_action_is_idempotent_not_an_error(store):
    """Magic links get clicked twice.

    Landing on the status you asked for is success, not a failure - a citizen
    who taps "Resolved" again should not see an error page.
    """
    app.handler(_event("resolve"))
    store["writes"].clear()

    res = app.handler(_event("resolve"))
    assert res["statusCode"] == 200
    assert _body(res)["changed"] is False
    assert store["writes"] == [], "a no-op must not write"


def test_writes_are_conditional_on_the_current_status(store):
    """Two people clicking the same link at once must not both win."""
    app.handler(_event("acknowledge"))
    assert store["writes"][0]["expected"] == "OPEN"
    assert store["writes"][0]["new_status"] == "ACKNOWLEDGED"


def test_a_concurrent_update_is_reported_as_a_conflict(store, monkeypatch):
    class ConditionalCheckFailedException(Exception):
        pass

    def _boom(*a, **kw):
        raise ConditionalCheckFailedException("the conditional request failed")

    monkeypatch.setattr(app, "update_complaint_status", _boom)
    res = app.handler(_event("acknowledge"))
    assert res["statusCode"] == 409
    assert _body(res)["error"]["code"] == "status_changed"


# ==========================================================================
# Reopening
# ==========================================================================


def test_reopening_clears_the_resolution(store):
    """Otherwise the ward's counts - and its index - keep crediting a bad fix."""
    store["record"] = _record(status="RESOLVED", resolved_at="2026-09-17T09:00:00+00:00")
    res = app.handler(_event("reopen"))

    assert _body(res)["status"] == "OPEN"
    assert store["writes"][0]["clear"] == ("resolved_at",)
    assert _body(res)["resolved_at"] is None


def test_reopening_appends_to_the_timeline_rather_than_erasing_it(store):
    """"Someone marked this fixed and it was not" is the accountability signal."""
    store["record"] = _record(
        status="RESOLVED",
        acknowledged_at="2026-09-16T06:00:00+00:00",
        resolved_at="2026-09-17T09:00:00+00:00",
    )
    body = _body(app.handler(_event("reopen")))
    labels = [step["label"] for step in body["timeline"]]

    assert "Acknowledged by ward office" in labels, "history must survive a reopen"
    assert labels[-1] == "Reported still broken"


def test_timeline_stays_in_chronological_order(store):
    store["record"] = _record(
        status="RESOLVED",
        acknowledged_at="2026-09-16T06:00:00+00:00",
        resolved_at="2026-09-17T09:00:00+00:00",
    )
    body = _body(app.handler(_event("reopen")))
    stamps = [step["at"] for step in body["timeline"]]
    assert stamps == sorted(stamps)


# ==========================================================================
# Input handling
# ==========================================================================


def test_new_status_is_accepted_as_an_alias_for_action(store):
    """The PRD's API table says `new_status`; the UI sends `action`."""
    res = app.handler(
        {"pathParameters": {"id": CID}, "body": json.dumps({"token": TOKEN, "new_status": "RESOLVED"})}
    )
    assert res["statusCode"] == 200
    assert _body(res)["status"] == "RESOLVED"


@pytest.mark.parametrize("action", ["", "delete", "DROP TABLE", None])
def test_unknown_actions_are_400(store, action):
    res = app.handler(_event(action))
    assert res["statusCode"] == 400
    assert _body(res)["error"]["code"] == "invalid_action"
    assert store["writes"] == []


def test_unknown_complaint_is_404(store):
    res = app.handler(_event("resolve", cid="CMP-NOPE"))
    assert res["statusCode"] == 404
    assert store["writes"] == []


def test_missing_body_is_400(store):
    assert app.handler({"pathParameters": {"id": CID}})["statusCode"] == 400


def test_malformed_json_is_400(store):
    res = app.handler({"pathParameters": {"id": CID}, "body": "{nope"})
    assert res["statusCode"] == 400
    assert _body(res)["error"]["code"] == "invalid_json"


def test_missing_complaint_id_is_400(store):
    res = app.handler({"body": json.dumps({"token": TOKEN, "action": "resolve"})})
    assert res["statusCode"] == 400


def test_unexpected_failure_is_a_500_without_a_stack_trace(store, monkeypatch):
    monkeypatch.setattr(app, "get_complaint", lambda cid: 1 / 0)
    res = app.handler(_event("resolve"))
    assert res["statusCode"] == 500
    assert "ZeroDivision" not in res["body"]
