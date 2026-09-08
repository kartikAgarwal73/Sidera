#!/usr/bin/env python3
"""Batch side of the differential test — runs INSIDE the oracle venv.

Reads a records file, computes PyJHora's answer for each, writes them out.
Knows nothing about Sidera: it cannot import it (different venv), and the
comparison happens in `differential.py` on the other side of this JSON.

Everything here is pinned the same way `export_pyjhora.py` pins it — Lahiri
ayanamsa, mean nodes — for the same reasons, and both defaults are recorded
per run so a report cannot be mistaken for one produced with the defaults.

Usage (differential.py drives this; you should not need to):
    python oracle_answers.py --records records.json --out answers.json
"""
from __future__ import annotations

import argparse
import json
import sys

from jhora import const, utils
from jhora.panchanga import drik

AYANAMSA_MODE = "LAHIRI"
PYJHORA_DEFAULT_MODE = "TRUE_PUSHYA"
USE_MEAN_NODES = True

# THE THIRD DEFAULT, found by this test rather than by reading the source.
# PyJHora sets swisseph's FLG_TRUEPOS — the true geometric position, with no
# light-time correction. Sidera does not, so it computes apparent positions,
# which is what almanacs publish and what the Sun's classic 20.2″ offset is
# the signature of. Clearing the flag makes the two ephemerides agree to the
# last printed digit; every residual arcsecond in the fixture comparison was
# this and nothing else.
#
# `--positions apparent` matches Sidera, which is what isolates a LOGIC
# disagreement from a convention one. `--positions true` leaves PyJHora at its
# own default and measures what the convention actually costs.
import swisseph as swe                                          # noqa: E402

BODIES = ("Lagna", "Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus",
          "Saturn", "Rahu", "Ketu")
DASHA_LORDS = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus",
               "Saturn", "Rahu", "Ketu")


def set_node_mode(use_true: bool) -> None:
    """Switch nodes all the way down — see export_pyjhora.py for why the
    `drik` planet tables have to be rebuilt as well as the constants."""
    const.set_node_mode(use_true)
    for table in (drik._sidereal_planet_list, drik._tropical_planet_list,
                  drik.planet_list):
        for key in [k for k, v in list(table.items())
                    if v in (const.RAHU_ID, const.KETU_ID)]:
            table.pop(key)
        table[const._RAHU] = const.RAHU_ID
        table[const._KETU] = const.KETU_ID


_POSITIONS = "apparent"
_WANT_TRUE_YEAR = True
_BASE_FLAGS = drik.PLANET_FLAGS


def set_positions(mode: str) -> None:
    global _POSITIONS
    _POSITIONS = mode
    if mode == "apparent":
        drik.PLANET_FLAGS = _BASE_FLAGS & ~swe.FLG_TRUEPOS
    else:
        drik.PLANET_FLAGS = _BASE_FLAGS | swe.FLG_TRUEPOS


def pin() -> None:
    const._DEFAULT_AYANAMSA_MODE = AYANAMSA_MODE
    drik.set_ayanamsa_mode(AYANAMSA_MODE)
    set_node_mode(not USE_MEAN_NODES)
    set_positions(_POSITIONS)


