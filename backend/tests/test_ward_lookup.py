"""Tests for the ward_lookup handler, response helpers and ids."""

from __future__ import annotations

import decimal
import json

import pytest

from common.ids import complaint_id, new_ulid, status_token, ulid_timestamp_ms
from common.responses import json_encode, ok
from common.store import councillor_block
from ward_lookup import app


@pytest.fixture(autouse=True)
def _no_dynamodb(monkeypatch):
    """Default: the Wards table has no row for this ward.

    That is the real state before the first index run, and the handler must
    still return a usable ward card.
    """
    monkeypatch.setattr(app, "get_ward_record", lambda ward_id: None)


def _body(response):
    return json.loads(response["body"])


# ------------------------------------------------------------------- routing

def test_lookup_by_coordinates(wards_file):
    res = app.handler({"queryStringParameters": {"lat": "28.05", "lng": "77.05"}})
    assert res["statusCode"] == 200
    body = _body(res)
    assert body["ward_id"] == "DEL-0001"
    assert body["ward_name"] == "Westside"
    assert body["query"] == {"lat": 28.05, "lng": 77.05}


def test_lookup_by_ward_id(wards_file):
    res = app.handler({"pathParameters": {"ward_id": "DEL-0002"}})
    assert res["statusCode"] == 200
    assert _body(res)["ward_name"] == "Eastside"


def test_unknown_ward_id_is_404(wards_file):
    res = app.handler({"pathParameters": {"ward_id": "DEL-9999"}})
    assert res["statusCode"] == 404
    assert _body(res)["error"]["code"] == "ward_not_found"


def test_point_outside_coverage_is_404_with_a_usable_message(wards_file):
    res = app.handler({"queryStringParameters": {"lat": "19.07", "lng": "72.87"}})
    assert res["statusCode"] == 404
    error = _body(res)["error"]
    assert error["code"] == "outside_coverage"
    assert "outside" in error["message"].lower()


# ---------------------------------------------------------------- validation

@pytest.mark.parametrize(
    "params,code",
    [
        ({}, "missing_coordinate"),
        ({"lat": "28.05"}, "missing_coordinate"),
        ({"lng": "77.05"}, "missing_coordinate"),
        ({"lat": "", "lng": "77.05"}, "missing_coordinate"),
        ({"lat": "abc", "lng": "77.05"}, "invalid_coordinate"),
        ({"lat": "28.05", "lng": "banana"}, "invalid_coordinate"),
        ({"lat": "nan", "lng": "77.05"}, "invalid_coordinate"),
        ({"lat": "inf", "lng": "77.05"}, "invalid_coordinate"),
        ({"lat": "91", "lng": "77.05"}, "coordinate_out_of_range"),
        ({"lat": "28.05", "lng": "181"}, "coordinate_out_of_range"),
    ],
)
def test_bad_coordinates_are_400_not_500(wards_file, params, code):
    res = app.handler({"queryStringParameters": params})
    assert res["statusCode"] == 400
    assert _body(res)["error"]["code"] == code


def test_handler_never_leaks_a_stack_trace(wards_file, monkeypatch):
    monkeypatch.setattr(app, "get_ward_record", lambda w: 1 / 0)
    res = app.handler({"pathParameters": {"ward_id": "DEL-0001"}})
    assert res["statusCode"] == 500
    assert "ZeroDivision" not in res["body"]


# ----------------------------------------------------- index and disclosure

def test_ward_with_no_data_reports_no_index_rather_than_zero(wards_file):
    body = _body(app.handler({"pathParameters": {"ward_id": "DEL-0001"}}))
    assert body["neglect_index"] is None
    assert body["index_note"] == "Not enough reports yet"


