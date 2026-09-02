"""Doshas and anti-anxiety framing.

Design rules (Phase 10):
- No fear language anywhere — a lint test enforces this.
- A dosha is NEVER shown bare: its classical cancellation checks auto-run
  and display alongside it.
- Demanding transits always carry an end date and a progress fraction —
  weather has a forecast, and forecasts end.
- Myth-buster cards generate automatically for placements people fear,
  with the classical basis cited at text level.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from engine import PLANETS, SIGNS, Chart
from transits import (
    TransitSnapshot,
    angular_distance,
    next_sign_ingress,
    sign_entry_before,
    aspected_signs,
)
from yogas import (
    detect_kemadruma,
    detect_neecha_bhanga,
    detect_viparita_raja,
    dignity,
    dignity_at,
    dignity_grade_at,
    house_lords,
    in_own_sign,
    is_exalted,
)

WEATHER_FRAMING = (
    "Weather, not verdict. A chart is a sky-map, not a sentence: transits "
    "and dashas describe seasons that arrive, do their work, and end — "
    "every one of them dated below. Classical texts treat each difficult "
    "combination as a hypothesis to be tested against its cancellation "
    "conditions, so this page always runs those checks for you and shows "
    "the working."
)


@dataclass(frozen=True)
class Dosha:
    name: str
    formed: bool          # does the textbook pattern appear at all?
    active: bool          # still standing after the cancellation checks?
    rule: str             # classical formation rule, verbatim
    detail: str           # chart-specific working
    cancellations: tuple[str, ...] = field(default=())  # checks that PASSED
    checks_run: tuple[str, ...] = field(default=())     # every check tried
    start: datetime | None = None   # for time-bound doshas
    end: datetime | None = None
    progress: float | None = None   # 0–1 through the window
    next_window: str | None = None  # when it next begins, if not running


def _sign_distance(a: int, b: int) -> int:
    return (b - a) % 12 + 1


# --- Mangal (Kuja) dosha -------------------------------------------------------

# The widely-carried exception verse pairs a sign with each dosha house:
# Aries in the 1st, Scorpio in the 4th, Capricorn in the 7th, Cancer in the
# 8th, Sagittarius in the 12th — Mars there forms no dosha.
_MANGAL_HOUSES = (1, 2, 4, 7, 8, 12)
_MANGAL_SIGN_EXCEPTION = {1: 0, 4: 7, 7: 9, 8: 3, 12: 8}


def detect_mangal(chart: Chart) -> Dosha:
    mars = chart.planets["Mars"]
    formed = mars.house in _MANGAL_HOUSES
    rule = ("Mangal dosha forms when Mars occupies house 1, 2, 4, 7, 8 or "
            "12 from the Lagna.")
    if not formed:
        return Dosha(
            name="Mangal dosha", formed=False, active=False, rule=rule,
            detail=f"Mars occupies house {mars.house} — the pattern does "
                   "not form.",
        )

    checks, passed = [], []

    check = ("sign-exception verse (Aries in 1st, Scorpio in 4th, Capricorn "
             "in 7th, Cancer in 8th, Sagittarius in 12th)")
    checks.append(check)
    if _MANGAL_SIGN_EXCEPTION.get(mars.house) == mars.sign_index:
        passed.append(
            f"Mars stands in {mars.sign} in house {mars.house} — exactly "
            f"the pairing the exception verse names; the dosha does not "
            f"apply. [{check}]")

    check = "Mars in own or exaltation sign"
    checks.append(check)
    if in_own_sign(chart, "Mars") or is_exalted(chart, "Mars"):
        passed.append(f"Mars is dignified ({dignity(chart, 'Mars')}). "
                      f"[{check}]")

    check = "Jupiter conjunct or aspecting Mars"
    checks.append(check)
    jup = chart.planets["Jupiter"]
    if (jup.sign_index == mars.sign_index
            or mars.sign_index in aspected_signs("Jupiter", jup.sign_index)):
        passed.append(f"Jupiter tempers Mars. [{check}]")

    check = "Moon conjunct Mars (Chandra-Mangala)"
    checks.append(check)
    if chart.planets["Moon"].sign_index == mars.sign_index:
        passed.append(f"The Moon joins Mars. [{check}]")

    return Dosha(
        name="Mangal dosha", formed=True, active=not passed, rule=rule,
        detail=f"Mars occupies house {mars.house} ({mars.sign}) — the "
               "textbook pattern appears, so the cancellation checks run "
               "automatically.",
        cancellations=tuple(passed), checks_run=tuple(checks),
    )


# --- Kaal Sarpa ---------------------------------------------------------------

def detect_kaal_sarpa(chart: Chart) -> Dosha:
    rahu = chart.planets["Rahu"].longitude
    ketu = chart.planets["Ketu"].longitude
    bodies = [p for p in PLANETS if p not in ("Rahu", "Ketu")]

    def within(lo: float, planet: str) -> bool:
        return (chart.planets[planet].longitude - lo) % 360.0 < 180.0

    side_a = [p for p in bodies if within(rahu, p)]      # Rahu → Ketu arc
    side_b = [p for p in bodies if not within(rahu, p)]  # Ketu → Rahu arc
    formed = not side_a or not side_b
    rule = ("Kaal Sarpa forms only when all seven classical grahas stand "
            "on one side of the Rahu–Ketu axis.")
    outside = side_a if len(side_a) <= len(side_b) else side_b
    if not formed:
        return Dosha(
            name="Kaal Sarpa", formed=False, active=False, rule=rule,
            detail="Planets stand on both sides of the nodal axis ("
                   + ", ".join(outside) + " break the hemicycle) — the "
                   "pattern does not form.",
        )
    # Which arc holds them, and by how little — the margin is the whole
    # question, since one graha crossing the axis dissolves the pattern.
    head, tail = ("Rahu", "Ketu") if side_a else ("Ketu", "Rahu")
    start = rahu if side_a else ketu
    margins = {p: (chart.planets[p].longitude - start) % 360.0
               for p in bodies}
    nearest = min(margins, key=margins.get)
    furthest = max(margins, key=margins.get)
    return Dosha(
        name="Kaal Sarpa", formed=True, active=True, rule=rule,
        detail=f"All seven grahas stand within one hemicycle of the nodal "
               f"axis — the {head}→{tail} arc. {nearest} sits closest to "
               f"{head} ({margins[nearest]:.1f}° past it) and {furthest} "
               f"closest to {tail} ({180.0 - margins[furthest]:.1f}° short "
               f"of it); either margin closing would dissolve the pattern.",
        checks_run=("any planet outside the hemicycle dissolves the "
                    "pattern",),
    )


# --- Sade Sati ------------------------------------------------------------------

def sade_sati_status(chart: Chart, now: datetime) -> Dosha:
    """Saturn transiting the 12th, 1st or 2nd sign from the natal Moon.
    Always dated: if running — start, end, progress; if not — when the next
    window begins."""
    moon_sign = chart.planets["Moon"].sign_index
    window_signs = {(moon_sign - 1) % 12, moon_sign, (moon_sign + 1) % 12}
    from engine import julian_day_ut, sidereal_positions
    sat_sign = sidereal_positions(julian_day_ut(now))["Saturn"].sign_index
    rule = ("Sade Sati runs while Saturn transits the 12th, 1st and 2nd "
            "signs counted from the natal Moon — about 7½ years in ~29.5.")

    if sat_sign in window_signs:
        start = sign_entry_before("Saturn", now)
        # walk forward until Saturn leaves the three-sign window
        t, end = now, None
        for _ in range(8):
            ing = next_sign_ingress("Saturn", t, max_days=3000)
            if ing is None:
                break
            if ing.to_sign_index not in window_signs:
                end = ing.when
                break
            t = ing.when
        phase = {(moon_sign - 1) % 12: "first (rising)",
                 moon_sign: "second (peak)",
                 (moon_sign + 1) % 12: "third (setting)"}[sat_sign]
        progress = None
        if start and end:
            progress = (now - start).total_seconds() / \
                (end - start).total_seconds()
        return Dosha(
            name="Sade Sati", formed=True, active=True, rule=rule,
            detail=f"Saturn is in the {phase} phase, transiting "
                   f"{SIGNS[sat_sign]} relative to your Moon in "
                   f"{SIGNS[moon_sign]}. This phase ends "
                   f"{end:%b %Y}." if end else
                   f"Saturn transits {SIGNS[sat_sign]}.",
            start=start, end=end, progress=progress,
        )

    # not running: find the next entry into the 12th-from-Moon sign
    t, begin = now, None
    for _ in range(16):
        ing = next_sign_ingress("Saturn", t, max_days=11000)
        if ing is None:
            break
        if ing.to_sign_index == (moon_sign - 1) % 12:
            begin = ing.when
            break
        t = ing.when
    dist = _sign_distance(moon_sign, sat_sign)
    return Dosha(
        name="Sade Sati", formed=False, active=False, rule=rule,
        detail=f"Not running: Saturn transits {SIGNS[sat_sign]}, the "
               f"{_ordinal(dist)} sign from your Moon — outside the "
               "12th/1st/2nd window.",
        next_window=f"{begin:%b %Y}" if begin else None,
    )


# --- Transit weather (end dates + progress, always) -----------------------------

# Classical gocara favourability, houses counted from the natal Moon.
GOCARA_FAVOURABLE = {
    "Saturn": (3, 6, 11),
    "Jupiter": (2, 5, 7, 9, 11),
    "Rahu": (3, 6, 10, 11),
    "Ketu": (3, 6, 10, 11),
}

HOUSE_MEANING_BRIEF = {
    1: "the body and self-presentation", 2: "resources and speech",
    3: "effort and courage", 4: "home and the heart's ease",
    5: "creativity and study", 6: "work, health and debts",
    7: "partnership", 8: "transformation and the hidden",
    9: "dharma, teachers and fortune", 10: "career and public standing",
    11: "gains and networks", 12: "retreat, expenditure and release",
}


def _ordinal(n: int) -> str:
    return {1: "1st", 2: "2nd", 3: "3rd"}.get(n, f"{n}th")


def transit_weather(chart: Chart, snapshot: TransitSnapshot) -> list[dict]:
    """Slow-mover cards, one per Saturn/Jupiter/Rahu/Ketu — the nodes share
    motion but occupy different houses and strike different natal points,
    so both render. Every line is generated from computed facts: transit
    dignity, natal house meaning, Moon-relative gocara quality, and close
    conjunctions (≤3°, sub-1° flagged exact). End dates always shown."""
    moon_sign = chart.planets["Moon"].sign_index
    cards = []
    for planet in ("Saturn", "Jupiter", "Rahu", "Ketu"):
        tp = snapshot.planets[planet]
        entered = sign_entry_before(planet, snapshot.when)
        leaves = next_sign_ingress(planet, snapshot.when)
        progress = None
        if entered and leaves:
            progress = (snapshot.when - entered).total_seconds() / \
                (leaves.when - entered).total_seconds()
        until = leaves.when.strftime("%b %Y") if leaves else None
        from_moon = _sign_distance(moon_sign, tp.position.sign_index)
        demanding = from_moon in (4, 8, 12) or (
            planet == "Saturn" and from_moon in (1, 2, 12))
        quality = ("demanding" if demanding else
                   "supportive" if from_moon in GOCARA_FAVOURABLE[planet]
                   else "neutral")

        # (i) transit dignity, graded where it matters
        state = dignity_at(planet, tp.position.sign_index,
                           tp.position.degree_in_sign)
        grade = dignity_grade_at(planet, tp.position.sign_index,
                                 tp.position.degree_in_sign)
        parts = []
        if state != "neutral":
            parts.append(f"{planet} is {grade or state} in {tp.sign} — "
                         + ("its strongest terrain."
                            if state in ("exalted", "moolatrikona") else
                            "at home." if state == "own sign" else
                            "working uphill terrain, and finite."))
        # (ii) natal house + one-line meaning
        parts.append(f"It works through your {_ordinal(tp.natal_house)} "
                     f"house — {HOUSE_MEANING_BRIEF[tp.natal_house]}.")
        # (iii) Moon-relative gocara quality
        parts.append(f"Counted from the Moon it stands {_ordinal(from_moon)}"
                     f" — a {quality} gocara position"
                     + (", already part-done and dated above."
                        if quality == "demanding" else "."))

        # (iv) close conjunctions with natal planets
        contacts = []
        for natal in PLANETS:
            orb = angular_distance(tp.position.longitude,
                                   chart.planets[natal].longitude)
            if orb <= 3.0:
                contacts.append({"natal": natal, "orb": round(orb, 2),
                                 "exact": orb < 1.0})
        contacts.sort(key=lambda c: c["orb"])
        contact_note = None
        if contacts:
            c0 = contacts[0]
            contact_note = (
                f"Transit {planet} sits {c0['orb']}° from natal "
                f"{c0['natal']}"
                + (" — an exact contact" if c0["exact"] else "")
                + f", colouring {c0['natal']} themes until {planet} leaves "
                f"{tp.sign} in {until}." if until else ".")

        cards.append({
            "planet": planet,
            "sign": tp.sign,
            "natal_house": tp.natal_house,
            "from_moon": from_moon,
            "dignity": state,
            "quality": quality,
            "entered": entered.strftime("%b %Y") if entered else None,
            "until": until,
            "progress": round(progress, 3) if progress is not None else None,
            "demanding": demanding,
            "note": " ".join(parts),
            "contacts": contacts,
            "contact_note": contact_note,
            "confidence": "Interpretive",
        })
    return cards


# --- Myth-busters -----------------------------------------------------------------

@dataclass(frozen=True)
class MythBuster:
    placement: str
    myth: str
    classical_record: str
    citation: str
    confidence: str


def myth_busters(chart: Chart, now: datetime) -> list[MythBuster]:
    """Auto-generate a card for each feared placement actually present."""
    out = []
    mars = chart.planets["Mars"]

    mangal = detect_mangal(chart)
    if mangal.formed:
        out.append(MythBuster(
            placement=f"Mars in house {mars.house} (Mangal dosha pattern)",
            myth="Popular reading: marriage is blocked for anyone with "
                 "this placement.",
            classical_record="The tradition itself ships the pattern with "
                 "exception rules — sign-based exemptions, dignity, and "
                 "Jupiter's influence are checked before anything is "
                 "concluded" + (
                     ". In this chart the checks cancel it: "
                     + " ".join(mangal.cancellations)
                     if mangal.cancellations else
                     "; matching charts and remedial counsel are the "
                     "classical response, not fatalism."),
            citation="Exception verses carried in standard jyotisha "
                     "compendia and Muhurta literature.",
            confidence="Moderate",
        ))

    if dignity(chart, "Mars") == "debilitated":
        nb = detect_neecha_bhanga(chart)
        out.append(MythBuster(
            placement="Debilitated Mars (Cancer)",
            myth="Popular reading: a debilitated planet simply fails.",
            classical_record="Debilitation is a hypothesis with named "
                 "cancellation conditions (Neecha Bhanga). "
                 + (f"This chart satisfies them: {nb[0].detail}"
                    if nb else "This chart does not satisfy them, which "
                    "classically reads as effort required, not absence."),
            citation="Neecha Bhanga conditions as given in Brihat Parashara "
                     "Hora Shastra's Raja Yoga chapters and Phaladeepika.",
            confidence="High",
        ))

    if mars.house == 8:
        # The Viparita clause has to be READ OFF THIS CHART. It used to be
        # hardcoded to one chart's configuration, which would have asserted
        # a yoga that most 8th-house-Mars charts do not have.
        mars_houses = sorted(h for h, lord in house_lords(chart).items()
                             if lord == "Mars")
        viparita = [y for y in detect_viparita_raja(chart)
                    if "Mars" in y.planets]
        if viparita:
            clause = (f" — and the Viparita logic even turns dusthana lords "
                      f"in dusthanas into gains through adversity, which is "
                      f"this chart: {viparita[0].detail}")
        elif mars_houses:
            clause = (f" — and here Mars rules "
                      f"{' and '.join(_ordinal(h) for h in mars_houses)}, so "
                      f"what the placement actually carries is those houses' "
                      f"affairs, not a verdict.")
        else:
            clause = ""
        out.append(MythBuster(
            placement="Mars in the 8th house",
            myth="Popular reading: an 8th-house Mars is uniformly harmful.",
            classical_record="The 8th is the house of research, longevity "
                 "and other people's resources; classical results depend on "
                 "sign, dignity and aspects" + clause,
            citation="Viparita Raja Yoga as defined in classical "
                     "compilations (Phaladeepika; Uttara Kalamrita).",
            confidence="Moderate",
        ))

    ks = detect_kaal_sarpa(chart)
    if ks.formed:
        out.append(MythBuster(
            placement="Kaal Sarpa (all grahas inside the nodal arc)",
            myth="Popular reading: the whole life is bound and nothing "
                 "arrives on time until an expensive remedy is performed.",
            classical_record="The pattern is absent from Brihat Parashara "
                 "Hora Shastra and the other foundational texts; it enters "
                 "the literature late and its rules were never settled — "
                 "authorities differ on whether the axis must be exact, "
                 "whether the lagna counts, and whether it applies at all. "
                 "What is computable is the geometry: " + ks.detail,
            citation="Absent from BPHS, Phaladeepika and Saravali; a "
                     "modern addition of disputed and recent standing.",
            confidence="Interpretive",
        ))

    kem = detect_kemadruma(chart)
    if kem and kem[0].cancelled:
        out.append(MythBuster(
            placement="Kemadruma pattern (unaccompanied Moon)",
            myth="Popular reading: an unaccompanied Moon means a life of "
                 "isolation.",
            classical_record="Kemadruma is defined together with its "
                 "exceptions; here they apply: "
                 + "; ".join(kem[0].cancellation) + ".",
            citation="Kemadruma exceptions as listed in standard Chandra "
                     "yoga chapters.",
            confidence="Moderate",
        ))

    sade = sade_sati_status(chart, now)
    if sade.active or sade.next_window:
        out.append(MythBuster(
            placement="Sade Sati (Saturn's 7½-year Moon transit)",
            myth="Popular reading: seven and a half years of unbroken "
                 "hardship.",
            classical_record="Classically it is Saturn auditing the mind's "
                 "house: three distinct phases, each dated, with results "
                 "conditioned by Saturn's dignity and the chart — many "
                 "texts note the peak phase builds what lasts. "
                 + ("It is not running for you now; the next window opens "
                    f"{sade.next_window} — dated, finite, survivable."
                    if not sade.active else
                    f"Your current phase ends {sade.end:%b %Y}."),
            citation="Sade Sati treatment in standard Saturn-transit "
                     "literature (gocara chapters).",
            confidence="Moderate",
        ))
    return out


def doshas_all(chart: Chart, now: datetime) -> list[Dosha]:
    return [detect_mangal(chart), detect_kaal_sarpa(chart),
            sade_sati_status(chart, now)]
