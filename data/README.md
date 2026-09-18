# MERAWARD — data

Ward polygons and the pipeline that produces them.

## `wards.geojson` — committed, 289 wards, 632 KB

Built by [`prepare_wards.py`](prepare_wards.py) and uploaded to the data S3 bucket as
`wards.geojson`. Each feature carries `properties.ward_id`, `ward_name` and `zone`;
geometry is `Polygon`/`MultiPolygon` in WGS84, budgeted to ≤500 vertices. Loaded once
per Lambda cold start into a `shapely` STRtree.

| | |
|---|---|
| Source | [DataMeet — Municipal Spatial Data](https://github.com/datameet/Municipal_Spatial_Data/tree/master/Delhi) |
| Licence | [CC BY-SA 2.5 IN](http://creativecommons.org/licenses/by-sa/2.5/in/) — full attribution in [`../CREDITS.md`](../CREDITS.md) |
| Coverage | 272 MCD · 9 NDMC · 8 Delhi Cantonment Board |
| Largest polygon | 283 vertices (already inside budget, so no simplification was applied) |
| Load time | ~47 ms cold, 0.023 ms per warm lookup |

> [!WARNING]
> **These are the pre-2022 boundaries** — 272 MCD wards, not the 250 created by the
> 2022 unification. We could not find the current boundaries published as usable open
> data. This is disclosed in `CREDITS.md`, on the `/about` page and in the writeup.
> See [`../docs/DECISIONS.md`](../docs/DECISIONS.md).

## Regenerating

```bash
python prepare_wards.py raw/<source>.geojson wards.geojson
```

The script normalises properties, repairs self-intersecting rings with `buffer(0)`,
drops features with no usable id or geometry, and budgets vertices adaptively. It
prints what it did — check the counts against the source before trusting the output.

**It never synthesises a boundary.** Every output feature comes from an input feature.

## Verifying a new dataset

Do not trust a boundary file because it parsed. Run known coordinates through the real
index:

```bash
cd ../backend
WARDS_GEOJSON_PATH=../data/wards.geojson python -c "
import sys; sys.path.insert(0,'src')
from common.wards import get_index
idx = get_index()
for name, lat, lng in [('Connaught Place',28.6315,77.2167), ('Karol Bagh',28.6519,77.1909),
                       ('Delhi Cantonment',28.5900,77.1300), ('Mumbai control',19.0760,72.8777)]:
    w = idx.lookup(lat, lng)
    print(f'{name:20} -> {w.ward_name if w else \"OUTSIDE COVERAGE\"}')
"
```

Connaught Place should land in NDMC, Karol Bagh in a ward named Karol Bagh, Delhi
Cantonment in the Cantonment Board, and the Mumbai control outside coverage.

## Seed complaints

**Not yet written — owner: Kartik** (see [issue #2](https://github.com/amritkang165/meraward/issues/2)).

150–300 rows at plausible locations inside real polygons, timestamps 10–120 days old,
mixed statuses, realistic issue-type distribution.

> [!IMPORTANT]
> **Every seeded row must carry `is_demo = true`.** The UI surfaces it and `/about`
> explains it. Reviewers understand demo data; they do not forgive being misled about
> which is which.
