"""Run the real Lambda handlers against isolated, temporary Moto services.

No AWS profile is read. All AWS SDK endpoints and credentials are replaced before
any handler is imported. This is a disposable demo, not an AWS parity claim.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import importlib
import json
import logging
import os
from pathlib import Path
import re
import sys
import threading
from urllib.parse import parse_qs
from wsgiref.simple_server import WSGIRequestHandler, make_server

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend/src"))
LOCK = threading.RLock()


def configure(port: int, origin: str) -> None:
    for name in list(os.environ):
        if name.startswith("AWS_ENDPOINT_URL_") or name in {
            "AWS_PROFILE", "AWS_DEFAULT_PROFILE", "AWS_SESSION_TOKEN", "AWS_SECURITY_TOKEN",
            "AWS_WEB_IDENTITY_TOKEN_FILE", "AWS_ROLE_ARN", "AWS_ROLE_SESSION_NAME",
        }:
            os.environ.pop(name, None)
    os.environ.update(
        AWS_ACCESS_KEY_ID="local-demo-only", AWS_SECRET_ACCESS_KEY="local-demo-only",
        AWS_CONFIG_FILE=os.devnull, AWS_SHARED_CREDENTIALS_FILE=os.devnull,
        AWS_EC2_METADATA_DISABLED="true", AWS_IGNORE_CONFIGURED_ENDPOINT_URLS="false",
        AWS_ENDPOINT_URL=f"http://localhost:{port}", AWS_DEFAULT_REGION="ap-south-1",
        AWS_REGION="ap-south-1", NO_PROXY="localhost,127.0.0.1",
        COMPLAINTS_TABLE="local-complaints", WARDS_TABLE="local-wards",
        RATE_LIMIT_TABLE="local-write-budgets", WARD_INDEX_NAME="ward-created-index",
        STATUS_INDEX_NAME="status-created-index", PHOTOS_BUCKET="local-photos",
        DATA_BUCKET="", WARDS_GEOJSON_PATH=str(ROOT / "data/wards.geojson"),
        ALLOWED_ORIGIN=origin, DELIVERY_MODE="DEMO_OUTBOX", SES_SENDER="", SES_DEMO_RECIPIENT="",
        BEDROCK_ENABLED="false", BEDROCK_INFERENCE_PROFILE_ID="", DRAFT_QUEUE_URL="",
        LOCAL_DEMO="true", REPORTS_PER_MINUTE="10", UPLOADS_PER_MINUTE="20",
        STATUS_UPDATES_PER_MINUTE="30",
    )


def bootstrap() -> None:
    import boto3
    from common.config import load_config
    from common.wards import get_index

    boto3.setup_default_session(aws_access_key_id="local-demo-only",
        aws_secret_access_key="local-demo-only",region_name="ap-south-1")
    ddb = boto3.resource("dynamodb", region_name="ap-south-1")
    ddb.create_table(
        TableName="local-complaints", BillingMode="PAY_PER_REQUEST",
        KeySchema=[{"AttributeName": "complaint_id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": key, "AttributeType": "S"}
                              for key in ["complaint_id", "ward_id", "status", "created_at"]],
        GlobalSecondaryIndexes=[{
            "IndexName": index,
            "KeySchema": [{"AttributeName": key, "KeyType": "HASH"},
                          {"AttributeName": "created_at", "KeyType": "RANGE"}],
            "Projection": {"ProjectionType": "ALL"},
        } for index, key in [("ward-created-index", "ward_id"), ("status-created-index", "status")]],
    )
    for name, key in [("local-wards", "ward_id"), ("local-write-budgets", "client_window")]:
        ddb.create_table(TableName=name, BillingMode="PAY_PER_REQUEST",
                         KeySchema=[{"AttributeName": key, "KeyType": "HASH"}],
                         AttributeDefinitions=[{"AttributeName": key, "AttributeType": "S"}])
    ddb.meta.client.update_time_to_live(TableName="local-write-budgets",
        TimeToLiveSpecification={"AttributeName": "expires_at", "Enabled": True})
    s3 = boto3.client("s3", region_name="ap-south-1")
    s3.create_bucket(Bucket="local-photos", CreateBucketConfiguration={"LocationConstraint": "ap-south-1"})
    s3.put_bucket_cors(Bucket="local-photos", CORSConfiguration={"CORSRules": [{
        "AllowedOrigins": [load_config().allowed_origin], "AllowedMethods": ["GET", "PUT"],
        "AllowedHeaders": ["content-type", "content-length"],
    }]})
    queue = boto3.client("sqs", region_name="ap-south-1").create_queue(QueueName="local-drafts")
    os.environ["DRAFT_QUEUE_URL"] = queue["QueueUrl"]
    load_config.cache_clear()

    # Actual bundled geometry, synthetic complaints, no councillor identities.
    from common.composer import compose
    now = datetime.now(timezone.utc)
    for group, (lat, lng) in enumerate([(28.6315,77.2167),(28.6514,77.1907),(28.5232,77.2013)]):
        ward = get_index().lookup(lat, lng)
        if ward is None:
            continue
        for number in range(6):
            identifier = f"LOCAL-DEMO-{group}-{number}"
            created = now - timedelta(days=3 + number * 4)
            draft = compose("POTHOLE", ward.ward_name, reported_on=created,
                ward_id=ward.ward_id, reference=identifier,
                description="Synthetic local example: broken road surface near the demo crossing.")
            item = dict(complaint_id=identifier, ward_id=ward.ward_id, ward_name=ward.ward_name,
                created_at=created.isoformat(), status="RESOLVED" if number==0 else "OPEN",
                lat=Decimal(str(lat)), lng=Decimal(str(lng)), issue_type="POTHOLE",
                is_demo=True, delivery_mode="DEMO_OUTBOX", draft_status="DRAFTED",
                status_token="local-seed-not-for-production", draft_source="template", **draft.to_dict())
            if number==0:
                item["resolved_at"] = (created+timedelta(days=2)).isoformat()
            ddb.Table("local-complaints").put_item(Item=item)
    importlib.import_module("compute_neglect_index.app").handler({}, None)


ROUTES = [
    ("GET", r"/health", "health.app", []),
    ("GET", r"/wards/lookup", "ward_lookup.app", []),
    ("GET", r"/wards/([^/]+)", "ward_lookup.app", ["ward_id"]),
    ("GET", r"/leaderboard", "complaints_query.app", []),
    ("GET", r"/complaints", "complaints_query.app", []),
    ("GET", r"/complaints/([^/]+)", "complaints_query.app", ["id"]),
    ("POST", r"/complaints/presign", "presign_upload.app", []),
    ("POST", r"/complaints", "create_complaint.app", []),
    ("POST", r"/complaints/([^/]+)/status", "status_update.app", ["id"]),
]


def application(environ, start_response):
    from common.config import load_config
    from common.responses import error
    method, path = environ["REQUEST_METHOD"], environ["PATH_INFO"]
    if method=="OPTIONS":
        result = {"statusCode": 204, "body": "", "headers": {
            "access-control-allow-origin": load_config().allowed_origin,
            "access-control-allow-methods": "GET,POST,OPTIONS", "access-control-allow-headers": "content-type"}}
    else:
        result = error(404, "not_found", "No such demo endpoint.")
        for verb, pattern, module, keys in ROUTES:
            match = re.fullmatch(pattern, path)
            if method!=verb or not match:
                continue
            try:
                length = int(environ.get("CONTENT_LENGTH") or 0)
                if length < 0 or length > 32_768:
                    result = error(413, "body_too_large", "Use the direct upload URL for photos.")
                    break
                raw = environ["wsgi.input"].read(length).decode("utf-8") if length else None
            except (ValueError, UnicodeDecodeError):
                result = error(400, "invalid_body", "Expected a UTF-8 JSON request.")
                break
            event = {"version":"2.0", "rawPath":path, "body":raw, "isBase64Encoded":False,
                "pathParameters":dict(zip(keys,match.groups())),
                "queryStringParameters":{k:v[-1] for k,v in parse_qs(environ.get("QUERY_STRING","")).items()},
                "requestContext":{"http":{"method":method,"sourceIp":environ.get("REMOTE_ADDR","")}}}
            with LOCK:
                result = importlib.import_module(module).handler(event, None)
                if module == "status_update.app" and result["statusCode"] == 200:
                    importlib.import_module("compute_neglect_index.app").handler({}, None)
                    importlib.import_module("complaints_query.app").reset_cache()
            break
    from http import HTTPStatus
    status = int(result["statusCode"])
    body = result.get("body", "").encode("utf-8")
    headers = {**result.get("headers",{}), "content-length":str(len(body))}
    start_response(f"{status} {HTTPStatus(status).phrase}", list(headers.items()))
    return [body]


def process_queue(stop: threading.Event) -> None:
    from common.aws import sqs_client
    from common.config import load_config
    worker = importlib.import_module("draft_and_send.app").handler
    compute = importlib.import_module("compute_neglect_index.app").handler
    queue = load_config().draft_queue_url
    while not stop.wait(0.25):
        try:
            with LOCK:
                messages = sqs_client().receive_message(QueueUrl=queue, MaxNumberOfMessages=5).get("Messages", [])
                if not messages:
                    continue
                result = worker({"Records":[{"messageId":m["MessageId"],"body":m["Body"]} for m in messages]}, None)
                failed = {item["itemIdentifier"] for item in result.get("batchItemFailures", [])}
                for message in messages:
                    if message["MessageId"] not in failed:
                        sqs_client().delete_message(QueueUrl=queue, ReceiptHandle=message["ReceiptHandle"])
                compute({}, None)
                importlib.import_module("complaints_query.app").reset_cache()
        except Exception:
            logging.exception("Local draft worker failed; queued items remain retryable")


class QuietRequests(WSGIRequestHandler):
    def log_message(self, *_):
        # Paths can contain capability tokens. Do not write them to stdout.
        pass


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", choices=["127.0.0.1","0.0.0.0","localhost"], default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8101)
    parser.add_argument("--aws-port", type=int, default=5001)
    parser.add_argument("--origin", default="http://localhost:5174")
    args = parser.parse_args()
    if args.port==args.aws_port or not all(0<port<65536 for port in [args.port,args.aws_port]):
        parser.error("Choose two distinct ports between 1 and 65535.")
    configure(args.aws_port, args.origin)
    logging.basicConfig(level=logging.WARNING)
    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    from moto.server import ThreadedMotoServer
    emulator = ThreadedMotoServer(ip_address=args.host, port=args.aws_port, verbose=False)
    stop = threading.Event()
    worker = None
    try:
        emulator.start()
        bootstrap()
        worker = threading.Thread(target=process_queue, args=(stop,), daemon=True)
        worker.start()
        with make_server(args.host,args.port,application,handler_class=QuietRequests) as server:
            print(f"Local API: http://localhost:{args.port}; frontend origin: {args.origin}",flush=True)
            print("Synthetic records; temporary in-memory storage; template drafts; no email or AWS calls.",flush=True)
            server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        if worker:
            worker.join(timeout=5)
        emulator.stop()


if __name__=="__main__":
    main()
