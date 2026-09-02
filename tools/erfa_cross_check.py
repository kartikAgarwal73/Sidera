#!/usr/bin/env python3
"""Recompute the reference chart's positions with a SECOND ephemeris.

`TestIndependentEphemerisCrossCheck` in test_gates.py asserts that swisseph
agrees with ERFA to within an arcminute, using constants pasted into the
test. This script is where those constants come from — run it to reproduce
or refresh them.

ERFA (pyerfa) is the Python binding of the IAU's SOFA-derived library. It
shares no code with swisseph, which is the entire point: a suite that only
checks this build against its own ephemeris proves nothing about whether
the ephemeris is being driven correctly.

    pip install pyerfa numpy      # dev-only; NOT an app dependency
    python tools/erfa_cross_check.py

Residuals of a few tens of arcseconds are expected and correct: swisseph
returns apparent positions (light-time and annual aberration applied),
while the ERFA routines used here return geometric ones.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import erfa
import swisseph as swe

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import fixtures                                            # noqa: E402
from engine import SIGNS, _init_sidereal, compute_chart    # noqa: E402

# TAI-UTC was 31s from 1997-07-01 to 1999-01-01; TT = TAI + 32.184s.
_LEAP_SECONDS_1998 = 31.0
_TT_MINUS_TAI = 32.184


def erfa_sidereal(birth) -> tuple[dict[str, float], float, float]:
    """(planet → sidereal longitude, lagna, ayanamsa) computed via ERFA."""
    jd_ut = birth.julian_day_ut
    tt = jd_ut + (_LEAP_SECONDS_1998 + _TT_MINUS_TAI) / 86400.0
    tt1, tt2 = 2400000.5, tt - 2400000.5

    heliocentric, _barycentric = erfa.epv00(tt1, tt2)
    earth = np.array(heliocentric[0])
    to_ecliptic = erfa.ecm06(tt1, tt2)   # ICRS → ecliptic of date

    def longitude(vec) -> float:
        e = to_ecliptic @ vec
        return np.degrees(np.arctan2(e[1], e[0])) % 360.0

    tropical = {
        "Sun": longitude(-earth),                                # epv00
        "Moon": longitude(np.array(erfa.moon98(tt1, tt2)[0])),   # ELP/Meeus
    }
    for name, body in (("Mercury", 1), ("Venus", 2), ("Mars", 4),
                       ("Jupiter", 5), ("Saturn", 6)):           # plan94
        tropical[name] = longitude(
            np.array(erfa.plan94(tt1, tt2, body)[0]) - earth)
    # Mean lunar node straight from the IAU fundamental argument.
    tropical["Rahu"] = np.degrees(
        erfa.faom03((tt - 2451545.0) / 36525.0)) % 360.0

    # Ascendant from apparent sidereal time and the obliquity of date.
    lat = np.radians(birth.latitude)
    gst = erfa.gst06a(2400000.5, jd_ut - 2400000.5, tt1, tt2)
    lst = (gst + np.radians(birth.longitude)) % (2 * np.pi)
    eps = erfa.obl06(tt1, tt2)
    lagna = np.degrees(np.arctan2(
        np.cos(lst),
        -(np.sin(lst) * np.cos(eps) + np.tan(lat) * np.sin(eps)))) % 360.0

    _init_sidereal()
    ayanamsa = swe.get_ayanamsa_ut(jd_ut)
    sidereal = {k: (v - ayanamsa) % 360.0 for k, v in tropical.items()}
    return sidereal, (lagna - ayanamsa) % 360.0, ayanamsa


def _fmt(lon: float) -> str:
    return f"{SIGNS[int(lon // 30)]:>11s} {lon % 30:8.4f}"


def main() -> int:
    birth = fixtures.birth("reference")
    sidereal, lagna, ayanamsa = erfa_sidereal(birth)
    chart = compute_chart(birth)

    print(f"instant   {birth.utc_datetime}  (JD_UT {birth.julian_day_ut})")
    print(f"ayanamsa  {ayanamsa:.6f}  (Lahiri)\n")
    print(f'{"":9s} {"ERFA":>20s} {"swisseph":>20s}      diff')

    worst = 0.0
    for name, expected in sidereal.items():
        got = chart.planets[name].longitude
        delta = abs((got - expected + 180) % 360 - 180) * 3600
        worst = max(worst, delta)
        print(f"{name:9s} {_fmt(expected)} {_fmt(got)}  {delta:8.1f}\"")
    delta = abs((chart.lagna.longitude - lagna + 180) % 360 - 180) * 3600
    worst = max(worst, delta)
    print(f'{"Lagna":9s} {_fmt(lagna)} {_fmt(chart.lagna.longitude)}'
          f'  {delta:8.1f}"')

    print(f"\nworst disagreement: {worst:.1f}\" "
          f"({'within' if worst <= 60 else 'OUTSIDE'} the 1′ gate tolerance)")
    print("\nConstants for TestIndependentEphemerisCrossCheck:")
    for name, lon in sidereal.items():
        print(f'        "{name}": {lon:.4f},')
    print(f"    ERFA_LAGNA = {lagna:.4f}")
    return 0 if worst <= 60 else 1


if __name__ == "__main__":
    raise SystemExit(main())
