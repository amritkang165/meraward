# MERAWARD — Product Requirements Document

> [!IMPORTANT]
> **This is the planning document, written before the build. It is kept as the record
> of intent, not as a description of the current system.**
>
> For what actually exists, read [`../README.md`](../README.md); for why it ended up
> that way, read [`DECISIONS.md`](DECISIONS.md). Where this document and the code
> disagree, **the code and its tests are correct.**
>
> Version 1 of this PRD was deleted in the documentation audit: it described an
> architecture we deliberately did not build (OpenSearch, Cognito, Transcribe) and
> misled anyone reading `docs/`. It remains in git history at commit `b7578b2`.

### Know your ward. Route your complaint. See who's ignoring you.
**Event:** First Commit · Bharat Builds Tour (Event 01 of 06) — WeMakeDevs × AWS
**Track:** SHIP IT (deployed on AWS, public URL)
**Team:** Sleepy peeps — Amrit Kang (leader), Kartik Dixit, Muneer Alam · Team code `4T5AKB`
**PRD version:** 2.0 — Saturday, Sept 19 2026
**Hard deadline:** Sunday, Sept 20, ~8:00 PM IST. **The form closes. There is no grace period.**

---

## 0. READ THIS FIRST — WHAT CHANGED FROM v1 AND WHY

v1 was a good plan for a team with 44 hours that had already started. Reality as of now: **no repo, no code, no AWS resources, Bedrock access not granted, ~30 hours left.** v1's plan spans 12 AWS services. That plan does not survive contact with the clock.

v2 cuts the service count roughly in half and hardens the parts judges actually score. Every cut is a deliberate trade, not an oversight.

| # | v1 said | v2 says | Why |
|---|---|---|---|
| C1 | OpenSearch `geo_shape` for point-in-polygon | **CUT.** `shapely` + STRtree inside the Lambda | 250 polygons is a few MB. OpenSearch Serverless has a **2-OCU floor (~$0.24/OCU-hr ≈ $11/day)** — v1's "$0–1" estimate was wrong, and would have made the "under $10" claim in the demo video false *on camera, to AWS judges*. Cutting it also deletes the DynamoDB→OpenSearch sync problem (v1's F-12) entirely. |
| C2 | Cognito email auth on `POST /complaints` | **CUT.** Anonymous reporting | The pitch is "one-tap complaint." v1 put a signup wall in front of it and would have burned ~20s of a 180s video on a login screen. Removes a service, an authorizer, and a whole frontend flow. |
| C3 | Transcribe `hi-IN` voice notes in the P0 pipeline | **DEMOTED to P1.** Hindi is delivered by *drafting in Hindi*, not transcribing it | v1 contradicted itself: F-7 called Hindi "decorative," but the pipeline ran real Transcribe jobs and the video hinged on a Hindi voice note. Transcribe batch adds a job-polling state machine and 20–45s of latency against v1's own 60s target. Bedrock drafting in Hindi *and* English is a better demo, costs one extra prompt, and makes the bilingual claim real. |
| C4 | SES emails real councillors | **DEMO MODE by default.** Generated → queued → shown in an in-app Outbox → delivered to verified team inboxes | Two blockers. (a) SES production access takes 24h+ and it is already Saturday; in sandbox you can only send to **verified identities**, and v1's mitigation ("pre-verify councillor addresses") is impossible — the councillor must click the verification link. (b) Even if it worked, blasting AI-drafted complaints at real named officials from a hackathon demo is spam. See §12. |
| C5 | "Neglect Score" on a card next to a real councillor's name | **"Ward Neglect Index" — scores the ward, never the person** | v1's own rule was "never fake councillor data," but it then attached a score computed from **150–300 fabricated complaints** to a real, named, elected individual. That is the same problem wearing a hat. Ward-level framing keeps the product fully intact and removes the risk. |
| C6 | Score formula | **Rewritten** (§13) | v1's formula was dominated by its middle term, unbounded, and normalized by city-max so one outlier flattened everyone else. Worse: a ward where nobody uses the app scored **0 — i.e. "perfect."** And v1's "one-sentence explanation" did not describe the formula printed directly above it. A judge finds this in 30 seconds. |
| C7 | `anthropic.claude-3-5-sonnet` in `ap-south-1` | **Global cross-region inference profile, model ID verified at runtime** (§11) | Current Claude models are not served regionally from `ap-south-1`; India access goes through Bedrock **global CRIS** profiles. v1's model ID is stale and the regional assumption is wrong — it would have failed on first invoke. |
| C8 | MapLibre + raw OSM tiles ("no API keys, no billing") | **A basemap provider whose terms permit app use** (§10.2) | `tile.openstreetmap.org`'s usage policy prohibits app/production use. A public URL that judges click is exactly the case it prohibits. |
| C9 | Nominatim reverse geocoding | **CUT.** Show ward name + "near your pin" | Same class of problem (usage policy, 1 req/sec), and the address string adds nothing to the demo. |
| C10 | 250 wards with verified councillor emails | **Polygons are P0; councillor contact is not** (§10) | Follows from C4 — we are not emailing real officials, so their addresses leave the critical path. This is the biggest unlock in the rewrite: it removes v1's highest-risk dependency from the blocking path. |
| C11 | Best UI prize unmentioned | **Named as an explicit secondary goal** (§9) | There is a dedicated **₹1,00,000 Best UI prize.** v1's risk table said "Amrit cuts visuals first." A map + heatmap + index dashboard is genuinely competitive there — it is your second-best win path and v1 treated it as ballast. |
| C12 | Rules compliance unaddressed | **New §4** | The rules name **disqualifying** offenses v1 never mentions: commit history predating the event, and undisclosed AI tooling. You are using AI agents (v1 §17 is literally an agent brief). That must appear in the writeup. |
| C13 | Video recorded Sunday 2–4 PM | **A complete rough cut exists by T-12; re-record only if time allows** (§14) | The video is its own judging criterion, and v1 scheduled it after everything else, at peak exhaustion, with 4 hours of margin. This is the most common way good hackathon projects score badly. |
| C14 | Sleep: 4 hours, then Amrit works ~40h straight | **Two protected sleep blocks, staggered** (§14) | Amrit owns final scope calls *and* narrates the video. v1 had the highest-leverage person making judgment calls at hour 38. |

