"""Viṃśopaka bala — a graha's strength read across the divisional charts.

WHAT IT IS
A graha can be splendid in the birth chart and homeless in every division
under it, and the birth chart alone will not say so. Viṃśopaka asks the same
question of a whole group of charts at once: in each one, is this graha in
its own sign, among friends, or among enemies? Each division carries a
weight, the weights of a group sum to twenty, and the answer is a score out
of twenty.

THE LADDER, per division
    own sign                        20
    great friend of the dispositor  18
    friend                          15
    neutral                         10
    enemy                            7
    great enemy                      5
and the division contributes `weight × value / 20`.

THE GROUP IS A FORK, and a consequential one — it is not a detail of
presentation. The four classical groups weight different charts, so the same
graha scores differently under each, and a reader comparing Sidera against
another astrologer needs to know which group produced the number. It is
`vimsopaka_group` in schools.py.

    ṣaḍvarga      6 charts   D1 D2 D3 D9 D12 D30
    saptavarga    7          + D7
    daśavarga    10          D1 D2 D3 D7 D9 D10 D12 D16 D30 D60
    ṣoḍaśavarga  16          all sixteen

THE SEVEN, NOT THE NINE
Viṃśopaka is computed for the seven visible grahas and not for Rahu and
Ketu. That is not squeamishness: the score rests on owning a sign and on
being a friend or enemy OF THE SIGN'S LORD, and the nodes rule nothing, so
both halves of the ladder are undefined for them. Implementations that do
score the nodes must first invent a lordship and a friendship table for
them, and those are not agreed. `NODES_EXCLUDED` says so where a reading can
print it rather than leaving a reader to wonder at a missing row.
"""
from __future__ import annotations

from engine import PLANETS, SIGNS, Chart
from yogas import natural_relation

import arudhas
import schools
import vargas

#: The seven. See the module docstring on why the nodes are not here.
BODIES = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn")

NODES_EXCLUDED = (
    "Rahu and Ketu are not scored: viṃśopaka rests on owning a sign and on "
    "friendship with the sign's lord, and the nodes rule no sign.")

#: Houses from a graha whose occupants are its TEMPORARY friends. The rest —
#: the 1st, 5th, 6th, 7th, 8th and 9th — are temporary enemies. Nearness is
#: friendship here, which is why the set is the ring around the graha.
TEMPORAL_FRIEND_HOUSES = frozenset({2, 3, 4, 10, 11, 12})

#: Natural + temporal, combined into the five-fold (pañcadhā maitrī) scale.
#: 4 is a great friend and 0 a great enemy.
_COMPOUND = {
    ("friend", "friend"): 4,
    ("friend", "enemy"): 2,
    ("neutral", "friend"): 3,
    ("neutral", "enemy"): 1,
    ("enemy", "friend"): 2,
    ("enemy", "enemy"): 0,
}

COMPOUND_NAMES = ("great enemy", "enemy", "neutral", "friend", "great friend")

#: What each rung of the compound scale is worth. Own sign is 20 and is
#: handled separately — it is not a relationship, it is being at home.
COMPOUND_VALUE = (5, 7, 10, 15, 18)
OWN_SIGN_VALUE = 20

#: The four classical groups. Every one sums to twenty, which is what makes
#: the score comparable across them — `TestVimsopaka` asserts it rather than
#: trusting the arithmetic here.
GROUPS: dict[str, dict[str, float]] = {
    "shadvarga": {"D1": 6, "D2": 2, "D3": 4, "D9": 5, "D12": 2, "D30": 1},
    "saptavarga": {"D1": 5, "D2": 2, "D3": 3, "D7": 1, "D9": 2.5,
                   "D12": 4.5, "D30": 2},
    "dashavarga": {"D1": 3, "D2": 1.5, "D3": 1.5, "D7": 1.5, "D9": 1.5,
                   "D10": 1.5, "D12": 1.5, "D16": 1.5, "D30": 1.5, "D60": 5},
    "shodasavarga": {"D1": 3.5, "D2": 1, "D3": 1, "D4": 0.5, "D7": 0.5,
                     "D9": 3, "D10": 0.5, "D12": 0.5, "D16": 2, "D20": 0.5,
                     "D24": 0.5, "D27": 0.5, "D30": 1, "D40": 0.5,
                     "D45": 0.5, "D60": 4},
}

GROUP_LABEL = {
    "shadvarga": "ṣaḍvarga — six charts",
    "saptavarga": "saptavarga — seven charts",
    "dashavarga": "daśavarga — ten charts",
    "shodasavarga": "ṣoḍaśavarga — all sixteen",
}


