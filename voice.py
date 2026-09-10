"""The editorial doctrine, as code — answer first, one breath, then the working.

WHY THIS EXISTS
A live walk-through found the app over-explaining and burying the answer: the
same over-hedging disease the readings themselves are built to avoid, in text
form. Someone asking about their marriage was handed three hundred words that
opened on the word "Mixed" and never quite said anything.

The fix is NOT less honesty. Every fact id, every rule citation, every
INTERPRETIVE label and the whole validator stay exactly as strict. What
changes is the ORDER and the ECONOMY of speech:

    1. ANSWER FIRST, ONE BREATH — the opening 1–2 sentences carry the actual
       verdict, in words a stranger understands.
    2. HARD BUDGETS — a teaser is 20 words, a synthesis 120, an agent lead 80.
       Everything else moves underneath, into expanders. Nothing is deleted.
    3. NO THROAT-CLEARING — "It is important to note that…" is not honesty,
       it is delay. The honesty lives in the expanders and the confidence
       labels, where it can be checked.
    4. ONE CAVEAT, AT THE END — one line, after the reading, never before it.
    5. PLAIN REGISTER ON TOP — the visible sentence uses no Sanskrit and no
       house numbers. Jargon begins inside the expanders, glossed.

This module holds the budgets, the banned patterns and the checkers, so the
prose and the tests that police it cannot drift apart.
"""
from __future__ import annotations

import re

# --- the budgets ------------------------------------------------------------
# Deliberately tight. A budget that is never binding is decoration.
TEASER_WORDS = 20          # a domain card's one line
SYNTHESIS_WORDS = 120      # a domain view, visible before any expander
ASK_LEAD_WORDS = 80        # the agent's opening paragraph
VERDICT_SENTENCES = 2      # "one breath"

# --- throat-clearing --------------------------------------------------------
# Phrases that delay the answer. Each was found in this app's own output or in
# the model's, not invented for the list. The pattern is always the same: a
# sentence about the reading, standing in front of the reading.
#
# Split in two because position matters. "It's important to note" is a delay
# wherever it appears. "First," and "Before we" are only a delay when they
# OPEN — "the day runs 01–31, month second" is not throat-clearing, and an
# unanchored pattern flagged exactly that kind of innocent sentence when this
# list was first run over the app's own pages.
THROAT_ANYWHERE = (
    r"it(?:'s| is) (?:important|worth) (?:to )?not(?:e|ing)",
    r"it should be noted",
    r"(?:the|your) chart (?:does ?n[o']t|cannot|can't) (?:forecast|predict|"
    r"guarantee|promise|tell)",
    r"while (?:no|there is no|there's no) (?:definitive|certain|guarantee)",
    r"as (?:always|with any reading)",
    r"(?:do )?(?:keep|bear) in mind",
    r"astrology (?:does ?n[o']t|is not|isn't) (?:a |an )?(?:predict|forecast|"
    r"determin|guarantee|fortune)",
    r"(?:i|we) (?:should|must|need to) (?:begin|start) by",
    r"there (?:are|is) (?:several|many|a number of|multiple) (?:factors|"
    r"things|considerations)",
    r"the (?:short|honest) answer is",   # still a delay: give the answer
)
THROAT_OPENERS = (
    r"(?:that|this) said,",
    r"before (?:we|i|answering)\b",
    r"(?:please )?remember(?: that)?,",
    r"(?:first|to begin)(?:,| of all)",
    r"(?:to|let me) (?:be clear|start|begin)",
)
THROAT_CLEARING = THROAT_ANYWHERE + THROAT_OPENERS

# Hedge stacks — a modal wrapped in a modal. One modal is fine; the reading is
# genuinely uncertain. Three in a row is how you say nothing at length.
HEDGE_STACK = (
    r"may (?:be )?(?:possible|possibly)",
    r"might (?:possibly|perhaps)",
    r"could (?:possibly|potentially|perhaps)",
    r"(?:suggests?|indicates?) that it (?:may|might|could)",
    r"it (?:may|might|could) be (?:possible|that it is possible)",
    r"(?:seems?|appears?) to (?:possibly|perhaps)",
    r"(?:possibly|perhaps) (?:may|might|could)",
    r"(?:tends? to )?(?:may|might) (?:sometimes|occasionally) (?:tend|seem)",
)

# --- vagueness --------------------------------------------------------------
# A verdict can be short, plain and answer-first and STILL say nothing. "Work
# and money is one of the stronger parts of your chart — the planet that rules
# it is strong" passes every rule above and tells the reader not one fact
# about their own chart. Being unspecific is its own failure mode, and it
# needs its own list.
VAGUE = (
    r"one of the (?:stronger|weaker|harder|better|easier) parts",
    r"the planet that rules it is (?:strong|weak)",
    r"its ruling planet is (?:strong|weak)",
    r"a second chart (?:confirms|does not confirm) it",
    r"more (?:helped than hindered|contested than helped)",
    r"is (?:well )?(?:supported|contested) (?:here|overall)",
)
_VAGUE_RE = tuple(re.compile(p, re.IGNORECASE) for p in VAGUE)

# The nine grahas, in the plain register the top layer uses. A verdict that
# names one of these is talking about THIS chart; one that does not is
# talking about charts in general.
PLANETS = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn",
           "north node", "south node")
_PLANET_RE = re.compile(
    r"\b(?:" + "|".join(PLANETS) + r")\b", re.IGNORECASE)
