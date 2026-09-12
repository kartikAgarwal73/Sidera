"""Divisional (varga) charts — Parāśarī, at DEGREE level.

WHAT A VARGA IS, MECHANICALLY
A sign is cut into N equal parts. Which part a graha falls in decides which
sign it takes in the divisional chart; the tables below are the classical
rules for that mapping, one per division. This build then does one more
thing, which milestone 3 named as its prerequisite: it keeps the POSITION
WITHIN THE PART and stretches it back over a full 30°, so every graha has a
divisional LONGITUDE and not merely a divisional sign.

    part      = floor(degree_in_sign / (30/N))
    remainder = degree_in_sign - part * (30/N)
    varga degree = remainder * N          ← the stretch
    varga longitude = varga_sign * 30 + varga degree

That degree is what unlocks varga nakṣatras and dignity-by-degree. It is a
SCALING CONVENTION, not a classical statement — the texts assign a sign, not
a position inside it — and `rule.varga.degree_convention` says so in as many
words, so nothing downstream can quote it as scripture.

WHERE THE SCHOOLS SPLIT
Three of these divisions are genuinely contested and this file says which
reading it uses rather than picking one in silence. `SCHOOL_NOTE` carries a
one-line statement per division and the plate prints it.

  D2   The classical horā gives only two signs — the Sun's (Leo) and the
       Moon's (Cancer). This build uses the TWELVE-SIGN horā instead
       (Jagannātha Hora / PVR convention), which counts continuously and
       reverses direction in even signs. The two schemes are not variants
       of one rule; they answer differently.
  D30  The classical triṃśāṃśa is UNEQUAL — five bands of 5, 5, 8, 7 and 5
       degrees, reversed in even signs. That is what decides the sign here.
       The equal 1° part is used ONLY for the degree stretch above, and it
       has to be, because a graha in an 8° band has no equal-part position.
  D60  Counted straight on from the sign itself, half a degree per division.
       Some texts reverse the count in even signs; this build does not.

EVERY DIVISION IS GATED
`TestEveryDivisionMatchesTheOracle` compares this module against PyJHora,
per body and per division, for both fictional charts — sign AND divisional
longitude. Nothing lights up in the gallery that has not passed it.
"""
from __future__ import annotations

from dataclasses import dataclass

from engine import PLANETS, SIGNS, Chart

# --- the sign rules, one per division -----------------------------------------
#
# Each takes the D1 sign index (0 = Aries), the part index (0-based) and the
# degree within the sign, and returns the divisional sign index.
#
# "Odd sign" throughout means odd by SIGN NUMBER — Aries is the 1st and odd,
# Taurus the 2nd and even. Sign INDEX is zero-based, so an odd sign has an
# even index. Getting that backwards is the classic off-by-one here, and it
# is why the helper is named for the thing it tests.


def _is_odd_sign(sign_index: int) -> bool:
    return sign_index % 2 == 0


def _modality(sign_index: int) -> int:
    """0 movable (cara), 1 fixed (sthira), 2 dual (dvisvabhāva)."""
    return sign_index % 3


# D30's five unequal bands: (upper degree, ruling planet's sign). Odd signs
# run Mars, Saturn, Jupiter, Mercury, Venus; even signs take the reverse
# order and each planet's OTHER sign.
TRIMSAMSA_ODD = ((5.0, 0), (10.0, 10), (18.0, 8), (25.0, 2), (30.0, 6))
TRIMSAMSA_EVEN = ((5.0, 1), (12.0, 5), (20.0, 11), (25.0, 9), (30.0, 7))


def _scheme(option_id: str) -> str:
    """The live answer to one divisional-scheme question.

    Imported lazily so `vargas` stays importable by tools that never touch
    the school registry, and so the module keeps no opinion of its own about
    which reading is in force.
    """
    import schools
    return schools.chosen(option_id).id


