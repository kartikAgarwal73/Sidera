"""Nakshatras and the Vimshottari dasha system.

Nakshatras: 27 equal divisions of 13°20′, four padas of 3°20′ each.
Vimshottari: 120-year cycle; the Mahadasha timeline starts from the Moon's
nakshatra lord with the balance proportional to the arc still to travel in
that nakshatra. Antardashas subdivide each MD in the same lord order,
proportionally (md_years × ad_years / 120).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from engine import Chart

NAKSHATRAS = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni",
    "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha",
    "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana",
    "Dhanishta", "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada",
    "Revati",
]

# Vimshottari lord cycle. Nakshatra n is ruled by DASHA_SEQUENCE[n % 9];
# the cycle repeats three times over the 27 nakshatras (Ashwini → Ketu).
DASHA_SEQUENCE = [
    ("Ketu", 7), ("Venus", 20), ("Sun", 6), ("Moon", 10), ("Mars", 7),
    ("Rahu", 18), ("Jupiter", 16), ("Saturn", 19), ("Mercury", 17),
]
TOTAL_YEARS = 120  # sum of the nine dasha years

NAKSHATRA_SPAN = 360.0 / 27.0  # 13°20′
PADA_SPAN = NAKSHATRA_SPAN / 4.0  # 3°20′

DAYS_PER_YEAR = 365.25


def _years(y: float) -> timedelta:
    return timedelta(days=y * DAYS_PER_YEAR)


@dataclass(frozen=True)
class Nakshatra:
    index: int  # 0 = Ashwini … 26 = Revati
    pada: int   # 1–4

    @property
    def name(self) -> str:
        return NAKSHATRAS[self.index]

    @property
    def lord(self) -> str:
        return DASHA_SEQUENCE[self.index % 9][0]

    def __str__(self) -> str:
        return f"{self.name} pada {self.pada} (lord {self.lord})"


def nakshatra_of(longitude: float) -> Nakshatra:
    """Nakshatra + pada for a sidereal longitude."""
    lon = longitude % 360.0
    index = int(lon // NAKSHATRA_SPAN)
    pada = int((lon % NAKSHATRA_SPAN) // PADA_SPAN) + 1
    return Nakshatra(index=index, pada=pada)


def nakshatra_table(chart: Chart) -> dict[str, Nakshatra]:
    """Nakshatra + pada for the Lagna and every graha."""
    table = {"Lagna": nakshatra_of(chart.lagna.longitude)}
    for name, pos in chart.planets.items():
        table[name] = nakshatra_of(pos.longitude)
    return table


@dataclass(frozen=True)
class Period:
    """A dasha period. All datetimes are timezone-aware UTC."""

    lord: str
    start: datetime
    end: datetime

    @property
    def years(self) -> float:
        return (self.end - self.start).total_seconds() / (DAYS_PER_YEAR * 86400)

    def contains(self, when: datetime) -> bool:
        return self.start <= when < self.end


@dataclass(frozen=True)
class MahaDasha(Period):
    antardashas: tuple[Period, ...] = ()


@dataclass(frozen=True)
class VimshottariTimeline:
    """Full 120-year Vimshottari timeline.

    The first Mahadasha's `start` is its *notional* start (before birth):
    the Moon had already traversed part of its nakshatra, so only the
    balance of that MD runs after birth. Clip at `birth` for display.
    """

    birth: datetime
    moon_nakshatra: Nakshatra
    balance_years: float  # of the first MD remaining at birth
    mahadashas: tuple[MahaDasha, ...]

    def at(self, when: datetime) -> tuple[MahaDasha, Period] | None:
        """(Mahadasha, Antardasha) running at `when`, or None if outside."""
        for md in self.mahadashas:
            if md.contains(when):
                for ad in md.antardashas:
                    if ad.contains(when):
                        return md, ad
                return md, md.antardashas[-1]  # float-edge fallback
        return None


def _antardashas(md_lord_index: int, start: datetime, md_years: float,
                 md_end: datetime) -> tuple[Period, ...]:
    """The nine ADs of an MD, beginning with the MD lord's own AD."""
    ads = []
    t = start
    for j in range(9):
        lord, ad_years = DASHA_SEQUENCE[(md_lord_index + j) % 9]
        end = md_end if j == 8 else t + _years(md_years * ad_years / TOTAL_YEARS)
        ads.append(Period(lord=lord, start=t, end=end))
        t = end
    return tuple(ads)


def vimshottari(chart: Chart) -> VimshottariTimeline:
    """Build the full MD/AD timeline from the natal Moon."""
    birth = chart.birth.utc_datetime
    moon_lon = chart.planets["Moon"].longitude
    nak = nakshatra_of(moon_lon)

    first_index = nak.index % 9
    first_years = DASHA_SEQUENCE[first_index][1]
    elapsed_fraction = (moon_lon % NAKSHATRA_SPAN) / NAKSHATRA_SPAN
    notional_start = birth - _years(first_years * elapsed_fraction)

    mahadashas = []
    t = notional_start
    for k in range(9):
        idx = (first_index + k) % 9
        lord, md_years = DASHA_SEQUENCE[idx]
        end = t + _years(md_years)
        mahadashas.append(MahaDasha(
            lord=lord, start=t, end=end,
            antardashas=_antardashas(idx, t, md_years, end),
        ))
        t = end

    return VimshottariTimeline(
        birth=birth,
        moon_nakshatra=nak,
        balance_years=first_years * (1.0 - elapsed_fraction),
        mahadashas=tuple(mahadashas),
    )
