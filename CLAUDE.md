# MERAWARD — agent handoff

Read this before touching anything. It is written for an AI agent joining the project
cold and covers what this is, how it is wired, what is already true, and the rules that
must not be broken. It is deliberately dense — every paragraph here exists because
getting it wrong would cost real time or would break something that is judged.

> Any agent works from this file — it is plain Markdown. Claude Code loads it
> automatically as `CLAUDE.md`.

---

## 1. What this is

A civic-accountability PWA for Delhi's municipal wards, built for the **First Commit ·
Bharat Builds Tour** hackathon (WeMakeDevs × AWS Builder Center), **Ship It** track.
Team "Sleepy peeps" (`4T5AKB`): Amrit Kang, Kartik Dixit, Muneer Alam.

Three surfaces:

1. **Find your ward** — GPS or dropped pin → point-in-polygon against 289 real Delhi ward
   polygons → ward, zone, councillor (where sourced), and the Ward Neglect Index.
2. **Report** — speak / photograph / type a problem → a formal complaint letter drafted
   **in Hindi and English**, shown for review and editing, routed to the right ward
   office, tracked at a public URL. **No signup, no login, no accounts anywhere.**
3. **Dashboard** — every report on a Delhi heatmap, plus wards ranked by Neglect Index.

### Live, and verified 2026-09-20

| | |
|---|---|
| App | https://main.d1s6q0cvldi6dz.amplifyapp.com |
| API | `https://9f41c4bkel.execute-api.ap-south-1.amazonaws.com` |
| Region | `ap-south-1` (Mumbai) |
| Stack | `meraward-infra` (CloudFormation, via SAM) |
| Amplify app id | `d1s6q0cvldi6dz` |
| Repo | https://github.com/amritkang165/meraward |
| Health | `/health` → `ward_index: {loaded: true, wards: 289}`, `drafting: {mode: "template"}` |
| Data | 240 seeded demo complaints + real reports (246 markers), 86 wards touched, 16 ranked |
| Tests | `python -m pytest backend -q` → **254 passed in ~1.6 s**, no AWS credentials needed |

---

## 2. Hard rules — do not break these

These are not style preferences. Three of them are in the rules this project is scored
against, and the rest would make the project indefensible in a judging room.

1. **The Neglect Index scores a WARD, never a person.** It is computed partly from
   generated demo data. `NeglectGauge` deliberately takes no councillor prop. The ward
   page shows a real councillor name *and* the index can be HIGH — the sentence separating
   the two must survive any redesign. A named councillor must never appear beside a bad
   score in the demo video either.
2. **A `null` index is not zero.** Under `MIN_SAMPLE` (5) total reports, the score is
   `None` and the UI says "Not enough reports yet". Rendering it as `0` would rank the
   wards nobody reports as the best-run in Delhi — exactly backwards.
3. **Demo-data disclosure stays visible.** `DemoNotice` on the ward card, the dashboard
   and complaint pages, plus the footer line. Every seeded row carries `is_demo: true`;
   real citizen reports never do. Unobtrusive is fine; absent is not.
4. **Unsourced councillor renders an explicit "not available"** — never a blank card,
   never a guess. `common/store.councillor_block` withholds the whole block without a
   `contact_source`. Do not paper over it in the UI.
5. **We do not email real officials.** `DELIVERY_MODE=DEMO_OUTBOX`. `SES_LIVE` exists in
   `common/delivery.py` so the path is reviewable and is **refused at runtime**. Turning
   it on requires editing that file, which is the point.
6. **Accessibility stays at 100 on every page.** Contrast ≥ 4.5:1 (three tokens were
   darkened for exactly this — `--color-ink-3` was failing at 4.18), touch targets ≥ 44px,
   focus ring intact, `prefers-reduced-motion` honoured.
7. **Never force-push, squash, or rewrite commit dates.** Mismatched commit history is a
   disqualifying offence under the hackathon rules. All three members commit under their
   own accounts.
8. **Disclose AI tooling.** The `## AI tools used` section in `README.md` and
   `docs/SUBMISSION.md` is mandatory under the rules. Do not remove it.
9. **Do not claim services that are not running.** `/health` is public. It returns
   `"drafting": {"mode": "template"}`. Saying "powered by Bedrock" / "uses Transcribe" /
   "uses Translate or Rekognition" is disprovable in ten seconds. See the do-not-say table
   in `docs/VIDEO_SCRIPT.md`.
10. **Never commit a real `.env`, `samconfig.toml`, or a teammate's personal email.**
    Already gitignored; keep it that way.

