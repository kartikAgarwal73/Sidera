"""The predicates — one per rule the resolver fires — and the signed table.

WHY THIS FILE EXISTS
The rule library says what the tradition reads a fact AS. Nothing in the
build said WHEN a rule applies to a chart: the model was handed the library
and trusted to fire the right ones, and the interim domain reading composed
its own signals with weights nobody had signed. A predicate is the missing
piece — for one rule id, read the one fact (or the few) the rule is about,
and either FIRE with the fact ids read and the values that decided it, or
stay silent, or say a fact is MISSING. Never guess, never compose.

THREE PROPERTIES, EACH GATED
  1. Every weight and confidence a finding carries comes from WEIGHTS, the
     table the owner signed on 2026-09-16, looked up by (rule, slot). A
     predicate cannot invent a number; `_finding()` refuses a pair the
     table does not hold.
  2. Dated findings never enter the balance. `period`, `live` and `window`
     are timing output — when a matter is in play, with the ledger's own
     dates — and `balance()` sums only `support` and `strain`. A transit
     contact at weight 3 cannot move a natal verdict.
  3. Every predicate declares the computation options it reads, so the
     resolver can re-run it under each answer of those options and report
     a split where the tradition splits (component 5).

Timing is windows the ledger already holds: dasha spans and transit spans
with their dates. No predicate here can produce a month the chart did not.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Callable

import math

import schools
import voice
from domains import DOMAINS, Domain
from explain import ordinal
from frames import FRAMES
from rulelib import KARAKATVAS, NATURAL_BENEFICS, RULES, house_words

NATURAL_MALEFICS = ("Sun", "Mars", "Saturn", "Rahu", "Ketu")
STRONG = ("exalted", "own sign", "moolatrikona")
WEAK = ("debilitated",)
SLOW_MOVERS = ("Saturn", "Jupiter", "Rahu", "Ketu")

# --- kinds --------------------------------------------------------------------

BALANCE_KINDS = ("support", "strain")      # the only two the verdict sums
TIMING_KINDS = ("period", "live", "window")  # dated; never summed
CITED = "cited"                             # read and named, weight 0
MISSING = "missing"                         # a fact the predicate needed
KINDS = BALANCE_KINDS + TIMING_KINDS + (CITED, MISSING)
CONFIDENCE = ("High", "Moderate", "Interpretive")
STEPS = ("NATAL", "KARAKA", "VARGA", "DASHA", "TRANSIT")


# --- the signed table -----------------------------------------------------------

@dataclass(frozen=True)
class Row:
    rule: str        # a rule id, or a family: rule.house.<h>, rule.transit.<slow>
    slot: str        # which case of the rule this row weighs
    kind: str
    weight: int
    confidence: str
    why: str         # the reason for the number, for the reader who argues

    def as_dict(self) -> dict:
        return asdict(self)


def _row(rule, slot, kind, weight, confidence, why) -> Row:
    return Row(rule, slot, kind, weight, confidence, why)


# Seeded from the derivation the owner approved: main house 3, supporting
# house 2, modifier 1, co-citation 0. High where the rule restates a dated
# or measured fact, Moderate for a classically sourced rule, Interpretive
# for a Sidera convention or a composed reading. Signed 2026-09-16 with two
# amendments: an empty varga house is cited, not a strain; dated rows are
# timing output only.
WEIGHTS: tuple[Row, ...] = (
    # NATAL — the houses through their lords and what looks at them
    _row("rule.house.<h>", "main_strong", "support", 3, "Moderate",
         "the main house's lord in dignity: the matter itself, eased"),
    _row("rule.house.<h>", "main_weak", "strain", 3, "Moderate",
         "the main house's lord debilitated: the matter itself, asking more"),
    _row("rule.house.<h>", "supporting_strong", "support", 2, "Moderate",
         "a supporting house's lord in dignity"),
    _row("rule.house.<h>", "supporting_weak", "strain", 2, "Moderate",
         "a supporting house's lord debilitated"),
    _row("rule.drishti.on_house", "benefic_main", "support", 2, "Moderate",
         "a natural benefic's drishti on the main house"),
    _row("rule.drishti.on_house", "benefic_supporting", "support", 1, "Moderate",
         "a natural benefic's drishti on a supporting house"),
    _row("rule.drishti.on_house", "malefic_main", "strain", 2, "Moderate",
         "a natural malefic's drishti on the main house; supporting houses "
         "are not weighed for it"),
    _row("rule.house.6_service", "lord_strong", "support", 2, "Moderate",
         "career only: the house of employment through its lord"),
    _row("rule.house.6_service", "lord_weak", "strain", 2, "Moderate",
         "career only: the house of employment through its lord"),
    _row("rule.house.6_service", "occupants", CITED, 0, "Moderate",
         "career only: what stands in the 6th is named; a malefic there is "
         "read two ways in the tradition (upachaya), so it is not weighed"),
    # KARAKA — the significator's own condition
    _row("rule.graha.karakatva", "primary_strong", "support", 3, "Moderate",
         "the primary natural karaka in dignity"),
    _row("rule.graha.karakatva", "primary_weak", "strain", 3, "Moderate",
         "the primary natural karaka debilitated"),
    _row("rule.graha.karakatva", "primary_hidden", "strain", 2, "Moderate",
         "the primary karaka in the 6th, 8th or 12th: its gifts arrive "
         "indirectly"),
    _row("rule.graha.karakatva", "primary_sound", "support", 1, "Moderate",
         "the primary karaka placed neither high nor low nor hidden"),
    _row("rule.graha.karakatva", "secondary_strong", "support", 1, "Moderate",
         "a secondary karaka in dignity"),
    _row("rule.graha.karakatva", "secondary_weak", "strain", 1, "Moderate",
         "a secondary karaka debilitated"),
    _row("rule.graha.karakatva", "secondary_hidden", "strain", 1, "Moderate",
         "a secondary karaka in a hidden house"),
    _row("rule.graha.karakatva", "secondary_sound", "support", 1, "Moderate",
         "a secondary karaka soundly placed"),
    _row("rule.karaka.by_sex", "set", CITED, 0, "Moderate",
         "which karaka is primary, and why — the owner said"),
    _row("rule.karaka.by_sex_unset", "unset", CITED, 0, "Interpretive",
         "which karaka is primary, and why — the owner has not said, so "
         "both are read, Venus first"),
    _row("rule.graha.combust", "main_lord", "strain", 2, "Moderate",
         "the main house's lord burnt: unable to deliver plainly"),
    _row("rule.graha.combust", "primary_karaka", "strain", 2, "Moderate",
         "the primary karaka burnt"),
    _row("rule.avastha.baladi", "main_lord", CITED, 0, "Interpretive",
         "read and named; never combined into the verdict "
         "(rule.avastha.independent)"),
    _row("rule.avastha.baladi", "primary_karaka", CITED, 0, "Interpretive",
         "read and named; never combined into the verdict"),
    _row("rule.avastha.jagradadi", "main_lord", CITED, 0, "Interpretive",
         "read and named; it restates dignity, which is already weighed"),
    _row("rule.avastha.jagradadi", "primary_karaka", CITED, 0, "Interpretive",
         "read and named; it restates dignity, which is already weighed"),
    _row("rule.karaka.darakaraka", "strong", "support", 2, "Moderate",
         "the chart's own spouse significator in dignity"),
    _row("rule.karaka.darakaraka", "weak", "strain", 2, "Moderate",
         "the chart's own spouse significator debilitated"),
    _row("rule.karaka.darakaraka", "hidden", "strain", 2, "Moderate",
         "the Darakaraka in the 6th, 8th or 12th"),
    _row("rule.karaka.darakaraka", "sound", "support", 1, "Moderate",
         "the Darakaraka soundly placed"),
    _row("rule.karaka.darakaraka", "strong_cited", "support", 1, "Moderate",
         "as strong, but its graha is already weighed as a natural karaka: "
         "one placement, one vote"),
    _row("rule.karaka.darakaraka", "weak_cited", "strain", 1, "Moderate",
         "as weak, but its graha is already weighed as a natural karaka"),
    _row("rule.karaka.darakaraka", "hidden_cited", "strain", 1, "Moderate",
         "as hidden, but its graha is already weighed as a natural karaka"),
    _row("rule.arudha.upapada_occupants", "malefic", "strain", 2, "Moderate",
         "a natural malefic on the Upapada asks more of the marriage"),
    _row("rule.arudha.upapada_occupants", "benefic", "support", 2, "Moderate",
         "a natural benefic on the Upapada supports it"),
    _row("rule.arudha.upapada_lord", "strong", "support", 2, "Moderate",
         "an empty Upapada whose lord stands in dignity"),
    _row("rule.arudha.upapada_lord", "weak", "strain", 2, "Moderate",
         "an empty Upapada whose lord is debilitated"),
    _row("rule.arudha.upapada_lord", "neutral", CITED, 0, "Moderate",
         "an empty Upapada whose lord is neither: named, not weighed"),
    _row("rule.arudha.second_from_upapada", "support", "support", 1, "Moderate",
         "the marriage's durability: a benefic in the 2nd from the Upapada, "
         "or its lord in dignity"),
    _row("rule.arudha.second_from_upapada", "strain", "strain", 1, "Moderate",
         "the marriage's durability: a malefic there, or its lord debilitated"),
    _row("rule.arudha.second_from_upapada", "neutral", CITED, 0, "Moderate",
         "the 2nd from the Upapada, named"),
    _row("rule.dosha.mangal", "active", "strain", 2, "Moderate",
         "Mangal dosha formed and standing after its checks"),
    _row("rule.dosha.mangal_cancelled", "cancelled", CITED, 0, "Moderate",
         "formed, and cancelled: cited with what cancelled it, not dropped"),
    _row("rule.dosha.mangal", "not_formed", CITED, 0, "Moderate",
         "the pattern does not form; said, so the reader is not left to ask"),
    # VARGA — does the promise carry?
    _row("rule.varga.confirms", "benefic", "support", 2, "Interpretive",
         "a natural benefic in the domain house of its varga"),
    _row("rule.varga.confirms", "malefic", "strain", 2, "Interpretive",
         "a natural malefic in the domain house of its varga"),
    _row("rule.varga.confirms", "empty", CITED, 0, "Interpretive",
         "an empty varga house is named, not a strain (owner's amendment): "
         "its lord's condition is read by rule.varga.from_varga_lagna"),
    _row("rule.varga.from_varga_lagna", "strong", "support", 1, "Interpretive",
         "the main lord in dignity in the varga, by the degree convention"),
    _row("rule.varga.from_varga_lagna", "weak", "strain", 1, "Interpretive",
         "the main lord debilitated in the varga, by the degree convention"),
    _row("rule.varga.from_varga_lagna", "neutral", CITED, 0, "Interpretive",
         "where the main lord sits in the varga, named"),
    _row("rule.varga.vargottama", "main_lord", "support", 2, "High",
         "the rule's own statement: the two charts agree about it"),
    _row("rule.vimsopaka.bala", "strong", "support", 2, "Moderate",
         "the main lord strong across the group of divisions"),
    _row("rule.vimsopaka.bala", "thin", "strain", 2, "Moderate",
         "the main lord thin across the group"),
    _row("rule.vimsopaka.bala", "middling", CITED, 0, "Moderate",
         "a middling score is a fact about the lord, not an argument"),
    # DASHA — is this what the period is about?
    _row("rule.dasha.lordship", "md", "period", 3, "High",
         "the running mahadasha lord rules or sits in a domain house; the "
         "dates are the ledger's"),
    _row("rule.dasha.lordship", "ad", "period", 2, "High",
         "the running antardasha lord rules or sits in a domain house"),
    _row("rule.dasha.lordship", "window_running", "window", 2, "High",
         "a dated window, running now, whose lord bears on the domain"),
    _row("rule.dasha.lordship", "window_upcoming", "window", 1, "High",
         "a dated window ahead, inside the horizon"),
    _row("rule.career.employment_period", "window_running", "window", 2, "High",
         "a running period of the 6th or 10th lord"),
    _row("rule.career.employment_period", "window_upcoming", "window", 1, "High",
         "a period of the 6th or 10th lord ahead, inside the horizon"),
    # TRANSIT — the slow movers, by occupation and by drishti, dated
    _row("rule.transit.<slow>", "on", "live", 2, "Moderate",
         "a slow mover in a domain house, until the ledger's date"),
    _row("rule.transit.<slow>", "aspecting", "live", 1, "Moderate",
         "a slow mover's drishti on a domain house, until the ledger's date"),
    _row("rule.transit.contact", "contact", "live", 3, "High",
         "a transit within orb of a domain lord, karaka or occupant: the "
         "sharpest fact in the ledger, and it outranks the from-the-Moon "
         "verdict"),
    _row("rule.transit.node_on_natal", "contact", "live", 3, "High",
         "a node on a domain lord, karaka or occupant: an eclipse of it"),
    _row("rule.transit.<slow>", "window", "window", 1, "Moderate",
         "Jupiter or Saturn reaching or aspecting the main house, ahead, "
         "inside the horizon"),
)

_FAMILY_HOUSE = re.compile(r"^rule\.house\.\d+$")
_FAMILY_SLOW = re.compile(r"^rule\.transit\.(saturn|jupiter|rahu|ketu)$")


def family(rule_id: str) -> str:
    """The table key a rule id is weighed under."""
    if _FAMILY_HOUSE.match(rule_id):
        return "rule.house.<h>"
    if _FAMILY_SLOW.match(rule_id):
        return "rule.transit.<slow>"
    return rule_id


_TABLE: dict[tuple[str, str], Row] = {(r.rule, r.slot): r for r in WEIGHTS}


def row(rule_id: str, slot: str) -> Row:
    """The signed row for a (rule, slot). KeyError is a programming error:
    a predicate asked for a weight the owner never signed."""
    return _TABLE[(family(rule_id), slot)]


def balance(findings) -> tuple[str, str]:
    """(technical label, plain verdict clause) from support and strain ONLY.

    The thresholds are the interim reading's, unchanged. Timing kinds are
    excluded by kind, not by weight — a live finding at weight 3 is timing
    output and cannot move this."""
    up = sum(f.weight for f in findings if f.kind == "support")
    down = sum(f.weight for f in findings if f.kind == "strain")
    if up >= down * 2 and up:
        return "Well supported", "runs strong"
    if down >= up * 2 and down:
        return "Asks real work", "asks real work"
    if up > down:
        return "Mixed", "leans your way"
    if down > up:
        return "Mixed", "runs uphill"
    return "Mixed", "cuts both ways"


# --- findings -------------------------------------------------------------------

@dataclass(frozen=True)
class Finding:
    """One rule, fired on one chart: what it read and what it decided.

    Three registers of the same reason, as the interim signals carried:
    `text` for the expander (Sanskrit and house numbers allowed), `brief`
    for a label, `plain` for the top layer (no Sanskrit, no house numbers;
    empty means "stays in the expander"). `values` is what the predicate
    read, so a re-run under another school can be compared value for
    value. `start`/`end` are ISO dates for the dated kinds only."""

    rule_id: str
    slot: str
    kind: str
    weight: int
    confidence: str
    step: str
    fact_ids: tuple[str, ...]
    text: str
    brief: str = ""
    plain: str = ""
    also: tuple[str, ...] = ()            # co-cited rule ids
    values: dict = field(default_factory=dict)
    start: str | None = None
    end: str | None = None
    reads_options: tuple[str, ...] = ()
    #: The ONE frame this finding is attributed to (frames.FRAMES), set by
    #: the resolver from its predicate's declaration — "" until then. A
    #: finding counts in one frame only, so a rule that reads two frames
    #: cannot vote twice.
    frame: str = ""

    def as_dict(self) -> dict:
        return asdict(self)


def _finding(rule_id, slot, *, step, fact_ids, text, brief="", plain="",
             also=(), values=None, start=None, end=None,
             reads_options=()) -> Finding:
    r = row(rule_id, slot)
    if r.kind in TIMING_KINDS:
        assert start or end, f"{rule_id}/{slot} is dated and carries no date"
    else:
        assert start is None and end is None, (
            f"{rule_id}/{slot} is not a timing row and carries a date")
    return Finding(rule_id=rule_id, slot=slot, kind=r.kind, weight=r.weight,
                   confidence=r.confidence, step=step,
                   fact_ids=tuple(fact_ids), text=text, brief=brief,
                   plain=plain, also=tuple(also), values=dict(values or {}),
                   start=start, end=end, reads_options=tuple(reads_options))


def _missing(rule_id, step, fact_id, reads_options=()) -> Finding:
    return Finding(rule_id=rule_id, slot="missing", kind=MISSING, weight=0,
                   confidence="Interpretive", step=step, fact_ids=(fact_id,),
                   text=f"{rule_id} could not be evaluated: the ledger has "
                        f"no fact {fact_id}",
                   brief=f"{fact_id} missing", plain="",
                   values={"missing": fact_id},
                   reads_options=tuple(reads_options))


# --- the frame verdict: the C3-c rows -------------------------------------------
#
# A SECOND SIGNED TABLE, beside WEIGHTS and never inside it (WEIGHTS is
# pinned row for row). These rows weigh FRAMES, not findings: each frame
# with weighed findings has a polarity, and the rows say what the frames
# together amount to. Signed 2026-09-19 against the owner's C3-c: a
# majority of frames favourable is favourable WITH the disagreeing frames
# always named; a tie is a split the narrator never resolves.

@dataclass(frozen=True)
class FrameRow:
    id: str
    when: str        # the condition, in words
    result: str      # what the row yields
    why: str

    def as_dict(self) -> dict:
        return asdict(self)


VERDICTS = ("favourable", "unfavourable", "split", "undecided")

FRAME_VERDICT: tuple[FrameRow, ...] = (
    FrameRow("frame.polarity",
             "support > strain → favourable; strain > support → "
             "unfavourable; equal and not zero → mixed; no weighed finding "
             "→ no polarity",
             "one polarity per frame, from that frame's own findings",
             "a frame votes with the findings attributed to it and nothing "
             "else; cited findings weigh 0 and give no polarity"),
    FrameRow("frame.count",
             "n = the frames with a polarity (favourable, unfavourable or "
             "mixed); silent frames and dated-only frames are not in n",
             "n",
             "a frame that said nothing cannot vote; a frame that only "
             "dated something never enters a natal verdict (the owner's "
             "amendment that dated rows are timing output)"),
    FrameRow("frame.favourable",
             "favourable ≥ ceil(n/2) and favourable > unfavourable",
             "verdict favourable; disagreement = every frame in n whose "
             "polarity is not favourable, always emitted, [] when empty",
             "the owner's C3-c row; the strict second clause is what "
             "sends an even tie to the split row"),
    FrameRow("frame.unfavourable",
             "unfavourable ≥ ceil(n/2) and unfavourable > favourable",
             "verdict unfavourable; disagreement = every frame in n whose "
             "polarity is not unfavourable",
             "the mirror of the favourable row"),
    FrameRow("frame.split",
             "neither majority row holds, and at least one frame took a "
             "side — an even tie, or mixed frames that deny either side a "
             "majority",
             "verdict split; disagreement = every frame in n, both sides "
             "named; the narrator never resolves it",
             "the owner's C3-c: ties → split. Mixed frames count in n "
             "because they spoke, so one favourable frame among mixed "
             "ones is not a verdict"),
    FrameRow("frame.undecided",
             "n = 0, or every frame in n is mixed",
             "verdict undecided; disagreement = the mixed frames, [] when "
             "nothing weighed",
             "no frame took a side: the reading says so rather than "
             "inventing one. A lone mixed frame is not a split — a split "
             "needs two sides"),
    FrameRow("frame.timing",
             "a dated frame is in_play when a window or period is running "
             "at the moment read, quiet when it holds dated windows and "
             "none is running, silent when it holds none",
             "dasha and transit carry in_play / quiet / silent, never a "
             "polarity; two dated frames that differ are a split",
             "timing is when, not whether; mapping in_play to favourable "
             "would let the majority row call a running Saturn a verdict"),
)


def frame_polarity(support: int, strain: int) -> str | None:
    if support == 0 and strain == 0:
        return None
    if support > strain:
        return "favourable"
    if strain > support:
        return "unfavourable"
    return "mixed"


def frame_verdict(polarities: dict) -> tuple[str, list[str]]:
    """(verdict, disagreement) from {frame: polarity | None}, exactly the
    FRAME_VERDICT rows. `disagreement` is always a list, [] when empty."""
    voting = {f: p for f, p in polarities.items() if p is not None}
    n = len(voting)
    fav = sorted(f for f, p in voting.items() if p == "favourable")
    unf = sorted(f for f, p in voting.items() if p == "unfavourable")
    if not fav and not unf:
        return "undecided", sorted(voting)
    need = math.ceil(n / 2)
    if len(fav) >= need and len(fav) > len(unf):
        return "favourable", sorted(f for f in voting if f not in fav)
    if len(unf) >= need and len(unf) > len(fav):
        return "unfavourable", sorted(f for f in voting if f not in unf)
    return "split", sorted(voting)


def timing_status(findings) -> str:
    """in_play | quiet | silent for one dated frame's findings."""
    dated = [f for f in findings if f.kind in TIMING_KINDS]
    if not dated:
        return "silent"
    running = [f for f in dated
               if f.kind in ("period", "live") or f.slot == "window_running"
               or f.values.get("running")]
    return "in_play" if running else "quiet"


