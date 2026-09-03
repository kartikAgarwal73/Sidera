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
from transits import natal_aspect_table, transit_snapshot
from vargas import dasamsa, navamsa
from yogas import detect_all, dignity_grade, house_lords


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
                + (f" — dignity: {grade}." if grade else ".")),
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

    # --- natal aspects -----------------------------------------------------
    for a in natal_aspect_table(chart):
        facts.append(Fact(
            id=f"aspect.{a.aspecting.lower()}-{a.aspected.lower()}",
            kind="aspect",
            statement=(f"{a.aspecting} casts its {ordinal(a.offset)} "
                       f"drishti onto {a.aspected}."),
            value={"from": a.aspecting, "to": a.aspected,
                   "offset": a.offset},
        ))

    # --- divisional charts -------------------------------------------------
    for label, varga in (("d9", navamsa(chart)), ("d10", dasamsa(chart))):
        facts.append(Fact(
            id=f"varga.{label}.lagna",
            kind="varga",
            statement=(f"The {label.upper()} lagna is {varga.lagna_sign}."),
            value={"varga": label.upper(), "lagna": varga.lagna_sign},
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
    snapshot = transit_snapshot(chart, when)
    for card in transit_weather(chart, snapshot):
        facts.append(Fact(
            id=f"transit.{card['planet'].lower()}",
            kind="transit",
            statement=(
                f"Transiting {card['planet']} is in {card['sign']}, moving "
                f"through the natal {ordinal(card['natal_house'])} house, "
                f"{ordinal(card['from_moon'])} from the natal Moon, until "
                f"{card['until']}. {card['note']}"),
            value={"planet": card["planet"], "sign": card["sign"],
                   "natal_house": card["natal_house"],
                   "from_moon": card["from_moon"], "until": card["until"],
                   "demanding": card["demanding"]},
        ))

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


def facts_payload(chart: Chart, when: datetime) -> dict:
    """The ledger as the JSON the agent is given. Sorted, so it caches."""
    facts = build_facts(chart, when)
    return {
        "as_of": when.date().isoformat(),
        "system": "sidereal, Lahiri ayanamsa, Whole Sign houses",
        "facts": [f.as_dict() for f in facts],
    }


def fact_index(chart: Chart, when: datetime) -> dict[str, Fact]:
    return {f.id: f for f in build_facts(chart, when)}
