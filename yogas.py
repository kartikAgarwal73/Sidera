"""Rule-based yoga detection.

Implements: Pancha Mahapurusha, Gaja Kesari, Budhaditya, Dhana yogas (via the
full house-lordship mapping), Viparita Raja, Neecha Bhanga, Kemadruma (with
exceptions). Every detection carries the classical rule verbatim plus the
chart-specific facts that fired it, so later phases can "show the working".
"""
from __future__ import annotations

from dataclasses import dataclass, field

from engine import PLANETS, SIGNS, Chart
from transits import aspected_signs

# --- Lordships & dignities -------------------------------------------------

SIGN_LORDS = [
    "Mars", "Venus", "Mercury", "Moon", "Sun", "Mercury",
    "Venus", "Mars", "Jupiter", "Saturn", "Saturn", "Jupiter",
]

EXALTATION_SIGN = {
    "Sun": 0, "Moon": 1, "Mars": 9, "Mercury": 5,
    "Jupiter": 3, "Venus": 11, "Saturn": 6,
}
DEBILITATION_SIGN = {p: (s + 6) % 12 for p, s in EXALTATION_SIGN.items()}

DEEP_EXALTATION_DEGREE = {
    "Sun": 10.0, "Moon": 3.0, "Mars": 28.0, "Mercury": 15.0,
    "Jupiter": 5.0, "Venus": 27.0, "Saturn": 20.0,
}

# Where a planet's exaltation sign is ALSO its own/moolatrikona sign, BPHS
# reads the stretch up to the deep-exaltation degree as the exaltation zone:
# Mercury in Virgo 0–15°, Moon in Taurus 0–3°.
EXALTATION_ZONE_END = {"Mercury": 15.0, "Moon": 3.0}

# Moolatrikona spans: planet → (sign_index, from_deg, to_deg). Standard BPHS
# table (Mercury's 16–20° Virgo per the classical segmentation).
MOOLATRIKONA = {
    "Sun": (4, 0.0, 20.0),      # Leo
    "Moon": (1, 3.0, 30.0),     # Taurus
    "Mars": (0, 0.0, 12.0),     # Aries
    "Mercury": (5, 16.0, 20.0), # Virgo
    "Jupiter": (8, 0.0, 10.0),  # Sagittarius
    "Venus": (6, 0.0, 15.0),    # Libra
    "Saturn": (10, 0.0, 20.0),  # Aquarius
}

# Naisargika maitri (natural relationships), classical seven-planet table.
NATURAL_FRIENDS = {
    "Sun": ("Moon", "Mars", "Jupiter"),
    "Moon": ("Sun", "Mercury"),
    "Mars": ("Sun", "Moon", "Jupiter"),
    "Mercury": ("Sun", "Venus"),
    "Jupiter": ("Sun", "Moon", "Mars"),
    "Venus": ("Mercury", "Saturn"),
    "Saturn": ("Mercury", "Venus"),
}
NATURAL_ENEMIES = {
    "Sun": ("Venus", "Saturn"),
    "Moon": (),
    "Mars": ("Mercury",),
    "Mercury": ("Moon",),
    "Jupiter": ("Mercury", "Venus"),
    "Venus": ("Sun", "Moon"),
    "Saturn": ("Sun", "Moon", "Mars"),
}

KENDRA_HOUSES = (1, 4, 7, 10)


def sign_lord(sign_index: int) -> str:
    return SIGN_LORDS[sign_index % 12]


def house_lords(chart: Chart) -> dict[int, str]:
    """Full lordship mapping: house number → lord of the sign in that house."""
    lagna = chart.lagna.sign_index
    return {h: sign_lord((lagna + h - 1) % 12) for h in range(1, 13)}


def houses_owned_by(chart: Chart, planet: str) -> tuple[int, ...]:
    return tuple(h for h, lord in house_lords(chart).items() if lord == planet)


def in_own_sign(chart: Chart, planet: str) -> bool:
    return sign_lord(chart.planets[planet].sign_index) == planet


