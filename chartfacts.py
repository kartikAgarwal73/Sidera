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
from engine import PLANETS, Chart
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
from yogas import (detect_all, dignity, dignity_grade, house_lords,
                   houses_owned_by, sign_lord)


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
        facts.append(Fact(
            id=f"planet.{name.lower()}",
            kind="planet",
            statement=(
                f"{name} is in {p.sign} at {p.dms}{retro}, in the "
                f"{ordinal(p.house)} house, in the nakshatra {nak.name} "
                f"pada {nak.pada} (lord {nak.lord})"
                + (f" — dignity: {grade}." if grade else ".")
                + (school_note("node_position") if name in NODES else "")),
            value={"planet": name, "sign": p.sign, "house": p.house,
                   "degree": round(p.degree_in_sign, 4),
                   "retrograde": p.retrograde, "nakshatra": nak.name,
                   "pada": nak.pada, "nakshatra_lord": nak.lord,
                   "dignity": grade or None},
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
        facts.append(Fact(
            id=f"karaka.{name.lower()}",
            kind="karaka",
            statement=(
                f"As a natural significator, {name} carries "
                f"{KARAKATVAS[name]}. In this chart it is in {p.sign}, "
                f"{ordinal(p.house)} house"
                + (f", dignity {grade}" if grade else "")
                + (", retrograde" if p.retrograde else "")
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
                   "benefic": name in NATURAL_BENEFICS},
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
    _VARGA_OF = {"d9": ("Navamsa", "inner strength, marriage and the "
                                   "durability of a natal promise"),
                 "d10": ("Dasamsa", "work, standing and the field of "
                                    "action")}
    for label, varga in (("d9", navamsa(chart)), ("d10", dasamsa(chart))):
        vname, vfor = _VARGA_OF[label]
        facts.append(Fact(
            id=f"varga.{label}.lagna",
            kind="varga",
            statement=(f"The {label.upper()} ({vname}) lagna is "
                       f"{varga.lagna_sign}. This varga is read for {vfor}."),
            value={"varga": label.upper(), "name": vname,
                   "lagna": varga.lagna_sign, "read_for": vfor},
        ))
        for name in PLANETS:
            vp = varga.planets[name]
            facts.append(Fact(
                id=f"varga.{label}.{name.lower()}",
                kind="varga",
                statement=(
                    f"In the {label.upper()} ({vname}), {name} is in "
                    f"{vp.sign}, in the {ordinal(vp.house)} house from the "
                    f"{label.upper()} lagna"
                    + (" — vargottama, the same sign it holds at birth."
                       if vp.vargottama else ".")
                    + " (Sign-level only: this build computes no degree "
                      "within a divisional sign.)"),
                value={"varga": label.upper(), "planet": name,
                       "sign": vp.sign, "house": vp.house,
                       "vargottama": vp.vargottama,
                       "degree": None},
            ))
        vargottama = [n for n, v in varga.planets.items() if v.vargottama]
        if label == "d9" and vargottama:
            facts.append(Fact(
                id="varga.d9.vargottama",
                kind="varga",
                statement=("Vargottama (same sign in D1 and D9): "
                           + ", ".join(vargottama) + "."),
                value={"planets": vargottama},
            ))

        # Step 3 asks what is IN the domain house of the divisional chart.
        # The per-planet varga facts held that, scattered across nine
        # entries the agent had to assemble itself — and did not. One fact
        # per divisional house, `d9.7th`, makes the step a single citation.
        from engine import SIGNS as _SIGNS
        vlagna = _SIGNS.index(varga.lagna_sign)
        for house in range(1, 13):
            sign = _SIGNS[(vlagna + house - 1) % 12]
            here = [n for n in PLANETS if varga.planets[n].house == house]
            lord = sign_lord(_SIGNS.index(sign))
            lord_in = varga.planets[lord].house
            facts.append(Fact(
                id=f"{label}.{ordinal(house)}",
                kind="varga",
                statement=(
                    f"In the {label.upper()}, the {ordinal(house)} house is "
                    f"{sign}, ruled by {lord} (which sits in the "
                    f"{ordinal(lord_in)} house of the {label.upper()})"
                    + (", occupied by " + _and_list(here) + "."
                       if here else ", with no graha in it.")
                    + " (Sign-level only: this build computes no degree "
                      "within a divisional sign, so there is no dignity by "
                      "degree here.)"),
                value={"varga": label.upper(), "house": house, "sign": sign,
                       "lord": lord, "lord_house": lord_in,
                       "occupants": here, "degree": None},
            ))

    # --- yogas -------------------------------------------------------------
    for yoga in detect_all(chart):
        facts.append(Fact(
            id=f"yoga.{_slug(yoga.name)}",
            kind="yoga",
            statement=f"{yoga.name}: {yoga.detail}",
            value={"name": yoga.name, "rule": yoga.rule,
                   "detail": yoga.detail, "planets": list(yoga.planets),
                   "notes": list(yoga.notes)},
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
                   "cancellations": list(dosha.cancellations)},
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
    return {
        **domain.as_dict(),
        "checklist": [{"step": name, "do": what}
                      for name, what in CHECKLIST],
        "fact_ids": {
            "NATAL": ([f"house.{h}" for h in domain.houses]
                      + [f"natal.{h}L" for h in domain.houses]
                      + sorted({f"planet.{lords[h].lower()}"
                                for h in domain.houses})),
            "KARAKA": [f"karaka.{k.lower()}" for k in domain.karakas],
            "VARGA": ([f"{varga}.lagna" if False else f"varga.{varga}.lagna"]
                      + [f"{varga}.{ordinal(h)}" for h in domain.houses]),
            "DASHA": ["dasha.current"] + [f"dasha.md.{p.lower()}"
                                          for p in PLANETS],
            "TRANSIT": ([f"transit.{p.lower()}" for p in
                         ("Saturn", "Jupiter", "Rahu", "Ketu")]
                        + [f"transit.{p.lower()}.aspects" for p in
                           ("Saturn", "Jupiter", "Rahu", "Ketu")]),
        },
    }


def facts_payload(chart: Chart, when: datetime,
                  question: str = "") -> dict:
    """The ledger as the JSON the agent is given. Sorted, so it caches."""
    facts = build_facts(chart, when)
    payload = {
        "as_of": when.date().isoformat(),
        "system": "sidereal, Lahiri ayanamsa, Whole Sign houses",
        "facts": [f.as_dict() for f in facts],
        "rules": [r.as_dict() for r in active_rules(chart, when)],
    }
    brief = domain_brief(chart, question)
    if brief:
        payload["domain"] = brief
    return payload


def fact_index(chart: Chart, when: datetime) -> dict[str, Fact]:
    return {f.id: f for f in build_facts(chart, when)}
