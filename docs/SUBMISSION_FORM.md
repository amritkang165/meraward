# Submission form — field-by-field answers

Everything below is copy-paste ready. Fields marked **⚠️ YOU MUST SUPPLY** cannot be
derived from the repo — usernames, LinkedIn URLs, resumes, the YouTube link.

Every factual claim here was verified against the live deployment on 2026-09-20:
`/health` returns `ward_index: {loaded: true, wards: 289}` and `drafting: {mode: "template"}`,
`/complaints` returns 246 markers, `/leaderboard` ranks 16 wards, and `pytest backend -q`
reports **254 passed**.

---

## 1. Team identity

| Field | Value |
|---|---|
| **Team leader's WeMakeDevs username** ⚠️ | _YOU MUST SUPPLY_ — from wemakedevs.org/home. Team code on record is `4T5AKB`, team name "Sleepy peeps" |
| Second member's WeMakeDevs username ⚠️ | _YOU MUST SUPPLY_ |
| Third member's WeMakeDevs username ⚠️ | _YOU MUST SUPPLY_ |
| Fourth member's WeMakeDevs username | _leave blank — three-person team_ |

> **Decide who is "team leader" before filling this.** `README.md` lists Amrit Kang as
> team lead, and the repo lives at `github.com/amritkang165/meraward`, so Amrit is the
> consistent answer. Whoever is listed first here must be listed first in every
> subsequent block (GitHub, LinkedIn, resume, contributions) — the form pairs them by
> position.

### GitHub

| Field | Value |
|---|---|
| **Team leader's GitHub** | `https://github.com/amritkang165` |
| Second member's GitHub | `https://github.com/Kartikdixit2468` |
| Third member's GitHub | `https://github.com/Muneer320` |

### LinkedIn ⚠️ YOU MUST SUPPLY

All three. Required field for the leader.

### Resumes ⚠️ YOU MUST SUPPLY

Optional, but it is the gate for **Amazon Fast Track Interviews** — upload to Google
Drive, set "Anyone with the link can view", paste the link. Worth the four minutes.

---

## 2. Project

| Field | Value |
|---|---|
| **Project title** | `MERAWARD` |
| **Track** | **Ship It** |
| **GitHub link** | `https://github.com/amritkang165/meraward` |
| **Deployed link** | `https://main.d1s6q0cvldi6dz.amplifyapp.com` |
| **YouTube demo** ⚠️ | _YOU MUST SUPPLY_ — script is ready at [`docs/VIDEO_SCRIPT.md`](VIDEO_SCRIPT.md). Upload **unlisted**, then confirm it plays logged-out in an incognito window |

**On the track choice:** the form allows submitting to both tracks and winning only one.
This project is a Ship It project — it is deployed, public, and the whole point is a live
URL a judge can click. Ship It only.

**Before you paste the GitHub link, confirm:** repo is public, `README.md` renders, and
commit history is intact (29 commits, three named contributors, no force-pushes). Judges
check this.

---

## 3. What does your project do? *(required)*

> Delhi has hundreds of municipal wards. Each has an elected councillor whose remit is
> exactly the things that stay broken — potholes, streetlights, garbage, drains,
> waterlogging. Three things are wrong at once: almost nobody knows which ward they live
> in, complaints filed on existing portals vanish with no tracking and no consequence, and
> there is no public ward-level data on what is being ignored. So the same pothole survives
> three monsoons, and holding anyone to account requires knowing who to ask.
>
> MERAWARD is a mobile-first PWA that closes all three gaps.
>
> **Find your ward.** GPS or a dropped pin runs point-in-polygon against 289 real Delhi
> ward polygons and returns your ward, its zone, its councillor where we could source one,
> and its Ward Neglect Index. Warm lookups measure 0.023 ms.
>
> **Report in one tap.** Speak it, photograph it, or type it. The complaint is drafted as a
> formal letter **in Hindi and English**, addressed to the correct ward office, and shown to
> you for review and editing before anything is filed. No signup, no login, no account
> anywhere in the product — a signup wall would contradict the entire pitch.
>
> **A public accountability dashboard.** Every report on a Delhi heatmap, plus wards ranked
> by Neglect Index — a 0–100 score built from how many reports are still open, how long
> they have waited, and how slow past fixes were, with all four raw inputs shown beside the
> gauge so anyone can check the arithmetic.
>
> It is for any resident of Delhi with a broken street and no idea who to tell — and for
> journalists, RWAs and civic groups who need "which ward gets ignored" to be a number
> instead of a rumour.
>
> Two rules we hold ourselves to. **The index scores a ward, never a person** — it is
> computed partly from demonstration data, and attaching that number to a real, named,
> elected individual would be indefensible. And **a ward with fewer than five reports has
> no index at all, not zero** — scoring a silent ward as zero would rank the wards nobody
> reports as the best-run in the city, which is exactly backwards.