# --- the register --------------------------------------------------------------

@dataclass(frozen=True)
class Predicate:
    rule_id: str
    step: str
    reads_options: tuple[str, ...]
    domains: tuple[str, ...] | None       # None: every domain
    fn: Callable
    #: The frame this predicate's findings are attributed to: one of
    #: frames.FRAMES, or "varga" — resolved by the resolver to the rule
    #: set's testing division — or None for a predicate that only cites
    #: (its findings weigh nothing and belong to no frame's vote).
    frame: str | None = None

    def frame_for(self, varga: str) -> str | None:
        if self.frame == "varga":
            return varga.lower()
        return self.frame


PREDICATES: list[Predicate] = []


def predicate(rule_id: str, step: str, options=(), domains=None, frame=None):
    assert step in STEPS, step
    assert frame is None or frame == "varga" or frame in FRAMES, frame
    for o in options:
        assert o in schools.OPTIONS, o

    def wrap(fn):
        PREDICATES.append(Predicate(rule_id, step, tuple(options),
                                    tuple(domains) if domains else None, fn,
                                    frame))
        return fn
    return wrap


# --- the context a predicate reads ------------------------------------------

_HIDDEN = (6, 8, 12)


class Ctx:
    """One chart's ledger, one domain, one moment — what every predicate
    reads. Facts are read by id; a missing id raises KeyError, which
    `evaluate()` turns into a MISSING finding."""

    def __init__(self, domain: Domain, facts: dict, when: datetime):
        self.domain = domain
        self.facts = facts
        self.when = when

    def v(self, fact_id: str) -> dict:
        return self.facts[fact_id].value

    @property
    def main(self) -> int:
        return self.domain.main_house

    def lord(self, house: int) -> str:
        return self.v(f"natal.{house}L")["lord"]

    @property
    def main_lord(self) -> str:
        return self.lord(self.main)

    @property
    def lords(self) -> list[str]:
        out = []
        for h in self.domain.houses:
            if self.lord(h) not in out:
                out.append(self.lord(h))
        return out

    @property
    def primary_karaka(self) -> str:
        if self.domain.id == "marriage":
            return self.v("karaka.spouse")["primary"]
        return self.domain.karakas[0]

    @property
    def secondary_karakas(self) -> tuple[str, ...]:
        if self.domain.id == "marriage":
            return (self.v("karaka.spouse")["secondary"],)
        return tuple(self.domain.karakas[1:2])

    @property
    def karakas(self) -> tuple[str, ...]:
        return (self.primary_karaka,) + self.secondary_karakas

    def matters(self, house: int) -> str:
        return _matters(self.domain.why.get(house, house_words(house)))


