"""Tests for the Ward Neglect Index (PRD §13)."""

from __future__ import annotations

import pytest

from common.index import (
    BAND_HIGH,
    BAND_LOW,
    BAND_MODERATE,
    MIN_SAMPLE,
    band_for,
    compute_neglect_index,
)


# ------------------------------------------------- the rule that matters most

@pytest.mark.parametrize("total", range(0, MIN_SAMPLE))
def test_a_quiet_ward_scores_none_not_zero(total):
    """A ward nobody reports must never rank as the best-run ward.

    This is the single most important property of the index. Scoring an
    unreported ward as 0 would put the wards with no civic engagement at the top
    of the leaderboard, which is exactly backwards.
    """
    result = compute_neglect_index(open_count=total, resolved_count=0)
    assert result.score is None
    assert result.band is None
    assert result.note == "Not enough reports yet"
    assert not result.has_score


def test_index_appears_once_the_sample_is_large_enough():
    result = compute_neglect_index(open_count=MIN_SAMPLE, resolved_count=0)
    assert result.score is not None
    assert result.note is None


def test_basis_is_present_even_without_a_score():
    """The UI shows the raw numbers even when it cannot show an index."""
    result = compute_neglect_index(open_count=2, resolved_count=1)
    assert result.basis["open"] == 2
    assert result.basis["resolved"] == 1


# ------------------------------------------------------------------ the maths

def test_worst_case_is_100():
    result = compute_neglect_index(
        open_count=50, resolved_count=0, median_open_age_days=365
    )
    assert result.score == 100
    assert result.band == BAND_HIGH


def test_best_case_is_0():
    result = compute_neglect_index(
        open_count=0, resolved_count=50, median_open_age_days=0,
        median_resolution_days=0,
    )
    assert result.score == 0
    assert result.band == BAND_LOW


def test_weights_match_the_documented_formula():
    # open=25, resolved=25 → B = 50
    # median_open_age = 45  → S = 50
    # median_resolution = 30 → L = 50
    # 0.40(50) + 0.40(50) + 0.20(50) = 50
    result = compute_neglect_index(25, 25, 45, 30)
    assert result.score == 50
    assert result.basis["components"] == {"backlog": 50.0, "staleness": 50.0, "sloth": 50.0}


def test_sloth_term_is_dropped_when_nothing_was_ever_resolved():
    """With no resolutions there is no resolution speed to measure.

    The weight is redistributed rather than scoring an unmeasured term as zero,
    which would flatter a ward that has never fixed anything.
    """
    result = compute_neglect_index(10, 0, 45, 0)
    # B = 100, S = 50 → 0.50(100) + 0.50(50) = 75
    assert result.score == 75
    assert result.basis["components"]["sloth"] is None


def test_anchors_are_fixed_not_relative_to_the_city_maximum():
    """A ward's score must not move because some *other* ward changed.

    Capping at the 90/60-day anchors keeps scores comparable across wards and
    across time; dividing by a city maximum would let one outlier compress
    everyone else toward zero.
    """
    a = compute_neglect_index(10, 10, 90, 60)
    b = compute_neglect_index(10, 10, 9000, 6000)
    assert a.score == b.score


def test_index_measures_rates_not_volume():
    """A busy ward is not penalised for being busy.

    Same ratio, wildly different volume, same score — otherwise the index
    mostly measures ward population and app adoption.
    """
    small = compute_neglect_index(3, 7, 30, 20)
    large = compute_neglect_index(300, 700, 30, 20)
    assert small.score == large.score


# -------------------------------------------------------------------- bands

@pytest.mark.parametrize(
    "score,expected",
    [(0, BAND_LOW), (29, BAND_LOW), (30, BAND_MODERATE), (59, BAND_MODERATE),
     (60, BAND_HIGH), (100, BAND_HIGH)],
)
def test_band_boundaries(score, expected):
    assert band_for(score) == expected


def test_score_is_always_within_bounds():
    for open_n in (0, 1, 7, 500):
        for resolved_n in (0, 1, 7, 500):
            r = compute_neglect_index(open_n, resolved_n, 1000, 1000)
            if r.score is not None:
                assert 0 <= r.score <= 100


# --------------------------------------------------------------- robustness

@pytest.mark.parametrize("junk", [None, -5, "not a number", float("nan")])
def test_garbage_inputs_degrade_rather_than_raise(junk):
    result = compute_neglect_index(junk, 10, junk, junk)
    assert result.score is None or 0 <= result.score <= 100


def test_negative_counts_are_treated_as_zero():
    assert compute_neglect_index(-10, 20).basis["open"] == 0