---

## 4. How did you use AWS in your project? *(required)*

> **Build it — the AWS open source stack**
>
> **AWS SAM** and the **AWS SAM CLI** are our infrastructure-as-code. One
> `backend/template.yaml` defines everything: eight Lambdas, the HTTP API, two DynamoDB
> tables with their GSIs, two S3 buckets, the SQS queue and its dead-letter queue, the
> EventBridge schedule, and every IAM policy. `sam validate --lint`, `sam build` and
> `sam deploy` are the whole deploy pipeline — no console clicking, and the stack updates
> in place because the logical IDs are preserved. `sam build` is also what proved shapely
> packages as the correct `cp313-cp313-manylinux_2_17_x86_64` Lambda wheel before we
> depended on it.
>
> **AWS SDK for Python (boto3)** is the only AWS code in the Lambdas, wrapped in
> `common/aws.py` so clients are created lazily and cached for the container's life —
> creating a boto3 resource costs real milliseconds and a container serves many invokes.
>
> The **AWS Lambda Python 3.13 managed runtime** is what the whole backend targets, and
> `WARDS_GEOJSON_PATH` lets the same code run under `sam local` and under pytest with no
> AWS credentials at all — all 254 tests run offline.
>
> **Ship it — the AWS services**
>
> **API Gateway (HTTP API)** fronts everything, nine routes, no authorizer. One-tap
> reporting *is* the product, so abuse control is throttling, an 8 MB photo cap and strict
> server-side validation rather than a login wall.
>
> **AWS Lambda** — eight Python 3.13 functions. The interesting one is that
> **point-in-polygon runs inside the Lambda**: `wards.geojson` loads from S3 once per cold
> start into a `shapely` STRtree held at module level. 289 polygons build in ~47 ms and
> warm lookups measure 0.023 ms. We priced **OpenSearch Serverless** for this and rejected
> it — a two-OCU floor is roughly $11/day whether or not anyone queries it, which would
> have made our own cost claim false on camera, and it would have added a
> DynamoDB→OpenSearch sync problem we do not otherwise have.
>
> **DynamoDB** (on-demand) holds complaints and ward statistics, with two GSIs —
> `ward-created-index` and `status-created-index` — behind the filtered read paths. The
> magic-link status lifecycle uses **conditional writes** on the current status, so two
> people clicking the same link cannot both win.
>
> **Amazon S3** — two encrypted, public-access-blocked buckets. Photos go **straight from
> the phone to S3 via a presigned PUT** and never pass through Lambda or API Gateway, which
> keeps us under the 10 MB payload limit and costs us no compute on a large upload. Both
> `ContentType` and `ContentLength` are bound into the signature, so the URL works for
> exactly the upload that was requested. The second bucket serves the ward boundary
> GeoJSON.
>
> **Amazon SQS (+ DLQ)** sits between the API and the drafting worker. `create_complaint`
> validates, resolves the ward, writes the row, enqueues and returns `202` in about 2 ms —
> the user never waits on a model. The row is written *before* the enqueue, because the
> other order races. The worker reports `ReportBatchItemFailures`, so one bad record does
> not redeliver and redraft the whole batch, and three failures redrive to the DLQ.
>
> **Amazon Bedrock** drafts the bilingual letter through the Converse API — and is
> **optional by design, and currently switched off**. We wrote a deterministic template
> composer *first*, returning the identical `{subject, body_en, body_hi}` shape, so the
> model is a config flag rather than a dependency. Model access had not been granted inside
> our window and the organisers confirmed Bedrock is not mandatory, so `BEDROCK_ENABLED` is
> `false` and `/health` says so publicly. The adapter, the prompt, the JSON extraction and
> the IAM policy are all in the repo and tested. We would rather say this plainly than
> claim a service a judge can disprove with one GET request.
>
> **Amazon SES** delivers the drafted letter, in sandbox, to a verified demo inbox. The
> sandbox is the design, not a limitation we are working around: we **do not email real
> officials**. A `SES_LIVE` mode exists in code so the path is reviewable and is refused at
> runtime.
>
> **EventBridge Scheduler** recomputes every ward's Neglect Index hourly — hourly rather
> than daily, because a daily job may never fire inside a judging window.
>
> **CloudWatch** carries the Lambda logs and a custom `DraftSource` metric that records
> whether each letter came from Bedrock or the composer.
>
> **AWS Amplify Hosting + CloudFront** serve the React PWA over HTTPS. Lighthouse against
> the live deployment scores 100/100/100/100 on the home page and 100 on accessibility,
> best practices and SEO on every page.
>
> **IAM and CloudFormation** underneath all of it — every function gets scoped policies
> from the SAM template, never a wildcard role.
>
> Region is `ap-south-1` (Mumbai) throughout. Everything runs inside Free Tier allowances
> at demo volumes.

