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
| Dataset | `data/delhi_mcd_ward_representatives.json` — 250 wards, as of 2026-09-19 |
| Sources | [MCD 2022 election results](https://sec.delhi.gov.in/sites/default/files/SEC/generic_multiple_files/electionreportvolume1-mcdelections2022.pdf) and [subsequent bye-elections](https://sec.delhi.gov.in/sites/default/files/SEC/circulars-orders/list_of_elected_councillors_bye_election.pdf), State Election Commission, NCT of Delhi |
| Scope | Councillor name and party only. No contact details — we do not email officials. |
| Coverage | **155 of 288 boundaries.** The rest render as an explicit "not available". |

### Matched by ward name, never by ward number

The councillor list is the **post-2022** delimitation (250 wards); our boundaries are the
**pre-2022** one. The 2022 re-delimitation renumbered everything, so the two numbering
schemes do not correspond — joining on `ward_number` agrees with the ward name in only
**5 of 250 cases**.

Joining on number would attach a real, named, elected person to a ward they do not
represent in 98% of cases. So [`data/load_councillors.py`](data/load_councillors.py)
matches on normalised ward name and writes nothing where there is no match.

Every populated record carries a `contact_source` stating both the source **and** that
the match was by name rather than by identical geography. `contact_source` is mandatory:
the API withholds the entire councillor block without it, so a name can never be
published unattributed.

MLA and MP fields in the source dataset are `null` by design — those represent assembly
and parliamentary constituencies, not municipal wards, and the upstream author declined
to guess the crosswalk. We have not guessed either.

## Libraries with attribution requirements

- `shapely` — BSD 3-Clause
- `MapLibre GL JS` — BSD 3-Clause
