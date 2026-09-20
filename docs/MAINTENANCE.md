# Demo maintenance

These are source changes for review; they do not describe a deployment that has
already been applied to the shared AWS stack.

## Write budgets and CORS

The SAM template provisions a separate, on-demand `WriteBudgetTable`. Its only
data is a SHA-256 digest of API Gateway's source address, a route scope, a minute
and a counter. Old rows expire via DynamoDB TTL. A conditional `UpdateItem`
enforces a shared limit across Lambda containers; it does not rely on TTL
deletion completing on time. `X-Forwarded-For` is not trusted.

Defaults per source address, per fixed minute:

| Operation | Setting | Default |
| --- | --- | --- |
| Create report | `REPORTS_PER_MINUTE` | 10 |
| Issue upload URL | `UPLOADS_PER_MINUTE` | 20 |
| Change status | `STATUS_UPDATES_PER_MINUTE` | 30 |

Exhausted budgets return `429 rate_limited` with `Retry-After`. A configured but
unavailable counter table returns `503 write_unavailable`; it does not silently
allow unlimited writes. An absent `RATE_LIMIT_TABLE` preserves compatibility with
the earlier deployment, so **deploy the reviewed SAM template to activate the
guard**. Shared networks share a budget, and a fixed-minute window permits a
burst across the boundary. This is basic abuse control, not authentication or
bot detection. API Gateway also has aggregate throttles.

The single `AllowedOrigin` parameter drives API Gateway, Lambda response headers
and S3 PUT CORS. It defaults to the existing Amplify origin and rejects `*` or a
trailing path. CORS restricts browser access; it does not authenticate API users.

IAM Policy Autopilot analyzed `common/aws.py` and `common/rate_limit.py` and
identified `dynamodb:UpdateItem`. The new grants are narrowed to the counter
table's ARN. Its suggested customer-key KMS grant is unnecessary for this table's
AWS-owned default encryption and was omitted. Existing resource logical IDs and
physical table names remain intact; only the counter table is new.

`SES_LIVE` remains refused. Bedrock remains disabled. Ward boundaries are not
changed by this work.

## Frontend dependencies

Use Node.js 22.12+ or 24 and `npm ci` in `frontend/`. Vite 7, React's Vite plugin
5, PWA plugin 2, React Router 7 and MapLibre 6 replace vulnerable older versions.
The MapLibre imports use its current named exports. React and the product routes
retain their existing design.

Run `npm run build` and `npm audit --omit=dev`. The full development audit still
reports Workbox build-tool advisories (deepmerge/glob/minimatch and their
dependents); no zero-advisory claim is made for the development toolchain.
Do not apply npm's forced downgrade suggestions without checking compatibility.

The earlier Lighthouse and timing numbers are historical measurements; a new
build or a larger patched map bundle does not inherit those scores. Re-measure
before making a fresh performance claim.

## Checks

From the repository root in a Python 3.13 virtual environment:

```bash
python -m pip install -r backend/requirements-dev.txt
python -m pytest backend -q
sam validate --lint --template-file backend/template.yaml --region ap-south-1
```

From `frontend/`:

```bash
npm ci
npm run build
npm audit --omit=dev
```

CI runs backend tests, the frontend build and production dependency audit, and
SAM lint without AWS credentials. Shared-stack deployment is a separate step
after PR review; no workflow deploys AWS resources.

## Isolated local runtime

`backend/local_demo.py` starts Moto on loopback, forces dummy SDK credentials and
endpoints, creates separate complaint/ward/counter tables, a photo bucket and a
draft queue, and seeds only synthetic reports. The bundled geometry is unchanged.
It invokes the actual handlers and SQS worker, with template/outbox modes forced
and CloudWatch emission disabled locally. Data is temporary, with no reset route
exposed. Local index statistics refresh after drafts/status changes; production
keeps its existing hourly schedule. The UI labels the sandbox and every record.

The frontend uses a Vite-resolved MapLibre worker asset; this fixes a blank-map
failure introduced by the required MapLibre patch migration. Source/public mounts
and polling support Windows Fast Refresh. The manifest references the existing
SVG icon. Public complaint text identifies outbox or verified-inbox modes without
claiming that an email was sent. Templates no longer invent an MCD affiliation
for every ward office.

`backend/tests/smoke_demo.py` uses only the Python standard library and refuses
non-loopback URLs/non-sandbox health before writing. It exercises actual HTTP
upload/draft/read/status behavior. The separate local-configuration regression
proves inherited profiles and per-service cloud endpoints are replaced.

SAM packaging was also verified in a Linux build container on Windows using
the already-installed Python 3.13 builder (`sam build --use-container
--skip-pull-image`). The initial builder-refresh attempt was interrupted while
waiting; the cached-image build completed. This verifies packaging, not a shared
stack deployment. Keep its artifacts ignored and do not reuse a stale builder
as a substitute for reviewing the eventual deployment environment.
