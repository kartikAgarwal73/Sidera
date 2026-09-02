"""Ask Your Chart — a structured question-to-evidence engine.

Every question in the registry declares: its text and category, the
placements/techniques it needs, the classical rules it applies, and a
confidence weight per lens. Answering computes the required facts from the
existing modules, applies the stored rules, and returns a Verdict carrying:
the plain-language answer (template-composed — NO free-text generation),
each contributing placement with its computed value, the rule invoked per
lens, a weighted convergence score, and an overall confidence tag.

Core product principle: where lenses disagree, the disagreement is
DISPLAYED, never resolved. The modal indication is reported as strongest;
dissenting lenses are listed beside it with their own indications intact.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Callable

from dashas import VimshottariTimeline
from engine import PLANETS, SIGNS, Chart
from explain import DASHA_THEME, ordinal
from transits import aspected_signs, next_sign_ingress, sign_entry_before
from vargas import dasamsa, navamsa
from yogas import (
    detect_dhana,
    dignity,
    dignity_grade,
    house_lords,
    natural_relation,
    sign_lord,
)

# --- vocabulary (stored rules operate over these tokens) ----------------------

PLANET_DOMAINS = {
    "Sun": ("authority", "government", "leadership"),
    "Moon": ("public life", "care work", "nourishment"),
    "Mars": ("engineering", "defence", "surgery", "sport"),
    "Mercury": ("commerce", "writing", "analysis", "administration"),
    "Jupiter": ("teaching", "counsel", "law", "finance"),
    "Venus": ("arts", "design", "luxury", "hospitality"),
    "Saturn": ("industry", "labour", "land", "structures"),
    "Rahu": ("technology", "foreign fields", "media"),
    "Ketu": ("research", "healing", "contemplative work"),
}

CONFIDENCE_ORDER = ("High", "Moderate", "Interpretive")


# --- result types --------------------------------------------------------------

@dataclass(frozen=True)
class Placement:
    label: str   # e.g. "7th lord"
    value: str   # computed value, e.g. "Mercury in Virgo (10th house), exalted"


@dataclass(frozen=True)
class LensFinding:
    lens: str
    technique: str
    rule: str                    # classical rule, verbatim
    weight: float                # stored confidence-weighting for this lens
    confidence: str              # High | Moderate | Interpretive
    placements: tuple[Placement, ...]
    indications: frozenset[str]  # tokens this lens points to
    statement: str               # template-composed per-lens statement


@dataclass(frozen=True)
class Verdict:
    key: str
    question: str
    category: str
    answer: str
    findings: tuple[LensFinding, ...]
    convergence: float           # 0–1, weighted share agreeing with the mode
    agreement: str               # 'strong convergence' | 'partial convergence'
    #                              | 'lenses disagree'
    disagreement: str | None     # explicit, never resolved
    confidence: str
    modal_indications: tuple[str, ...]


@dataclass
class ChartContext:
    """Shared computed facts, built once per chart."""

    chart: Chart
    timeline: VimshottariTimeline
    now: datetime

    def __post_init__(self):
        self.d9 = navamsa(self.chart)
        self.d10 = dasamsa(self.chart)
        self.lords = house_lords(self.chart)
        self.dhana = detect_dhana(self.chart)
        self._jupiter_periods = None

    def placement_value(self, planet: str) -> str:
        pos = self.chart.planets[planet]
        state = dignity_grade(self.chart, planet) or dignity(self.chart, planet)
        return (f"{planet} in {pos.sign} ({ordinal(pos.house)} house)"
                + (f", {state}" if state != "neutral" else ""))

    def jupiter_periods(self, horizon_days: int = 2600):
        """(start, end, sign_index) spans for transit Jupiter."""
        if self._jupiter_periods is None:
            spans = []
            start = sign_entry_before("Jupiter", self.now) or self.now
            t = start
            while (t - self.now).days < horizon_days:
                ing = next_sign_ingress("Jupiter", t, max_days=horizon_days)
                if ing is None:
                    break
                spans.append((t, ing.when, ing.from_sign_index))
                t = ing.when
            self._jupiter_periods = spans
        return self._jupiter_periods

    def dasha_windows(self, targets: set[str], horizon_years: float = 8.0):
        """AD windows (within running/future MDs) whose MD or AD lord is in
        `targets`, inside the horizon."""
        horizon = self.now + timedelta(days=horizon_years * 365.25)
        out = []
        for md in self.timeline.mahadashas:
            if md.end < self.now or md.start > horizon:
                continue
            for ad in md.antardashas:
                if ad.end < self.now or ad.start > horizon:
                    continue
                hit = [p for p in (md.lord, ad.lord) if p in targets]
                if hit:
                    out.append({
                        "md": md.lord, "ad": ad.lord,
                        "start": ad.start, "end": ad.end,
                        "hit": tuple(dict.fromkeys(hit)),
                        "running": ad.contains(self.now),
                    })
        return out


# --- lens / question framework -------------------------------------------------

@dataclass(frozen=True)
class Lens:
    name: str
    technique: str
    rule: str
    weight: float
    confidence: str
    compute: Callable[[ChartContext], tuple[tuple[Placement, ...],
                                            frozenset, str]]

    def run(self, ctx: ChartContext) -> LensFinding:
        placements, indications, statement = self.compute(ctx)
        return LensFinding(
            lens=self.name, technique=self.technique, rule=self.rule,
            weight=self.weight, confidence=self.confidence,
            placements=placements, indications=frozenset(indications),
            statement=statement,
        )


@dataclass(frozen=True)
class Question:
    key: str
    text: str
    category: str
    techniques: tuple[str, ...]
    lenses: tuple[Lens, ...]
    answer_frame: str  # template for the synthesis line


def _confidence_floor(tags: list[str]) -> str:
    return max(tags, key=CONFIDENCE_ORDER.index)  # weakest wins


def _agreement_label(convergence: float) -> str:
    """How much of the weight backs the modal reading.

    Named rather than inlined so the low-convergence branch stays testable
    on its own: whether any committed chart happens to reach it is an
    accident of that chart, but the threshold is part of the contract.
    """
    if convergence >= 0.75:
        return "strong convergence"
    if convergence >= 0.5:
        return "partial convergence"
    return "lenses disagree"


def ask(key: str, ctx: ChartContext) -> Verdict:
    q = REGISTRY[key]
    findings = tuple(lens.run(ctx) for lens in q.lenses)

    # Weighted convergence: the modal indication is the token carrying the
    # greatest total lens weight; convergence = share of total weight from
    # lenses whose indications include a modal token.
    token_weight: dict[str, float] = {}
    for f in findings:
        for tok in f.indications:
            token_weight[tok] = token_weight.get(tok, 0.0) + f.weight
    total = sum(f.weight for f in findings) or 1.0
    if token_weight:
        top = max(token_weight.values())
        modal = tuple(sorted(t for t, w in token_weight.items()
                             if abs(w - top) < 1e-9))
        agreeing = sum(f.weight for f in findings
                       if f.indications & set(modal))
        convergence = round(agreeing / total, 2)
    else:
        modal, convergence = (), 0.0

    dissenters = [f for f in findings if not (f.indications & set(modal))]
    agreement = _agreement_label(convergence)

    disagreement = None
    if dissenters:
        parts = [f"{f.lens} points instead to "
                 + ", ".join(sorted(f.indications)) for f in dissenters]
        disagreement = ("The lenses do not fully agree — shown side by "
                        "side, unresolved: " + "; ".join(parts) + ".")

    answer = q.answer_frame.format(
        modal=", ".join(modal) if modal else "no single signal",
        carriers=", ".join(f.lens for f in findings
                           if f.indications & set(modal)) or "none",
        pct=int(convergence * 100),
    )
    if disagreement:
        answer += " Divergent testimony is listed below, not averaged away."

    confidence = _confidence_floor([f.confidence for f in findings])
    if convergence < 0.75 and confidence != "Interpretive":
        confidence = CONFIDENCE_ORDER[
            CONFIDENCE_ORDER.index(confidence) + 1]

    return Verdict(
        key=q.key, question=q.text, category=q.category, answer=answer,
        findings=findings, convergence=convergence, agreement=agreement,
        disagreement=disagreement, confidence=confidence,
        modal_indications=modal,
    )


def ask_all(ctx: ChartContext) -> list[Verdict]:
    return [ask(key, ctx) for key in REGISTRY]


# --- helper computes -----------------------------------------------------------

def _domains(planet: str) -> frozenset[str]:
    return frozenset(PLANET_DOMAINS[planet])


def _window_years(start: datetime, end: datetime) -> frozenset[str]:
    return frozenset(str(y) for y in range(start.year, end.year + 1))


def _fmt_window(w) -> str:
    return f"{w['start']:%b %Y} – {w['end']:%b %Y}"


# --- the five sample questions --------------------------------------------------

def _spouse_l1(ctx):
    lord7 = ctx.lords[7]
    return ((Placement("7th lord", ctx.placement_value(lord7)),),
            _domains(lord7),
            f"The 7th lord is {lord7} — its nature colours the partner's "
            f"working life toward {', '.join(PLANET_DOMAINS[lord7])}.")


def _spouse_l2(ctx):
    d9 = ctx.d9
    seventh_sign = (d9.lagna_sign_index + 6) % 12
    occupants = [p for p in PLANETS
                 if d9.planets[p].sign_index == seventh_sign]
    if occupants:
        toks = frozenset().union(*(_domains(p) for p in occupants))
        pls = tuple(Placement(f"D9 7th occupant", f"{p} in D9 "
                              f"{SIGNS[seventh_sign]}") for p in occupants)
        stmt = (f"The navamsa 7th ({SIGNS[seventh_sign]}) holds "
                + ", ".join(occupants) + ".")
    else:
        ruler = sign_lord(seventh_sign)
        toks = _domains(ruler)
        pls = (Placement("D9 7th lord",
                         f"{ruler} rules D9 {SIGNS[seventh_sign]}; placed "
                         f"in D9 {d9.planets[ruler].sign}"),)
        stmt = (f"The navamsa 7th ({SIGNS[seventh_sign]}) is empty; its "
                f"lord {ruler} speaks for it — "
                f"{', '.join(PLANET_DOMAINS[ruler])}.")
    return pls, toks, stmt


def _spouse_l3(ctx):
    pos = ctx.chart.planets["Venus"]
    return ((Placement("Venus (kalatra karaka)",
                       ctx.placement_value("Venus")),),
            _domains("Venus") | _domains(ctx.lords[pos.house]),
            f"Venus, the marriage karaka, stands in the "
            f"{ordinal(pos.house)} house in {pos.sign} — its own field "
            f"({', '.join(PLANET_DOMAINS['Venus'])}) tinted by that "
            "house's lord.")


def _career_l1(ctx):
    lord10 = ctx.lords[10]
    return ((Placement("10th lord", ctx.placement_value(lord10)),),
            _domains(lord10),
            f"The 10th lord {lord10} carries the karma-sthana: "
            f"{', '.join(PLANET_DOMAINS[lord10])}.")


def _career_l2(ctx):
    occupants = [p for p in PLANETS if ctx.chart.planets[p].house == 10]
    if not occupants:
        return ((Placement("10th house", "unoccupied"),), frozenset(),
                "No planet occupies the 10th; the lord speaks alone.")
    toks = frozenset().union(*(_domains(p) for p in occupants))
    pls = tuple(Placement("10th-house occupant", ctx.placement_value(p))
                for p in occupants)
    return (pls, toks,
            "Planets standing in the 10th add their trades: "
            + "; ".join(f"{p} — {', '.join(PLANET_DOMAINS[p])}"
                        for p in occupants) + ".")


def _career_l3(ctx):
    d10 = ctx.d10
    lord = sign_lord(d10.lagna_sign_index)
    tenth = (d10.lagna_sign_index + 9) % 12
    occupants = [p for p in PLANETS if d10.planets[p].sign_index == tenth]
    toks = _domains(lord)
    pls = [Placement("D10 lagna lord",
                     f"{lord} rules D10 {d10.lagna_sign}")]
    stmt = (f"The dasamsa rises in {d10.lagna_sign}, ruled by {lord} "
            f"({', '.join(PLANET_DOMAINS[lord])})")
    if occupants:
        toks = toks | frozenset().union(*(_domains(p) for p in occupants))
        pls += [Placement("D10 10th occupant",
                          f"{p} in D10 {SIGNS[tenth]}") for p in occupants]
        stmt += "; its 10th holds " + ", ".join(occupants)
    return tuple(pls), toks, stmt + "."


def _wealth_l1(ctx):
    targets = {ctx.lords[h] for h in (2, 5, 9, 11)}
    dhana_planets = {p for y in ctx.dhana for p in y.planets}
    targets |= dhana_planets
    wins = ctx.dasha_windows(targets)[:4]
    toks = frozenset().union(*(_window_years(w["start"], w["end"])
                               for w in wins)) if wins else frozenset()
    pls = tuple(Placement(
        f"{w['md']}–{w['ad']} period" + (" (running)" if w["running"] else ""),
        f"{_fmt_window(w)} — {', '.join(w['hit'])} rule(s) wealth houses")
        for w in wins)
    stmt = ("Dasha periods ruled by the 2/5/9/11 lords or Dhana-yoga "
            "planets: " + "; ".join(
                f"{w['md']}–{w['ad']} {_fmt_window(w)}" for w in wins)
            + ".") if wins else "No wealth-lord period within the horizon."
    return pls, toks, stmt


def _wealth_l2(ctx):
    lagna = ctx.chart.lagna.sign_index
    targets = {(lagna + 1) % 12, (lagna + 10) % 12}  # 2nd and 11th signs
    wins = []
    for start, end, sign in ctx.jupiter_periods():
        if sign in targets or set(aspected_signs("Jupiter", sign)) & targets:
            wins.append({"start": max(start, ctx.now), "end": end,
                         "sign": sign})
    wins = wins[:3]
    toks = frozenset().union(*(_window_years(w["start"], w["end"])
                               for w in wins)) if wins else frozenset()
    pls = tuple(Placement(
        f"Jupiter through {SIGNS[w['sign']]}",
        f"{w['start']:%b %Y} – {w['end']:%b %Y} — touches the 2nd/11th")
        for w in wins)
    stmt = ("Transit Jupiter reaches or aspects the wealth houses: "
            + "; ".join(f"{SIGNS[w['sign']]} {w['start']:%b %Y}–"
                        f"{w['end']:%b %Y}" for w in wins) + ".")
    return pls, toks, stmt


def _marriage_l1(ctx):
    targets = {ctx.lords[7], "Venus"}
    occupants = {p for p in PLANETS if ctx.chart.planets[p].house == 7}
    targets |= occupants
    wins = ctx.dasha_windows(targets)[:4]
    toks = frozenset().union(*(_window_years(w["start"], w["end"])
                               for w in wins)) if wins else frozenset()
    pls = tuple(Placement(
        f"{w['md']}–{w['ad']} period" + (" (running)" if w["running"] else ""),
        f"{_fmt_window(w)} — {', '.join(w['hit'])}: 7th lord, karaka or "
        "7th occupant")
        for w in wins)
    stmt = ("Periods of the 7th lord, Venus (karaka) or 7th-house "
            "occupants: " + "; ".join(
                f"{w['md']}–{w['ad']} {_fmt_window(w)}" for w in wins) + ".")
    return pls, toks, stmt


def _marriage_l2(ctx):
    lagna = ctx.chart.lagna.sign_index
    seventh = (lagna + 6) % 12
    wins = []
    for start, end, sign in ctx.jupiter_periods():
        if sign == seventh or seventh in aspected_signs("Jupiter", sign):
            wins.append({"start": max(start, ctx.now), "end": end,
                         "sign": sign})
    wins = wins[:3]
    toks = frozenset().union(*(_window_years(w["start"], w["end"])
                               for w in wins)) if wins else frozenset()
    pls = tuple(Placement(
        f"Jupiter through {SIGNS[w['sign']]}",
        f"{w['start']:%b %Y} – {w['end']:%b %Y} — reaches or aspects the "
        f"7th ({SIGNS[seventh]})") for w in wins)
    stmt = ("Transit Jupiter touching the 7th house: " + "; ".join(
        f"from {SIGNS[w['sign']]}, {w['start']:%b %Y}–{w['end']:%b %Y}"
        for w in wins) + ".") if wins else \
        "Jupiter does not touch the 7th within the horizon."
    return pls, toks, stmt


def _dasha_l1(ctx):
    cur = ctx.timeline.at(ctx.now)
    md = cur[0].lord
    pos = ctx.chart.planets[md]
    from yogas import houses_owned_by
    owned = houses_owned_by(ctx.chart, md)
    # The nodes rule no sign, so they own no house — the sentence has to
    # say that rather than leave a gap where the lordships would go.
    rules = (f"rules houses {' & '.join(map(str, owned))}" if owned
             else "rules no house — a shadow graha borrows from its "
                  "dispositor")
    return ((Placement("Mahadasha lord", ctx.placement_value(md)),),
            frozenset(DASHA_THEME[md].split(", ")),
            f"{md} {rules} and stands "
            f"in the {ordinal(pos.house)} — the era's theme: "
            f"{DASHA_THEME[md]}.")


def _dasha_l2(ctx):
    cur = ctx.timeline.at(ctx.now)
    ad = cur[1].lord
    pos = ctx.chart.planets[ad]
    return ((Placement("Antardasha lord", ctx.placement_value(ad)),),
            frozenset(DASHA_THEME[ad].split(", ")),
            f"{ad}'s antara (until {cur[1].end:%b %Y}) inflects it from "
            f"the {ordinal(pos.house)} house: {DASHA_THEME[ad]}.")


def _dasha_l3(ctx):
    cur = ctx.timeline.at(ctx.now)
    md, ad = cur[0].lord, cur[1].lord
    rel = natural_relation(md, ad)
    toks = (frozenset(DASHA_THEME[md].split(", "))
            | frozenset(DASHA_THEME[ad].split(", "))) \
        if rel != "enemy" else frozenset()
    return ((Placement("MD–AD relationship",
                       f"{md} regards {ad} as a natural {rel}"),),
            toks,
            f"{md} and {ad} are natural {rel}s — their agendas "
            + ("cooperate." if rel == "friend" else
               "coexist." if rel == "neutral" else
               "pull against each other; both themes run, in friction."))


REGISTRY: dict[str, Question] = {q.key: q for q in [
    Question(
        key="spouse-profession",
        text="What field might my spouse work in?",
        category="partnership",
        techniques=("7th lordship", "navamsa", "karaka"),
        answer_frame=("The strongest agreement ({pct}%) points toward "
                      "{modal} — carried by {carriers}."),
        lenses=(
            Lens("7th lord", "lordship",
                 "The 7th lord's nature describes the partner's vocation.",
                 0.40, "Moderate", _spouse_l1),
            Lens("Navamsa 7th", "varga",
                 "The D9's 7th house — occupants first, else its lord — "
                 "refines the partner picture.",
                 0.35, "Moderate", _spouse_l2),
            Lens("Venus karaka", "karaka",
                 "Venus as kalatra karaka signifies the partner by its "
                 "sign, house and dignity.",
                 0.25, "Interpretive", _spouse_l3),
        )),
    Question(
        key="career-field",
        text="What field suits my career?",
        category="career",
        techniques=("10th lordship", "occupancy", "dasamsa"),
        answer_frame=("The strongest agreement ({pct}%) points toward "
                      "{modal} — carried by {carriers}."),
        lenses=(
            Lens("10th lord", "lordship",
                 "The lord of the 10th describes the native's karma-field.",
                 0.35, "Moderate", _career_l1),
            Lens("10th occupants", "occupancy",
                 "Planets in the 10th impose their trades on the career.",
                 0.30, "Moderate", _career_l2),
            Lens("Dasamsa", "varga",
                 "The D10 lagna lord and D10 10th magnify the professional "
                 "signature.",
                 0.35, "Moderate", _career_l3),
        )),
    Question(
        key="wealth-timing",
        text="When do wealth-building periods open?",
        category="wealth",
        techniques=("vimshottari", "dhana lordship", "gocara"),
        answer_frame=("Dated windows with the strongest overlap ({pct}%): "
                      "{modal} — carried by {carriers}."),
        lenses=(
            Lens("Wealth-lord dashas", "vimshottari",
                 "Periods ruled by the lords of 2/5/9/11 or by Dhana-yoga "
                 "planets open earning windows.",
                 0.55, "Moderate", _wealth_l1),
            Lens("Jupiter to 2nd/11th", "gocara",
                 "Transit Jupiter reaching or aspecting the 2nd and 11th "
                 "marks accumulation seasons.",
                 0.45, "Interpretive", _wealth_l2),
        )),
    Question(
        key="marriage-timing",
        text="When are marriage-significant periods?",
        category="partnership",
        techniques=("vimshottari", "karaka", "gocara"),
        answer_frame=("Dated windows with the strongest overlap ({pct}%): "
                      "{modal} — carried by {carriers}."),
        lenses=(
            Lens("7th-connected dashas", "vimshottari",
                 "Periods of the 7th lord, Venus, or planets occupying the "
                 "7th activate partnership.",
                 0.55, "Moderate", _marriage_l1),
            Lens("Jupiter to the 7th", "gocara",
                 "Transit Jupiter reaching or aspecting the 7th house "
                 "traditionally times unions.",
                 0.45, "Moderate", _marriage_l2),
        )),
    Question(
        key="current-dasha",
        text="What are the themes of my current period?",
        category="timing",
        techniques=("vimshottari", "lordship", "naisargika maitri"),
        answer_frame=("The period's converging themes ({pct}%): {modal} — "
                      "carried by {carriers}."),
        lenses=(
            Lens("Mahadasha lord", "vimshottari",
                 "The mahadasha lord's placement and lordships set the "
                 "era's theme.",
                 0.45, "Moderate", _dasha_l1),
            Lens("Antardasha lord", "vimshottari",
                 "The antardasha lord inflects the running era from its "
                 "own seat.",
                 0.35, "Moderate", _dasha_l2),
            Lens("Lords' relationship", "maitri",
                 "The natural relationship between the two lords tells "
                 "whether their agendas cooperate.",
                 0.20, "Moderate", _dasha_l3),
        )),
]}
