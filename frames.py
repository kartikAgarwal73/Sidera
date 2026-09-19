"""The eight frames of reference a rule can read — and nothing else.

WHY THIS IS A LEAF MODULE
A frame is the vantage a rule reads a chart from: the houses counted from
the lagna, the same houses counted from the Moon, the navāṃśa, the
daśāṃśa, the running periods, the sky now, the Jaimini points, and the
Aṣṭakavarga count. Every rule in `rulelib` declares which of these it
reads (`frames_required`); every predicate in `conditions` declares the one
frame its findings are attributed to; the resolver produces one
FrameResult per frame a rule set declares; the narrator opens each frame's
paragraph with that frame's fixed opener; and the SECOND READER — which
must be independent of the resolver — checks the narration for exactly
those openers. So the openers live here, imported by both sides, and this
module imports nothing from the resolver, the predicates or the ledger. A
second reader that shared code with the narrator would be reading its own
handwriting.
"""
from __future__ import annotations

# In narration order. The lagna first because it is the chart; the Moon
# beside it because the tradition judges from both; the divisions; then the
# clocks; then the Jaimini points and the count.
FRAMES = ("lagna", "moon", "d9", "d10", "dasha", "transit", "jaimini",
          "ashtakavarga")

# What each frame is, in the reader's words. No Sanskrit, no house numbers
# — voice.find_jargon() is the gate — and each is DISTINCT from every
# other so the second reader cannot mistake one frame's sentence for
# another's.
PLAIN = {
    "lagna": "the birth chart",
    "moon": "the chart counted from the Moon",
    "d9": "the second chart",
    "d10": "the chart of work",
    "dasha": "the running periods",
    "transit": "the sky now",
    "jaimini": "the chart's own significators",
    "ashtakavarga": "the house-by-house support count",
}

# THE OPENER. Every paragraph the narrator writes about a frame begins
# with this exact phrase, and the second reader looks for exactly this
# phrase and nothing looser. A word like "period" or "on it" occurs in
# ordinary sentences about the birth chart; an opener does not.
OPENER = {
    "lagna": "In the birth chart,",
    "moon": "Counted from the Moon,",
    "d9": "In the second chart,",
    "d10": "In the chart of work,",
    "dasha": "By the running periods,",
    "transit": "In the sky now,",
    "jaimini": "By the chart's own significators,",
    "ashtakavarga": "On the house-by-house support count,",
}

# The one fact a frame is always anchored to — what a silent frame cites,
# and what the coverage pass requires inside a sentence tagged with the
# frame. Distinct across frames by construction (gated).
ANCHOR = {
    "lagna": "lagna",
    "moon": "planet.moon",
    "d9": "varga.d9.lagna",
    "d10": "varga.d10.lagna",
    "dasha": "dasha.windows",
    "transit": "transit.jupiter.aspects",
    "jaimini": "karaka.chara.darakaraka",
    "ashtakavarga": "sav.summary",
}


def is_frame(name: str) -> bool:
    return name in FRAMES


def second_reader(frames_required, text: str) -> list[str]:
    """C7-c. The frames a narration does not address, from the narration's
    WORDS alone: a frame is addressed only if its exact opener appears at
    the start of a sentence. Input is the list of required frames and the
    prose; nothing from the resolver, nothing from the predicates, no fact
    ids. Any non-empty return is a withhold."""
    text = text or ""
    starts = _sentence_starts(text)
    missing = []
    for frame in frames_required:
        opener = OPENER[frame]
        if not any(s.startswith(opener) for s in starts):
            missing.append(frame)
    return missing


def _sentence_starts(text: str) -> list[str]:
    """Each sentence's opening, so an opener buried mid-sentence — quoted,
    say — does not count as a paragraph about that frame."""
    import re
    out = []
    for sentence in re.split(r"(?<=[.!?])\s+|\n+", text.strip()):
        sentence = sentence.strip()
        if sentence:
            out.append(sentence)
    return out
