"""Pañcāṅga — the five limbs of the day.

Domain contract from the build framework (THREE · DOMAIN MODEL):
    Pancanga = { tithi: {id, name, paksa, endsAt}, nakshatra: {id, endsAt},
                 yoga, karana, sunrise, sunset, weekday }

Pure functions over ephemeris output — the moment is always an argument,
never read from the clock. All instants are timezone-aware UTC.

Arithmetic (sidereal, Lahiri — consistent with the rest of the engine):
    elongation = Moon − Sun.  tithi = elongation ÷ 12°  (30 per lunation)
                              karana = elongation ÷ 6°  (60 per lunation)
    yoga       = (Sun + Moon) ÷ 13°20′                  (27 per cycle)
    nakshatra  = Moon ÷ 13°20′
Ayanāṃśa cancels in the tithi/karana difference but not in the yoga sum,
which is why the yoga is taken from sidereal longitudes here.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import swisseph as swe

from dashas import NAKSHATRAS, nakshatra_of
from engine import BirthData, julian_day_ut, sidereal_positions

TITHI_NAMES = [
    "Pratipadā", "Dvitīyā", "Tṛtīyā", "Caturthī", "Pañcamī", "Ṣaṣṭhī",
    "Saptamī", "Aṣṭamī", "Navamī", "Daśamī", "Ekādaśī", "Dvādaśī",
    "Trayodaśī", "Caturdaśī",
]  # the 15th is Pūrṇimā (śukla) or Amāvāsyā (kṛṣṇa)

YOGA_NAMES = [
    "Viṣkambha", "Prīti", "Āyuṣmān", "Saubhāgya", "Śobhana", "Atigaṇḍa",
    "Sukarman", "Dhṛti", "Śūla", "Gaṇḍa", "Vṛddhi", "Dhruva", "Vyāghāta",
    "Harṣaṇa", "Vajra", "Siddhi", "Vyatīpāta", "Varīyān", "Parigha", "Śiva",
    "Siddha", "Sādhya", "Śubha", "Śukla", "Brahma", "Indra", "Vaidhṛti",
]

# Seven movable karanas cycle eight times (karanas 2–57); four fixed karanas
# bracket the lunation.
MOVABLE_KARANAS = ["Bava", "Bālava", "Kaulava", "Taitila", "Gara", "Vaṇija",
                   "Viṣṭi"]
WEEKDAY_NAMES = ["Somavāra", "Maṅgalavāra", "Budhavāra", "Guruvāra",
                 "Śukravāra", "Śanivāra", "Ravivāra"]  # Python Mon=0 … Sun=6
WEEKDAY_LORDS = ["Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn",
                 "Sun"]

TITHI_SPAN = 12.0
KARANA_SPAN = 6.0
YOGA_SPAN = 360.0 / 27.0
NAKSHATRA_SPAN = 360.0 / 27.0


@dataclass(frozen=True)
class Anga:
    """One limb: its index, display name, and the instant it gives way."""

    index: int          # 1-based
    name: str
    ends_at: datetime | None

    @property
    def ends_label(self) -> str:
        return self.ends_at.strftime("%d %b %H:%M UTC") if self.ends_at else "—"


@dataclass(frozen=True)
class Pancanga:
    when: datetime
    tithi: Anga
    paksa: str          # 'śukla' | 'kṛṣṇa'
    nakshatra: Anga
    yoga: Anga
    karana: Anga
    sunrise: datetime | None
    sunset: datetime | None
    weekday: int        # 0 = Monday … 6 = Sunday
    moon_phase: float   # 0–1 of the lunation elapsed

    @property
    def weekday_name(self) -> str:
        return WEEKDAY_NAMES[self.weekday]

    @property
    def weekday_lord(self) -> str:
        return WEEKDAY_LORDS[self.weekday]

    @property
    def tithi_label(self) -> str:
        return f"{self.paksa} {self.tithi.name}"


def _angles(jd: float) -> tuple[float, float]:
    """(elongation, yoga-sum) in degrees at a Julian day."""
    pos = sidereal_positions(jd)
    sun, moon = pos["Sun"].longitude, pos["Moon"].longitude
    return (moon - sun) % 360.0, (sun + moon) % 360.0


def _crossing(when: datetime, value_fn, span: float,
              max_days: float, step_hours: float = 3.0) -> datetime | None:
    """When does `value_fn` next cross the top of its current span?

    Coarse forward scan then bisection to the minute. Works for any of the
    monotonic-in-practice angas (tithi, karana, yoga, nakṣatra).
    """
    start_index = int(value_fn(julian_day_ut(when)) // span)

    def moved(dt: datetime) -> bool:
        return int(value_fn(julian_day_ut(dt)) // span) != start_index

    t0 = when
    limit = when + timedelta(days=max_days)
    while t0 < limit:
        t1 = min(t0 + timedelta(hours=step_hours), limit)
        if moved(t1):
            lo, hi = t0, t1
            while hi - lo > timedelta(minutes=1):
                mid = lo + (hi - lo) / 2
                if moved(mid):
                    hi = mid
                else:
                    lo = mid
            return hi
        t0 = t1
    return None


def _rise_set(when: datetime, lat: float, lon: float, flag: int):
    """Sunrise or sunset for the day containing `when`, at that place."""
    day_start = when.replace(hour=0, minute=0, second=0, microsecond=0)
    try:
        res, tret = swe.rise_trans(
            julian_day_ut(day_start), swe.SUN, flag | swe.BIT_DISC_CENTER,
            (lon, lat, 0.0))
    except Exception:
        return None
    if res != 0:
        return None  # circumpolar — no event that day
    year, month, day, hour = swe.revjul(tret[0])
    h = int(hour)
    m = int(round((hour - h) * 60))
    if m == 60:
        h, m = h + 1, 0
    base = datetime(year, month, day, tzinfo=timezone.utc)
    return base + timedelta(hours=h, minutes=m)


def karana_name(index: int) -> str:
    """Karana 1–60 → its classical name."""
    if index == 1:
        return "Kiṃstughna"
    if index == 58:
        return "Śakuni"
    if index == 59:
        return "Catuṣpāda"
    if index == 60:
        return "Nāga"
    return MOVABLE_KARANAS[(index - 2) % 7]


def compute_pancanga(when: datetime, latitude: float,
                     longitude: float) -> Pancanga:
    """The five limbs at a moment and place. `when` must be tz-aware."""
    if when.tzinfo is None:
        raise ValueError("datetime must be timezone-aware")
    jd = julian_day_ut(when)
    elongation, yoga_sum = _angles(jd)
    moon_lon = sidereal_positions(jd)["Moon"].longitude

    tithi_index = int(elongation // TITHI_SPAN) + 1          # 1–30
    paksa = "śukla" if tithi_index <= 15 else "kṛṣṇa"
    within = (tithi_index - 1) % 15 + 1                      # 1–15
    if within == 15:
        tithi_name = "Pūrṇimā" if paksa == "śukla" else "Amāvāsyā"
    else:
        tithi_name = TITHI_NAMES[within - 1]

    karana_index = int(elongation // KARANA_SPAN) + 1        # 1–60
    yoga_index = int(yoga_sum // YOGA_SPAN) + 1              # 1–27
    nak = nakshatra_of(moon_lon)

    return Pancanga(
        when=when,
        tithi=Anga(tithi_index, tithi_name,
                   _crossing(when, lambda j: _angles(j)[0], TITHI_SPAN, 1.6)),
        paksa=paksa,
        nakshatra=Anga(nak.index + 1, nak.name,
                       _crossing(when,
                                 lambda j: sidereal_positions(j)["Moon"].longitude,
                                 NAKSHATRA_SPAN, 1.6)),
        yoga=Anga(yoga_index, YOGA_NAMES[yoga_index - 1],
                  _crossing(when, lambda j: _angles(j)[1], YOGA_SPAN, 1.6)),
        karana=Anga(karana_index, karana_name(karana_index),
                    _crossing(when, lambda j: _angles(j)[0], KARANA_SPAN, 1.0)),
        sunrise=_rise_set(when, latitude, longitude, swe.CALC_RISE),
        sunset=_rise_set(when, latitude, longitude, swe.CALC_SET),
        weekday=when.weekday(),
        moon_phase=round(elongation / 360.0, 4),
    )


def pancanga_for(birth: BirthData, when: datetime) -> Pancanga:
    """Today's pañcāṅga at the person's birth place — the almanac frame the
    reading is written against."""
    return compute_pancanga(when, birth.latitude, birth.longitude)
