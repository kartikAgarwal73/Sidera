"""Chara karakas — the movable significators — and the Kārakāṃśa.

WHAT THESE ARE
A natural significator never changes: Venus signifies the wife in every
chart ever cast. A CHARA karaka is the opposite — it is assigned by the
chart itself. Rank the grahas by how far each has travelled into its sign,
highest first, and the list of offices falls out in order: the graha at the
greatest degree is the Ātmakāraka, the soul's significator, down to the
Dārakāraka, the significator of the spouse.

That makes the Dārakāraka the second thing a marriage reading wants, after
the Upapada, and it is why this module lands here.

THE FORK
The tradition does not agree on how many offices there are.

    Seven   The seven grahas alone. Rahu and Ketu are shadows, not bodies;
            they signify nothing of their own and take no office.
    Eight   Rahu is admitted, which inserts a Pitṛkāraka between the Mātṛ
            and Putra offices and shifts every office below it. Ketu stays
            out under both schemes — it is nobody's significator.

Because Rahu moves backwards, its degree is counted BACKWARDS too: a Rahu
at 7° of its sign has, in its own direction of travel, 23° behind it. That
is not a fudge to make the numbers work; it is the same fact that makes
Rahu's dasha run from a different point than every other graha's.

Admitting Rahu does not merely add an eighth name to the end of the list.
It can take a senior office and push everything below it down one, so the
Dārakāraka under the two schemes is frequently a different graha entirely
— which is exactly why this is a question put to the reader rather than a
constant.

ON THE TIE
Two grahas at the identical degree of their signs is vanishingly rare and
not addressed by the classical sources, so the convention is written down
rather than left to whatever order a sort happened to produce: degrees are
compared at full precision, and where even that is equal the natural order
of the grahas — Sun first, Saturn last, Rahu after Saturn — takes the more
senior office. `rule.karaka.tie_convention` says so in those words. A tie
broken silently by the order of a dictionary is not a rule; it is a bug
waiting for the day two grahas line up.
"""
from __future__ import annotations

from dataclasses import dataclass

from engine import PLANETS, SIGNS, Chart

import schools
import vargas

#: The seven grahas, in the natural order the tie convention uses.
SEVEN = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn")

#: The eight-karaka scheme admits Rahu, and only Rahu.
EIGHT = SEVEN + ("Rahu",)

#: Offices in rank order, per scheme. Admitting Rahu inserts Pitṛ and moves
#: every office below it down one — including the Dārakāraka.
OFFICES_7 = ("Atmakaraka", "Amatyakaraka", "Bhratrikaraka", "Matrikaraka",
             "Putrakaraka", "Gnatikaraka", "Darakaraka")
OFFICES_8 = ("Atmakaraka", "Amatyakaraka", "Bhratrikaraka", "Matrikaraka",
             "Pitrikaraka", "Putrakaraka", "Gnatikaraka", "Darakaraka")

#: What each office signifies, in plain words.
SIGNIFIES = {
    "Atmakaraka": "the self, and what the life is actually for",
    "Amatyakaraka": "the counsel one keeps, and the work one is advised into",
    "Bhratrikaraka": "siblings, and courage",
    "Matrikaraka": "the mother, and what nourishes",
    "Pitrikaraka": "the father, and inherited standing",
    "Putrakaraka": "children, and what one creates",
    "Gnatikaraka": "kin, rivals, and obstruction",
    "Darakaraka": "the spouse, and partnership",
}

#: Short forms, as the texts write them.
ABBR = {"Atmakaraka": "AK", "Amatyakaraka": "AmK", "Bhratrikaraka": "BK",
        "Matrikaraka": "MK", "Pitrikaraka": "PiK", "Putrakaraka": "PK",
        "Gnatikaraka": "GK", "Darakaraka": "DK"}


@dataclass(frozen=True)
class Karaka:
    office: str
    planet: str
    degree_in_sign: float
    #: The value actually ranked — the degree itself, or 30° minus it for
    #: Rahu. Carried so a reading can show its own working.
    ranked_by: float
    reversed_for_rahu: bool = False

    @property
    def abbr(self) -> str:
        return ABBR[self.office]

    @property
    def signifies(self) -> str:
        return SIGNIFIES[self.office]


def scheme() -> str:
    """'seven' or 'eight', from the live school."""
    return schools.chosen("karaka_count").id


def _bodies(which: str) -> tuple[str, ...]:
    return EIGHT if which == "eight" else SEVEN


def _offices(which: str) -> tuple[str, ...]:
    return OFFICES_8 if which == "eight" else OFFICES_7