def _d2(sign: int, part: int, deg: float) -> int:
    """Horā, under whichever scheme is in force.

    TWELVE-SIGN (default): odd signs count forward from twice the sign, even
    signs BACKWARD from one past it — every sign is reachable.
    TWO-SIGN: the older Parāśarī horā, which has only two. The first half of
    an odd sign is the Sun's horā (Leo) and the second the Moon's (Cancer);
    even signs take them the other way round. Every graha in the chart lands
    in Leo or Cancer and nowhere else, which is not a defect — the horā is
    read for wealth through the solar or lunar half, and that is a
    two-valued question.
    """
    if _scheme("hora_scheme") == "two_sign":
        sun_first = _is_odd_sign(sign)
        first, second = (4, 3) if sun_first else (3, 4)
        return first if part == 0 else second
    return (2 * sign + part) % 12 if _is_odd_sign(sign) \
        else (2 * sign + 1 - part) % 12


def _d3(sign: int, part: int, deg: float) -> int:
    """Drekkāṇa, under whichever scheme is in force.

    PARĀŚARĪ (default): the sign itself, the 5th from it, the 9th from it —
    the trines, which is why the drekkāṇa is read for siblings and courage.
    PARIVṚTTI-TRAYA: a plain cyclic count, three signs per sign, running
    straight through the zodiac without regard to trine.
    """
    if _scheme("drekkana_scheme") == "parivritti":
        return (sign * 3 + part) % 12
    return (sign + 4 * part) % 12


def _d7(sign: int, part: int, deg: float) -> int:
    """Saptāṃśa: odd signs from the sign itself, even from the 7th."""
    return (sign + part + (0 if _is_odd_sign(sign) else 6)) % 12


def _d9(sign: int, part: int, deg: float) -> int:
    """Navāṃśa. Movable from the sign, fixed from the 9th, dual from the
    5th — which collapses to the familiar (sign x 9 + part)."""
    return (sign * 9 + part) % 12


def _d10(sign: int, part: int, deg: float) -> int:
    """Daśāṃśa: odd signs from the sign itself, even from the 9th."""
    return (sign + part + (0 if _is_odd_sign(sign) else 8)) % 12


def _d12(sign: int, part: int, deg: float) -> int:
    """Dvādaśāṃśa: counted straight on from the sign itself."""
    return (sign + part) % 12


def _d16(sign: int, part: int, deg: float) -> int:
    """Ṣoḍaśāṃśa: movable signs start at Aries, fixed at Leo, dual at
    Sagittarius."""
    return ({0: 0, 1: 4, 2: 8}[_modality(sign)] + part) % 12


def _d30(sign: int, part: int, deg: float) -> int:
    """Triṃśāṃśa, by the classical UNEQUAL bands. `part` is ignored here on
    purpose — it is the equal-division index, which the degree stretch uses
    and which the sign rule must not."""
    bands = TRIMSAMSA_ODD if _is_odd_sign(sign) else TRIMSAMSA_EVEN
    for upper, varga_sign in bands:
        if deg < upper:
            return varga_sign
    return bands[-1][1]


def _d60(sign: int, part: int, deg: float) -> int:
    """Ṣaṣṭyāṃśa: half a degree per division, counted on from the sign."""
    return (sign + part) % 12


def _d4(sign: int, part: int, deg: float) -> int:
    """Chaturthāṃśa: the four kendras from the sign — itself, the 4th, the
    7th, the 10th."""
    return (sign + 3 * part) % 12


def _d20(sign: int, part: int, deg: float) -> int:
    """Viṃśāṃśa: movable signs start at Aries, fixed at Sagittarius, dual at
    Leo."""
    return ({0: 0, 1: 8, 2: 4}[_modality(sign)] + part) % 12


def _d24(sign: int, part: int, deg: float) -> int:
    """Chaturviṃśāṃśa (Siddhāṃśa): odd signs start at Leo, even at Cancer."""
    return ((4 if _is_odd_sign(sign) else 3) + part) % 12


#: D27's element starts: fire from Aries, earth from Cancer, air from Libra,
#: water from Capricorn. Sign index mod 4 gives the element, Aries first.
BHAMSA_START = {0: 0, 1: 3, 2: 6, 3: 9}


def _d27(sign: int, part: int, deg: float) -> int:
    """Bhāṃśa (Nakṣatrāṃśa), counted forward from the element's sign.

    Equivalent in closed form to (sign × 3 + part), which is how it is
    usually written down — the two are the same rule, not two schools.
    The genuine fork is whether even signs REVERSE the count, and that is
    `bhamsa_scheme` in schools.py.
    """
    start = BHAMSA_START[sign % 4]
    if not _is_odd_sign(sign) and _scheme("bhamsa_scheme") == "even_reverse":
        return (start + DIVISIONS["D27"] - 1 - part) % 12
    return (start + part) % 12


