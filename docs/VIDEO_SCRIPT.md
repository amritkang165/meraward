# MERAWARD — demo video script

**3:00 hard limit · YouTube, public or unlisted · captions on · AWS visible on screen**

- **Live:** https://main.d1s6q0cvldi6dz.amplifyapp.com
- **API:** `https://9f41c4bkel.execute-api.ap-south-1.amazonaws.com`
- **Repo:** https://github.com/amritkang165/meraward

Everything in quote marks is **word-for-word narration**. Read it as written; it is
timed. Total **454 words** — about **2:56** spoken at a natural pace, inside the 3:00 limit.
Section word counts are in the headings. If you run long, drop §2:36 (66 words) and you
land near 2:30.

---

## How to use the tags

Parts of the product are finished and parts are not. Every shot is tagged:

| Tag | What it means |
|---|---|
| 🎥 **FILM LIVE** | It genuinely works. Perform the interaction on camera. |
| 🖼 **SHOW ONLY** | Put the real screen on camera and talk over it. **Do not click through, do not mime a result, do not cut in a way that implies something happened.** |

The narration for 🖼 shots is written to *describe the screen*, never to claim an
outcome. Keep it that way if you change anything — describing an interface is honest;
implying it just did something is not.

### Two hard rules for this recording

1. **Never say** Bedrock, Transcribe, Translate or Rekognition are running. `/health`
   is a public endpoint and returns `"drafting": {"mode": "template"}`. A judge can
   check it in ten seconds. The honest version is scripted below and is a better story.
2. **Never show a named councillor beside a bad Neglect Index.** Pick a ward that has
   none, or stay on the gauge.

### Pre-flight — run this an hour before recording

Anything that fails becomes 🖼 **SHOW ONLY**. Adjust the tags, not the truth.

- [ ] `/ward` — drop a pin, ward card appears with the gauge
- [ ] `/dashboard` — heatmap, filters, leaderboard
- [ ] `/c/:id` — a complaint opens with both letters
- [ ] `/about` — loads
- [ ] Report → Write → submit → complaint ID appears
- [ ] Report → Photo → upload → submit
- [ ] Report → Voice → transcript *(known broken — expect 🖼)*
- [ ] Review screen — editing the text before submit

---

# THE SCRIPT

## 0:00 – 0:17 · Hook · *43 words*

🖼 **SHOW ONLY.** A real Delhi pothole, or a civic complaint tweet with no replies.
Hold three seconds. Then cut to the MERAWARD home screen on a phone.

> "Delhi has hundreds of municipal wards. Every one of them has an elected councillor
> whose job is exactly this — potholes, streetlights, garbage, drains.
>
> Almost nobody knows which ward they live in. So complaints go nowhere, and the same
> pothole survives three monsoons."

---

## 0:17 – 0:38 · About the project · *54 words*

🖼 **SHOW ONLY.** The home screen. Scroll slowly so all three entry cards are seen —
Speak, Photo, Write. **Do not tap any of them.**

> "MERAWARD is built on one idea: reporting a civic problem should feel like telling
> someone, not filling in a form.
>
> Three ways in — speak it, photograph it, type it — all arriving at the same place:
> your ward identified, a formal complaint in Hindi and English, and a public record
> anyone can follow."


---

## 0:38 – 1:10 · Find your ward · *58 words* · **the strongest live moment**

🎥 **FILM LIVE**, one unbroken take on the phone:
1. Open `/ward`
2. Drag the pin — or tap **Use my location**
3. Let the ward card rise: ward name, zone, the banded gauge, the four numbers beneath

> "This is the part that doesn't exist anywhere else. I drop a pin, and a
> point-in-polygon lookup against two hundred and eighty-nine real Delhi ward boundaries
> tells me exactly which ward I'm standing in — in about a fiftieth of a millisecond.
>
> And the ward doesn't come back with just a name. It comes back with a number."

---

## 1:10 – 1:36 · The accountability half · *49 words*

🎥 **FILM LIVE** — `/dashboard`. Toggle heatmap to points. Change one filter. Scroll the
leaderboard a little.

> "Every report is public, and every ward gets a Neglect Index: how many reports are
> open, how long they've waited, how slow past fixes were.
>
> A ward nobody reports scores nothing. Not zero — score it zero, and the most ignored
> wards look like the best-run in the city."

---

## 1:36 – 1:58 · The complaint itself · *56 words*

🎥 **FILM LIVE** — open an existing complaint at `/c/:id`. Tap the **हिन्दी** tab so the
letter switches language on camera.