def ranking_value(planet: str, degree_in_sign: float) -> float:
    """What a graha is ranked by. Rahu counts its degree backwards."""
    return (30.0 - degree_in_sign) if planet == "Rahu" else degree_in_sign


def karakas(chart: Chart, which: str | None = None) -> tuple[Karaka, ...]:
    """The chara karakas in rank order, Ātmakāraka first."""
    which = which or scheme()
    bodies = _bodies(which)
    offices = _offices(which)

    def sort_key(planet: str):
        degree = chart.planets[planet].degree_in_sign
        # Descending by ranked degree; on an exact tie the natural order of
        # the grahas decides, and it decides EXPLICITLY. See the module
        # docstring and rule.karaka.tie_convention.
        return (-ranking_value(planet, degree), bodies.index(planet))

    ordered = sorted(bodies, key=sort_key)
    out = []
    for office, planet in zip(offices, ordered):
        degree = chart.planets[planet].degree_in_sign
        out.append(Karaka(
            office=office, planet=planet, degree_in_sign=degree,
            ranked_by=ranking_value(planet, degree),
            reversed_for_rahu=(planet == "Rahu"),
        ))
    return tuple(out)


def by_office(chart: Chart, which: str | None = None) -> dict[str, Karaka]:
    return {k.office: k for k in karakas(chart, which)}


def atmakaraka(chart: Chart, which: str | None = None) -> Karaka:
    return karakas(chart, which)[0]


def darakaraka(chart: Chart, which: str | None = None) -> Karaka:
    return karakas(chart, which)[-1]


def karakamsa(chart: Chart, which: str | None = None) -> dict:
    """The Kārakāṃśa: the D9 sign the Ātmakāraka occupies.

    The Ātmakāraka is what the life is for; the navāṃśa is where a natal
    promise is tested. The sign where those two meet is read as the field
    the self is worked out in — so it is reported with its house from the
    D9 lagna, which is the frame that sign sits in.
    """
    ak = atmakaraka(chart, which)
    navamsa = vargas.varga_chart(chart, "D9")
    position = navamsa.planets[ak.planet]
    return {
        "planet": ak.planet,
        "sign_index": position.sign_index,
        "sign": SIGNS[position.sign_index],
        "house_from_d9_lagna": position.house,
        "d9_lagna_sign": navamsa.lagna_sign,
        "degree_in_sign": position.degree_in_sign,
        "vargottama": position.vargottama,
    }


def tie_groups(chart: Chart, which: str | None = None) -> list[list[str]]:
    """Grahas ranked at exactly the same value, if any.

    Reported rather than hidden: where this is non-empty the order below it
    rests on a convention and not on the chart, and a reading that says so
    is worth more than one that does not know.
    """
    which = which or scheme()
    seen: dict[float, list[str]] = {}
    for planet in _bodies(which):
        value = ranking_value(planet, chart.planets[planet].degree_in_sign)
        seen.setdefault(value, []).append(planet)
    return [group for group in seen.values() if len(group) > 1]


def both_schemes(chart: Chart) -> dict[str, dict[str, str]]:
    """Office → graha under each scheme, for showing a fork side by side."""
    return {which: {k.office: k.planet for k in karakas(chart, which)}
            for which in ("seven", "eight")}


def schemes_agree_on(chart: Chart, office: str) -> bool:
    both = both_schemes(chart)
    return both["seven"].get(office) == both["eight"].get(office)


def describe(chart: Chart) -> dict:
    """Everything a reading or a ledger fact needs, computed once."""
    which = scheme()
    ranked = karakas(chart, which)
    ak, dk = ranked[0], ranked[-1]
    return {
        "scheme": which,
        "school": schools.chosen("karaka_count").school,
        "karakas": [
            {"office": k.office, "abbr": k.abbr, "planet": k.planet,
             "degree_in_sign": round(k.degree_in_sign, 4),
             "ranked_by": round(k.ranked_by, 4),
             "reversed_for_rahu": k.reversed_for_rahu,
             "signifies": k.signifies}
            for k in ranked],
        "atmakaraka": ak.planet,
        "darakaraka": dk.planet,
        "darakaraka_sign": SIGNS[chart.planets[dk.planet].sign_index],
        "darakaraka_house": chart.planets[dk.planet].house,
        "karakamsa": karakamsa(chart, which),
        "ties": tie_groups(chart, which),
        "darakaraka_agrees_across_schemes": schemes_agree_on(
            chart, "Darakaraka"),
    }
