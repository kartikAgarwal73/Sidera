"""'Ask about this chart' — a grounded agent over the computed fact ledger.

THE CONSTRAINT, AND WHY IT IS ENFORCED IN CODE
The agent answers only from `chartfacts.build_facts()`. It never computes a
position, never invents a placement, never predicts past the dasha and
transit facts it was handed.

A system prompt asking for that is necessary but not sufficient — prompts are
requests, not guarantees, and a fluent sentence about a Mars in the wrong
house reads exactly like a correct one. So every answer is parsed and checked
against the ledger before it reaches the user:

    validate_answer()  extracts every (planet, sign) and (planet, house)
                       claim in the prose and verifies each against the
                       chart — natal claims against the birth chart, transit
                       claims against today's sky.
    validate_payload() adds the two forbidden things: an outcome asserted as
                       settled, and a date the ledger never produced.

A violated answer is withheld, never captioned.

WHERE THE LINE ACTUALLY SITS
It is NOT "do not interpret". An earlier version read the constraint that way
and started listing facts while declining to read them — honest, and useless
to the person asking. Interpretation is REQUIRED, through `rulelib`, with the
rule id cited. What is forbidden is certainty about outcomes and invented
dates. Everything between those is the reading.

That check is pure and deterministic, so the tests exercise it directly with
adversarial answers rather than depending on a live model, an API key, or the
model happening to misbehave on the day CI runs.

This sits ALONGSIDE the deterministic `ask.py`, which is unchanged. That
engine derives its five verdicts from stored rules with no generation at all
and remains the primary surface; this one takes free-text questions and pays
for the flexibility with a validator.
"""
from __future__ import annotations

import json
import os
import re
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from engine import SIGNS, PLANETS, Chart
from chartfacts import build_facts, facts_payload

# The commission said "claude-sonnet-4-6 or cheaper". Sonnet 5 is both:
# $2/$10 per MTok against Sonnet 4.6's $3/$15, and a newer model. Override
# with SIDERA_ASK_MODEL if you want a different point on that curve.
DEFAULT_MODEL = "claude-sonnet-5"
MAX_QUESTIONS_PER_SESSION = 10
IP_WINDOW_SECONDS = 3600
IP_MAX_IN_WINDOW = 30
MAX_QUESTION_CHARS = 400

CORRECTIONS_LOG = Path(
    os.environ.get("SIDERA_CORRECTIONS_LOG",
                   Path(__file__).resolve().parent / "corrections.jsonl"))