**Golden rule (unchanged, and it is literally the scoring criterion):** if it is P1 or P2 and you are behind, **cut it**. One feature that runs beats five that almost do.

---

## 1. WHERE WE WERE WHEN THIS WAS WRITTEN

> *Historical. Retained because the plan below only makes sense against it.*

- Repo: **did not exist.** Creating it was task #1 (§4 — DQ risk).
- AWS: **nothing provisioned.** Bedrock model access **not granted**.
- SES: assume **sandbox**. Design for it.
- Code: **zero lines.**
- Time: **~30 hours**, of which ~7 must be sleep and ~4 must be submission work.

**Where things actually stand now is in [`../README.md`](../README.md).** Briefly: the
backend and frontend are complete with 245 passing tests, 289 real ward polygons are
committed, and deployment is the remaining blocker. Bedrock turned out to be optional —
the organisers confirmed on 2026-09-18 that only deploying on AWS is required.

---

## 2. PROBLEM

Delhi has **250 municipal wards** (post-2022 MCD delimitation). Each has an elected councillor whose remit covers exactly the things that stay broken: potholes, streetlights, garbage, drains, waterlogging.

1. **Nobody knows their ward.** Boundaries were redrawn in 2022; most people still cite old zones. There is no simple "which ward am I in?" tool on current data.
2. **Complaints go into black holes.** Portals accept them and offer no tracking, no escalation, no consequence. People tweet into the void instead.
3. **There is no public scoreboard.** No ward-level public data on open complaints or resolution speed exists, so "which areas get ignored" stays a rumour instead of a number.

**Result:** the same pothole survives three monsoons, and accountability requires knowing who to ask — which nobody does.

## 3. SOLUTION — MERAWARD

A mobile-first PWA with three connected surfaces:

1. **Which ward am I in?** — GPS or dropped pin → your ward, its councillor (public record), and its **Ward Neglect Index**.
2. **One-tap report** — Photo + issue type → AI drafts a formal complaint **in Hindi and English** → addressed to the correct ward office, tracked publicly. No signup.
3. **Public accountability dashboard** — Delhi map with complaint heatmap, Ward Neglect Index leaderboard, live status tracking.

**Pitch:** *Accountability shouldn't require knowing who to blame. Now it doesn't.*

### 3.1 What "done" means
| # | Criterion | Proof |
|---|---|---|
| G1 | Pin drop → ward + Neglect Index renders in < 3s | Screen recording |
| G2 | Photo + issue type → bilingual drafted complaint in the app in < 20s, and in the Outbox | Screen recording |
| G3 | Dashboard: Delhi map, heatmap, leaderboard, 150–300 clearly-labelled demo complaints | Screenshots + live URL |
| G4 | Status lifecycle OPEN → ACKNOWLEDGED → RESOLVED with timestamps | Screen recording |
| G5 | Public HTTPS URL on AWS, working on a real phone on mobile data | Judges click it |
| G6 | 3-min video on YouTube, **AWS visibly on screen**, captions on | Submitted |
| G7 | Public repo, commit history entirely inside the event window, AI tooling disclosed | Submitted |

### 3.2 Judging criteria → how we score them
| Criterion | How we hit it |
|---|---|
| **Idea & Impact** | Civic accountability; every judge has a pothole story; Delhi-specific and current |
| **AWS Integration** | Lambda, API Gateway, DynamoDB, S3, SQS, Bedrock, SES, EventBridge, CloudWatch, Amplify/CloudFront — fewer services than v1, each genuinely load-bearing, each **shown on screen**. The rules require AWS to be *demonstrated in the video*, not merely named in the writeup. |
| **Learning** | `LEARNING.md`, one substantive entry per person, written **as you go**, not Sunday night. Feeds the video and the blog post. |
| **Execution** | One bulletproof loop. Seeded, clearly-labelled data so nothing is ever empty. |
| **Demo Video** | §16 script. Rough cut exists by T-12. |

### 3.3 Non-goals — do not build
Multi-city · real municipal portal API integration · payments · comments/social · native apps · SMS · automated reply detection · admin panel · user accounts · **unsolicited email to real officials (§12)**

---

## 4. RULES COMPLIANCE — DISQUALIFICATION RISKS

Read once, act on it, then never think about it again.

| Rule | What we do |
|---|---|
| **Projects begun before the event do not qualify, even if rewritten. Mismatched commit history is a disqualifying offense.** | Create the repo **now**, fresh. First commit inside the event window. **Never force-push, never squash history, never rewrite commit dates.** All three of you commit under your own accounts — "what gets judged is what you added during the event," and three contributors in the graph is the evidence. Copy no code from any pre-existing project of ours. |
| **AI coding tools are permitted *if listed in the writeup*.** | We use AI agents heavily (§18). Put a plain `## AI tools used` section in the README **and** in the submission writeup: which tools, for what. Omitting this is the cheapest possible way to lose. |
| **Public repo required.** | Public from the first commit. Not private-then-flipped at the end. |
| **Demo video: max 3 minutes, on YouTube, public or unlisted.** | Upload early, grab the link, confirm it plays logged-out in an incognito window. v1's "≤100MB" constraint was invented — the real constraint is YouTube. |
| **AWS usage must be demonstrated in the video.** | §16 puts real AWS console / CloudWatch footage on screen. An architecture diagram alone does not satisfy this. |
| **Writeup must cover problem, build, and AWS integration.** | §17 checklist. |
| **One submission per team, one team per person.** | Confirm none of the three of you is registered on another team. |
| **AWS Builder Center student verification is required to compete.** | **All three, confirmed done, in the first hour.** v1 buried this in a Sunday checklist. If someone is unverified, find out now — not at 7 PM Sunday. |
| Attribution and licensing for anything external | `CREDITS.md`: ward boundary data source + licence, basemap provider, any library with attribution requirements. |