def is_exalted(chart: Chart, planet: str) -> bool:
    return EXALTATION_SIGN.get(planet) == chart.planets[planet].sign_index


def is_debilitated(chart: Chart, planet: str) -> bool:
    return DEBILITATION_SIGN.get(planet) == chart.planets[planet].sign_index


def dignity_at(planet: str, sign_index: int, degree_in_sign: float) -> str:
    """Mutually exclusive dignity state for ANY position (natal or transit):
    'exalted' | 'moolatrikona' | 'own sign' | 'debilitated' | 'neutral'.

    Classical BPHS segmentation. Where the exaltation sign is also the
    planet's own or moolatrikona sign, degree bands decide — Mercury in
    Virgo: 0–15° exaltation zone (deep exaltation at 15°), 16–20°
    moolatrikona, remainder own sign; Moon in Taurus: 0–3° exaltation,
    then moolatrikona.
    """
    if DEBILITATION_SIGN.get(planet) == sign_index:
        return "debilitated"
    if EXALTATION_SIGN.get(planet) == sign_index:
        zone_end = EXALTATION_ZONE_END.get(planet)
        if zone_end is None or degree_in_sign <= zone_end:
            return "exalted"
        # dual-status sign, past the exaltation zone → resolved below
    mt = MOOLATRIKONA.get(planet)
    if mt and sign_index == mt[0] and mt[1] <= degree_in_sign < mt[2]:
        return "moolatrikona"
    if sign_lord(sign_index) == planet:
        return "own sign"
    return "neutral"


def dignity(chart: Chart, planet: str) -> str:
    """Natal dignity — see dignity_at()."""
    pos = chart.planets[planet]
    return dignity_at(planet, pos.sign_index, pos.degree_in_sign)


def dignity_grade_at(planet: str, sign_index: int,
                     degree_in_sign: float) -> str:
    """Graded dignity where a plain state undersells the picture — e.g.
    'exalted (early degree, rising toward deep exaltation at 15°)'.
    Empty string when the binary state is the whole story."""
    state = dignity_at(planet, sign_index, degree_in_sign)
    deg = degree_in_sign
    if state in ("exalted", "debilitated"):
        deep = DEEP_EXALTATION_DEGREE[planet]
        peak = "deep exaltation" if state == "exalted" else "deep fall"
        if abs(deg - deep) < 0.5:
            return f"{state} (at the {peak} degree, {int(deep)}°)"
        if deg < deep:
            direction = ("rising toward" if state == "exalted"
                         else "approaching")
            return f"{state} (early degree, {direction} {peak} at {int(deep)}°)"
        return f"{state} (past the {peak} degree at {int(deep)}°, easing)"
    if state == "moolatrikona":
        _sign, lo, hi = MOOLATRIKONA[planet]
        return f"moolatrikona ({int(lo)}°–{int(hi)}° span)"
    return ""


def dignity_grade(chart: Chart, planet: str) -> str:
    """Natal graded dignity — see dignity_grade_at()."""
    pos = chart.planets[planet]
    return dignity_grade_at(planet, pos.sign_index, pos.degree_in_sign)


def natural_relation(a: str, b: str) -> str:
    """'friend' | 'enemy' | 'neutral' — from planet a's perspective."""
    if b in NATURAL_FRIENDS.get(a, ()):
        return "friend"
    if b in NATURAL_ENEMIES.get(a, ()):
        return "enemy"
    return "neutral"


def mutual_natural_enemies(a: str, b: str) -> bool:
    return natural_relation(a, b) == "enemy" and natural_relation(b, a) == "enemy"


def _aspects_planet(chart: Chart, aspecting: str, aspected: str) -> bool:
    return chart.planets[aspected].sign_index in aspected_signs(
        aspecting, chart.planets[aspecting].sign_index
    )


def _sign_distance(from_sign: int, to_sign: int) -> int:
    """Inclusive count from one sign to another, 1–12."""
    return (to_sign - from_sign) % 12 + 1


