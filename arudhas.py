"""Bhāva arudhas A1–A12, and the Upapada Lagna read for marriage.

WHAT AN ARUDHA IS
A house says what a matter *is*; its arudha says how that matter *appears* —
the image the world sees. It is counted by reflection: as far as the lord has
travelled from its house, count that far again from the lord.

    A(n) = the sign as far from the lord's sign as the lord's sign is from
           house n.

with one classical exception: an image cannot fall on the thing it is an image
of, nor directly opposite it. If the count lands on the house itself or the
7th from it, the 10th from that is taken instead.

THE UPAPADA (A12) is the arudha of the 12th and is read for marriage and the
spouse. That is why this module exists now rather than later.

THE FORK, AND WHY IT IS NOT DECIDED HERE
An arudha is counted FROM THE LORD, so a house whose sign has two lords has
two possible counts. Scorpio is shared by Mars and Ketu, Aquarius by Saturn
and Rahu, and the tradition does not speak with one voice:

    Parāśarī   the sole classical lord — Mars for Scorpio, Saturn for
               Aquarius. The nodes own no sign. This is the recommended
               default and what most software does.
    Jaimini    the STRONGER of the two co-lords, decided per chart, so Ketu
               or Rahu can carry the count.

The 12th is Scorpio or Aquarius in a sixth of all charts, and when it is, the
Upapada itself is contested — which is not academic when it is being read for
someone's marriage. `schools.py` asks the reader in plain English and this
module answers to that choice; nothing here picks a winner.

ON THE STRENGTH RULES
The Jaimini comparison is a hierarchy, applied in order, and it is written
here from the tradition rather than transcribed from another implementation
— an oracle that we had copied would no longer be an independent check of
anything. See `TestArudhas` for what that costs: the two agree exactly on the
Parāśarī school and on both fixtures, and part company on a measured minority
of random charts at the tie-break levels. The disagreement is recorded, not
hidden.
"""
from __future__ import annotations

from engine import PLANETS, SIGNS, Chart

import schools

#: Sign rulers, Aries first. The nodes rule nothing — that is the whole
#: subject of the fork below.
SIGN_LORDS = ("Mars", "Venus", "Mercury", "Moon", "Sun", "Mercury",
              "Venus", "Mars", "Jupiter", "Saturn", "Saturn", "Jupiter")

#: The two signs with a second, disputed lord, and their pair in the order
#: (classical sole lord, node).
CO_LORDS: dict[int, tuple[str, str]] = {
    7: ("Mars", "Ketu"),       # Scorpio
    10: ("Saturn", "Rahu"),    # Aquarius
}

#: The sign each node is held to co-rule.
NODE_SIGN = {"Ketu": 7, "Rahu": 10}

#: Exaltation signs, for the strength hierarchy's third step.
EXALTATION = {"Sun": 0, "Moon": 1, "Mars": 9, "Mercury": 5, "Jupiter": 3,
              "Venus": 11, "Saturn": 6, "Rahu": 1, "Ketu": 7}

MOVABLE, FIXED, DUAL = 0, 1, 2


def modality(sign_index: int) -> int:
    """0 movable, 1 fixed, 2 dual — Aries is movable and the cycle repeats."""
    return sign_index % 3


def rasi_drishti(sign_index: int) -> tuple[int, ...]:
    """Signs that `sign_index` aspects by RĀŚI drishti.

    Jaimini's sign-to-sign aspect, which is a different system from the graha
    drishti in `transits.py` and is not interchangeable with it: movable signs
    look at the fixed signs, fixed at the movable, dual at dual — each
    excepting its own immediate neighbour, which is too close to be seen.
    """
    mode = modality(sign_index)
    if mode == MOVABLE:
        return tuple(s for s in range(12)
                     if modality(s) == FIXED and s != (sign_index + 1) % 12)
    if mode == FIXED:
        return tuple(s for s in range(12)
                     if modality(s) == MOVABLE and s != (sign_index - 1) % 12)
    return tuple(s for s in range(12)
                 if modality(s) == DUAL and s != sign_index)


def _signs_of(chart: Chart) -> dict[str, int]:
    return {p: chart.planets[p].sign_index for p in PLANETS}