SYSTEM_PROMPT = """\
You are an astrologer reading ONE person's Vedic (sidereal, Lahiri ayanamsa, \
Whole Sign) chart. You are given a fact ledger and a rule library. Your job \
is to READ the chart for them — not to recite it.

Lead with the reading, in plain, direct, warm prose. Two or three short \
paragraphs. Speak to the person, not about the data. A list of placements is \
not an answer; neither is a disclaimer.

WHAT YOU MAY DRAW ON
`facts` — everything computed from this chart. `planet.*` is the BIRTH chart; \
`transit.*` is TODAY'S SKY, and the same graha is usually in a different sign \
in each. Say which you mean — "transiting Jupiter", "your natal Jupiter" — \
never a bare "Jupiter is in ...".
`varga.d9.*` and `varga.d10.*` are DIVISIONAL charts — a third and fourth \
sky. Venus can be in Cancer at birth, Virgo in the D9 and Gemini in the D10, \
all true at once. Always name the chart: "in the D9, Venus is in ...". These \
are sign-level only; there is no degree within a divisional sign, so never \
give a varga degree, nakshatra or dignity-by-degree.
`rules` — the classical rules you interpret through. Cite by id.

Never state a placement, period or date the ledger does not contain. Do not \
compute. Do not name a yoga, dosha or dasha that has no fact.

THE ONE HARD LINE
You may say what a period FAVOURS, what it ASKS FOR, what it CAUTIONS, what \
it classically TENDS toward, and what themes are live. You may not say what \
WILL happen.

  Forbidden: "you will get a job in December", "this guarantees marriage", \
"you are going to move", any date the ledger does not contain.
  Required instead: "this is a period that rewards consolidation in visible \
work rather than quick moves", "classically this favours ...", "the tradition \
reads this as a season for ...".

That is the whole restriction. Everything else is yours to interpret.

HOW TO READ A PERIOD
For a question about how a stretch of time looks, work through:
  1. The running mahadasha lord — the houses it rules (its affairs become the \
material of the period), the house it occupies (where they play out), its \
dignity (how much friction). Rahu and Ketu rule nothing: read them from the \
house occupied.
  2. The antardasha lord the same way — it inflects the era, it does not \
replace it. Note whether the two lords are friends or not.
  3. The slow transits — Saturn, Jupiter, Rahu, Ketu — by the house each \
occupies and how long it stays, and from the natal Moon where that matters.
  4. Draw the threads together: what this combination favours, what it asks \
for, where the tradition would counsel care. Be specific to THIS chart.
Then give the dated windows so the person knows the shape of the season.

LABEL EVERY STATEMENT
  COMPUTED     — restates a ledger fact. Cite `fact_ids`.
  INTERPRETIVE — a classical reading. Cite `fact_ids` AND `rule_ids` from the \
rule library, and put the rule in your own words in `rule`.
A real reading is mostly INTERPRETIVE. Give at least three interpretive \
statements for any question about a period or a life area.

WHEN TO REFUSE — RARELY
Refuse only when the question has NO hook in this chart at all: another \
person's chart ("will she marry me?", "is my boss trustworthy?"), or \
something astrology does not address ("which stock should I buy?", lottery \
numbers). Then set `refused` true, say so warmly and briefly, and offer what \
this chart CAN speak to.

A broad question about the person's own year, work, relationships or health \
IS answerable — read it through the dasha and transits. Do not refuse it.

NO DIRECTIVES
Describe what the chart says; leave decisions to them. No medical, legal or \
financial instructions, no predictions of death or disease. Where a question \
touches those, speak to the chart's themes and leave the action to the person.

VOICE
An honest astrologer speaking to someone they respect. Warm, direct, \
unhurried. No flattery, no cosmic reassurance, no hedging filler, no \
compliance language. Sanskrit terms in their usual roman transliteration, \
briefly glossed the first time.
"""

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "answer": {
            "type": "string",
            "description": "The reply in plain prose, 2-6 sentences.",
        },
        "answer_statements": {
            "type": "array",
            "description": "Each claim in the answer, labelled and cited.",
            "items": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "label": {"type": "string",
                              "enum": ["COMPUTED", "INTERPRETIVE"]},
                    "fact_ids": {"type": "array",
                                 "items": {"type": "string"}},
                    "rule_ids": {"type": "array",
                                 "items": {"type": "string"},
                                 "description": "ids from the `rules` list; "
                                                "required for INTERPRETIVE"},
                    "rule": {"type": "string",
                             "description": "the rule in your own words"},
                },
                "required": ["text", "label", "fact_ids", "rule_ids",
                             "rule"],
                "additionalProperties": False,
            },
        },
        "facts_used": {"type": "array", "items": {"type": "string"}},
        "rules_applied": {"type": "array", "items": {"type": "string"}},
        "confidence": {"type": "string",
                       "enum": ["High", "Moderate", "Interpretive"]},
        "refused": {"type": "boolean"},
        "refusal_reason": {"type": "string"},
    },
    "required": ["answer", "answer_statements", "facts_used",
                 "rules_applied", "confidence", "refused", "refusal_reason"],
    "additionalProperties": False,
}

SUGGESTED_QUESTIONS = (
    "What does my current dasha period emphasise?",
    "Which houses are strongest in this chart, and why?",
    "What do the slow transits touch right now?",
)


# --- grounding validation -----------------------------------------------------

_ORDINAL = r"(?:1st|2nd|3rd|[4-9]th|1[0-2]th)"
_PLANETS_RE = "|".join(PLANETS)
_SIGNS_RE = "|".join(SIGNS)

# The verbs a placement can be asserted with. "transiting" and "moving
# through" are here so a transit claim is EXTRACTED — before they were
# missing, and "Jupiter is transiting Scorpio" sailed past unchecked
# because it matched no pattern at all. An unchecked claim is worse than a
# wrongly-checked one.
_PLACED = (r"(?:in|occupies|sits in|stands in|transits|transiting|"
           r"moving through|passing through|crossing)")
