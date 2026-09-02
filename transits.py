"""Transits and graha drishti (sign-level Vedic aspects).

Drishti offsets (houses counted inclusively from the planet's sign):
every graha aspects the 7th; Mars additionally 4th & 8th; Jupiter 5th & 9th;
Saturn 3rd & 10th; Rahu/Ketu 5th & 9th.

Transit-to-natal contacts: conjunction when within a 3° orb of a natal
planet's longitude; aspects are sign-level (Whole Sign) drishti from the
transiting planet's sign onto the natal planet's sign.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from engine import PLANETS, SIGNS, Chart, Position, julian_day_ut, sidereal_positions

DRISHTI_OFFSETS: dict[str, tuple[int, ...]] = {
    "Sun": (7,),
    "Moon": (7,),
    "Mars": (4, 7, 8),
    "Mercury": (7,),
    "Jupiter": (5, 7, 9),
    "Venus": (7,),
    "Saturn": (3, 7, 10),
    "Rahu": (5, 7, 9),
    "Ketu": (5, 7, 9),
}

CONJUNCTION_ORB = 3.0  # degrees


def angular_distance(a: float, b: float) -> float:
    """Shortest arc between two longitudes, 0–180°."""
    d = abs(a - b) % 360.0
    return min(d, 360.0 - d)


def aspected_signs(planet: str, sign_index: int) -> tuple[int, ...]:
    """Sign indexes a planet in `sign_index` casts drishti onto.

    Offset n means the nth sign counted inclusively from the occupied sign,
    so the 7th aspect lands on sign_index + 6.
    """
    return tuple(
        (sign_index + off - 1) % 12 for off in DRISHTI_OFFSETS[planet]
    )


@dataclass(frozen=True)
class NatalAspect:
    """One planet's drishti onto another in the same (natal) chart."""

    aspecting: str
    aspected: str
    offset: int  # 3/4/5/7/8/9/10 — the inclusive house count


def natal_aspect_table(chart: Chart) -> list[NatalAspect]:
    """Every graha-drishti between natal planets (sign-level)."""
    table = []
    for a in PLANETS:
        a_sign = chart.planets[a].sign_index
        for b in PLANETS:
            if a == b:
                continue
            offset = (chart.planets[b].sign_index - a_sign) % 12 + 1
            if offset in DRISHTI_OFFSETS[a]:
                table.append(NatalAspect(aspecting=a, aspected=b, offset=offset))
    return table


def houses_aspected_by(chart: Chart, planet: str) -> tuple[int, ...]:
    """Natal houses (1–12) a planet casts drishti onto — never empty, since
    every graha casts at least the 7th aspect."""
    lagna = chart.lagna.sign_index
    return tuple(sorted(
        (s - lagna) % 12 + 1
        for s in aspected_signs(planet, chart.planets[planet].sign_index)
    ))


def aspects_on_house(chart: Chart, house: int) -> list[str]:
    """Natal planets casting drishti onto a natal house (1–12)."""
    target_sign = (chart.lagna.sign_index + house - 1) % 12
    out = []
    for name in PLANETS:
        if target_sign in aspected_signs(name, chart.planets[name].sign_index):
            out.append(name)
    return out


@dataclass(frozen=True)
class TransitPlanet:
    name: str
    position: Position
    natal_house: int  # Whole Sign house from the NATAL lagna

    @property
    def sign(self) -> str:
        return self.position.sign

    @property
    def retrograde(self) -> bool:
        return self.position.retrograde


@dataclass(frozen=True)
class TransitSnapshot:
    when: datetime
    planets: dict[str, TransitPlanet]

    @property
    def by_natal_house(self) -> dict[int, list[str]]:
        out: dict[int, list[str]] = {h: [] for h in range(1, 13)}
        for name in PLANETS:
            out[self.planets[name].natal_house].append(name)
        return out


def transit_snapshot(chart: Chart, when: datetime) -> TransitSnapshot:
    """All nine grahas at `when` (tz-aware), mapped to natal houses."""
    positions = sidereal_positions(julian_day_ut(when))
    lagna_sign = chart.lagna.sign_index
    planets = {
        name: TransitPlanet(
            name=name,
            position=pos,
            natal_house=(pos.sign_index - lagna_sign) % 12 + 1,
        )
        for name, pos in positions.items()
    }
    return TransitSnapshot(when=when, planets=planets)


