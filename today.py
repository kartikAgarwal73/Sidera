"""Today, for this chart — the dated sky, composed deterministically.

WHAT THIS IS FOR
The arrival screen used to open on a contents page. It opens on TODAY now:
three or four short entries, each naming a graha and a date, and one line of
verdict. "Ketu leaves the degree of your Venus today — the four-month pinch
on comfort ends" is the sentence this module exists to produce.

WHY IT NEEDED NEW MACHINERY
The ledger already knew a transit was sitting within 3° of a natal point
(`contact.*`) and it already knew when a planet changes sign. It did NOT know
when a CONTACT ends — the orb has no boundary in the fact, only a current gap.
Without that date the entry would read "Ketu is on your Venus", which is the
vague register the whole voice doctrine exists to refuse. `contact_window()`
finds the two edges the same way `transits.next_sign_ingress` finds a sign
boundary: coarse scan, then bisect.

WHAT IT WILL NOT SAY
The same line every other reading works to. It reports a dated CONDITION —
what is touching what, and until when. It never says what will come of it.
Every date here is computed from the ephemeris, never rounded into a claim.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

import voice
from engine import (Chart, PLANETS, SIGNS, sidereal_positions,
                    julian_day_ut)
from rulelib import HOUSE_MATTERS, KARAKATVAS
from transits import (
    CONJUNCTION_ORB,
    angular_distance,
    next_sign_ingress,
    transit_snapshot,
)

# The nodes have no English name in ordinary use; everything else is the
# reader's own sky. Same table the domain reading uses.
PLAIN_PLANET = {"Rahu": "the north node", "Ketu": "the south node",
                "Sun": "the Sun", "Moon": "the Moon"}

# How far ahead an event is still "today's news". A sign change six months
# out is true and is not news.
HORIZON_DAYS = 45

# At most four. The screen is a day's reading, not a feed.
MAX_ENTRIES = 4


def _plain(name: str) -> str:
    return PLAIN_PLANET.get(name, name)


def _lon(planet: str, when: datetime) -> float:
    return sidereal_positions(julian_day_ut(when))[planet].longitude


@dataclass(frozen=True)
class Entry:
    """One dated line. `fact_ids` keeps the expander pattern intact."""

    text: str
    when: datetime            # the date the line turns on, for ordering
    kind: str                 # contact | ingress | station
    fact_ids: tuple[str, ...]
    weight: int = 1


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
    return HOUSE_MATTERS[house].split(",")[0].strip()


def _months_between(a: datetime | None, b: datetime) -> str:
    if a is None:
        return "long"
    months = max(1, round((b - a).days / 30.4))
    names = {1: "one-month", 2: "two-month", 3: "three-month",
             4: "four-month", 5: "five-month", 6: "six-month"}
    return names.get(months, f"{months}-month")


def entries(chart: Chart, when: datetime) -> list[Entry]:
    """Three or four dated lines about today, sharpest first."""
    snapshot = transit_snapshot(chart, when)
    out: list[Entry] = []

    # --- 1. contacts: a transit sitting on a natal point, with both edges --
    for t in PLANETS:
        t_lon = snapshot.planets[t].position.longitude
        for n in PLANETS:
            natal = chart.planets[n]
            if angular_distance(t_lon, natal.longitude) > CONJUNCTION_ORB:
                continue
            entered, leaves = contact_window(t, natal.longitude, when)
            fact = (f"contact.{t.lower()}-{n.lower()}",)
            # A planet on its OWN natal degree is a return, not a crossing,
            # and saying "Mars crosses your Mars" reads like a bug.
            own = (t == n)
            if leaves is not None and (leaves.date() - when.date()).days == 0:
                out.append(Entry(
                    _sentence(
                        f"{_plain(t)} leaves "
                        + (f"its own place in your chart"
                           if own else f"the degree of your {_plain(n)}")
                        + f" today — the {_months_between(entered, when)} "
                          f"stretch on {_matters(n)} closes."),
                    when, "contact", fact, weight=5))
            else:
                out.append(Entry(
                    _sentence(
                        (f"{_plain(t)} is back on its own natal degree"
                         if own else
                         f"{_plain(t)} crosses your {_plain(n)}")
                        + f" until {when_phrase(leaves, when)} — a dated "
                          f"stretch on {_matters(n)}."),
                    leaves or when, "contact", fact, weight=4))

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
        out.append(Entry(
            _sentence(f"{_plain(t)} moves into {ing.to_sign} "
                      f"{on_phrase(ing.when, when)} — the part of your "
                      f"chart that holds {_holds(chart, ing.to_sign)}."),
            ing.when, "ingress", (f"transit.{t.lower()}.aspects",),
            weight=3 if t in ("Saturn", "Jupiter", "Rahu", "Ketu") else 2))

    # --- 3. a slow mover turning ------------------------------------------
    for t in ("Mars", "Mercury", "Jupiter", "Venus", "Saturn"):
        tp = snapshot.planets[t]
        if getattr(tp.position, "retrograde", False):
            out.append(Entry(
                _sentence(f"{_plain(t)} is retrograde — {_matters(t)} is "
                          f"being gone back over rather than pushed "
                          f"forward."),
                when, "station", (f"transit.{t.lower()}.station",), weight=1))

    out.sort(key=lambda e: (-e.weight, e.when))
    return out[:MAX_ENTRIES]


def day_header(when: datetime, pancanga) -> str:
    """'Thursday 11 September · Kṛṣṇa Pratipadā' — the day, named twice:
    once by the civil calendar and once by the Moon."""
    civil = f"{when.strftime('%A')} {when.day} {when.strftime('%B')}"
    return f"{civil} · {pancanga.paksa.capitalize()} {pancanga.tithi.name}"
