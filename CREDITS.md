# Credits & attribution

Everything external we use, with its source and licence. Filled in as each dependency lands —
**nothing ships without an entry here.**

## Ward boundary data

| Field | Value |
|---|---|
| Source | _TBD — see `docs/DECISIONS.md` for the 90-minute acquisition timebox_ |
| Licence | _TBD_ |
| Retrieved | _TBD_ |
| Notes | We never invent a boundary. A coarser real boundary beats a precise fake one. |

## Basemap tiles

| Field | Value |
|---|---|
| Provider | _TBD — must be a provider whose terms permit application use_ |
| Licence / attribution string | _TBD_ |

> We deliberately do **not** use `tile.openstreetmap.org`: its usage policy prohibits
> application/production use, and this is a public URL judges will click.

## Councillor identity data

| Field | Value |
|---|---|
| Source | 2022 MCD election results (public record) |
| Scope | Name and party only, where verifiable against two sources |
| Notes | `contact_source` is mandatory on any populated councillor field. Unsourced fields stay null and render as "not available". |

## Libraries with attribution requirements

_Listed as added._

- `shapely` — BSD 3-Clause
- `MapLibre GL JS` — BSD 3-Clause
