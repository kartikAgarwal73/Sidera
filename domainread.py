"""The deterministic domain reading — synthesis without a language model.

WHY THIS IS NOT THE AGENT
The dashboard's domain view leads with a synthesis: what supports this matter,
what strains it, what the running period emphasises. That is a reading, and
"no language model writes readings" is a standing property of this build — the
agent is optional, needs a key, and must never be load-bearing for the core
page.

So this composes the same three paragraphs from the same ledger facts the
agent's checklist cites, by rule, deterministically. The same chart on the
same day gets the same words forever. Where the agent IS configured it adds
the six-step reading on top; it does not replace this one.

WHAT IT WILL AND WILL NOT SAY
It reports CONDITION, never outcome. "The 7th lord is debilitated and Jupiter
aspects the house" is a condition; "you will marry late" is a prediction, and
this module cannot express one — there is no sentence template for it. Every
line carries the fact ids it was composed from, so the expander pattern works
the same way it does everywhere else in the app.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime

from domains import DOMAINS, Domain
from engine import Chart
from explain import ordinal
from rulelib import KARAKATVAS, NATURAL_BENEFICS

# Natural malefics — the other half of the benefic list, with the nodes.
NATURAL_MALEFICS = ("Sun", "Mars", "Saturn", "Rahu", "Ketu")

STRONG = ("exalted", "own sign", "moolatrikona")
WEAK = ("debilitated",)


@dataclass(frozen=True)
class Signal:
    """One computed reason, with the fact it came from.

    `brief` is the same reason in a handful of words, for the card teaser —
    written here rather than truncated from `text`, because a sentence cut
    at 60 characters reads like a bug.
    """

    kind: str            # support | strain | period | live
    text: str
    fact_ids: tuple[str, ...]
    rule_ids: tuple[str, ...] = ()
    brief: str = ""
    weight: int = 1      # the sharper the signal, the higher


@dataclass(frozen=True)
class DomainReading:
    domain: Domain
    teaser: str
    paragraphs: tuple[str, ...]
    signals: tuple[Signal, ...]
    confidence: str = "Interpretive"

    @property
    def supports(self):
        return [s for s in self.signals if s.kind == "support"]

    @property
    def strains(self):
        return [s for s in self.signals if s.kind == "strain"]

    @property
    def period(self):
        return [s for s in self.signals if s.kind in ("period", "live")]

    def as_dict(self) -> dict:
        return {
            "id": self.domain.id, "label": self.domain.label,
            "teaser": self.teaser, "paragraphs": list(self.paragraphs),
            "confidence": self.confidence,
            "signals": [{"kind": s.kind, "text": s.text,
                         "fact_ids": list(s.fact_ids),
                         "rule_ids": list(s.rule_ids)}
                        for s in self.signals],
        }


def _and(items) -> str:
    items = list(items)
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + " and " + items[-1]


def _matters(why: str) -> str:
    """`domain.why` reads "the house of X" — the appositive form is "X"."""
    for prefix in ("the house of ", "the 2nd from the 7th: "):
        if why.startswith(prefix):
            trimmed = why[len(prefix):]
            # "marriage, and of dealings with…" — the second "of" belonged
            # to the prefix that has just gone.
            return re.sub(r"^(.*?), and of ", r"\1, and ", trimmed)
    return why


def _dignity_phrase(dignity: str) -> str:
    """"own sign" needs a preposition; "exalted" does not."""
    if dignity in ("own sign", "moolatrikona"):
        return f"in its {dignity}"
    return dignity


def _dignity_of(fact) -> str:
    return (fact.value.get("lord_dignity") or fact.value.get("dignity")
            or "") or ""


def read(chart: Chart, when: datetime, domain_id: str,
         facts: dict | None = None) -> DomainReading:
    """One domain's condition, composed from the ledger.

    `facts` is the id→Fact index; passed in by the caller so a dashboard
    render builds the ledger once for all five domains rather than five
    times.
    """
    from chartfacts import build_facts
    if facts is None:
        facts = {f.id: f for f in build_facts(chart, when)}
    domain = DOMAINS[domain_id]
    signals: list[Signal] = []

    # --- step 1, natal: each house through its lord and what falls on it ---
    for house in domain.houses:
        lord_fact = facts[f"natal.{house}L"]
        v = lord_fact.value
        ids = (f"natal.{house}L", f"house.{house}")
        rule = (f"rule.house.{house}", "rule.dasha.lordship")
        dignity = _dignity_of(lord_fact).split(" (")[0]
        matters = _matters(domain.why[house])
        main = house == domain.main_house
        where = f"the {ordinal(house)} house — {matters} —"
        if any(x in dignity for x in STRONG):
            signals.append(Signal(
                "support",
                f"{where} has its lord {v['lord']} "
                f"{_dignity_phrase(dignity)}, so those "
                f"matters arrive with less friction",
                ids, rule,
                brief=f"a strong {ordinal(house)} lord",
                weight=3 if main else 2))
        elif any(x in dignity for x in WEAK):
            signals.append(Signal(
                "strain",
                f"{where} has its lord {v['lord']} "
                f"{_dignity_phrase(dignity)}, so the same "
                f"matters ask more effort of you than they would otherwise",
                ids, rule,
                brief=f"a {dignity} {ordinal(house)} lord",
                weight=3 if main else 2))
        benefics = [p for p in v["aspected_by"] if p in NATURAL_BENEFICS]
        malefics = [p for p in v["aspected_by"] if p in NATURAL_MALEFICS]
        if benefics:
            verb = "casts" if len(benefics) == 1 else "cast"
            signals.append(Signal(
                "support",
                f"{_and(benefics)} {verb} drishti onto the "
                f"{ordinal(house)} house, which the tradition reads as "
                f"protection over {matters}",
                ids, ("rule.transit.aspect", f"rule.house.{house}"),
                brief=(f"{_and(benefics)} "
                       f"{'protects' if len(benefics) == 1 else 'protect'} "
                       f"the {ordinal(house)}"),
                weight=2 if main else 1))
        if malefics and main:
            verb = "aspects" if len(malefics) == 1 else "aspect"
            signals.append(Signal(
                "strain",
                f"{_and(malefics)} {verb} the {ordinal(house)} house too, "
                f"which classically presses on the matter rather than "
                f"easing it",
                ids, ("rule.transit.aspect", f"rule.house.{house}"),
                brief=(f"{_and(malefics)} "
                       f"{'presses' if len(malefics) == 1 else 'press'} on "
                       f"the {ordinal(house)}"),
                weight=2))

    # --- step 2, karaka --------------------------------------------------
    for karaka in domain.karakas[:2]:
        kf = facts[f"karaka.{karaka.lower()}"]
        v = kf.value
        dignity = _dignity_of(kf)
        ids = (f"karaka.{karaka.lower()}",)
        rule = ("rule.graha.karakatva",)
        where = (f"{karaka}, which naturally signifies "
                 f"{KARAKATVAS[karaka].split(',')[0]} here, sits in your "
                 f"{ordinal(v['house'])} house")
        first = karaka == domain.karakas[0]
        if any(x in dignity for x in STRONG):
            signals.append(Signal(
                "support",
                f"{where} and is {_dignity_phrase(dignity.split(' (')[0])}",
                ids, rule, brief=f"{karaka} strong", weight=3 if first else 1))
        elif any(x in dignity for x in WEAK):
            signals.append(Signal(
                "strain",
                f"{where} but is {_dignity_phrase(dignity.split(' (')[0])}",
                ids, rule, brief=f"{karaka} debilitated",
                weight=3 if first else 1))
        elif v["house"] in (6, 8, 12):
            signals.append(Signal(
                "strain",
                f"{where} — one of the three houses the tradition reads as "
                f"hidden or costly, so its gifts arrive indirectly",
                ids, rule + (f"rule.house.{v['house']}",),
                brief=f"{karaka} tucked in the {ordinal(v['house'])}",
                weight=2 if first else 1))
        else:
            signals.append(Signal("support", where, ids, rule,
                                  brief=f"{karaka} soundly placed",
                                  weight=1))

    # --- step 3, varga: does the promise carry? ---------------------------
    varga = domain.varga.lower()
    vf = facts[f"{varga}.{ordinal(domain.main_house)}"]
    here = vf.value["occupants"]
    signals.append(Signal(
        "support" if here else "strain",
        (f"in the {domain.varga}, the chart read for {domain.varga_for}, "
         f"your {ordinal(domain.main_house)} house is {vf.value['sign']}"
         + (f" and holds {_and(here)} — the birth chart's promise is "
            f"repeated there" if here else
            " and stands empty, so the promise rests on the birth chart "
            "alone rather than being confirmed twice")),
        (f"{varga}.{ordinal(domain.main_house)}", f"varga.{varga}.lagna"),
        ("rule.varga.confirms", "rule.varga.purpose"),
        brief=(f"the {domain.varga} repeats it" if here
               else f"the {domain.varga} does not confirm it"),
        weight=3))

    # --- step 4, dasha: is this domain what the period is about? ----------
    current = facts.get("dasha.current")
    if current:
        cv = current.value
        for role, lord in (("mahadasha", cv["mahadasha"]),
                           ("antardasha", cv["antardasha"])):
            owns = facts[f"karaka.{lord.lower()}"].value["rules"]
            sits = facts[f"planet.{lord.lower()}"].value["house"]
            touches = sorted(set(owns) & set(domain.houses))
            if touches or sits in domain.houses:
                reason = []
                if touches:
                    reason.append("rules your "
                                  + _and([ordinal(h) for h in touches]))
                if sits in domain.houses:
                    reason.append(f"sits in your {ordinal(sits)}")
                signals.append(Signal(
                    "period",
                    f"the running {role} lord is {lord}, which "
                    + _and(reason) + " — so this is a stretch in which the "
                    "matter is actively in play",
                    ("dasha.current", f"karaka.{lord.lower()}",
                     f"planet.{lord.lower()}"),
                    ("rule.dasha.lordship", "rule.dasha.placement"),
                    brief=f"the {lord} {role} touches it",
                    weight=3 if role == "mahadasha" else 2))

    # --- step 5, transits: occupancy AND drishti, with dates --------------
    for planet in ("Saturn", "Jupiter", "Rahu", "Ketu"):
        af = facts[f"transit.{planet.lower()}.aspects"]
        v = af.value
        occupied = v["natal_house"] in domain.houses
        aspected = sorted(set(v["aspects"]) & set(domain.houses))
        if not occupied and not aspected:
            continue
        how = []
        if occupied:
            how.append(f"sitting in your {ordinal(v['natal_house'])}")
        if aspected:
            how.append("aspecting your "
                       + _and([ordinal(h) for h in aspected]))
        until = f" until {v['until']}" if v["until"] else ""
        signals.append(Signal(
            "live",
            f"transiting {planet} is {_and(how)}{until}",
            (f"transit.{planet.lower()}.aspects",
             f"transit.{planet.lower()}"),
            ("rule.transit.house", "rule.transit.aspect",
             f"rule.transit.{planet.lower()}", "rule.transit.window"),
            brief=(f"{planet} on it{until}" if occupied
                   else f"{planet} aspecting it{until}"),
            weight=2 if occupied else 1))

    return DomainReading(domain=domain,
                         teaser=_teaser(domain, signals),
                         paragraphs=_paragraphs(domain, signals),
                         signals=tuple(signals))


# How the balance is named. Weighted, so a debilitated lord of the MAIN
# house counts for more than a benefic aspect on a supporting one — which is
# how an astrologer would weigh them, and a bare count would not.
def _balance(supports, strains) -> str:
    up = sum(s.weight for s in supports)
    down = sum(s.weight for s in strains)
    if up >= down * 2 and up:
        return "Well supported"
    if down >= up * 2 and down:
        return "Asks real work"
    return "Mixed"


def _teaser(domain: Domain, signals: list[Signal]) -> str:
    """The one line a card carries. Condition, never prediction.

    A count ("4 supporting · 4 straining") is honest and tells the reader
    nothing they can act on. This names the balance, then the single
    sharpest reason on each side, then whether the chart has it live.
    """
    supports = [s for s in signals if s.kind == "support"]
    strains = [s for s in signals if s.kind == "strain"]
    live = [s for s in signals if s.kind in ("period", "live")]
    if not signals:
        return "Nothing in this chart bears strongly either way."

    def sharpest(items):
        ranked = sorted((s for s in items if s.brief),
                        key=lambda s: -s.weight)
        return ranked[0].brief if ranked else ""

    reasons = [r for r in (sharpest(supports), sharpest(strains)) if r]
    line = _balance(supports, strains)
    if reasons:
        line += " — " + _and(reasons)
    if live:
        top = sharpest(live)
        line += f". Live now: {top}." if top else ". Live right now."
    else:
        line += ". Quiet at the moment."
    return line


def _paragraphs(domain: Domain, signals: list[Signal]) -> tuple[str, ...]:
    """Two or three short paragraphs. Supports, strains, what is live."""
    def sentence(items):
        return "; ".join(s.text for s in items)

    out = []
    supports = [s for s in signals if s.kind == "support"]
    strains = [s for s in signals if s.kind == "strain"]
    live = [s for s in signals if s.kind in ("period", "live")]

    if supports:
        out.append(f"What supports {domain.label} here: "
                   + sentence(supports) + ".")
    else:
        out.append(f"Nothing in the houses read for {domain.label} stands "
                   "out as strengthening it, which is a plain reading of "
                   "the chart rather than a bad sign — most charts are "
                   "mixed.")
    if strains:
        out.append("What asks more of you: " + sentence(strains) + ".")
    else:
        out.append("Nothing here reads as an obstruction to it.")
    if live:
        out.append("What is live right now: " + sentence(live)
                   + ". A transit is a season with an end date, not a "
                     "verdict.")
    return tuple(out)


def read_all(chart: Chart, when: datetime) -> list[DomainReading]:
    """Every domain, from one build of the ledger."""
    from chartfacts import build_facts
    facts = {f.id: f for f in build_facts(chart, when)}
    return [read(chart, when, did, facts) for did in DOMAINS]