def _d40(sign: int, part: int, deg: float) -> int:
    """Khavedāṃśa: odd signs start at Aries, even at Libra."""
    return ((0 if _is_odd_sign(sign) else 6) + part) % 12


def _d45(sign: int, part: int, deg: float) -> int:
    """Akṣavedāṃśa: movable signs start at Aries, fixed at Leo, dual at
    Sagittarius."""
    return ({0: 0, 1: 4, 2: 8}[_modality(sign)] + part) % 12


# THE REGISTRY. `varga_chart` is generic over this table, and so is the
# gallery: a division renders as a real plate exactly when it has an entry
# here, and as a dashed empty frame when it does not. Adding a division is
# one line — and `TestEveryComputedVargaIsPlotted` fails if a computation
# lands and the gallery does not plot it.
_VARGA_FN = {
    "D2": _d2, "D3": _d3, "D4": _d4, "D7": _d7, "D9": _d9, "D10": _d10,
    "D12": _d12, "D16": _d16, "D20": _d20, "D24": _d24, "D27": _d27,
    "D30": _d30, "D40": _d40, "D45": _d45, "D60": _d60,
}

#: How many parts each division cuts a sign into. Always int(code[1:]) — kept
#: as a lookup so a caller never has to parse a string to know.
DIVISIONS = {code: int(code[1:]) for code in _VARGA_FN}

#: Division codes this build can cast, D1 aside.
SUPPORTED = tuple(_VARGA_FN)

#: What each division is read FOR, in plain words. One place, so the gallery,
#: the ledger and the agent cannot describe the same chart differently.
READ_FOR = {
    "D2": "wealth and what is kept",
    "D3": "siblings, courage and the reach of one's own effort",
    "D7": "children, and what the chart carries forward",
    "D9": "marriage, and the inner strength of every planet",
    "D10": "work, standing, and the field a career takes place in",
    "D12": "the parents, and what was inherited",
    "D4": "home, land, and what one can call a fixed place",
    "D16": "vehicles, comforts, and the furnishing of a life",
    "D20": "devotion, practice, and what one turns to",
    "D24": "learning, and what the mind is actually trained in",
    "D27": "underlying strength and weakness, sign by sign",
    "D40": "what comes down the maternal line",
    "D45": "what comes down the paternal line",
    "D30": "where the chart is tested, and which planet does the testing",
    "D60": "the finest division Parāśara gives",
}

#: Where the tradition genuinely splits, said out loud. Printed on the plate
#: of any division that has an entry here — the reader is told which reading
#: they are looking at rather than left to assume there is only one.
SCHOOL_NOTE = {
    "D2": ("The horā is cut two ways and you are being shown one of them. "
           "The twelve-sign horā counts continuously and reverses in even "
           "signs; the older Parāśarī horā gives only the Sun's sign and "
           "the Moon's, so every graha lands in Leo or Cancer."),
    "D3": ("The drekkāṇa is cut two ways. Parāśarī sends each third to the "
           "sign, the 5th and the 9th — the trines; the parivṛtti-traya "
           "counts straight on through the zodiac instead."),
    "D27": ("The bhāṃśa starts from the element's sign — fire from Aries, "
            "earth from Cancer, air from Libra, water from Capricorn. "
            "Whether the even signs then count backward is disputed, and "
            "the answer you chose is in force."),
    "D30": ("Classical UNEQUAL triṃśāṃśa: bands of 5°, 5°, 8°, 7°, 5° ruled "
            "by Mars, Saturn, Jupiter, Mercury and Venus, reversed in even "
            "signs. The equal 1° part is used only to scale the degree, "
            "never to choose the sign."),
    "D60": ("Half a degree per division, counted straight on from the sign "
            "itself. Some texts reverse the count in even signs; this build "
            "does not."),
}

#: The rule id in `rulelib` each division's construction rests on.
SCHOOL_RULE = {
    "D2": "rule.varga.hora_school",
    "D3": "rule.varga.drekkana_school",
    "D27": "rule.varga.bhamsa_school",
    "D30": "rule.varga.trimsamsa_school",
    "D60": "rule.varga.shastyamsa_school",
}


