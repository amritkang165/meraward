# Known issues

Rough edges we know about and consciously chose not to fix inside the event window.
Logged so they are disclosed rather than discovered, and so we stop reopening them.

Severity is about **impact on a user or a reviewer**, not effort to fix.

## Data

| # | Issue | Severity | Why it stands |
|---|---|:---:|---|
| 1 | Ward boundaries are the **pre-2022 delimitation** — 272 MCD wards, not the 250 created by the 2022 unification. | High | The post-2022 boundaries do not appear to be published as usable open data. Disclosed in [`CREDITS.md`](CREDITS.md), on `/about`, and in the writeup. See [`docs/DECISIONS.md`](docs/DECISIONS.md). |
| 2 | **Councillor details are not populated.** Every councillor field is null. | Medium | Verifying names against two sources for 289 wards did not fit the window, and we will not publish unsourced names. The API withholds the whole block without a `contact_source`, so the UI shows an explicit "not available" rather than a blank card. |
| 3 | One source feature was dropped during preparation (no ward number). | Low | 289 of 290 features carry a usable id. The dropped one is logged by `data/prepare_wards.py` on every run. |

## Backend

| # | Issue | Severity | Why it stands |
|---|---|:---:|---|
| 4 | **Bedrock is not wired to live model access.** `BEDROCK_ENABLED` defaults to `false`. | Low | By design. The organisers confirmed Bedrock is not mandatory, and the deterministic composer produces a complete bilingual letter. Enabling it is two environment variables. |
| 5 | The leaderboard's 60-second cache is **per Lambda container**, not shared. | Low | Two concurrent containers can serve values up to 60 s apart. A shared cache is an extra service for a page that changes hourly. |
| 6 | Map queries return at most **2,000 markers**, then set `truncated: true`. | Low | Delhi's demo dataset is a few hundred rows. The cap exists so an unbounded response can never be produced. |
| 7 | An unfiltered map query does a **DynamoDB scan**. | Low | Correct at this size — it is a few hundred items, and the filtered paths use GSI1/GSI2. It would need revisiting at city-wide real usage. |
| 8 | Abuse control on the write path is **API Gateway throttling plus validation only**. | Medium | There is no authentication anywhere by design — one-tap reporting *is* the product. A per-IP limit and a photo-content check would be the next additions. |

## Frontend

| # | Issue | Severity | Why it stands |
|---|---|:---:|---|
| 9 | `/ward` and `/dashboard` score 80 and 86 on Lighthouse performance. | Low | MapLibre is 801 kB and that is the floor for a map page. It is already split into its own chunk, excluded from precaching, and never fetched by `/` or `/about` — which score 100 and 95. |
| 10 | **HEIC photos are uploaded uncompressed.** | Medium | Browsers cannot decode HEIC into a canvas, so compression silently falls back to the original file. iOS users on mobile data will have a slower upload. Failing to compress must never mean failing to report, so the fallback is deliberate. |
| 11 | `/u/:token` needs the complaint id as `?id=`. | Low | The token authorises but does not identify. The links we generate always include it; a hand-typed token alone shows a clear "incomplete link" message rather than failing obscurely. |
| 12 | Dashboard markers are **not clustered** at high zoom-out. | Low | The heatmap layer covers that case, and clustering hundreds of points buys little. It would matter at tens of thousands. |
| 13 | The reporter's magic link is kept in `localStorage`. | Low | It can be lost by clearing site data or using a private window. The link is also shown on screen at submission time. There are no accounts to recover it from — that is the tradeoff of not having accounts. |

## Deployment

| # | Issue | Severity | Why it stands |
|---|---|:---:|---|
| 14 | **SES stays in sandbox**, so email reaches verified identities only. | Low | This is the design, not a limitation we are working around. We do not send to real officials — see [`README.md`](README.md#data--demo-mode-disclaimer). |
| 15 | `shapely` has not yet been verified on a **deployed** Lambda. | **High** | It imports and runs locally, but a manylinux wheel mismatch on the Lambda runtime would break the entire geospatial path. This is the single highest-risk unknown and needs a deploy to close. |

---

Something here fixed, or something new found? Update this table in the same commit as
the change.
