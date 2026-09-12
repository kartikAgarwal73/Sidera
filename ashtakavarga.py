"""Aṣṭakavarga — the eight-fold strength tally, raw.

WHAT IT IS
For each of the seven grahas, the tradition gives a table: from each of eight
reference points (the seven grahas and the lagna), which houses counted from
that point receive a benefic dot — a bindu. Lay all eight rows over the
zodiac and you get that graha's Bhinnāṣṭakavarga, a twelve-value array
indexed by SIGN. Add the seven planetary arrays and you get the
Sarvāṣṭakavarga, the chart's overall distribution of support across the
zodiac.

WHAT IS AND IS NOT HERE
RAW bindus only. The reductions — trikoṇa śodhana, ekādhipatya śodhana and
the Śodhya Piṇḍa built on them — are deliberately NOT implemented. Published
implementations genuinely diverge on the order the two reductions are applied
in and on the handling of a sign with zero bindus, and shipping one reading of
a disputed method under a number that looks exact is the opposite of what this
app is for. `REDUCTIONS_NOTE` says so in the app, not only here.

THREE HAZARDS, HANDLED IN THE TYPES
  1. PER SIGN, NOT PER HOUSE. Every array here is indexed Aries→Pisces.
     Rotating to houses-from-the-lagna is a separate, named step
     (`by_house`), because a table silently rotated once is indistinguishable
     from one rotated twice.
  2. RAW, BEFORE REDUCTIONS. See above. Comparing raw against reduced is the
     classic false failure.
  3. SEVEN BAVs, NOT EIGHT. The lagna's own row is computed and reported
     separately and is NOT part of the SAV. Adding it would give 386 where
     every text says 337.

THE CHECKSUM, AND WHAT IT IS WORTH
The per-graha totals — Sun 48, Moon 49, Mars 39, Mercury 54, Jupiter 56,
Venus 52, Saturn 39, summing to 337 — are the same for EVERY chart. They
count rows in the tables below and depend on no birth moment. They gate the
transcription of a 56-row table, which is the part of this module a typo
would most plausibly land in, and they gate nothing about the computation.
The per-sign arrays are what vary between charts, and those are checked
against an independent implementation in `fixtures_pyjhora.json`.
"""
from __future__ import annotations

from dataclasses import dataclass

from engine import Chart, SIGNS

#: The seven grahas that get a Bhinnāṣṭakavarga. The nodes get none: the
#: classical tables have no row for them and none for their own varga.
BODIES = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn")

#: The eight reference points every table is counted from.
REFERENCES = BODIES + ("Lagna",)

