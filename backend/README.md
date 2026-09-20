# MeraWard backend

Python 3.13 Lambda handlers for ward lookup, complaint drafting and public tracking. The same handlers power the local sandbox and the AWS SAM deployment. There is no server account system: write budgets limit basic abuse, and a private capability token authorizes complaint-status changes.

## Run it

The root [local demo instructions](../README.md#run-the-local-demo) start the complete app. For a native API in a Python 3.13 virtual environment, from the root:

```bash
python -m pip install -r backend/requirements-demo.txt
python backend/local_demo.py
```

The API is at `http://localhost:8101`; the Moto service endpoint is at `http://localhost:5001`. Both bind to loopback by default. The frontend origin is `http://localhost:5174`. CLI `--port`, `--aws-port` and `--origin` change these together when needed; the two ports must differ. `--host 0.0.0.0` is used inside Compose, whose published ports remain loopback-only.

The sandbox is temporary. It forces dummy credentials/local endpoints, loads the committed ward geometry, seeds synthetic reports and runs the real queue worker. It does not use an AWS profile, Bedrock, SES or CloudWatch metrics. Recreating/stopping it discards all records and photos.

## Modules and endpoints

| Module | Contract |
| --- | --- |
| `ward_lookup` | `GET /wards/lookup?lat=&lng=`, `GET /wards/{ward_id}` |
| `presign_upload` | `POST /complaints/presign`; bounded image type/length, direct S3 PUT URL |
| `create_complaint` | `POST /complaints`; validates evidence/location, saves before enqueueing, returns 202 and private token |
| `complaints_query` | Public complaint detail, map markers and leaderboard |
| `status_update` | Token-protected acknowledge/resolve/reopen, with conditional status writes |
| `draft_and_send` | SQS worker: draft, save, demo delivery record and production metric |
| `compute_neglect_index` | Recompute ward statistics; hourly on AWS |
| `health` | Geometry loading, configured drafting/delivery mode and write-budget state |
| `common/wards.py` | Cached Shapely STRtree over the configured geometry |
| `common/store.py`, `common/views.py` | DynamoDB access and public-field allowlists |
| `common/composer.py`, `common/bedrock.py` | Deterministic bilingual floor and optional model adapter |
| `common/rate_limit.py` | Conditional DynamoDB counters per source, scope and minute |

`WARDS_GEOJSON_PATH` selects a local file. Otherwise the service loads `WARDS_GEOJSON_KEY` from `DATA_BUCKET` in S3. The local runner always chooses the bundled file. `COMPLAINTS_TABLE`, `WARDS_TABLE` and index names select the AWS stores; `RATE_LIMIT_TABLE` activates the shared write guard. See [maintenance configuration](../docs/MAINTENANCE.md) and [the environment example](../.env.example).

## Checks

From the root in the configured Python environment:

```bash
python -m pip install -r backend/requirements-dev.txt
python -m pytest backend -q
sam validate --lint --template-file backend/template.yaml --region ap-south-1
```

With the sandbox running:

```bash
python backend/tests/smoke_demo.py
```

Unit/regression tests use fakes or isolated Moto state. The HTTP smoke uses actual SDK calls against the local service endpoint and refuses to write to a non-loopback API. These tests do not establish real AWS permissions or production S3 signature enforcement.

## SAM deployment contract

Every function uses `CodeUri: src/` relative to `backend/template.yaml`, a dotted handler such as `ward_lookup.app.handler`, and runtime `python3.13`. `common/` is therefore importable by every function. The native Shapely wheel must match Lambda's Linux runtime; use a container build when packaging from Windows.

The SQS mapping uses `FunctionResponseTypes: [ReportBatchItemFailures]` and batch size 5. Preserve that setting so a failed item does not redeliver every successful item in the batch. The worker's persisted terminal state avoids redrafting an already completed complaint.

The template keeps the existing resource logical IDs and physical complaint/ward table names. It adds a separate TTL counter table; the three write functions receive only `dynamodb:UpdateItem` on that table. `AllowedOrigin` consistently configures API Gateway, Lambda responses and S3 PUT CORS. Existing deployments need the reviewed template deployed to activate those changes.

Use the [AWS runbook](../docs/AWS_SETUP.md) for the shared stack. No CI workflow deploys it. `SES_LIVE` remains refused; keep delivery in `DEMO_OUTBOX` unless a separately authorized verified-inbox test is intended. Original team ownership and the shared SAM history are preserved in the [root credits](../README.md#team-and-contribution).