---

## 3. Architecture

```
Phone (React PWA on Amplify + CloudFront)
  │
  ├── POST /complaints/presign ──► presign_upload ──► signed S3 PUT url
  │        └── PUT photo ────────────────────────────► S3 photos bucket (direct, never via Lambda)
  │
  ├── POST /complaints ──────────► create_complaint
  │        validate → point-in-polygon (in-Lambda STRtree) → DynamoDB write
  │        → SQS enqueue → 202 in ~2 ms
  │                                     │
  │                                     ▼
  │                              draft_and_send (SQS worker, BatchSize 5)
  │                                 Bedrock Converse ──(any failure)──► deterministic composer
  │                                 → save draft (DRAFTED) → SES demo delivery
  │                                 → CloudWatch custom metric
  │
  ├── GET  /wards/lookup?lat&lng ─► ward_lookup ──► ward + Neglect Index + councillor
  ├── GET  /wards/{ward_id} ──────► ward_lookup
  ├── GET  /complaints/{id} ──────► complaints_query   (UI polls this while draft is PENDING)
  ├── GET  /complaints ───────────► complaints_query   (map markers, ≤ 2000)
  ├── GET  /leaderboard ──────────► complaints_query   (60 s per-container cache)
  ├── POST /complaints/{id}/status► status_update      (magic-link token)
  └── GET  /health ───────────────► health

EventBridge Scheduler, rate(1 hour) ──► compute_neglect_index ──► ward stats in DynamoDB
```

Rendered diagram: `docs/architecture.svg`. Sequence and state diagrams: `README.md`.

### Three decisions that explain most of the code

**Point-in-polygon runs inside the Lambda.** `wards.geojson` loads from S3 once per cold
start into a `shapely` STRtree held at module level (`common/wards.py`). 289 polygons
build in ~47 ms; warm lookups measure **0.023 ms**. OpenSearch Serverless was priced and
rejected — a two-OCU floor of ~$11/day would have made our own cost claim false, and it
would have added a DynamoDB→OpenSearch sync problem.

> **The subtle bug that is already fixed — do not reintroduce it.** An STRtree narrows
> candidates by *bounding box*, not by shape. `tree.query(point)` on an L-shaped ward
> returns that ward for a point sitting in the notch. `WardIndex.lookup` confirms real
> `geom.contains(point)` afterwards, and falls back to the first bbox touch only for a
> point exactly on a boundary. Without the containment check it returns a *plausible
> neighbouring ward* rather than an error — it would ship silently and show the wrong
> councillor to a real user.

**SQS sits between the API and the AI draft.** `create_complaint` returns `202` in ~2 ms;
the user never waits on a model. **The row is written BEFORE the enqueue** — the other
order races, because the worker can pick the message up and find nothing to draft
against. If SQS is unreachable, `create_complaint` drafts inline with the composer rather
than failing, so a complaint is never stuck on `PENDING` forever.

**Bedrock is optional by design.** `common/composer.py` — a pure, deterministic bilingual
template composer — was written *first* and returns the identical
`{subject, body_en, body_hi}` shape that Bedrock Converse returns. The model is therefore
a config flag (`BEDROCK_ENABLED` + `BEDROCK_INFERENCE_PROFILE_ID`), not a dependency.
Both are currently off/empty. **Never hardcode a Bedrock model id** — current Claude
models are not served regionally from `ap-south-1`; access goes through a global
cross-region inference profile discovered at deploy time.

---

## 4. Repository layout

