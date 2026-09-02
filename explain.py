"""Explanation Engine — every output explained in three layers.

Layer 1 (fact): what is, stated plainly.
Layer 2 (mechanism): how it was computed, with the counting shown.
Layer 3 (meaning): the classical reading, carrying a MANDATORY confidence tag.

Confidence policy:
- High         — stated outcome of the classical rule itself (Mahapurusha
                 fruits, Viparita reversals, Neecha Bhanga restoration).
- Moderate     — standard classical attribution, widely agreed across texts
                 (nakshatra qualities, dasha lord themes, named-yoga fruits,
                 sign temperament).
- Interpretive — composed synthesis with no single textual source
                 (planet-in-house blends, transit weather).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from dashas import (
    DASHA_SEQUENCE,
    NAKSHATRA_SPAN,
    VimshottariTimeline,
    nakshatra_of,
)
from engine import PLANETS, SIGNS, Chart
from transits import DRISHTI_OFFSETS, TransitSnapshot
from yogas import (
    DEEP_EXALTATION_DEGREE,
    EXALTATION_SIGN,
    EXALTATION_ZONE_END,
    Yoga,
    dignity,
    dignity_grade,
    in_own_sign,
    is_exalted,
)

CONFIDENCE_LEVELS = ("High", "Moderate", "Interpretive")


@dataclass(frozen=True)
class Explanation:
    fact: str
    mechanism: str
    meaning: str
    confidence: str  # mandatory on ALL interpretations

    def __post_init__(self):
        if self.confidence not in CONFIDENCE_LEVELS:
            raise ValueError(
                f"confidence must be one of {CONFIDENCE_LEVELS}, "
                f"got {self.confidence!r}"
            )


@dataclass(frozen=True)
class ExplainedItem:
    """A titled explanation, ready for an expandable UI entry."""

    title: str
    subtitle: str
    explanation: Explanation


# --- classical vocabulary ----------------------------------------------------

PLANET_SIGNIFIES = {
    "Sun": "the self, authority, vitality, the father",
    "Moon": "the mind, emotions, the mother, the public",
    "Mars": "energy, courage, siblings, contest",
    "Mercury": "intellect, speech, trade, wit",
    "Jupiter": "wisdom, expansion, teachers, fortune",
    "Venus": "love, art, comforts, partnership",
    "Saturn": "discipline, time, labour, endurance",
    "Rahu": "appetite, amplification, the foreign, ambition",
    "Ketu": "detachment, insight, past mastery, release",
}

HOUSE_THEME = {
    1: "the body, temperament and self-presentation",
    2: "wealth, speech and family resources",
    3: "courage, effort and younger siblings",
    4: "home, mother, land and the heart's ease",
    5: "creativity, children, intellect and merit",
    6: "obstacles, service, debts and health",
    7: "partnership, marriage and the other",
    8: "transformation, longevity and the hidden",
    9: "dharma, fortune, teachers and grace",
    10: "karma, career and public standing",
    11: "gains, networks and aspirations",
    12: "expenditure, retreat, foreign shores and liberation",
}

SIGN_TEMPERAMENT = {
    "Aries": "initiating, martial, direct",
    "Taurus": "steady, sensual, acquisitive",
    "Gemini": "curious, verbal, twin-natured",
    "Cancer": "protective, tidal, remembering",
    "Leo": "sovereign, warm, display-loving",
    "Virgo": "exacting, serviceable, analytical",
    "Libra": "balancing, relational, aesthetic",
    "Scorpio": "intense, secretive, regenerative",
    "Sagittarius": "aspiring, dharmic, far-aiming",
    "Capricorn": "structural, patient, ambitious",
    "Aquarius": "systemic, austere, collective",
    "Pisces": "dissolving, compassionate, boundless",
}

NAKSHATRA_QUALITY = {
    "Ashwini": "the Ashvins' star — swiftness, healing, fresh starts",
    "Bharani": "Yama's star — bearing, restraint, the cycles of birth",
    "Krittika": "Agni's star — cutting clarity and purification",
    "Rohini": "Prajapati's star — ripening, fertility, beauty",
    "Mrigashira": "Soma's star — searching, gentle curiosity",
    "Ardra": "Rudra's star — storm, catharsis, a sharp mind",
    "Punarvasu": "Aditi's star — the return of light, renewal, shelter",
    "Pushya": "Brihaspati's star — nourishment and priestly steadiness",
    "Ashlesha": "the Nagas' star — coiling insight, hypnotic depth",
    "Magha": "the Pitris' star — ancestry, thrones, inheritance",
    "Purva Phalguni": "Bhaga's star — pleasure, rest, patronage",
    "Uttara Phalguni": "Aryaman's star — contracts, kindness, alliance",
    "Hasta": "Savitar's star — the skilled hand, craft, wit",
    "Chitra": "Tvashtar's star — design, brilliance, form",
    "Swati": "Vayu's star — independence, the scattering wind",
    "Vishakha": "Indra-Agni's star — forked purpose, determined pursuit",
    "Anuradha": "Mitra's star — friendship, devotion across distance",
    "Jyeshtha": "Indra's star — seniority, guardianship, testing",
    "Mula": "Nirriti's star — the root, uprooting, investigation",
    "Purva Ashadha": "Apas' star — invigoration, the early victory",
    "Uttara Ashadha": "the Vishvedevas' star — the lasting victory",
    "Shravana": "Vishnu's star — listening, learning, connection",
    "Dhanishta": "the Vasus' star — rhythm, wealth, music",
    "Shatabhisha": "Varuna's star — the hundred healers, remedy, secrecy",
    "Purva Bhadrapada": "Aja Ekapada's star — austerity, transforming fire",
    "Uttara Bhadrapada": "Ahirbudhnya's star — deep waters, stable wisdom",
    "Revati": "Pushan's star — safe passage, completion, care of the flock",
}

DASHA_THEME = {
    "Ketu": "unravelling, pilgrimage, mastery recalled",
    "Venus": "relationship, comfort, art and increase",
    "Sun": "authority claimed, visibility, the father's line",
    "Moon": "feeling, home, the public and the tides of mood",
    "Mars": "effort, contest, decisive action",
    "Rahu": "appetite, acceleration, unfamiliar territory",
    "Jupiter": "growth, teaching, children and fortune",
    "Saturn": "slow load-bearing work, pruning, structures that last",
    "Mercury": "study, commerce, writing and connection",
}

YOGA_MEANING = {
    "Ruchaka": ("Mars-born Mahapurusha: courage, command, a leader's frame "
                "and the fruits of decisive action.", "High"),
    "Bhadra": ("Mercury-born Mahapurusha: penetrating intellect, mastery of "
               "speech and commerce, long-preserved learning.", "High"),
    "Hamsa": ("Jupiter-born Mahapurusha: wisdom, ethical standing, the "
              "respect of teachers and the fortune that follows it.", "High"),
    "Malavya": ("Venus-born Mahapurusha: grace, comforts, artistic "
                "refinement and happiness through partnership.", "High"),
    "Shasha": ("Saturn-born Mahapurusha: authority over land and people, "
               "endurance, power built patiently.", "High"),
    "Gaja Kesari": ("The elephant-lion pairing of Moon and Jupiter: durable "
                    "reputation, discerning intelligence, resources that "
                    "recover after loss.", "Moderate"),
    "Budhaditya": ("Sun and Mercury conjoined: intellect fused with "
                   "authority — skill in analysis, administration and "
                   "expression.", "Moderate"),
    "Dhana": ("A wiring of wealth houses: earning capacity flows along the "
              "connected lords' significations.", "Moderate"),
    "Viparita Raja": ("Lords of loss placed in houses of loss undo each "
                      "other: gains arriving through adversity, reversals "
                      "resolving in one's favour.", "High"),
    "Neecha Bhanga": ("The cancelled fall: the planet's strength is "
                      "restored, classically read as rising after an early "
                      "setback.", "High"),
    "Kemadruma": ("The unaccompanied Moon: self-reliance demanded of the "
                  "mind; classically softened by its many exceptions.",
                  "Moderate"),
}

_ORDINAL = {1: "1st", 2: "2nd", 3: "3rd"}


def ordinal(n: int) -> str:
    return _ORDINAL.get(n, f"{n}th")


def counting_chain(from_sign: int, to_sign: int) -> str:
    """The inclusive Whole-Sign count, every step shown:
    'Sagittarius 1 · Capricorn 2 · … · Virgo 10'."""
    steps = (to_sign - from_sign) % 12 + 1
    return " · ".join(
        f"{SIGNS[(from_sign + k) % 12]} {k + 1}" for k in range(steps)
    )


def _dms(deg: float) -> str:
    d = int(deg)
    m = int(round((deg - d) * 60))
    if m == 60:
        d, m = d + 1, 0
    return f"{d}°{m:02d}′"


# --- explainers ---------------------------------------------------------------

def explain_lagna(chart: Chart) -> Explanation:
    lagna = chart.lagna
    return Explanation(
        fact=f"The Lagna is {lagna.sign} {lagna.dms}.",
        mechanism=(
            f"At the birth moment the eastern horizon cut the ecliptic at "
            f"sidereal {_dms(lagna.longitude)} (tropical ascendant minus the "
            f"Lahiri ayanāṃśa of {_dms(chart.ayanamsa)}). "
            f"{_dms(lagna.longitude)} ÷ 30° falls in the "
            f"{ordinal(lagna.sign_index + 1)} sign, {lagna.sign}, at "
            f"{lagna.dms}. Every house is the whole sign counted from here: "
            f"house 1 is {lagna.sign} itself."
        ),
        meaning=(
            f"The rising sign frames the whole kundli — body, temperament, "
            f"self-presentation. {lagna.sign} rising is "
            f"{SIGN_TEMPERAMENT[lagna.sign]}."
        ),
        confidence="Moderate",
    )


def explain_planet(chart: Chart, name: str) -> Explanation:
    pos = chart.planets[name]
    state = dignity(chart, name)
    chain = counting_chain(chart.lagna.sign_index, pos.sign_index)

    mech = (
        f"Sidereal longitude {_dms(pos.longitude)} ÷ 30° → the "
        f"{ordinal(pos.sign_index + 1)} sign, {pos.sign}, at {pos.dms}. "
        f"House counting from the Lagna: {chain} — the "
        f"{ordinal(pos.house)} house."
    )
    if pos.retrograde and name not in ("Rahu", "Ketu"):
        mech += (f" Daily motion {pos.speed:+.2f}°/day is negative — "
                 f"retrograde.")
    if name in ("Rahu", "Ketu"):
        mech += " The nodes always move retrograde (mean node)."
    if state != "neutral":
        if is_exalted(chart, name) and in_own_sign(chart, name):
            zone = EXALTATION_ZONE_END[name]
            mech += (
                f" {pos.sign} is both {name}'s own and exaltation sign; "
                f"BPHS reads its first {_dms(zone)} as the exaltation zone "
                f"(deep exaltation at {_dms(DEEP_EXALTATION_DEGREE[name])}) "
                f"— at {pos.dms} the state reads '{state}'."
            )
        else:
            mech += f" In {pos.sign}, {name} is {state}."
        grade = dignity_grade(chart, name)
        if grade:
            mech += f" Graded: {grade}."

    retro_txt = " (retrograde)" if pos.retrograde else ""
    graded_state = dignity_grade(chart, name) or state
    return Explanation(
        fact=(f"{name} is at {pos.sign} {pos.dms}{retro_txt}, in the "
              f"{ordinal(pos.house)} house — dignity: {graded_state}."),
        mechanism=mech,
        meaning=(
            f"{name} carries {PLANET_SIGNIFIES[name]}; placed in the "
            f"{ordinal(pos.house)} house it works through "
            f"{HOUSE_THEME[pos.house]}."
        ),
        confidence="Interpretive",
    )


def explain_nakshatra(point: str, longitude: float) -> Explanation:
    nak = nakshatra_of(longitude)
    within = longitude % NAKSHATRA_SPAN
    return Explanation(
        fact=f"{point} occupies {nak.name} pada {nak.pada}, lord {nak.lord}.",
        mechanism=(
            f"Longitude {_dms(longitude)} ÷ 13°20′ = {int(longitude // NAKSHATRA_SPAN)} "
            f"complete mansions → the {ordinal(nak.index + 1)} nakshatra, "
            f"{nak.name}. Remainder {_dms(within)} ÷ 3°20′ → pada "
            f"{nak.pada}. Lords repeat in nines "
            f"(Ketu–Venus–Sun–Moon–Mars–Rahu–Jupiter–Saturn–Mercury): "
            f"{nak.index + 1} mod 9 → {nak.lord}."
        ),
        meaning=f"{nak.name} is {NAKSHATRA_QUALITY[nak.name]}.",
        confidence="Moderate",
    )


def explain_dasha_now(timeline: VimshottariTimeline,
                      when: datetime) -> Explanation:
    current = timeline.at(when)
    nak = timeline.moon_nakshatra
    elapsed_pct = 100 * (1 - timeline.balance_years
                         / dict(DASHA_SEQUENCE)[nak.lord])
    if current is None:
        return Explanation(
            fact="The queried date falls outside the 120-year cycle.",
            mechanism="Vimshottari covers 120 years from the notional start "
                      "of the birth mahadasha.",
            meaning="No dasha applies.", confidence="High",
        )
    md, ad = current
    return Explanation(
        fact=(f"Now running: {md.lord} mahādaśā, {ad.lord} antaradaśā "
              f"(until {ad.end:%b %Y})."),
        mechanism=(
            f"The Moon sat {elapsed_pct:.1f}% through {nak.name}, whose lord "
            f"{nak.lord} rules {dict(DASHA_SEQUENCE)[nak.lord]} years — the "
            f"remaining {100 - elapsed_pct:.1f}% gave a birth balance of "
            f"{timeline.balance_years:.2f} years. Mahadashas then follow the "
            f"fixed order "
            + " → ".join(f"{l} {y}y" for l, y in DASHA_SEQUENCE)
            + f". Each antaradaśā spans md_years × ad_years ÷ 120; within "
              f"{md.lord}'s period, {ad.lord}'s share runs "
              f"{ad.start:%b %Y} – {ad.end:%b %Y}."
        ),
        meaning=(
            f"A {md.lord} season — {DASHA_THEME[md.lord]} — currently "
            f"inflected by {ad.lord}: {DASHA_THEME[ad.lord]}."
        ),
        confidence="Moderate",
    )


def explain_yoga(chart: Chart, yoga: Yoga) -> Explanation:
    key = next((k for k in YOGA_MEANING if yoga.name.startswith(k)), None)
    if key is None:
        key = next((k for k in YOGA_MEANING if k in yoga.kind), "Dhana")
    meaning, conf = YOGA_MEANING[key]

    mech = f"Rule: {yoga.rule} Working: {yoga.detail}"
    if yoga.name.startswith("Gaja Kesari"):
        mech += (" Counting from the Moon: "
                 + counting_chain(chart.planets["Moon"].sign_index,
                                  chart.planets["Jupiter"].sign_index) + ".")
    if yoga.notes:
        mech += " Note: " + " ".join(yoga.notes)
    if yoga.cancelled:
        mech += " Held in check: " + "; ".join(yoga.cancellation) + "."

    return Explanation(
        fact=f"{yoga.name} is present"
             + (" (cancelled)" if yoga.cancelled else "")
             + f" — formed by {', '.join(yoga.planets)}.",
        mechanism=mech,
        meaning=meaning,
        confidence=conf,
    )


def explain_gocara(chart: Chart, snapshot: TransitSnapshot) -> Explanation:
    rows = []
    for name in ("Saturn", "Jupiter", "Rahu"):
        tp = snapshot.planets[name]
        rows.append(f"{name} in {tp.sign} → your {ordinal(tp.natal_house)} "
                    f"house")
    slow = "; ".join(rows)
    sat = snapshot.planets["Saturn"]
    chain = counting_chain(chart.lagna.sign_index, sat.position.sign_index)
    return Explanation(
        fact=f"Slow movers today: {slow}.",
        mechanism=(
            f"A transit occupies whichever natal house holds its current "
            f"sign. Example — Saturn at {sat.position.dms} {sat.sign}: "
            f"counting from your Lagna, {chain} — the "
            f"{ordinal(sat.natal_house)} house. Each graha also casts its "
            f"drishti from there (all cast the 7th; Mars adds 4/8, Jupiter "
            f"5/9, Saturn 3/10, the nodes 5/9)."
        ),
        meaning=(
            "Transits are weather over the natal promise: the slow movers "
            "(Saturn, Jupiter, the nodes) set the season; the fast ones "
            "time its days."
        ),
        confidence="Interpretive",
    )


def explain_dashboard(chart: Chart, timeline: VimshottariTimeline,
                      snapshot: TransitSnapshot,
                      yogas: list[Yoga]) -> list[ExplainedItem]:
    """The Paṭha feed: every dashboard output as a three-layer entry."""
    items = [
        ExplainedItem("Lagna", chart.lagna.sign, explain_lagna(chart)),
        ExplainedItem(
            "Lagna nakṣatra",
            nakshatra_of(chart.lagna.longitude).name,
            explain_nakshatra("The Lagna", chart.lagna.longitude)),
    ]
    for name in PLANETS:
        pos = chart.planets[name]
        items.append(ExplainedItem(
            name, f"{pos.sign} · house {pos.house}",
            explain_planet(chart, name)))
        items.append(ExplainedItem(
            f"{name} nakṣatra", nakshatra_of(pos.longitude).name,
            explain_nakshatra(name, pos.longitude)))
    items.append(ExplainedItem(
        "Daśā now", f"{timeline.moon_nakshatra.name}-born cycle",
        explain_dasha_now(timeline, snapshot.when)))
    items.append(ExplainedItem(
        "Gocara", snapshot.when.strftime("%d %B %Y"),
        explain_gocara(chart, snapshot)))
    for y in yogas:
        items.append(ExplainedItem(y.name, y.kind, explain_yoga(chart, y)))
    return items