# "Mars is in Leo", "Mars occupies Leo", "Jupiter is transiting Cancer"
_CLAIM_SIGN = re.compile(
    rf"\b({_PLANETS_RE})\b(?:\s+is)?(?:\s+currently)?(?:\s+placed)?\s+"
    rf"{_PLACED}\s+(?:the\s+)?\b({_SIGNS_RE})\b", re.IGNORECASE)
# "Mars in the 8th house", "Mars occupies the 8th"
_CLAIM_HOUSE = re.compile(
    rf"\b({_PLANETS_RE})\b(?:\s+is)?(?:\s+currently)?(?:\s+placed)?\s+"
    rf"{_PLACED}\s+(?:your\s+)?(?:natal\s+)?(?:the\s+)?({_ORDINAL})\b",
    re.IGNORECASE)
# "Leo lagna", "the lagna is Leo"
_CLAIM_LAGNA = re.compile(
    rf"\b(?:lagna|ascendant)\s+(?:is\s+)?(?:in\s+)?\b({_SIGNS_RE})\b"
    rf"|\b({_SIGNS_RE})\s+(?:lagna|ascendant|rising)\b", re.IGNORECASE)


# A claim can be about the birth chart or about today's sky, and they are
# different facts about the same planet. Reading a transit statement as a
# natal one is not a small mistake: natal Jupiter is in Pisces here while
# transiting Jupiter is in Cancer, so a CORRECT sentence about the months
# ahead gets rejected. That failure lands hardest on forward-looking
# questions — exactly the ones the feature exists to answer.
_TRANSIT_MARK = re.compile(
    r"\b(?:transit(?:s|ed|ing)?|gocara|currently|right now|at present|"
    r"these days|moving through|passing through|crossing|goes through|"
    r"now in|(?:through|until|till)\s+\w+\s+\d{4})\b", re.IGNORECASE)
_NATAL_MARK = re.compile(
    r"\b(?:natal|natally|birth chart|at birth|in your chart|radix|"
    r"you were born with|rasi|rashi|d1)\b", re.IGNORECASE)
# A divisional chart is a THIRD sky. Venus is in Cancer at birth, Virgo in
# the D9 and Gemini in the D10 — three true statements about one planet.
# Without this the D9 facts could not be used without being withheld, which
# is the transit bug wearing a different coat.
_D9_MARK = re.compile(r"\b(?:d-?9|navamsa|nav[aā]ṃ?[sś]a)\b", re.IGNORECASE)
_D10_MARK = re.compile(r"\b(?:d-?10|dasamsa|da[sś][aā]ṃ?[sś]a)\b",
                       re.IGNORECASE)
# "in the divisional chart" without saying which — accept either varga.
_VARGA_MARK = re.compile(r"\b(?:divisional|varga|vargas)\b", re.IGNORECASE)
_CLAUSE_END = ".;:\n"


@dataclass(frozen=True)
class Violation:
    kind: str        # unknown-fact-id | wrong-sign | wrong-house | …
    claim: str
    detail: str


def _frame(text: str, start: int, end: int) -> str:
    """'natal' or 'transit' — which chart a claim at [start:end) is about.

    NEAREST MARKER WINS. One sentence can carry both frames — "Natal
    Jupiter is in Pisces, while transiting Jupiter is in Cancer" is two
    true claims about two different skies — so a rule like "any natal word
    in the sentence means natal" mislabels one of them. Distance to the
    claim decides instead.

    The window runs from the clause boundary to a little past the claim, so
    a trailing marker still counts ("Saturn occupies the 8th by transit").
    With no marker at all the claim is natal: that keeps the default strict,
    since the ledger is mostly a birth chart.
    """
    boundary = max((text.rfind(ch, 0, start) for ch in _CLAUSE_END),
                   default=-1)
    lo = boundary + 1
    window = text[lo:min(len(text), end + 45)]
    nearest, frame = None, "natal"
    for pattern, name in ((_TRANSIT_MARK, "transit"), (_NATAL_MARK, "natal"),
                          (_D9_MARK, "d9"), (_D10_MARK, "d10"),
                          (_VARGA_MARK, "varga")):
        for m in pattern.finditer(window):
            at = lo + m.start()
            # English puts the qualifier in front — "transiting Jupiter",
            # "your natal Moon" — so a marker before the claim outranks an
            # equally close one after it. Without this, the next clause's
            # qualifier can capture the previous clause's claim.
            distance = (start - at) if at < start else (at - end) + 12
            if nearest is None or distance < nearest:
                nearest, frame = distance, name
    return frame


