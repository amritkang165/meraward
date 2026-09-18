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

- **2026-09-19 · Ward polygons** — Acquisition timebox closed at ~25 minutes, well inside the
  90-minute budget. Ladder worked top-down:

  1. *Open government / civic portals* — the ArcGIS Hub "Delhi Ward Boundary 2022" item returns
     `Item does not exist or is inaccessible` from both the `opendata.arcgis.com` and
     `hub.arcgis.com` export endpoints. OpenCity's CKAN API returns only Census 2011 tables for
     Delhi wards, no boundary geometry.
  2. *OSM Overpass* — a query for `admin_level` 8/9/10 relations inside Delhi returned nothing
     usable; Delhi's municipal wards are not consistently mapped as administrative relations.
  3. *Community datasets* — **taken.** DataMeet's `Municipal_Spatial_Data/Delhi/Delhi_Wards.geojson`,
     CC BY-SA 2.5 IN, 290 features, WGS84, all polygons.

  Verified rather than assumed: eleven known Delhi coordinates were resolved through the actual
  `WardIndex`. Connaught Place and India Gate land in NDMC, Karol Bagh resolves to the ward
  literally named Karol Bagh, Delhi Cantonment resolves to the Cantonment Board, and a Mumbai
  control coordinate correctly falls outside coverage. 289 wards load in ~47 ms; warm lookups
  measure 0.023 ms.

- **2026-09-19 · Ward polygons are the PRE-2022 delimitation** — The dataset carries **272 MCD
  wards**, not the **250** created by the 2022 unification and re-delimitation. We could not find
  the post-2022 boundaries published as usable open data inside the timebox.

  We ship it, and label it precisely: `/about` and `CREDITS.md` state the delimitation and the
  retrieval date. We do **not** claim it is current. The alternative rungs were coarser units
  (70 assembly constituencies, or 11 districts) — real but less useful; this is real, complete,
  and finer, and its only flaw is its vintage, which we disclose.

  **This changes one line of the pitch.** The problem statement said "boundaries were redrawn in
  2022 and nobody knows their new ward." We cannot demo current wards, so the honest framing is
  the stronger one anyway: the current ward boundaries of a city of 20 million are not readily
  available as open data, which is itself an instance of the accountability gap the product is
  about. Say that on camera rather than around it.