---

## 5. SCOPE

### P0 — the product. All of it must work.
| ID | Feature | Notes |
|---|---|---|
| F-1 | Ward lookup by GPS / dropped pin | `shapely` STRtree point-in-polygon in Lambda; polygons from S3, cached at module level on cold start |
| F-2 | Ward card | Ward no., name, zone, Ward Neglect Index + band, open/resolved counts; councillor block **only where sourced** (§12) |
| F-3 | Report flow | Photo (S3 presigned PUT) → issue type → submit. **No login.** Reporter email optional, used only for their tracking link |
| F-4 | Bilingual AI draft | Bedrock returns strict JSON `{subject, body_en, body_hi}`. Shown to the user and **editable** before anything is sent |
| F-5 | Outbox + delivery | Complaint queued to a visible in-app **Ward Outbox**; SES delivers to a verified demo inbox in demo mode. The mode is stated in the UI, not buried (§12) |
| F-6 | Public dashboard | Delhi map + complaint heatmap + Neglect Index leaderboard + filters (issue type, status) |
| F-7 | Status lifecycle | OPEN → ACKNOWLEDGED → RESOLVED via magic-link token, no auth wall |
| F-8 | Complaint detail page | Photo, bilingual draft, status timeline, ward context. This is the shareable artifact |

### P1 — only once P0 is green end-to-end on the deployed URL
| ID | Feature |
|---|---|
| F-9 | Voice note → Transcribe `hi-IN` → feeds the draft |
| F-10 | Rekognition auto-label on the photo, shown as a confidence chip |
| F-11 | Neglect Index 30-day trend + "most improved ward" badge |
| F-12 | OG share cards for WhatsApp |

### P2 — cut list. Touch only if everything is green by T-8.
Weekly email digest · clustered markers · councillor response-rate stat · real SES production sending

---

## 6. ARCHITECTURE

```
                 ┌───────────────────────────────────────────────┐
                 │  React PWA · Amplify Hosting + CloudFront      │
                 │  HTTPS, global CDN, mobile-first              │
                 └───────────────────┬───────────────────────────┘
                                     │ HTTPS / JSON
                           API Gateway (HTTP API) — no authorizer
                                     │
   ┌──────────────┬──────────────────┼──────────────────┬──────────────────┐
   ▼              ▼                  ▼                  ▼                  ▼
ward_lookup   presign_upload   create_complaint   complaints_query   status_update
   │              │                  │                  │                  │
   │              ▼                  │                  │                  │
   │         S3 (photos)             │                  │                  │
   │                                 ▼                  ▼                  ▼
   ▼                          ┌─────────────────────────────────────────────┐
wards.geojson                 │  DynamoDB                                    │
(S3 → in-Lambda               │   Complaints  PK complaint_id                │
 shapely STRtree,             │     GSI1 ward_id + created_at                │
 cached on cold start)        │     GSI2 status  + created_at                │
                              │   Wards       PK ward_id (stats + councillor)│
                              └─────────────────────────────────────────────┘
                                     │
                create_complaint writes OPEN, enqueues ──► SQS
                                                            │
                                                            ▼
                                                  draft_and_send worker
                                             Bedrock (bilingual JSON draft)
                                                  → DynamoDB update
                                                  → SES (demo inbox)
                                                  → CloudWatch metric
                                     │
   EventBridge Scheduler (hourly) ──► compute_neglect_index ──► DynamoDB Wards
```

### Why these choices (judges ask — have the answer ready)
| Decision | Choice | Why |
|---|---|---|
| Geospatial | `shapely` STRtree in Lambda, polygons on S3 | 250 polygons ≈ a few MB; an R-tree query is sub-millisecond. A managed search cluster for this is cost and ops we cannot afford in 30 hours. **Honest engineering beats an impressive-sounding service that might be down at demo time.** |
| Async | **SQS** between the API and the AI draft | Bedrock + SES take seconds; the user should not wait on them. The API returns `202` immediately, the worker does the slow part, the UI polls. Retries and a DLQ come free. This is the best architecture decision in the project — say so on camera. |
| Compute | Lambda, no containers | Zero idle cost, generous free tier, scales through a demo-video traffic spike |
| IaC | SAM only | One deploy path, one owner, `sam local` for dev |
| Records | DynamoDB | Access patterns known exactly; two GSIs cover every dashboard query; 25GB free tier |
| Dashboard aggregation | Query GSI, aggregate in Lambda, cache 60s | It is 300 complaints. That is a `for` loop, not a search cluster. |
| Auth | **None on the write path** | One-tap *is* the product. Abuse control = API Gateway throttling + per-IP rate limit + photo size cap |
| Hosting | Amplify Hosting + CloudFront | Connect the repo once, HTTPS included, Ship It points |
| Region | `ap-south-1` (Mumbai) | Latency for Indian judges. Bedrock reached via global CRIS (§11) |

---

## 7. DATA MODEL