def _canon(word: str, options) -> str:
    for o in options:
        if o.lower() == word.lower():
            return o
    return word


# --- the forbidden half: certainty about outcomes, and invented dates ---------
#
# The line is NOT "do not interpret" — that produced fact-lists nobody could
# use. It is "do not assert an outcome as settled, and do not invent a date".
# Astrology in the classical register describes tendencies and seasons; it is
# the flat prediction and the specific promised date that this app must never
# produce.
_CERTAINTY = re.compile(
    r"\b(?:"
    r"you\s+will\s+(?!find\s+(?:that|it)\b)(?:\w+\s+){0,2}?"
    r"(?:get|gain|receive|land|secure|marry|meet|win|lose|move|leave|join|"
    r"be\s+(?:offered|promoted|hired|married))|"
    r"you(?:'re|\s+are)\s+going\s+to\s+\w+|"
    r"(?:is|are)\s+guaranteed|guarantees\s+you|"
    r"(?:will|shall)\s+definitely|definitely\s+(?:will|happens?)|"
    r"certain(?:ly)?\s+to\s+\w+|without\s+(?:doubt|fail)|"
    r"is\s+assured|promises\s+you|you\s+can\s+expect\s+to\s+"
    r"(?:get|receive|land|marry)|"
    r"there\s+will\s+be\s+a\s+(?:job|marriage|promotion|child)"
    r")\b", re.IGNORECASE)

_MONTHS = ("january", "february", "march", "april", "may", "june", "july",
           "august", "september", "october", "november", "december")
_MONTH_RE = "|".join(_MONTHS) + "|" + "|".join(m[:3] for m in _MONTHS)
_DATE_TOKEN = re.compile(rf"\b({_MONTH_RE})\.?\s+(\d{{4}})\b",
                         re.IGNORECASE)


def _ledger_text(chart: Chart, when: datetime) -> str:
    parts = []
    for f in build_facts(chart, when):
        parts.append(f.statement)
        parts.append(json.dumps(f.value, default=str))
    return " ".join(parts).lower()


def find_certainty(text: str) -> list[str]:
    """Outcome claims stated as settled fact."""
    return [m.group(0) for m in _CERTAINTY.finditer(text or "")]


def find_invented_dates(text: str, ledger: str) -> list[str]:
    """Month-year dates the ledger does not contain.

    'A job in December 2026' is the failure mode: a real-looking window
    the chart never produced. Bare years are not checked — too coarse to
    be a fabrication, and the question itself usually names one.
    """
    out = []
    for m in _DATE_TOKEN.finditer(text or ""):
        month, year = m.group(1).lower(), m.group(2)
        stem = month[:3]
        if f"{stem}" in ledger and year in ledger:
            # the ledger names this month and this year somewhere
            if re.search(rf"{stem}\w*\s+{year}", ledger):
                continue
        out.append(m.group(0))
    return out


def _transit_positions(chart: Chart, when: datetime) -> dict:
    """{planet: (sign, natal_house)} for today's sky."""
    from transits import transit_snapshot
    snap = transit_snapshot(chart, when)
    return {n: (p.sign, p.natal_house) for n, p in snap.planets.items()}


def _frame_positions(chart: Chart, when: datetime) -> dict:
    """{frame: {planet: (sign, house)}} — every sky a claim may be about."""
    from vargas import dasamsa, navamsa
    d9, d10 = navamsa(chart), dasamsa(chart)
    return {
        "natal": {n: (p.sign, p.house) for n, p in chart.planets.items()},
        "transit": _transit_positions(chart, when),
        "d9": {n: (p.sign, p.house) for n, p in d9.planets.items()},
        "d10": {n: (p.sign, p.house) for n, p in d10.planets.items()},
    }


_FRAME_LABEL = {"natal": "", "transit": "transiting ",
                "d9": "in the D9, ", "d10": "in the D10, "}