> **⚠️ Before submitting:** if anyone quotes a total AWS cost on camera or in a blog, pull
> the real number from Cost Explorer first. `docs/SUBMISSION.md` still has a TODO there —
> Cost Explorer returned no data while the account was under 48 hours old. Either quote the
> real figure or say nothing.

---

## 5. Contributions

> These are written from the actual commit history (`git shortlog -sne`: 29 commits,
> muneer320 21, Amrit Kang 6, Kartik Dixit 2). Judges read the commit graph — make sure
> what you paste matches what they will see. **Order these to match the order you used in
> the username/GitHub/LinkedIn blocks above.**

### Amrit Kang — team lead · ward data · frontend foundation

> Team lead and submission owner. Sourced and validated the Delhi ward boundary dataset —
> ran an acquisition ladder through ArcGIS Hub, OpenCity CKAN and OSM Overpass before
> landing on DataMeet's CC BY-SA set, then verified it rather than trusting it by running
> eleven known Delhi coordinates through the real lookup (Connaught Place and India Gate to
> NDMC, Karol Bagh to the ward actually named Karol Bagh, a Mumbai control correctly
> outside coverage). Wrote `data/prepare_wards.py`, the property-normalisation and
> geometry-validation pipeline that produces the committed `wards.geojson`. Built the
> frontend foundation: the React 18 + Vite + TypeScript + Tailwind v4 app scaffold, the
> typed API client with machine-readable error codes, and the `/ward`, `/report`,
> `/dashboard`, `/c/:id` and `/u/:token` screens with MapLibre. Caught and fixed a real
> production crash that no test had found — with the API base URL unset, requests were
> hitting the SPA fallback and getting `index.html` back with a 200, and every screen died
> on its first property access. Made the accessibility call that took three design tokens
> from failing contrast (4.18:1) to AA across the board. Chose CARTO Positron over OSM
> tiles after reading the usage policy — OSM prohibits application use, and this is a
> public URL judges click. Authored `docs/architecture.svg` and the submission writeup.

### Kartik Dixit — AWS infrastructure foundation · frontend redesign

> Authored the original `meraward-infra` SAM stack — the DynamoDB tables and their GSIs,
> the encrypted public-access-blocked buckets, the SQS queue with DLQ redrive, and the
> hourly EventBridge schedule. That foundation was sound enough that the final template
> updated it *in place* rather than replacing it: same API id, same buckets, same queue,
> and the ward GeoJSON never moved. Owned AWS account provisioning, the IAM CLI user and
> budget alerts. In the final day, took over the product's visual and interaction design:
> redesigned the complaint intake into the three-route flow (Speak / Photo / Write) that is
> the most distinctive thing in the demo, added support for text-only reports end to end,
> and built the guest-profile system — a one-click device-local `user####` alias that can
> be renamed and remembers recent reports, deliberately presented as convenience and never
> as server authentication. Also rebuilt the loading and skeleton states so the app degrades
> legibly on a slow phone.

### Muneer Alam — backend · geospatial · the Neglect Index · deployment