def _matters(why: str) -> str:
    for prefix in ("the house of ", "the 2nd from the 7th: "):
        if why.startswith(prefix):
            trimmed = why[len(prefix):]
            return re.sub(r"^(.*?), and of ", r"\1, and ", trimmed)
    return why


def _dignity(v: dict) -> str:
    d = v.get("lord_dignity") or v.get("dignity") or ""
    return (d or "").split(" (")[0].strip()


def _is_strong(d: str) -> bool:
    return any(x in d for x in STRONG)


def _is_weak(d: str) -> bool:
    return any(x in d for x in WEAK)


def _dignity_phrase(d: str) -> str:
    return f"in its {d}" if d in ("own sign", "moolatrikona") else d


PLAIN_DIGNITY = {"exalted": "exalted", "own sign": "in its own sign",
                 "moolatrikona": "in its best sign",
                 "debilitated": "at its weakest", "neutral": "neutrally placed"}


def _plain_dignity(d: str) -> str:
    return PLAIN_DIGNITY.get(d, d)


def _p(name: str) -> str:
    return voice.plain(name)


def _and(items) -> str:
    items = list(items)
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + " and " + items[-1]


def _ps(names) -> str:
    return _and(_p(n) for n in names)


def _year(iso: str | None) -> str:
    if not iso:
        return "its end"
    try:
        return datetime.fromisoformat(iso).strftime("%b %Y")
    except ValueError:
        return "its end"