```
backend/
  template.yaml            SAM — 8 Lambdas, HTTP API, 2 tables, 2 buckets, SQS+DLQ, schedule, IAM
  src/
    common/                shared core, importable from every handler
      aws.py               lazily-created, container-cached boto3 clients
      bedrock.py           Converse adapter; raises BedrockUnavailable, caller falls back
      composer.py          deterministic bilingual letter — the Bedrock-free floor
      config.py            all env reading, cached per cold start. No handler touches os.environ
      delivery.py          DEMO_OUTBOX / SES_VERIFIED / SES_LIVE(refused). The ethics live here
      ids.py               ULID complaint ids (CMP-…), UUID status tokens
      index.py             Ward Neglect Index formula + MIN_SAMPLE rule
      responses.py         HTTP API v2 responses, CORS, Decimal-safe JSON, ApiError
      store.py             DynamoDB reads/writes; councillor block with enforced provenance
      validation.py        write-path input validation (the only thing between the net and the tables)
      views.py             PUBLIC allow-list — what may leave the database. Security boundary
      wards.py             ward polygons, STRtree, point-in-polygon, module-level cache
    <fn>/app.py            one package per Lambda; handler path is <fn>.app.handler
  tests/                   254 tests, no AWS needed. These are the API specification
frontend/
  src/
    api/client.ts          fetch wrapper, ApiError with machine-readable code
    api/types.ts           mirrors the API exactly; if it disagrees with a test, the test is right
    auth/GuestAuth.tsx     device-local guest profile (NOT authentication)
    components/            MapView, ComplaintsMap, NeglectGauge, GuestIdentity, Icon, states
    lib/image.ts           client-side photo compression before upload
    routes/                one file per route
    index.css              Tailwind v4 @theme design tokens — change tokens, not components
data/
  prepare_wards.py         source GeoJSON → normalised, validated data/wards.geojson
  load_councillors.py      SEC Delhi results → ward rows, matched by NAME never by number
  seed_complaints.py       demo complaints, sampled INSIDE real polygons, is_demo=true
  wards.geojson            the committed 289-polygon set (raw/ is gitignored)
docs/
  MERAWARD_PRD.md          the spec
  DECISIONS.md             append-only log of WHY. Add to this when you make a call
  AWS_SETUP.md             account/deploy runbook
  SUBMISSION.md            the writeup
  SUBMISSION_FORM.md       field-by-field answers for the submission form
  VIDEO_SCRIPT.md          3-minute shot-by-shot script + verified-facts + do-not-say tables
  architecture.svg
CREDITS.md                 data provenance and licences. Nothing ships without an entry
KNOWN_ISSUES.md            disclosed rough edges, with severity and why each stands
LEARNING.md                one substantive entry per person — a scored criterion
```

`KARTIK-HANDOFF.md` and `AMRIT-HANDOFF.md` are gitignored local notes; they carry useful
context but are not part of the repo.

---

## 5. Running it

### Backend

```bash
python -m pip install -r backend/requirements-dev.txt
python -m pytest backend -q          # 254 tests, offline, ~1.6 s
```

`WARDS_GEOJSON_PATH` points the ward index at a local file instead of S3 — that is how
tests and `sam local` run without credentials.

### Frontend

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173
npm run build        # tsc -b && vite build
npm run typecheck    # types only, faster
```

`frontend/.env` already points at the **deployed** API, so the dev server talks to real
data. No AWS credentials, no Docker, no local backend needed to work on the UI.

### Deploying

```bash
cd backend
sam build --template template.yaml
sam deploy --stack-name meraward-infra --region ap-south-1 --profile meraward \
           --capabilities CAPABILITY_IAM --resolve-s3 \
           --parameter-overrides MerawardEmail=<ses-address> AllowedOrigin=<amplify-domain>
```

After any deploy, `GET /health` reporting `ward_index.loaded: true` is the check that
shapely imported on the real runtime.

**Amplify is not connected to GitHub** — frontend deploys are manual zip uploads
(`create-deployment` → upload → `start-deployment`, app id `d1s6q0cvldi6dz`).

The template preserves the original stack's **logical IDs**, so a deploy *updates in
place*: same API id, same bucket names, `wards.geojson` untouched. **Do not rename
logical IDs, and do not recreate the DynamoDB tables** — a GSI cannot be renamed in
place, which is why index names are configuration (`WARD_INDEX_NAME`,
`STATUS_INDEX_NAME`) rather than constants.

---

## 6. The Ward Neglect Index

`common/index.py`. Three bounded sub-scores against fixed anchors, 0–100, higher = worse.

```
B  Backlog    = 100 × open / (open + resolved)
S  Staleness  = 100 × min(median_open_age_days, 90) / 90
L  Sloth      = 100 × min(median_resolution_days, 60) / 60      [only when resolved > 0]

WNI = 0.40·B + 0.40·S + 0.20·L      when resolved > 0
WNI = 0.50·B + 0.50·S               when resolved = 0   (redistribute; never score an
                                                          unmeasured term as zero)