def validate_answer(text: str, chart: Chart, when: datetime,
                    facts_used=(), fact_ids=None,
                    transits=None) -> list[Violation]:
    """Every placement asserted in `text` must be true of `chart`.

    This is the guarantee the system prompt only requests. A model that
    invents "Mars in Leo" for a Cancer Mars produces a violation here and
    the answer is withheld — the reader never sees a plausible sentence
    that happens to be about a different chart.

    Natal and transit claims are checked against their own positions. A
    transit claim is still checked; it is simply checked against the right
    sky.
    """
    known = fact_ids if fact_ids is not None else {
        f.id for f in build_facts(chart, when)}
    frames = transits if isinstance(transits, dict) and "natal" in (
        transits or {}) else _frame_positions(chart, when)
    out: list[Violation] = []

    for fid in facts_used:
        if fid not in known:
            out.append(Violation(
                "unknown-fact-id", fid,
                f"cited fact '{fid}' is not in the ledger"))

    def _check(planet, claimed, frame, index, matched, unit):
        """One claim against the sky its clause says it is about.

        'varga' means the clause said "divisional" without naming which, so
        it is satisfied by either D9 or D10 — that ambiguity is the writer's,
        and refusing it would withhold a true sentence.
        """
        if frame == "varga":
            candidates = [frames["d9"][planet][index],
                          frames["d10"][planet][index]]
            if claimed in candidates:
                return None
            actual = " or ".join(str(c) for c in candidates)
            return Violation(
                f"wrong-varga-{unit}", matched,
                f"in the divisional charts {planet} is in {actual}, "
                f"not {claimed}")
        actual = frames[frame][planet][index]
        if claimed == actual:
            return None
        return Violation(
            f"wrong-{frame}-{unit}", matched,
            f"{_FRAME_LABEL.get(frame, '')}{planet} is in "
            f"{'house ' if unit == 'house' else ''}{actual}, not {claimed}")

    for m in _CLAIM_SIGN.finditer(text):
        planet = _canon(m.group(1), PLANETS)
        claimed = _canon(m.group(2), SIGNS)
        bad = _check(planet, claimed, _frame(text, m.start(), m.end()),
                     0, m.group(0), "sign")
        if bad:
            out.append(bad)

    for m in _CLAIM_HOUSE.finditer(text):
        planet = _canon(m.group(1), PLANETS)
        claimed = int(re.sub(r"\D", "", m.group(2)))
        bad = _check(planet, claimed, _frame(text, m.start(), m.end()),
                     1, m.group(0), "house")
        if bad:
            out.append(bad)

    for m in _CLAIM_LAGNA.finditer(text):
        claimed = _canon(m.group(1) or m.group(2), SIGNS)
        if claimed != chart.lagna.sign:
            out.append(Violation(
                "wrong-lagna", m.group(0),
                f"the lagna is {chart.lagna.sign}, not {claimed}"))

    return out


def validate_payload(payload: dict, chart: Chart,
                     when: datetime) -> list[Violation]:
    """Validate the whole structured response, prose and citations alike."""
    from rulelib import is_known as _rule_known
    known = {f.id for f in build_facts(chart, when)}
    moving = _frame_positions(chart, when)
    ledger = _ledger_text(chart, when)
    answer = payload.get("answer", "")
    out = list(validate_answer(answer, chart, when,
                               payload.get("facts_used", ()), known,
                               transits=moving))

    # The forbidden half. Everything else about interpretation is allowed —
    # these two are what turn a reading into a promise.
    whole = " ".join(
        [answer] + [st.get("text", "") for st
                    in payload.get("answer_statements", [])])
    for claim in find_certainty(whole):
        out.append(Violation(
            "asserted-certainty", claim,
            "an outcome is stated as settled; the chart describes "
            "tendencies and seasons, not events"))
    for token in find_invented_dates(whole, ledger):
        out.append(Violation(
            "invented-date", token,
            f"'{token}' is not a date this chart produced"))
    for rid in payload.get("rules_applied", ()):
        if not _rule_known(rid) and rid.startswith("rule."):
            out.append(Violation(
                "unknown-rule-id", rid,
                f"cited rule '{rid}' is not in the rule library"))
    # A refusal asserts nothing about the chart, so there is nothing to
    # cite. Demanding citations from it would push the model toward
    # answering rather than declining — the opposite of what we want.
    if payload.get("refused"):
        return out
    for stmt in payload.get("answer_statements", []):
        if not (stmt.get("text") or "").strip():
            continue
        out.extend(validate_answer(stmt.get("text", ""), chart, when,
                                   stmt.get("fact_ids", ()), known,
                                   transits=moving))
        if stmt.get("label") == "INTERPRETIVE":
            if not stmt.get("rule") and not stmt.get("rule_ids"):
                out.append(Violation(
                    "uncited-interpretation", stmt.get("text", "")[:80],
                    "an INTERPRETIVE statement must name its classical rule"))
            for rid in stmt.get("rule_ids", ()):
                if not _rule_known(rid):
                    out.append(Violation(
                        "unknown-rule-id", rid,
                        f"cited rule '{rid}' is not in the rule library"))
        if stmt.get("label") == "COMPUTED" and not stmt.get("fact_ids"):
            out.append(Violation(
                "uncited-computed", stmt.get("text", "")[:80],
                "a COMPUTED statement must cite at least one fact id"))
    # The answer prose and its statements restate each other, so the same
    # bad claim surfaces twice. Report it once.
    seen, unique = set(), []
    for v in out:
        key = (v.kind, v.claim.lower(), v.detail)
        if key not in seen:
            seen.add(key)
            unique.append(v)
    return unique


