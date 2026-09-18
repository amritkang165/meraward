# MERAWARD — Product Requirements Document
### One-tap civic complaint routing + public ward accountability dashboard
**Event:** First Commit · Bharat Builds Tour (Event 01 of 06) — WeMakeDevs × AWS
**Track:** SHIP IT (deployed on AWS, public URL)
**Team:** Sleepy peeps — Amrit Kang (leader), Kartik Dixit, Muneer Alam
**Team code:** 4T5AKB
**PRD version:** 1.0 — Friday, Sept 18 2026, 11:55 PM IST
**Hard deadline:** Sunday, Sept 20, ~8:00 PM IST (~44 hours from now)

---

## 0. HOW TO USE THIS DOCUMENT

- **Humans:** Read sections 1–3 for context, section 4 for scope discipline, then your role's section (5–8), then the schedule (12). Skim the rest.
- **AI coding agents:** If you are an AI agent onboarded to build part of this project, ALSO read section 17 (Agent Context Block) verbatim — it is a condensed, self-contained briefing of everything in this file.
- **Golden rule:** If a feature is marked P1 or P2 and you are running out of time, CUT IT. P0 is the product. "One feature that runs beats five that almost do" — this is literally the judges' scoring criterion.

---

## 1. PROBLEM STATEMENT

Delhi has **250 municipal wards** (post-2022 MCD delimitation), each with an elected **Ward Committee / councillor** whose job includes local infrastructure fixes — potholes, streetlights, garbage, drains.

Yet:
1. **No citizen knows their ward number or councillor's name/contact.** Ward boundaries were redrawn in 2022; most people still reference old zones. There is no simple "which ward am I in?" tool with current data.
2. **Complaints go into black holes.** Municipal apps/portals accept complaints but offer no tracking, no escalation, no consequence. People default to tweeting into the void.
3. **Zero public accountability.** No ward-level public scoreboard of open complaints or resolution speed exists. Corporators face no data-driven public pressure.

**Result:** the same pothole survives three monsoons, and accountability requires knowing who to blame — which nobody does.

## 2. SOLUTION — MERAWARD

A web app (mobile-first PWA) with three connected surfaces:

1. **"Which ward am I in?"** — Drop a pin / use GPS → get your ward, councillor card (name, party, contact), and the ward's **Neglect Score** (public accountability metric).
2. **One-tap complaint** — Snap a photo (pothole/streetlight/garbage/water), optional Hindi voice note → AI drafts a formal complaint → routed to the correct councillor contact via email. Tracked publicly.
3. **Public accountability dashboard** — Live Delhi map: heatmap of open complaints, Neglect Score leaderboard per ward, resolution status tracking. The shareable, viral layer.

**The one-sentence pitch:** *Accountability shouldn't require knowing who to blame. Now it doesn't.*

## 3. GOALS & SUCCESS CRITERIA

### 3.1 Demo-day success (what "done" means Sunday 6 PM)
| # | Criterion | Measurable |
|---|---|---|
| G1 | Pin drop → ward + councillor card renders in < 3s | Live demo + screen recording |
| G2 | Photo + voice note → drafted complaint email visible in inbox (SES) in < 60s | Live demo |
| G3 | Dashboard shows Delhi map with heatmap + leaderboard with 150–300 seeded realistic complaints | Screenshots + URL |
| G4 | Complaint status lifecycle works: OPEN → ACKNOWLEDGED → RESOLVED, with timestamps | Live demo |
| G5 | Public URL live on AWS, HTTPS, works on a phone | Judges click it |
| G6 | 3-minute demo video recorded, scripted per section 14 | Submitted |

### 3.2 Judging-criteria mapping (design every feature to score these)
| Judge criterion | How we hit it |
|---|---|
| Idea & Impact | Civic accountability; relatable to every judge; Delhi-specific, real, current |
| Built on AWS | OpenSearch geospatial, Bedrock, Transcribe, Lambda, DynamoDB, SES, EventBridge, Cognito, S3, CloudFront, Amplify — deep but each piece simple; architecture diagram + cost analysis in submission |
| Learning | Each teammate documents 1–2 things they learned (first geospatial index, first Bedrock structured output, first SAM pipeline) — goes in the video + README |
| Execution | P0 loop is bulletproof; seeded data so nothing looks empty |
| Demo video | Follows section 14 script exactly |