### 7.1 DynamoDB — `Complaints`
| Attr | Type | Notes |
|---|---|---|
| `complaint_id` | S (PK) | `CMP-{ulid}` |
| `ward_id` | S | `DEL-0042` · GSI1 PK |
| `created_at` | S | ISO8601 · GSI1 SK, GSI2 SK |
| `status` | S | `OPEN` / `ACKNOWLEDGED` / `RESOLVED` · GSI2 PK |
| `draft_status` | S | `PENDING` / `DRAFTED` / `SENT` / `FAILED` — what the UI polls |
| `issue_type` | S | `POTHOLE` / `STREETLIGHT` / `GARBAGE` / `WATER` / `OTHER` |
| `lat`, `lng` | N | pin location |
| `photo_key` | S | S3 key |
| `subject` | S | Bedrock output |
| `body_en`, `body_hi` | S | Bedrock output, user-editable before send |
| `is_demo` | BOOL | **seeded rows are `true`. Never omit this.** (§12) |
| `delivery_mode` | S | `DEMO_OUTBOX` / `SES_VERIFIED` / `SES_LIVE` |
| `status_token` | S | random UUID (v1 said "HMAC" in the API spec and "UUID" in the data model — it is a UUID) |
| `reporter_email` | S? | optional; used only for the tracking link |
| `ses_message_id` | S? | |
| `resolved_at` | S? | |

### 7.2 DynamoDB — `Wards`
`ward_id` (PK) · `ward_name` · `zone` · `councillor_name?` · `party?` · `councillor_contact?` · `contact_source?` · `neglect_index` · `index_band` · `open_count` · `resolved_count` · `median_open_age_days` · `median_resolution_days` · `index_updated_at`

Every councillor field is **nullable**, and `contact_source` is mandatory whenever any of them is populated. Missing data renders as an explicit "not available" badge — never blank, never guessed.

### 7.3 `wards.geojson` (S3)
FeatureCollection. Each feature carries `properties.ward_id`, `ward_name`, `zone`; geometry `Polygon`/`MultiPolygon`, WGS84, simplified to ≤500 points. Loaded once per cold start into an STRtree keyed by `ward_id`.

---

## 8. API SPEC (API Gateway HTTP API, stage `prod`)

Base: `https://<api-id>.execute-api.ap-south-1.amazonaws.com/prod` · **No authorizer anywhere.**

| Method | Path | Lambda | Purpose |
|---|---|---|---|
| `GET` | `/wards/lookup?lat=&lng=` | `ward_lookup` | → ward + Neglect Index + councillor block |
| `GET` | `/wards/{ward_id}` | `ward_lookup` | ward detail page data |
| `POST` | `/complaints/presign` | `presign_upload` | → `{upload_url, photo_key}` for S3 PUT |
| `POST` | `/complaints` | `create_complaint` | `{photo_key, issue_type, lat, lng, reporter_email?}` → `202 {complaint_id, status_token}` |
| `GET` | `/complaints/{id}` | `complaints_query` | detail + status timeline + `draft_status` (UI polls this) |
| `GET` | `/complaints?bbox=&status=&issue_type=` | `complaints_query` | map data |
| `GET` | `/leaderboard` | `complaints_query` | wards ranked by Neglect Index |
| `POST` | `/complaints/{id}/status` | `status_update` | `{token, new_status}` magic-link update |
| `GET` | `/health` | `health` | uptime ping — **give it a real Lambda**; v1's table left it with none |

### `GET /wards/lookup` response
```json
{
  "ward_id": "DEL-0042",
  "ward_name": "Sadar Bazar",
  "zone": "City-SP Zone",
  "neglect_index": 53,
  "index_band": "MODERATE",
  "index_basis": { "open": 23, "resolved": 41,
                   "median_open_age_days": 61, "median_resolution_days": 34 },
  "councillor": { "name": "...", "party": "...",
                  "contact": null, "contact_source": "MCD election results 2022" },
  "data_notice": "Complaint data on this deployment is demo data. See /about."
}
```
`councillor` is `null` in its entirety when we have not sourced it. The frontend renders "Councillor details not available for this ward" — never an empty card.

### `create_complaint` (fast path, must stay under ~1s)
1. Validate input; reject photos > 8MB and malformed coords
2. Point-in-polygon → `ward_id` (shared module with `ward_lookup`)
3. Write DynamoDB item: `status=OPEN`, `draft_status=PENDING`, `is_demo=false`
4. Enqueue `{complaint_id}` to SQS
5. Return `202 {complaint_id, status_token}`

### `draft_and_send` worker (SQS-triggered, slow path)
1. Read complaint from DynamoDB
2. **Bedrock Converse** → strict JSON `{subject, body_en, body_hi}`. System prompt: formal, respectful, first-person citizen complaint, references ward name and issue type, **no legal threats, no accusations against any named individual**
3. Update DynamoDB: `subject`, `body_en`, `body_hi`, `draft_status=DRAFTED`
4. Deliver per `delivery_mode` (§12) → `draft_status=SENT`; emit a CloudWatch metric
5. On failure: `draft_status=FAILED` + templated fallback body so the UI is never empty. SQS retries twice, then DLQ

---

## 9. FRONTEND (Amrit) — *and the ₹1,00,000 Best UI prize*

There is a dedicated **Best UI prize**. Given a map, a heatmap, and an index dashboard, this is a realistic second win path. **Treat UI quality as a scored deliverable, not as slack to cut.** The cut order when behind is: P1 features → dashboard filters → animation polish. **Never** the core visual quality of the three P0 screens.

### 9.1 Stack
React 18 + Vite + TypeScript + Tailwind · MapLibre GL JS · TanStack Query · React Router · `vite-plugin-pwa`

