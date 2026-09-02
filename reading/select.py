"""Stages 2 and 3 — RANK and SELECT.

RANK: "Sort by weight. Keep the top hit as the subject, the next as the
qualifier. Discard the rest. Ties break by the graha's natural order."

SELECT: "Pick one fragment per slot from the subject's variant list, indexed
by a seeded hash."

    seed  = hash(personId + isoDate + fragmentId)
    index = seed % variants.length

Two deliberate refinements, both documented rather than silent:

1. The slot name is folded into the seed. The framework's own arithmetic
   requires it — "three variants per slot gives 27 phrasings per condition"
   is 3×3×3, which only holds if the three slots are drawn independently.
   With one seed for all slots, equal-length lists would move in lockstep
   and yield 3 phrasings, not 27.
2. The hash is SHA-256, not Python's `hash()`, which is salted per process
   and would give a different sentence on every restart — the exact
   non-reproducibility the framework forbids.
"""
from __future__ import annotations

import hashlib

# Tie-break order: the classical sequence of the grahas.
NATURAL_ORDER = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus",
                 "Saturn", "Rahu", "Ketu", "")

FALLBACK_THRESHOLD = 25  # "a day with no hit above 25 falls back"


def rank(hits):
    """(subject, qualifier) — the two strongest hits, or (None, None)."""
    ordered = sorted(
        hits,
        key=lambda h: (-h.weight, NATURAL_ORDER.index(h.graha)
                       if h.graha in NATURAL_ORDER else len(NATURAL_ORDER),
                       h.fragment_id),
    )
    subject = ordered[0] if ordered else None
    qualifier = ordered[1] if len(ordered) > 1 else None
    return subject, qualifier


def needs_fallback(hits) -> bool:
    """True when nothing rose above the pañcāṅga floor."""
    return not any(h.weight > FALLBACK_THRESHOLD for h in hits)


def seed_for(person_key: str, iso_date: str, fragment_id: str,
             slot: str) -> int:
    digest = hashlib.sha256(
        f"{person_key}|{iso_date}|{fragment_id}|{slot}".encode()).digest()
    return int.from_bytes(digest[:8], "big")


def pick_variant(variants, person_key: str, iso_date: str,
                 fragment_id: str, slot: str) -> str:
    """The stable choice for this person, this day, this fragment, this slot."""
    if not variants:
        return ""
    return variants[seed_for(person_key, iso_date, fragment_id, slot)
                    % len(variants)]