# "until Jun 2027", "in June 2027", "from Dec 2026" — a window the ledger gave.
_DATE_RE = re.compile(
    r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4}\b")


def find_vagueness(text: str) -> list[str]:
    """Phrases that fill a verdict without saying anything about the chart."""
    return [m.group(0) for rx in _VAGUE_RE for m in rx.finditer(text or "")]


def names_a_planet(text: str) -> list[str]:
    return [m.group(0) for m in _PLANET_RE.finditer(text or "")]


def names_a_date(text: str) -> list[str]:
    return [m.group(0) for m in _DATE_RE.finditer(text or "")]


def is_concrete(text: str) -> bool:
    """Does this sentence name something the reader could look up?

    One named graha is the floor. It is a low bar deliberately — the point is
    to make "your career planet, Mercury, is exalted" pass and "the planet
    that rules it is strong" fail.
    """
    return bool(names_a_planet(text)) and not find_vagueness(text)


_THROAT_RE = tuple(re.compile(p, re.IGNORECASE) for p in THROAT_ANYWHERE)
_OPENER_RE = tuple(re.compile(r"^\W*(?:" + p + r")", re.IGNORECASE)
                   for p in THROAT_OPENERS)
_HEDGE_RE = tuple(re.compile(p, re.IGNORECASE) for p in HEDGE_STACK)

# --- plain register ---------------------------------------------------------
# Banned from the TOP layer only. Every one of these is welcome — and mostly
# required — inside an expander, where it can be glossed and cited. Planet
# names in English (Saturn, Jupiter, Venus) are not on this list: they are the
# reader's own sky, not jargon.
SANSKRIT = (
    "drishti", "dṛṣṭi", "dasha", "daśā", "dasa", "mahadasha", "mahādaśā",
    "antardasha", "antaradaśā", "antara", "navamsa", "navāṃśa", "dasamsa",
    "daśāṃśa", "varga", "vargas", "graha", "grahas", "lagna", "nakshatra",
    "nakṣatra", "rasi", "rāśi", "karaka", "kāraka", "moolatrikona",
    "mūlatrikoṇa", "gocara", "kundli", "kuṇḍalī", "yoga", "dosha", "doṣa",
    "vimshottari", "viṃśottarī", "paksa", "pakṣa", "tithi", "rahu", "ketu",
    "ashtakavarga", "aṣṭakavarga", "arudha", "upapada", "atmakaraka",
    "parashari", "pārāśarī", "jaimini", "bhava", "sphuta", "shadbala",
)
# "the 7th house", "your 5th lord", "the 2nd from the 7th" — precise, and
# meaningless to someone who has not been taught the system.
_HOUSE_NUMBER_RE = re.compile(
    r"\b(?:\d+(?:st|nd|rd|th)|first|second|third|fourth|fifth|sixth|seventh|"
    r"eighth|ninth|tenth|eleventh|twelfth)\s+(?:house|lord|bhava|from)\b",
    re.IGNORECASE)
_D_CHART_RE = re.compile(r"\bD-?\d{1,2}\b")
_SANSKRIT_RE = re.compile(
    r"\b(?:" + "|".join(re.escape(w) for w in SANSKRIT) + r")\b",
    re.IGNORECASE)


def words(text: str) -> int:
    """Words as a reader counts them, not as a tokeniser does."""
    return len([w for w in re.split(r"\s+", (text or "").strip()) if w])


def sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", (text or "").strip())
    return [p for p in parts if p]


def find_throat_clearing(text: str) -> list[str]:
    """Every delaying phrase in `text`, as matched — for a test's message.

    THROAT_ANYWHERE is checked everywhere, because "…, but it's important to
    note that…" is the same disease with a comma in front of it.
    THROAT_OPENERS is checked only where a sentence begins, because that is
    the only place those words delay anything.
    """
    hits = []
    for rx in _THROAT_RE + _HEDGE_RE:
        hits += [m.group(0) for m in rx.finditer(text or "")]
    for sentence in sentences(text):
        for rx in _OPENER_RE:
            m = rx.match(sentence)
            if m:
                hits.append(m.group(0))
    return hits


def find_jargon(text: str) -> list[str]:
    """Sanskrit, divisional-chart shorthand and house numbers.

    For the TOP layer only. Passing this is not a virtue anywhere else — an
    expander that avoided the technical term would be worse, not better.
    """
    hits = [m.group(0) for m in _SANSKRIT_RE.finditer(text or "")]
    hits += [m.group(0) for m in _D_CHART_RE.finditer(text or "")]
    hits += [m.group(0) for m in _HOUSE_NUMBER_RE.finditer(text or "")]
    return hits


def is_answer_first(text: str) -> bool:
    """Does the opening sentence carry the verdict, or clear its throat?

    A weak test on purpose: it can prove the opener is NOT an answer, which
    is the failure that shipped. Whether a clean opener is a *good* answer is
    a judgement no regex makes, and the word budgets do the rest of the work.
    """
    first = sentences(text)[:1]
    if not first:
        return False
    return not find_throat_clearing(first[0])


def trim_to(text: str, budget: int) -> str:
    """Drop whole sentences from the end until the text fits the budget.

    Sentences, never words: a paragraph cut mid-clause reads like a bug, and
    the material is not lost — it is already in the expanders below.
    """
    kept: list[str] = []
    for s in sentences(text):
        if words(" ".join(kept + [s])) > budget:
            break
        kept.append(s)
    return " ".join(kept)