### 9.2 Routes
| Route | Content |
|---|---|
| `/` | Hero + "Find my ward" CTA, live index ticker, 3-step how-it-works, dashboard link |
| `/ward` | Map with draggable pin → ward card, Neglect Index gauge, "Report an issue" CTA |
| `/report` | 3 steps: ① issue type cards ② photo capture ③ review the bilingual draft (EN/HI tabs, editable) → submit → processing → success with tracking link |
| `/dashboard` | Full map + heatmap toggle, leaderboard table, filters |
| `/c/:id` | Complaint detail: photo, bilingual draft, status timeline, ward context |
| `/u/:token` | Magic-link status update: Acknowledge / Resolve / Still broken |
| `/about` | **Data provenance page** (§12) — sources, licences, demo-data disclosure, methodology |

### 9.3 UI decisions
- Mobile-first; bottom-sheet ward card; touch targets ≥44px
- Neglect Index shown as a **banded gauge** (red / amber / green) with the band word, never a bare number
- **EN/HI tabs on the draft are real content, not a decorative toggle** — this is what C3 buys us
- Every empty state is designed. Nothing is ever blank
- Persistent, unobtrusive demo-data notice on dashboard and ward cards (§12)

### 9.4 States to never forget
Loading skeletons · geolocation denied → manual pin · upload failure retry · `draft_status=PENDING` processing screen · `FAILED` fallback · offline banner

### 9.5 Device note
**Record and test the demo on Android Chrome.** iOS Safari's `MediaRecorder` and camera-capture behaviour is the kind of thing that eats two hours you do not have.

---

## 10. DATA ACQUISITION — TIMEBOXED, WITH A GUARANTEED FLOOR

**This is still the riskiest dependency, but C10 shrank it: only polygons block the build.**

### 10.1 Ward polygons — **hard timebox: 90 minutes**
Work the ladder top-down. At the 90-minute mark, **take whatever rung you are on and move on.** Log the decision in `DECISIONS.md`. Do not keep hunting; a coarser real boundary beats a perfect one that arrives at midnight.

1. An open government / civic-data source publishing MCD ward boundaries as GeoJSON or Shapefile
2. OpenStreetMap via Overpass (`admin_level` ward relations for Delhi) — coverage varies, **eyeball every polygon on a map before trusting it**
3. Community-maintained Indian boundary datasets on GitHub (check the licence, record it in `CREDITS.md`)
4. **Guaranteed floor:** Delhi's 70 assembly constituencies or 11 districts. Coarser, but real, well-mapped, and universally available. The product works identically — the unit is just bigger, and we say so plainly.

**Never invent a boundary.** Real-and-coarse beats fake-and-precise, every time.

### 10.2 Basemap tiles
Do **not** point MapLibre at `tile.openstreetmap.org` — its usage policy prohibits app use, and this is a public URL judges will click. Use a provider whose free tier permits it (MapTiler, Protomaps, Carto, or Amazon Location Service). Attribute it in-map and in `CREDITS.md`. **Verify tiles load from the deployed URL, not just localhost**, before the video.

### 10.3 Councillor identity — **P1, non-blocking**
Names and parties from 2022 MCD election results are public record; populate what you can verify against two sources, set `contact_source`, and leave the rest null. **Contact emails are explicitly not required** — we are not sending to them (§12). Do not spend blocking time here.

### 10.4 Seed complaints
150–300 rows, plausible locations inside real ward polygons, timestamps 10–120 days old, mixed statuses, realistic issue-type distribution. **Every seeded row carries `is_demo = true`**, and the UI surfaces it (§12). Judges understand demo data; they do not forgive an empty dashboard, and they do not forgive being misled about which is which.

---

## 11. AWS CONFIGURATION (Kartik)

| Item | Config |
|---|---|
| Region | `ap-south-1` (Mumbai) |
| **Bedrock** | **Request model access in the first 15 minutes.** Current Claude models are *not served regionally* from `ap-south-1` — reach them through a **global cross-region inference profile**. Do not hardcode v1's `anthropic.claude-3-5-sonnet`; it is a stale ID and the regional assumption is wrong. Run `aws bedrock list-inference-profiles --region ap-south-1` and `aws bedrock list-foundation-models --region ap-south-1`, put the **exact profile ID you actually see** in an env var, and read it from config. Preference order: **Claude Haiku 4.5** (cheapest, more than good enough for a two-paragraph complaint letter) → Claude Sonnet 5 if credits allow → **Amazon Nova Lite** as the fallback (Amazon's own models typically clear access fastest). Call it via boto3 `bedrock-runtime` **Converse**. |
| **Bedrock hard fallback** | If access has not landed by **T-20**, ship the deterministic template composer (§11.1) and swap in Bedrock the moment access arrives. **The product must be demoable without Bedrock.** |
| SQS | Standard queue + DLQ (maxReceiveCount 3), Lambda event source, visibility timeout ≥ 6× worker timeout |
| SES | Sandbox assumed. Verify the 3 team inboxes + a `meraward-demo@` address as identities **immediately** (verification is instant, useful either way). Submit the production-access request too — free to ask, do not plan on it. See §12 |
| S3 | `meraward-photos-<acct>`: CORS for presigned PUT, block public ACLs, photos served via presigned GET. `meraward-data-<acct>`: `wards.geojson`. Lifecycle: photos expire 30 days |
| DynamoDB | On-demand billing. `Complaints` (+GSI1, GSI2), `Wards` |
| EventBridge | Scheduler `rate(1 hour)` → `compute_neglect_index`. **Hourly, not daily** — a daily job may never fire inside the demo window, and v1 would have shipped a score that was stale or absent on camera |
| Lambda | Python 3.12. `shapely` via a Lambda layer or container-free wheel — **verify it imports on Lambda in hour one**; a manylinux wheel mismatch is a classic 2-hour sink |
| CloudWatch | Log groups with 7-day retention; one custom metric (`ComplaintsDrafted`) + a tiny dashboard. **Cheap AWS-integration points and it is B-roll for the video** |
| Amplify Hosting | GitHub `main`, `npm ci && npm run build`, output `dist/`. SPA rewrite rule (`/<*>` → `/index.html`) or every deep link 404s |
| Budgets | Alerts at $5 and $10 |