def stronger_co_lord(chart: Chart, classical: str,
                     node: str) -> tuple[str, str]:
    """(winner, the step that decided it) for a disputed sign's two lords.

    The classical hierarchy, in order. Each step only speaks when the one
    above it was silent, which is why the step is returned — a verdict that
    rests on the modality of a sign is a weaker claim than one that rests on
    a planet being exalted, and a reader is entitled to know which they have.
    """
    signs = _signs_of(chart)
    own = NODE_SIGN[node]
    classical_sign, node_sign = signs[classical], signs[node]

    # 0. THE SIGN ITSELF. A planet sitting in the disputed sign does not
    #    thereby win it: the tradition gives the count to the OTHER of the
    #    pair, the one whose claim is not merely positional.
    if classical_sign == own and node_sign != own:
        return node, "occupancy"
    if node_sign == own and classical_sign != own:
        return classical, "occupancy"

    # 1. COMPANY. The planet with more bodies in its sign is stronger. The
    #    lagna counts as one of them — in Jaimini it is a point of strength
    #    in its own right, not merely a reference for counting houses.
    def company(planet: str) -> int:
        sign = signs[planet]
        return (sum(1 for other, s in signs.items()
                    if other != planet and s == sign)
                + (1 if chart.lagna.sign_index == sign else 0))

    if company(classical) != company(node):
        return ((classical if company(classical) > company(node) else node),
                "company")

    # 2. GOOD COMPANY, specifically: Jupiter, Mercury and the dispositor,
    #    whether sitting in the sign or aspecting it by rāśi drishti.
    def support(planet: str) -> int:
        sign = signs[planet]
        wanted = ("Mercury", "Jupiter", SIGN_LORDS[sign])
        seen = rasi_drishti(sign)
        return (sum(1 for w in wanted if signs.get(w) == sign)
                + sum(1 for w in wanted if signs.get(w) in seen))

    if support(classical) != support(node):
        return ((classical if support(classical) > support(node) else node),
                "support")

    # 3. EXALTATION. One exalted and the other not settles it.
    exalted = {p: signs[p] == EXALTATION[p] for p in (classical, node)}
    if exalted[classical] != exalted[node]:
        return (classical if exalted[classical] else node), "exaltation"

    # 4. THE SIGN'S OWN NATURE: dual is stronger than fixed, fixed than
    #    movable.
    rank = {MOVABLE: 1, FIXED: 2, DUAL: 3}
    by_sign = (rank[modality(classical_sign)], rank[modality(node_sign)])
    if by_sign[0] != by_sign[1]:
        return (classical if by_sign[0] > by_sign[1] else node), "modality"

    # 5. NOTHING SEPARATES THEM. The classical lord keeps the count — said
    #    out loud rather than left to the order of a comparison, because a
    #    tie resolved silently is indistinguishable from a rule that fired.
    return classical, "undecided"


def counting_lord(chart: Chart, sign_index: int) -> tuple[str, str]:
    """(the lord an arudha is counted from, why) under the live school."""
    if sign_index not in CO_LORDS:
        return SIGN_LORDS[sign_index], "sole lord"
    classical, node = CO_LORDS[sign_index]
    if schools.chosen("dual_lord").id == "single":
        return classical, "sole lord (Parāśarī)"
    winner, step = stronger_co_lord(chart, classical, node)
    return winner, f"stronger co-lord by {step}"


def arudha_pada(chart: Chart, house: int) -> int:
    """The arudha of one house (1–12), as a sign index."""
    house_sign = (chart.lagna.sign_index + house - 1) % 12
    lord, _ = counting_lord(chart, house_sign)
    lord_sign = chart.planets[lord].sign_index
    distance = (lord_sign - house_sign) % 12
    pada = (lord_sign + distance) % 12
    # The image may fall neither on the house nor opposite it.
    if (pada - house_sign) % 12 in (0, 6):
        pada = (pada + 9) % 12
    return pada


def arudhas(chart: Chart) -> tuple[int, ...]:
    """A1…A12 as sign indices, in house order."""
    return tuple(arudha_pada(chart, h) for h in range(1, 13))


def upapada(chart: Chart) -> int:
    """The Upapada Lagna — A12 — as a sign index."""
    return arudha_pada(chart, 12)


def upapada_house(chart: Chart) -> int:
    """The house the Upapada falls in, counted from the natal lagna."""
    return (upapada(chart) - chart.lagna.sign_index) % 12 + 1


def contested_houses(chart: Chart) -> tuple[int, ...]:
    """Houses whose sign has two lords, so whose arudha depends on the
    school. Empty for most charts; the reader is only told when it matters."""
    return tuple(h for h in range(1, 13)
                 if (chart.lagna.sign_index + h - 1) % 12 in CO_LORDS)


def upapada_is_contested(chart: Chart) -> bool:
    return 12 in contested_houses(chart)


def both_schools(chart: Chart) -> dict[str, tuple[int, ...]]:
    """A1…A12 under each school, for showing a disagreement side by side.

    The resolver needs both to report a conflict rather than resolve one, so
    they are computed together here instead of by switching a global twice at
    the call site.
    """
    out = {}
    for answer in ("single", "stronger"):
        with schools.use({**schools.active(), "dual_lord": answer}):
            out[answer] = arudhas(chart)
    return out


def schools_agree(chart: Chart) -> bool:
    values = both_schools(chart)
    return values["single"] == values["stronger"]


def describe(chart: Chart) -> dict:
    """Everything a reading or a ledger fact needs, computed once."""
    padas = arudhas(chart)
    ul = padas[11]
    occupants = [p for p in PLANETS if chart.planets[p].sign_index == ul]
    return {
        "arudhas": padas,
        "arudha_signs": [SIGNS[s] for s in padas],
        "upapada_sign_index": ul,
        "upapada_sign": SIGNS[ul],
        "upapada_house": (ul - chart.lagna.sign_index) % 12 + 1,
        "upapada_occupants": occupants,
        "upapada_lord": SIGN_LORDS[ul],
        "contested_houses": contested_houses(chart),
        "upapada_contested": upapada_is_contested(chart),
        "schools_agree": schools_agree(chart),
        "school": schools.chosen("dual_lord").school,
    }
