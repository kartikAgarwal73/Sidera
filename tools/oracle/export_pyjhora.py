#!/usr/bin/env python3
"""Export a second implementation's answers for the fictional fixture charts.

WHAT THIS IS
An ORACLE, not a dependency. PyJHora (AGPL-3.0, github.com/naturalstupid/
PyJHora) is a mature, independently written Vedic astrology library. It
computes a great deal that Sidera does not yet: degree-level divisional
charts, bhava arudhas, chara karakas, Ashtakavarga, sphutas, Shadbala. This
script runs it once, off to the side, and writes its answers to
`fixtures_pyjhora.json`. That JSON is the gate the next two milestones are
built against.

WHY IT LIVES OUTSIDE THE APP PACKAGE, AND IS NEVER IMPORTED
Two separate reasons, and both matter:

  1. Licensing. Sidera is AGPL-3.0 already (pyswisseph forces that), so
     linking PyJHora would not change the licence. But an oracle that the
     app imports is no longer an oracle: the moment our answer and its
     answer come from the same code, the agreement proves nothing. The
     value here is that PyJHora shares no line of interpretation code with
     us. `test_hygiene.py` fails if any app module imports `jhora`.

  2. Weight. PyJHora pulls PyQt6, timezonefinder, geopy, numpy and more. A
     web deploy should not carry a GUI toolkit to check a fixture.

So: a scratch venv OUTSIDE the repository, built by `make_oracle.sh`, and
only the resulting JSON is committed.

THE AYANAMSA TRAP
PyJHora's default is `TRUE_PUSHYA`, not Lahiri. Silently accepting it would
produce a fixture that disagrees with every Sidera value by roughly 5
arcminutes and looks like a bug in our engine. This script sets LAHIRI
explicitly in two places — `drik.set_ayanamsa_mode()` and
`const._DEFAULT_AYANAMSA_MODE`, since internal call sites read the latter —
and then RECORDS BOTH VALUES in the output so the file itself carries proof
that the default was not used.

Usage (see make_oracle.sh — it wires the venv up for you):
    python export_pyjhora.py --births births.json --out fixtures_pyjhora.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone

# Import order matters: the ayanamsa must be pinned before anything computes.
from jhora import const, utils                                  # noqa: E402
from jhora.panchanga import drik                                # noqa: E402

AYANAMSA_MODE = "LAHIRI"
PYJHORA_DEFAULT_MODE = "TRUE_PUSHYA"   # what we are deliberately NOT using


def pin_ayanamsa() -> None:
    """Set Lahiri everywhere PyJHora looks for it.

    `set_ayanamsa_mode` sets the swisseph sidereal mode, but several PyJHora
    internals re-read `const._DEFAULT_AYANAMSA_MODE` and would quietly put
    True Pushya back. Both are set, and `verify_ayanamsa` proves it took.
    """
    const._DEFAULT_AYANAMSA_MODE = AYANAMSA_MODE
    drik.set_ayanamsa_mode(AYANAMSA_MODE)
    set_node_mode(not USE_MEAN_NODES)


def verify_ayanamsa(jd: float) -> dict:
    """The Lahiri and True Pushya values at this moment, and the gap.

    Recorded in the output so a reader can confirm from the file alone which
    ayanamsa produced it — the two differ by several arcminutes, which is
    far larger than any disagreement we would tolerate between ephemerides.
    """
    pin_ayanamsa()
    lahiri = drik.get_ayanamsa_value(jd)
    drik.set_ayanamsa_mode(PYJHORA_DEFAULT_MODE)
    pushya = drik.get_ayanamsa_value(jd)
    pin_ayanamsa()                       # leave it pinned, always
    again = drik.get_ayanamsa_value(jd)
    if abs(again - lahiri) > 1e-9:
        raise SystemExit("ayanamsa did not stay pinned to LAHIRI")
    return {
        "mode": AYANAMSA_MODE,
        "value_deg": round(lahiri, 8),
        "pyjhora_default_mode": PYJHORA_DEFAULT_MODE,
        "pyjhora_default_value_deg": round(pushya, 8),
        "difference_arcsec": round((lahiri - pushya) * 3600.0, 3),
    }


# --- the OTHER trap: mean node vs true node ---------------------------------
# Sidera computes Rahu from swisseph's MEAN node (engine.py says so). PyJHora
# defaults to the TRUE node. Neither is wrong — the tradition and the software
# both split on it — but they differ by up to ~1.8°, which is enough to move a
# node into the next sign and change every arudha, chara karaka and house
# placement that depends on it. On the partner fixture the gap is 1.48°.
#
# Left alone, that difference would show up in this file as an apparent Sidera
# bug. So the oracle is run with MEAN nodes to match, and the true-node
# positions are recorded alongside so the divergence stays visible and either
# convention can be gated later.
USE_MEAN_NODES = True


def set_node_mode(use_true: bool) -> None:
    """Switch PyJHora between true and mean nodes, all the way down.

    `const.set_node_mode` updates the constants, but `drik`'s planet tables
    were built from them at import time and keep the old swisseph body id.
    Rebuilding those dicts is what actually changes the answer.
    """
    const.set_node_mode(use_true)
    for table in (drik._sidereal_planet_list, drik._tropical_planet_list,
                  drik.planet_list):
        for key in [k for k, v in list(table.items())
                    if v in (const.RAHU_ID, const.KETU_ID)]:
            table.pop(key)
        table[const._RAHU] = const.RAHU_ID
        table[const._KETU] = const.KETU_ID


SIGNS = ("Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra",
         "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces")
BODIES = ("Lagna", "Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus",
          "Saturn", "Rahu", "Ketu")

# PyJHora returns [[body, (rasi, longitude_in_sign)], ...] with the Lagna
# first and the planets in Sun..Ketu order.
SEVEN = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn")

# Chara karaka names. PyJHora ships the 8-karaka (Jaimini, Rahu included)
# scheme only; the 7-karaka list is derived below from its own longitudes.
KARAKA_8 = ("Atma", "Amatya", "Bhratri", "Matri", "Pitri", "Putra",
            "Jnati", "Dara")
KARAKA_7 = ("Atma", "Amatya", "Bhratri", "Matri", "Putra", "Jnati", "Dara")

SHADBALA_ROWS = ("sthana_bala", "kaala_bala", "dig_bala", "cheshta_bala",
                 "naisargika_bala", "drik_bala", "total_shashtiamsas",
                 "total_rupas", "strength_ratio")


def positions(pp) -> dict:
    """PyJHora's position list as {body: {sign, degree, longitude}}."""
    out = {}
    for body, (rasi, lon_in_sign) in pp[:len(BODIES)]:
        name = "Lagna" if body == const._ascendant_symbol else BODIES[
            int(body) + 1]
        rasi = int(rasi) % 12
        out[name] = {
            "sign_index": rasi,
            "sign": SIGNS[rasi],
            "degree_in_sign": round(float(lon_in_sign), 6),
            "longitude": round(rasi * 30.0 + float(lon_in_sign), 6),
        }
    return out


