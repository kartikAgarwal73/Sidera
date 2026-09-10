"""A yoga, read rather than merely detected.

WHAT WAS WRONG
`yogas.py` finds the combinations and `explain.py` says what each family
classically means. Between them a reader got a name, a rule, and a sentence
of meaning that was true of the yoga rather than of their chart — and no
answer at all to the two questions anybody actually asks: is it real in my
chart, and when does it do anything?

WHAT A YOGA ENTRY OWES THE READER, in this order:

  FORMED IN     D1 — and whether the divisional charts agree. A promise made
                by the birth chart and dropped by the ninth division is
                thinner than it looks; `rule.varga.confirms` is the
                classical statement of that, and this module applies it
                instead of leaving the reader to.
  WHAT IT GIVES one plain sentence of the classical result, cited.
  WHEN          the periods of its forming grahas, with dates off the
                ledger. A yoga is latent until one of them runs
                (`rule.graha.yoga_activation`). If that period is past, this
                says so; if it is ahead, it dates it.
  WHERE         the houses involved, in plain words.

WHAT IT WILL NOT DO
Promise an outcome, or invent a date. Every date here comes from the
Vimshottari timeline the ledger already publishes, and every claim carries
the rule id it rests on, so `chartfacts` can back it and the validator can
check it.

ON VARGA DIGNITY
This build computes divisional positions to the SIGN, never the degree
(`rule.varga.sign_level`). Exaltation, debilitation and own-sign are sign
properties and are available; moolatrikona needs a degree and is not. The
strength test below says exactly which of those it used, and never reaches
for the one that is not there.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import voice
from dashas import vimshottari
from engine import Chart, PLANETS, SIGNS
from rulelib import HOUSE_MATTERS, KARAKATVAS
from transits import CONJUNCTION_ORB, angular_distance, transit_snapshot
from vargas import VargaChart, varga_chart
from yogas import (DEBILITATION_SIGN, EXALTATION_SIGN, Yoga, detect_all,
                   sign_lord)

# The nodes have no English name in ordinary use; everything else is the
# reader's own sky. Same table `today.py` and `domainread.py` use.
PLAIN_PLANET = {"Rahu": "the north node", "Ketu": "the south node",
                "Sun": "the Sun", "Moon": "the Moon"}

# Which yogas are tested in the tenth division as well as the ninth. Read off
# the chart, not from a list of names: a combination that touches the houses
# of held resources, visible work or gains is a career-or-wealth yoga
# whatever it is called, and the D10 is the division those are tested in.
CAREER_WEALTH_HOUSES = (2, 10, 11)
CAREER_WEALTH_KINDS = ("Dhana", "Viparita Raja")

# What each family classically GIVES, in one plain sentence. Deliberately
# separate from `explain.YOGA_MEANING`, which is written for the expander and
# uses the technical register; these are the top layer, and the plain-register
# rule applies to them.
GIVES = {
    "Ruchaka": "Command, physical courage, and results that come from "
               "deciding quickly.",
    "Bhadra": "A sharp mind for analysis and speech, and learning that "
              "stays.",
    "Hamsa": "Good judgement, the respect of teachers, and the fortune "
             "that tends to follow both.",
    "Malavya": "Comfort, refinement, and happiness arriving through other "
               "people.",
    "Shasha": "Authority built slowly, over land, work and people.",
    "Gaja Kesari": "A reputation that lasts and resources that recover "
                   "after a loss.",
    "Budhaditya": "Intelligence joined to authority — skill at analysis, "
                  "administration and being understood.",
    "Dhana": "Money arrives along the lines these planets already run.",
    "Viparita Raja": "Gains that arrive through difficulty, and reversals "
                     "that end in your favour.",
    "Neecha Bhanga": "The weakness is cancelled: strength restored, "
                     "classically after an early setback.",
    "Kemadruma": "Self-reliance asked of the mind — softened, classically, "
                 "by the exceptions that cancel it.",
}

# The rule each of those sentences rests on. The validator checks that a
# claim cites a rule that exists; these are the citations.
GIVES_RULE = {
    "Ruchaka": "rule.yoga.mahapurusha", "Bhadra": "rule.yoga.mahapurusha",
    "Hamsa": "rule.yoga.mahapurusha", "Malavya": "rule.yoga.mahapurusha",
    "Shasha": "rule.yoga.mahapurusha",
    "Gaja Kesari": "rule.yoga.chandra",
    "Budhaditya": "rule.yoga.solar",
    "Dhana": "rule.yoga.dhana",
    "Viparita Raja": "rule.yoga.viparita",
    "Neecha Bhanga": "rule.yoga.neecha_bhanga",
    "Kemadruma": "rule.yoga.kemadruma",
}


def yoga_fact_id(name: str) -> str:
    """The ledger id for a yoga, made in ONE place.

    `yogaread` cites fact ids and `chartfacts` publishes them; when each
    slugged the name its own way the reading cited
    `yoga.dhana-yoga-(lords-of-1-&-2-conjoined)` and the ledger carried
    `yoga.dhana-yoga-lords-of-1--2-conjoined`. A citation that does not
    resolve is worse than no citation: it looks checkable and is not.
    """
    keep = [c.lower() if c.isalnum() else "-" for c in name]
    return "yoga." + "".join(keep).strip("-").replace("--", "-")


def _plain(name: str) -> str:
    return PLAIN_PLANET.get(name, name)


def _and_list(items: list[str]) -> str:
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + " and " + items[-1]


def family(yoga: Yoga) -> str:
    """Which entry in GIVES this yoga belongs to."""
    for key in GIVES:
        if yoga.name.startswith(key) or key in yoga.kind:
            return key
    return "Dhana"


def varga_dignity(varga: VargaChart, planet: str) -> str:
    """Dignity in a divisional chart, from the SIGN alone.

    Exaltation, debilitation and own-sign are properties of the sign and are
    computable here. Moolatrikona is a degree band and is not — this build
    holds no degree inside a divisional sign — so it is never returned and
    never implied. `rule.varga.sign_level` is the statement of that limit.
    """
    sign = varga.planets[planet].sign_index
    if DEBILITATION_SIGN.get(planet) == sign:
        return "debilitated"
    if EXALTATION_SIGN.get(planet) == sign:
        return "exalted"
    if sign_lord(sign) == planet:
        return "own sign"
    return "neutral"


STRONG = ("exalted", "own sign")


@dataclass(frozen=True)
class VargaTest:
    """One division's verdict on a yoga's forming grahas."""

    varga: str                 # "D9" | "D10"
    read_for: str              # what this division is read for, plainly
    strong: tuple[str, ...]    # forming grahas dignified here
    weak: tuple[str, ...]      # forming grahas at their weakest here
    detail: str                # graha by graha, for the expander
    verdict: str               # the one line the top layer prints
    confirmed: bool


@dataclass(frozen=True)
class Activation:
    """A period of a forming graha — the window a yoga is read as delivering
    in."""

    lord: str
    level: str                 # "mahadasha" | "antardasha"
    start: datetime
    end: datetime
    state: str                 # "past" | "running" | "ahead"

    @property
    def window(self) -> str:
        return f"{self.start:%b %Y} – {self.end:%b %Y}"


@dataclass(frozen=True)
class YogaReading:
    yoga: Yoga
    verdict: str                       # answer first, two sentences at most
    gives: str                         # the classical result, plainly
    gives_rule: str
    where: str                         # the houses, in plain words
    varga_tests: tuple[VargaTest, ...]
    activations: tuple[Activation, ...]
    contacts: tuple[str, ...]          # transits on a forming graha now
    fact_ids: tuple[str, ...]
    rule_ids: tuple[str, ...]

    @property
    def running(self) -> Activation | None:
        return next((a for a in self.activations if a.state == "running"),
                    None)

    @property
    def next_up(self) -> Activation | None:
        return next((a for a in self.activations if a.state == "ahead"), None)


def _varga_test(yoga: Yoga, chart: Chart, code: str, read_for: str,
                vc: VargaChart | None = None) -> VargaTest:
    vc = vc if vc is not None else varga_chart(chart, code)
    strong, weak, rows = [], [], []
    for p in yoga.planets:
        state = varga_dignity(vc, p)
        rows.append(f"{p} is in {SIGNS[vc.planets[p].sign_index]} "
                    f"({state}) in the {code}")
        if state in STRONG:
            strong.append(_plain(p))
        elif state == "debilitated":
            weak.append(_plain(p))
    ordinal = "ninth" if code == "D9" else "tenth"
    if strong and not weak:
        verdict = (f"Confirmed in the {ordinal} division: "
                   f"{_and_list(strong)} "
                   f"{'holds' if len(strong) == 1 else 'hold'} strength "
                   f"there too.")
        confirmed = True
    elif weak and not strong:
        verdict = (f"It weakens in the {ordinal} division — the promise is "
                   f"thinner than it looks. {_and_list(weak).capitalize()} "
                   f"{'is' if len(weak) == 1 else 'are'} at "
                   f"{'its' if len(weak) == 1 else 'their'} weakest there.")
        confirmed = False
    elif strong and weak:
        verdict = (f"The {ordinal} division splits: {_and_list(strong)} "
                   f"{'holds' if len(strong) == 1 else 'hold'} up and "
                   f"{_and_list(weak)} "
                   f"{'does' if len(weak) == 1 else 'do'} not.")
        confirmed = False
    else:
        verdict = (f"The {ordinal} division neither confirms nor weakens it: "
                   f"{_and_list([_plain(p) for p in yoga.planets])} "
                   f"{'stands' if len(yoga.planets) == 1 else 'stand'} "
                   f"neutrally there.")
        confirmed = False
    return VargaTest(varga=code, read_for=read_for, strong=tuple(strong),
                     weak=tuple(weak), detail="; ".join(rows) + ".",
                     verdict=verdict, confirmed=confirmed)


def _activations(yoga: Yoga, chart: Chart, when: datetime,
                 timeline=None) -> tuple[Activation, ...]:
    """The periods of this yoga's forming grahas, dated off the timeline.

    A yoga is latent until a period of one of its forming grahas runs. Both
    levels count: the mahadasha of a forming graha is the long window, and
    its antardasha inside the running mahadasha is the short one.
    """
    timeline = timeline if timeline is not None else vimshottari(chart)
    forming = set(yoga.planets)
    out: list[Activation] = []
    for md in timeline.mahadashas:
        if md.lord in forming:
            out.append(Activation(
                lord=md.lord, level="mahadasha", start=md.start, end=md.end,
                state=("running" if md.contains(when)
                       else "past" if md.end <= when else "ahead")))
        # The antardashas of forming grahas inside the RUNNING mahadasha.
        # Every other mahadasha's would be nine more rows saying nothing the
        # mahadasha row does not already say.
        if md.contains(when):
            for ad in md.antardashas:
                if ad.lord in forming and ad.lord != md.lord:
                    out.append(Activation(
                        lord=ad.lord, level="antardasha", start=ad.start,
                        end=ad.end,
                        state=("running" if ad.contains(when)
                               else "past" if ad.end <= when else "ahead")))
    out.sort(key=lambda a: a.start)
    return tuple(out)


def _contacts(yoga: Yoga, chart: Chart, when: datetime,
              snap=None) -> tuple[str, ...]:
    """Transits standing on a forming graha now — the short, dated prompt."""
    snap = snap if snap is not None else transit_snapshot(chart, when)
    out = []
    for t in PLANETS:
        t_lon = snap.planets[t].position.longitude
        for p in yoga.planets:
            gap = angular_distance(t_lon, chart.planets[p].longitude)
            if gap <= CONJUNCTION_ORB:
                out.append(f"{_plain(t)} is standing on your {_plain(p)} "
                           f"({gap:.1f}° away) — the combination is being "
                           f"prompted now.")
    return tuple(out)


def _where(yoga: Yoga) -> str:
    """The houses involved, in plain words and never by number."""
    seen, parts = set(), []
    for h in yoga.houses:
        if h in seen:
            continue
        seen.add(h)
        parts.append(HOUSE_MATTERS[h].split(",")[0].strip())
    return _and_list(parts) if parts else "the chart as a whole"


# A yoga verdict is the answer, not the working: two sentences, and short.
# Longer than a domain card's teaser because it has two things to say —
# whether the combination is real and when it acts — and much shorter than a
# domain synthesis, which is a whole fold.
VERDICT_WORDS = 40


def _verdict(yoga: Yoga, tests: tuple[VargaTest, ...],
             activations: tuple[Activation, ...], when: datetime) -> str:
    """Answer first, in at most two sentences.

    Sentence one: is it real, and what does it touch. Sentence two: when.
    Nothing else goes here — the working is in the expander.

    The yoga's NAME is not repeated. It is the heading this sentence sits
    under, and repeating it both wasted a fifth of the budget and put
    "Yoga" — a word the plain-register rule bans from the top layer — into
    every verdict in the app.
    """
    planets = _and_list([_plain(p) for p in yoga.planets])
    plural = len(yoga.planets) != 1
    where = _where(yoga)
    if yoga.cancelled:
        head = (f"Held in check: {planets} form it, but it does not deliver "
                f"on {where}.")
    else:
        d9 = next((t for t in tests if t.varga == "D9"), None)
        if d9 is not None and d9.confirmed:
            head = (f"Real, and confirmed: {planets} "
                    f"{'hold' if plural else 'holds'} up in the ninth "
                    f"division too, and it works on {where}.")
        elif d9 is not None and d9.weak:
            weak = _and_list(d9.weak)
            head = (f"Thinner than it looks: {weak[:1].upper()}{weak[1:]} "
                    f"{'weaken' if len(d9.weak) != 1 else 'weakens'} in the "
                    f"ninth division, so its promise on {where} asks more of "
                    f"you.")
        else:
            # Sentence case, NOT `.capitalize()`: that lowercases everything
            # after the first character and turned "the Sun and Mercury"
            # into "The sun and mercury".
            lead = planets[:1].upper() + planets[1:]
            head = (f"{lead} {'form' if plural else 'forms'} it, and it "
                    f"works on {where}.")

    running = next((a for a in activations if a.state == "running"), None)
    ahead = next((a for a in activations if a.state == "ahead"), None)
    past = [a for a in activations if a.state == "past"]
    if running:
        tail = f"Its period runs until {running.end:%b %Y}."
    elif ahead:
        tail = (f"It comes into force {ahead.start:%b %Y} and runs to "
                f"{ahead.end:%b %Y}.")
    elif past:
        last = max(past, key=lambda a: a.end)
        tail = (f"Its period ended {last.end:%b %Y} — already given, not "
                f"still coming.")
    else:
        tail = "No period of these planets falls in the next hundred years."
    return f"{head} {tail}"


@dataclass(frozen=True)
class _Shared:
    """Everything a yoga reading needs that is a property of the CHART, not
    of the yoga: the divisional charts, the 120-year timeline, and today's
    sky. Computed once per chart and handed to every yoga.

    This is not premature optimisation. Built per-yoga, a chart with eight
    yogas cast the D9 and D10 eight times each, rebuilt the whole
    Vimshottari timeline eight times and took a full transit snapshot eight
    times — and `chartfacts` then did all of it again. A single page render
    went from under a second to over two minutes.
    """

    d9: VargaChart
    d10: VargaChart
    timeline: object
    snapshot: object


def shared_for(chart: Chart, when: datetime) -> _Shared:
    return _Shared(d9=varga_chart(chart, "D9"), d10=varga_chart(chart, "D10"),
                   timeline=vimshottari(chart),
                   snapshot=transit_snapshot(chart, when))


def read_yoga(yoga: Yoga, chart: Chart, when: datetime,
              shared: _Shared | None = None) -> YogaReading:
    shared = shared if shared is not None else shared_for(chart, when)
    tests = [_varga_test(yoga, chart, "D9",
                         "marriage, and the inner strength of every planet",
                         vc=shared.d9)]
    if (any(h in CAREER_WEALTH_HOUSES for h in yoga.houses)
            or yoga.kind in CAREER_WEALTH_KINDS):
        tests.append(_varga_test(
            yoga, chart, "D10",
            "work, standing, and the field a career takes place in",
            vc=shared.d10))
    activations = _activations(yoga, chart, when, timeline=shared.timeline)
    key = family(yoga)
    base = yoga_fact_id(yoga.name)
    facts = [base, f"{base}.varga", f"{base}.activation"]
    facts += [f"varga.d9.{p.lower()}" for p in yoga.planets]
    if any(t.varga == "D10" for t in tests):
        facts += [f"varga.d10.{p.lower()}" for p in yoga.planets]
    facts.append("dasha.current")
    rules = ["rule.graha.yoga_varga", "rule.graha.yoga_activation",
             "rule.varga.confirms", "rule.varga.sign_level",
             GIVES_RULE[key]]
    return YogaReading(
        yoga=yoga,
        verdict=_verdict(yoga, tuple(tests), activations, when),
        gives=GIVES[key],
        gives_rule=GIVES_RULE[key],
        where=_where(yoga),
        varga_tests=tuple(tests),
        activations=activations,
        contacts=_contacts(yoga, chart, when, snap=shared.snapshot),
        fact_ids=tuple(facts),
        rule_ids=tuple(rules),
    )


def read_all(chart: Chart, when: datetime) -> list[YogaReading]:
    shared = shared_for(chart, when)
    return [read_yoga(y, chart, when, shared) for y in detect_all(chart)]