### 3.3 Non-goals (explicitly OUT of scope — do not build)
- ❌ Multi-city (Delhi only)
- ❌ Real municipal portal API integration (email routing only; portal link as reference)
- ❌ Payments, donations, crowdfunding
- ❌ User-to-user comments/social features
- ❌ Native iOS/Android app (PWA only)
- ❌ Real SMS (email only)
- ❌ Automated councillor response detection (manual status updates by complainant)
- ❌ Any Hindi UI beyond a decorative toggle (see F-7)
- ❌ Admin panel beyond a simple seed/fix script

---

## 4. SCOPE — PRIORITIZED FEATURES

### P0 — THE PRODUCT (non-negotiable, must all work)
| ID | Feature | Notes |
|---|---|---|
| F-1 | Ward lookup by GPS pin / browser geolocation | OpenSearch `geo_shape` query on ward polygons |
| F-2 | Ward + councillor card | Ward no., name, zone, councillor name, party, email, phone (if available), Neglect Score, open-complaint count |
| F-3 | Complaint creation flow | Photo upload (S3 presigned), issue type picker (pothole / streetlight / garbage / water-logging / other), optional voice note (≤60s), description auto-drafted by Bedrock |
| F-4 | Complaint email routing | SES sends drafted complaint to councillor email + confirmation to complainant; complaint stored publicly |
| F-5 | Public dashboard | Delhi map (MapLibre + OSM tiles), heatmap layer of complaints, ward leaderboard by Neglect Score, complaint detail page |
| F-6 | Status lifecycle | OPEN → ACKNOWLEDGED → RESOLVED; complainant updates via emailed link (magic-link style token, no login wall) |
| F-7 | Hindi toggle button on complaint page | **Decorative only.** Renders a static sample Hindi drafted complaint. Does NOT need to function end-to-end. Judges see the vision, we skip the plumbing. |

### P1 — STRONG IF TIME (build only after P0 demo is green)
| ID | Feature | Notes |
|---|---|---|
| F-8 | Neglect Score v2 | Trend: score vs. 30 days ago; "most improved ward" badge |
| F-9 | Rekognition photo check | Auto-label photo (pothole confidence %) shown as a "smart check" chip in UI |
| F-10 | Clustered map markers at high zoom | Basic OpenSearch geo aggregation |
| F-11 | Email digest | Weekly ward digest to subscribed users (EventBridge → SES batch) |

### P2 — CUT LIST (only if everything is green by Sunday noon)
| ID | Feature |
|---|---|
| F-12 | DynamoDB Streams → OpenSearch real-time sync (replace with 60s polling for P0) |
| F-13 | WhatsApp share cards / OG images for viral sharing |
| F-14 | Councillor response-rate stat (requires reply detection — skip) |

---

## 5. TEAM & OWNERSHIP

**Guiding principle:** territories are primary ownership, not silos. Anyone may commit anywhere, but each area has ONE accountable owner.

| Person | Primary ownership | Secondary |
|---|---|---|
| **Amrit** (leader) | Frontend (React app, all screens, dashboard visualizations), demo video production, submission write-up | Data verification, complaint copy |
| **Kartik** | AWS platform: SAM template, CI/deploy pipeline, Cognito, SES, EventBridge, CloudFront/Amplify hosting, cost monitoring | OpenSearch ops, backend glue |
| **Muneer** | Backend functions (all Lambdas), Bedrock + Transcribe integration, S3 presigned flow | Neglect Score computation, seed scripts |

**Leader-only duties (Amrit):** final scope cuts, demo video narration, submission form, blog post draft (for the Logitech keyboard prize — top 5 blogs, publish on AWS Builder Center and link in submission).

### Communication & workflow
- Single GitHub repo, `main` protected, everything via PRs (review optional during crunch, mandatory for `template.yaml` and schema changes)
- Standups: 12 AM, 9 AM, 3 PM, 9 PM (15 min, camera optional, blockers only)
- Decisions logged in `/docs/DECISIONS.md` — one line each, timestamped. Judges' "Learning" criterion + your blog post source material.
- Deploys: Kartik owns `sam deploy`; nobody else touches prod AWS console directly.

---

## 6. SYSTEM ARCHITECTURE