def divisional_charts(jd, place) -> dict:
    """Every standard Dn, WITH the degree inside the divisional sign.

    Sidera computes D9 and D10 to the sign only. This is the half it does
    not have, and the reason milestone 3 is gated on this file.
    """
    from jhora.horoscope.chart import charts
    out = {}
    for dvf in const.division_chart_factors:
        pin_ayanamsa()
        pp = charts.divisional_chart(jd, place, divisional_chart_factor=dvf)
        out[f"D{dvf}"] = positions(pp)
    return out


def _arudhas_under(pp, scorpio_lord, aquarius_lord) -> list[int]:
    """A1..A12 with the Sc/Aq co-lord question decided one way.

    PyJHora exposes exactly the switch the two schools turn on:
    `const.scorpio_owner_for_dhasa_calculations` / `..aquarius..`. Left None
    it takes the STRONGER co-lord (Jaimini); forced to Mars/Saturn it takes
    the Parashari sole lord.
    """
    from jhora.horoscope.chart import arudhas
    saved = (const.scorpio_owner_for_dhasa_calculations,
             const.aquarius_owner_for_dhasa_calculations)
    const.scorpio_owner_for_dhasa_calculations = scorpio_lord
    const.aquarius_owner_for_dhasa_calculations = aquarius_lord
    try:
        return [int(r) for r in
                arudhas.bhava_arudhas_from_planet_positions(pp)]
    finally:
        (const.scorpio_owner_for_dhasa_calculations,
         const.aquarius_owner_for_dhasa_calculations) = saved


