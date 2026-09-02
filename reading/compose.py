"""Stage 4 — COMPOSE.

"Assemble stem + emphasis + close. Mark the emphasis span for the accent
tint."

Two outputs, per the framework's voice rule:
  statement  — under fifteen words, for the Today hero
  long       — twenty-five to forty words, for the full day

The emphasis span is returned separately so the interface can tint it
without parsing prose.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from .detect import Conditions, Hit, detect
from .fragments import BY_ID, FRAGMENTS
from .select import needs_fallback, pick_variant, rank


@dataclass(frozen=True)
class Reading:
    statement: str          # the whole short sentence, emphasis included
    statement_stem: str     # split for tinting: the part before the emphasis
    emphasis: str           # the accent span
    close: str
    long: str
    subject_id: str
    qualifier_id: str | None
    facts: tuple[str, ...]  # the computed working behind both hits
    fallback: bool
    hits: tuple[Hit, ...] = field(default=())

    @property
    def word_count(self) -> int:
        return len(self.long.split())


def read_day(chart, timeline, pancanga, when: datetime,
             person_key: str = "") -> Reading:
    """The day's sentence. Same person, same day → same words, forever."""
    conditions = Conditions(chart=chart, timeline=timeline,
                            pancanga=pancanga, when=when,
                            person_key=person_key)
    hits = detect(conditions, FRAGMENTS)
    fallback = needs_fallback(hits)
    if fallback:
        hits = [h for h in hits if h.fragment_id == "pancanga.day"] or hits
    subject, qualifier = rank(hits)

    iso = when.strftime("%Y-%m-%d")
    frag = BY_ID[subject.fragment_id]
    stem = pick_variant(frag.stem, person_key, iso, frag.id, "stem")
    emphasis = pick_variant(frag.emphasis, person_key, iso, frag.id,
                            "emphasis")
    close = pick_variant(frag.close, person_key, iso, frag.id, "close")

    statement_stem = f"{stem} — "
    statement = f"{statement_stem}{emphasis}."

    facts = [subject.fact]
    qualifier_clause = ""
    if qualifier is not None:
        qfrag = BY_ID[qualifier.fragment_id]
        qemph = pick_variant(qfrag.emphasis, person_key, iso, qfrag.id,
                             "emphasis")
        qualifier_clause = f" Beneath it, {qemph}."
        facts.append(qualifier.fact)

    long = f"{statement} {close}{qualifier_clause}"

    # The framework fixes the long reading at 25–40 words. Rather than pad
    # with prose, a short reading is grounded in the day's own arithmetic —
    # a fact, never filler — and an over-long one drops its qualifier.
    if len(long.split()) < 25:
        p = pancanga
        ends = p.tithi.ends_at.strftime("%H:%M") if p.tithi.ends_at else "—"
        long += (f" The tithi is {p.paksa} {p.tithi.name}, "
                 f"{p.tithi.index} of 30, turning at {ends} UTC.")
    elif len(long.split()) > 40:
        long = f"{statement} {close}"

    return Reading(
        statement=statement, statement_stem=statement_stem,
        emphasis=emphasis, close=close, long=long,
        subject_id=subject.fragment_id,
        qualifier_id=qualifier.fragment_id if qualifier else None,
        facts=tuple(facts), fallback=fallback,
        hits=tuple(sorted(hits, key=lambda h: -h.weight)),
    )