# --- Result type -------------------------------------------------------------

@dataclass(frozen=True)
class Yoga:
    name: str
    kind: str  # family: "Pancha Mahapurusha", "Dhana", "Viparita Raja", …
    planets: tuple[str, ...]
    houses: tuple[int, ...]
    rule: str    # the classical rule, verbatim
    detail: str  # chart-specific facts that satisfied the rule
    cancelled: bool = False
    cancellation: tuple[str, ...] = field(default=())
    notes: tuple[str, ...] = field(default=())  # qualifying factors, e.g.
    # natural-enmity friction between the combining planets


# --- Detectors ----------------------------------------------------------------

_MAHAPURUSHA = {
    "Mars": "Ruchaka", "Mercury": "Bhadra", "Jupiter": "Hamsa",
    "Venus": "Malavya", "Saturn": "Shasha",
}


def detect_pancha_mahapurusha(chart: Chart) -> list[Yoga]:
    out = []
    for planet, name in _MAHAPURUSHA.items():
        pos = chart.planets[planet]
        if pos.house not in KENDRA_HOUSES:
            continue
        if in_own_sign(chart, planet) or is_exalted(chart, planet):
            state = dignity(chart, planet)
            out.append(Yoga(
                name=f"{name} Yoga", kind="Pancha Mahapurusha",
                planets=(planet,), houses=(pos.house,),
                rule=f"{name} Yoga forms when {planet} occupies its own or "
                     "exaltation sign and stands in a Kendra (1/4/7/10) "
                     "from the Lagna.",
                detail=f"{planet} is in {pos.sign} ({state}) in house "
                       f"{pos.house}, a Kendra.",
            ))
    return out


def detect_gaja_kesari(chart: Chart) -> list[Yoga]:
    moon_sign = chart.planets["Moon"].sign_index
    jup = chart.planets["Jupiter"]
    dist = _sign_distance(moon_sign, jup.sign_index)
    if dist in KENDRA_HOUSES:
        return [Yoga(
            name="Gaja Kesari Yoga", kind="Chandra yoga",
            planets=("Jupiter", "Moon"),
            houses=(chart.planets["Moon"].house, jup.house),
            rule="Gaja Kesari Yoga forms when Jupiter stands in a Kendra "
                 "(1st, 4th, 7th or 10th sign) counted from the Moon.",
            detail=f"Jupiter in {jup.sign} is the {dist}th sign from the "
                   f"Moon in {SIGNS[moon_sign]}.",
        )]
    return []


def detect_budhaditya(chart: Chart) -> list[Yoga]:
    sun, mer = chart.planets["Sun"], chart.planets["Mercury"]
    if sun.sign_index == mer.sign_index:
        return [Yoga(
            name="Budhaditya Yoga", kind="Solar yoga",
            planets=("Sun", "Mercury"), houses=(sun.house,),
            rule="Budhaditya Yoga forms when the Sun and Mercury are "
                 "conjoined in one sign.",
            detail=f"Sun and Mercury are both in {sun.sign} "
                   f"(house {sun.house}).",
        )]
    return []


WEALTH_HOUSES = (1, 2, 5, 9, 11)