def _iso_date(iso: str | None) -> str | None:
    return iso[:10] if iso else None


# --- NATAL ---------------------------------------------------------------------

@predicate("rule.house.<h>", "NATAL", frame="lagna")
def house_lord_dignity(ctx: Ctx) -> list[Finding]:
    out = []
    for h in ctx.domain.houses:
        if ctx.domain.id == "career" and h == 6:
            continue                     # weighed once, by rule.house.6_service
        v = ctx.v(f"natal.{h}L")
        d = _dignity(v)
        main = h == ctx.main
        if _is_strong(d):
            slot, tail = (("main_strong" if main else "supporting_strong"),
                          "so those matters arrive with less friction")
        elif _is_weak(d):
            slot, tail = (("main_weak" if main else "supporting_weak"),
                          "so the same matters ask more effort of you than "
                          "they would otherwise")
        else:
            continue
        lord = v["lord"]
        out.append(_finding(
            f"rule.house.{h}", slot, step="NATAL",
            fact_ids=(f"natal.{h}L", f"house.{h}"),
            text=(f"the {ordinal(h)} house — {ctx.matters(h)} — has its lord "
                  f"{lord} {_dignity_phrase(d)}, {tail}"),
            brief=f"a {'strong' if _is_strong(d) else d} {ordinal(h)} lord",
            plain=(f"{_p(lord)} rules it and sits {_plain_dignity(d)}"
                   if main else ""),
            also=("rule.dasha.dignity",),
            values={"house": h, "lord": lord, "dignity": d}))
    return out


@predicate("rule.drishti.on_house", "NATAL",
           options=("node_reach", "node_position"), frame="lagna")
def drishti_on_house(ctx: Ctx) -> list[Finding]:
    out = []
    for h in ctx.domain.houses:
        v = ctx.v(f"natal.{h}L")
        main = h == ctx.main
        onto = list(v["aspected_by"])
        benefics = [p for p in onto if p in NATURAL_BENEFICS]
        malefics = [p for p in onto if p in NATURAL_MALEFICS]
        ids = (f"natal.{h}L", f"house.{h}")
        if benefics:
            n = len(benefics)
            out.append(_finding(
                "rule.drishti.on_house",
                "benefic_main" if main else "benefic_supporting",
                step="NATAL", fact_ids=ids,
                text=(f"{_and(benefics)} {'casts' if n == 1 else 'cast'} "
                      f"drishti onto the {ordinal(h)} house, which the "
                      f"tradition reads as protection over {ctx.matters(h)}"),
                brief=f"{_and(benefics)} {'protects' if n == 1 else 'protect'} "
                      f"the {ordinal(h)}",
                plain=(f"{_ps(benefics)} {'protects' if n == 1 else 'protect'} it"
                       if main else ""),
                also=(f"rule.house.{h}", "rule.graha.nature"),
                values={"house": h, "benefics": benefics},
                reads_options=("node_reach", "node_position")))
        if malefics and main:
            n = len(malefics)
            out.append(_finding(
                "rule.drishti.on_house", "malefic_main", step="NATAL",
                fact_ids=ids,
                text=(f"{_and(malefics)} {'aspects' if n == 1 else 'aspect'} "
                      f"the {ordinal(h)} house too, which classically presses "
                      f"on the matter rather than easing it"),
                brief=f"{_and(malefics)} {'presses' if n == 1 else 'press'} on "
                      f"the {ordinal(h)}",
                plain=f"{_ps(malefics)} {'presses' if n == 1 else 'press'} on it",
                also=(f"rule.house.{h}", "rule.graha.nature"),
                values={"house": h, "malefics": malefics},
                reads_options=("node_reach", "node_position")))
    return out


@predicate("rule.house.6_service", "NATAL", domains=("career",),
           frame="lagna")
def sixth_as_employment(ctx: Ctx) -> list[Finding]:
    v = ctx.v("natal.6L")
    d = _dignity(v)
    lord = v["lord"]
    out = []
    if _is_strong(d) or _is_weak(d):
        slot = "lord_strong" if _is_strong(d) else "lord_weak"
        out.append(_finding(
            "rule.house.6_service", slot, step="NATAL",
            fact_ids=("natal.6L", "house.6"),
            text=(f"the 6th house — service, employment in the plain sense — "
                  f"has its lord {lord} {_dignity_phrase(d)}, so the holding "
                  f"and keeping of a job "
                  + ("comes with less friction" if _is_strong(d)
                     else "asks more effort")),
            brief=f"a {'strong' if _is_strong(d) else d} 6th lord",
            plain=(f"{_p(lord)}, which rules the part of your chart that "
                   f"holds employment, sits {_plain_dignity(d)}"),
            also=("rule.house.6",),
            values={"lord": lord, "dignity": d}))
    occupants = list(v["occupants"])
    if occupants:
        out.append(_finding(
            "rule.house.6_service", "occupants", step="NATAL",
            fact_ids=("house.6",),
            text=(f"{_and(occupants)} {'stands' if len(occupants) == 1 else 'stand'} "
                  f"in the 6th, the house of employment — named here, not "
                  f"weighed, because a malefic in the 6th is read two ways"),
            brief=f"{_and(occupants)} in the 6th",
            also=("rule.house.6",),
            values={"occupants": occupants}))
    return out


# --- KARAKA --------------------------------------------------------------------

