"""Today, for this chart — the dated sky, composed deterministically.

WHAT THIS IS FOR
The arrival screen used to open on a contents page. It opens on TODAY now:
three or four short entries, each naming a graha and a date, and one line of
verdict. "The south node leaves the degree of your Venus today — the
four-month stretch on love closes" is the sentence this module exists to
produce.

WHY IT NEEDED NEW MACHINERY
The ledger already knew a transit was sitting within 3° of a natal point
(`contact.*`) and it already knew when a planet changes sign. It did NOT know
when a CONTACT ends — the orb has no boundary in the fact, only a current gap.
Without that date the entry would read "Ketu is on your Venus", which is the
vague register the whole voice doctrine exists to refuse. `contact_window()`
finds the two edges the same way `transits.next_sign_ingress` finds a sign
boundary: coarse scan, then bisect.

HOW A LINE GETS ITS WORDS — re-pinned 2026-09-14, from a review of the live
site, which found two things. "Mars crosses your the Moon": the plain names
carry their own article, and the template wrote "your " in front of them.
And three consecutive lines ending "— a dated stretch on X.": each kind of
entry had exactly one sentence, and the sort clusters entries of a kind.
So composition and rendering are two steps now. `drafts()` finds the facts;
the list is sorted and cut to four; only THEN does `render()` choose each
line's sentence — by its position, from three forms per kind — so no two
neighbours can share a closing. The possessive is `voice.yours`, a function
rather than a prefix, and the plain-name table lives in voice.py with the
doctrine rather than in a copy here.

WHAT IT WILL NOT SAY
The same line every other reading works to. It reports a dated CONDITION —
what is touching what, and until when. It never says what will come of it.
Every date here is computed from the ephemeris, never rounded into a claim.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta

import voice
from engine import (Chart, PLANETS, SIGNS, sidereal_positions,
                    julian_day_ut)
from rulelib import KARAKATVAS, house_words
from transits import (
    CONJUNCTION_ORB,
    angular_distance,
    next_sign_ingress,
    transit_snapshot,
)

#: The plain names of the nine. ONE table, kept with the doctrine; this
#: name survives because app.py reads it here.
PLAIN_PLANET = voice.PLAIN_PLANET

# How far ahead an event is still "today's news". A sign change six months
# out is true and is not news.
HORIZON_DAYS = 45

# At most four. The screen is a day's reading, not a feed.
MAX_ENTRIES = 4


def _plain(name: str) -> str:
    return voice.plain(name)


def _yours(name: str) -> str:
    """'your Moon', 'your north node' — never 'your the Moon'."""
    return voice.yours(name)


def _lon(planet: str, when: datetime) -> float:
    return sidereal_positions(julian_day_ut(when))[planet].longitude


@dataclass(frozen=True)
class Entry:
    """One dated line. `fact_ids` keeps the expander pattern intact; `form`
    names the sentence it was rendered with, so a gate can say two
    neighbours differ without parsing prose."""

    text: str
    when: datetime            # the date the line turns on, for ordering
    kind: str                 # contact | ingress | station
    fact_ids: tuple[str, ...]
    weight: int = 1
    form: str = ""


@dataclass(frozen=True)
class Draft:
    """An entry before it has words: the facts, and the slots a form fills.

    A draft cannot be rendered when it is found, because the form is chosen
    by POSITION in the day's list, and the position is not known until the
    list is sorted and cut to four.
    """

    kind: str                 # contact | contact_own | contact_ends |
                              # contact_ends_own | ingress | station
    when: datetime
    fact_ids: tuple[str, ...]
    weight: int
    slots: dict


def contact_window(planet: str, natal_longitude: float, when: datetime,
                   orb: float = CONJUNCTION_ORB,
                   max_days: int = 400) -> tuple[datetime | None,
                                                 datetime | None]:
    """When this transit entered the orb of that natal point, and when it
    leaves — scanned outward from `when` and bisected to the hour.

    Returns (entered, leaves). Either may be None if the edge is further than
    `max_days` away, which is the honest answer for a node sitting on a point
    for most of a year.
    """
    def inside(t: datetime) -> bool:
        return angular_distance(_lon(planet, t), natal_longitude) <= orb

    if not inside(when):
        return None, None

    def edge(direction: int) -> datetime | None:
        step = timedelta(days=1) * direction
        t0 = when
        for _ in range(max_days):
            t1 = t0 + step
            if not inside(t1):
                lo, hi = (t0, t1) if direction > 0 else (t1, t0)
                while hi - lo > timedelta(hours=1):
                    mid = lo + (hi - lo) / 2
                    if inside(mid):
                        lo, hi = (mid, hi) if direction > 0 else (lo, mid)
                    else:
                        lo, hi = (lo, mid) if direction > 0 else (mid, hi)
                return hi if direction > 0 else lo
            t0 = t1
        return None

    return edge(-1), edge(+1)


def _ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        return f"{n}th"
    return f"{n}{ {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th') }"


def on_phrase(target: datetime | None, now: datetime) -> str:
    """`when_phrase` with the right preposition in front of it — "on the
    20th" but "today", never "on today"."""
    phrase = when_phrase(target, now)
    return phrase if phrase in ("today", "tomorrow") else f"on {phrase}"


