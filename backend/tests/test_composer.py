"""Tests for the deterministic bilingual composer.

These are the guardrails that let us swap Bedrock in and out without worrying:
whatever happens to model access, this path always returns a real letter.
"""

import re
from datetime import date, datetime, timezone

import pytest

from common.composer import (
    ISSUE_TYPES,
    Draft,
    compose,
    normalise_issue_type,
)


# ---------------------------------------------------------------- issue types

@pytest.mark.parametrize("known", ISSUE_TYPES)
def test_known_issue_types_round_trip(known):
    assert normalise_issue_type(known) == known


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("pothole", "POTHOLE"),
        ("  Garbage  ", "GARBAGE"),
        ("StReEtLiGhT", "STREETLIGHT"),
    ],
)
def test_issue_type_is_case_and_whitespace_insensitive(raw, expected):
    assert normalise_issue_type(raw) == expected


@pytest.mark.parametrize("junk", ["", "   ", "BANANA", None, 42, [], {"a": 1}])
def test_unknown_issue_types_fall_back_to_other(junk):
    """A junk issue type must never cost the user their draft."""
    assert normalise_issue_type(junk) == "OTHER"


# ---------------------------------------------------------------- happy path

def test_every_issue_type_produces_a_complete_bilingual_draft():
    for issue in ISSUE_TYPES:
        d = compose(issue, "Sadar Bazar", reported_on=date(2026, 9, 19))
        assert isinstance(d, Draft)
        assert d.source == "template"
        for field in (d.subject, d.body_en, d.body_hi):
            assert field.strip(), f"{issue} produced an empty field"
        assert len(d.body_en) > 300
        assert len(d.body_hi) > 300


def test_hindi_body_is_actually_devanagari():
    """Guards against the bilingual claim being decorative.

    The Hindi tab is real content in the demo, so assert the Hindi body is
    substantially Devanagari rather than English with a Hindi heading.
    """
    d = compose("POTHOLE", "Sadar Bazar")
    devanagari = sum(1 for ch in d.body_hi if "\u0900" <= ch <= "\u097F")
    letters = sum(1 for ch in d.body_hi if ch.isalpha())
    assert letters
    assert devanagari / letters > 0.85


def test_ward_name_and_date_appear_in_both_languages():
    d = compose("WATER", "Karol Bagh", reported_on=date(2026, 9, 19))
    assert "Karol Bagh" in d.subject
    assert "Karol Bagh" in d.body_en
    assert "Karol Bagh" in d.body_hi
    assert "19 September 2026" in d.body_en
    assert "19 सितम्बर 2026" in d.body_hi


def test_ward_id_reference_and_landmark_are_rendered_when_given():
    d = compose(
        "GARBAGE",
        "Sadar Bazar",
        ward_id="DEL-0042",
        reference="CMP-01J8XY",
        landmark="the community park gate",
    )
    assert "Ward DEL-0042" in d.subject
    assert "CMP-01J8XY" in d.body_en and "CMP-01J8XY" in d.body_hi
    assert "the community park gate" in d.body_en
    assert "the community park gate" in d.body_hi


def test_optional_fields_are_omitted_not_blank():
    """Missing data must never render as a dangling empty sentence."""
    d = compose("POTHOLE", "Sadar Bazar")
    assert "Ward None" not in d.subject
    assert "near ." not in d.body_en
    assert "reference number" not in d.body_en
    # No blank paragraph left where an omitted optional section used to be.
    assert "\n\n\n" not in d.body_en
    assert "\n\n\n" not in d.body_hi
    assert not any(not p.strip() for p in d.body_en.split("\n\n"))
    assert not any(not p.strip() for p in d.body_hi.split("\n\n"))


# ---------------------------------------------------------------- ethics (PRD §12)

def test_letter_never_threatens_or_accuses():
    """The letter addresses an office, never a person, and never threatens.

    This is a product constraint, not a style preference: we are drafting mail
    that a citizen sends to a public body, from demo data.
    """
    banned = [
        "legal action", "sue", "sued", "lawsuit", "court", "negligent",
        "negligence", "corrupt", "incompetent", "resign", "councillor",
        "penalty", "liable",
    ]
    for issue in ISSUE_TYPES:
        d = compose(issue, "Sadar Bazar")
        lowered = d.body_en.lower()
        for word in banned:
            # Word boundaries matter: "sue" is a substring of "issue".
            assert not re.search(rf"\b{re.escape(word)}\b", lowered), (
                f"{issue}: banned phrase {word!r}"
            )


def test_letter_is_addressed_to_the_ward_office():
    d = compose("POTHOLE", "Sadar Bazar")
    assert "The Ward Office" in d.body_en
    assert "वार्ड कार्यालय" in d.body_hi


# ---------------------------------------------------------------- robustness

@pytest.mark.parametrize(
    "value",
    [
        date(2026, 9, 19),
        datetime(2026, 9, 19, 14, 30, tzinfo=timezone.utc),
        "2026-09-19",
        "2026-09-19T14:30:00+05:30",
        "2026-09-19T09:00:00Z",
    ],
)
def test_date_accepts_every_shape_the_worker_might_pass(value):
    d = compose("POTHOLE", "Sadar Bazar", reported_on=value)
    assert "19 September 2026" in d.body_en


@pytest.mark.parametrize("junk_date", ["not-a-date", "", "2026-13-45"])
def test_unparseable_date_falls_back_to_today_rather_than_raising(junk_date):
    d = compose("POTHOLE", "Sadar Bazar", reported_on=junk_date)
    assert str(datetime.now(timezone.utc).year) in d.body_en


@pytest.mark.parametrize("blank", ["", "   ", None])
def test_missing_ward_name_degrades_gracefully(blank):
    d = compose("POTHOLE", blank)
    assert "this ward" in d.body_en
    assert d.body_hi.strip()


def test_output_matches_the_bedrock_contract():
    """The dict shape must match what Bedrock Converse returns.

    If these drift, swapping the model in stops being a config flag.
    """
    d = compose("POTHOLE", "Sadar Bazar").to_dict()
    assert set(d) == {"subject", "body_en", "body_hi", "source"}
    assert all(isinstance(v, str) for v in d.values())


def test_composition_is_deterministic():
    kwargs = dict(reported_on=date(2026, 9, 19), ward_id="DEL-0042", reference="CMP-1")
    assert compose("POTHOLE", "Sadar Bazar", **kwargs) == compose(
        "POTHOLE", "Sadar Bazar", **kwargs
    )


def test_draft_is_immutable():
    d = compose("POTHOLE", "Sadar Bazar")
    with pytest.raises(Exception):
        d.subject = "tampered"
