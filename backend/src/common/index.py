"""Ward Neglect Index (PRD §13).

Three bounded sub-scores against fixed anchors, 0–100, higher = worse. The index
belongs to a **ward**, never to a person: it is computed partly from demo data,
and attaching that number to a named elected individual would be defamation
shaped. Labels, copy and the demo video all say "Ward 42's Neglect Index".

    B  Backlog    = 100 × open / (open + resolved)
    S  Staleness  = 100 × min(median_open_age_days, 90) / 90
    L  Sloth      = 100 × min(median_resolution_days, 60) / 60   [resolved > 0]

    WNI = 0.40·B + 0.40·S + 0.20·L    when resolved > 0
    WNI = 0.50·B + 0.50·S            when resolved = 0

Below :data:`MIN_SAMPLE` total reports the index is ``None``, not ``0``. This is
the rule that matters most: scoring a silent ward as zero would rank the wards
nobody reports as the best-run wards in Delhi, which is precisely backwards.

Rates, not counts, and fixed anchors rather than a city maximum — otherwise the
index mostly measures ward population and app adoption, and a single outlier
compresses every other ward toward zero.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Final

__all__ = [
    "BAND_HIGH",
    "BAND_LOW",
    "BAND_MODERATE",
    "EXPLANATION",
    "MIN_SAMPLE",
    "NeglectIndex",
    "band_for",
    "compute_neglect_index",
]

MIN_SAMPLE: Final[int] = 5
STALE_ANCHOR_DAYS: Final[float] = 90.0
SLOTH_ANCHOR_DAYS: Final[float] = 60.0

BAND_LOW: Final[str] = "LOW"
BAND_MODERATE: Final[str] = "MODERATE"
BAND_HIGH: Final[str] = "HIGH"

#: Shown next to the gauge. It must describe what the formula actually computes.
EXPLANATION: Final[str] = (
    "How many reports are still open, how long those have been waiting, "
    "and how slow past fixes were."
)

INSUFFICIENT_DATA: Final[str] = "Not enough reports yet"


def band_for(score: int) -> str:
    if score < 30:
        return BAND_LOW
    if score < 60:
        return BAND_MODERATE
    return BAND_HIGH


@dataclass(frozen=True)
class NeglectIndex:
    """The score plus the numbers it came from.

    ``basis`` is rendered beside the gauge in the UI. Explainability is the
    feature: a judge who asks "what is 74 made of?" gets four raw numbers, not
    a shrug.
    """

    score: int | None
    band: str | None
    basis: dict[str, Any]
    note: str | None = None

    @property
    def has_score(self) -> bool:
        return self.score is not None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _clamp_non_negative(value: float | int | None) -> float:
    if value is None:
        return 0.0
    try:
        v = float(value)
    except (TypeError, ValueError):
        return 0.0
    return v if v > 0 else 0.0


def compute_neglect_index(
    open_count: int | None,
    resolved_count: int | None,
    median_open_age_days: float | None = None,
    median_resolution_days: float | None = None,
) -> NeglectIndex:
    """Compute a ward's Neglect Index.

    Returns a :class:`NeglectIndex` whose ``score`` is ``None`` when the ward has
    fewer than :data:`MIN_SAMPLE` total reports.
    """
    open_n = int(_clamp_non_negative(open_count))
    resolved_n = int(_clamp_non_negative(resolved_count))
    total = open_n + resolved_n

    open_age = _clamp_non_negative(median_open_age_days)
    resolution = _clamp_non_negative(median_resolution_days)

    basis: dict[str, Any] = {
        "open": open_n,
        "resolved": resolved_n,
        "median_open_age_days": round(open_age, 1),
        "median_resolution_days": round(resolution, 1),
    }

    if total < MIN_SAMPLE:
        return NeglectIndex(score=None, band=None, basis=basis, note=INSUFFICIENT_DATA)

    backlog = 100.0 * open_n / total
    staleness = 100.0 * min(open_age, STALE_ANCHOR_DAYS) / STALE_ANCHOR_DAYS

    if resolved_n > 0:
        sloth = 100.0 * min(resolution, SLOTH_ANCHOR_DAYS) / SLOTH_ANCHOR_DAYS
        raw = 0.40 * backlog + 0.40 * staleness + 0.20 * sloth
    else:
        # Nothing has ever been resolved, so there is no resolution speed to
        # measure. Redistribute rather than score an unmeasured term as zero.
        sloth = None
        raw = 0.50 * backlog + 0.50 * staleness

    score = int(round(raw))
    score = max(0, min(100, score))

    basis["components"] = {
        "backlog": round(backlog, 1),
        "staleness": round(staleness, 1),
        "sloth": round(sloth, 1) if sloth is not None else None,
    }

    return NeglectIndex(score=score, band=band_for(score), basis=basis)