def when_phrase(target: datetime | None, now: datetime) -> str:
    """A date a reader can act on, in as few words as it takes.

    Same month → "the 20th". Same year → "4 October". Otherwise the year is
    carried. "today" is reserved for the actual day, because it is the only
    word here anyone will act on immediately.
    """
    if target is None:
        return "for months yet"
    days = (target.date() - now.date()).days
    if days == 0:
        return "today"
    if days == 1:
        return "tomorrow"
    if target.year == now.year and target.month == now.month:
        return f"the {_ordinal(target.day)}"
    if target.year == now.year:
        return f"{target.day} {target.strftime('%B')}"
    return f"{target.strftime('%b %Y')}"


def _sentence(text: str) -> str:
    """Sentence case. The plain planet names carry their own article — "the
    Moon" — so a line can start lowercase without this."""
    return text[:1].upper() + text[1:] if text else text


def _matters(planet: str) -> str:
    """What a graha carries, in two or three plain words."""
    return KARAKATVAS[planet].split(",")[0].strip()


def _holds(chart: Chart, sign: str) -> str:
    """What that sign is, IN THIS CHART — the shortest true clause.

    A sign change is sky news and belongs to everybody. Which part of the
    reader's own chart it lands in is the thing the screen is headed with:
    "Today for this chart". Whole Sign, counted from the lagna, and named
    in plain words rather than by number, per the plain-register rule.
    """
    house = (SIGNS.index(sign) - chart.lagna.sign_index) % 12 + 1
    return house_words(house)


def _months_between(a: datetime | None, b: datetime) -> str:
    if a is None:
        return "long"
    months = max(1, round((b - a).days / 30.4))
    names = {1: "one-month", 2: "two-month", 3: "three-month",
             4: "four-month", 5: "five-month", 6: "six-month"}
    return names.get(months, f"{months}-month")


def _months_words(k: str) -> str:
    """'four-month' → 'four months'; the 'long' case has no count."""
    return "many months" if k == "long" else k.replace("-month", " months")


# THE FORMS. Three per kind, so no two of a day's four lines need share a
# closing. Every form of a kind carries the same facts — the transit, the
# natal point or the sign, the date, what the point carries or what the
# house holds — and states a dated condition, never an outcome. Form 0 of
# each kind is the sentence the screen has always shown.
#
# Two literals are load-bearing and stay in every form of their kind: "back
# on its own natal degree" and "its own place in your chart" — the return
# forms — because "Mars crosses your Mars" reads like a bug, and a gate greps
# this file for them. "The part of your chart" is the house's phrase and no
# form lends it to anything else.
CONTACT = (
    "{T} crosses {yn} until {date} — a dated stretch on {m}.",
    "{T} is on {yn} until {date} — {m} is what it is leaning on until then.",
    "{T} stays on {yn} until {date} — {m} takes the pressure.",
)
CONTACT_OWN = (
    "{T} is back on its own natal degree until {date} — a dated stretch "
    "on {m}.",
    "{T} is back on its own natal degree until {date} — {m} is what it is "
    "leaning on until then.",
    "{T} is back on its own natal degree until {date} — {m} takes the "
    "pressure.",
)
CONTACT_ENDS = (
    "{T} leaves the degree of {yn} today — the {k} stretch on {m} closes.",
    "{T} moves off {yn} today — {k_words} on {m} end here.",
    "{T} clears {yn} today — the {k} stretch on {m} is over.",
)
CONTACT_ENDS_OWN = (
    "{T} leaves its own place in your chart today — the {k} stretch on {m} "
    "closes.",
    "{T} moves off its own place in your chart today — {k_words} on {m} "
    "end here.",
    "{T} clears its own place in your chart today — the {k} stretch on {m} "
    "is over.",
)
INGRESS = (
    "{T} moves into {sign} {on} — the part of your chart that holds {h}.",
    "{T} enters {sign} {on} — in this chart, the part that holds {h}.",
    "{T} goes into {sign} {on} — in your chart, where {h} sits.",
)
STATION = (
    "{T} is retrograde — {m} is being gone back over rather than pushed "
    "forward.",
    "{T} is retrograde — a time for going back over {m}, not pushing it.",
    "{T} is retrograde — {m} is being revisited, not advanced.",
)
FORMS = {
    "contact": CONTACT, "contact_own": CONTACT_OWN,
    "contact_ends": CONTACT_ENDS, "contact_ends_own": CONTACT_ENDS_OWN,
    "ingress": INGRESS, "station": STATION,
}
_KIND_SHOWN = {"contact": "contact", "contact_own": "contact",
               "contact_ends": "contact", "contact_ends_own": "contact",
               "ingress": "ingress", "station": "station"}