def arudha_block(pp) -> dict:
    """A1-A12 under BOTH schools, with the Upapada called out.

    THE TWO SCHOOLS, AND WHY BOTH ARE HERE
    An arudha is counted from the lord of the house. Scorpio and Aquarius
    have two lords each — Mars/Ketu and Saturn/Rahu — and the tradition does
    not speak with one voice about which to count from:

      Parashari  the sole classical lord: Mars for Scorpio, Saturn for
                 Aquarius. The nodes own no sign.
      Jaimini    the STRONGER of the two co-lords, by the Jaimini strength
                 rules. Ketu or Rahu can therefore carry the count.

    Upapada Lagna (UL) is the arudha of the 12th house, so it inherits the
    disagreement whenever the 12th is Scorpio or Aquarius — and UL is read
    for marriage, where being wrong is not academic. Sidera will expose both
    and name the school rather than pick a winner silently, the same way
    `gunamilan.py` handles the yoni and vasya splits.
    """
    parashari = _arudhas_under(pp, const.MARS_ID, const.SATURN_ID)
    jaimini = _arudhas_under(pp, None, None)
    lagna_sign = int(pp[0][1][0]) % 12
    house_signs = [(lagna_sign + h) % 12 for h in range(12)]
    contested = [h + 1 for h, s in enumerate(house_signs)
                 if SIGNS[s] in ("Scorpio", "Aquarius")]
    return {
        "note": ("A1..A12 as SIGN INDICES (0=Aries). A12 is the Upapada "
                 "Lagna. The two schools differ only where a counted house "
                 "is Scorpio or Aquarius."),
        "parashari": {
            "rule": "sole classical lord — Mars for Scorpio, Saturn for "
                    "Aquarius",
            "arudhas": parashari,
            "arudha_signs": [SIGNS[a] for a in parashari],
            "upapada_sign_index": parashari[11],
            "upapada_sign": SIGNS[parashari[11]],
        },
        "jaimini": {
            "rule": "stronger of the two co-lords — Mars/Ketu, Saturn/Rahu",
            "arudhas": jaimini,
            "arudha_signs": [SIGNS[a] for a in jaimini],
            "upapada_sign_index": jaimini[11],
            "upapada_sign": SIGNS[jaimini[11]],
        },
        "schools_agree": parashari == jaimini,
        "houses_where_schools_differ": [
            {"house": h + 1,
             "parashari": SIGNS[parashari[h]],
             "jaimini": SIGNS[jaimini[h]]}
            for h in range(12) if parashari[h] != jaimini[h]],
        "houses_that_are_scorpio_or_aquarius": contested,
        "upapada_contested_in_this_chart": 12 in contested,
    }


def chara_karakas(pp) -> dict:
    """Both karaka schemes.

    The 8-karaka list is PyJHora's own. The 7-karaka list is DERIVED here
    from PyJHora's longitudes by dropping Rahu — the library does not ship
    it — so it is a weaker gate than the rest of this file and is labelled
    so rather than passed off as oracle output.
    """
    from jhora.horoscope.chart import house
    eight = [BODIES[int(p) + 1] for p in house.chara_karakas(pp)]
    # Sun..Rahu with Rahu's longitude reversed within its sign, exactly as
    # PyJHora does it; then sorted by degree descending.
    rows = []
    for idx, (body, (_rasi, lon)) in enumerate(pp[1:len(BODIES) - 1]):
        deg = float(lon)
        if BODIES[int(body) + 1] == "Rahu":
            deg = 30.0 - deg
        rows.append((BODIES[int(body) + 1], deg))
    seven = [name for name, _ in
             sorted([r for r in rows if r[0] != "Rahu"],
                    key=lambda r: r[1], reverse=True)]
    return {
        "eight_karaka": {
            "source": "PyJHora house.chara_karakas() — Rahu included",
            "order": eight,
            "assignment": dict(zip(KARAKA_8, eight)),
        },
        "seven_karaka": {
            "source": "DERIVED HERE from PyJHora longitudes by excluding "
                      "Rahu; PyJHora ships the 8-karaka scheme only",
            "order": seven,
            "assignment": dict(zip(KARAKA_7, seven)),
        },
    }