> Wrote the backend: all eight Lambdas and the shared `common/` core — ward geometry,
> DynamoDB access, validation, drafting, delivery, public projections and responses — plus
> the 254-test suite that specifies them, none of which needs AWS credentials. Designed the
> in-Lambda geospatial lookup: a `shapely` STRtree over 289 polygons cached at module
> level, after pricing OpenSearch Serverless at ~$11/day and rejecting it. Found and tested
> the R-tree containment bug before hitting it — the tree narrows by *bounding box*, so an
> L-shaped ward matches a point sitting in its notch, which would have shipped silently and
> shown the wrong councillor to a real user. Specified and implemented the Ward Neglect
> Index, including the two rules the project is judged on: a sub-five-report ward scores
> `None` and never `0`, and the score attaches to a ward and never to a person. Wrote the
> deterministic bilingual composer *before* the Bedrock adapter, turning the model from a
> dependency into a config flag, with tests that encode product rules — the letter is
> addressed to a ward *office*, never a person, and carries no legal threat. Built the
> magic-link lifecycle with constant-time token comparison and conditional writes, the
> presigned-upload path with `ContentLength` bound into the signature, and the SQS worker
> with idempotency and partial batch failures. Rewrote the SAM template to the API
> contract, corrected the runtime to 3.13, added the S3 CORS rule without which the browser
> PUT fails opaquely, and **deployed the whole stack** — then proved shapely actually
> imports on the real Lambda rather than assuming it. Rewrote the seed script after finding
> it generated `W###` ward ids against real `DEL-0042` ids with no coordinates — no seeded
> row would have resolved to a ward or appeared on the map — and round-tripped all 240
> replacements through the live index (240/240 resolve to their own ward). Built the
> councillor loader that matches on ward *name* rather than number, after measuring that
> joining on number agrees in only 5 of 250 cases. Wrote the documentation set: decisions
> log, credits, known issues, AWS runbook and the video script.

---

## 6. Blog links

Optional — up to four, one per member, published on **AWS Builder Center**. Top five blogs
win a Logitech keyboard, and the prizes are individual.

Three strong posts are sitting in this repo already, fully drafted in substance:

1. **"Why our point-in-polygon runs inside the Lambda"** — the OpenSearch Serverless
   costing, the STRtree, the bounding-box containment bug. Source: `LEARNING.md`,
   `docs/DECISIONS.md`.
2. **"Write the fallback before the feature"** — the deterministic composer, and how it
   turned Bedrock from a dependency into a config flag. Source: `LEARNING.md`.
3. **"The data you need often does not exist, and that is the finding"** — the ward
   boundary acquisition ladder and the pre-2022 delimitation disclosure. Source:
   `LEARNING.md`, `CREDITS.md`.

---

## 7. What you didn't like about the AWS services *(required)*