def one(record: dict) -> dict:
    from jhora.horoscope.chart import charts
    from jhora.horoscope.dhasa.graha import vimsottari

    pin()
    place = drik.Place(record.get("place", "x"), float(record["latitude"]),
                       float(record["longitude"]), float(record["tz_hours"]))
    dob = (record["year"], record["month"], record["day"])
    tob = (record["hour"], record["minute"], record["second"])
    jd = utils.julian_day_number(dob, tob)

    out: dict = {"id": record["id"], "julian_day": round(jd, 9),
                 "ayanamsa": round(drik.get_ayanamsa_value(jd), 8)}

    def longitudes(pp) -> dict:
        vals = {}
        for body, (rasi, lon) in pp[:len(BODIES)]:
            name = ("Lagna" if body == const._ascendant_symbol
                    else BODIES[int(body) + 1])
            vals[name] = round((int(rasi) % 12) * 30.0 + float(lon), 8)
        return vals

    pp = charts.rasi_chart(jd, place)
    out["d1"] = longitudes(pp)
    # PyJHora's own nakshatra arithmetic, on PyJHora's own longitudes, so the
    # comparison covers the counting rule and not only the ephemeris.
    out["nakshatra"] = {}
    for body, longitude in out["d1"].items():
        index, pada, _rem = drik.nakshatra_pada(longitude)
        out["nakshatra"][body] = [int(index), int(pada)]

    for dvf in (9, 10):
        pin()
        vp = charts.divisional_chart(jd, place, divisional_chart_factor=dvf)
        out[f"d{dvf}_signs"] = {
            ("Lagna" if b == const._ascendant_symbol
             else BODIES[int(b) + 1]): int(r) % 12
            for b, (r, _lon) in vp[:len(BODIES)]}

    # Vimshottari. PyJHora returns [((md_id, ad_id), (Y,M,D,hours), years)]
    # with the times in the PLACE's local zone, which is also how it read the
    # birth moment. differential.py converts to UTC before comparing.
    #
    # THE YEAR LENGTH IS PINNED, AND THAT IS A FINDING IN ITSELF.
    # PyJHora's default is TRUE_SIDEREAL_YEAR: `drik.true_sidereal_year()`
    # measured for that chart. On some (date, place) pairs that function
    # returns ≈366.2 days — about a day too long, and astronomically
    # impossible, since a sidereal year varies by minutes, not by a day. The
    # dasha timeline then drifts by up to ~112 days over a lifetime. Left
    # unpinned it would fill this report with PyJHora's defect and hide
    # anything real, so the comparison uses MEAN_SIDEREAL_YEAR — the same
    #365.256364 constant Sidera uses — and the raw value is recorded per
    # record below so the incidence can be counted rather than guessed.
    pin()
    # An ephemeris search, and the slowest call in this file. It does not
    # depend on the position flag in any way that matters for counting how
    # often PyJHora's default year is wrong, so it runs in one pass only.
    if _WANT_TRUE_YEAR:
        out["true_sidereal_year"] = round(
            drik.true_sidereal_year(jd, place), 6)
    _seed, rows = vimsottari.get_vimsottari_dhasa_bhukthi(
        jd, place,
        dhasa_duration_type=const.DHASA_YEAR_DURATION.MEAN_SIDEREAL_YEAR)
    out["vimsottari"] = [
        {"md": DASHA_LORDS[int(md)], "ad": DASHA_LORDS[int(ad)],
         "start_local": [int(y), int(m), int(d), float(h)],
         "years": round(float(years), 9)}
        for (md, ad), (y, m, d, h), years in rows]
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--records", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--skip-true-year", action="store_true",
                    help="skip drik.true_sidereal_year(); it is an "
                         "ephemeris search and the slowest call here")
    ap.add_argument("--positions", choices=("apparent", "true"),
                    default="apparent",
                    help="'apparent' clears FLG_TRUEPOS to match Sidera; "
                         "'true' leaves PyJHora at its own default")
    args = ap.parse_args()

    records = json.loads(open(args.records, encoding="utf-8").read())
    global _WANT_TRUE_YEAR
    _WANT_TRUE_YEAR = not args.skip_true_year
    set_positions(args.positions)
    pin()
    probe = utils.julian_day_number((2000, 1, 1), (12, 0, 0))
    lahiri = drik.get_ayanamsa_value(probe)
    drik.set_ayanamsa_mode(PYJHORA_DEFAULT_MODE)
    pushya = drik.get_ayanamsa_value(probe)
    pin()

    answers, failures = [], []
    for i, record in enumerate(records):
        try:
            answers.append(one(record))
        except Exception as exc:                    # recorded, never hidden
            failures.append({"id": record["id"],
                             "error": f"{type(exc).__name__}: {exc}"})
        if (i + 1) % 50 == 0:
            print(f"    {i + 1}/{len(records)}", file=sys.stderr, flush=True)

    payload = {
        "settings": {
            "ayanamsa_mode": AYANAMSA_MODE,
            "node_mode": "mean" if USE_MEAN_NODES else "true",
            "ayanamsa_at_j2000_lahiri": round(lahiri, 8),
            "ayanamsa_at_j2000_pyjhora_default": round(pushya, 8),
            "pyjhora_default_mode": PYJHORA_DEFAULT_MODE,
            "positions": args.positions,
            "dhasa_year": "MEAN_SIDEREAL_YEAR (pinned; PyJHora's own "
                          "TRUE_SIDEREAL_YEAR default is unreliable — see "
                          "true_sidereal_year per record)",
            "mean_sidereal_year": const.sidereal_year,
            "planet_flags": int(drik.PLANET_FLAGS),
            "flg_truepos_set": bool(drik.PLANET_FLAGS & swe.FLG_TRUEPOS),
        },
        "answers": answers,
        "failures": failures,
    }
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh)
    print(f"    oracle: {len(answers)} ok, {len(failures)} failed",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