# The benefic-point tables, from the classical enumeration. Each entry is the
# set of houses, counted from the reference point, in which the subject graha
# receives a bindu.
#
# Read one line as: "in Sun's aṣṭakavarga, counted from Mars, the 1st, 2nd,
# 4th, 7th, 8th, 9th, 10th and 11th are benefic."
#
# FOUR ROWS WERE WRONG WHEN FIRST WRITTEN DOWN, and it is worth recording how
# that surfaced, because the failure mode is the one this table invites. The
# per-graha totals were all correct — 48, 49, 39, 54, 56, 52, 39 — and the
# 337 checksum passed. It could not have caught them: a bindu written at the
# wrong offset moves where it lands and not how many there are. Only the
# per-sign comparison against an independent implementation
# (`fixtures_pyjhora.json`, both fictional charts) found them:
#
#   Moon    from Moon      9 was missing
#   Moon    from Mars      a spurious 9
#   Moon    from Jupiter   12 where the row has 2
#   Venus   from Mars      5 where the row has 4
#
# Each correction was then checked two further ways before being taken: it is
# the MINIMUM edit that reconciles both charts (an exhaustive solver over one,
# two and three rows found no smaller one and no alternative at that size),
# and each corrected row is the one the standard published enumeration
# carries. Agreeing with an oracle by editing until it agrees is fitting, not
# verifying; the minimality and the independent reading are what make this a
# correction rather than a fit.
BENEFIC_PLACES: dict[str, dict[str, tuple[int, ...]]] = {
    "Sun": {
        "Sun":     (1, 2, 4, 7, 8, 9, 10, 11),
        "Moon":    (3, 6, 10, 11),
        "Mars":    (1, 2, 4, 7, 8, 9, 10, 11),
        "Mercury": (3, 5, 6, 9, 10, 11, 12),
        "Jupiter": (5, 6, 9, 11),
        "Venus":   (6, 7, 12),
        "Saturn":  (1, 2, 4, 7, 8, 9, 10, 11),
        "Lagna":   (3, 4, 6, 10, 11, 12),
    },
    "Moon": {
        "Sun":     (3, 6, 7, 8, 10, 11),
        "Moon":    (1, 3, 6, 7, 9, 10, 11),
        "Mars":    (2, 3, 5, 6, 10, 11),
        "Mercury": (1, 3, 4, 5, 7, 8, 10, 11),
        "Jupiter": (1, 2, 4, 7, 8, 10, 11),
        "Venus":   (3, 4, 5, 7, 9, 10, 11),
        "Saturn":  (3, 5, 6, 11),
        "Lagna":   (3, 6, 10, 11),
    },
    "Mars": {
        "Sun":     (3, 5, 6, 10, 11),
        "Moon":    (3, 6, 11),
        "Mars":    (1, 2, 4, 7, 8, 10, 11),
        "Mercury": (3, 5, 6, 11),
        "Jupiter": (6, 10, 11, 12),
        "Venus":   (6, 8, 11, 12),
        "Saturn":  (1, 4, 7, 8, 9, 10, 11),
        "Lagna":   (1, 3, 6, 10, 11),
    },
    "Mercury": {
        "Sun":     (5, 6, 9, 11, 12),
        "Moon":    (2, 4, 6, 8, 10, 11),
        "Mars":    (1, 2, 4, 7, 8, 9, 10, 11),
        "Mercury": (1, 3, 5, 6, 9, 10, 11, 12),
        "Jupiter": (6, 8, 11, 12),
        "Venus":   (1, 2, 3, 4, 5, 8, 9, 11),
        "Saturn":  (1, 2, 4, 7, 8, 9, 10, 11),
        "Lagna":   (1, 2, 4, 6, 8, 10, 11),
    },
    "Jupiter": {
        "Sun":     (1, 2, 3, 4, 7, 8, 9, 10, 11),
        "Moon":    (2, 5, 7, 9, 11),
        "Mars":    (1, 2, 4, 7, 8, 10, 11),
        "Mercury": (1, 2, 4, 5, 6, 9, 10, 11),
        "Jupiter": (1, 2, 3, 4, 7, 8, 10, 11),
        "Venus":   (2, 5, 6, 9, 10, 11),
        "Saturn":  (3, 5, 6, 12),
        "Lagna":   (1, 2, 4, 5, 6, 7, 9, 10, 11),
    },
    "Venus": {
        "Sun":     (8, 11, 12),
        "Moon":    (1, 2, 3, 4, 5, 8, 9, 11, 12),
        "Mars":    (3, 4, 6, 9, 11, 12),
        "Mercury": (3, 5, 6, 9, 11),
        "Jupiter": (5, 8, 9, 10, 11),
        "Venus":   (1, 2, 3, 4, 5, 8, 9, 10, 11),
        "Saturn":  (3, 4, 5, 8, 9, 10, 11),
        "Lagna":   (1, 2, 3, 4, 5, 8, 9, 11),
    },
    "Saturn": {
        "Sun":     (1, 2, 4, 7, 8, 10, 11),
        "Moon":    (3, 6, 11),
        "Mars":    (3, 5, 6, 10, 11, 12),
        "Mercury": (6, 8, 9, 10, 11, 12),
        "Jupiter": (5, 6, 11, 12),
        "Venus":   (6, 11, 12),
        "Saturn":  (3, 5, 6, 11),
        "Lagna":   (1, 3, 4, 6, 10, 11),
    },
    # The lagna's own row. Computed and reported, never summed into the SAV.
    "Lagna": {
        "Sun":     (3, 4, 6, 10, 11, 12),
        "Moon":    (3, 6, 10, 11, 12),
        "Mars":    (1, 3, 6, 10, 11),
        "Mercury": (1, 2, 4, 6, 8, 10, 11),
        "Jupiter": (1, 2, 4, 5, 6, 7, 9, 10, 11),
        "Venus":   (1, 2, 3, 4, 5, 8, 9),
        "Saturn":  (1, 3, 4, 6, 10, 11),
        "Lagna":   (3, 6, 10, 11),
    },
}

#: Stated in the app, not only in this docstring. See the module note.
REDUCTIONS_NOTE = (
    "These are RAW bindus. The classical reductions — trikoṇa and "
    "ekādhipatya śodhana, and the Śodhya Piṇḍa built on them — are not "
    "applied: published implementations disagree about the order the two "
    "are performed in and about a sign left with none, and a disputed "
    "method printed as an exact number would be worse than no number."
)

