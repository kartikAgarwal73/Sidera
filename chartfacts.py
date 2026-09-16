"""The fact ledger — every computed statement the agent is allowed to use.

WHY THIS FILE EXISTS
Sidera's product claim is that a reading shows its computation. An LLM that
paraphrases a chart breaks that claim silently: fluent text about a Mars it
placed in the wrong house is indistinguishable, to a reader, from fluent text
about the real one.

So the agent never sees a chart object and never computes. It sees this
ledger: a flat list of facts, each with a stable ID, each already computed by
the engine. Its job is selection and phrasing over a closed set. Anything not
in the ledger is, by construction, not derivable — and the agent is required
to say so rather than fill the gap.

The IDs are the citation vocabulary. They are stable so a stored answer can
be re-checked against a re-computed chart later, and so `agent.validate()`
can verify that every placement the model asserted actually exists here.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime

from dashas import nakshatra_table, vimshottari
from doshas import doshas_all, transit_weather
from engine import PLANETS, SIGNS, Chart
from explain import ordinal
import schools
from rulelib import (
    CONTACT_PRECEDENCE_RULE,
    GENERAL_GOCARA_RULE,
    KARAKATVAS,
    NAME_BOTH_RULE,
    NATURAL_BENEFICS,
)
from transits import (
    CONJUNCTION_ORB,
    drishti_offsets as _drishti_offsets,
    TransitSnapshot,
    angular_distance,
    aspects_on_house,
    aspected_signs,
    natal_aspect_table,
    next_sign_ingress,
    sign_entry_before,
    transit_snapshot,
)
from vargas import dasamsa, navamsa
import arudhas
import avasthas
import karakas
import vimsopaka
from ashtakavarga import BODIES as AV_BODIES
from ashtakavarga import REDUCTIONS_NOTE, STRONG_FLOOR as av_strong
from ashtakavarga import THIN_CEILING as av_thin
from ashtakavarga import ashtakavarga
from ashtakavarga import strongest as av_strongest
from ashtakavarga import thinnest as av_thinnest
from ashtakavarga import verdict as ashtakavarga_verdict
from yogas import (COMBUSTION_ORB, COMBUSTION_ORB_RETRO, combust,
                   detect_all, dignity, dignity_at, dignity_grade,
                   house_lords, houses_owned_by, sign_lord)


@dataclass(frozen=True)
class Fact:
    """One computed statement, addressable by ID."""

    id: str
    kind: str        # lagna | planet | house | aspect | yoga | dasha | …
    statement: str   # plain-language, already true of this chart
    value: dict      # the structured values behind the statement

    def as_dict(self) -> dict:
        return asdict(self)


def _slug(text: str) -> str:
    keep = [c.lower() if c.isalnum() else "-" for c in text]
    return "".join(keep).strip("-").replace("--", "-")


NODES = {"Rahu", "Ketu"}


def school_note(*option_ids: str) -> str:
    """The provenance clause a school-dependent statement carries.

    The rule is not "mention it when it is unusual" — a reader comparing
    this chart against another astrologer's cannot tell from the number
    which convention produced it, and the default is a convention too.
    """
    note = schools.note_for(*option_ids)
    return f" (Computed under: {note}.)" if note else ""


def _combustion(chart: Chart, name: str) -> dict:
    """Whether a graha is burnt, with the orb it was judged by and its
    distance from the Sun — so a fact can say "combust, 3.63° from the Sun
    inside Mercury's 14°" rather than a bare flag. The orb table and the
    retrograde tightening are `yogas`'s; rule.graha.combust states them.
    The Sun and the nodes carry `combust: False` and no orb."""
    if name not in COMBUSTION_ORB:
        return {"combust": False, "combust_orb": None, "sun_distance": None}
    pos = chart.planets[name]
    orb = COMBUSTION_ORB[name]
    if pos.retrograde and name in COMBUSTION_ORB_RETRO:
        orb = COMBUSTION_ORB_RETRO[name]
    gap = angular_distance(pos.longitude, chart.planets["Sun"].longitude)
    return {"combust": combust(chart, name), "combust_orb": orb,
            "sun_distance": round(gap, 2)}


def _combust_clause(c: dict) -> str:
    if not c["combust"]:
        return ""
    return (f" It is combust (asta), {c['sun_distance']}° from the Sun "
            f"inside its {c['combust_orb']:g}° orb.")


def _and_list(items: list[str]) -> str:
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + " and " + items[-1]


# The generic gocara verdict, in the same words `rule.transit.from_moon`
# uses. It is quoted in the contact fact so the agent can see exactly which
# claim the contact is displacing.
def _gocara_quality(from_moon: int) -> str:
    if from_moon in (3, 6, 10, 11):
        return "supportive"
    if from_moon in (4, 8, 12):
        return "demanding"
    return "neutral"


def transit_contacts_summary(chart: Chart, when: datetime,
                             snapshot: TransitSnapshot | None = None,
                             orb: float = CONJUNCTION_ORB) -> list[dict]:
    """Every transit-to-natal contact within `orb`, with what it suppresses.

    This is the fact the reading kept losing. A node 2.66° from natal Venus
    is a specific statement about Venus — its lordships, its karakatvas —
    and the generic "3rd from the Moon is supportive" verdict is a statement
    about nothing in particular. One line of this ledger has to carry both,
    plus which of the two governs, or the agent is left to guess and picks
    the one it saw first.

    Shared with the validator so the check and the prompt cannot drift.
    """
    snapshot = snapshot or transit_snapshot(chart, when)
    moon_sign = chart.planets["Moon"].sign_index
    out: list[dict] = []
    for t in PLANETS:
        tp = snapshot.planets[t]
        from_moon = (tp.position.sign_index - moon_sign) % 12 + 1
        targets = [(n, chart.planets[n].longitude) for n in PLANETS]
        targets.append(("Lagna", chart.lagna.longitude))
        for point, longitude in targets:
            gap = angular_distance(tp.position.longitude, longitude)
            if gap > orb:
                continue
            if point == "Lagna":
                owns, karaka = (), "the body, vitality and how you are met"
                sign, house = chart.lagna.sign, 1
                benefic = False
            else:
                np_ = chart.planets[point]
                owns = houses_owned_by(chart, point)
                karaka = KARAKATVAS[point]
                sign, house = np_.sign, np_.house
                benefic = point in NATURAL_BENEFICS
            out.append({
                "id": f"contact.{t.lower()}-{point.lower()}",
                "transit": t,
                "point": point,
                "orb": round(gap, 2),
                "exact": gap < 1.0,
                "natal_sign": sign,
                "natal_house": house,
                "lordships": list(owns),
                "karakatvas": karaka,
                "node": t in ("Rahu", "Ketu"),
                "benefic": benefic,
                "from_moon": from_moon,
                "generic_quality": _gocara_quality(from_moon),
                "governs": True,
                "outranks_rule": GENERAL_GOCARA_RULE,
                "governing_rule": ("rule.transit.node_on_natal"
                                   if t in ("Rahu", "Ketu")
                                   else "rule.transit.contact"),
                "slow_mover": t in ("Saturn", "Jupiter", "Rahu", "Ketu"),
            })
    out.sort(key=lambda c: (c["orb"], c["id"]))
    return out


def transit_aspects(chart: Chart, when: datetime,
                    snapshot: TransitSnapshot | None = None) -> dict:
    """{planet: [natal houses it aspects]} for today's sky.

    WHY THE LEDGER NEEDS THIS SEPARATELY FROM OCCUPATION
    Occupation says where a graha *is*; drishti says everything else it is
    doing. Saturn in the 4th is also working the 10th, and a reading that
    only reports occupancy silently drops two-thirds of what the classical
    method looks at.

    The offsets come from `transits.drishti_offsets`, which follows the
    reader's answer to "How far does the influence of Rahu and Ketu reach?"
    — so the nodes' rows here are the selected school's, not a constant.
    Shared with the validator, so a claim can be checked against exactly the
    table the ledger published.
    """
    snapshot = snapshot or transit_snapshot(chart, when)
    lagna = chart.lagna.sign_index
    return {
        name: sorted((s - lagna) % 12 + 1
                     for s in aspected_signs(
                         name, snapshot.planets[name].position.sign_index))
        for name in PLANETS
    }


def _window(planet: str, when: datetime) -> dict:
    """When this transit began and when it ends, as dated strings.

    Timing may only be quoted as a window the ledger produced. Without the
    entry date the agent has half a window and tends to invent the other
    half — which `find_invented_dates` then withholds the whole answer for.
    """
    # sign_entry_before returns a datetime; next_sign_ingress an Ingress.
    entered = sign_entry_before(planet, when)
    leaves = next_sign_ingress(planet, when)
    leaves_at = leaves.when if leaves else None
    return {
        "entered": entered.strftime("%b %Y") if entered else None,
        "until": leaves_at.strftime("%b %Y") if leaves_at else None,
        "entered_iso": entered.date().isoformat() if entered else None,
        "until_iso": leaves_at.date().isoformat() if leaves_at else None,
    }


def _contact_statement(c: dict) -> str:
    """One contact, written so the precedence cannot be read off wrongly."""
    where = (f"your lagna ({c['natal_sign']})" if c["point"] == "Lagna"
             else (f"natal {c['point']} ({c['natal_sign']}, "
                   f"{ordinal(c['natal_house'])} house)"))
    parts = [
        f"TRANSIT CONTACT (today, not birth): transit {c['transit']} stands "
        f"{c['orb']}° from {where}"
        + (" — an exact contact." if c["exact"] else ".")
    ]

    # (1) the suppressed significations, concretely
    if c["lordships"]:
        houses = _and_list([f"{ordinal(h)}" for h in c["lordships"]])
        parts.append(f"{c['point']} rules the {houses} house"
                     f"{'s' if len(c['lordships']) > 1 else ''} in this "
                     f"chart, and is the natural karaka of "
                     f"{c['karakatvas']}.")
    elif c["point"] == "Lagna":
        parts.append(f"The lagna carries {c['karakatvas']}.")
    else:
        parts.append(f"{c['point']} rules no sign, so it is read from the "
                     f"house it occupies and from its dispositor; it is the "
                     f"natural karaka of {c['karakatvas']}.")

    # (2) what the contact does
    if c["node"]:
        verb = ("withdraws and severs" if c["transit"] == "Ketu"
                else "inflates and adulterates")
        parts.append(
            f"A node on a natal point is read as an eclipse: while the orb "
            f"holds, those significations are obscured or withheld rather "
            f"than delivered — {c['transit']} {verb}."
            + (f" {c['point']} is a natural benefic, so what is suppressed "
               f"is exactly what it protects." if c["benefic"] else ""))
    else:
        parts.append(
            f"A transit within orb of a natal point acts on that point's "
            f"affairs, not merely on the house the transit occupies.")

    # (3) the precedence, spelled out with both rule ids
    parts.append(
        f"PRECEDENCE: transit {c['transit']} stands "
        f"{ordinal(c['from_moon'])} from the natal Moon, which the generic "
        f"gocara rule ({GENERAL_GOCARA_RULE}) reads as "
        f"{c['generic_quality']}. This contact GOVERNS that verdict "
        f"({CONTACT_PRECEDENCE_RULE}). Name both readings, say the "
        f"conjunction governs and why, and do not call this transit "
        f"{c['generic_quality']} unqualified ({NAME_BOTH_RULE}).")
    return " ".join(parts)


def build_facts(chart: Chart, when: datetime) -> list[Fact]:
    """The complete ledger for one chart at one moment.

    Ordered by kind so the serialised form is stable — an unstable ordering
    would defeat prompt caching and make stored answers hard to diff.
    """
    facts: list[Fact] = []
    lords = house_lords(chart)
    naks = nakshatra_table(chart)
    timeline = vimshottari(chart)

    # --- lagna -------------------------------------------------------------
    facts.append(Fact(
        id="lagna",
        kind="lagna",
        statement=(f"The Lagna (ascendant) is {chart.lagna.sign} at "
                   f"{chart.lagna.dms}, in the nakshatra "
                   f"{naks['Lagna'].name} pada {naks['Lagna'].pada}."),
        value={"sign": chart.lagna.sign,
               "degree": round(chart.lagna.degree_in_sign, 4),
               "nakshatra": naks["Lagna"].name,
               "pada": naks["Lagna"].pada},
    ))

    # --- planets -----------------------------------------------------------
    for name in PLANETS:
        p = chart.planets[name]
        grade = dignity_grade(chart, name)
        nak = naks[name]
        retro = " (retrograde)" if p.retrograde else ""
        burnt = _combustion(chart, name)
        facts.append(Fact(
            id=f"planet.{name.lower()}",
            kind="planet",
            statement=(
                f"{name} is in {p.sign} at {p.dms}{retro}, in the "
                f"{ordinal(p.house)} house, in the nakshatra {nak.name} "
                f"pada {nak.pada} (lord {nak.lord})"
                + (f" — dignity: {grade}." if grade else ".")
                + _combust_clause(burnt)
                + (school_note("node_position") if name in NODES else "")),
            value={"planet": name, "sign": p.sign, "house": p.house,
                   "degree": round(p.degree_in_sign, 4),
                   "retrograde": p.retrograde, "nakshatra": nak.name,
                   "pada": nak.pada, "nakshatra_lord": nak.lord,
                   "dignity": grade or None, **burnt},
        ))

    # --- houses ------------------------------------------------------------
    occupants = chart.houses
    for house in range(1, 13):
        sign = chart.house_signs[house]
        here = occupants[house]
        facts.append(Fact(
            id=f"house.{house}",
            kind="house",
            statement=(
                f"The {ordinal(house)} house is {sign}, ruled by "
                f"{lords[house]}" + (
                    f", occupied by {', '.join(here)}." if here
                    else ", with no graha in it.")),
            value={"house": house, "sign": sign, "lord": lords[house],
                   "occupants": here},
        ))

    # --- house lords, as their own facts ------------------------------------
    # Step 1 of the reading checklist asks where each domain house's LORD
    # sits and how well it is placed. That was derivable from two other
    # facts and therefore, in practice, skipped: the agent would name the
    # 7th house and stop. One fact per lord, `natal.7L`, makes the step
    # answerable in a single citation — and its absence visible.
    for house in range(1, 13):
        lord = lords[house]
        lp = chart.planets[lord]
        grade = dignity_grade(chart, lord) or dignity(chart, lord)
        onto = aspects_on_house(chart, house)
        also = [h for h in houses_owned_by(chart, lord) if h != house]
        facts.append(Fact(
            id=f"natal.{house}L",
            kind="lord",
            statement=(
                f"The lord of the {ordinal(house)} house is {lord}, which "
                f"sits in {lp.sign} in the {ordinal(lp.house)} house"
                + (f" — dignity: {grade}" if grade else "")
                + (f". {lord} also rules the "
                   + _and_list([ordinal(h) for h in also]) + " house"
                   + ("s" if len(also) > 1 else "") + "."
                   if also else ".")
                + (f" The {ordinal(house)} house receives drishti from "
                   + _and_list(onto) + "." if onto else
                   f" No graha aspects the {ordinal(house)} house.")),
            value={"house": house, "lord": lord, "lord_sign": lp.sign,
                   "lord_house": lp.house, "lord_dignity": grade or None,
                   "lord_retrograde": lp.retrograde,
                   "also_rules": also, "aspected_by": onto,
                   "occupants": occupants[house]},
        ))

    # --- karakas ------------------------------------------------------------
    # Step 2. A graha's natural significations are constant, but its
    # CONDITION is not, and that condition is what the step asks for.
    for name in PLANETS:
        p = chart.planets[name]
        grade = dignity_grade(chart, name) or dignity(chart, name)
        onto = [a.aspecting for a in natal_aspect_table(chart)
                if a.aspected == name]
        owns = houses_owned_by(chart, name)
        burnt = _combustion(chart, name)
        facts.append(Fact(
            id=f"karaka.{name.lower()}",
            kind="karaka",
            statement=(
                f"As a natural significator, {name} carries "
                f"{KARAKATVAS[name]}. In this chart it is in {p.sign}, "
                f"{ordinal(p.house)} house"
                + (f", dignity {grade}" if grade else "")
                + (", retrograde" if p.retrograde else "")
                + (", combust" if burnt["combust"] else "")
                + (", ruling the " + _and_list([ordinal(h) for h in owns])
                   + " house" + ("s" if len(owns) > 1 else "")
                   if owns else ", ruling no sign")
                + (", and aspected by " + _and_list(onto) if onto
                   else ", unaspected")
                + "."),
            value={"planet": name, "karakatvas": KARAKATVAS[name],
                   "sign": p.sign, "house": p.house,
                   "dignity": grade or None, "retrograde": p.retrograde,
                   "rules": list(owns), "aspected_by": onto,
                   "benefic": name in NATURAL_BENEFICS, **burnt},
        ))

    # --- natal aspects -----------------------------------------------------
    # An aspect involving a node depends on an answer the reader gave, so it
    # carries that answer. The agent then cannot state a nodal aspect
    # without the school travelling with it.
    for a in natal_aspect_table(chart):
        nodal = NODES & {a.aspecting, a.aspected}
        note = school_note("node_reach") if nodal else ""
        facts.append(Fact(
            id=f"aspect.{a.aspecting.lower()}-{a.aspected.lower()}",
            kind="aspect",
            statement=(f"{a.aspecting} casts its {ordinal(a.offset)} "
                       f"drishti onto {a.aspected}." + note),
            value={"from": a.aspecting, "to": a.aspected,
                   "offset": a.offset,
                   "school": schools.chosen("node_reach").school
                             if nodal else None},
        ))

    # --- divisional charts -------------------------------------------------
    # Per-planet, not just the lagna. The app has computed and displayed
    # these all along while the ledger carried only a summary, so the agent
    # had to decline D9 questions it held the answers to.
    #
    # These are SIGN-LEVEL: `vargas.py` maps a natal longitude to a
    # divisional sign and discards the position within it. No varga degree,
    # so no varga nakshatra and no dignity-by-degree — stated in the fact
    # so the agent does not reach for what is not there.
    # EVERY DIVISION THIS BUILD CASTS, not two. The ledger carried D9 and
    # D10 only while the app computed only those; it is generic over
    # `vargas.SUPPORTED` now, so a division that lands is in the ledger the
    # same day it is in the gallery.
    #
    # These are DEGREE-LEVEL. `rule.varga.degree_convention` states what the
    # degree is — a scaling convention, not something the texts assign — and
    # every fact here carries that caveat so the agent cannot quote a
    # divisional degree as a classical figure.
    from vargas import (READ_FOR as _READ_FOR, SCHOOL_NOTE as _SCHOOL_NOTE,
                        SUPPORTED as _SUPPORTED, varga_chart as _varga_chart)
    _DEGREE_CAVEAT = (" (The divisional degree is a scaling convention — the "
                      "position within the part, stretched over 30° — not a "
                      "figure the classical texts assign.)")
    for code in _SUPPORTED:
        label = code.lower()
        varga = _varga_chart(chart, code)
        vfor = _READ_FOR[code]
        school = _SCHOOL_NOTE.get(code)
        facts.append(Fact(
            id=f"varga.{label}.lagna",
            kind="varga",
            statement=(f"The {code} lagna is {varga.lagna_sign} "
                       f"{varga.lagna_degree_in_sign:.2f}°. This varga is "
                       f"read for {vfor}."
                       + (f" SCHOOL: {school}" if school else "")),
            value={"varga": code, "lagna": varga.lagna_sign,
                   "lagna_degree": round(varga.lagna_degree_in_sign, 4),
                   "read_for": vfor, "school": school},
        ))
        for name in PLANETS:
            vp = varga.planets[name]
            facts.append(Fact(
                id=f"varga.{label}.{name.lower()}",
                kind="varga",
                statement=(
                    f"In the {code}, {name} is in {vp.sign} {vp.dms}, in the "
                    f"{ordinal(vp.house)} house from the {code} lagna"
                    + (" — vargottama, the same sign it holds at birth."
                       if vp.vargottama else ".")
                    + _DEGREE_CAVEAT),
                value={"varga": code, "planet": name, "sign": vp.sign,
                       "house": vp.house, "vargottama": vp.vargottama,
                       "degree": round(vp.degree_in_sign, 4),
                       # Dignity by degree in the division — the thing the
                       # degree-level vargas were built to make computable.
                       # Added 2026-09-14 so a reading that names a varga
                       # lord's sign can say its condition there too.
                       "dignity": dignity_at(name, vp.sign_index,
                                             vp.degree_in_sign)},
            ))
        vargottama = [n for n, v in varga.planets.items() if v.vargottama]
        if code == "D9" and vargottama:
            facts.append(Fact(
                id="varga.d9.vargottama",
                kind="varga",
                statement=("Vargottama (same sign in D1 and D9): "
                           + ", ".join(vargottama) + "."),
                value={"planets": vargottama},
            ))

        # One fact per divisional HOUSE. Step 3 of the domain method asks
        # what is in the domain house of a divisional chart; before this the
        # answer was scattered across nine per-planet entries the agent had
        # to assemble itself, and did not.
        from engine import SIGNS as _SIGNS
        vlagna = varga.lagna_sign_index
        for house in range(1, 13):
            sign = _SIGNS[(vlagna + house - 1) % 12]
            here = [n for n in PLANETS if varga.planets[n].house == house]
            lord = sign_lord(_SIGNS.index(sign))
            lord_in = varga.planets[lord].house
            facts.append(Fact(
                id=f"{label}.{ordinal(house)}",
                kind="varga",
                statement=(
                    f"In the {code}, the {ordinal(house)} house is {sign}, "
                    f"ruled by {lord} (which sits in the {ordinal(lord_in)} "
                    f"house of the {code})"
                    + (", occupied by " + _and_list(here) + "."
                       if here else ", with no graha in it.")),
                value={"varga": code, "house": house, "sign": sign,
                       "lord": lord, "lord_house": lord_in,
                       "occupants": here},
            ))

    # --- yogas -------------------------------------------------------------
    #
    # THREE FACTS PER YOGA, not one. The ledger used to carry only the
    # detection, so the two things a reading actually asserts about a yoga —
    # that the divisional charts confirm it, and that a period of its
    # forming grahas runs from such a date to such a date — rested on
    # nothing the validator could check. A claim the ledger cannot back is
    # exactly what this file exists to make impossible.
    import yogaread as _yogaread
    # One shared computation for every yoga — see `yogaread._Shared`.
    _shared = _yogaread.shared_for(chart, when)
    for yoga in detect_all(chart):
        # The id comes from `yogaread`, which is what CITES it. See
        # `yoga_fact_id` — the two used to slug the same name differently.
        base = _yogaread.yoga_fact_id(yoga.name)
        facts.append(Fact(
            id=base,
            kind="yoga",
            statement=f"{yoga.name}: {yoga.detail}",
            value={"name": yoga.name, "rule": yoga.rule,
                   "detail": yoga.detail, "planets": list(yoga.planets),
                   "houses": list(yoga.houses), "kind": yoga.kind,
                   "cancelled": yoga.cancelled,
                   "notes": list(yoga.notes)},
        ))
        reading = _yogaread.read_yoga(yoga, chart, when, _shared)
        tests = {t.varga: t for t in reading.varga_tests}
        facts.append(Fact(
            id=f"{base}.varga",
            kind="yoga",
            statement=(
                f"{yoga.name} in the divisional charts — "
                + " ".join(f"{t.varga}: {t.detail}"
                           for t in reading.varga_tests)
                + " (Sign-level only: this build computes no degree within a "
                  "divisional sign, so there is no moolatrikona here.)"),
            value={"name": yoga.name,
                   "tested_in": [t.varga for t in reading.varga_tests],
                   "confirmed": {t.varga: t.confirmed
                                 for t in reading.varga_tests},
                   "strong": {v: list(t.strong) for v, t in tests.items()},
                   "weak": {v: list(t.weak) for v, t in tests.items()},
                   "degree": None},
        ))
        acts = reading.activations
        facts.append(Fact(
            id=f"{base}.activation",
            kind="yoga",
            statement=(
                f"{yoga.name} is carried by {', '.join(yoga.planets)}; "
                + ("their periods: "
                   + "; ".join(f"{a.lord} {a.level} {a.start:%b %Y}–"
                               f"{a.end:%b %Y} ({a.state})" for a in acts)
                   + "."
                   if acts else
                   "no period of these grahas falls inside the 120-year "
                   "cycle this chart covers.")),
            value={"name": yoga.name,
                   "periods": [{"lord": a.lord, "level": a.level,
                                "start": a.start.isoformat(),
                                "end": a.end.isoformat(), "state": a.state}
                               for a in acts]},
        ))

    # --- ashtakavarga ------------------------------------------------------
    #
    # NINETEEN FACTS, not ninety-six. `sav.house.N` ×12 plus `bav.<planet>`
    # ×7 carrying a twelve-value array each. Per-planet-per-house ids would
    # have needed 84 more, tripling the prompt payload and burying the
    # useful facts under a grid nobody asks about.
    av = ashtakavarga(chart)
    by_house = av.sav_by_house
    for house in range(1, 13):
        score = by_house[house]
        facts.append(Fact(
            id=f"sav.house.{house}",
            kind="ashtakavarga",
            statement=(
                f"The {ordinal(house)} house ({av.sign_of_house(house)}) "
                f"carries {score} Sarvashtakavarga bindus out of the 337 "
                f"this chart distributes"
                + (" — among its strongest." if score >= av_strong
                   else " — among its thinnest." if score <= av_thin
                   else ".")
                + " RAW: no trikona or ekadhipatya sodhana applied."),
            value={"house": house, "sign": av.sign_of_house(house),
                   "bindus": score, "raw": True},
        ))
    for planet in AV_BODIES:
        row = av.bav_by_sign[planet]
        facts.append(Fact(
            id=f"bav.{planet.lower()}",
            kind="ashtakavarga",
            statement=(
                f"{planet}'s Bhinnashtakavarga, by house from the lagna: "
                + ", ".join(f"{ordinal(h)} {v}"
                            for h, v in av.by_house(row).items())
                + f" (total {sum(row)}). RAW: no reductions applied."),
            value={"planet": planet, "by_sign": list(row),
                   "by_house": av.by_house(row), "total": sum(row),
                   "raw": True},
        ))
    facts.append(Fact(
        id="sav.summary",
        kind="ashtakavarga",
        statement=(
            ashtakavarga_verdict(av) + " " + REDUCTIONS_NOTE),
        value={"strongest": av_strongest(av), "thinnest": av_thinnest(av),
               "total": av.sav_total, "raw": True},
    ))

    # --- dashas ------------------------------------------------------------
    current = timeline.at(when)
    if current:
        md, ad = current
        facts.append(Fact(
            id="dasha.current",
            kind="dasha",
            statement=(f"The running period is the {md.lord} mahadasha "
                       f"({md.start:%b %Y} – {md.end:%b %Y}) with the "
                       f"{ad.lord} antardasha ({ad.start:%b %Y} – "
                       f"{ad.end:%b %Y})."),
            value={"mahadasha": md.lord, "antardasha": ad.lord,
                   "md_start": md.start.isoformat(),
                   "md_end": md.end.isoformat(),
                   "ad_start": ad.start.isoformat(),
                   "ad_end": ad.end.isoformat()},
        ))
    for md in timeline.mahadashas:
        facts.append(Fact(
            id=f"dasha.md.{md.lord.lower()}",
            kind="dasha",
            statement=(f"The {md.lord} mahadasha runs {md.start:%b %Y} – "
                       f"{md.end:%b %Y} ({md.years:.0f} years)."),
            value={"lord": md.lord, "start": md.start.isoformat(),
                   "end": md.end.isoformat(), "years": round(md.years, 2)},
        ))

    # --- transits ----------------------------------------------------------
    # ALL NINE, not just the slow movers. A question about the months ahead
    # is answered mostly from transits, and a fact the agent does not have
    # is one it either omits or invents — the ledger has to carry every
    # position the validator will later check a claim against.
    snapshot = transit_snapshot(chart, when)
    weather = {c["planet"]: c for c in transit_weather(chart, snapshot)}
    contacts = transit_contacts_summary(chart, when, snapshot)
    aspects = transit_aspects(chart, when, snapshot)
    by_transit: dict[str, list[dict]] = {}
    for c in contacts:
        by_transit.setdefault(c["transit"], []).append(c)
    for name in PLANETS:
        tp = snapshot.planets[name]
        card = weather.get(name)
        retro = " (retrograde)" if tp.retrograde else ""
        detail = (f" It runs there until {card['until']}. {card['note']}"
                  if card else "")
        # The from-the-Moon verdict lives inside `card['note']`, and a live
        # reading quoted it as the answer while a node sat 2.66° off natal
        # Venus. The general verdict must not be the last thing this fact
        # says when a contact is standing on top of it.
        touching = by_transit.get(name, [])
        override = ""
        if touching:
            named = _and_list([
                (f"your lagna" if c["point"] == "Lagna"
                 else f"natal {c['point']}") + f" ({c['orb']}°)"
                for c in touching])
            override = (
                f" GOVERNING CONTACT: transiting {name} is within "
                f"{CONJUNCTION_ORB:.0f}° of {named}. That contact is the "
                f"governing reading for this transit and outranks the "
                f"from-the-Moon verdict above "
                f"({CONTACT_PRECEDENCE_RULE}) — see "
                + ", ".join(c["id"] for c in touching) + ".")
        facts.append(Fact(
            id=f"transit.{name.lower()}",
            kind="transit",
            statement=(
                f"TRANSIT (today, not birth): {name} is currently moving "
                f"through {tp.sign}{retro}, which is your natal "
                f"{ordinal(tp.natal_house)} house.{detail}{override}"
                + (school_note("node_position") if name in NODES else "")),
            value={"planet": name, "sign": tp.sign,
                   "natal_house": tp.natal_house,
                   "retrograde": tp.retrograde,
                   "from_moon": card["from_moon"] if card else None,
                   "until": card["until"] if card else None,
                   "demanding": card["demanding"] if card else None,
                   "slow_mover": card is not None,
                   "aspects": aspects[name],
                   "governing_contacts": [c["id"] for c in touching]},
        ))

    # --- what each transit ASPECTS, not only what it occupies --------------
    # A reading built on occupancy alone drops most of what a transit does.
    # Saturn in the 4th is also disciplining the 10th, and the career
    # question turns on that. One fact per graha, with the window, so the
    # synthesis can say "…and it holds until <date>" without inventing one.
    for name in PLANETS:
        tp = snapshot.planets[name]
        window = _window(name, when)
        houses = aspects[name]
        slow = name in ("Saturn", "Jupiter", "Rahu", "Ketu")
        nodal = school_note("node_reach") if name in NODES else ""
        if houses:
            reach = ("its own drishti reaches your "
                     + _and_list([ordinal(h) for h in houses]) + " house"
                     + ("s" if len(houses) > 1 else ""))
        else:
            reach = "it casts no drishti at all under the selected school"
        facts.append(Fact(
            id=f"transit.{name.lower()}.aspects",
            kind="transit",
            statement=(
                f"TRANSIT DRISHTI (today, not birth): from {tp.sign} — your "
                f"{ordinal(tp.natal_house)} house — transiting {name}, "
                f"{reach}."
                + (f" It entered {tp.sign} in {window['entered']}."
                   if window["entered"] else "")
                + (f" It leaves in {window['until']}."
                   if window["until"] else "")
                + ("" if slow else " It is a fast mover: this is texture "
                   "over the slow transits, not the main current.")
                + nodal),
            value={"planet": name, "sign": tp.sign,
                   "natal_house": tp.natal_house,
                   "aspects": houses,
                   "offsets": list(_drishti_offsets(name)),
                   "entered": window["entered"],
                   "until": window["until"],
                   "entered_iso": window["entered_iso"],
                   "until_iso": window["until_iso"],
                   "slow_mover": slow,
                   "school": (schools.chosen("node_reach").school
                              if name in NODES else None)},
        ))
        # (d) stations and retrogrades — the sensitive part of a window.
        if tp.retrograde or name in ("Rahu", "Ketu"):
            facts.append(Fact(
                id=f"transit.{name.lower()}.station",
                kind="transit",
                statement=(
                    f"TRANSIT MOTION (today): {name} is retrograde"
                    + (" — the nodes are always so, which is their nature "
                       "rather than a condition of this moment."
                       if name in NODES else
                       ", so the ground it has already covered is being "
                       "gone over again. Classically a retrograde graha "
                       "revisits rather than advances; the house it "
                       "occupies and the houses it aspects are reworked, "
                       "not opened.")),
                value={"planet": name, "retrograde": True,
                       "always_retrograde": name in NODES,
                       "speed": round(tp.position.speed, 6),
                       "natal_house": tp.natal_house,
                       "aspects": houses},
            ))

    # --- transit-to-natal contacts ----------------------------------------
    # A separate fact per contact, so it has an id the answer can cite and
    # the validator can look for. The precedence lives IN the fact: a rule
    # that only exists in the system prompt is a rule the ledger cannot
    # defend.
    for c in contacts:
        facts.append(Fact(id=c["id"], kind="contact",
                          statement=_contact_statement(c), value=dict(c)))

    # --- doshas ------------------------------------------------------------
    for dosha in doshas_all(chart, when):
        facts.append(Fact(
            id=f"dosha.{_slug(dosha.name)}",
            kind="dosha",
            statement=(
                f"{dosha.name}: "
                + ("formed" if dosha.formed else "does not form")
                + (", and still stands after its cancellation checks."
                   if dosha.formed and dosha.active
                   else ", but stands cancelled." if dosha.formed
                   else ".")
                + f" {dosha.detail}"),
            value={"name": dosha.name, "formed": dosha.formed,
                   "active": dosha.active, "detail": dosha.detail,
                   "cancellations": list(dosha.cancellations),
                   # The library rules this dosha is read by. Mangal has
                   # two since C1; Kaal Sarpa and Sade Sati none yet.
                   "rule_ids": list(dosha.rule_ids)},
        ))

    # --- arudhas and the Upapada -------------------------------------------
    #
    # A12 is read for marriage, so where the co-lord school splits the two
    # readings BOTH are carried. A ledger that recorded only the live one
    # would let a reading assert the Upapada without the reader ever
    # learning that the other school puts it elsewhere.
    arudha_view = arudhas.describe(chart)
    both_arudhas = arudhas.both_schools(chart)
    contested = set(arudha_view["contested_houses"])
    for house in range(1, 13):
        sign_index = arudha_view["arudhas"][house - 1]
        sign = SIGNS[sign_index]
        occupants = [p for p in PLANETS
                     if chart.planets[p].sign_index == sign_index]
        split = (both_arudhas["single"][house - 1]
                 != both_arudhas["stronger"][house - 1])
        facts.append(Fact(
            id=f"arudha.a{house}",
            kind="arudha",
            statement=(
                f"A{house}, the arudha of the {ordinal(house)} house, "
                f"falls in {sign} — the {ordinal((sign_index - chart.lagna.sign_index) % 12 + 1)} "
                f"house from the lagna"
                + (f", with {_and_list(occupants)} in it." if occupants
                   else ", with no graha in it.")
                + (f" The two co-lord readings disagree here: "
                   f"{SIGNS[both_arudhas['single'][house - 1]]} under the "
                   f"sole classical lord, "
                   f"{SIGNS[both_arudhas['stronger'][house - 1]]} under the "
                   f"stronger co-lord." if split else "")
                + school_note("dual_lord")),
            value={"house": house, "sign": sign, "sign_index": sign_index,
                   "house_from_lagna":
                       (sign_index - chart.lagna.sign_index) % 12 + 1,
                   "occupants": occupants,
                   "lord": arudhas.SIGN_LORDS[sign_index],
                   "contested": house in contested,
                   "schools_differ": split,
                   "parashari": SIGNS[both_arudhas["single"][house - 1]],
                   "jaimini": SIGNS[both_arudhas["stronger"][house - 1]]},
        ))
    # The Upapada's OWN split, as `arudha.a12` carries it. `schools_agree`
    # below is a statement about the whole chart — on the reference fixture
    # it is False while A12 itself agrees — and the interim marriage reading
    # had to reach into `arudha.a12` to learn whether the Upapada moves. A
    # predicate reads one fact; this fact now answers for itself.
    ul_split = (both_arudhas["single"][11] != both_arudhas["stronger"][11])
    ul_pair = {"parashari": SIGNS[both_arudhas["single"][11]],
               "jaimini": SIGNS[both_arudhas["stronger"][11]]}
    facts.append(Fact(
        id="arudha.upapada",
        kind="arudha",
        statement=(
            f"The Upapada Lagna — the arudha of the 12th — is "
            f"{arudha_view['upapada_sign']}, the "
            f"{ordinal(arudha_view['upapada_house'])} house from the lagna, "
            f"ruled by {arudha_view['upapada_lord']}"
            + (f", with {_and_list(arudha_view['upapada_occupants'])} on it."
               if arudha_view["upapada_occupants"] else ", with no graha on it.")
            + " It is read for marriage and for the spouse."
            + (f" The two co-lord readings disagree here: "
               f"{ul_pair['parashari']} under the sole classical lord, "
               f"{ul_pair['jaimini']} under the stronger co-lord."
               if ul_split else "")
            + ("" if arudha_view["schools_agree"] else
               " The two co-lord readings do not agree across this chart.")
            + school_note("dual_lord")),
        value={"sign": arudha_view["upapada_sign"],
               "sign_index": arudha_view["upapada_sign_index"],
               "house_from_lagna": arudha_view["upapada_house"],
               "lord": arudha_view["upapada_lord"],
               "occupants": arudha_view["upapada_occupants"],
               "contested": arudha_view["upapada_contested"],
               "schools_agree": arudha_view["schools_agree"],
               "schools_differ": ul_split, **ul_pair},
    ))
    # The 2nd from the Upapada — read for the durability of the marriage
    # (rule.arudha.second_from_upapada). The rule was in the library with no
    # fact to fire on; this is the fact. Counted from the Upapada's sign, not
    # from the lagna, which is the whole point of bhavat bhavam.
    ul_index = arudha_view["upapada_sign_index"]
    second_index = (ul_index + 1) % 12
    second_lord = sign_lord(second_index)
    second_lord_pos = chart.planets[second_lord]
    second_occupants = [p for p in PLANETS
                        if chart.planets[p].sign_index == second_index]
    second_lord_grade = (dignity_grade(chart, second_lord)
                         or dignity(chart, second_lord))
    facts.append(Fact(
        id="arudha.upapada_2nd",
        kind="arudha",
        statement=(
            f"The 2nd from the Upapada is {SIGNS[second_index]}, the "
            f"{ordinal((second_index - chart.lagna.sign_index) % 12 + 1)} "
            f"house from the lagna"
            + (f", with {_and_list(second_occupants)} in it" if second_occupants
               else ", with no graha in it")
            + f"; its lord {second_lord} sits in {second_lord_pos.sign} in "
            f"the {ordinal(second_lord_pos.house)} house"
            + (f" — dignity: {second_lord_grade}." if second_lord_grade
               and second_lord_grade != "neutral" else ".")
            + " It is read for the durability of the marriage."
            + school_note("dual_lord")),
        value={"sign": SIGNS[second_index], "sign_index": second_index,
               "house_from_lagna":
                   (second_index - chart.lagna.sign_index) % 12 + 1,
               "occupants": second_occupants,
               "lord": second_lord, "lord_sign": second_lord_pos.sign,
               "lord_house": second_lord_pos.house,
               "lord_dignity": second_lord_grade or None,
               "upapada_sign": arudha_view["upapada_sign"],
               "rule_ids": ["rule.arudha.second_from_upapada"]},
    ))

    # --- chara karakas ------------------------------------------------------
    # Each office carries the graha's CONDITION as well as its seat — dignity,
    # what aspects it, combustion, retrogression — because rule.karaka.
    # darakaraka reads "its sign, its house, its dignity and what aspects
    # it", and a predicate that had to join two facts to evaluate one rule
    # would cite two and read as though it had read one.
    aspect_table = natal_aspect_table(chart)
    for karaka in karakas.karakas(chart):
        position = chart.planets[karaka.planet]
        grade = (dignity_grade(chart, karaka.planet)
                 or dignity(chart, karaka.planet))
        onto = [a.aspecting for a in aspect_table
                if a.aspected == karaka.planet]
        burnt = _combustion(chart, karaka.planet)
        facts.append(Fact(
            id=f"karaka.chara.{karaka.office.lower()}",
            kind="karaka",
            statement=(
                f"{karaka.planet} is the {karaka.office} ({karaka.abbr}), "
                f"signifying {karaka.signifies}. It sits in "
                f"{position.sign} at {position.degree_in_sign:.2f}°, in the "
                f"{ordinal(position.house)} house"
                + (f", dignity {grade}" if grade and grade != "neutral" else "")
                + (", retrograde" if position.retrograde else "")
                + (", combust" if burnt["combust"] else "")
                + (", aspected by " + _and_list(onto) if onto
                   else ", unaspected")
                + (" — ranked by its degree counted BACKWARDS, since Rahu "
                   "travels that way." if karaka.reversed_for_rahu else ".")
                + school_note("karaka_count")),
            value={"office": karaka.office, "abbr": karaka.abbr,
                   "planet": karaka.planet, "sign": position.sign,
                   "house": position.house,
                   "degree_in_sign": round(karaka.degree_in_sign, 4),
                   "ranked_by": round(karaka.ranked_by, 4),
                   "signifies": karaka.signifies,
                   "dignity": grade or None, "aspected_by": onto,
                   "retrograde": position.retrograde, **burnt},
        ))
    # Both schemes side by side. The seven-karaka count and the eight can
    # give different grahas for the same office — the spouse's most of all,
    # since Rahu's admission moves every office below it — and a reading
    # that names the Darakaraka must be able to say whether the other school
    # names the same one. One fact, both answers, which is in force.
    schemes = karakas.both_schemes(chart)
    differ_on = sorted(office for office in schemes["seven"]
                       if schemes["seven"][office] != schemes["eight"].get(office))
    dk_pair = {"seven": schemes["seven"]["Darakaraka"],
               "eight": schemes["eight"]["Darakaraka"]}
    facts.append(Fact(
        id="karaka.chara.schemes",
        kind="karaka",
        statement=(
            f"Under the seven-karaka scheme the Darakaraka is "
            f"{dk_pair['seven']}; under the eight-karaka scheme it is "
            f"{dk_pair['eight']}"
            + (" — the two schemes agree on the spouse's significator."
               if dk_pair["seven"] == dk_pair["eight"] else
               " — the two schemes DISAGREE on the spouse's significator.")
            + (" Offices that move between the schemes: "
               + _and_list(differ_on) + "." if differ_on
               else " No office moves between the schemes on this chart.")
            + school_note("karaka_count")),
        value={"seven": schemes["seven"], "eight": schemes["eight"],
               "differ_on": differ_on, "darakaraka": dk_pair,
               "in_force": karakas.scheme(),
               "schemes_differ_on_spouse":
                   dk_pair["seven"] != dk_pair["eight"]},
    ))
    # The spouse's natural significator. Venus for the wife in a man's
    # chart, Jupiter for the husband in a woman's (rule.karaka.by_sex); the
    # chart does not yet carry its owner's sex, so this reads under the
    # stated convention (rule.karaka.by_sex_unset) — both, Venus first — and
    # says so. Component 8 makes it switch.
    facts.append(Fact(
        id="karaka.spouse",
        kind="karaka",
        statement=(
            "The spouse's natural significator is read as both Venus and "
            "Jupiter, Venus first: the chart's owner has not said, and "
            "Sidera's convention is to read both."),
        value={"primary": "Venus", "secondary": "Jupiter", "basis": "unset",
               "rule_ids": ["rule.karaka.by_sex_unset"]},
    ))
    karakamsa = karakas.karakamsa(chart)
    facts.append(Fact(
        id="karaka.karakamsa",
        kind="karaka",
        statement=(
            f"The Karakamsa is {karakamsa['sign']} — the navamsa sign the "
            f"Atmakaraka ({karakamsa['planet']}) occupies, the "
            f"{ordinal(karakamsa['house_from_d9_lagna'])} house from the D9 "
            f"lagna ({karakamsa['d9_lagna_sign']})."
            + school_note("karaka_count")),
        value=karakamsa,
    ))

    # --- vimsopaka bala -----------------------------------------------------
    vimsopaka_view = vimsopaka.describe(chart)
    facts.append(Fact(
        id="vimsopaka.group",
        kind="vimsopaka",
        statement=(
            f"Vimsopaka bala here is weighed across the "
            f"{vimsopaka_view['group_label']}: "
            + ", ".join(vimsopaka_view["charts"]) + ". "
            + vimsopaka_view["nodes_excluded"]
            + school_note("vimsopaka_group")),
        value={"group": vimsopaka_view["group"],
               "charts": vimsopaka_view["charts"],
               "strongest": vimsopaka_view["strongest"],
               "thinnest": vimsopaka_view["thinnest"]},
    ))
    for planet in vimsopaka.BODIES:
        value = vimsopaka_view["scores"][planet]
        facts.append(Fact(
            id=f"vimsopaka.{planet.lower()}",
            kind="vimsopaka",
            statement=(
                f"{planet} scores {value:.2f} of 20 on vimsopaka bala across "
                f"the {vimsopaka_view['group_label']} — "
                f"{vimsopaka_view['bands'][planet]}."
                + school_note("vimsopaka_group", "dual_lord")),
            value={"planet": planet, "score": value,
                   "band": vimsopaka_view["bands"][planet],
                   "group": vimsopaka_view["group"],
                   "working": vimsopaka.working(chart, planet)},
        ))

    # --- avasthas -----------------------------------------------------------
    for row in avasthas.describe(chart)["avasthas"]:
        facts.append(Fact(
            id=f"avastha.{row['planet'].lower()}",
            kind="avastha",
            statement=(
                f"{row['planet']} is {row['baladi_name']} by degree — "
                f"{row['baladi_sense']} — and {row['jagradadi_name']} by "
                f"dignity — {row['jagradadi_sense']}."
                + (" The two point different ways, which is itself the "
                   "reading." if row["at_odds"] else "")),
            value=row,
        ))

    # --- the running pratyantardasha ---------------------------------------
    #
    # ONE fact, not 729. The ledger is what the agent reads, and the whole
    # third level would swamp a payload that carries 189 facts in total.
    # The full tree stays queryable in `dashas`.
    running = timeline.at_depth(when)
    if running is not None:
        maha, antara, pratyantara = running
        facts.append(Fact(
            id="dasha.pratyantar",
            kind="dasha",
            statement=(
                f"Within {maha.lord}/{antara.lord}, the running "
                f"pratyantardasha is {pratyantara.lord}, from "
                f"{pratyantara.start:%d %b %Y} to "
                f"{pratyantara.end:%d %b %Y}."),
            value={"maha": maha.lord, "antara": antara.lord,
                   "pratyantara": pratyantara.lord,
                   "start": pratyantara.start.isoformat(),
                   "end": pratyantara.end.isoformat()},
        ))

    return facts


def active_rules(chart: Chart, when: datetime) -> list:
    """The classical rules that bear on this chart's active facts.

    Interpretation is required of the agent, not improvised by it — so the
    rules it may read through travel with the facts, and their ids are
    checkable exactly as fact ids are.
    """
    from rulelib import rules_for
    timeline = vimshottari(chart)
    current = timeline.at(when)
    lords = [md.lord for md in ([current[0]] if current else [])]
    lords += [current[1].lord] if current else []
    snapshot = transit_snapshot(chart, when)
    houses = sorted({p.natal_house for p in snapshot.planets.values()}
                    | {chart.planets[l].house for l in lords
                       if l in chart.planets})
    contacts = {c["transit"] for c
                in transit_contacts_summary(chart, when, snapshot)}
    return rules_for(dasha_lords=lords,
                     transit_planets=list(PLANETS),
                     houses=houses,
                     vargas=("D9", "D10"),
                     contacts=sorted(contacts))


def domain_brief(chart: Chart, question: str) -> dict | None:
    """The checklist for the domain a question is about, with its fact ids.

    The agent used to be told "read the chart" and given 140 facts. That
    produced an answer built on whichever fact it happened to look at
    first. This hands it the named steps AND the exact ids each step is
    answerable from, so a skipped step is visible rather than plausible.
    """
    from domains import CHECKLIST, detect
    domain = detect(question)
    if domain is None:
        return None
    lords = house_lords(chart)
    varga = domain.varga.lower()
    # The spouse's own facts, marriage only — the Dārakāraka, the two
    # karaka schemes, the spouse karaka, the Upapada and its 2nd, and Mangal
    # dosha — filed under the step each belongs to, so a reading that
    # cites them is credited with the step and one that skips them is seen
    # to. `vimsopaka.<lord>` for every domain-house lord that has a score
    # (the nodes take none), and the main-house lord's own varga placement.
    spouse_natal = (["arudha.upapada", "arudha.upapada_2nd",
                     "dosha.mangal-dosha"]
                    if domain.id == "marriage" else [])
    spouse_karaka = (["karaka.chara.darakaraka", "karaka.chara.schemes",
                      "karaka.spouse"]
                     if domain.id == "marriage" else [])
    scored_lords = sorted({lords[h] for h in domain.houses}
                          - {"Rahu", "Ketu"})
    return {
        **domain.as_dict(),
        "checklist": [{"step": name, "do": what}
                      for name, what in CHECKLIST],
        "fact_ids": {
            "NATAL": ([f"house.{h}" for h in domain.houses]
                      + [f"natal.{h}L" for h in domain.houses]
                      + sorted({f"planet.{lords[h].lower()}"
                                for h in domain.houses})
                      + spouse_natal),
            "KARAKA": ([f"karaka.{k.lower()}" for k in domain.karakas]
                       + [f"avastha.{k.lower()}" for k in domain.karakas
                          if k not in ("Rahu", "Ketu")]
                       + spouse_karaka),
            "VARGA": ([f"varga.{varga}.lagna"]
                      + [f"{varga}.{ordinal(h)}" for h in domain.houses]
                      + [f"varga.{varga}.{lords[domain.main_house].lower()}"]
                      + [f"vimsopaka.{lord.lower()}" for lord in scored_lords]),
            "DASHA": ["dasha.current"] + [f"dasha.md.{p.lower()}"
                                          for p in PLANETS],
            "TRANSIT": ([f"transit.{p.lower()}" for p in
                         ("Saturn", "Jupiter", "Rahu", "Ketu")]
                        + [f"transit.{p.lower()}.aspects" for p in
                           ("Saturn", "Jupiter", "Rahu", "Ketu")]),
        },
    }


#: Divisions whose FULL detail travels to the agent by default. The ledger
#: holds all nine; the prompt does not need all nine. D9 tests every promise
#: and D10 is the career division, so those two are always in; a domain adds
#: its own if it names another.
#:
#: WHY THIS SLICE EXISTS. Casting seven more divisions took the ledger from
#: 130 facts to 330, and every one of them would have gone into every prompt
#: — tripling the payload to answer a question about marriage with the
#: Ṣaṣṭyāṃśa positions of nine grahas. The LAGNA of every division still
#: travels, because the agent must know a division exists and can be asked
#: for; the per-graha and per-house detail of an unasked-for division does
#: not.
_PROMPT_VARGAS = ("D9", "D10")


def _varga_in_prompt(fact_id: str, wanted: frozenset[str]) -> bool:
    """Does this varga fact belong in the agent's payload?"""
    if fact_id.endswith(".lagna"):
        return True
    for code in wanted:
        low = code.lower()
        if fact_id.startswith(f"varga.{low}.") or fact_id.startswith(f"{low}."):
            return True
    return False