**Cost estimate (the weekend):** Lambda ~$0 · DynamoDB on-demand ~$0 · S3 < $0.10 · SQS ~$0 · Bedrock Haiku ~$0.20 · SES ~$0 · Amplify/CloudFront ~$0 · CloudWatch ~$0. **Total well under $2.** With OpenSearch cut (C1), the "under $10 on Free Tier" line in the video is now *true* — that is the whole point of that cut. Verify actual spend in Cost Explorer before recording, and quote the real number.

### 11.1 Template composer (the Bedrock-free fallback)
A pure-Python function mapping `(issue_type, ward_name, date)` to a formal complaint in EN and HI from hand-written templates. **Write it first, in 20 minutes, before touching Bedrock.** It guarantees F-4 ships, gives the worker something to fall back to on `FAILED`, and makes the Bedrock integration a strict upgrade instead of a single point of failure.

---

## 12. DATA INTEGRITY & ETHICS — NON-NEGOTIABLE

Two problems v1 created for itself. Both are cheap to fix now and expensive to be caught on.

### 12.1 We do not email real officials
Unsolicited AI-drafted complaints sent to real named public officials, from demo data, by a weekend project, is spam — regardless of intent. SES sandbox makes it impossible anyway (C4). So:

- **`DEMO_OUTBOX` is the default and the demo mode.** The complaint is drafted, queued, and rendered in a real in-app **Ward Outbox** with recipient, subject, and full bilingual body — showing exactly what *would* be sent.
- SES sends a real email to a **verified demo inbox** (`SES_VERIFIED`), so the demo shows a genuine inbox and the SES integration is real. The recipient line reads `Ward 42 Office (demo recipient)`.
- `SES_LIVE` exists in the code as a config flag and is **off**. Say on camera: *"Routing is real and the email is real; in this deployment it goes to a demo inbox rather than to officials, because a hackathon demo shouldn't put unsolicited mail in a public servant's inbox."* That sentence earns more credit than pretending otherwise — it shows judgment.

### 12.2 We score wards, not people
The Neglect Index is computed from demo data. Attaching a number derived from fabricated complaints to a real, named, elected individual is defamation-shaped, and v1 did exactly that while telling itself it did not fake data.

- The index belongs to the **ward**. Labels, copy, and the video all say "Ward 42's Neglect Index," never "Councillor X's score."
- The councillor block is **identity only** — name, party, source — presented as public record, visually separated from the index.
- Every index display carries a demo-data marker. The `/about` page states: sources and licences, that complaint data is generated for demonstration, the index methodology in full, and how to report a data error.
- **The video never shows a real councillor's name next to a bad score.** Use a ward number.

This costs about 40 minutes and removes the only question in this project that could go genuinely badly in a judging room.

---

## 13. WARD NEGLECT INDEX (replaces v1's formula)

Three bounded sub-scores, 0–100 each, fixed anchors, higher = worse.

```
B  Backlog    = 100 × open / (open + resolved)
S  Staleness  = 100 × min(median_open_age_days, 90) / 90
L  Sloth      = 100 × min(median_resolution_days, 60) / 60      [resolved > 0 only]

WNI = round(0.40·B + 0.40·S + 0.20·L)          when resolved > 0
WNI = round(0.50·B + 0.50·S)                   when resolved = 0

if (open + resolved) < 5:  WNI = null → display "Not enough reports yet"
```

Bands: `0–29 LOW` · `30–59 MODERATE` · `60–100 HIGH`

**Why this and not v1's:**
- **Rates, not counts.** v1's index was an unbounded sum, so it mostly measured ward population and app adoption. A judge asks "doesn't a busy ward just look bad?" and v1 has no answer.
- **The minimum-sample rule fixes the worst bug.** Under v1, a ward with zero complaints scored 0 — the *best possible* score. The wards nobody reports were ranked as the best-run wards.
- **Fixed anchors (90d, 60d), not city-max.** v1 divided by the city maximum, so one outlier compressed every other ward toward zero, and scores were not comparable across time.
- **The one-line explanation now matches the formula:** *"How many reports are still open, how long those have been waiting, and how slow past fixes were."* Under v1 that sentence described something the formula did not compute.

Show `index_basis` (the four raw numbers) next to the gauge. Explainability is the feature.

---

## 14. SCHEDULE — T-MINUS FROM NOW

Times are hours before the 8:00 PM Sunday deadline. **Convert to wall-clock and pin it in the group chat right now.** Assume ~30 hours; if you have less, cut from the bottom of P0 upward.

### Block A — First 90 minutes · ALL THREE, TOGETHER, NO EXCEPTIONS
Nothing else starts until these are done:
1. **Repo created public, first commit pushed, all three with write access** (§4 — DQ risk)
2. **All three Builder Center student verifications confirmed** (§4)
3. **Bedrock model access requested** (§11) — it is a waiting game, start the clock
4. **SES: verify 4 identities**, submit the production request
5. Kartik: `sam init` → HelloWorld deploys end-to-end → Amplify connected to repo, blank app live on HTTPS
6. Muneer: confirm `shapely` **imports on deployed Lambda**. Not locally. On Lambda
7. Amrit: start the 90-minute polygon timebox (§10.1)

