"""Verification fixtures — the birth records the gate suite is anchored to.

WHY THIS FILE EXISTS
Sidera's claim is that its numbers are checkable. That claim is carried by a
handful of charts whose expected values came from OUTSIDE this build, and the
suite asserts against them (see `conftest.py` for how provenance is tracked).
Those charts are real birth records, so they live in one place, they are
overridable, and they can be removed without touching a single test.

OVERRIDING
Point `SIDERA_FIXTURES` at a JSON file to supply your own:

    SIDERA_FIXTURES=/path/to/fixtures.json pytest

    {"reference": {"year": 1990, "month": 3, "day": 15, "hour": 8,
                   "minute": 45, "latitude": 19.07283, "longitude": 72.88261,
                   "tz": "Asia/Kolkata", "place": "Mumbai"}}

Tests anchored to the built-in reference values are skipped when a different
reference is supplied — its expected positions are not known to this build,
and inventing them would defeat the point of an external anchor.

ON THE DEFAULT REFERENCE CHART — AND WHAT IT IS WORTH
The committed chart is fictional (see below), so **no real birth record lives
in this repository**. That has a cost worth stating plainly: the original
Phase 1–5 gate values were supplied and independently verified by the author
against his own records, which made them a genuine *external* anchor. A
fictional chart cannot carry that by itself — recomputing its positions with
the same ephemeris and asserting they match is circular.

Two things restore real anchoring, and the gate suite carries both:

  * `TestIndependentEphemerisCrossCheck` — every position in the reference
    chart, recomputed with ERFA (the IAU SOFA-derived library), agreeing
    with swisseph to under an arcminute. A SECOND ephemeris is an outside
    source in a way our own never is. Regenerate the constants with
    `python tools/erfa_cross_check.py` (needs `pip install pyerfa numpy`;
    dev-only, not an app dependency).

  * `TestAstronomicalAnchors` — published, person-free facts: Spica at 180°
    (the definition of the Lahiri ayanāṃśa), the ayanāṃśa's standard value
    at epoch, and a catalogued total solar eclipse. No chart involved.

Everything downstream of the chart — which yogas fire, which daśās run, what
the page renders — is `characterization` and is declared so in `conftest.py`,
rather than relabelled to keep the counts looking strong.

To run the original private gates, supply the real chart via
`SIDERA_FIXTURES`; the chart-specific tests then skip, because their
committed expectations belong to the fictional chart.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from engine import BirthData

# The committed reference chart is FICTIONAL: "Aisha Rao", the sample persona
# named by the Sidera Framework document, with her birth data corrected — as
# the document writes it (14 Aug 1998, 04:32) it does not produce the values
# the document itself states. See ui-design/FRAMEWORK-AUDIT.md.
#
# No real person's birth record is committed to this repository.
_DEFAULT_AISHA = {
    "year": 1998, "month": 8, "day": 16, "hour": 6, "minute": 57,
    "latitude": 26.9124, "longitude": 75.7873,
    "tz": "+05:30", "place": "Jaipur",
}

# A second fictional record, "Dev Menon", so the Guṇa Milan and match-UI
# gates pair two DIFFERENT charts. Pairing a chart with itself would make
# the aṣṭakūṭa tables look symmetric and every kūṭa full — the opposite of
# what those tests exist to prove.
_DEFAULT_PARTNER = {
    "year": 1993, "month": 2, "day": 4, "hour": 15, "minute": 40,
    "latitude": 18.5204, "longitude": 73.8567,
    "tz": "+05:30", "place": "Pune",
}

_BUILT_IN = {
    "reference": _DEFAULT_AISHA,
    "aisha": _DEFAULT_AISHA,
    "partner": _DEFAULT_PARTNER,
}


def _loaded() -> dict:
    path = os.environ.get("SIDERA_FIXTURES", "").strip()
    if not path:
        return dict(_BUILT_IN)
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    merged = dict(_BUILT_IN)
    merged.update(data)
    return merged


def birth(name: str = "reference") -> BirthData:
    """The named fixture as a BirthData."""
    spec = _loaded()[name]
    if spec is None:
        raise KeyError(f"fixture {name!r} has been removed; set SIDERA_FIXTURES")
    return BirthData(**spec)


def is_built_in(name: str = "reference") -> bool:
    """True when the fixture still holds this build's own anchor values.

    Gate assertions that hard-code expected positions are only meaningful
    for the built-in charts; they skip otherwise.
    """
    return _loaded().get(name) == _BUILT_IN[name]
