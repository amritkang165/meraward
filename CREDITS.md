# Credits & attribution

Everything external we use, with its source and licence. **Nothing ships without an entry here.**

## Ward boundary data

| Field | Value |
|---|---|
| Dataset | `Delhi_Wards.geojson` |
| Source | [DataMeet — Municipal Spatial Data](https://github.com/datameet/Municipal_Spatial_Data/tree/master/Delhi) |
| Upstream origin | Scraped by DataMeet from an ArcGIS Online map ([item 7c4f1b9be6cc4cecbcd28ee5136898f7](http://www.arcgis.com/home/item.html?id=7c4f1b9be6cc4cecbcd28ee5136898f7)) |
| Licence | [Creative Commons Attribution-ShareAlike 2.5 India (CC BY-SA 2.5 IN)](http://creativecommons.org/licenses/by-sa/2.5/in/) |
| Retrieved | 2026-09-19 |
| Coverage | 289 wards — 272 MCD, 9 NDMC, 8 Delhi Cantonment Board |
| Processing | [`data/prepare_wards.py`](data/prepare_wards.py) — property normalisation, geometry validation, vertex budget. No geometry was synthesised. |

### ⚠️ This is the pre-2022 delimitation, and we say so on the site

The dataset carries **272 MCD wards**. Delhi's three municipal corporations were
unified in 2022 and re-delimited to **250 wards**. So these are the *previous*
boundaries, not the current ones.

We looked for the post-2022 250-ward boundaries as open data and could not find them
published in a usable, openly-licensed form within our acquisition timebox — see
[`docs/DECISIONS.md`](docs/DECISIONS.md) for exactly what we tried.

We use this dataset because it is **real, correctly georeferenced, openly licensed and
complete for Delhi**, and because the alternative was a coarser unit (assembly
constituencies or districts). What we do *not* do is claim it is current. The `/about`
page states the delimitation and the retrieval date plainly.

That the current ward boundaries of a city of 20 million are not readily available as
open data is, itself, a fair illustration of the problem this project is about.

### Attribution notice (CC BY-SA 2.5 IN)

> Ward boundary data © DataMeet contributors, licensed under
> [CC BY-SA 2.5 IN](http://creativecommons.org/licenses/by-sa/2.5/in/).
> Adapted for MERAWARD: properties normalised, geometry validated, vertices reduced.

Because the licence is ShareAlike, this attribution appears in-app on `/about`, and any
redistribution of the derived `data/wards.geojson` carries the same licence.

## Basemap tiles

| Field | Value |
|---|---|
| Provider | [CARTO Positron](https://basemaps.cartocdn.com/gl/positron-gl-style/style.json) |
| Why | Permits application use with attribution, and needs no API key |
| Attribution (rendered in-map) | `© CARTO · © OpenStreetMap contributors` |
| Underlying data | © [OpenStreetMap](https://www.openstreetmap.org/copyright) contributors, ODbL |

> We deliberately do **not** use `tile.openstreetmap.org`: its usage policy prohibits
> application/production use, and this is a public URL judges will click.

## Councillor identity data

| Field | Value |
|---|---|
| Source | 2022 MCD election results (public record) |
| Scope | Name and party only, where verifiable against two sources |
| Status | **Not populated.** Every councillor field is null and renders as "not available". |

`contact_source` is mandatory on any populated councillor field — the API withholds the
whole councillor block if it is missing, so a name can never be published unattributed.

## Libraries with attribution requirements

- `shapely` — BSD 3-Clause
- `MapLibre GL JS` — BSD 3-Clause
