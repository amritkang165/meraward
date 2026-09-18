# What we learned building MERAWARD

One substantive entry per person, written **as we go** — not reconstructed on Sunday night.
Honest entries, including the things that went wrong.

---

## Muneer Alam

### 2026-09-19 — Why the point-in-polygon lives inside the Lambda

The first version of our plan put ward boundaries in OpenSearch and used a
`geo_shape` query for point-in-polygon. It sounds like the right tool, and I
would have built it that way without thinking twice.

Two things changed my mind. OpenSearch Serverless has a two-OCU floor, which is
roughly $11 a day whether or not anyone queries it — so the "runs for under $10"
line we wanted in the demo video would have been false, on camera, to AWS judges.
And it introduced a sync problem: every complaint write would have had to reach
both DynamoDB and OpenSearch, and the two would drift.

Delhi has about 250 wards. That is a few megabytes of polygons. I put them in an
R-tree (`shapely`'s STRtree) inside the Lambda, loaded from S3 once per cold
start and held at module level. Warm lookups measure about **0.05 ms**. The
3-second budget in our success criteria is now spent almost entirely on the
network.

The thing I actually learned: an R-tree narrows candidates by *bounding box*, not
by shape. `tree.query(point)` on an L-shaped ward returns that ward for a point
sitting in the notch, because the point is inside the bounding rectangle. You
have to confirm real containment afterwards. I wrote the test before I hit the
bug, which is the only reason I know it would have been a bug — it returns a
plausible neighbouring ward rather than an error, so it would have shipped
silently and shown the wrong councillor to a real user.

### 2026-09-19 — Writing the fallback before the feature

Bedrock model access hadn't been granted, and the organisers confirmed mid-event
that Bedrock isn't mandatory. The instinct is to wait for access and build the
real thing. Instead I wrote the deterministic template composer first: a pure
function from `(issue_type, ward_name, date)` to a formal complaint letter in
Hindi and English, no network call, no dependency.

It returns the same `{subject, body_en, body_hi}` shape Bedrock Converse returns.
That one decision turned the model from a dependency into a config flag — if
access lands we swap it in, if it doesn't the product is complete anyway, and
when a live call fails the worker has something real to fall back to instead of
showing an empty draft.

I also learned that a test can encode a product rule, not just behaviour. Two of
the composer's tests assert the letter is addressed to a ward *office* and never
to a person, and that it carries no legal threat. Those aren't style preferences
— we're drafting mail that a citizen sends to a public body, partly from demo
data, and the tests are what stop that constraint quietly eroding at 4am.

---

## Amrit Kang

> Drafted from the work done in this lane — Amrit, rewrite these in your own voice
> before submission. The reasoning is real; the phrasing should be yours.

### 2026-09-19 — The data you need often does not exist, and that is the finding

I budgeted ninety minutes to find Delhi's ward boundaries and expected to spend it
on formats and projections. I spent it discovering that the data is not there.

The ArcGIS Hub item for "Delhi Ward Boundary 2022" returns *item does not exist or
is inaccessible* from both of its export endpoints. OpenCity's API has Delhi ward
data, but only Census 2011 tables — no geometry. OpenStreetMap has no consistent
`admin_level` relations for Delhi's municipal wards. What finally worked was
DataMeet, a community civic-data project, under a CC BY-SA licence.

And that dataset is the **pre-2022** delimitation: 272 MCD wards, not the 250 the
city actually has now.

The instinct was to keep hunting or to quietly ship it and hope nobody counted. What
I think is actually right is to ship it and say exactly what it is, because the gap
is the story: the current ward boundaries of a city of twenty million are not
available as open data. That is the same accountability failure the product is
about, showing up in our own build log.

The engineering lesson underneath it: verify data, do not trust it. I ran eleven
known Delhi coordinates through the real lookup — Connaught Place and India Gate
landed in NDMC, Karol Bagh resolved to the ward actually named Karol Bagh, and a
Mumbai control correctly fell outside coverage. That took ten minutes and is the
only reason I believe the file.

### 2026-09-19 — Terms of service are an engineering constraint

I was about to point MapLibre at `tile.openstreetmap.org` because it needs no API
key. Its usage policy prohibits exactly that — application use — and we were about
to put a public URL in front of judges. Switched to CARTO Positron, which permits
application use with attribution, and rendered the attribution in-map.

"It works in development" and "we are allowed to do this" are different questions,
and only the second one survives being deployed.

### 2026-09-19 — Measuring beat guessing, twice

Two things I would have shipped broken if I had trusted my eyes.

The first: I picked a grey for secondary text that looked fine. Computing the
contrast ratio showed 4.18:1 against the page background, below the 4.5:1 AA
threshold. Two of the index band colours failed too, at 4.21 and 4.29 — and
**Lighthouse could not see those**, because the band chips do not appear on the page
I audited. An automated check tells you about the page it looked at, not about your
design system.

The second: Lighthouse reported a console error I assumed was a headless-browser
artifact. It was a real crash. With the API base URL unset, requests were hitting
the single-page fallback and getting `index.html` back with a **200**; the client
treated an unparseable success body as an empty success and returned null, so every
screen died on its first property access. A proxy error page in production does
precisely the same thing. The audit found a bug that no test had.

---

## Kartik Dixit

> Kartik — one substantive entry is a scored submission criterion, so this is worth
> twenty minutes before we submit. The AWS account recovery decision, the SAM wiring,
> and whatever bit you into a wall are all good material.

_Awaiting Kartik._