> **Amazon Bedrock — the model access and regional story is the single hardest thing we hit.**
> We never got a live draft out of it, and not for want of trying. Three separate problems
> compound. First, model access is a request-and-wait with no stated SLA, which is
> unworkable on a 30-hour clock — you cannot plan around "sometime". Second, current Claude
> models are not served regionally from `ap-south-1`, so you must go through a global
> cross-region inference profile, and *nothing in the console tells you that*. You discover
> it by getting an error from `InvokeModel` with a perfectly valid model id.
> `list-foundation-models` and `list-inference-profiles` return different things and the
> docs do not make clear which one you need — we ended up hardcoding nothing and injecting
> `BEDROCK_INFERENCE_PROFILE_ID` at deploy time purely because we could not know the value
> at write time. Third, there is no way to see what you will be granted *before* you
> request it, so you cannot pick a fallback model rationally. A "you have access to X, in
> region Y, reachable via profile Z" panel would remove the entire class of problem.
>
> **AWS Cost Explorer returns no data for an account under about 48 hours old.** For a
> hackathon this is close to a showstopper: we were asked to talk about cost on camera, and
> we could not check our own spend for the entire duration of the event. Budget alerts fire
> but Cost Explorer stays empty. Even a rough same-day figure would be better than nothing.
>
> **Amazon SES sandbox onboarding is opaque about what "verified" means.**
> `verify-email-identity` succeeds instantly and tells you nothing about the fact that you
> still cannot send to anyone else. The production-access request form asks questions
> ("describe your sending practices") that a weekend project cannot answer in the shape SES
> wants, and there is no "this is a demo, cap me at 50 emails a day" option — which is
> exactly what a hackathon needs.
>
> **Amazon S3 presigned PUT failures are invisible in the browser.** Two things bit us. If
> the bucket has no CORS rule, a browser `PUT` fails with an opaque network error and no
> S3-side signal at all — the request never reaches a place that could tell you what is
> wrong. And `content-length` must be in `AllowedHeaders` if you bind `ContentLength` into
> the signature, which is not obvious and is not mentioned near the presigning docs. Both
> cost us real time on a path where the failure message contains zero information.
>
> **OpenSearch Serverless has a two-OCU floor of roughly $11/day.** We wanted it — a
> `geo_shape` query is the textbook answer to point-in-polygon — and we could not justify a
> standing charge larger than our entire project budget for a service that would sit idle.
> A genuinely scale-to-zero tier would have won our use case outright.
>
> **API Gateway HTTP API has no built-in per-IP rate limiting.** Route-level throttling is
> global, not per client. For an intentionally unauthenticated public write path — which is
> our product decision, not an oversight — the only real answer is AWS WAF or dropping back
> to REST API usage plans, both of which are a large step up in cost and complexity for a
> small control. A simple per-source-IP burst limit on HTTP API would be widely used.
>
> **AWS SAM — two sharp edges.** `FunctionResponseTypes: [ReportBatchItemFailures]` is not
> the default on an SQS event source, and omitting it means one bad record redelivers the
> entire batch. For a worker that sends email that is a duplicate-mail bug, and the failure
> is silent. Making partial batch failures the default, or warning when a handler returns
> `batchItemFailures` without the mapping opting in, would prevent a real class of
> production bug. Separately, `samconfig.toml` is generated containing parameter values
> that are frequently secrets or personal data — ours held a teammate's email address — and
> nothing warns you before it lands next to a public repo. We gitignore it; a default
> `.gitignore` entry or a warning from `sam deploy --guided` would be better.
>
> **DynamoDB returns every number as `Decimal` through boto3**, which is correct and is
> also the classic first 500 of any DynamoDB-backed JSON API. We wrote a custom JSON
> encoder, as does everyone. A documented encoder in the SDK would save that rediscovery.
>
> **A GSI cannot be renamed in place**, and changing one in a SAM template means replacing
> the table — which, with live data in it, means losing it. We ended up making the index
> names *configuration* in our code rather than constants, bending the application to the
> infrastructure. That is the right call, but it is a workaround for a CloudFormation
> limitation that is not flagged anywhere until you try it.
>
> **AWS Amplify Hosting's manual-deploy path is far less documented than the Git-connected
> one.** `create-deployment` → upload zip → `start-deployment` works, but you assemble it
> from three API reference pages; the console and the getting-started guides assume a
> connected repository.
>
> **AWS Lambda gives you no packaging feedback until runtime.** `sam build` will happily
> package a native wheel for the wrong platform and say nothing. Our one hard dependency is
> `shapely`, which ships native `.so` files, and the only way to know it worked was to
> deploy and hit a health endpoint. `sam build` printing the resolved wheel tags — "picked
> `cp313-cp313-manylinux_2_17_x86_64`" — would turn a two-hour risk into a one-line check.

---

## 8. What you liked about the AWS services *(required)*