def _karaka_finding(ctx: Ctx, name: str, primary: bool) -> Finding:
    v = ctx.v(f"karaka.{name.lower()}")
    d = _dignity(v)
    gloss = KARAKATVAS[name].split(",")[0]
    where = (f"{name}, which naturally signifies {gloss} here, sits in your "
             f"{ordinal(v['house'])} house")
    who = f"{_p(name)}, the planet of {gloss},"
    tier = "primary" if primary else "secondary"
    ids = (f"karaka.{name.lower()}",)
    if _is_strong(d):
        return _finding("rule.graha.karakatva", f"{tier}_strong", step="KARAKA",
                        fact_ids=ids,
                        text=f"{where} and is {_dignity_phrase(d)}",
                        brief=f"{name} strong",
                        plain=f"{who} sits {_plain_dignity(d)}" if primary else "",
                        values={"karaka": name, "dignity": d, "house": v["house"]})
    if _is_weak(d):
        return _finding("rule.graha.karakatva", f"{tier}_weak", step="KARAKA",
                        fact_ids=ids,
                        text=f"{where} but is {_dignity_phrase(d)}",
                        brief=f"{name} debilitated",
                        plain=f"{who} sits {_plain_dignity(d)}" if primary else "",
                        values={"karaka": name, "dignity": d, "house": v["house"]})
    if v["house"] in _HIDDEN:
        return _finding("rule.graha.karakatva", f"{tier}_hidden", step="KARAKA",
                        fact_ids=ids,
                        text=(f"{where} — one of the three houses the tradition "
                              f"reads as hidden or costly, so its gifts arrive "
                              f"indirectly"),
                        brief=f"{name} tucked in the {ordinal(v['house'])}",
                        plain=f"{who} sits somewhere hidden" if primary else "",
                        also=(f"rule.house.{v['house']}",),
                        values={"karaka": name, "dignity": d, "house": v["house"]})
    return _finding("rule.graha.karakatva", f"{tier}_sound", step="KARAKA",
                    fact_ids=ids, text=where, brief=f"{name} soundly placed",
                    plain=f"{who} is soundly placed" if primary else "",
                    values={"karaka": name, "dignity": d, "house": v["house"]})


@predicate("rule.graha.karakatva", "KARAKA", frame="lagna")
def karaka_condition(ctx: Ctx) -> list[Finding]:
    out = [_karaka_finding(ctx, ctx.primary_karaka, True)]
    out += [_karaka_finding(ctx, k, False) for k in ctx.secondary_karakas]
    return out


@predicate("rule.karaka.by_sex_unset", "KARAKA", domains=("marriage",))  # cites only: no frame
def spouse_karaka_convention(ctx: Ctx) -> list[Finding]:
    v = ctx.v("karaka.spouse")
    if v["basis"] == "unset":
        return [_finding(
            "rule.karaka.by_sex_unset", "unset", step="KARAKA",
            fact_ids=("karaka.spouse",),
            text=("the spouse's natural significator is read as both Venus "
                  "and Jupiter, Venus first: the chart's owner has not said, "
                  "and Sidera's convention is to read both"),
            brief="spouse karaka: both, by convention",
            also=("rule.karaka.by_sex",),
            values={"primary": v["primary"], "secondary": v["secondary"],
                    "basis": "unset"})]
    return [_finding(
        "rule.karaka.by_sex", "set", step="KARAKA",
        fact_ids=("karaka.spouse",),
        text=(f"the spouse's natural significator is {v['primary']} here, "
              f"with {v['secondary']} read second, because the chart's owner "
              f"said so"),
        brief=f"spouse karaka: {v['primary']}",
        values={"primary": v["primary"], "secondary": v["secondary"],
                "basis": v["basis"]})]


@predicate("rule.graha.combust", "KARAKA", frame="lagna")
def combust(ctx: Ctx) -> list[Finding]:
    out = []
    for slot, name, fid in (("main_lord", ctx.main_lord,
                             f"planet.{ctx.main_lord.lower()}"),
                            ("primary_karaka", ctx.primary_karaka,
                             f"karaka.{ctx.primary_karaka.lower()}")):
        v = ctx.v(fid)
        if not v["combust"]:
            continue
        role = (f"lord of your {ordinal(ctx.main)}" if slot == "main_lord"
                else f"the natural significator here")
        out.append(_finding(
            "rule.graha.combust", slot, step="KARAKA", fact_ids=(fid,),
            text=(f"{name}, {role}, is combust — {v['sun_distance']}° from "
                  f"the Sun inside its {v['combust_orb']:g}° orb — and is "
                  f"read as unable to deliver its own results plainly"),
            brief=f"{name} combust",
            plain=(f"{_p(name)}, which "
                   + ("rules it" if slot == "main_lord" else "stands for it")
                   + ", sits burnt beside the Sun"),
            values={"planet": name, "sun_distance": v["sun_distance"],
                    "orb": v["combust_orb"]}))
    return out


def _avastha(ctx: Ctx, rule_id: str, slot: str, name: str) -> Finding | None:
    fid = f"avastha.{name.lower()}"
    if fid not in ctx.facts:                 # the nodes take no avastha
        return None
    v = ctx.v(fid)
    if rule_id.endswith("baladi"):
        text = (f"{name} is {v['baladi_name']} by degree — "
                f"{v['baladi_sense']}")
        brief = f"{name} {v['baladi_name']} by degree"
        vals = {"planet": name, "baladi": v["baladi"]}
    else:
        text = (f"{name} is {v['jagradadi_name']} by dignity — "
                f"{v['jagradadi_sense']}")
        brief = f"{name} {v['jagradadi_name']} by dignity"
        vals = {"planet": name, "jagradadi": v["jagradadi"]}
    return _finding(rule_id, slot, step="KARAKA", fact_ids=(fid,),
                    text=text, brief=brief,
                    also=("rule.avastha.independent",), values=vals)


@predicate("rule.avastha.baladi", "KARAKA", frame="lagna")
def avastha_baladi(ctx: Ctx) -> list[Finding]:
    out = [_avastha(ctx, "rule.avastha.baladi", "main_lord", ctx.main_lord),
           _avastha(ctx, "rule.avastha.baladi", "primary_karaka",
                    ctx.primary_karaka)]
    return [f for f in out if f]


@predicate("rule.avastha.jagradadi", "KARAKA", frame="lagna")
def avastha_jagradadi(ctx: Ctx) -> list[Finding]:
    out = [_avastha(ctx, "rule.avastha.jagradadi", "main_lord", ctx.main_lord),
           _avastha(ctx, "rule.avastha.jagradadi", "primary_karaka",
                    ctx.primary_karaka)]
    return [f for f in out if f]


@predicate("rule.karaka.darakaraka", "KARAKA", options=("karaka_count",),
           domains=("marriage",), frame="jaimini")
def darakaraka(ctx: Ctx) -> list[Finding]:
    v = ctx.v("karaka.chara.darakaraka")
    dk = v["planet"]
    d = _dignity(v)
    # ONE PLACEMENT, ONE VOTE: when the Darakaraka is also a natural karaka
    # already weighed by rule.graha.karakatva, its office adds a citation
    # at half the weight, not a second full vote for the same graha.
    already = dk in ctx.karakas
    ids = ("karaka.chara.darakaraka",)
    where = (f"{dk} is the Darakaraka, the chart's own significator of the "
             f"spouse, in {v['sign']} in the {ordinal(v['house'])} house")
    who = f"{_p(dk)}, which stands for the spouse here,"
    if _is_strong(d):
        base, text = "strong", f"{where}, {_dignity_phrase(d)}"
        plain = f"{who} sits {_plain_dignity(d)}"
    elif _is_weak(d):
        base, text = "weak", f"{where}, {_dignity_phrase(d)}"
        plain = f"{who} sits {_plain_dignity(d)}"
    elif v["house"] in _HIDDEN:
        base = "hidden"
        text = f"{where} — a hidden house, so what it gives arrives indirectly"
        plain = f"{who} sits somewhere hidden"
    else:
        base, text, plain = "sound", f"{where}, soundly placed", ""
    slot = f"{base}_cited" if (already and base != "sound") else base
    return [_finding("rule.karaka.darakaraka", slot, step="KARAKA",
                     fact_ids=ids, text=text,
                     brief=f"Darakaraka {dk} {base}", plain=plain,
                     also=("rule.karaka.chara",),
                     values={"darakaraka": dk, "dignity": d,
                             "house": v["house"], "already_cited": already},
                     reads_options=("karaka_count",))]


@predicate("rule.arudha.upapada_occupants", "NATAL",
           options=("dual_lord", "node_position"), domains=("marriage",),
           frame="jaimini")