**Gate A:** a public URL exists and a deployed Lambda returns JSON. If this is not true in 2 hours, the problem is the toolchain — fix it before writing any features.

### Block B — T-26 → T-20 · Core loop
- **Muneer:** template composer (§11.1) → `ward_lookup` + point-in-polygon → `create_complaint` + SQS enqueue
- **Kartik:** SAM template complete (all Lambdas, both tables, SQS+DLQ, S3, IAM) → `draft_and_send` worker skeleton → SES send to verified inbox
- **Amrit:** polygons finalized and uploaded → `/ward` page with map + pin + ward card

**Gate B (T-20): ward lookup works on the deployed URL from a phone.** If not, drop to the §10.1 floor immediately and log it.
**Also at T-20: Bedrock decision.** Access granted → wire it. Not granted → ship the template composer and stop waiting.

### Block C — T-20 → T-14 · Complete the loop
- **Muneer:** Bedrock bilingual draft (or composer) → worker end-to-end → `complaints_query` + leaderboard aggregation
- **Kartik:** `compute_neglect_index` + hourly EventBridge → seed script → **run it** → CloudWatch metric + dashboard
- **Amrit:** `/report` flow (3 steps + polling) → `/c/:id` detail page

**Gate C (T-14): full loop works on the deployed URL. Photo → draft → Outbox → dashboard → status update.**

### Block D — T-14 → T-12 · **THE VIDEO GATE**
> **A complete 3-minute rough cut exists at T-12. Not a plan for one. A file.**

Record whatever works right now, narration and all. It will be imperfect. It does not matter — from this moment you have a submittable artifact, and every remaining hour is upside instead of risk. This single rule is the difference between the project you built and the score you get.

**Sleep block 1: Amrit sleeps T-12 → T-6** (must be rested to narrate and make final calls).

### Block E — T-12 → T-6 · Polish (Kartik + Muneer)
- Dashboard heatmap + leaderboard visual quality (§9 — **Best UI**)
- `/about` provenance page (§12)
- Bug burn-down: **P0 bugs only**. Everything else goes in a `KNOWN_ISSUES.md` you never open again
- `LEARNING.md` written properly. `CREDITS.md`, `DECISIONS.md`
- Blog post draft for AWS Builder Center
- **Sleep block 2: Kartik + Muneer sleep T-9 → T-5**

### Block F — T-6 → T-2 · Submission (Amrit leads, rested)
- Re-record the video **only if the rough cut is genuinely weak** — otherwise re-cut the existing footage
- Upload to YouTube, unlisted, captions on, **verify it plays logged-out in incognito**
- Writeup: problem → solution → AWS integration → impact. **Include the AI-tools disclosure** (§4)
- Architecture diagram exported as an image
- README final: setup, architecture, demo-data disclaimer, AI tools, credits, team
- Full QA on the live URL from a phone on **mobile data**, not wifi
- Publish the blog post, link it

### Block G — T-2 → T-0 · **SUBMIT AT T-2**
Submit with two hours to spare. Then, if there is time, improve and resubmit if the form allows. **Never approach the deadline with an unsubmitted form.** Once it closes, it closes.

**Slack: ~4 hours, spread across the gates.** v1 budgeted one hour across 44, which is not slack, it is optimism.

---

## 15. RISKS

| Risk | Likelihood | Mitigation |
|---|---|---|
| **Bedrock access never arrives** | **High** | Template composer written first (§11.1). Product is fully demoable without it. Nova Lite as a faster-approving alternative |
| Ward polygons unusable | Medium | 90-minute timebox + guaranteed floor (§10.1). Never fake a boundary |
| `shapely` won't import on Lambda | Medium | **Verified in Block A**, before any dependency on it |
| SES stuck in sandbox | **Near-certain** | Already the design (§12). It is a feature we narrate, not a failure we hide |
| Basemap tiles blocked from the deployed origin | Medium | Provider with app-permitting terms (§10.2); verified from the deployed URL, not localhost |
| S3 presigned PUT CORS | **High** — it gets everyone | Budget an explicit hour. Test the browser PUT early, in Block B, not at T-8 |
| Amplify SPA deep links 404 | Medium | Rewrite rule in Block A |
| Time overrun | High | Gates A–C are real stop-and-cut decisions, not checkpoints to slide past |
| Video never gets made properly | **This is the one that actually kills projects** | The T-12 video gate (Block D) |
| Fatigue degrades final-hours judgment | High | Staggered sleep; Amrit rested for the submission block |
| DQ on commit history or AI disclosure | Low but **fatal** | Block A item 1; §4 |

---

## 16. DEMO VIDEO SCRIPT (3:00 — judges score this, and only this, as the demo)

The rules require AWS to be **demonstrated on screen**. Budget real console footage.

