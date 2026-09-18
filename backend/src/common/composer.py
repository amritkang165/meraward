"""Deterministic bilingual complaint composer.

This is the floor under F-4, not a stopgap. It maps
``(issue_type, ward_name, reported_on)`` onto a formal complaint letter in
English and Hindi using hand-written templates, with no network call, no model
access and no third-party dependency.

It exists for three reasons:

1. **It guarantees the draft ships.** Bedrock model access is not granted at
   the time of writing, and the organisers have confirmed Bedrock is not
   mandatory for the hackathon. The product must be fully demoable without it.
2. **It is the worker's fallback.** When a Bedrock call fails or times out,
   ``draft_and_send`` falls back here rather than leaving the UI empty.
3. **It makes Bedrock a strict upgrade.** The Bedrock path returns the same
   shape this module returns, so swapping one for the other is a config flag,
   not a rewrite.

The output shape is identical to the Bedrock Converse contract:
``{"subject": str, "body_en": str, "body_hi": str}``.

Editorial constraints, which the templates enforce by construction:

* Formal, respectful, first-person citizen complaint.
* References the ward and the issue type.
* **No legal threats, and no accusation against any named individual.** The
  letter addresses a ward *office*, never a person. See PRD §12.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from typing import Final

__all__ = [
    "Draft",
    "IssueType",
    "ISSUE_TYPES",
    "compose",
    "normalise_issue_type",
]


# --------------------------------------------------------------------------
# Issue types
# --------------------------------------------------------------------------

IssueType = str

POTHOLE: Final[IssueType] = "POTHOLE"
STREETLIGHT: Final[IssueType] = "STREETLIGHT"
GARBAGE: Final[IssueType] = "GARBAGE"
WATER: Final[IssueType] = "WATER"
OTHER: Final[IssueType] = "OTHER"

ISSUE_TYPES: Final[tuple[IssueType, ...]] = (
    POTHOLE,
    STREETLIGHT,
    GARBAGE,
    WATER,
    OTHER,
)


def normalise_issue_type(value: object) -> IssueType:
    """Coerce arbitrary input to a known issue type.

    Unknown, missing or malformed values fall back to ``OTHER`` rather than
    raising: a complaint that reaches the worker with a junk issue type should
    still produce a letter, because the alternative the user sees is an empty
    draft.
    """
    if not isinstance(value, str):
        return OTHER
    candidate = value.strip().upper()
    return candidate if candidate in ISSUE_TYPES else OTHER


# --------------------------------------------------------------------------
# Result
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Draft:
    """A composed complaint, in both languages.

    ``source`` records which path produced it so the UI and CloudWatch can tell
    a templated draft from a model-generated one. It is deliberately part of the
    record: claiming an AI drafted something it did not would be the same class
    of problem as faking the demo data.
    """

    subject: str
    body_en: str
    body_hi: str
    source: str = "template"

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


# --------------------------------------------------------------------------
# Per-issue-type copy
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class _Copy:
    subject_en: str
    subject_hi: str
    problem_en: str
    problem_hi: str
    request_en: str
    request_hi: str


_COPY: Final[dict[IssueType, _Copy]] = {
    POTHOLE: _Copy(
        subject_en="Pothole on a public road",
        subject_hi="सार्वजनिक सड़क पर गड्ढा",
        problem_en=(
            "I wish to report a pothole on a public road in this ward. The road "
            "surface has broken up and now holds a depression deep enough to be a "
            "hazard to two-wheeler riders and pedestrians, particularly after rain "
            "and after dark."
        ),
        problem_hi=(
            "मैं इस वार्ड की एक सार्वजनिक सड़क पर बने गड्ढे की सूचना देना चाहता/चाहती हूँ। "
            "सड़क की सतह टूट चुकी है और वहाँ इतना गहरा गड्ढा बन गया है कि दोपहिया वाहन "
            "चालकों तथा पैदल चलने वालों के लिए, विशेषकर वर्षा के बाद और अंधेरे में, "
            "दुर्घटना का खतरा बना रहता है।"
        ),
        request_en=(
            "I request that the location be inspected and the road surface repaired."
        ),
        request_hi=(
            "निवेदन है कि उक्त स्थान का निरीक्षण कराकर सड़क की मरम्मत करवाई जाए।"
        ),
    ),
    STREETLIGHT: _Copy(
        subject_en="Non-functional street lighting",
        subject_hi="बंद पड़ी स्ट्रीट लाइट",
        problem_en=(
            "I wish to report a street light in this ward that is not working. The "
            "stretch of road it covers stays unlit after sunset, which makes it "
            "difficult to use on foot and raises a safety concern for residents "
            "returning home in the evening."
        ),
        problem_hi=(
            "मैं इस वार्ड में एक बंद पड़ी स्ट्रीट लाइट की सूचना देना चाहता/चाहती हूँ। "
            "सूर्यास्त के बाद सड़क का यह हिस्सा अँधेरे में रहता है, जिससे पैदल आवागमन "
            "कठिन हो जाता है तथा शाम को घर लौटने वाले निवासियों की सुरक्षा को लेकर "
            "चिंता बनी रहती है।"
        ),
        request_en=(
            "I request that the fitting be inspected and the light restored to "
            "working order."
        ),
        request_hi=(
            "निवेदन है कि उक्त लाइट का निरीक्षण कराकर उसे शीघ्र चालू करवाया जाए।"
        ),
    ),
    GARBAGE: _Copy(
        subject_en="Uncollected garbage accumulating in a public area",
        subject_hi="सार्वजनिक स्थान पर कूड़े का ढेर",
        problem_en=(
            "I wish to report garbage accumulating in a public area of this ward "
            "that has not been cleared. The waste has built up over a period of "
            "time and is now a source of odour and of flies, and is a health "
            "concern for households and shops nearby."
        ),
        problem_hi=(
            "मैं इस वार्ड के एक सार्वजनिक स्थान पर एकत्र हो रहे कूड़े की सूचना देना "
            "चाहता/चाहती हूँ, जिसका उठान नहीं हो रहा है। कुछ समय से कूड़े का ढेर बढ़ता "
            "जा रहा है, जिससे दुर्गंध तथा मक्खियों की समस्या उत्पन्न हो गई है और आसपास "
            "के घरों एवं दुकानों के लिए यह स्वास्थ्य संबंधी चिंता का विषय है।"
        ),
        request_en=(
            "I request that the waste be cleared and that regular collection at "
            "this location be restored."
        ),
        request_hi=(
            "निवेदन है कि कूड़े का उठान करवाया जाए तथा इस स्थान पर नियमित सफ़ाई "
            "व्यवस्था पुनः सुनिश्चित की जाए।"
        ),
    ),
    WATER: _Copy(
        subject_en="Waterlogging and drainage failure",
        subject_hi="जलभराव तथा नाली की समस्या",
        problem_en=(
            "I wish to report waterlogging in this ward caused by a drain that is "
            "not carrying water away. Standing water collects on the road and does "
            "not clear for a considerable time, obstructing movement and creating "
            "conditions for mosquito breeding."
        ),
        problem_hi=(
            "मैं इस वार्ड में नाली के अवरुद्ध होने के कारण हो रहे जलभराव की सूचना देना "
            "चाहता/चाहती हूँ। सड़क पर पानी जमा हो जाता है और लंबे समय तक नहीं निकलता, "
            "जिससे आवागमन बाधित होता है तथा मच्छरों के पनपने की स्थिति बनती है।"
        ),
        request_en=(
            "I request that the drain be cleared and the standing water removed."
        ),
        request_hi=(
            "निवेदन है कि नाली की सफ़ाई करवाकर जमा पानी की निकासी सुनिश्चित की जाए।"
        ),
    ),
    OTHER: _Copy(
        subject_en="Civic issue requiring attention",
        subject_hi="नागरिक समस्या की ओर ध्यानाकर्षण",
        problem_en=(
            "I wish to report a civic issue in this ward that falls within the "
            "remit of the ward office and has not been attended to. Details and a "
            "photograph of the location are attached with this report."
        ),
        problem_hi=(
            "मैं इस वार्ड में एक ऐसी नागरिक समस्या की सूचना देना चाहता/चाहती हूँ जो "
            "वार्ड कार्यालय के कार्यक्षेत्र में आती है और जिस पर अभी तक कोई कार्रवाई "
            "नहीं हुई है। इस शिकायत के साथ स्थान का विवरण एवं छायाचित्र संलग्न है।"
        ),
        request_en=(
            "I request that the location be inspected and appropriate action taken."
        ),
        request_hi=(
            "निवेदन है कि उक्त स्थान का निरीक्षण कराकर समुचित कार्रवाई की जाए।"
        ),
    ),
}


# --------------------------------------------------------------------------
# Dates
# --------------------------------------------------------------------------

_MONTHS_EN: Final[tuple[str, ...]] = (
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
)

_MONTHS_HI: Final[tuple[str, ...]] = (
    "जनवरी", "फ़रवरी", "मार्च", "अप्रैल", "मई", "जून",
    "जुलाई", "अगस्त", "सितम्बर", "अक्टूबर", "नवम्बर", "दिसम्बर",
)


def _fmt_date(d: date, months: tuple[str, ...]) -> str:
    return f"{d.day} {months[d.month - 1]} {d.year}"


def _coerce_date(value: date | datetime | str | None) -> date:
    """Accept a date, a datetime, an ISO-8601 string, or nothing."""
    if value is None:
        return datetime.now(timezone.utc).date()
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text).date()
    except ValueError:
        return datetime.now(timezone.utc).date()


# --------------------------------------------------------------------------
# Composition
# --------------------------------------------------------------------------

_PLATFORM: Final[str] = "MERAWARD"


def _ward_line(ward_name: str, ward_id: str | None) -> str:
    return f"{ward_name} (Ward {ward_id})" if ward_id else ward_name


def compose(
    issue_type: object,
    ward_name: str,
    *,
    reported_on: date | datetime | str | None = None,
    ward_id: str | None = None,
    reference: str | None = None,
    landmark: str | None = None,
) -> Draft:
    """Compose a formal bilingual complaint.

    Args:
        issue_type: One of ``ISSUE_TYPES``. Anything else becomes ``OTHER``.
        ward_name: The ward as resolved by point-in-polygon lookup.
        reported_on: When the complaint was filed. Defaults to today (UTC).
        ward_id: Ward identifier, e.g. ``DEL-0042``. Rendered only if present.
        reference: Complaint id, rendered as a reference number if present.
        landmark: Optional free-text locality hint from the reporter.

    Returns:
        A frozen :class:`Draft` with ``source="template"``.

    The letter never names an individual and never threatens action. It is
    addressed to the ward office as an institution.
    """
    copy = _COPY[normalise_issue_type(issue_type)]
    when = _coerce_date(reported_on)

    ward = (ward_name or "").strip() or "this ward"
    ward_full = _ward_line(ward, ward_id)

    subject = f"{copy.subject_en} — {ward_full}"
    subject_hi = f"{copy.subject_hi} — {ward_full}"

    # Optional paragraphs, omitted entirely rather than rendered empty.
    landmark_en = (
        f"The reported location is near {landmark.strip()}."
        if landmark and landmark.strip()
        else ""
    )
    landmark_hi = (
        f"शिकायत का स्थान {landmark.strip()} के समीप है।"
        if landmark and landmark.strip()
        else ""
    )
    reference_en = f" The reference number for this report is {reference}." if reference else ""
    reference_hi = f" इस शिकायत की संदर्भ संख्या {reference} है।" if reference else ""

    body_en = "\n\n".join(
        part
        for part in [
            "To,\n"
            f"The Ward Office, {ward_full}\n"
            "Municipal Corporation of Delhi",
            f"Subject: {subject}",
            "Sir/Madam,",
            f"I am a resident of {ward}. {copy.problem_en}",
            landmark_en,
            f"This complaint was filed on {_fmt_date(when, _MONTHS_EN)} through "
            f"{_PLATFORM}, a public civic-reporting platform, and has been recorded "
            f"with a photograph and the location coordinates.{reference_en}",
            f"{copy.request_en} I would be grateful to be informed of the action "
            "taken and of an expected timeline.",
            "Thank you for your attention to this matter.",
            "Yours faithfully,\n" f"A resident of {ward}",
        ]
        if part
    )

    body_hi = "\n\n".join(
        part
        for part in [
            "सेवा में,\n"
            f"वार्ड कार्यालय, {ward_full}\n"
            "नगर निगम, दिल्ली",
            f"विषय: {subject_hi}",
            "महोदय/महोदया,",
            f"मैं {ward} का निवासी हूँ। {copy.problem_hi}",
            landmark_hi,
            f"यह शिकायत दिनांक {_fmt_date(when, _MONTHS_HI)} को {_PLATFORM} नामक "
            "सार्वजनिक नागरिक-शिकायत मंच के माध्यम से दर्ज की गई है, तथा इसके साथ "
            f"छायाचित्र एवं स्थान-निर्देशांक अभिलिखित हैं।{reference_hi}",
            f"{copy.request_hi} कृपया की गई कार्रवाई तथा संभावित समय-सीमा से अवगत "
            "कराने का कष्ट करें।",
            "सधन्यवाद।",
            "भवदीय,\n" f"{ward} का एक निवासी",
        ]
        if part
    )

    return Draft(subject=subject, body_en=body_en, body_hi=body_hi, source="template")