def upapada_occupants(ctx: Ctx) -> list[Finding]:
    v = ctx.v("arudha.upapada")
    occupants = list(v["occupants"])
    if not occupants:
        return []
    malefics = [p for p in occupants if p in NATURAL_MALEFICS]
    benefics = [p for p in occupants if p in NATURAL_BENEFICS]
    face = "the marriage's public face"
    out = []
    for slot, group in (("malefic", malefics), ("benefic", benefics)):
        if not group:
            continue
        out.append(_finding(
            "rule.arudha.upapada_occupants", slot, step="NATAL",
            fact_ids=("arudha.upapada",),
            text=(f"the Upapada — A12, the arudha of the 12th, read for "
                  f"marriage and for the spouse — is {v['sign']} with "
                  f"{_and(group)} on it, which "
                  + ("asks more of the marriage" if slot == "malefic"
                     else "supports it")),
            brief=f"Upapada in {v['sign']} with {_and(group)}",
            plain=f"{face} falls in {v['sign']}, with {_ps(group)} on it",
            also=("rule.arudha.pada", "rule.arudha.upapada"),
            values={"sign": v["sign"], "occupants": occupants, "group": group},
            reads_options=("dual_lord", "node_position")))
    return out


@predicate("rule.arudha.upapada_lord", "NATAL", options=("dual_lord",),
           domains=("marriage",), frame="jaimini")
def upapada_lord(ctx: Ctx) -> list[Finding]:
    v = ctx.v("arudha.upapada")
    if v["occupants"]:
        return []
    lord = v["lord"]
    d = _dignity(ctx.v(f"karaka.{lord.lower()}"))
    slot = "strong" if _is_strong(d) else "weak" if _is_weak(d) else "neutral"
    face = "the marriage's public face"
    return [_finding(
        "rule.arudha.upapada_lord", slot, step="NATAL",
        fact_ids=("arudha.upapada", f"karaka.{lord.lower()}"),
        text=(f"the Upapada is {v['sign']} with no graha on it, so its lord "
              f"{lord} speaks for the marriage"
              + (f" — {_dignity_phrase(d)}" if slot != "neutral" else "")),
        brief=f"Upapada in {v['sign']}, lord {lord}"
              + (f" {d}" if slot != "neutral" else ""),
        plain=(f"{face} falls in {v['sign']}, and {_p(lord)}, which rules it, "
               f"sits {_plain_dignity(d)}" if slot != "neutral" else ""),
        also=("rule.arudha.pada", "rule.arudha.upapada"),
        values={"sign": v["sign"], "lord": lord, "dignity": d},
        reads_options=("dual_lord",))]


@predicate("rule.arudha.second_from_upapada", "NATAL", options=("dual_lord",),
           domains=("marriage",), frame="jaimini")
def upapada_second(ctx: Ctx) -> list[Finding]:
    v = ctx.v("arudha.upapada_2nd")
    d = (v.get("lord_dignity") or "").split(" (")[0]
    benefics = [p for p in v["occupants"] if p in NATURAL_BENEFICS]
    malefics = [p for p in v["occupants"] if p in NATURAL_MALEFICS]
    if malefics or _is_weak(d):
        slot = "strain"
    elif benefics or _is_strong(d):
        slot = "support"
    else:
        slot = "neutral"
    reason = (f"{_and(malefics)} in it" if malefics else
              f"its lord {v['lord']} {_dignity_phrase(d)}" if _is_weak(d) else
              f"{_and(benefics)} in it" if benefics else
              f"its lord {v['lord']} {_dignity_phrase(d)}" if _is_strong(d) else
              f"its lord {v['lord']} in {v['lord_sign']}")
    return [_finding(
        "rule.arudha.second_from_upapada", slot, step="NATAL",
        fact_ids=("arudha.upapada_2nd",),
        text=(f"the 2nd from the Upapada, read for the durability of the "
              f"marriage, is {v['sign']} with {reason}"),
        brief=f"2nd from Upapada: {v['sign']}, {reason}",
        plain=("" if slot == "neutral" else
               f"what keeps the marriage going "
               + ("is under pressure" if slot == "strain" else "holds up")
               + f", with {_ps(malefics or benefics) if (malefics or benefics) else _p(v['lord'])} "
               + ("on it" if (malefics or benefics) else f"ruling it {_plain_dignity(d)}")),
        also=("rule.arudha.pada",),
        values={"sign": v["sign"], "occupants": v["occupants"],
                "lord": v["lord"], "lord_dignity": d},
        reads_options=("dual_lord",))]


@predicate("rule.dosha.mangal", "NATAL", domains=("marriage",), frame="lagna")
def mangal(ctx: Ctx) -> list[Finding]:
    v = ctx.v("dosha.mangal-dosha")
    ids = ("dosha.mangal-dosha", "planet.mars")
    mars = ctx.v("planet.mars")
    if not v["formed"]:
        return [_finding("rule.dosha.mangal", "not_formed", step="NATAL",
                         fact_ids=ids,
                         text=(f"Mangal dosha does not form: Mars stands in "
                               f"the {ordinal(mars['house'])} house"),
                         brief="no Mangal dosha",
                         values={"formed": False, "house": mars["house"]})]
    if v["active"]:
        return [_finding("rule.dosha.mangal", "active", step="NATAL",
                         fact_ids=ids,
                         text=(f"Mangal dosha forms — Mars in the "
                               f"{ordinal(mars['house'])} house — and stands "
                               f"after its cancellation checks, which the "
                               f"tradition reads as strain on the marriage"),
                         brief="Mangal dosha standing",
                         plain=(f"{_p('Mars')} sits where the tradition reads "
                                f"it as hard on a marriage, and nothing in "
                                f"the chart cancels that"),
                         also=("rule.dosha.mangal_cancelled",),
                         values={"formed": True, "active": True,
                                 "house": mars["house"]})]
    return [_finding("rule.dosha.mangal_cancelled", "cancelled", step="NATAL",
                     fact_ids=ids,
                     text=(f"Mangal dosha forms — Mars in the "
                           f"{ordinal(mars['house'])} house — and is "
                           f"cancelled: " + " ".join(v["cancellations"])),
                     brief="Mangal dosha formed, cancelled",
                     also=("rule.dosha.mangal",),
                     values={"formed": True, "active": False,
                             "house": mars["house"],
                             "cancellations": list(v["cancellations"])})]


# --- VARGA ---------------------------------------------------------------------

@predicate("rule.varga.confirms", "VARGA", frame="varga")
def varga_confirms(ctx: Ctx) -> list[Finding]:
    code = ctx.domain.varga
    label = code.lower()
    fid = f"{label}.{ordinal(ctx.main)}"
    v = ctx.v(fid)
    here = list(v["occupants"])
    lead = (f"in the {code}, the chart read for {ctx.domain.varga_for}, your "
            f"{ordinal(ctx.main)} house is {v['sign']}")
    ids = (fid, f"varga.{label}.lagna")
    also = ("rule.varga.purpose",)
    if not here:
        return [_finding(
            "rule.varga.confirms", "empty", step="VARGA", fact_ids=ids,
            text=(f"{lead} and stands empty, so the promise rests on the birth "
                  f"chart and on the house's lord there"),
            brief=f"the {code} house is empty", also=also,
            values={"varga": code, "sign": v["sign"], "occupants": []})]
    out = []
    benefics = [p for p in here if p in NATURAL_BENEFICS]
    malefics = [p for p in here if p in NATURAL_MALEFICS]
    for slot, group in (("benefic", benefics), ("malefic", malefics)):
        if not group:
            continue
        out.append(_finding(
            "rule.varga.confirms", slot, step="VARGA", fact_ids=ids,
            text=(f"{lead} and holds {_and(group)}"
                  + (" — the birth chart's promise is repeated there"
                     if slot == "benefic" else
                     " — a malefic there thins what the birth chart promises")),
            brief=f"the {code} {'repeats' if slot == 'benefic' else 'thins'} it",
            plain=(f"the second chart puts {_ps(group)} over it"),
            also=also,
            values={"varga": code, "sign": v["sign"], "occupants": here,
                    "group": group}))
    return out