def detect_dhana(chart: Chart) -> list[Yoga]:
    """Dhana yogas: combinations among the lords of houses 1/2/5/9/11 —
    conjunction, sign exchange, mutual aspect, or one wealth lord placed in
    another wealth house."""
    lords = house_lords(chart)
    out = []
    seen: set[tuple] = set()

    def add(name, planets, houses, rule, detail, notes=()):
        key = (name, planets, houses)
        if key not in seen:
            seen.add(key)
            out.append(Yoga(name=name, kind="Dhana", planets=planets,
                            houses=houses, rule=rule, detail=detail,
                            notes=tuple(notes)))

    for i in WEALTH_HOUSES:
        for j in WEALTH_HOUSES:
            if j <= i:
                continue
            a, b = lords[i], lords[j]
            if a == b:
                continue  # same planet owns both — no combination to form
            pa, pb = chart.planets[a], chart.planets[b]
            pair = tuple(sorted((a, b)))
            friction = ()
            if mutual_natural_enemies(a, b):
                friction = (
                    f"{a} and {b} are natural enemies (naisargika maitri); "
                    "this combination carries friction — the wealth link "
                    "operates under strain.",
                )
            if pa.sign_index == pb.sign_index:
                add(f"Dhana Yoga (lords of {i} & {j} conjoined)",
                    pair, (i, j),
                    "A Dhana Yoga forms when the lords of two wealth houses "
                    "(1/2/5/9/11) are conjoined in one sign.",
                    f"{a} (lord of {i}) and {b} (lord of {j}) are together "
                    f"in {pa.sign}.", notes=friction)
            if (sign_lord(pa.sign_index) == b
                    and sign_lord(pb.sign_index) == a):
                add(f"Dhana Yoga (lords of {i} & {j} in exchange)",
                    pair, (i, j),
                    "A Dhana Yoga forms when the lords of two wealth houses "
                    "exchange signs (Parivartana).",
                    f"{a} occupies {pa.sign} ({b}'s sign) while {b} occupies "
                    f"{pb.sign} ({a}'s sign).", notes=friction)
            if _aspects_planet(chart, a, b) and _aspects_planet(chart, b, a):
                add(f"Dhana Yoga (lords of {i} & {j} in mutual aspect)",
                    pair, (i, j),
                    "A Dhana Yoga forms when the lords of two wealth houses "
                    "aspect each other by graha drishti.",
                    f"{a} (lord of {i}) and {b} (lord of {j}) cast mutual "
                    "drishti.", notes=friction)

    for i in WEALTH_HOUSES:
        lord = lords[i]
        placed = chart.planets[lord].house
        if placed in WEALTH_HOUSES and placed != i:
            add(f"Dhana Yoga (lord of {i} in house {placed})",
                (lord,), (i, placed),
                "A Dhana Yoga forms when the lord of one wealth house "
                "(1/2/5/9/11) occupies another wealth house.",
                f"{lord}, lord of house {i}, stands in house {placed}.")
    return out


DUSTHANA_HOUSES = (6, 8, 12)
_VIPARITA_NAMES = {6: "Harsha", 8: "Sarala", 12: "Vimala"}


def detect_viparita_raja(chart: Chart) -> list[Yoga]:
    lords = house_lords(chart)
    out = []
    for h in DUSTHANA_HOUSES:
        lord = lords[h]
        placed = chart.planets[lord].house
        if placed in DUSTHANA_HOUSES:
            out.append(Yoga(
                name=f"{_VIPARITA_NAMES[h]} (Viparita Raja) Yoga",
                kind="Viparita Raja",
                planets=(lord,), houses=(h, placed),
                rule="A Viparita Raja Yoga forms when the lord of a "
                     "dusthana (6/8/12) occupies a dusthana (6/8/12).",
                detail=f"{lord}, lord of house {h}, stands in house "
                       f"{placed}.",
            ))
    return out