# The nodes are one axis. Transit Rahu on natal Ketu is, to the degree,
# transit Ketu on natal Rahu, and a return of one is a return of the other —
# both are always 180° from their twin. Two lines for one sky event took two
# of the day's four slots on the live site; the Rahu line carries both facts.
_NODE_TWIN = {"Rahu": "Ketu", "Ketu": "Rahu"}


def closing(text: str) -> str:
    """The template of a line's ending: what follows its last em-dash, with
    the month count generalised. Two lines share a closing when a reader
    would hear the same sentence twice."""
    tail = text.rsplit(" — ", 1)[-1]
    return re.sub(r"\b\w+-month\b", "N-month", tail)


def render(draft: Draft, position: int) -> Entry:
    """Words for a draft, from the form its position in the list picks."""
    forms = FORMS[draft.kind]
    index = position % len(forms)
    return Entry(_sentence(forms[index].format(**draft.slots)), draft.when,
                 _KIND_SHOWN[draft.kind], draft.fact_ids, draft.weight,
                 form=f"{draft.kind}/{index}")


def drafts(chart: Chart, when: datetime) -> list[Draft]:
    """Every candidate line about today, before words."""
    snapshot = transit_snapshot(chart, when)
    out: list[Draft] = []

    # --- 1. contacts: a transit sitting on a natal point, with both edges --
    for t in PLANETS:
        t_lon = snapshot.planets[t].position.longitude
        for n in PLANETS:
            natal = chart.planets[n]
            if angular_distance(t_lon, natal.longitude) > CONJUNCTION_ORB:
                continue
            fact = (f"contact.{t.lower()}-{n.lower()}",)
            if t == "Ketu" and n in _NODE_TWIN:
                # The Rahu line for the same event carries this fact id.
                continue
            if t == "Rahu" and n in _NODE_TWIN:
                fact = fact + (f"contact.ketu-{_NODE_TWIN[n].lower()}",)
            entered, leaves = contact_window(t, natal.longitude, when)
            # A planet on its OWN natal degree is a return, not a crossing,
            # and saying "Mars crosses your Mars" reads like a bug.
            own = (t == n)
            if leaves is not None and (leaves.date() - when.date()).days == 0:
                k = _months_between(entered, when)
                out.append(Draft(
                    "contact_ends_own" if own else "contact_ends", when, fact,
                    5, {"T": _plain(t), "yn": _yours(n), "k": k,
                        "k_words": _months_words(k), "m": _matters(n)}))
            else:
                out.append(Draft(
                    "contact_own" if own else "contact", leaves or when, fact,
                    4, {"T": _plain(t), "yn": _yours(n),
                        "date": when_phrase(leaves, when), "m": _matters(n)}))

    # --- 2. sign changes inside the horizon --------------------------------
    horizon = when + timedelta(days=HORIZON_DAYS)
    for t in PLANETS:
        # The Moon changes sign every two and a half days. It is true, it is
        # never news, and left in it crowded out everything that was.
        if t == "Moon":
            continue
        ing = next_sign_ingress(t, when, max_days=HORIZON_DAYS + 1)
        if ing is None or ing.when > horizon:
            continue
        out.append(Draft(
            "ingress", ing.when, (f"transit.{t.lower()}.aspects",),
            3 if t in ("Saturn", "Jupiter", "Rahu", "Ketu") else 2,
            {"T": _plain(t), "sign": ing.to_sign,
             "on": on_phrase(ing.when, when),
             "h": _holds(chart, ing.to_sign)}))

    # --- 3. a slow mover turning ------------------------------------------
    for t in ("Mars", "Mercury", "Jupiter", "Venus", "Saturn"):
        tp = snapshot.planets[t]
        if getattr(tp.position, "retrograde", False):
            out.append(Draft(
                "station", when, (f"transit.{t.lower()}.station",), 1,
                {"T": _plain(t), "m": _matters(t)}))
    return out


def entries(chart: Chart, when: datetime) -> list[Entry]:
    """Three or four dated lines about today, sharpest first — and no two
    neighbours ending the same way."""
    chosen = sorted(drafts(chart, when),
                    key=lambda d: (-d.weight, d.when))[:MAX_ENTRIES]
    return [render(d, i) for i, d in enumerate(chosen)]


def day_header(when: datetime, pancanga) -> str:
    """'Thursday 11 September · Kṛṣṇa Pratipadā' — the day, named twice:
    once by the civil calendar and once by the Moon."""
    civil = f"{when.strftime('%A')} {when.day} {when.strftime('%B')}"
    return f"{civil} · {pancanga.paksa.capitalize()} {pancanga.tithi.name}"
