"""Avasthās — the condition a graha is found in.

An avasthā is not a strength score. It is a STATE, and the tradition
describes several independent ones that answer different questions about the
same graha. Two are built here.

    BĀLĀDI     how far through its sign the graha has travelled, read as an
               age: infant, youth, adult, old, dead. Purely positional, and
               the direction reverses in even signs.
    JĀGRADĀDI  how awake the graha is where it sits, read from its dignity:
               awake, dreaming, asleep.

They are deliberately separate. A graha can be *yuvā* — at the strongest
point of its passage — and *suṣupti* at the same time, because being
mid-sign says nothing about whose sign it is. Collapsing the two into one
number would throw away exactly the disagreement that makes them worth
reporting.

THERE IS NO ORACLE FOR THIS, AND THAT IS STATED RATHER THAN GLOSSED
Every other computation in this build is checked against PyJHora, body by
body. PyJHora does not implement avasthās at all, so nothing here has an
independent implementation to disagree with it. What that leaves is:

  * bālādi is mechanical — five equal bands of 6°, reversed in even signs —
    so the gates assert the partition itself: the bands tile the sign with
    no gap and no overlap, the reversal is exact, and a degree on a boundary
    lands in the band the rule names.
  * jāgradādi composes from `yogas.dignity_at`, which IS gated against the
    oracle, so its inputs are checked even though its mapping is not.

That is weaker evidence than the rest of this repo runs on, and
`tools/oracle/DIFFERENTIAL.md` says so in as many words.

ON STRENGTH PROPORTIONS
Several texts attach fractions to the bālādi states — a quarter for the
infant, a half for the youth, and so on — and they do not agree with one
another. No fractions are computed here. The states are reported with their
classical sense in words, and a reading that wants to weigh them can say
which text it is weighing them by.
"""
from __future__ import annotations

from engine import PLANETS, SIGNS, Chart
from yogas import dignity_at

#: Avasthās are read for the seven. The nodes have no dignity of their own
#: — `dignity_at` returns 'neutral' for them by default rather than by
#: finding — so a jāgradādi state for a node would be an artefact of the
#: table rather than a reading of the chart.
BODIES = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn")

NODES_EXCLUDED = (
    "Rahu and Ketu are not given an avasthā: bālādi would be a bare degree "
    "reading with no tradition behind it for a shadow point, and jāgradādi "
    "rests on a dignity the nodes do not have.")

# --- bālādi: the graha's age in its sign -------------------------------------

#: Five equal bands of six degrees, in order for an ODD sign. Even signs
#: take the same bands in reverse, so a graha at 2° of Taurus is mṛta where
#: one at 2° of Aries is bāla.
BALADI_STATES = ("bala", "kumara", "yuva", "vriddha", "mrita")
BALADI_BAND = 6.0

BALADI_SENSE = {
    "bala": "an infant — present, and not yet able to deliver much of what "
            "it promises",
    "kumara": "a youth — gathering, and not yet at full reach",
    "yuva": "an adult — the strongest stretch of its passage through the "
            "sign",
    "vriddha": "old — its work largely done, and slower to act",
    "mrita": "spent — at the far end of its passage, with least to give",
}

BALADI_NAME = {
    "bala": "Bāla", "kumara": "Kumāra", "yuva": "Yuvā",
    "vriddha": "Vṛddha", "mrita": "Mṛta",
}


def _is_odd_sign(sign_index: int) -> bool:
    """Odd by SIGN NUMBER — Aries is the 1st and odd, so index 0 is odd."""
    return sign_index % 2 == 0


def baladi_at(sign_index: int, degree_in_sign: float) -> str:
    """The bālādi state of a position, as a state id.

    The band index is clamped rather than allowed to run off the end: a
    degree of exactly 30.0 is not a position inside the sign, but a caller
    that hands one over should get the last band rather than an IndexError.
    """
    band = min(int(degree_in_sign // BALADI_BAND), len(BALADI_STATES) - 1)
    if not _is_odd_sign(sign_index):
        band = len(BALADI_STATES) - 1 - band
    return BALADI_STATES[band]


def baladi(chart: Chart, planet: str) -> str:
    position = chart.planets[planet]
    return baladi_at(position.sign_index, position.degree_in_sign)


def baladi_bands(sign_index: int) -> tuple[tuple[float, float, str], ...]:
    """(from, to, state) across the whole sign, for showing the working."""
    out = []
    for index in range(len(BALADI_STATES)):
        low = index * BALADI_BAND
        out.append((low, low + BALADI_BAND,
                    baladi_at(sign_index, low + BALADI_BAND / 2)))
    return tuple(out)


# --- jāgradādi: how awake the graha is ---------------------------------------

JAGRADADI_STATES = ("jagrat", "svapna", "sushupti")

#: Dignity decides it. `yogas.dignity_at` returns exactly these five states,
#: so the mapping is total by construction — a dignity this table did not
#: anticipate would raise rather than fall through to a default, which is
#: how a new dignity state would announce itself instead of being silently
#: read as 'dreaming'.
JAGRADADI_BY_DIGNITY = {
    "exalted": "jagrat",
    "moolatrikona": "jagrat",
    "own sign": "jagrat",
    "neutral": "svapna",
    "debilitated": "sushupti",
}

JAGRADADI_SENSE = {
    "jagrat": "awake — acting as itself, in a sign that supports it",
    "svapna": "dreaming — present but working at one remove, neither "
              "supported nor obstructed",
    "sushupti": "asleep — its nature obstructed by the sign it sits in",
}

JAGRADADI_NAME = {
    "jagrat": "Jāgrat", "svapna": "Svapna", "sushupti": "Suṣupti",
}


def jagradadi_for(dignity: str) -> str:
    """The jāgradādi state for a dignity, raising on one it does not know."""
    try:
        return JAGRADADI_BY_DIGNITY[dignity]
    except KeyError:                                    # pragma: no cover
        raise ValueError(
            f"no jāgradādi state for dignity {dignity!r} — the dignity "
            f"vocabulary grew and this table did not") from None


def jagradadi(chart: Chart, planet: str) -> str:
    position = chart.planets[planet]
    return jagradadi_for(dignity_at(planet, position.sign_index,
                                    position.degree_in_sign))


# --- both at once -------------------------------------------------------------

def for_planet(chart: Chart, planet: str) -> dict:
    position = chart.planets[planet]
    age = baladi(chart, planet)
    waking = jagradadi(chart, planet)
    dignity = dignity_at(planet, position.sign_index,
                         position.degree_in_sign)
    return {
        "planet": planet,
        "sign": SIGNS[position.sign_index],
        "degree_in_sign": round(position.degree_in_sign, 4),
        "baladi": age,
        "baladi_name": BALADI_NAME[age],
        "baladi_sense": BALADI_SENSE[age],
        "jagradadi": waking,
        "jagradadi_name": JAGRADADI_NAME[waking],
        "jagradadi_sense": JAGRADADI_SENSE[waking],
        "dignity": dignity,
        # The two states are independent, and where they point different
        # ways that IS the reading — reported rather than averaged.
        "at_odds": (age == "yuva" and waking == "sushupti")
        or (age in ("bala", "mrita") and waking == "jagrat"),
    }


def describe(chart: Chart) -> dict:
    rows = [for_planet(chart, planet) for planet in BODIES]
    return {
        "avasthas": rows,
        "at_odds": [row["planet"] for row in rows if row["at_odds"]],
        "nodes_excluded": NODES_EXCLUDED,
    }