def detect_neecha_bhanga(chart: Chart) -> list[Yoga]:
    """Neecha Bhanga (cancellation of debilitation), standard conditions:
    1. the dispositor is in a Kendra from the Lagna or the Moon;
    2. the planet exalted in the debilitation sign is in a Kendra from the
       Lagna or the Moon;
    3. the debilitated planet is aspected by its dispositor;
    4. the debilitated planet exchanges signs with its dispositor."""
    moon_sign = chart.planets["Moon"].sign_index
    lagna_sign = chart.lagna.sign_index
    out = []

    def in_kendra_from(sign: int, ref: int) -> bool:
        return _sign_distance(ref, sign) in KENDRA_HOUSES

    for planet in PLANETS:
        if not is_debilitated(chart, planet):
            continue
        pos = chart.planets[planet]
        dispositor = sign_lord(pos.sign_index)
        disp_pos = chart.planets[dispositor]
        conditions = []

        if (in_kendra_from(disp_pos.sign_index, lagna_sign)
                or in_kendra_from(disp_pos.sign_index, moon_sign)):
            conditions.append(
                f"dispositor {dispositor} is in a Kendra from the Lagna "
                "or Moon")
        exalt_owner = next(
            (p for p, s in EXALTATION_SIGN.items() if s == pos.sign_index),
            None)
        if exalt_owner and (
                in_kendra_from(chart.planets[exalt_owner].sign_index,
                               lagna_sign)
                or in_kendra_from(chart.planets[exalt_owner].sign_index,
                                  moon_sign)):
            conditions.append(
                f"{exalt_owner}, exalted in {pos.sign}, is in a Kendra "
                "from the Lagna or Moon")
        if _aspects_planet(chart, dispositor, planet):
            conditions.append(
                f"dispositor {dispositor} aspects {planet}")
        if sign_lord(disp_pos.sign_index) == planet:
            conditions.append(
                f"{planet} and {dispositor} exchange signs")

        if conditions:
            out.append(Yoga(
                name=f"Neecha Bhanga ({planet})", kind="Neecha Bhanga",
                planets=(planet, dispositor), houses=(pos.house,),
                rule="Debilitation is cancelled (Neecha Bhanga) when the "
                     "dispositor or the planet exalted in that sign stands "
                     "in a Kendra from the Lagna or Moon, or the dispositor "
                     "aspects or exchanges with the debilitated planet.",
                detail=f"{planet} is debilitated in {pos.sign} (house "
                       f"{pos.house}); satisfied: "
                       + "; ".join(conditions) + ".",
            ))
    return out


def detect_kemadruma(chart: Chart) -> list[Yoga]:
    """Kemadruma: no graha (other than the Sun; nodes excluded) in the 2nd
    or 12th from the Moon, nor conjoined with it. Standard exceptions
    (any one cancels): a planet in a Kendra from the Moon; the Moon in a
    Kendra from the Lagna; the Moon aspected by Jupiter."""
    moon_sign = chart.planets["Moon"].sign_index
    others = [p for p in PLANETS if p not in ("Moon", "Sun", "Rahu", "Ketu")]

    flanking = [
        p for p in others
        if _sign_distance(moon_sign, chart.planets[p].sign_index) in (1, 2, 12)
    ]
    if flanking:
        return []  # yoga does not form at all

    exceptions = []
    kendra_planets = [
        p for p in others
        if _sign_distance(moon_sign, chart.planets[p].sign_index)
        in KENDRA_HOUSES
    ]
    if kendra_planets:
        exceptions.append(
            "planet(s) in a Kendra from the Moon: "
            + ", ".join(kendra_planets))
    if chart.planets["Moon"].house in KENDRA_HOUSES:
        exceptions.append(
            f"Moon itself is in a Kendra from the Lagna "
            f"(house {chart.planets['Moon'].house})")
    if _aspects_planet(chart, "Jupiter", "Moon"):
        exceptions.append("Jupiter aspects the Moon")

    return [Yoga(
        name="Kemadruma Yoga", kind="Chandra yoga",
        planets=("Moon",), houses=(chart.planets["Moon"].house,),
        rule="Kemadruma forms when no planet (Sun and nodes excluded) "
             "occupies the 2nd or 12th from the Moon or joins it — unless "
             "a standard exception intervenes.",
        detail=f"Moon in {SIGNS[moon_sign]} has no flanking or conjoined "
               "planet.",
        cancelled=bool(exceptions),
        cancellation=tuple(exceptions),
    )]


def detect_all(chart: Chart) -> list[Yoga]:
    return (
        detect_pancha_mahapurusha(chart)
        + detect_gaja_kesari(chart)
        + detect_budhaditya(chart)
        + detect_dhana(chart)
        + detect_viparita_raja(chart)
        + detect_neecha_bhanga(chart)
        + detect_kemadruma(chart)
    )
