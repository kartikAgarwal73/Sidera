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

import voice
from domains import DOMAINS, Domain
from engine import Chart
from explain import ordinal
from rulelib import KARAKATVAS, NATURAL_BENEFICS

# Natural malefics — the other half of the benefic list, with the nodes.
NATURAL_MALEFICS = ("Sun", "Mars", "Saturn", "Rahu", "Ketu")

STRONG = ("exalted", "own sign", "moolatrikona")
WEAK = ("debilitated",)


# --- the plain register -----------------------------------------------------
# The top layer is read by someone who has never met this system, so it uses
# no Sanskrit and no house numbers (voice.py holds the rule and the test).
# Everything technical still exists — one tap down, in the expanders, where a
# term can be glossed and cited. This is a translation, not a deletion.

# What the domain IS, in a stranger's words. The domain labels are accurate
# and unusable here: "constitution, energy and the body's routines" is not
# how anyone opens a sentence about their health.
SUBJECT = {
    "marriage": "Marriage",
    "career": "Work and money",
    "vitality": "Your health and energy",
    "home": "Home and family",
    "learning": "Study and creative work",
}

# The plain names of the nine — ONE table, kept in voice.py with the
# doctrine rather than copied here. See voice.PLAIN_PLANET for why.
PLAIN_PLANET = voice.PLAIN_PLANET


def _year(iso: str | None) -> str:
    """'2027-02-08T…' → 'Feb 2027'. A window the ledger produced, never one
    this module invented."""
    if not iso:
        return "its end"
    try:
        return datetime.fromisoformat(iso).strftime("%b %Y")
    except ValueError:
        return "its end"


def _planet(name: str) -> str:
    return PLAIN_PLANET.get(name, name)


def _planets(names) -> str:
    return _and([_planet(n) for n in names])


@dataclass(frozen=True)
class Signal:
    """One computed reason, with the fact it came from.

    Three registers of the same thing, written rather than truncated — a
    sentence cut at 60 characters reads like a bug:

      `text`  the full technical statement, for the expander. Sanskrit and
              house numbers belong here.
      `brief` a handful of words, still technical.
      `plain` the same reason with no Sanskrit and no house number, for the
              verdict and the visible synthesis. Empty means "this one has no
              plain form" — it stays in the expander and out of the top layer,
              which is the right outcome for a supporting-house detail nobody
              needs in the first breath.
    """

    kind: str            # support | strain | period | live
    text: str
    fact_ids: tuple[str, ...]
    rule_ids: tuple[str, ...] = ()
    brief: str = ""
    plain: str = ""
    weight: int = 1      # the sharper the signal, the higher


@dataclass(frozen=True)
class DomainReading:
    domain: Domain
    verdict: str
    teaser: str
    paragraphs: tuple[str, ...]
    caveat: str
    signals: tuple[Signal, ...]
    confidence: str = "Interpretive"

    @property
    def visible(self) -> str:
        """Every word shown before any expander is opened — what the budget
        in voice.SYNTHESIS_WORDS is actually a budget for."""
        return " ".join(list(self.paragraphs) + [self.caveat])

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
            "verdict": self.verdict,
            "teaser": self.teaser, "paragraphs": list(self.paragraphs),
            "caveat": self.caveat,
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


# The same four conditions with the Sanskrit taken out, for the top layer.
# "moolatrikona" is precise and it is exactly the kind of word the plain
# register exists to keep out of a first sentence.
PLAIN_DIGNITY = {
    "exalted": "exalted",
    "own sign": "in its own sign",
    "moolatrikona": "in its best sign",
    "debilitated": "at its weakest",
    "neutral": "neutrally placed",
}


