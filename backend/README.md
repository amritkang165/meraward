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