```
                          ┌─────────────────────────────────────────────┐
                          │              USERS (mobile / desktop)        │
                          │        React PWA served via CloudFront       │
                          │   Amplify Hosting  ──  HTTPS, global CDN     │
                          └──────────────────┬──────────────────────────┘
                                             │ HTTPS / JSON
                                      API Gateway (HTTP API)
                                             │
        ┌────────────────┬───────────────────┼────────────────────┬──────────────────┐
        ▼                ▼                   ▼                    ▼                  ▼
  ┌───────────┐   ┌─────────────┐    ┌──────────────┐     ┌─────────────┐   ┌─────────────┐
  │ ward_lookup│   │ create_     │    │ complaints_  │     │ status_     │   │ presign_    │
  │ _handler   │   │ complaint   │    │ query        │     │ update      │   │ upload      │
  │ (Lambda)   │   │ _handler    │    │ _handler     │     │ _handler    │   │ _handler    │
  └─────┬─────┘   └──────┬──────┘    └──────┬───────┘     └──────┬──────┘   └──────┬──────┘
        │                │                  │                    │                 │
        ▼                ▼                  ▼                    ▼                 ▼
  ┌───────────┐   ┌──────────────────────────────────────────────────────────────┐
  │ OpenSearch│   │ Amazon DynamoDB                                              │
  │ wards idx │   │  Table: Complaints (PK: complaint_id; GSI1: ward_id+created; │
  │ (geo_shape)│  │  GSI2: status+created)   Table: Councillors (PK: ward_id)    │
  └───────────┘   └──────────────────────────────────────────────────────────────┘
        ▲                ▲
        │                │
  ┌─────┴────────────────┴──────────────────────────────────────────────────────┐
  │ Backend flow inside create_complaint (Lambda, Python):                       │
  │   S3 photo (via presigned PUT) → Transcribe (voice→text, hi-IN)              │
  │   → Bedrock Claude (draft formal complaint JSON) → DynamoDB put              │
  │   → OpenSearch index complaint (geo_point) → SES send (councillor + user)    │
  └──────────────────────────────────────────────────────────────────────────────┘
                                             │
  ┌──────────────────────────────────────────┼──────────────────────────────────┐
  │ EventBridge Scheduler (daily 06:00 IST)  ▼                                  │
  │   → compute_neglect_scores Lambda → updates ward stats in DynamoDB + OS     │
  │ Cognito (email-only login) · SES (transactional email)                      │
  └─────────────────────────────────────────────────────────────────────────────┘
```

### Architecture decisions (and WHY — judges ask this)
| Decision | Choice | Why |
|---|---|---|
| Compute | Lambda, no containers | Zero idle cost, free-tier generous, auto-scales to the demo-video traffic spike |
| IaC | SAM only (no CDK/Terraform) | One deploy path, teammate 2 owns it, `sam local` for dev |
| Geo store | OpenSearch `geo_shape`/`geo_point` | Purpose-built geospatial; "which polygon contains this point" + aggregations in one system; most teams never demo this — differentiator |
| Records store | DynamoDB | Exactly-known access patterns; GSI covers dashboard queries; free tier 25GB |
| Sync (P0) | 60s polling from frontend for dashboard freshness | Streams→OS sync is P2; polling is honest and robust |
| Auth | Cognito email-only | Free under MAU limits; no SMS/SPNs approval hell; complaint updates use signed tokens, no auth wall |
| Maps | MapLibre GL + OSM tiles | No API keys, no billing, offline-capable demo |
| Frontend hosting | Amplify Hosting + CloudFront | One command connect to repo; HTTPS included; Ship It points |

---

## 7. DATA MODEL

### 7.1 DynamoDB — Table: `Complaints`
| Attr | Type | Notes |
|---|---|---|
| complaint_id | String (PK) | `CMP-{ulid}` |
| ward_id | String | e.g. `DEL-0042` — GSI1 PK |
| created_at | String (ISO8601) | GSI1 SK |
| status | String | OPEN / ACKNOWLEDGED / RESOLVED — GSI2 PK |
| issue_type | String | POTHOLE / STREETLIGHT / GARBAGE / WATER / OTHER |
| location | {lat: N, lng: N} | pin from GPS |
| address_guess | String | reverse-geocoded (Nominatim) or "Near user pin" |
| photo_key | String | S3 object key |
| voice_key | String? | S3 key, optional |
| transcript | String? | Transcribe output |
| drafted_text | String | Bedrock output (English) |
| councillor_email | String | snapshot at send time |
| email_message_id | String | SES trace |
| status_token | String | random UUID for magic-link status updates |
| reporter_id | String? | Cognito sub (nullable — allow anonymous) |
| resolved_at | String? | |