@predicate("rule.varga.from_varga_lagna", "VARGA", frame="varga")
def varga_lord_dignity(ctx: Ctx) -> list[Finding]:
    code = ctx.domain.varga
    label = code.lower()
    lord = ctx.main_lord
    fid = f"varga.{label}.{lord.lower()}"
    v = ctx.v(fid)
    d = (v.get("dignity") or "").split(" (")[0]
    slot = "strong" if _is_strong(d) else "weak" if _is_weak(d) else "neutral"
    return [_finding(
        "rule.varga.from_varga_lagna", slot, step="VARGA",
        fact_ids=(fid, f"varga.{label}.lagna"),
        text=(f"{lord}, lord of your {ordinal(ctx.main)}, sits in {v['sign']} "
              f"in the {code}, the {ordinal(v['house'])} house of that chart"
              + (f", {_dignity_phrase(d)}" if slot != "neutral" else "")),
        brief=f"{lord} in {code} {v['sign']}" + (f", {d}" if slot != "neutral" else ""),
        plain=(f"in the second chart {_p(lord)}, which rules it, sits "
               f"{_plain_dignity(d)}" if slot != "neutral" else ""),
        also=("rule.varga.degree_convention",),
        values={"varga": code, "lord": lord, "sign": v["sign"],
                "house": v["house"], "dignity": d})]


@predicate("rule.varga.vargottama", "VARGA", frame="d9")
def vargottama(ctx: Ctx) -> list[Finding]:
    lord = ctx.main_lord
    fid = f"varga.d9.{lord.lower()}"
    v = ctx.v(fid)
    if not v["vargottama"]:
        return []
    return [_finding(
        "rule.varga.vargottama", "main_lord", step="VARGA", fact_ids=(fid,),
        text=(f"{lord}, lord of your {ordinal(ctx.main)}, is vargottama — "
              f"{v['sign']} at birth and in the D9 alike — and is read as "
              f"notably strengthened"),
        brief=f"{lord} vargottama",
        plain=f"{_p(lord)}, which rules it, holds the same sign in both charts",
        values={"lord": lord, "sign": v["sign"]})]


@predicate("rule.vimsopaka.bala", "VARGA",
           options=("vimsopaka_group", "dual_lord"), frame="d9")
def vimsopaka(ctx: Ctx) -> list[Finding]:
    lord = ctx.main_lord
    fid = f"vimsopaka.{lord.lower()}"
    if fid not in ctx.facts:                 # a node takes no score
        return []
    v = ctx.v(fid)
    band = v["band"]
    slot = {"strong": "strong", "thin": "thin"}.get(band, "middling")
    who = f"{_p(lord)}, which rules it,"
    return [_finding(
        "rule.vimsopaka.bala", slot, step="VARGA",
        fact_ids=(fid, "vimsopaka.group"),
        text=(f"{lord}, lord of the {ordinal(ctx.main)}, scores "
              f"{v['score']:.2f} of 20 on vimsopaka bala across the "
              f"{v['group']} — {band}"),
        brief=f"{lord} {band} across the vargas",
        plain=(f"{who} holds up across the finer charts" if slot == "strong"
               else f"{who} runs thin across the finer charts" if slot == "thin"
               else ""),
        also=("rule.vimsopaka.group_school",),
        values={"lord": lord, "score": v["score"], "band": band,
                "group": v["group"]},
        reads_options=("vimsopaka_group", "dual_lord"))]


# --- DASHA ---------------------------------------------------------------------

@predicate("rule.dasha.lordship", "DASHA", frame="dasha")
def dasha_running(ctx: Ctx) -> list[Finding]:
    if "dasha.current" not in ctx.facts:     # outside the 120-year cycle
        return []
    cv = ctx.v("dasha.current")
    out = []
    for slot, role, lord, start, end in (
            ("md", "mahadasha", cv["mahadasha"], cv["md_start"], cv["md_end"]),
            ("ad", "antardasha", cv["antardasha"], cv["ad_start"], cv["ad_end"])):
        owns = ctx.v(f"karaka.{lord.lower()}")["rules"]
        sits = ctx.v(f"planet.{lord.lower()}")["house"]
        touches = sorted(set(owns) & set(ctx.domain.houses))
        if not touches and sits not in ctx.domain.houses:
            continue
        reason = []
        if touches:
            reason.append("rules your " + _and(ordinal(h) for h in touches))
        if sits in ctx.domain.houses:
            reason.append(f"sits in your {ordinal(sits)}")
        out.append(_finding(
            "rule.dasha.lordship", slot, step="DASHA",
            fact_ids=("dasha.current", f"karaka.{lord.lower()}",
                      f"planet.{lord.lower()}"),
            text=(f"the running {role} lord is {lord}, which {_and(reason)} — "
                  f"so this is a stretch in which the matter is actively in "
                  f"play, {_year(start)} to {_year(end)}"),
            brief=f"the {lord} {role} touches it",
            plain=(f"{_p(lord)}'s period holds it until {_year(end)}"
                   if slot == "md" else
                   f"{_p(lord)}'s stretch inside it runs to {_year(end)}"),
            also=("rule.dasha.placement",),
            values={"lord": lord, "role": role, "rules": touches, "sits": sits},
            start=_iso_date(start), end=_iso_date(end)))
    return out


def _window_targets(ctx: Ctx) -> dict[str, str]:
    """graha → why it bears on the domain's timing."""
    why: dict[str, str] = {}
    for h in ctx.domain.houses:
        why.setdefault(ctx.lord(h), f"lord of your {ordinal(h)}")
    for k in ctx.karakas:
        why.setdefault(k, "the natural significator")
    for p in ctx.v(f"house.{ctx.main}")["occupants"]:
        why.setdefault(p, f"standing in your {ordinal(ctx.main)}")
    if ctx.domain.id == "marriage":
        why.setdefault(ctx.v("karaka.chara.darakaraka")["planet"],
                       "the Darakaraka")
    return why


@predicate("rule.dasha.lordship", "DASHA", options=("karaka_count",),
           frame="dasha")
def dasha_windows(ctx: Ctx) -> list[Finding]:
    """Dated windows, inside the horizon, whose lord bears on the domain.
    For career the 6th and 10th lords fire rule.career.employment_period
    instead — the rule that names employment — and the others fire this."""
    if "dasha.windows" not in ctx.facts:
        return []
    why = _window_targets(ctx)
    employment = set()
    if ctx.domain.id == "career":
        employment = {ctx.lord(6), ctx.lord(10)}
    out = []
    for w in ctx.v("dasha.windows")["windows"]:
        hit = [p for p in (w["md"], w["ad"]) if p in why]
        hit = list(dict.fromkeys(hit))
        if not hit:
            continue
        rule_id = ("rule.career.employment_period"
                   if any(p in employment for p in hit)
                   else "rule.dasha.lordship")
        slot = "window_running" if w["running"] else "window_upcoming"
        reasons = _and(f"{p} ({why[p]})" for p in hit)
        out.append(_finding(
            rule_id, slot, step="DASHA",
            fact_ids=("dasha.windows",),
            text=(f"the {w['md']}–{w['ad']} period, {_year(w['start'])} to "
                  f"{_year(w['end'])}, is run by {reasons}"
                  + (" — running now" if w["running"] else "")),
            brief=f"{w['md']}–{w['ad']} {_year(w['start'])}–{_year(w['end'])}",
            plain=(f"{_ps(hit)} {'has' if len(hit) == 1 else 'have'} the "
                   f"period from {_year(w['start'])} to {_year(w['end'])}"
                   + (", running now" if w["running"] else "")),
            also=("rule.dasha.antara",),
            values={"md": w["md"], "ad": w["ad"], "hit": hit,
                    "running": w["running"]},
            start=_iso_date(w["start"]), end=_iso_date(w["end"]),
            reads_options=("karaka_count",)))
    return out