def is_supported(varga: str) -> bool:
    return varga in _VARGA_FN


def varga_longitude(longitude: float, varga: str) -> tuple[int, float]:
    """(divisional sign index, degree within it) for one sidereal longitude.

    The degree is the position inside the part, stretched over a full 30°.
    See the module docstring: a scaling convention, and named as one.
    """
    fn = _VARGA_FN[varga]
    parts = DIVISIONS[varga]
    span = 30.0 / parts
    lon = longitude % 360.0
    sign = int(lon // 30)
    deg = lon - sign * 30.0
    part = min(int(deg // span), parts - 1)
    return fn(sign, part, deg), (deg - part * span) * parts


@dataclass(frozen=True)
class VargaPosition:
    name: str
    sign_index: int
    house: int  # Whole Sign house from the divisional lagna, 1–12
    #: Degree within the divisional sign, 0–30. See the module docstring on
    #: what this is and is not.
    degree_in_sign: float = 0.0
    vargottama: bool = False  # same sign in D1 and D9 (set for D9 only)

    @property
    def sign(self) -> str:
        return SIGNS[self.sign_index]

    @property
    def longitude(self) -> float:
        return self.sign_index * 30.0 + self.degree_in_sign

    @property
    def dms(self) -> str:
        d = int(self.degree_in_sign)
        m = int(round((self.degree_in_sign - d) * 60))
        if m == 60:
            d, m = d + 1, 0
        return f"{d}°{m:02d}′"


@dataclass(frozen=True)
class VargaChart:
    varga: str
    lagna_sign_index: int
    planets: dict[str, VargaPosition]
    lagna_degree_in_sign: float = 0.0

    @property
    def lagna_sign(self) -> str:
        return SIGNS[self.lagna_sign_index]

    @property
    def read_for(self) -> str:
        return READ_FOR[self.varga]

    @property
    def school_note(self) -> str | None:
        return SCHOOL_NOTE.get(self.varga)

    @property
    def house_signs(self) -> dict[int, str]:
        return {
            h: SIGNS[(self.lagna_sign_index + h - 1) % 12] for h in range(1, 13)
        }

    @property
    def houses(self) -> dict[int, list[str]]:
        out: dict[int, list[str]] = {h: [] for h in range(1, 13)}
        for name in PLANETS:
            out[self.planets[name].house].append(name)
        return out


def varga_chart(chart: Chart, varga: str) -> VargaChart:
    """Divisional chart: every graha's divisional sign, degree and house."""
    if varga not in _VARGA_FN:
        raise ValueError(
            f"Unsupported varga {varga!r}; supported: {', '.join(SUPPORTED)}")

    lagna_sign, lagna_deg = varga_longitude(chart.lagna.longitude, varga)
    planets: dict[str, VargaPosition] = {}
    for name, pos in chart.planets.items():
        d_sign, d_deg = varga_longitude(pos.longitude, varga)
        planets[name] = VargaPosition(
            name=name,
            sign_index=d_sign,
            house=(d_sign - lagna_sign) % 12 + 1,
            degree_in_sign=d_deg,
            vargottama=(varga == "D9" and d_sign == pos.sign_index),
        )
    return VargaChart(varga=varga, lagna_sign_index=lagna_sign,
                      planets=planets, lagna_degree_in_sign=lagna_deg)


def varga_sign(longitude: float, varga: str) -> int:
    """Just the divisional sign, for a caller that wants no degree."""
    return varga_longitude(longitude, varga)[0]


def navamsa_sign(longitude: float) -> int:
    """D9 sign index for a sidereal longitude.

    Kept as a named function through the degree-level rewrite because a set
    of anchored gates asserts specific values against it — 0° Aries is the
    first navāṃśa, 30° Aries the tenth, and so on. Those assertions are the
    external anchor on this division; routing them through the general
    machinery is how the rewrite proves it did not move anything.
    """
    return varga_sign(longitude, "D9")


def dasamsa_sign(longitude: float) -> int:
    """D10 sign index for a sidereal longitude. See `navamsa_sign`."""
    return varga_sign(longitude, "D10")


def navamsa(chart: Chart) -> VargaChart:
    return varga_chart(chart, "D9")


def dasamsa(chart: Chart) -> VargaChart:
    return varga_chart(chart, "D10")