> "Here's a filed complaint. A formal letter to the ward office in English — and the
> same letter in Hindi. With the photo, the location, and a status timeline: reported,
> acknowledged, resolved."

🖼 **SHOW ONLY** — the review screen from the report flow. Hold it still, about three
seconds. Do not type into it.

> "And this screen is the reason the flow exists: before anything is filed, the citizen
> sees exactly what will go out in their name."

---

## 1:58 – 2:36 · Tech stack, architecture, AWS on screen · *84 words*

🖼 **SHOW ONLY** — `docs/architecture.svg` for four seconds, then cut to the **real AWS
console footage** from the shot list below, changing shot roughly every six seconds.

> "React and MapLibre on Amplify, behind CloudFront. API Gateway into eight Python
> Lambdas, DynamoDB for state, S3 for photos and boundaries.
>
> SQS sits between the API and the drafting worker, so the API answers in two
> milliseconds and nobody waits on the slow part. EventBridge recomputes the index
> hourly, CloudWatch watches everything, and the whole stack is one SAM template.
>
> The point-in-polygon runs inside the Lambda. We priced a managed search cluster at
> eleven dollars a day and decided we did not need one."

---

## 2:36 – 2:52 · What we would defend, and what is next · *66 words*

🖼 **SHOW ONLY** — the `/about` page, scrolling steadily.

> "Three calls we would defend. The letter comes from a deterministic composer, so it
> works with or without a model — never hostage to an LLM. The index scores a ward,
> never a person. And we do not email real officials: a hackathon shouldn't put
> unsolicited mail in a public servant's inbox.
>
> Voice and translation are built into the interface. They are what we finish next."

*That closing line is what earns the right to have shown the Speak card at 0:17.*

---

## 2:52 – 3:00 · Learning, and close · *44 words*

🖼 **SHOW ONLY** — end card: live URL, repo, the three names. Hold five seconds.

> "The thing we genuinely did not expect to learn: the current ward boundaries of a city
> of twenty million people are not published as open data. So we shipped the ones that
> are — and we said so, on the site.
>
> MERAWARD. It's live."

---

# AWS console shot list

Record these **before** you start, then lay the 1:58 narration over them.

| # | Shot | Where to get it |
|---|---|---|
| 1 | The eight Lambda functions | Lambda → Functions, filter `meraward` |
| 2 | The SQS queue and its dead-letter queue side by side | SQS → `meraward-infra-ComplaintQueue` |
| 3 | A CloudWatch log line from a real draft | CloudWatch → `/aws/lambda/…DraftAndSend…` |
| 4 | A DynamoDB item with `body_hi` visible in Devanagari | DynamoDB → `meraward-complaints` → Explore items |
| 5 | `GET /health` open in a browser tab | the live API URL |

Shot 5 deserves three seconds alone. `ward_index.loaded: true, wards: 289` is proof the
geospatial index really loads inside Lambda, rather than being a local trick.

---

# Verified true on 20 September 2026

Checked against the live deployment, not recalled.

| Claim | Evidence |
|---|---|
| 289 ward polygons, point-in-polygon inside Lambda | `/health` → `ward_index.loaded: true, wards: 289` |
| Warm lookup ≈ 0.023 ms | measured |
| API returns `202` in ~2 ms | measured |
| A complaint drafts in both languages and quotes the reporter | verified against the live API today |
| 254 backend tests, none needing AWS credentials | `pytest backend -q` |
| Lighthouse 100 / 100 / 100 / 100 on the home page | against the live site |
| 100 accessibility on every page | against the live site |
| Councillor names from official SEC Delhi results | 155 of 288 boundaries |

## Do not claim

| Don't say | Why not |
|---|---|
| "Powered by Amazon Bedrock" | Wired, but disabled. `/health` reports `template`. |
| "Uses Amazon Transcribe" | Not wired. Voice is browser speech recognition, and it is not working yet. |
| "Amazon Translate" / "Rekognition" | Not used at all. |
| "Complaints are sent to councillors" | `DELIVERY_MODE=DEMO_OUTBOX`. Nothing is emailed to anyone real. |
| "250 current wards" | Ours are the pre-2022 delimitation — 272 MCD wards. |

---

# Production notes

- **Captions on.** Judges may watch muted, and there is Hindi on screen.
- Record the app on **Android Chrome**.
- Music low, or none at all — the narration is dense.
- Upload **unlisted**, then confirm it plays logged-out in an incognito window.
- Running long? Cut §2:36 first. **Never cut §0:38**, the live ward lookup — it is the
  one moment that is both unique to this project and provably working.
