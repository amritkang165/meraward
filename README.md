# MERAWARD

### Know your ward. Route your complaint. See who's ignoring you.

A mobile-first PWA for Delhi's 250 municipal wards: find which ward you're standing in,
file a photo-backed complaint that AI drafts into a formal letter in Hindi and English,
and see a public accountability dashboard of which wards are being ignored.

**Built for:** First Commit · Bharat Builds Tour (Event 01 of 06) — WeMakeDevs × AWS Builder Center
**Track:** Ship It (deployed on AWS, public URL)
**Event window:** 17–20 September 2026

---

## Status

🚧 **Under active development during the event window.** This README is updated as we ship.

| | |
|---|---|
| Live URL | _pending deploy_ |
| Demo video | _pending_ |
| Region | `ap-south-1` (Mumbai) |

---

## The problem

Delhi has **250 municipal wards** (post-2022 MCD delimitation). Each has an elected councillor
whose remit covers exactly the things that stay broken: potholes, streetlights, garbage, drains,
waterlogging.

1. **Nobody knows their ward.** Boundaries were redrawn in 2022; most people still cite old zones.
2. **Complaints go into black holes.** Portals accept them and offer no tracking, no escalation.
3. **There is no public scoreboard.** "Which areas get ignored" stays a rumour instead of a number.

## The solution

1. **Which ward am I in?** — GPS or dropped pin → your ward, its councillor (public record), and its **Ward Neglect Index**.
2. **One-tap report** — Photo + issue type → AI drafts a formal complaint **in Hindi and English** → routed to the correct ward office, tracked publicly. No signup.
3. **Public accountability dashboard** — Delhi map with complaint heatmap, Ward Neglect Index leaderboard, live status tracking.

---

## Architecture

```
          React PWA · Amplify Hosting + CloudFront (HTTPS, global CDN)
                                  │ HTTPS / JSON
                     API Gateway (HTTP API) — no authorizer
                                  │
   ┌────────────┬─────────────────┼────────────────┬─────────────────┐
   ▼            ▼                 ▼                ▼                 ▼
ward_lookup  presign_upload  create_complaint  complaints_query  status_update
   │            │                 │                │                 │
   │            ▼                 │                │                 │
   │       S3 (photos)            │                │                 │
   ▼                              ▼                ▼                 ▼
wards.geojson (S3)          ┌──────────────────────────────────────────┐
shapely STRtree in-Lambda   │ DynamoDB: Complaints (GSI1, GSI2) · Wards │
cached on cold start        └──────────────────────────────────────────┘
                                  │
        create_complaint writes OPEN, enqueues ──► SQS ──► draft_and_send worker
                                                            Bedrock (bilingual draft)
                                                            → DynamoDB → SES → CloudWatch
        EventBridge Scheduler (hourly) ──► compute_neglect_index ──► DynamoDB Wards
```

**AWS services used:** Lambda · API Gateway · DynamoDB · S3 · SQS (+DLQ) · Bedrock ·
SES · EventBridge Scheduler · CloudWatch · Amplify Hosting / CloudFront. IaC is AWS SAM.

Point-in-polygon runs **inside the Lambda** via `shapely` + STRtree over ~250 polygons loaded
from S3 and cached at module level. A managed search cluster was considered and deliberately
rejected — see [`docs/DECISIONS.md`](docs/DECISIONS.md).

---

## Repository layout

```
backend/     Python 3.12 Lambdas + AWS SAM template      (owner: Kartik, Muneer)
frontend/    React 18 + Vite + TS + Tailwind + MapLibre  (owner: Amrit)
data/        Ward polygon prep + seed scripts            (owner: Muneer)
docs/        PRD, decisions log, architecture            (all)
```

---

## Local setup

_Filled in as each surface lands. See `backend/README.md` and `frontend/README.md`._

Environment variables are documented in `.env.example` (never commit a real `.env`).

---

## Data & demo-mode disclaimer

> **Complaint data on the deployed demo is generated for demonstration.**
> Every seeded record carries `is_demo = true` and the UI says so on screen.

- The **Ward Neglect Index scores a ward, never a person.** Councillor details, where shown, are
  identity only (name, party, source) as public record, and are visually separated from the index.
- Councillor fields we could not source render as an explicit "not available" badge. **We never
  invent councillor data.**
- Email delivery defaults to a **demo Outbox + a verified demo inbox**. We do **not** send
  unsolicited AI-drafted mail to real public officials.
- Ward boundary sources, licences and the basemap provider are listed in [`CREDITS.md`](CREDITS.md).
- Full provenance and index methodology live on the deployed `/about` page.

---

## AI tools used

Per the hackathon rules, AI coding tools are permitted **if disclosed**. We used them heavily.

| Tool | Used for |
|---|---|
| Claude (Anthropic) — Claude Code / claude.ai | PRD review and rewrite, architecture critique, scaffolding, Lambda handler drafts, code review, README and docs |
| Amazon Bedrock | **Runtime product feature**, not a build tool — drafts the bilingual complaint letter (see `backend/src/draft_and_send`) |

All architectural decisions, scope cuts, service choices and the final code were reviewed and
accepted by the team. Commit history is unmodified: no force-pushes, no squashes, no rewritten
commit dates.

---

## Team — Sleepy peeps (`4T5AKB`)

| | Role |
|---|---|
| **Amrit Kang** ([@amritkang165](https://github.com/amritkang165)) | Team lead · frontend · ward data |
| **Kartik Dixit** | AWS infrastructure · SAM · delivery pipeline |
| **Muneer Alam** ([@Muneer320](https://github.com/Muneer320)) | Backend Lambdas · geospatial · index + seed data |

## Licence

[MIT](LICENSE)