@dataclass(frozen=True)
class Ingress:
    """A planet crossing a sidereal sign boundary."""

    planet: str
    when: datetime
    from_sign_index: int
    to_sign_index: int

    @property
    def to_sign(self) -> str:
        return SIGNS[self.to_sign_index]


def _sign_at(planet: str, when: datetime) -> int:
    return sidereal_positions(julian_day_ut(when))[planet].sign_index


def next_sign_ingress(planet: str, start: datetime,
                      max_days: int = 4000,
                      step_days: float = 5.0) -> Ingress | None:
    """First sign change after `start`: coarse daily scan + bisection to
    under an hour. Handles retrograde re-entries — whatever boundary is
    crossed next is what's reported."""
    t0, s0 = start, _sign_at(planet, start)
    limit = start + timedelta(days=max_days)
    while t0 < limit:
        t1 = min(t0 + timedelta(days=step_days), limit)
        s1 = _sign_at(planet, t1)
        if s1 != s0:
            lo, hi = t0, t1
            while hi - lo > timedelta(hours=1):
                mid = lo + (hi - lo) / 2
                if _sign_at(planet, mid) == s0:
                    lo = mid
                else:
                    hi = mid
            return Ingress(planet=planet, when=hi,
                           from_sign_index=s0, to_sign_index=_sign_at(planet, hi))
        t0, s0 = t1, s1
    return None


def sign_entry_before(planet: str, when: datetime,
                      max_days: int = 4000,
                      step_days: float = 5.0) -> datetime | None:
    """When the planet last entered the sign it occupies at `when` —
    scans backwards for the most recent boundary crossing."""
    target = _sign_at(planet, when)
    t0 = when
    limit = when - timedelta(days=max_days)
    while t0 > limit:
        t1 = max(t0 - timedelta(days=step_days), limit)
        if _sign_at(planet, t1) != target:
            lo, hi = t1, t0  # lo: different sign, hi: target sign
            while hi - lo > timedelta(hours=1):
                mid = lo + (hi - lo) / 2
                if _sign_at(planet, mid) == target:
                    hi = mid
                else:
                    lo = mid
            return hi
        t0 = t1
    return None


def upcoming_ingresses(start: datetime, horizon_days: int = 1825,
                       planets: tuple[str, ...] = ("Saturn", "Jupiter", "Rahu"),
                       ) -> list[Ingress]:
    """Dated sign-change markers for the slow movers over the horizon."""
    events = []
    for planet in planets:
        t = start
        remaining = horizon_days
        while remaining > 0:
            ing = next_sign_ingress(planet, t, max_days=remaining)
            if ing is None:
                break
            events.append(ing)
            remaining -= (ing.when - t).days + 1
            t = ing.when + timedelta(days=1)
    return sorted(events, key=lambda e: e.when)


@dataclass(frozen=True)
class Contact:
    """A transiting planet touching a natal planet."""

    transit_planet: str
    natal_planet: str
    kind: str  # "conjunction" | "aspect"
    offset: int = 0  # drishti house count (aspects only)
    orb: float = 0.0  # degrees from exact (conjunctions only)


def transit_contacts(chart: Chart, snapshot: TransitSnapshot,
                     orb: float = CONJUNCTION_ORB) -> list[Contact]:
    """Conjunctions (within `orb`) and sign-level drishti from each
    transiting planet onto each natal planet."""
    contacts = []
    for t in PLANETS:
        t_pos = snapshot.planets[t].position
        for n in PLANETS:
            n_pos = chart.planets[n]
            gap = angular_distance(t_pos.longitude, n_pos.longitude)
            if gap <= orb:
                contacts.append(Contact(
                    transit_planet=t, natal_planet=n,
                    kind="conjunction", orb=round(gap, 2),
                ))
            offset = (n_pos.sign_index - t_pos.sign_index) % 12 + 1
            if offset in DRISHTI_OFFSETS[t]:
                contacts.append(Contact(
                    transit_planet=t, natal_planet=n,
                    kind="aspect", offset=offset,
                ))
    return contacts