def explain_violations(violations) -> tuple[str, str]:
    """(what went wrong, what to try) — in the reader's terms.

    "That answer did not check out" tells someone nothing about what to do
    next. Name the kind of mistake and suggest a narrower question, because
    the usual cause is a question broad enough that the reply wandered off
    the computed facts.
    """
    kinds = {v.kind for v in violations}
    if "asserted-certainty" in kinds:
        return ("the reply stated an outcome as certain, and this chart "
                "describes tendencies and seasons rather than events",
                "Ask what the period favours or asks for, rather than what "
                "will happen.")
    if "invented-date" in kinds:
        return ("the reply named a date your chart did not produce",
                "Ask about a window the chart does carry — a dasha period or "
                "a slow transit.")
    if "unknown-rule-id" in kinds:
        return ("the reply leaned on a classical rule that is not in this "
                "app's rule library",
                "Try asking about a dasha period or a transit, where the "
                "library is fullest.")
    if kinds & {"wrong-natal-sign", "wrong-natal-house", "wrong-lagna"}:
        why = ("the reply made a placement claim that does not match your "
               "computed chart")
    elif kinds & {"wrong-transit-sign", "wrong-transit-house"}:
        why = ("the reply described a transit that does not match where the "
               "grahas actually are today")
    elif "unknown-fact-id" in kinds:
        why = "the reply cited a fact that is not in your chart's ledger"
    elif kinds & {"uncited-interpretation", "uncited-computed"}:
        why = "the reply made a claim without citing what it rests on"
    else:
        why = "the reply did not check out against your computed chart"
    hint = ("Try rephrasing — for example \u201cwhat does my current dasha "
            "emphasise?\u201d or \u201cwhich house is Saturn transiting?\u201d")
    return why, hint


# --- rate limiting ------------------------------------------------------------

class RateLimiter:
    """Per-IP sliding window plus a per-session question cap.

    In-process and therefore per-worker: with N gunicorn workers the real
    ceiling is N x the configured limit. That is deliberate for a
    single-instance deploy and is stated rather than hidden — a shared
    limiter would need Redis, which this app does not have.
    """

    def __init__(self, window=IP_WINDOW_SECONDS, per_window=IP_MAX_IN_WINDOW,
                 per_session=MAX_QUESTIONS_PER_SESSION):
        self.window = window
        self.per_window = per_window
        self.per_session = per_session
        self._ip: dict[str, list[float]] = {}
        self._session: dict[str, int] = {}
        self._lock = threading.Lock()

    def check(self, ip: str, session_id: str, now: float | None = None):
        """(allowed, reason, remaining_for_session)."""
        now = time.time() if now is None else now
        with self._lock:
            hits = [t for t in self._ip.get(ip, []) if now - t < self.window]
            self._ip[ip] = hits
            used = self._session.get(session_id, 0)
            if used >= self.per_session:
                return False, (
                    f"This session's {self.per_session}-question limit is "
                    f"used up. Reload to start a new chart."), 0
            if len(hits) >= self.per_window:
                return False, (
                    "Too many questions from this address in the last hour. "
                    "Try again later."), self.per_session - used
            return True, "", self.per_session - used

    def record(self, ip: str, session_id: str, now: float | None = None):
        now = time.time() if now is None else now
        with self._lock:
            self._ip.setdefault(ip, []).append(now)
            self._session[session_id] = self._session.get(session_id, 0) + 1

    def remaining(self, session_id: str) -> int:
        with self._lock:
            return max(0, self.per_session
                       - self._session.get(session_id, 0))