def ashtakavarga(pp) -> dict:
    """Raw BAV and SAV — per SIGN, before any reduction.

    Two things this file has to be unambiguous about, because both are easy
    to get wrong when reading a screenshot:

      * The arrays are indexed by SIGN (0=Aries), not by house. Sidera's
        dashboard will present them by house; the conversion is ours to do
        and must not be assumed here.
      * These are RAW bindus. No trikona or ekadhipatya sodhana has been
        applied. Reductions are deferred in Sidera too, and comparing a raw
        table against a reduced one is the classic false failure.

    SAV excludes the Lagna's BAV row, which is why seven rows sum to it and
    eight do not.
    """
    from jhora.horoscope.chart import ashtakavarga as av
    h_to_p = utils.get_house_planet_list_from_planet_positions(pp)
    bav_rows, sav, _prastara = av.get_ashtaka_varga(h_to_p)
    bav = {name: [int(v) for v in bav_rows[i]]
           for i, name in enumerate(SEVEN)}
    lagna_row = [int(v) for v in bav_rows[7]]
    return {
        "note": ("RAW bindus, indexed by SIGN (0=Aries, 11=Pisces). No "
                 "trikona or ekadhipatya sodhana applied. SAV is the sum of "
                 "the seven planetary BAVs; the Lagna row is reported "
                 "separately and is NOT part of SAV. NOTE ON THE 337 "
                 "CHECKSUM: bav_totals and sav_total are the SAME for every "
                 "chart — they count rows in the classical benefic-point "
                 "tables, which do not depend on any birth moment. They "
                 "gate the tables, not a chart. The per-sign arrays are "
                 "what actually varies and what a real comparison must "
                 "use."),
        "bav_by_sign": bav,
        "bav_totals": {name: sum(row) for name, row in bav.items()},
        "lagna_bav_by_sign": lagna_row,
        "lagna_bav_total": sum(lagna_row),
        "sav_by_sign": [int(v) for v in sav],
        "sav_total": int(sum(sav)),
    }


def sphutas(dob, tob, place) -> dict:
    from jhora.horoscope.chart import sphuta as sp
    date_obj = drik.Date(*dob)
    names = ("tri_sphuta", "chatur_sphuta", "pancha_sphuta", "prana_sphuta",
             "deha_sphuta", "mrityu_sphuta", "sookshma_tri_sphuta",
             "beeja_sphuta", "kshetra_sphuta", "tithi_sphuta", "yoga_sphuta",
             "yogi_sphuta", "avayogi_sphuta", "rahu_tithi_sphuta")
    out = {}
    for name in names:
        pin_ayanamsa()
        fn = getattr(sp, name)
        # Some take a Date, some a plain tuple; the ones that reach
        # gulika_longitude need the Date. Try the Date first.
        for first in (date_obj, dob):
            try:
                rasi, lon = fn(first, tob, place)
                break
            except AttributeError:
                continue
        else:                                        # pragma: no cover
            raise SystemExit(f"{name} accepted neither date form")
        rasi = int(rasi) % 12
        out[name] = {
            "sign_index": rasi,
            "sign": SIGNS[rasi],
            "degree_in_sign": round(float(lon), 6),
            "longitude": round(rasi * 30.0 + float(lon), 6),
        }
    return out


def shadbala(jd, place) -> dict:
    from jhora.horoscope.chart import strength
    pin_ayanamsa()
    rows = strength.shad_bala(jd, place)
    return {
        "note": ("Six components in shashtiamsas, then their sum, the same "
                 "in rupas (/60), and the ratio to the classical required "
                 "strength. Sun..Saturn only — the nodes have no shadbala."),
        "components": {
            label: dict(zip(SEVEN, [round(float(v), 4) for v in row]))
            for label, row in zip(SHADBALA_ROWS, rows)
        },
    }