- **0:00–0:18 · Hook.** An 8-month-old pothole tweet, zero replies. *"This pothole has been on the internet for eight months. Nothing happened — because nobody knows whose job it is to fix it."*
- **0:18–0:50 · The reveal.** Delhi map, drop a pin. Ward card rises: ward number, zone, a red gauge — Neglect Index 74, with the four raw numbers beside it. *"250 wards. Every Delhiite lives in one. Almost nobody knows which. Now it takes three seconds — and the ward comes with a number."*
- **0:50–1:35 · The loop.** Phone: photograph a pothole, tap the issue type. Processing. The drafted complaint appears — **tap the Hindi tab, show the same complaint in Hindi**. Cut to the Outbox, then to a real inbox showing the received email. *"Photo, one tap. AI drafts a formal complaint in Hindi and English, addressed to the right ward. It's real email — in this deployment it goes to a demo inbox, not to officials, because a hackathon shouldn't put unsolicited mail in a public servant's inbox."*
- **1:35–2:10 · Accountability.** Dashboard: heatmap across Delhi, leaderboard scrolling. One complaint flips to RESOLVED and the index ticks down. *"Every report is public. Every ward gets an index — how many reports are still open, how long they've waited, how slow past fixes were. 'Which ward gets ignored' stops being a rumour and becomes a number."*
- **2:10–2:45 · The build — AWS on screen.** Architecture diagram, then **real console footage**: the SQS queue draining, the CloudWatch metric ticking up, the Lambda log of a Bedrock draft, the Cost Explorer number. *"API Gateway to Lambda. SQS so the user never waits on the AI. Bedrock drafts it, SES sends it, DynamoDB and EventBridge keep the index live. Point-in-polygon runs inside the Lambda — 250 polygons didn't need a search cluster."* **Quote the real cost figure.**
- **2:45–3:00 · Learning + close.** One second each: *"First time I'd shipped a queue-backed pipeline." / "First SAM deploy." / "First Bedrock structured output."* End card: URL, repo, team, 5 seconds.

**Production notes:** real Android device, 1080p, **captions on** (judges may watch muted), music low. **Never show a real councillor's name beside a bad index** (§12).

---

## 17. SUBMISSION CHECKLIST

- [ ] Public repo, history entirely inside the event window, all three contributing, never force-pushed
- [ ] **`## AI tools used` in README and in the writeup** — DQ risk if omitted
- [ ] Public HTTPS URL, tested on a phone on mobile data
- [ ] Video ≤ 3:00, on YouTube, public/unlisted, **verified playing logged-out**, captions on, AWS visible on screen
- [ ] Writeup: problem → solution → **AWS integration** → impact
- [ ] Architecture diagram image
- [ ] README: setup, `.env.example`, architecture, **demo-data disclaimer**, AI tools, team
- [ ] `LEARNING.md` — one substantive entry per person
- [ ] `CREDITS.md` — boundary data source + licence, basemap provider, libraries
- [ ] `/about` page live (data provenance + index methodology)
- [ ] Blog post published on AWS Builder Center + linked
- [ ] All three Builder Center student verifications confirmed
- [ ] **Submitted by T-2 (6:00 PM), not T-0**

---

## 18. AI AGENT CONTEXT BLOCK (paste verbatim into a coding agent's system prompt)

> You are building MERAWARD, a civic-tech PWA for the WeMakeDevs × AWS "First Commit" hackathon (Ship It track, deadline Sunday Sept 20 2026 8 PM IST, team of 3, Delhi only, ~30 hours total). Problem: Delhi's 250 MCD wards each have an elected councillor, but citizens don't know their ward, complaints go nowhere, and there is no public ward-level accountability data. Solution: (1) GPS/pin → ward + Ward Neglect Index, (2) photo + issue type → AI-drafted bilingual (Hindi + English) formal complaint, queued to a visible Outbox and delivered by SES, publicly tracked, (3) public dashboard with map heatmap + ward index leaderboard.
>
> Stack: React 18 + Vite + TypeScript + Tailwind + MapLibre on Amplify Hosting/CloudFront; Python 3.12 Lambdas behind API Gateway HTTP API with NO authorizer; DynamoDB `Complaints` (PK complaint_id, GSI1 ward_id+created_at, GSI2 status+created_at) and `Wards` (PK ward_id); SQS + DLQ between the API and the AI draft worker; S3 for photos (presigned PUT) and for `wards.geojson`; **point-in-polygon runs in-Lambda via shapely STRtree — there is NO OpenSearch and no search cluster**; Bedrock Converse for the bilingual draft; SES for delivery; EventBridge hourly index recompute; CloudWatch metrics; region ap-south-1; IaC is SAM only.
>
> Bedrock: do NOT hardcode a model ID. Current Claude models are not served regionally from ap-south-1 — use a global cross-region inference profile, discovered at build time via `aws bedrock list-inference-profiles`, read from an env var. Prefer Claude Haiku 4.5; fall back to Amazon Nova Lite. If Bedrock access is unavailable, use the deterministic template composer — the product must be fully demoable without Bedrock.
>
> Ward Neglect Index (0–100, higher = worse, ward-level ONLY, never attached to a named person): B = 100×open/(open+resolved); S = 100×min(median_open_age_days,90)/90; L = 100×min(median_resolution_days,60)/60. WNI = 0.40B + 0.40S + 0.20L, or 0.50B + 0.50S when resolved = 0. If (open+resolved) < 5, WNI is null and the UI shows "Not enough reports yet."
>
> P0 only: ward lookup, report flow (presign → S3 → DynamoDB → SQS → Bedrock draft → SES), dashboard map + leaderboard, status lifecycle via magic-link token, complaint detail page. P1: Transcribe voice notes, Rekognition labels, index trends. NEVER build: auth/signup, SMS, payments, multi-city, native apps, comments/social, OpenSearch, Cognito.
>
> Hard constraints: no user accounts anywhere; total AWS cost under $10 and the figure must be true; seeded complaints carry `is_demo = true` and the UI must disclose it; NO invented councillor data — null fields render as explicit "not available" badges; the Neglect Index attaches to the ward, never to a named individual; email delivery defaults to a demo Outbox + verified demo inbox and must NEVER send to real officials' addresses. Prefer one bulletproof flow over breadth. When in doubt, cut scope and report the cut.

---

*End of PRD v2.0. v1 lives in git history at `b7578b2`. Further changes go in [`DECISIONS.md`](DECISIONS.md) as timestamped one-liners.*