# --- TRANSIT -------------------------------------------------------------------

@predicate("rule.transit.<slow>", "TRANSIT",
           options=("node_reach", "node_position"), frame="transit")
def transit_slow(ctx: Ctx) -> list[Finding]:
    out = []
    for planet in SLOW_MOVERS:
        fid = f"transit.{planet.lower()}.aspects"
        v = ctx.v(fid)
        occupied = v["natal_house"] in ctx.domain.houses
        aspected = sorted(set(v["aspects"]) & set(ctx.domain.houses))
        if not occupied and not aspected:
            continue
        how = []
        if occupied:
            how.append(f"sitting in your {ordinal(v['natal_house'])}")
        if aspected:
            how.append("aspecting your " + _and(ordinal(h) for h in aspected))
        until = f" until {v['until']}" if v["until"] else ""
        out.append(_finding(
            f"rule.transit.{planet.lower()}", "on" if occupied else "aspecting",
            step="TRANSIT",
            fact_ids=(fid, f"transit.{planet.lower()}"),
            text=f"transiting {planet} is {_and(how)}{until}",
            brief=(f"{planet} on it{until}" if occupied
                   else f"{planet} aspecting it{until}"),
            plain=(f"{_p(planet)} is on it{until}" if occupied
                   else f"{_p(planet)} is working on it{until}"),
            also=("rule.transit.house", "rule.transit.aspect",
                  "rule.transit.window"),
            values={"planet": planet, "natal_house": v["natal_house"],
                    "aspects": aspected, "occupied": occupied},
            start=v["entered_iso"], end=v["until_iso"],
            reads_options=("node_reach", "node_position")))
    return out


@predicate("rule.transit.contact", "TRANSIT", options=("node_position",),
           frame="transit")
def transit_contact(ctx: Ctx) -> list[Finding]:
    """A transit within orb of a domain lord, karaka or main-house
    occupant. The contact governs the from-the-Moon verdict, and the fact
    itself carries the two rule ids that say so."""
    why = _window_targets(ctx)
    out = []
    for fid, fact in sorted(ctx.facts.items()):
        if fact.kind != "contact":
            continue
        c = fact.value
        if c["point"] not in why:
            continue
        rule_id = c["governing_rule"]
        planet, point = c["transit"], c["point"]
        until = c.get("until_iso")
        out.append(_finding(
            rule_id, "contact", step="TRANSIT", fact_ids=(fid,),
            text=(f"transiting {planet} stands {c['orb']}° from natal "
                  f"{point}, {why[point]}"
                  + (f", until {_year(until)}" if until else "")
                  + (" — an eclipse of it, while the contact holds"
                     if c["node"] else " — and acts on that point directly")),
            brief=f"{planet} on natal {point}",
            plain=(f"{_p(planet)} is standing on {voice.yours(point)}"
                   + (f" until {_year(until)}" if until else "")),
            also=(c["outranks_rule"], "rule.transit.contact_over_gocara",
                  "rule.precedence.name_both", "rule.graha.karakatva"),
            values={"transit": planet, "point": point, "orb": c["orb"],
                    "node": c["node"]},
            start=ctx.when.date().isoformat(), end=until,
            reads_options=("node_position",)))
    return out


@predicate("rule.transit.<slow>", "TRANSIT", options=("node_reach",),
           frame="transit")
def transit_ahead(ctx: Ctx) -> list[Finding]:
    """Jupiter and Saturn reaching or aspecting the main house, ahead,
    inside the horizon — dated windows, from the ledger's own spans."""
    out = []
    for planet in ("Jupiter", "Saturn"):
        fid = f"transit.{planet.lower()}.ahead"
        if fid not in ctx.facts:
            continue
        for span in ctx.v(fid)["spans"]:
            on = span["natal_house"] == ctx.main
            aspecting = ctx.main in span["aspects"]
            if not on and not aspecting:
                continue
            out.append(_finding(
                f"rule.transit.{planet.lower()}", "window", step="TRANSIT",
                fact_ids=(fid,),
                text=(f"transiting {planet} "
                      + ("moves through" if on else "casts drishti onto")
                      + f" your {ordinal(ctx.main)} from {span['sign']}, "
                      f"{_year(span['start'])} to {_year(span['end'])}"),
                brief=f"{planet} through {span['sign']} "
                      f"{_year(span['start'])}–{_year(span['end'])}",
                plain=(f"{_p(planet)} "
                       + ("is on it" if on else "works on it")
                       + f" from {_year(span['start'])} to {_year(span['end'])}"),
                also=("rule.transit.house", "rule.transit.aspect",
                      "rule.transit.window"),
                values={"planet": planet, "sign": span["sign"],
                        "on": on, "aspecting": aspecting},
                start=_iso_date(span["start"]), end=_iso_date(span["end"]),
                reads_options=("node_reach",)))
    return out


# --- evaluation ------------------------------------------------------------------

def applicable(domain: Domain) -> list[Predicate]:
    return [p for p in PREDICATES
            if p.domains is None or domain.id in p.domains]


def evaluate_by_predicate(domain: Domain | str, facts: dict, when: datetime,
                          only=None) -> list[tuple[Predicate, Finding]]:
    """Every applicable predicate, in register order, under the live
    school selection — each finding paired with the predicate that fired
    it, which is how the resolver knows a finding's frame. A fact a
    predicate needed and could not find is a MISSING finding, never an
    exception and never silence. `only`, when given, restricts the run to
    those Predicate objects (a rule set's own steps)."""
    if isinstance(domain, str):
        domain = DOMAINS[domain]
    ctx = Ctx(domain, facts, when)
    out: list[tuple[Predicate, Finding]] = []
    for p in applicable(domain):
        if only is not None and p not in only:
            continue
        try:
            found = p.fn(ctx)
        except KeyError as exc:
            out.append((p, _missing(p.rule_id, p.step, str(exc.args[0]),
                                    p.reads_options)))
            continue
        for f in found:
            # A finding may declare a subset of its predicate's options,
            # never one the predicate did not declare — the resolver's
            # split pass trusts this.
            assert set(f.reads_options) <= set(p.reads_options), (
                p.rule_id, f.rule_id, f.reads_options, p.reads_options)
            assert f.step == p.step, (p.rule_id, f.rule_id)
            out.append((p, f))
    return out


def evaluate(domain: Domain | str, facts: dict, when: datetime,
             only=None) -> list[Finding]:
    """The findings alone — see evaluate_by_predicate."""
    return [f for _, f in evaluate_by_predicate(domain, facts, when, only)]


def rule_ids_in_table() -> set[str]:
    return {r.rule for r in WEIGHTS}


def check_table() -> list[str]:
    """Every row's rule exists in the library (families expanded), kinds
    and confidences are known, and timing rows are timing kinds."""
    problems = []
    for r in WEIGHTS:
        if r.rule == "rule.house.<h>":
            ok = all(f"rule.house.{h}" in RULES for h in range(1, 13))
        elif r.rule == "rule.transit.<slow>":
            ok = all(f"rule.transit.{p.lower()}" in RULES for p in SLOW_MOVERS)
        else:
            ok = r.rule in RULES
        if not ok:
            problems.append(f"{r.rule}: not in the rule library")
        if r.kind not in KINDS or r.kind == MISSING:
            problems.append(f"{r.rule}/{r.slot}: kind {r.kind}")
        if r.confidence not in CONFIDENCE:
            problems.append(f"{r.rule}/{r.slot}: confidence {r.confidence}")
        if r.kind == CITED and r.weight != 0:
            problems.append(f"{r.rule}/{r.slot}: cited rows weigh 0")
        if r.kind in TIMING_KINDS and r.weight == 0:
            problems.append(f"{r.rule}/{r.slot}: a timing row weighs at least 1")
    return problems
