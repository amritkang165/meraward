# Submission writeup — MERAWARD

**Draft.** Paste into the submission form once the live URL and video link exist.
Fill the three `<!-- TODO -->` markers first.

---

## The problem

Delhi has hundreds of municipal wards, each with an elected councillor whose remit
covers exactly the things that stay broken: potholes, streetlights, garbage, drains,
waterlogging.

Three things are wrong at once.

**Nobody knows their ward.** The boundaries were redrawn in 2022 and most people
still cite the old zones. There is no simple "which ward am I in?" tool.

**Complaints go into black holes.** Portals accept a complaint and offer no tracking,
no escalation, and no consequence. People tweet into the void instead.

**There is no public scoreboard.** No ward-level data on open complaints or
resolution speed exists publicly, so "which areas get ignored" stays a rumour
instead of a number.

The result is that the same pothole survives three monsoons, and holding anyone to
account requires knowing who to ask — which almost nobody does.

## What we built

A mobile-first PWA with three connected surfaces.

**Find your ward.** GPS or a dropped pin returns your ward, its zone, its councillor
where we could source one, and its Ward Neglect Index. Point-in-polygon against 289
real ward polygons, in about 0.02 ms.

**Report in one tap.** A photo and an issue type. The complaint is drafted as a
formal letter **in Hindi and English**, addressed to the correct ward office, and
tracked publicly. No signup, no account, no login anywhere in the product.

**A public accountability dashboard.** Every report on a Delhi map as a heatmap or
points, plus a leaderboard of wards ranked by the Neglect Index.

## How it is built on AWS

**API Gateway (HTTP API) → six Python 3.12 Lambdas → DynamoDB.** No authorizer
anywhere: one-tap reporting *is* the product, and a signup wall would contradict the
pitch. Abuse control is API Gateway throttling, a photo size cap, and strict
validation of every field.

**Point-in-polygon runs inside the Lambda.** `wards.geojson` lives in S3 and is
loaded once per cold start into a `shapely` STRtree held at module level. 289
polygons is a few megabytes; an R-tree query over them is sub-millisecond. We
considered a managed search cluster and rejected it — OpenSearch Serverless has a
two-OCU floor of roughly $11/day, which would have made our own cost claim false.

**SQS sits between the API and the AI draft.** `create_complaint` validates,
resolves the ward, writes the row, enqueues, and returns `202` in about 2 ms. The
draft and the email happen on a worker, so the user never waits on a model. Retries
and a dead-letter queue come free. The row is written *before* the enqueue, because
the other order races: the worker can pick up a message and find nothing to draft
against.

**Bedrock drafts the bilingual letter, and is optional by design.** A deterministic
template composer was written *first*, returning the same
`{subject, body_en, body_hi}` shape, so the model is a config flag rather than a
dependency. If SQS itself is unreachable, `create_complaint` composes inline and the
user still gets a complete complaint instead of one stuck on pending forever.

**SES delivers, EventBridge keeps the index live, CloudWatch measures it.** An
hourly scheduled Lambda recomputes every ward's index — hourly rather than daily,
because a daily job may never fire inside a demo window.

**Amplify Hosting and CloudFront** serve the PWA over HTTPS.

Services used: Lambda · API Gateway · DynamoDB · S3 · SQS (+DLQ) · Bedrock · SES ·
EventBridge Scheduler · CloudWatch · Amplify / CloudFront. IaC is AWS SAM.

## Engineering decisions we would defend

**The index scores a ward, never a person.** It is computed partly from generated
demonstration data. Attaching such a number to a real, named, elected individual
would be indefensible, so the index belongs to the ward and the councillor block is
identity only, visually separated, and withheld entirely unless we sourced it.

**A ward with fewer than five reports has no index at all** — not zero. Scoring a
silent ward as zero would rank the wards nobody reports as the best-run wards in the
city, which is exactly backwards.

**We do not email real officials.** Complaints are drafted, queued to a visible
outbox, and delivered to a verified demo inbox. Sending unsolicited AI-drafted mail
to public servants from a demonstration system would be spam regardless of intent,
so the live-send path exists in code and is switched off.

**Our ward boundaries are real but not current, and we say so.** They are the
pre-2022 delimitation — 272 MCD wards, not the 250 created by the 2022 unification.
We could not find the post-2022 boundaries published as usable open data. That the
present ward boundaries of a city of twenty million are not openly available is
itself a fair illustration of the problem this project is about.

**Every generated record is flagged** `is_demo` in the database and labelled in the
interface.

## Impact

Accountability currently requires knowing who to blame, and the information needed
to know that is not readily available. This closes the first gap in three seconds
and measures the second: "which ward gets ignored" stops being a rumour and becomes
a number with four visible inputs anyone can check.

## Quality

- **213 backend tests**, none requiring AWS credentials.
- **Lighthouse mobile**: 100 performance / 100 accessibility / 100 best practices /
  100 SEO on the home page; 100 accessibility and best practices on every page.
- Total AWS cost for the weekend: <!-- TODO: real Cost Explorer figure -->

## AI tools used

AI coding tools are permitted under the rules **if disclosed**. We used them heavily
and this is the disclosure.

| Tool | Used for |
|---|---|
| Claude (Anthropic), via Claude Code | PRD review and rewrite, architecture critique, implementation of backend Lambdas and frontend screens, test authoring, ward-data pipeline, performance work, documentation |
| Amazon Bedrock | A **runtime product feature**, not a build tool — it drafts the bilingual complaint letter |

Every architectural decision, scope cut and service choice was reviewed and accepted
by the team. The commit history is unmodified: no force-pushes, no squashes, no
rewritten commit dates, and all three team members commit under their own accounts.

## Links

- **Live URL:** <!-- TODO -->
- **Demo video:** <!-- TODO -->
- **Repository:** https://github.com/amritkang165/meraward

## Team — Sleepy peeps (`4T5AKB`)

| | Role |
|---|---|
| Amrit Kang | Team lead · frontend · ward data · submission |
| Kartik Dixit | AWS infrastructure · SAM · delivery pipeline |
| Muneer Alam | Backend Lambdas · geospatial · index |