#: The classical per-graha totals. Chart-invariant: they count rows in the
#: tables above. See the module docstring on what that is worth.
CLASSICAL_TOTALS = {"Sun": 48, "Moon": 49, "Mars": 39, "Mercury": 54,
                    "Jupiter": 56, "Venus": 52, "Saturn": 39}
CLASSICAL_SAV_TOTAL = 337
CLASSICAL_LAGNA_TOTAL = 49


@dataclass(frozen=True)
class Ashtakavarga:
    """One chart's raw tally.

    Every array is indexed BY SIGN, Aries first. `by_house` is the only
    thing that rotates, and it is named for what it does.
    """

    bav_by_sign: dict[str, tuple[int, ...]]      # the seven grahas
    sav_by_sign: tuple[int, ...]                 # their sum, per sign
    lagna_bav_by_sign: tuple[int, ...]           # reported, never summed in
    lagna_sign_index: int

    @property
    def sav_total(self) -> int:
        return sum(self.sav_by_sign)

    def by_house(self, row: tuple[int, ...]) -> dict[int, int]:
        """A per-sign array rotated to houses counted from the lagna.

        Whole Sign, so house n is the nth sign from the lagna's. Kept as an
        explicit call rather than a stored field: a table silently rotated
        once is indistinguishable from one rotated twice, and this app has
        already been bitten by a value that was right in one frame and
        printed in another.
        """
        return {h: row[(self.lagna_sign_index + h - 1) % 12]
                for h in range(1, 13)}

    @property
    def sav_by_house(self) -> dict[int, int]:
        return self.by_house(self.sav_by_sign)

    def sign_of_house(self, house: int) -> str:
        return SIGNS[(self.lagna_sign_index + house - 1) % 12]


def _row(chart: Chart, subject: str) -> tuple[int, ...]:
    """One Bhinnāṣṭakavarga, per sign."""
    counts = [0] * 12
    for ref, places in BENEFIC_PLACES[subject].items():
        base = (chart.lagna.sign_index if ref == "Lagna"
                else chart.planets[ref].sign_index)
        for offset in places:
            counts[(base + offset - 1) % 12] += 1
    return tuple(counts)


def ashtakavarga(chart: Chart) -> Ashtakavarga:
    bav = {p: _row(chart, p) for p in BODIES}
    sav = tuple(sum(bav[p][s] for p in BODIES) for s in range(12))
    return Ashtakavarga(bav_by_sign=bav, sav_by_sign=sav,
                        lagna_bav_by_sign=_row(chart, "Lagna"),
                        lagna_sign_index=chart.lagna.sign_index)


# --- the reading --------------------------------------------------------------

#: Where the tradition draws its own lines. A sign carrying 28 or more is
#: read as well supported and one carrying 25 OR FEWER as thin; 26 and 27
#: are unremarkable and are not dressed up as a finding.
#:
#: BOTH EDGES ARE INCLUSIVE, and this comment used to say "under 25" — a
#: strict comparison — while `app.py` and `chartfacts.py` both implemented
#: `<= 25`. On the reference chart the 12th sits at exactly 25 and was
#: called thin by the app and unremarkable by its own documentation. The
#: prose was wrong, not the code: nothing a reader sees moved.
#:
#: `TestInterpretationThresholds` now pins both edges. It exists because a
#: mutation survey moved STRONG_FLOOR from 28 to 20 — taking this chart
#: from four strong houses to twelve — and the entire suite stayed green.
STRONG_FLOOR = 28
THIN_CEILING = 25


def strongest(av: Ashtakavarga, n: int = 2) -> list[tuple[int, int]]:
    """The n houses with the most bindus, as (house, score), best first."""
    rows = sorted(av.sav_by_house.items(), key=lambda kv: (-kv[1], kv[0]))
    return rows[:n]


def thinnest(av: Ashtakavarga, n: int = 2) -> list[tuple[int, int]]:
    rows = sorted(av.sav_by_house.items(), key=lambda kv: (kv[1], kv[0]))
    return rows[:n]


def _ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        return f"{n}th"
    return f"{n}{ {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th') }"


def verdict(av: Ashtakavarga) -> str:
    """The founder's sentence, verbatim in shape:

        "your strongest houses are the 8th at 34 and the 6th at 33; the
        thinnest are the 4th at 24 and the 9th at 24"

    Answer first: the four numbers a reader can act on, before the grid.
    """
    top = strongest(av)
    low = thinnest(av)
    def phrase(rows):
        return " and ".join(f"the {_ordinal(h)} at {v}" for h, v in rows)
    return (f"Your strongest houses are {phrase(top)}; the thinnest are "
            f"{phrase(low)}.")