#: Arudhas that travel in the agent payload. A1-A11 stay in the LEDGER —
#: the validator can check any claim about them — but they are a systematic
#: table of twelve undifferentiated rows that almost no question touches,
#: and eleven of them would be weight without reach. A12 is different: the
#: Upapada is read for marriage and carries an actual reading.
_PROMPT_ARUDHAS = frozenset({"arudha.upapada", "arudha.upapada_2nd"})


def _in_prompt(fact: Fact) -> bool:
    """Whether a fact travels to the agent, beyond the varga slice.

    THE RULE THIS ANSWERS TO, set when the vargas were sliced: a smaller
    prompt must not become a smaller truth. Everything excluded here stays
    in the ledger, and `validate_payload` checks answers against the LEDGER,
    not against the payload — so leaving a fact out costs the model reach,
    never the reader accuracy.
    """
    if fact.kind == "arudha":
        return fact.id in _PROMPT_ARUDHAS
    return True


def facts_payload(chart: Chart, when: datetime,
                  question: str = "") -> dict:
    """The ledger as the JSON the agent is given. Sorted, so it caches."""
    facts = build_facts(chart, when)
    brief_for_slice = domain_brief(chart, question)
    wanted = set(_PROMPT_VARGAS)
    if brief_for_slice:
        wanted.add(brief_for_slice["varga"])
    wanted = frozenset(wanted)
    facts = [f for f in facts
             if f.kind != "varga" or _varga_in_prompt(f.id, wanted)]
    facts = [f for f in facts if _in_prompt(f)]
    payload = {
        "as_of": when.date().isoformat(),
        "system": "sidereal, Lahiri ayanamsa, Whole Sign houses",
        "facts": [f.as_dict() for f in facts],
        "rules": [r.as_dict() for r in active_rules(chart, when)],
    }
    if brief_for_slice:
        payload["domain"] = brief_for_slice
    return payload


def fact_index(chart: Chart, when: datetime) -> dict[str, Fact]:
    return {f.id: f for f in build_facts(chart, when)}
