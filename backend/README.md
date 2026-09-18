# MERAWARD — backend

Python 3.12 Lambdas behind an API Gateway HTTP API (no authorizer), deployed with AWS SAM.

## Layout

```
backend/
  template.yaml          SAM template — all Lambdas, tables, queue, bucket, IAM
  src/
    common/              shared: ward geometry, DynamoDB access, responses
    ward_lookup/         GET /wards/lookup, GET /wards/{ward_id}
    presign_upload/      POST /complaints/presign
    create_complaint/    POST /complaints  (fast path, <1s, enqueues to SQS)
    complaints_query/    GET /complaints, /complaints/{id}, /leaderboard
    status_update/       POST /complaints/{id}/status  (magic-link token)
    draft_and_send/      SQS worker: Bedrock draft → DynamoDB → SES
    compute_neglect_index/  EventBridge hourly
    health/              GET /health
```

## Owners

`common`, `ward_lookup`, `create_complaint`, `complaints_query`, `draft_and_send` — **Muneer**
`template.yaml`, IAM, deploy pipeline, `compute_neglect_index`, seed — **Kartik**

## Getting started

_To be filled in once `sam init` lands._

## SAM wiring — read this before writing `template.yaml`

Handlers import shared code as `from common.x import y`, so **every function uses
`CodeUri: backend/src`** and a dotted handler path:

```yaml
WardLookupFunction:
  Type: AWS::Serverless::Function
  Properties:
    CodeUri: src/
    Handler: ward_lookup.app.handler
    Runtime: python3.12
```

Each handler directory is a package (has `__init__.py`). One `CodeUri` for all
functions keeps `common/` importable everywhere without a layer.

`shapely` is the only non-stdlib runtime dependency (`requirements.txt`). It ships
a manylinux wheel, but **verify it imports on a deployed Lambda before anything
depends on it** — an architecture mismatch here is a classic two-hour sink.

## Local development

```bash
python -m pip install -r backend/requirements-dev.txt
python -m pytest backend -q
```

Tests need no AWS credentials. `WARDS_GEOJSON_PATH` points the ward index at a
local GeoJSON file instead of S3, which is also how `sam local` should be run.

## What exists so far

| Module | Purpose |
|---|---|
| `common/composer.py` | Deterministic bilingual complaint letters (the Bedrock-free floor) |
| `common/wards.py` | Ward polygons, STRtree, point-in-polygon, cached per cold start |
| `common/index.py` | Ward Neglect Index (PRD §13) |
| `common/store.py` | DynamoDB reads; councillor block with enforced provenance |
| `common/responses.py` | HTTP API responses, CORS, Decimal-safe JSON |
| `common/config.py` | Environment configuration |
| `common/ids.py` | ULID complaint ids, status tokens |
| `ward_lookup/app.py` | `GET /wards/lookup`, `GET /wards/{ward_id}` |
| `common/validation.py` | Write-path input validation |
| `common/aws.py` | Lazily-created, container-cached boto3 clients |
| `presign_upload/app.py` | `POST /complaints/presign` |
| `create_complaint/app.py` | `POST /complaints` — fast path, 202 + SQS enqueue |
| `health/app.py` | `GET /health` |
| `common/views.py` | Public projections — the allow-list that decides what is publishable |
| `complaints_query/app.py` | `GET /complaints/{id}`, `GET /complaints`, `GET /leaderboard` |
| `status_update/app.py` | `POST /complaints/{id}/status` — magic-link lifecycle |
| `common/bedrock.py` | Bedrock Converse adapter — optional, fails into the composer |
| `common/delivery.py` | SES delivery per mode; `SES_LIVE` refused at runtime |
| `draft_and_send/app.py` | SQS worker — draft, deliver, record, measure |


## `draft_and_send` — event source configuration

The worker returns partial batch failures, so only genuinely failed records are
redelivered. That requires the event source mapping to opt in:

```yaml
Events:
  DraftQueue:
    Type: SQS
    Properties:
      Queue: !GetAtt DraftQueue.Arn
      BatchSize: 5
      FunctionResponseTypes:
        - ReportBatchItemFailures   # required, or the whole batch retries
```

Without `ReportBatchItemFailures`, one bad record redelivers the entire batch and
every complaint in it gets redrafted.