### 7.2 DynamoDB — Table: `Councillors`
| Attr | Type | Notes |
|---|---|---|
| ward_id | String (PK) | `DEL-0001`…`DEL-0250` |
| ward_name | String | |
| zone | String | MCD zone |
| corporator_name | String | |
| party | String | |
| email | String | primary routing target |
| phone | String? | display only |
| neglect_score | Number | recomputed daily |
| open_count | Number | |
| resolved_count | Number | |

### 7.3 OpenSearch — Index: `wards`
```json
{
  "mappings": {
    "properties": {
      "ward_id":    { "type": "keyword" },
      "ward_name":  { "type": "text" },
      "zone":       { "type": "keyword" },
      "geometry":   { "type": "geo_shape" }
    }
  }
}
```
Query for F-1: `geo_shape` with `relation: intersects` on a point.

### 7.4 OpenSearch — Index: `complaints_geo`
```json
{
  "mappings": {
    "properties": {
      "complaint_id": { "type": "keyword" },
      "location":     { "type": "geo_point" },
      "issue_type":   { "type": "keyword" },
      "status":       { "type": "keyword" },
      "ward_id":      { "type": "keyword" },
      "created_at":   { "type": "date" }
    }
  }
}
```
Used for: heatmap (geo aggregation grid), ward-level counts, leaderboard aggregation.

### 7.5 Neglect Score formula (v1 — keep it explainable)
```
score = (open_complaints × 10)
      + Σ(open days for each OPEN complaint, capped at 365)
      + (resolved_avg_days × 2, if resolved_count > 0)
```
- Rounded, normalized 0–100 display scale (divide by max in city × 100).
- Must be explainable in ONE sentence in the video: *"open complaints, how long they've been open, and how slow past fixes were."*
- Computed daily by EventBridge Lambda; stored on Councillors table + denormalized to OS for sorting.

---

## 8. API SPEC (API Gateway HTTP API, stage `prod`)

Base: `https://<api-id>.execute-api.ap-south-1.amazonaws.com/prod`

| Method | Path | Auth | Lambda | Purpose |
|---|---|---|---|---|
| GET | `/wards/lookup?lat={}&lng={}` | none | ward_lookup | → ward + councillor + score |
| POST | `/complaints/presign` | Cognito | presign_upload | → `{upload_url, photo_key}` for S3 PUT |
| POST | `/complaints` | Cognito | create_complaint | body: `{photo_key, issue_type, lat, lng, voice_key?}` → starts async pipeline |
| GET | `/complaints/{id}` | none | complaints_query | detail incl. public status timeline |
| GET | `/complaints?bbox={}&status={}&issue_type={}` | none | complaints_query | map data (geo bbox filter) |
| GET | `/leaderboard` | none | complaints_query | top-N wards by neglect_score |
| POST | `/complaints/{id}/status` | HMAC token in body | status_update | `{token, new_status}` magic-link update |
| GET | `/health` | none | — | uptime ping |

### Key request/response shapes
**GET /wards/lookup** →
```json
{
  "ward_id": "DEL-0042",
  "ward_name": "Sadar Bazar",
  "zone": "City-SP Zone",
  "corporator": { "name": "...", "party": "...", "email": "...", "phone": null },
  "neglect_score": 78.4,
  "open_count": 23,
  "resolved_count": 41,
  "avg_resolution_days": 34
}
```

**POST /complaints** → `202 Accepted` with `{complaint_id, status_url}` — pipeline is async; UI shows "drafting & sending…" then polls `GET /complaints/{id}`.

