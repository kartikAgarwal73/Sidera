"""Core Vedic astrology calculation engine.

All ephemeris work is done by pyswisseph — nothing is approximated manually.
Zodiac: sidereal, Lahiri ayanamsa. Houses: Whole Sign from the Lagna.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import swisseph as swe

SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]

# Order matters: this is the canonical display order for the nine grahas.
PLANETS = [
    "Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu",
]

_SWE_BODY = {
    "Sun": swe.SUN,
    "Moon": swe.MOON,
    "Mars": swe.MARS,
    "Mercury": swe.MERCURY,
    "Jupiter": swe.JUPITER,
    "Venus": swe.VENUS,
    "Saturn": swe.SATURN,
    "Rahu": swe.MEAN_NODE,  # mean node per spec; Ketu derived as Rahu + 180°
}

_CALC_FLAGS = swe.FLG_SWIEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED

_OFFSET_RE = re.compile(r"^(UTC)?([+-])(\d{1,2}):?(\d{2})$")


_EPHE_PATH_SET = False


def _init_sidereal() -> None:
    """(Re)assert Lahiri ayanamsa before any calculation.

    swisseph sidereal mode is global process state; other code (or tests)
    could change it, so every public entry point re-sets it.

    Also points swisseph at bundled ephemeris files when SE_EPHE_PATH is
    given. The path is resolved relative to this file, so it works
    identically on a laptop and on a container with a different working
    directory.
    """
    global _EPHE_PATH_SET
    if not _EPHE_PATH_SET:
        configured = os.environ.get("SE_EPHE_PATH", "").strip()
        if configured:
            path = Path(configured)
            if not path.is_absolute():
                path = Path(__file__).resolve().parent / path
            swe.set_ephe_path(str(path))
        _EPHE_PATH_SET = True
    swe.set_sid_mode(swe.SIDM_LAHIRI)


def ephemeris_backend() -> str:
    """Which ephemeris swisseph actually served — 'swieph' | 'moseph' | 'jpl'.

    This build ships NO .se1 files. swisseph therefore falls back from the
    requested SWIEPH to its built-in Moshier analytical ephemeris, which is
    accurate to well under an arcsecond over any date this app handles and
    needs no data files at all — which is why the app deploys to a container
    with nothing to mount.

    The fallback is silent inside swisseph, so it is surfaced here and
    asserted in the suite: if someone later adds .se1 files via SE_EPHE_PATH,
    that is a change of numerical source and the gate values must be
    re-verified, not assumed.
    """
    _init_sidereal()
    jd = swe.julday(2000, 1, 1, 12.0)
    _vals, retflag = swe.calc_ut(jd, swe.SUN, _CALC_FLAGS)
    if retflag & swe.FLG_JPLEPH:
        return "jpl"
    if retflag & swe.FLG_SWIEPH:
        return "swieph"
    return "moseph"


def resolve_timezone(tz: str):
    """Accept an IANA name ('Asia/Kolkata') or a fixed offset ('+05:30')."""
    m = _OFFSET_RE.match(tz.strip())
    if m:
        sign = 1 if m.group(2) == "+" else -1
        delta = timedelta(hours=int(m.group(3)), minutes=int(m.group(4)))
        return timezone(sign * delta, name=tz.strip())
    return ZoneInfo(tz)


def julian_day_ut(when: datetime) -> float:
    """Julian Day (UT) for a timezone-aware datetime."""
    if when.tzinfo is None:
        raise ValueError("datetime must be timezone-aware")
    ut = when.astimezone(timezone.utc)
    return swe.julday(
        ut.year, ut.month, ut.day,
        ut.hour + ut.minute / 60.0 + ut.second / 3600.0,
    )


@dataclass(frozen=True)
class BirthData:
    """A birth event: local wall-clock time plus place coordinates."""

    year: int
    month: int
    day: int
    hour: int
    minute: int
    latitude: float
    longitude: float
    tz: str  # IANA name (e.g. 'Asia/Kolkata') or fixed offset (e.g. '+05:30')
    place: str = ""
    second: int = 0

    @property
    def local_datetime(self) -> datetime:
        return datetime(
            self.year, self.month, self.day, self.hour, self.minute, self.second,
            tzinfo=resolve_timezone(self.tz),
        )

    @property
    def utc_datetime(self) -> datetime:
        return self.local_datetime.astimezone(timezone.utc)

    @property
    def julian_day_ut(self) -> float:
        ut = self.utc_datetime
        return swe.julday(
            ut.year, ut.month, ut.day,
            ut.hour + ut.minute / 60.0 + ut.second / 3600.0,
        )


@dataclass(frozen=True)
class Position:
    """A sidereal zodiac position."""

    longitude: float  # 0–360 sidereal
    speed: float = 0.0  # deg/day; negative means retrograde

    @property
    def sign_index(self) -> int:
        return int(self.longitude // 30) % 12

    @property
    def sign(self) -> str:
        return SIGNS[self.sign_index]

    @property
    def degree_in_sign(self) -> float:
        return self.longitude % 30

    @property
    def retrograde(self) -> bool:
        return self.speed < 0

    @property
    def dms(self) -> str:
        d = self.degree_in_sign
        deg = int(d)
        minutes_f = (d - deg) * 60
        mins = int(minutes_f)
        secs = int(round((minutes_f - mins) * 60))
        if secs == 60:
            secs, mins = 0, mins + 1
        if mins == 60:
            mins, deg = 0, deg + 1
        return f"{deg}°{mins:02d}′{secs:02d}″"


@dataclass(frozen=True)
class PlanetPosition(Position):
    name: str = ""
    house: int = 0  # Whole Sign house from Lagna, 1–12


@dataclass(frozen=True)
class Chart:
    birth: BirthData
    lagna: Position
    planets: dict[str, PlanetPosition]
    ayanamsa: float

    @property
    def house_signs(self) -> dict[int, str]:
        """Whole Sign: house n occupies the nth sign counted from the Lagna sign."""
        first = self.lagna.sign_index
        return {h: SIGNS[(first + h - 1) % 12] for h in range(1, 13)}

    @property
    def houses(self) -> dict[int, list[str]]:
        """Planets occupying each house (1–12)."""
        out: dict[int, list[str]] = {h: [] for h in range(1, 13)}
        for name in PLANETS:
            out[self.planets[name].house].append(name)
        return out


def _house_of(sign_index: int, lagna_sign_index: int) -> int:
    return (sign_index - lagna_sign_index) % 12 + 1


def compute_lagna(birth: BirthData) -> Position:
    """Sidereal ascendant via swisseph (Whole Sign house system)."""
    _init_sidereal()
    _cusps, ascmc = swe.houses_ex(
        birth.julian_day_ut, birth.latitude, birth.longitude, b"W", _CALC_FLAGS
    )
    return Position(longitude=ascmc[0])


def sidereal_positions(jd_ut: float) -> dict[str, Position]:
    """Sidereal longitudes + speeds for the nine grahas at any moment.

    Used both for natal charts and (later) transits, so both always go
    through the identical ephemeris path.
    """
    _init_sidereal()
    out: dict[str, Position] = {}
    for name in PLANETS:
        if name == "Ketu":
            continue  # derived from Rahu below
        (lon, _lat, _dist, speed_lon, _slat, _sdist), _ = swe.calc_ut(
            jd_ut, _SWE_BODY[name], _CALC_FLAGS
        )
        out[name] = Position(longitude=lon, speed=speed_lon)
    rahu = out["Rahu"]
    # Ketu moves with Rahu; mean node speed is negative (retro).
    out["Ketu"] = Position(
        longitude=(rahu.longitude + 180.0) % 360.0, speed=rahu.speed
    )
    return out


def compute_chart(birth: BirthData) -> Chart:
    """Full sidereal chart: Lagna + nine grahas with Whole Sign house placement."""
    jd = birth.julian_day_ut
    lagna = compute_lagna(birth)

    planets = {
        name: PlanetPosition(
            longitude=pos.longitude,
            speed=pos.speed,
            name=name,
            house=_house_of(pos.sign_index, lagna.sign_index),
        )
        for name, pos in sidereal_positions(jd).items()
    }

    return Chart(
        birth=birth,
        lagna=lagna,
        planets=planets,
        ayanamsa=swe.get_ayanamsa_ut(jd),
    )