def _plain_dignity(dignity: str) -> str:
    return PLAIN_DIGNITY.get(dignity.split(" (")[0].strip(),
                             dignity.split(" (")[0].strip())


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
                # Only the MAIN house earns a place in the first breath. A
                # strong lord of a supporting house is real and is in the
                # expander; leading with it would bury the actual subject.
                plain=(f"{_planet(v['lord'])} rules it and sits "
                       f"{_plain_dignity(dignity)}" if main else ""),
                weight=3 if main else 2))
        elif any(x in dignity for x in WEAK):
            signals.append(Signal(
                "strain",
                f"{where} has its lord {v['lord']} "
                f"{_dignity_phrase(dignity)}, so the same "
                f"matters ask more effort of you than they would otherwise",
                ids, rule,
                brief=f"a {dignity} {ordinal(house)} lord",
                plain=(f"{_planet(v['lord'])} rules it and sits "
                       f"{_plain_dignity(dignity)}" if main else ""),
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
                plain=(f"{_planets(benefics)} "
                       f"{'protects' if len(benefics) == 1 else 'protect'} it"
                       if main else ""),
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
                plain=(f"{_planets(malefics)} "
                       f"{'presses' if len(malefics) == 1 else 'press'} "
                       f"on it"),
                weight=2))

    # --- step 2, karaka --------------------------------------------------
    for karaka in domain.karakas[:2]:
        kf = facts[f"karaka.{karaka.lower()}"]
        v = kf.value
        dignity = _dignity_of(kf)
        ids = (f"karaka.{karaka.lower()}",)
        rule = ("rule.graha.karakatva",)
        gloss = KARAKATVAS[karaka].split(",")[0]
        where = (f"{karaka}, which naturally signifies "
                 f"{gloss} here, sits in your "
                 f"{ordinal(v['house'])} house")
        # In the plain register a karaka is "the planet of X" — which is
        # exactly what a karaka is, said without the word.
        who = f"{_planet(karaka)}, the planet of {gloss},"
        first = karaka == domain.karakas[0]
        if any(x in dignity for x in STRONG):
            signals.append(Signal(
                "support",
                f"{where} and is {_dignity_phrase(dignity.split(' (')[0])}",
                ids, rule, brief=f"{karaka} strong",
                plain=(f"{who} sits {_plain_dignity(dignity)}"
                       if first else ""),
                weight=3 if first else 1))
        elif any(x in dignity for x in WEAK):
            signals.append(Signal(
                "strain",
                f"{where} but is {_dignity_phrase(dignity.split(' (')[0])}",
                ids, rule, brief=f"{karaka} debilitated",
                plain=(f"{who} sits {_plain_dignity(dignity)}"
                       if first else ""),
                weight=3 if first else 1))
        elif v["house"] in (6, 8, 12):
            signals.append(Signal(
                "strain",
                f"{where} — one of the three houses the tradition reads as "
                f"hidden or costly, so its gifts arrive indirectly",
                ids, rule + (f"rule.house.{v['house']}",),
                brief=f"{karaka} tucked in the {ordinal(v['house'])}",
                plain=(f"{who} sits somewhere hidden" if first else ""),
                weight=2 if first else 1))
        else:
            signals.append(Signal("support", where, ids, rule,
                                  brief=f"{karaka} soundly placed",
                                  plain=(f"{who} is soundly placed"
                                         if first else ""),
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
        plain=(f"the second chart puts {_planets(here)} over it" if here
               else f"the second chart leaves it to "
                    f"{_planet(vf.value['lord'])} alone"),
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
                    plain=(f"{_planet(lord)}'s period holds it until "
                           f"{_year(cv.get('md_end'))}"
                           if role == "mahadasha"
                           else f"{_planet(lord)}'s stretch inside it runs to "
                                f"{_year(cv.get('ad_end'))}"),
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
            plain=(f"{_planet(planet)} is on it{until}" if occupied
                   else f"{_planet(planet)} is working on it{until}"),
            weight=2 if occupied else 1))

    # The main house's own lord, named — the fact every domain has, kept as a
    # last resort so no verdict can fall back to a phrase with no chart in it.
    mv = facts[f"natal.{domain.main_house}L"].value
    headline = Signal(
        "support", "", (f"natal.{domain.main_house}L",),
        plain=(f"{_planet(mv['lord'])} rules it from {mv['lord_sign']}"),
        weight=0)

    return DomainReading(domain=domain,
                         verdict=_verdict_and_spent(domain, signals,
                                                    headline)[0],
                         teaser=_teaser(domain, signals, headline),
                         paragraphs=_paragraphs(domain, signals, headline),
                         caveat=_caveat(signals),
                         signals=tuple(signals))


# How the balance is named. Weighted, so a debilitated lord of the MAIN
# house counts for more than a benefic aspect on a supporting one — which is
# how an astrologer would weigh them, and a bare count would not.
#
# THE VERDICT IS A CONDITION, NOT AN OUTCOME. "Marriage is one of the strong
# parts of your chart" is a verdict a stranger understands and this module can
# stand behind. "You will marry in 2027" is a prediction, and there is still
# no sentence template that can produce one. Answering first changed the ORDER
# of speech, not what may be said.
def _balance(supports, strains) -> tuple[str, str]:
    """(technical label, plain verdict clause).

    The clauses are short on purpose and none of them is a filler phrase:
    "is one of the stronger parts of your chart" passed every rule in
    voice.py and told the reader nothing about their own chart, so it — and
    its four siblings — are on the vagueness ban-list now. A verdict states a
    judgement AND the named fact behind it, in one breath.
    """
    up = sum(s.weight for s in supports)
    down = sum(s.weight for s in strains)
    if up >= down * 2 and up:
        return "Well supported", "runs strong"
    if down >= up * 2 and down:
        return "Asks real work", "asks real work"
    if up > down:
        return "Mixed", "leans your way"
    if down > up:
        return "Mixed", "runs uphill"
    return "Mixed", "cuts both ways"


def _named(items):
    """The sharpest signal whose plain form names a graha."""
    pool = [s for s in items if s.plain and voice.names_a_planet(s.plain)]
    return sorted(pool, key=lambda s: -s.weight)[0] if pool else None


def _sharpest(items, plain_only=False):
    pool = [s for s in items if (s.plain if plain_only else s.brief)]
    ranked = sorted(pool, key=lambda s: -s.weight)
    return ranked[0] if ranked else None