**create_complaint internal pipeline (Muneer's core function):**
1. Validate input, fetch ward via lookup logic (reuse geo query)
2. If `voice_key`: invoke Transcribe job (`hi-IN`), poll ≤ 30s
3. Bedrock Converse — model `anthropic.claude-3-5-sonnet` (or whatever is enabled in ap-south-1 at build time — verify and fall back to `claude-3-haiku` for speed/cost). System prompt + user content: issue type, transcript, rough location → **strict JSON** `{subject, body}` formal complaint, respectful, references ward & issue, no legal threats.
4. Put DynamoDB item (status OPEN), index OS doc
5. SES `send_email`: to councillor email (from Councillors table), cc reporter; subject `[Meraward #{id}] {subject}`, body = drafted_text + photo link (public S3 GET URL or email attachment ≤5MB — decide: **attachment if < 5MB, else link**)
6. Store SES message id; return

---

## 9. FRONTEND SPEC (Amrit)

### 9.1 Stack
React 18 + Vite + TypeScript, Tailwind, MapLibre GL JS + `maplibre-gl`, TanStack Query for server state, React Router. PWA via `vite-plugin-pwa`.

### 9.2 Pages
| Route | Page | Content |
|---|---|---|
| `/` | Landing | Hero: pin-drop demo gif; "Find your ward" CTA; live neglect ticker strip; how-it-works (3 steps); link to dashboard |
| `/ward` | Ward card | Big map, draggable pin; on drop → councillor card + Neglect Score gauge + "Report an issue" CTA |
| `/report` | Complaint flow | 4 steps: ① issue type cards (icons) ② photo capture/upload ③ optional voice recorder (MediaRecorder API) ④ review drafted text (editable textarea) → submit → success screen with tracking link |
| `/dashboard` | Accountability | Full map + heatmap layer toggle; leaderboard table (rank, ward, councillor, open, avg days, score bar); filters: issue type, status, time range |
| `/c/:id` | Complaint detail | Photo, drafted text, status timeline, ward context, councillor card mini |
| `/u/:token` | Status update (magic link) | 3 buttons: Acknowledge / Resolve / Not fixed — no login |

### 9.3 Key UI decisions
- Mobile-first: bottom sheet pattern for ward card; touch targets ≥44px
- Neglect Score: red→amber→green gauge, NOT a raw number alone — one-glance judgment
- Photo-first complaint flow: the camera is step 2, not an afterthought (most civic reports are visual)
- Empty states are designed, never blank
- Hindi sample button (F-7) sits on step ④ of the report flow as a language toggle showing a static translated draft

### 9.4 States to never forget
Loading skeletons, geolocation denied fallback (manual pin drag), upload failure retry, complaint pipeline "processing" screen, offline banner.

---

## 10. DELHI DATA ACQUISITION PLAN (the riskiest dependency — START TONIGHT)

**Target:** 250 MCD wards with councillor identity + contact, ward boundary polygons.

### Sources (in order of reliability — verify each live):
1. **Ward boundaries (GeoJSON):** data.gov.in (search "Delhi ward boundary" / MCD delimitation datasets); Municipal GIS portals; OpenStreetMap (overpass query for `boundary=administrative` ward relations — quality varies, must eyeball)
2. **Councillor list:** MCD official site (post-2022 election results pages); Delhi State Election Commission results (sec.delhi.gov.in) — elected member names per ward are public; party from election data
3. **Contact emails/phones:** the hard part. Municipal corporation contact directories, councillor-published contact info, RTI-documented lists. **Where email is missing:** route to the ward's official MCD zone office email as fallback, and display "contact unavailable — email zone office" transparently.

### Fallback ladder (decide by Saturday 6 PM, log decision in DECISIONS.md)
1. **Full 250 wards** with polygons + councillors — goal
2. Polygons for all 250, councillors for top ~50 wards by population, rest "data coming soon" — acceptable
3. Zone-level (22 zones) polygons + zone office contacts, ward table inside — only if 1–2 collapse; demo still works
4. **Never:** fake or invented councillor data. Wrong data = credibility death in judging. Unknown = "unavailable" badge.

### Processing
- Amrit owns. Python + GeoPandas: clean polygons → validate (no self-intersections) → simplify to ≤ ~500 points/polygon (map perf) → export `wards.geojson`
- `corporators.json` hand-verified against 2 sources where possible
- Kartik bulk-indexes into OpenSearch; Muneer seeds DynamoDB Councillors table
- **Seed complaints:** 150–300 realistic complaints spread across wards (scripted generation with real-ish locations, timestamps 10–120 days old, mixed statuses) so the dashboard looks alive. Clearly mark as seed data in README/submission (judges understand demo data; they don't forgive emptiness).

---

## 11. AWS CONFIGURATION DETAILS (Kartik)

| Item | Config |
|---|---|
| Region | `ap-south-1` (Mumbai) — latency for Indian users + judges |
| Cognito | User Pool, email-only sign-in, hosted UI optional (custom minimal login screen preferred), no SMS |
| SES | Verify domain or use sandbox + verified recipient emails for demo; sandbox works if we email ONLY verified addresses during judging — **decide: request production access immediately Friday night, fallback = mailcatcher-style demo via verified addresses** |
| S3 | Bucket `meraward-photos-prod`, CORS for presigned PUT, lifecycle: delete audio after 7 days, photos after 90 |
| Bedrock | Request model access in `ap-south-1` **tonight** (approval can take hours; haiku first, sonnet if granted) |
| Transcribe | `hi-IN` medical off; standard batch jobs |
| OpenSearch Serverless | Collection `meraward`, index policies for `wards`, `complaints_geo`, encryption with AWS-owned key (hackathon simplicity) |
| EventBridge | Scheduler: `rate(1 day)` → compute_neglect_scores |
| Amplify Hosting | Connected to GitHub repo, `main` branch, build: `npm ci && npm run build`, output `dist/` |
| CloudFront | Default Amplify distribution is fine; custom domain optional |
| Budgets | AWS Budgets alert at $5 and $10 — mention in video ("we engineered for cost") |

**Cost estimate (demo weekend):** Lambda ~$0, DynamoDB ~$0, S3 < $0.10, OpenSearch Serverless ~$0–1 (OCU min — verify serverless vs small managed; if serverless OCU floor is a concern, use managed `t3.small.search` ~$0.35/hr and DELETE after event), Bedrock haiku ~$0.20, Transcribe ~$0.20, SES ~$0, Cognito free tier. **Total: $2–8. Delete the OpenSearch domain Sunday night after submissions.**

---

## 12. BUILD SCHEDULE (44 hours, Fri 11:55 PM → Sun 8 PM)

### Phase 0 — TONIGHT (Fri 11:55 PM – Sat 6 AM) · "De-risk everything"
| Time | Who | Task |
|---|---|---|
| 12:00–2:00 | Kartik | AWS: Bedrock model access request, SES verified + prod access request, Cognito pool, S3 buckets, `sam init` repo skeleton deploys `HelloWorld` end-to-end |
| 12:00–2:00 | Muneer | Repo setup, local dev env (SAM local + LocalStack optional), OpenSearch local docker for dev |
| 12:00–3:00 | Amrit | **Data hunt:** find Delhi ward polygons + councillor list; download raw files; overpass query if needed |
| 2:00–6:00 | All | Sleep. Seriously. This is a marathon; Sunday needs clear heads. |

### Phase 1 — Sat 6 AM – 6 PM · "Core backend + data"
| Time | Who | Task |
|---|---|---|
| 6–9 | Muneer | `ward_lookup` Lambda + OS geo query working with sample polygons |
| 6–9 | Kartik | SAM template complete: all 7 Lambdas stubbed, DynamoDB tables, Cognito authorizer, deploy pipeline green |
| 6–12 | Amrit | Polygon cleaning pipeline (GeoPandas) → `wards.geojson`; councillor list v1 |
| 9–12 | Muneer | Bedrock prompt + structured JSON output working in isolation (test harness script) |
| 12–3 | Muneer | `create_complaint` pipeline: presign → S3 → Transcribe → Bedrock → DynamoDB → OS index |
| 12–3 | Kartik | SES send + status token flow + `status_update` Lambda |
| 3–6 | Kartik | Bulk index wards + councillors; seed complaint generator script run → dashboard-ready data |
| 6:00 | ALL | **Checkpoint 1: P0 backend API testable via curl/Postman. Scope cut decision logged.** |

### Phase 2 — Sat 6 PM – Sun 6 AM · "Frontend + dashboard"
| Time | Who | Task |
|---|---|---|
| 6 PM–12 | Amrit | Landing + ward lookup page end-to-end (map, pin, councillor card) |
| 6 PM–2 AM | Muneer | `/dashboard` data endpoints: bbox query, leaderboard aggregation |
| 9 PM–3 AM | Kartik | Neglect Score Lambda + EventBridge schedule; wire leaderboard numbers |
| 12–6 | Amrit | Complaint flow steps ①–④ + success/polling screens |
| 3–6 | Muneer | Complaint detail + magic-link status page |

### Phase 3 — Sun 6 AM – 2 PM · "Integration, polish, seeds"
| Time | Who | Task |
|---|---|---|
| 6–10 | All | Full end-to-end on PROD URL from a real phone; bug burn-down list, P0 bugs only |
| 10–12 | Amrit | Dashboard polish, leaderboard visual, OG share card (if time), Hindi sample button |
| 10–12 | Muneer | Seed data top-up (target 200+), edge-case fixes |
| 12–2 | Kartik | Load test light (100 req), budgets alarm, architecture diagram for submission, cost summary |

### Phase 4 — Sun 2 PM – 8 PM · "Demo, video, submit"
| Time | Who | Task |
|---|---|---|
| 2–4 | Amrit | Record 3-min demo video (script §14), 2 takes, pick best; screen-record live flows as backup b-roll |
| 3–5 | All | Submission form: description, architecture write-up, learning notes, repo README polish |
| 4–6 | Muneer/Kartik | Blog post draft → publish on AWS Builder Center (keyboard prize), link in submission |
| 5–7 | Amrit | Final QA pass on live URL from phone + desktop; freeze code 7 PM |
| 7–8 | Amrit | SUBMIT. Then sleep. |

**Slack buffer:** 1 hour total. If Phase 1 checkpoint slips > 2h, immediately execute the fallback ladder (§10) and cut F-6 magic link to plain "contact us to update" — protect G1–G3, G5.

---

## 13. RISKS & MITIGATIONS

| Risk | Likelihood | Mitigation |
|---|---|---|
| Ward polygon data for Delhi is unusable/stale | Medium | Fallback ladder §10; OSM overpass; zone-level fallback; never fake it |
| Councillor emails largely unavailable | High | Zone-office fallback routing; transparency badge; phone display when known |
| Bedrock model access not approved in time | Low-Med | Request tonight; fallback to Amazon Nova models in ap-south-1; last resort: pre-drafted templates + LLM offline (cut AI drafting, keep everything else) |
| Transcribe latency slows complaint flow | Medium | Async pipeline + polling UI (already designed); cap voice at 60s |
| SES sandbox limits (verified recipients only) | High | Request prod access Friday night; demo day: councillor addresses pre-verified as identities; judges see real inbox screenshot + live send to verified test inbox |
| OpenSearch Serverless cost floor | Medium | Compare vs managed t3.small; delete resources Sunday night |
| Time overrun on frontend | Medium | Amrit cuts P1/P2 visuals first; P0 pages are 3 routes only; use Tailwind UI blocks, no custom design system |
| Team fatigue/conflict | Medium | Sleep blocks scheduled; Amrit owns final call authority; scope cuts are logged not debated at 4 AM |

---

## 14. DEMO VIDEO SCRIPT (3:00, no live demo — judges watch THIS)

- **0:00–0:20 · Hook.** Real screenshot of a pothole tweet, 8 months old, zero replies. VO: *"This pothole has been on the internet for eight months. Here's why nothing happened — nobody knows whose job it is to fix it."*
- **0:20–0:55 · The reveal.** Screen: map of Delhi. Drop a pin on a street. Ward card slides up: ward number, councillor name, party, and a red gauge — Neglect Score 78. VO: *"250 wards. Every Delhiite lives in one. Almost nobody knows which one, or who's accountable for it. Now they do — in three seconds."*
- **0:55–1:40 · The magic loop.** Phone screen: photograph a pothole, tap issue type, speak a Hindi voice note. Watch: transcript appears → AI drafts a formal complaint → *"Sent to Councillor [name]"* — cut to the actual email in the inbox. VO: *"Photo, voice note, one tap. The complaint reaches the person whose job it is — drafted, documented, and tracked."*
- **1:40–2:20 · The accountability layer.** Dashboard: heatmap glowing across Delhi, leaderboard scrolling — Ward 42: 147 open, avg 94 days. One complaint flips to RESOLVED. VO: *"Every complaint is public. Every ward gets a Neglect Score. For the first time, 'which ward gets ignored' is a number, not a rumor."*
- **2:20–3:00 · The build.** Fast architecture diagram pan, AWS service icons, cost line on screen: *"Under $10 on the AWS Free Tier — Lambda, DynamoDB, OpenSearch geospatial, Bedrock, Transcribe."* Teammate 1-second each: *"First geospatial index I'd ever built."* / *"First agent pipeline."* / *"First SAM deploy."* Close: *"Accountability shouldn't require knowing who to blame. Meraward fixes that. Try it: meraward.in"* (or actual URL).

**Production notes:** record phone screen with real device (not emulator), 1080p, captions ON (judges may watch muted), background music low, end card with URL + repo + team name for 5 seconds.

---

## 15. SUBMISSION CHECKLIST (Sunday)
- [ ] Public URL live, tested on mobile data (not just wifi)
- [ ] 3-min video ≤ 100MB, captions, ends with URL
- [ ] Description: problem → solution → AWS stack → impact (150 words)
- [ ] Architecture diagram image (from §6)
- [ ] Repo: README with setup, `.env.example`, architecture, **seed-data disclaimer**, team names
- [ ] "What we learned" — one line per teammate (judging criterion)
- [ ] Blog post on AWS Builder Center + link (keyboard prize)
- [ ] Team details + Builder Center profiles verified

---

## 16. TOOLING SUMMARY

| Layer | Tooling |
|---|---|
| Frontend | React 18, Vite, TypeScript, Tailwind, MapLibre GL, TanStack Query, vite-plugin-pwa |
| Backend | Python 3.12 Lambdas, SAM CLI, API Gateway HTTP API |
| Data | DynamoDB, OpenSearch (wards geo_shape / complaints geo_point), S3 |
| AI | Bedrock (Claude haiku→sonnet), Transcribe (hi-IN), optional Rekognition |
| Auth/Comms | Cognito (email), SES, EventBridge Scheduler |
| Hosting | Amplify Hosting + CloudFront |
| Local dev | SAM local, DynamoDB Local, docker OpenSearch for dev |
| Repo/CI | GitHub, `main` + PRs, `sam deploy` via Kartik (Amplify auto-builds frontend) |
| Regions | ap-south-1 only |

---

## 17. AI AGENT CONTEXT BLOCK (paste verbatim into any coding agent's system prompt)

> You are building MERAWARD, a civic-tech web app for the WeMakeDevs × AWS "First Commit" hackathon (Ship It track, deadline Sunday Sept 20 2026 8 PM IST, team of 3, Delhi-only scope). Problem: Delhi's 250 MCD wards each have an elected councillor, but citizens don't know their ward or councillor, complaints go nowhere, and there is no public ward-level accountability data. Solution: (1) GPS pin → ward + councillor card with a "Neglect Score", (2) photo + optional Hindi voice note → Bedrock-drafted complaint emailed to the councillor via SES and publicly tracked, (3) public dashboard with map heatmap + ward neglect leaderboard. Stack: React 18 + Vite + TS + Tailwind + MapLibre frontend on Amplify/CloudFront; Python 3.12 Lambdas behind API Gateway HTTP API; DynamoDB tables `Complaints` (PK complaint_id, GSI ward_id, GSI status) and `Councillors` (PK ward_id); OpenSearch indices `wards` (geo_shape) and `complaints_geo` (geo_point); S3 photos via presigned PUT; Cognito email-only auth; SES transactional email; EventBridge daily neglect-score recompute; region ap-south-1; IaC is SAM only. Neglect Score = open_count×10 + Σ open days (cap 365) + avg_resolution_days×2, normalized 0–100. P0 scope only: ward lookup, complaint create pipeline (presign→S3→Transcribe→Bedrock→DynamoDB→OS→SES), dashboard map+leaderboard, status lifecycle with magic-link token updates, email-only Cognito. P1: Rekognition photo check, score trends. NEVER build: SMS, payments, multi-city, native apps, comments/social. Constraints: total AWS cost < $10; everything must work on the AWS Free Tier; demo data is seeded and must be labeled as such; Hindi UI toggle is decorative only (static sample, non-functional is acceptable); no invented councillor data — use "unavailable" badges for missing data. Priorities: a bulletproof single user flow over breadth. When in doubt, cut scope and report the cut.

---

*End of PRD v1.0. Changes after Friday night must be one-liners in `/docs/DECISIONS.md` with timestamp + reason.*
