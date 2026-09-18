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

_Pending._

---

## Kartik Dixit

_Pending._
