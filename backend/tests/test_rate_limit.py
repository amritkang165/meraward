import json

import boto3
import pytest
from moto import mock_aws

from common.aws import reset_clients
from common.rate_limit import enforce_write_budget
from common.responses import ApiError
from common.config import load_config


@pytest.fixture
def budget(monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_TABLE", "test-write-budgets")
    monkeypatch.setenv("REPORTS_PER_MINUTE", "2")
    monkeypatch.setenv("UPLOADS_PER_MINUTE", "2")
    monkeypatch.setenv("STATUS_UPDATES_PER_MINUTE", "2")
    monkeypatch.setattr("common.rate_limit.time.time", lambda: 125)
    reset_clients()
    with mock_aws():
        table = boto3.resource("dynamodb", region_name="ap-south-1").create_table(
            TableName="test-write-budgets", BillingMode="PAY_PER_REQUEST",
            KeySchema=[{"AttributeName": "client_window", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "client_window", "AttributeType": "S"}],
        )
        yield table
    reset_clients()


def event(ip="192.0.2.1"):
    return {"requestContext": {"http": {"sourceIp": ip}}}


def test_limits_are_shared_and_do_not_trust_forwarding_headers(budget):
    request = event()
    enforce_write_budget(request, "report")
    reset_clients()  # another container sees the same stored counter
    enforce_write_budget(request, "report")
    request["headers"] = {"x-forwarded-for": "192.0.2.99"}
    with pytest.raises(ApiError) as failure:
        enforce_write_budget(request, "report")
    response = failure.value.to_response()
    assert response["statusCode"] == 429
    assert response["headers"]["retry-after"] == "55"
    assert json.loads(response["body"])["error"]["code"] == "rate_limited"
    enforce_write_budget(event("192.0.2.2"), "report")
    enforce_write_budget(request, "upload")
    rows = budget.scan()["Items"]
    assert len(rows) == 3
    assert all("192.0.2" not in str(row) for row in rows)
    assert all(row["expires_at"] == 240 for row in rows)


def test_new_minute_does_not_wait_for_ttl_deletion(budget, monkeypatch):
    for _ in range(2):
        enforce_write_budget(event(), "report")
    monkeypatch.setattr("common.rate_limit.time.time", lambda: 180)
    enforce_write_budget(event(), "report")
    assert len(budget.scan()["Items"]) == 2


def test_unknown_client_and_unavailable_store_fail_closed(budget, monkeypatch):
    with pytest.raises(ApiError, match="no client address"):
        enforce_write_budget({}, "report")
    monkeypatch.setenv("RATE_LIMIT_TABLE", "missing-table")
    load_config.cache_clear()
    with pytest.raises(ApiError) as failure:
        enforce_write_budget(event(), "report")
    assert failure.value.status == 503


@pytest.mark.parametrize("module,scope", [
    ("create_complaint.app", "report"), ("presign_upload.app", "upload"), ("status_update.app", "status"),
])
def test_each_write_route_enforces_budget_before_work(budget, module, scope):
    import importlib
    handler = importlib.import_module(module).handler
    for _ in range(2):
        enforce_write_budget(event(), scope)
    response = handler({**event(), "body": "{}"})
    assert response["statusCode"] == 429
    assert response["headers"]["retry-after"] == "55"