> **AWS SAM is the reason three people could ship this in a weekend.** One
> `template.yaml`, 300 lines, defines eight Lambdas, an HTTP API with nine routes, two
> DynamoDB tables with GSIs, two encrypted buckets, an SQS queue with DLQ redrive, an
> EventBridge schedule and every IAM policy. The thing we appreciated most was subtle:
> because we preserved the original stack's *logical IDs*, a rewritten template deployed as
> an **in-place update** — same API id, same bucket names, `wards.geojson` untouched, zero
> data loss — while changing almost every function in it. That is a genuinely excellent
> property and it let one person rewrite the whole backend without coordinating a cutover
> with anyone. `sam validate --lint` also caught real mistakes before any deploy.
>
> **The `Policies:` shorthand is the best IAM ergonomics on AWS.**
> `S3ReadPolicy: {BucketName: !Ref X}` and `DynamoDBCrudPolicy: {TableName: !Ref Y}` gave
> every one of our eight functions a correctly scoped role with no wildcard and no policy
> JSON written by hand. Least privilege that is *easier* than the insecure alternative is
> rare, and it is why we have no over-permissioned role anywhere in this stack.
>
> **AWS Lambda's Python 3.13 managed runtime, including native dependencies.** We expected
> `shapely` — C extensions, numpy underneath — to be the hard part. It packaged as the
> correct manylinux wheel and imported first try on the real runtime. Holding a parsed
> 289-polygon STRtree at module level across warm invocations gives us 0.023 ms lookups and
> costs nothing, and the CPU-scales-with-memory behaviour meant bumping to 1536 MB
> measurably shortened the cold-start index build. Serverless as the *natural* home for a
> geospatial index is not what we expected going in.
>
> **SQS partial batch failures plus DLQ redrive turned correctness into configuration.**
> `ReportBatchItemFailures` plus `maxReceiveCount: 3` gave us at-least-once delivery with
> per-record retry and a poison-message escape hatch, in about six lines of YAML. We wrote
> the idempotency check; SQS gave us everything else. The `202`-in-2ms API that this
> enables is the single best architectural property of the project.
>
> **DynamoDB conditional writes made a genuinely hard concurrency problem easy.** Our
> status lifecycle is driven by an unauthenticated magic link, so two people clicking the
> same link simultaneously is a real scenario. `ConditionExpression` on the current status
> meant exactly one wins and the other gets a clean 409 — no locks, no transactions, no
> thinking. On-demand billing meant we also never sized anything.
>
> **S3 presigned PUT is the right answer to file upload and we wish it were better
> advertised.** The photo goes phone → S3 directly, never touching Lambda or API Gateway.
> That sidesteps the 10 MB payload limit, costs us no compute on a large upload, and is
> faster on mobile data. Binding `ContentType` *and* `ContentLength` into the signature
> means the URL is good for exactly one intended upload and an 8 MB cap is actually
> enforced rather than decorative.
>
> **EventBridge Scheduler (`ScheduleV2`) is four lines for a cron job.** No rule, no target
> wiring, no permission block — `ScheduleExpression: rate(1 hour)` and it runs. For keeping
> a leaderboard live during a demo, that is exactly the right amount of ceremony.
>
> **API Gateway HTTP API** was the right default: cheaper and dramatically simpler than
> REST API, with payload format 2.0 giving a clean event shape, and CORS configured
> declaratively in the template instead of per-route OPTIONS handlers.
>
> **Amplify Hosting + CloudFront gave us HTTPS, a global CDN and a working URL for free,
> with no configuration.** Our home page scores 100/100/100/100 on Lighthouse mobile
> against the live deployment — we did the code splitting, but the delivery layer was free.
>
> **Amazon Bedrock's Converse API, even though we shipped with it off.** The API shape is
> genuinely good: one request format across model families, so the adapter we wrote is
> ~60 lines and swapping models is an environment variable. Being able to write, test and
> review a complete Bedrock integration *without model access* — because the interface is
> stable and documented — is what let us treat it as an upgrade rather than a blocker.
>
> **CloudWatch Logs was where every real bug was actually found**, and `PutMetricData` for
> a single custom metric (`DraftSource`: bedrock vs template) took one IAM statement and
> one call.
>
> **The Free Tier on a new account is generous enough to be invisible.** We never thought
> about cost during the build, which is the correct experience for people learning a
> platform.

---

## Pre-submit checklist

- [ ] WeMakeDevs usernames for all three members
- [ ] LinkedIn URLs for all three
- [ ] Resumes uploaded to Drive, link-shareable (gates Amazon Fast Track)
- [ ] Demo video recorded, ≤ 3:00, uploaded unlisted, verified logged-out
- [ ] Repo is public and `README.md` renders on GitHub
- [ ] **Decide the team-leader ordering and use it consistently across all four blocks**
- [ ] Real Cost Explorer figure pulled, or no cost claim made anywhere
- [ ] `docs/SUBMISSION.md` TODOs filled (video link, cost)
- [ ] Nobody on the team registered on a second team
- [ ] Set the photos bucket `AllowedOrigin` from `*` to the Amplify domain (one-line deploy)
- [ ] After the event: rotate the IAM access key that was shared over chat
