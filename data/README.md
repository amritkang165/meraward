# MERAWARD — data

Ward polygon acquisition, simplification, and seed complaint generation. **Owner: Muneer.**

## `wards.geojson`

FeatureCollection uploaded to the data S3 bucket. Each feature carries
`properties.ward_id`, `ward_name`, `zone`; geometry `Polygon`/`MultiPolygon`, WGS84,
simplified to ≤500 points. Loaded once per Lambda cold start into a `shapely` STRtree.

**Source and licence go in [`../CREDITS.md`](../CREDITS.md) the moment the data lands.**
Never invent a boundary — a coarser real boundary beats a precise fake one.

## Seed complaints

150–300 rows at plausible locations inside real polygons, timestamps 10–120 days old,
mixed statuses and a realistic issue-type distribution.

**Every seeded row carries `is_demo = true`,** and the UI surfaces it. Judges understand
demo data; they do not forgive being misled about which is which.