score < 30 → LOW    < 60 → MODERATE    else HIGH
total reports < MIN_SAMPLE (5) → score is None, band is None, note = "Not enough reports yet"
```

Rates, not counts, and **fixed anchors rather than a city maximum** — otherwise the index
mostly measures ward population and app adoption, and one outlier compresses every other
ward toward zero.

`basis` (the four raw numbers, plus components) is returned with every score and rendered
beside the gauge. **Explainability is the feature**: "what is 74 made of?" gets four
numbers, not a shrug.

**The formula exists in exactly one place.** `compute_neglect_index` recomputes hourly and
writes the four *raw inputs*; every reader recomputes the score from those. An earlier
standalone version of that Lambda had its own copy of the weights — two implementations of
one formula is a drift bug waiting to happen. Do not reintroduce a second copy.

---

## 7. The API contract

The tests in `backend/tests/` are the specification. `frontend/src/api/types.ts` mirrors
them; if the two disagree, **the test is right**.

| Route | Function | Notes |
|---|---|---|
| `GET /health` | `health` | public; reports ward index + drafting mode + delivery mode |
| `GET /wards/lookup?lat=&lng=` | `ward_lookup` | **GET with query params**, `wards` plural |
| `GET /wards/{ward_id}` | `ward_lookup` | path param must be named `ward_id` |
| `POST /complaints/presign` | `presign_upload` | `{content_type, content_length}` |
| `POST /complaints` | `create_complaint` | `202`; returns `status_token` |
| `GET /complaints/{id}` | `complaints_query` | path param is `id`, not `complaint_id` |
| `GET /complaints?bbox=&status=&issue_type=&ward_id=` | `complaints_query` | map markers, ≤ 2000 |
| `GET /leaderboard` | `complaints_query` | 60 s per-container cache |
| `POST /complaints/{id}/status` | `status_update` | `{token, action}` |

Enums: `IssueType` = POTHOLE · STREETLIGHT · GARBAGE · WATER · OTHER.
`ComplaintStatus` = OPEN · ACKNOWLEDGED · RESOLVED.
`DraftStatus` = PENDING · DRAFTED · SENT · FAILED.
`IndexBand` = LOW · MODERATE · HIGH.

Errors carry a stable machine-readable `code` alongside a human `message`. The frontend
branches on the code.

### Security boundaries worth knowing before you edit

- **`common/views.py` is an allow-list, not a deny-list.** A field added to the table
  later is private by default and must be named there to become public. Three attributes
  must never leave the database: `status_token` (publishing it on the page it controls
  would make the lifecycle forgeable by anyone), `reporter_email`, and `ses_message_id`.
- **`validate_photo_key` accepts only keys we issue** (`photos/YYYY/MM/DD/<26-char
  ULID>.<ext>`). Without it an unauthenticated caller could attach any object in the
  bucket to a complaint.
- **`require_evidence`**: photo and description are each optional so voice, photo and
  written reports each work — but a complaint with neither is not a report.
- **Status tokens are compared with `secrets.compare_digest`.** A plain `==` leaks the
  prefix through timing on a public endpoint.
- **Status transitions are conditional writes** on the current status, so two people
  clicking the same magic link cannot both win. Clicking the same link twice lands on
  `changed: false`, not an error.
- **Reopening clears `resolved_at`**, so the ward's counts — and its index — tell the
  truth again after a fix that did not hold. "Somebody marked this resolved and it
  wasn't" is the accountability signal the product exists to capture.

---

## 8. Data provenance — read before touching anything in `data/`

- **Ward boundaries are the PRE-2022 delimitation**: 272 MCD + 9 NDMC + 8 Cantonment =
  289 usable polygons, from **DataMeet**, **CC BY-SA 2.5 IN**. Delhi's corporations were
  unified in 2022 and re-delimited to 250 wards. We could not find the post-2022
  boundaries published as usable open data. **We ship it and label it precisely** — never
  claim it is current. The attribution is required in-app by the ShareAlike licence and
  appears on `/about`.
- **Councillors are matched by ward NAME, never by ward number.** The councillor list is
  post-2022 (250 wards); our boundaries are pre-2022. Joining on `ward_number` agrees with
  the ward name in only **5 of 250 cases** — it would attach a real, named, elected person
  to a ward they do not represent 98% of the time. Coverage is **155 of 288**; the rest
  render "not available". Every populated record carries a `contact_source` stating both
  the source and that the match was by name. Without `contact_source` the API withholds
  the whole block, so a name can never be published unattributed.
- **Councillor data is name and party only.** No contact details — we do not email
  officials.
- **Basemap is CARTO Positron**, which permits application use with attribution and needs
  no API key. **Do not switch to `tile.openstreetmap.org`** — its usage policy prohibits
  application use, and this is a public URL judges click.
- **Nothing ships without an entry in `CREDITS.md`.**

---

## 9. What is deliberately NOT here

Do not "fix" these — each is a decision with a reason in `docs/DECISIONS.md`.

- **No authentication anywhere.** One-tap reporting *is* the product; a signup wall
  contradicts the pitch. Abuse control is API Gateway throttling, an 8 MB photo cap and
  strict validation. The guest profile in `auth/GuestAuth.tsx` is a device-local alias for
  convenience and is deliberately not presented as server authentication.
- **Bedrock is off** (`BEDROCK_ENABLED=false`). A supported state, not a gap.
- **SES stays in sandbox.** The design, not a limitation being worked around.
- **No OpenSearch / managed search cluster.** Priced and rejected.
- **No marker clustering** on the dashboard — the heatmap covers that case.
- **No load balancers or connection pooling** — serverless, and DynamoDB is HTTP.
- **Non-goals from the PRD:** multi-city, real municipal portal integration, payments,
  comments/social, native apps, SMS, admin panel, user accounts, and unsolicited email to
  real officials.

Known rough edges with severity and rationale live in `KNOWN_ISSUES.md`. Two are worth
fixing if you have time: the photos bucket `AllowedOrigin` is `*` and should be the
Amplify domain (a template parameter, so a one-line deploy), and the IAM access key that
was shared over chat should be rotated after the event.

---

## 10. Working conventions

- **Tests are the spec.** Changing an API shape means changing `backend/tests/` first.
  Some tests encode *product rules*, not behaviour — two composer tests assert the letter
  is addressed to a ward **office** and never a person, and that it carries no legal
  threat. Those exist to stop that constraint quietly eroding at 4am. Do not weaken them.
- **Design tokens, not components.** Colours live in `frontend/src/index.css` under
  `@theme` (Tailwind v4). Change the tokens and the whole app moves.
- **Lazy-load anything heavy.** Routes use `React.lazy`; `vite.config.ts` has a
  `manualChunks` map. MapLibre is 801 kB, is chunk-split, excluded from service-worker
  precaching, and preconnect-hinted. `/ward` scores 69 and `/dashboard` 76 on Lighthouse
  performance because the map is the LCP element — that is the floor for a map page, not a
  defect. Do not regress the other scores.
- **Append to `docs/DECISIONS.md` when you make a real call**, with the date and the why.
- **Update `KNOWN_ISSUES.md` in the same commit** as anything it covers.
- **Conventional commit prefixes** (`feat(backend):`, `fix(frontend):`, `docs:`, `chore:`,
  `test(backend):`) matching the existing history.
- Test the mobile UI on **Android Chrome** — voice capture and camera behave there; iOS
  Safari's camera is its own afternoon.

### Facts to keep straight

- **Voice input is the browser's Web Speech API** (`SpeechRecognition` /
  `webkitSpeechRecognition` in `routes/Report.tsx`). **Not Amazon Transcribe.** Transcribe,
  Translate and Rekognition are not used at all.
- **Hindi comes from the composer/Bedrock prompt**, not Amazon Translate.
- **HEIC photos upload uncompressed** — browsers cannot decode HEIC into a canvas, so
  `lib/image.ts` falls back to the original file. Deliberate: failing to compress must
  never mean failing to report.
- **`/u/:token` needs the complaint id as `?id=`.** The token authorises but does not
  identify.
- **Most wards have no index** (70 of 86 seeded wards are under the five-report minimum),
  so "Not enough reports yet" is the common case, not the edge case. Design for it.
- **The worst ward is Model Town, index 100, HIGH** — useful for testing the red band.
- **Real data is live in dev**, so `/dashboard` shows ~246 markers and 16 ranked wards.

---

## 11. Outstanding work

- [ ] **Demo video** — script is complete at `docs/VIDEO_SCRIPT.md` with a verified-facts
      table and a do-not-say table. 3:00 hard limit, YouTube unlisted, captions on, **real
      AWS console footage on screen** (an architecture diagram alone does not satisfy the
      rule).
- [ ] **Submission form** — answers drafted at `docs/SUBMISSION_FORM.md`; usernames,
      LinkedIn, resumes and the video link still need supplying.
- [ ] **Kartik's `LEARNING.md` entry** — one substantive entry per person is a scored
      criterion, and his section still says "_Awaiting Kartik_".
- [ ] **Amrit's `LEARNING.md` entries** are drafted from the real work in that lane and
      labelled as such; they should be rewritten in his own voice.
- [ ] **Real Cost Explorer figure** — `docs/SUBMISSION.md` has a TODO. Cost Explorer
      returned no data while the account was under 48 hours old. Quote the real number or
      make no cost claim.
- [ ] Photos bucket `AllowedOrigin`: `*` → the Amplify domain.
- [ ] Post-event: rotate the IAM access key.