def _top(items, n, plain_only=True):
    pool = [s for s in items if (s.plain if plain_only else s.brief)]
    return sorted(pool, key=lambda s: -s.weight)[:n]


def _verdict_and_spent(domain: Domain, signals: list[Signal],
                       headline: Signal | None = None
                       ) -> tuple[str, list[Signal]]:
    """The first breath: 1–2 sentences a stranger understands.

    No throat-clearing, no house numbers, no Sanskrit, and the actual answer
    in the opening clause rather than after a paragraph of positioning.

    Returns the prose and the signals it spent, so the paragraphs beneath do
    not repeat, word for word, the reason just given. Saying it twice is how
    a short reading becomes a long one again.
    """
    subject = SUBJECT.get(domain.id, domain.label.capitalize())
    supports = [s for s in signals if s.kind == "support"]
    strains = [s for s in signals if s.kind == "strain"]
    live = [s for s in signals if s.kind in ("period", "live")]
    if not signals:
        return (f"{subject} is quiet in your chart — nothing bears strongly "
                f"on it either way."), []

    _, clause = _balance(supports, strains)
    # One concrete reason, on whichever side is doing the most work — and it
    # must NAME a planet. A verdict that says "the planet that rules it is
    # strong" is short, plain, answer-first and completely uninformative;
    # naming the graha is what makes it about this chart.
    side = strains if clause in ("asks real work", "runs uphill") else supports
    driver = _named(side) or _named(supports) or _named(strains) or headline
    first = f"{subject} {clause}"
    used = []
    if driver is not None:
        candidate = f"{first}: {driver.plain}"
        if voice.words(candidate + ".") <= voice.TEASER_WORDS:
            first = candidate
            used = [driver]
    out = first + "."

    # Where a domain has a dated influence running, the verdict says WHEN —
    # a reader can act on "until Jun 2027" and cannot act on "right now".
    dated = [s for s in live if s.plain and voice.names_a_date(s.plain)]
    top_live = _named(dated) or _sharpest(dated or live, plain_only=True)
    if top_live:
        out += f" {top_live.plain[0].upper()}{top_live.plain[1:]}."
        used.append(top_live)
    return out, used


def _teaser(domain: Domain, signals: list[Signal],
            headline: Signal | None = None) -> str:
    """The card's one line — the reading's own first breath, trimmed.

    Deliberately not written separately. A card that promised one thing and
    a view that said another would be two readings of one chart, and the
    card is the more-read of the two.
    """
    verdict, _ = _verdict_and_spent(domain, signals, headline)
    return voice.trim_to(verdict, voice.TEASER_WORDS)


# THE one caveat — a field, not a sentence buried in the prose, so that "one
# caveat maximum, at the end, one line" is a property of the structure rather
# than a habit anyone has to remember. It is true, it matters, and it belongs
# after the reading: a caveat that arrives first is not honesty, it is a
# refusal to answer wearing honesty's coat.
CAVEAT_LIVE = "A transit is a season with an end date, not a verdict."
CAVEAT_STILL = "This reads the chart's condition, not what will happen."


def _paragraphs(domain: Domain, signals: list[Signal],
                headline: Signal | None = None) -> tuple[str, ...]:
    """The visible synthesis: the verdict, then the working, within budget.

    Everything cut here is one tap away in the expanders below, unchanged and
    still citing its fact ids. This is a question of what arrives first and
    how much of it, not of what the app is willing to say.
    """
    supports = [s for s in signals if s.kind == "support"]
    strains = [s for s in signals if s.kind == "strain"]
    live = [s for s in signals if s.kind in ("period", "live")]

    verdict, spent = _verdict_and_spent(domain, signals, headline)
    said = {id(x) for x in spent}
    supports = [s for s in supports if id(s) not in said]
    strains = [s for s in strains if id(s) not in said]
    live = [s for s in live if id(s) not in said]

    out = [verdict]
    budget = (voice.SYNTHESIS_WORDS - voice.words(verdict)
              - voice.words(CAVEAT_LIVE))

    def para(items, lead, n):
        picked = _top(items, n)
        if not picked:
            return ""
        return f"{lead} {_and([s.plain for s in picked])}."

    # Ordered by what a person actually wants: the obstacle, then the help,
    # then the clock. Budget spends from the top, so a long strain sentence
    # crowds out the transit line rather than truncating it mid-clause.
    for text in (para(strains, "What asks more of you:", 2),
                 para(supports, "What holds it up:", 2),
                 para(live, "Live now:", 2)):
        if text and voice.words(text) <= budget:
            out.append(text)
            budget -= voice.words(text)

    return tuple(out)


def _caveat(signals: list[Signal]) -> str:
    """One line. The dated one only if a dated claim was actually made."""
    return (CAVEAT_LIVE if any(s.kind == "live" for s in signals)
            else CAVEAT_STILL)


def read_all(chart: Chart, when: datetime) -> list[DomainReading]:
    """Every domain, from one build of the ledger."""
    from chartfacts import build_facts
    facts = {f.id: f for f in build_facts(chart, when)}
    return [read(chart, when, did, facts) for did in DOMAINS]