def group() -> str:
    """The live group, from the school registry."""
    return schools.chosen("vimsopaka_group").id


def temporal_relation(chart: Chart, of: str, towards: str) -> str:
    """'friend' | 'enemy' — decided by where the two sit in the BIRTH chart.

    Temporary friendship is a fact about this chart and not about the
    grahas, and it is read from D1 even when scoring a division: a graha's
    companions are its companions wherever else it is being looked at.
    """
    distance = (chart.planets[towards].sign_index
                - chart.planets[of].sign_index) % 12 + 1
    return "friend" if distance in TEMPORAL_FRIEND_HOUSES else "enemy"


def compound_relation(chart: Chart, of: str, towards: str) -> int:
    """0–4 on the five-fold scale, from `of`'s point of view."""
    return _COMPOUND[(natural_relation(of, towards),
                      temporal_relation(chart, of, towards))]


def compound_name(chart: Chart, of: str, towards: str) -> str:
    return COMPOUND_NAMES[compound_relation(chart, of, towards)]


def _sign_in(chart: Chart, planet: str, code: str) -> int:
    if code == "D1":
        return chart.planets[planet].sign_index
    return vargas.varga_chart(chart, code).planets[planet].sign_index


def dispositor(chart: Chart, sign_index: int) -> str:
    """The lord of a sign, UNDER THE LIVE CO-LORD SCHOOL.

    Scorpio and Aquarius have two claimed lords, and viṃśopaka asks how a
    graha stands with the lord of the sign it is in — so the `dual_lord`
    question the arudhas already put to the reader decides this too. It is
    not a detail: on the reference chart the Sun in Scorpio scores 18 with
    Mars as the dispositor and 15 with Ketu, and that difference propagates
    into every group the D12 appears in.

    `arudhas.counting_lord` is the one implementation of that choice, so it
    is called rather than copied.
    """
    return arudhas.counting_lord(chart, sign_index)[0]


def value_in(chart: Chart, planet: str, code: str) -> tuple[int, str]:
    """(value out of 20, why) for one graha in one division."""
    sign = _sign_in(chart, planet, code)
    lord = dispositor(chart, sign)
    if lord == planet:
        return OWN_SIGN_VALUE, "own sign"
    rung = compound_relation(chart, planet, lord)
    return COMPOUND_VALUE[rung], f"{COMPOUND_NAMES[rung]} of {lord}"


def score(chart: Chart, planet: str, which: str | None = None) -> float:
    """One graha's viṃśopaka out of twenty, under the given group."""
    weights = GROUPS[which or group()]
    return sum(weight * value_in(chart, planet, code)[0] / OWN_SIGN_VALUE
               for code, weight in weights.items())


def scores(chart: Chart, which: str | None = None) -> dict[str, float]:
    which = which or group()
    return {p: score(chart, p, which) for p in BODIES}


def working(chart: Chart, planet: str,
            which: str | None = None) -> list[dict]:
    """The per-division breakdown, so a score can show its own arithmetic."""
    which = which or group()
    out = []
    for code, weight in GROUPS[which].items():
        value, why = value_in(chart, planet, code)
        out.append({
            "varga": code, "weight": weight, "sign": SIGNS[
                _sign_in(chart, planet, code)],
            "value": value, "why": why,
            "contributes": round(weight * value / OWN_SIGN_VALUE, 4),
        })
    return out


#: Where the tradition draws its own lines on the twenty-point scale.
STRONG_FLOOR = 15.0
THIN_CEILING = 10.0


def band(value: float) -> str:
    if value >= STRONG_FLOOR:
        return "strong"
    if value < THIN_CEILING:
        return "thin"
    return "middling"


def describe(chart: Chart, which: str | None = None) -> dict:
    """Everything a reading or a ledger fact needs, computed once."""
    which = which or group()
    values = scores(chart, which)
    ranked = sorted(values.items(), key=lambda kv: (-kv[1], kv[0]))
    return {
        "group": which,
        "group_label": GROUP_LABEL[which],
        "charts": sorted(GROUPS[which], key=lambda c: int(c[1:])),
        "school": schools.chosen("vimsopaka_group").school,
        "scores": {p: round(v, 4) for p, v in values.items()},
        "bands": {p: band(v) for p, v in values.items()},
        "strongest": ranked[0][0],
        "thinnest": ranked[-1][0],
        "nodes_excluded": NODES_EXCLUDED,
    }