LIMITER = RateLimiter()


# --- corrections log ----------------------------------------------------------

_LOG_LOCK = threading.Lock()


def log_correction(question: str, answer: str, *, reason: str = "",
                   facts_used=(), model: str = "",
                   violations=(), path: Path | None = None) -> dict:
    """Append a thumbs-down to the corrections log.

    Append-only JSONL: a rejected answer is evidence, and evidence that can
    be rewritten in place is worth less. Nothing here is user-identifying —
    the question and answer only, never the birth record.
    """
    entry = {
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "question": question,
        "answer": answer,
        "reason": reason,
        "facts_used": list(facts_used),
        "model": model,
        "violations": [v if isinstance(v, str) else
                       f"{v.kind}: {v.detail}" for v in violations],
    }
    target = path or CORRECTIONS_LOG
    with _LOG_LOCK:
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


# --- the call -----------------------------------------------------------------

@dataclass(frozen=True)
class AgentAnswer:
    answer: str
    statements: list[dict] = field(default_factory=list)
    facts_used: list[str] = field(default_factory=list)
    rules_applied: list[str] = field(default_factory=list)
    confidence: str = "Interpretive"
    refused: bool = False
    refusal_reason: str = ""
    violations: list[Violation] = field(default_factory=list)
    model: str = ""

    @property
    def ok(self) -> bool:
        return not self.violations


class AgentUnavailable(RuntimeError):
    """No API key, or the upstream call failed."""


def _client():
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not key:
        raise AgentUnavailable(
            "The chart agent is not configured on this deployment "
            "(ANTHROPIC_API_KEY is unset). The rule-based 'Ask your chart' "
            "section above works without it.")
    try:
        import anthropic
    except ImportError as exc:                      # pragma: no cover
        raise AgentUnavailable(
            "The anthropic package is not installed.") from exc
    return anthropic.Anthropic(api_key=key)


def is_configured() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY", "").strip())


def build_user_message(payload: dict, question: str) -> str:
    """Ledger first, question last — the cacheable prefix is the ledger."""
    return (
        "Fact ledger for this chart (your only source):\n"
        + json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=1)
        + "\n\nQuestion: " + question.strip()
    )


def ask_chart(chart: Chart, when: datetime, question: str, *,
              client=None, model: str | None = None) -> AgentAnswer:
    """Answer one question, validated against the ledger before returning.

    `client` is injectable so the tests can drive the whole path — prompt
    assembly, parsing, validation — without an API key or a network call.
    """
    question = (question or "").strip()
    if not question:
        raise ValueError("Ask a question first.")
    if len(question) > MAX_QUESTION_CHARS:
        raise ValueError(
            f"Questions are limited to {MAX_QUESTION_CHARS} characters.")

    model = model or os.environ.get("SIDERA_ASK_MODEL", DEFAULT_MODEL)
    client = client or _client()
    payload = facts_payload(chart, when)

    try:
        response = client.messages.create(
            model=model,
            max_tokens=2000,
            system=[{"type": "text", "text": SYSTEM_PROMPT,
                     "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user",
                       "content": build_user_message(payload, question)}],
            output_config={
                "effort": "low",
                "format": {"type": "json_schema",
                           "schema": RESPONSE_SCHEMA},
            },
        )
    except Exception as exc:                        # surfaced, never silent
        raise AgentUnavailable(f"The chart agent call failed: {exc}") from exc

    if getattr(response, "stop_reason", None) == "refusal":
        return AgentAnswer(
            answer="", refused=True, model=model,
            refusal_reason="The model declined to answer this question.")

    text = "".join(b.text for b in response.content
                   if getattr(b, "type", None) == "text")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise AgentUnavailable(
            f"The agent returned unparseable output: {exc}") from exc

    violations = validate_payload(data, chart, when)
    return AgentAnswer(
        answer=data.get("answer", ""),
        statements=data.get("answer_statements", []),
        facts_used=data.get("facts_used", []),
        rules_applied=data.get("rules_applied", []),
        confidence=data.get("confidence", "Interpretive"),
        refused=bool(data.get("refused")),
        refusal_reason=data.get("refusal_reason", ""),
        violations=violations,
        model=model,
    )