def test_index_is_computed_from_the_ward_record(wards_file, monkeypatch):
    monkeypatch.setattr(
        app,
        "get_ward_record",
        lambda w: {
            "open_count": decimal.Decimal(25),
            "resolved_count": decimal.Decimal(25),
            "median_open_age_days": decimal.Decimal(45),
            "median_resolution_days": decimal.Decimal(30),
        },
    )
    body = _body(app.handler({"pathParameters": {"ward_id": "DEL-0001"}}))
    assert body["neglect_index"] == 50
    assert body["index_band"] == "MODERATE"
    assert body["index_basis"]["open"] == 25


def test_every_response_carries_the_demo_data_notice(wards_file):
    body = _body(app.handler({"pathParameters": {"ward_id": "DEL-0001"}}))
    assert "demo data" in body["data_notice"].lower()


def test_explanation_matches_what_the_formula_computes(wards_file):
    body = _body(app.handler({"pathParameters": {"ward_id": "DEL-0001"}}))
    text = body["index_explanation"].lower()
    assert "still open" in text and "waiting" in text and "slow" in text


# ---------------------------------------------- councillor block (PRD §12)

def test_councillor_is_null_when_unsourced():
    assert councillor_block(None) is None
    assert councillor_block({}) is None
    assert councillor_block({"councillor_name": "A. Person"}) is None, (
        "a name without a contact_source must be withheld, not published unattributed"
    )


def test_councillor_is_published_only_with_provenance():
    block = councillor_block(
        {
            "councillor_name": "A. Person",
            "party": "Some Party",
            "contact_source": "MCD election results 2022",
        }
    )
    assert block == {
        "name": "A. Person",
        "party": "Some Party",
        "source": "MCD election results 2022",
    }


def test_councillor_block_never_carries_contact_details():
    """We do not email officials, so we do not collect or publish addresses."""
    block = councillor_block(
        {
            "councillor_name": "A. Person",
            "contact_source": "MCD election results 2022",
            "councillor_contact": "someone@example.gov.in",
        }
    )
    assert "someone@example.gov.in" not in json.dumps(block)


def test_index_and_councillor_are_separate_fields(wards_file, monkeypatch):
    """The score attaches to the ward, never nested under the person."""
    monkeypatch.setattr(
        app,
        "get_ward_record",
        lambda w: {
            "open_count": 30,
            "resolved_count": 5,
            "councillor_name": "A. Person",
            "contact_source": "MCD election results 2022",
        },
    )
    body = _body(app.handler({"pathParameters": {"ward_id": "DEL-0001"}}))
    assert body["neglect_index"] is not None
    assert set(body["councillor"]) == {"name", "party", "source"}


# ------------------------------------------------------------------ plumbing

def test_decimal_from_dynamodb_encodes_cleanly():
    """boto3 returns Decimal for every number; unhandled it is the first 500."""
    encoded = json.loads(json_encode({"a": decimal.Decimal("23"), "b": decimal.Decimal("1.5")}))
    assert encoded == {"a": 23, "b": 1.5}


def test_responses_carry_cors_and_content_type():
    headers = ok({"x": 1})["headers"]
    assert headers["access-control-allow-origin"] == "*"
    assert "application/json" in headers["content-type"]


def test_hindi_survives_json_encoding():
    assert "सड़क" in json_encode({"body_hi": "सड़क"})


# ----------------------------------------------------------------------- ids

def test_ulids_sort_chronologically():
    early = new_ulid(1_600_000_000_000)
    late = new_ulid(1_700_000_000_000)
    assert early < late


def test_ulid_round_trips_its_timestamp():
    assert ulid_timestamp_ms(new_ulid(1_789_638_905_000)) == 1_789_638_905_000


def test_ulids_are_unique_and_correctly_shaped():
    ids = {new_ulid() for _ in range(2000)}
    assert len(ids) == 2000
    assert all(len(i) == 26 for i in ids)
    assert not ({"I", "L", "O", "U"} & set("".join(ids))), "Crockford base32 excludes ILOU"


def test_complaint_id_is_prefixed():
    assert complaint_id().startswith("CMP-")


def test_status_tokens_are_unique():
    assert len({status_token() for _ in range(1000)}) == 1000