def export_chart(name: str, birth: dict) -> dict:
    from jhora.horoscope.chart import charts
    pin_ayanamsa()
    place = drik.Place(birth.get("place", name), float(birth["latitude"]),
                       float(birth["longitude"]), float(birth["tz_hours"]))
    dob = (int(birth["year"]), int(birth["month"]), int(birth["day"]))
    tob = (int(birth["hour"]), int(birth["minute"]), 0)
    jd = utils.julian_day_number(dob, tob)
    ayanamsa = verify_ayanamsa(jd)

    pin_ayanamsa()
    pp = charts.rasi_chart(jd, place)

    # Recorded, not used: everything else in this file is mean-node, to match
    # Sidera. This block is here so the size of the disagreement is on the
    # record rather than discovered later as a mystery.
    set_node_mode(True)
    true_node = positions(charts.rasi_chart(jd, place))
    pin_ayanamsa()
    mean_node = positions(pp)
    node_gap = {
        body: round(abs((mean_node[body]["longitude"]
                         - true_node[body]["longitude"] + 180) % 360 - 180)
                    * 3600.0, 2)
        for body in ("Rahu", "Ketu")
    }

    return {
        "birth": {**{k: birth[k] for k in
                     ("year", "month", "day", "hour", "minute",
                      "latitude", "longitude", "place")},
                  "tz_hours": birth["tz_hours"]},
        "julian_day_ut": round(jd, 9),
        "ayanamsa": ayanamsa,
        "rasi": mean_node,
        "nodes": {
            "note": ("Everything in this chart uses the MEAN node, matching "
                     "Sidera's engine. PyJHora's own default is the TRUE "
                     "node; those positions are recorded here only so the "
                     "divergence is visible. Both conventions are standard "
                     "and the tradition splits on which to use."),
            "used": "mean",
            "true_node_positions": {b: true_node[b]
                                    for b in ("Rahu", "Ketu")},
            "mean_minus_true_arcsec": node_gap,
        },
        "divisional_charts": divisional_charts(jd, place),
        "bhava_arudhas": arudha_block(pp),
        "chara_karakas": chara_karakas(pp),
        "ashtakavarga": ashtakavarga(pp),
        "sphutas": sphutas(dob, tob, place),
        "shadbala": shadbala(jd, place),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--births", required=True,
                    help="JSON {name: {year, month, ..., tz_hours}} — "
                         "written by make_oracle.sh from fixtures.py")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    births = json.loads(open(args.births, encoding="utf-8").read())
    try:
        import swisseph as swe
        swe_version = swe.version
    except Exception:                                # pragma: no cover
        swe_version = "unknown"
    from jhora import _package_info

    charts_out = {name: export_chart(name, birth)
                  for name, birth in sorted(births.items())}
    payload = {
        "_README": (
            "ORACLE FIXTURE. Computed by PyJHora (AGPL-3.0), an independent "
            "Vedic astrology implementation that Sidera does not link, "
            "import or ship. Regenerate with tools/oracle/make_oracle.sh. "
            "Every chart here is FICTIONAL — see fixtures.py. Treat these "
            "values as EXTERNAL: if a Sidera test against them goes red, "
            "the presumption is that Sidera is wrong."),
        "generator": "tools/oracle/export_pyjhora.py",
        "generated_at_utc": datetime.now(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"),
        "oracle": {
            "package": "PyJHora",
            "version": getattr(_package_info, "version", "unknown"),
            "licence": "AGPL-3.0",
            "url": "https://github.com/naturalstupid/PyJHora",
            "pyswisseph": swe_version,
            "python": sys.version.split()[0],
        },
        "settings": {
            "ayanamsa_mode": AYANAMSA_MODE,
            "ayanamsa_note": (
                "PyJHora's own default is TRUE_PUSHYA. It is overridden here "
                "in both places the library reads it. Each chart records the "
                "Lahiri and True Pushya values so the file proves which was "
                "used."),
            "house_system": "whole sign (PyJHora rasi chart)",
            "node_mode": "mean",
            "node_note": (
                "PyJHora's own default is the TRUE node; Sidera uses the "
                "MEAN node, so the oracle is run with mean nodes and the "
                "true-node positions are recorded per chart for reference. "
                "The two differ by up to ~1.8°, enough to move a node "
                "between signs."),
        },
        "charts": charts_out,
    }
    body = json.dumps(payload, indent=1, sort_keys=True, ensure_ascii=False)
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()[:16]
    payload["content_sha256_16"] = digest
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, indent=1, sort_keys=True,
                            ensure_ascii=False) + "\n")
    print(f"wrote {args.out}: {len(charts_out)} chart(s), digest {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
