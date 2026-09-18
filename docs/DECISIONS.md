# Decisions log

Timestamped one-liners. Append only. This is the record of *why*, so we can answer
"why did you do it that way?" without reconstructing it from memory.

Times are IST.

---

- **2026-09-19 · Repo** — Repository created public under `amritkang165/meraward` at the start of
  work, inside the event window. History will never be force-pushed, squashed or date-rewritten;
  all three members commit under their own GitHub accounts.

- **2026-09-19 · Geospatial** — Point-in-polygon runs in-Lambda via `shapely` + STRtree over
  polygons loaded from S3 and cached at module level, instead of a managed search cluster.
  ~250 polygons is a few MB and an R-tree query is sub-millisecond; OpenSearch Serverless has a
  2-OCU floor (≈$11/day) that would have made our cost claim false on camera. It also deletes the
  DynamoDB→OpenSearch sync problem entirely.

- **2026-09-19 · Auth** — No authentication on the write path. "One-tap complaint" *is* the
  product; a signup wall contradicts the pitch. Abuse control is API Gateway throttling,
  per-IP rate limiting and a photo size cap.

- **2026-09-19 · Async** — SQS sits between the API and the AI draft worker. Bedrock and SES take
  seconds; the user should not wait on them. The API returns `202` immediately and the UI polls.
  Retries and a DLQ come free.

- **2026-09-19 · Bedrock** — Model ID is **not hardcoded**. Current Claude models are not served
  regionally from `ap-south-1`; access goes through a global cross-region inference profile
  discovered at deploy time and read from an env var. A deterministic template composer is written
  **first** so the product is fully demoable without Bedrock.
  _Confirmed by the organisers on 2026-09-18: Bedrock is **not mandatory**; only deploying on AWS is._

- **2026-09-19 · Ethics** — The Neglect Index attaches to a **ward**, never to a named individual.
  Email delivery defaults to a demo Outbox plus a verified demo inbox; `SES_LIVE` exists as a
  config flag and is off. We do not put unsolicited AI-drafted mail in a public servant's inbox.

- **2026-09-19 · Index** — The PRD's §8 example response was internally inconsistent: it showed
  `neglect_index: 74` against `index_basis` values (open 23, resolved 41, median open age 61,
  median resolution 34) that compute to **53 / MODERATE** under §13's own formula. Corrected the
  example to match the formula, since the formula is the specification and the implementation now
  has a test asserting exactly those weights. Worth knowing: a judge reading the writeup and the
  API response side by side would have found this in under a minute.
