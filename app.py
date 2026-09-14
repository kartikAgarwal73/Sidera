"""Sidera — single-page Flask UI: birth form → dashboard.

Implements the "Colophon" direction from ui-design/Astrology App.dc.html:
ink ground, cream text, gold hairlines, Cormorant Garamond / Lora,
North-Indian kundli plate with D1/D9/D10 tabs, dasha ledger, gocara
(transits), yogas and nakshatra table.

Copyright (C) 2026 Kartik Agarwal.

This program is free software: you can redistribute it and/or modify it
under the terms of the GNU Affero General Public License as published by the
Free Software Foundation, either version 3 of the License, or (at your
option) any later version. See LICENSE.

The licence is inherited, not chosen: every position comes from pyswisseph,
which is AGPL-3.0. Section 13 is why the page footer carries a Source link —
a network user must be offered the Corresponding Source, and a public
repository only does that if the running app points at it.
"""
from __future__ import annotations

import json
import os
import secrets
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from flask import Flask, jsonify, render_template, request

from dashas import nakshatra_of, nakshatra_table, vimshottari
from ask import ChartContext, ask_all
from pancanga import pancanga_for
from gunamilan import fraction, guna_milan
from reading import read_day
from doshas import (WEATHER_FRAMING, combinations, doshas_all,
                    transit_weather)
from lessons import CONTEXT_LESSONS, LESSONS
from engine import SIGNS, PLANETS, BirthData, compute_chart
from explain import DASHA_THEME, explain_dashboard, explain_yoga, ordinal
from rulelib import HOUSE_MATTERS
import schools
from transits import (
    DRISHTI_OFFSETS,
    aspected_signs,
    next_sign_ingress,
    transit_contacts,
    transit_snapshot,
    upcoming_ingresses,
)
import arudhas
import avasthas
import karakas
import vimsopaka
from vargas import dasamsa, navamsa
import vargas
import agent
import chartfacts
import today
import voice
import yogaread
import ashtakavarga as av_mod
from yogas import (combust, detect_all, dignity, dignity_at,
                   dignity_grade, natural_nature, sign_lord)

app = Flask(__name__)
app.template_filter("ordinal")(ordinal)  # '3' → '3rd', app-wide
app.template_filter("fraction")(fraction)  # 28.5 → '28½'


@app.context_processor
def _plate_geometry():
    """The plate tables, available to every template render.

    Injected rather than duplicated in the template so the browser's
    highlight layer and the server's placement layer cannot disagree.
    """
    # The plate's type sizes travel with it. They were duplicated as
    # literals in the template, so raising MINI_SIZE here changed what
    # `plate_layout` reserved room for and not one pixel of what was drawn —
    # the glyphs stayed at 26 units and stayed under the legibility floor.
    return {"house_poly": HOUSE_POLY, "house_center": HOUSE_CENTER,
            "DEG_SIZE": DEG_SIZE, "DEG_LEADING": DEG_LEADING,
            "COMPACT_SIZE": COMPACT_SIZE, "COMPACT_LEADING": COMPACT_LEADING,
            "MINI_SIZE": MINI_SIZE, "MINI_LEADING": MINI_LEADING}


@app.route("/favicon.ico")
@app.route("/apple-touch-icon.png")
@app.route("/apple-touch-icon-precomposed.png")
def favicon():
    return app.send_static_file("favicon.svg"), 200, {
        "Content-Type": "image/svg+xml"}


@dataclass(frozen=True)
class Profile:
    """One person's saved details. v1 renders a single profile per request;
    the shape is ready for multiple stored profiles later (no accounts)."""

    name: str  # optional — empty string means anonymous
    birth: BirthData
    partner_name: str = ""
    partner_birth: BirthData | None = None


# --- offline city lookup (bundled dataset, no network at runtime) ------------

def _fold(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore") \
        .decode().lower()


_CITIES: list[tuple[str, list]] | None = None


def _cities() -> list[tuple[str, list]]:
    global _CITIES
    if _CITIES is None:
        rows = json.loads(
            (Path(__file__).parent / "data" / "cities.json")
            .read_text(encoding="utf-8"))
        # rows arrive population-sorted; pre-fold names for matching
        _CITIES = [(_fold(r[0]), r) for r in rows]
    return _CITIES


@app.route("/api/cities")
def cities_api():
    q = _fold(request.args.get("q", "").strip())
    if len(q) < 3:
        return jsonify(results=[])
    results = []
    for folded, (name, region, country, lat, lon, tz, _pop) in _cities():
        if folded.startswith(q) or f" {q}" in folded:
            label = ", ".join(x for x in (name, region, country) if x)
            results.append({"label": label, "lat": lat, "lon": lon,
                            "tz": tz})
            if len(results) == 8:
                break
    return jsonify(results=results)


# --- input parsing -------------------------------------------------------------

_TIME_RE = re.compile(
    r"^\s*(\d{1,2})[:.](\d{2})\s*(am|pm|a\.m\.|p\.m\.)?\s*$", re.IGNORECASE)
# Separator-free: '1312' or '812'. Not a fallback — the primary mobile path.
# The field is masked text with inputmode="numeric", so the keypad offers no
# colon key; the mask types the colon, and digits alone must also parse here
# in case the script has not run.
_TIME_BARE_RE = re.compile(r"^\s*(\d{1,2})(\d{2})\s*(am|pm)?\s*$",
                           re.IGNORECASE)


def parse_time(text: str) -> tuple[int, int]:
    """Accept 24-hour ('14:20'), 12-hour ('2:20 PM') and bare ('1420')."""
    m = _TIME_RE.match(text or "") or _TIME_BARE_RE.match(text or "")
    if not m:
        raise ValueError(
            "Time must look like 14:20 (24-hour) or 2:20 PM (12-hour).")
    hour, minute = int(m.group(1)), int(m.group(2))
    meridiem = (m.group(3) or "").lower().replace(".", "")
    if minute > 59:
        raise ValueError("Minutes run 00–59.")
    if meridiem:
        if not 1 <= hour <= 12:
            raise ValueError("With AM/PM the hour runs 1–12.")
        hour = hour % 12 + (12 if meridiem == "pm" else 0)
    elif hour > 23:
        raise ValueError("In 24-hour time the hour runs 0–23.")
    return hour, minute

_COORD_RE = re.compile(
    r"^\s*([+\-−–]?)\s*(\d{1,3}(?:[.,]\d+)?)\s*°?\s*"
    r"([NSEWnsew])?\s*$")
_NEGATIVE_HEMISPHERES = {"s", "w"}


def parse_coord(text: str, axis: str) -> float:
    """Decimal degrees from the several shapes people actually type.

    Signed ('-33.87'), hemisphere-suffixed ('33.87 S', '33.87°S') and
    comma-decimal ('33,87') all parse. The hemisphere form matters on
    mobile: a numeric keypad may offer no minus key at all, which would
    otherwise make the entire southern and western hemispheres unreachable
    through the manual-coordinate fallback.
    """
    limit = 90 if axis == "latitude" else 180
    m = _COORD_RE.match(text or "")
    if not m:
        raise ValueError(
            f"{axis.capitalize()} must be decimal degrees — e.g. "
            f"{'-33.87 or 33.87 S' if axis == 'latitude' else '-70.67 or 70.67 W'}.")
    sign, number, hemisphere = m.group(1), m.group(2), (m.group(3) or "").lower()
    if hemisphere and hemisphere not in (
            "ns" if axis == "latitude" else "ew"):
        raise ValueError(
            f"{axis.capitalize()} takes "
            f"{'N or S' if axis == 'latitude' else 'E or W'}, not "
            f"{hemisphere.upper()}.")
    if sign and hemisphere:
        raise ValueError(
            f"Give {axis} a sign or a hemisphere letter, not both.")
    value = float(number.replace(",", "."))
    if sign in ("-", "−", "–") or hemisphere in _NEGATIVE_HEMISPHERES:
        value = -value
    if not -limit <= value <= limit:
        raise ValueError(f"{axis.capitalize()} runs −{limit} to {limit}.")
    return value


# --- SCREEN 3: the divisional charts, and the ones not built yet ------------
# Every varga this app can cast, plus the slots it cannot. A gallery that
# quietly omitted D2 and D7 would imply the list is complete; saying "in
# preparation" is the same honesty the disabled Upapada option gets.
# SCREEN 3 — the divisional charts, in the order a reader meets them.
#
# The NAME and the ORDER live here; what each division is read for lives in
# `vargas.READ_FOR`, and whether it can be cast at all lives in
# `vargas.SUPPORTED`. Three files could disagree about the D7; only one of
# them is allowed to have an opinion about any given thing.
VARGA_SLOTS = (
    ("d1", "D1", "Rāśi"),
    ("d2", "D2", "Horā"),
    ("d3", "D3", "Drekkāṇa"),
    ("d4", "D4", "Chaturthāṃśa"),
    ("d7", "D7", "Saptāṃśa"),
    ("d9", "D9", "Navāṃśa"),
    ("d10", "D10", "Daśāṃśa"),
    ("d12", "D12", "Dvādaśāṃśa"),
    ("d16", "D16", "Ṣoḍaśāṃśa"),
    ("d20", "D20", "Viṃśāṃśa"),
    ("d24", "D24", "Chaturviṃśāṃśa"),
    ("d27", "D27", "Bhāṃśa"),
    ("d30", "D30", "Triṃśāṃśa"),
    ("d40", "D40", "Khavedāṃśa"),
    ("d45", "D45", "Akṣavedāṃśa"),
    ("d60", "D60", "Ṣaṣṭyāṃśa"),
)

#: The one-line summary a gallery card carries. The birth chart is not a
#: division and has no entry in `vargas.READ_FOR`, so it gets its own.
D1_SUMMARY = "The birth chart itself — every other chart is read against this one."


def varga_summary(code: str) -> str:
    if code == "D1":
        return D1_SUMMARY
    read_for = vargas.READ_FOR[code].strip()
    return read_for[:1].upper() + read_for[1:] + "."


def _and_list(names: list[str]) -> str:
    """'Venus', 'Venus and Saturn', 'Venus, Saturn and Mars'."""
    if len(names) == 1:
        return names[0]
    return ", ".join(names[:-1]) + " and " + names[-1]


#: The division's number in plain words, for a sentence a reader can say
#: out loud. "Rises in the D16" is a code; "rises in the sixteenth division"
#: is English.
# One word per division, because "the D24 divides each sign into 24" reads
# like a spec and "the twenty-fourth division" reads like a sentence. A
# missing entry used to be a KeyError that took the whole dashboard down
# with a 400 — `plate_reading` now falls back rather than raising, and
# `TestYourChartsScreen` asserts every computed division has a word.
_ORDINAL_WORD = {2: "second", 3: "third", 4: "fourth", 7: "seventh",
                 9: "ninth", 10: "tenth", 12: "twelfth", 16: "sixteenth",
                 20: "twentieth", 24: "twenty-fourth", 27: "twenty-seventh",
                 30: "thirtieth", 40: "fortieth", 45: "forty-fifth",
                 60: "sixtieth"}


def plate_reading(key: str, chart) -> str:
    """One line of reading for a plate, composed from that plate alone.

    A gallery of charts with no reading is a filing cabinet. Each of these
    says the one thing the division is FOR, out of this chart's own
    placements. Plain register, no house numbers, no Sanskrit: the technical
    reading of every placement is two taps away in Explore.

    GENERIC over `vargas.SUPPORTED` since the seven new divisions landed.
    It used to have a branch per division and an `else` that fell through to
    the D10's sentence — so the D3, the D7, the D12, the D16, the D30 and
    the D60 all told the reader about the tenth division.
    """
    def matters(house: int) -> str:
        return HOUSE_MATTERS[house].split(",")[0].strip()

    def plain(name: str) -> str:
        return voice.plain(name)

    if key == "d1":
        lord = sign_lord(chart.lagna.sign_index)
        return (f"{chart.lagna.sign} rises, so {plain(lord)} rules this "
                f"chart — and it stands in {matters(chart.planets[lord].house)}.")

    code = key.upper()
    vc = vargas.varga_chart(chart, code)
    lord = sign_lord(vc.lagna_sign_index)
    parts = vargas.DIVISIONS[code]
    which = _ORDINAL_WORD.get(parts, f"{parts}-part")

    if code == "D9":
        # The ninth has its own question — which grahas keep the sign they
        # were born in — and it is the sharpest thing this division says.
        kept = [p for p in PLANETS if vc.planets[p].vargottama]
        head = (f"{vc.lagna_sign} rises in the {which} division, so "
                f"{plain(lord)} carries the inner chart")
        rest = [plain(p) for p in kept if p != lord]
        if lord in kept:
            tail = "and it keeps the sign it was born in"
            if rest:
                tail += (f", as {'does' if len(rest) == 1 else 'do'} "
                         f"{_and_list(rest)}")
            return f"{head} — {tail}."
        if rest:
            return (f"{head} — and {_and_list(rest)} "
                    f"{'keeps' if len(rest) == 1 else 'keep'} the sign "
                    f"{'it was' if len(rest) == 1 else 'they were'} born in.")
        return f"{head} — and no planet keeps the sign it was born in."

    head = (f"{vc.lagna_sign} rises in the {which} division, so "
            f"{plain(lord)} carries {vargas.READ_FOR[code]}")
    # Which grahas are strong HERE — computable per division now that a
    # divisional position carries a degree.
    strong = [plain(p) for p in PLANETS
              if dignity_at(p, vc.planets[p].sign_index,
                            vc.planets[p].degree_in_sign)
              in ("exalted", "moolatrikona", "own sign")]
    if strong:
        return (f"{head} — and {_and_list(strong)} "
                f"{'is' if len(strong) == 1 else 'are'} at "
                f"{'its' if len(strong) == 1 else 'their'} strongest here.")
    weak = [plain(p) for p in PLANETS
            if dignity_at(p, vc.planets[p].sign_index,
                          vc.planets[p].degree_in_sign) == "debilitated"]
    if weak:
        return (f"{head} — and {_and_list(weak)} "
                f"{'is' if len(weak) == 1 else 'are'} at "
                f"{'its' if len(weak) == 1 else 'their'} weakest here.")
    return f"{head} — and no graha is dignified either way here."


# SCREEN 3 — the divisional charts, in the order a reader meets them.
#
# The NAME and the ORDER live here; what each division is read for lives in
# `vargas.READ_FOR`, and whether it can be cast at all lives in
# `vargas.SUPPORTED`. Three files could disagree about the D7; only one of
# them is allowed to have an opinion about any given thing.
VARGA_SLOTS = (
    ("d1", "D1", "Rāśi"),
    ("d2", "D2", "Horā"),
    ("d3", "D3", "Drekkāṇa"),
    ("d4", "D4", "Chaturthāṃśa"),
    ("d7", "D7", "Saptāṃśa"),
    ("d9", "D9", "Navāṃśa"),
    ("d10", "D10", "Daśāṃśa"),
    ("d12", "D12", "Dvādaśāṃśa"),
    ("d16", "D16", "Ṣoḍaśāṃśa"),
    ("d20", "D20", "Viṃśāṃśa"),
    ("d24", "D24", "Chaturviṃśāṃśa"),
    ("d27", "D27", "Bhāṃśa"),
    ("d30", "D30", "Triṃśāṃśa"),
    ("d40", "D40", "Khavedāṃśa"),
    ("d45", "D45", "Akṣavedāṃśa"),
    ("d60", "D60", "Ṣaṣṭyāṃśa"),
)

#: The one-line summary a gallery card carries. The birth chart is not a
#: division and has no entry in `vargas.READ_FOR`, so it gets its own.
D1_SUMMARY = "The birth chart itself — every other chart is read against this one."


def varga_summary(code: str) -> str:
    if code == "D1":
        return D1_SUMMARY
    read_for = vargas.READ_FOR[code].strip()
    return read_for[:1].upper() + read_for[1:] + "."


def _and_list(names: list[str]) -> str:
    """'Venus', 'Venus and Saturn', 'Venus, Saturn and Mars'."""
    if len(names) == 1:
        return names[0]
    return ", ".join(names[:-1]) + " and " + names[-1]


def varga_gallery(chart) -> list[dict]:
    """The gallery index — every division, cast where this build can cast it.

    Generic over `vargas.SUPPORTED`: a new division needs no change here.
    """
    marks = planet_marks(chart)
    out = []
    for key, code, name in VARGA_SLOTS:
        live = code == "D1" or vargas.is_supported(code)
        row = {"key": key, "code": code, "name": name,
               "summary": varga_summary(code), "live": live,
               # Where the tradition splits, said on the plate rather than
               # assumed away. None for the divisions that do not split.
               "school": vargas.SCHOOL_NOTE.get(code),
               "school_rule": vargas.SCHOOL_RULE.get(code)}
        if live:
            if code == "D1":
                sign_index = chart.lagna.sign_index
                houses = {p: chart.planets[p].house for p in PLANETS}
                degrees = {p: (chart.planets[p].degree_in_sign,
                               chart.planets[p].retrograde) for p in PLANETS}
                lagna_degree = chart.lagna.degree_in_sign
            else:
                vc = vargas.varga_chart(chart, code)
                sign_index = vc.lagna_sign_index
                houses = {p: vc.planets[p].house for p in PLANETS}
                # A divisional chart HAS degrees now. Retrograde is a
                # property of the real body's motion and does not divide, so
                # it is carried through from the birth chart unchanged.
                degrees = {p: (vc.planets[p].degree_in_sign,
                               chart.planets[p].retrograde) for p in PLANETS}
                lagna_degree = vc.lagna_degree_in_sign
            row["houses"] = kundli_houses(sign_index, houses, degrees=degrees,
                                          lagna_degree=lagna_degree,
                                          marks=marks)
            row["lagna"] = SIGNS[sign_index]
            row["reading"] = plate_reading(key, chart)
        out.append(row)
    return out


def ashtakavarga_view(chart) -> dict:
    """The Aṣṭakavarga fold: the answer, then the grid.

    Rotated to HOUSES here and once only. The module works per sign, which
    is how the tables are defined and how the oracle exports them; every
    number a reader sees is per house, which is the only frame in which
    "your 10th" means anything. Doing the rotation in one named place is
    what stops a table being rotated twice.
    """
    av = av_mod.ashtakavarga(chart)
    by_house = av.sav_by_house
    strongest = av_mod.strongest(av)
    thinnest = av_mod.thinnest(av)
    rows = []
    for h in range(1, 13):
        score = by_house[h]
        rows.append({
            "house": h,
            "sign": av.sign_of_house(h),
            "sav": score,
            "band": ("strong" if score >= av_mod.STRONG_FLOOR
                     else "thin" if score <= av_mod.THIN_CEILING
                     else "middling"),
            "matters": HOUSE_MATTERS[h].split(",")[0].strip(),
            "bav": {p: av.by_house(av.bav_by_sign[p])[h]
                    for p in av_mod.BODIES},
        })
    return {
        "verdict": av_mod.verdict(av),
        "rows": rows,
        "bodies": av_mod.BODIES,
        "totals": {p: sum(av.bav_by_sign[p]) for p in av_mod.BODIES},
        "sav_total": av.sav_total,
        "lagna_total": sum(av.lagna_bav_by_sign),
        "note": av_mod.REDUCTIONS_NOTE,
        "strongest": strongest,
        "thinnest": thinnest,
        # The number for each house, keyed by house, for the D1 plate.
        "by_house": by_house,
    }


def transit_ticks(chart, when) -> list[dict]:
    """Today's transiting grahas, marked on the outer edge of the plate.

    A tick per occupied house, carrying the abbreviations of whatever stands
    there — the plate is a square of fixed houses, so "outer edge" means the
    outward-facing corner of that house's cell.
    """
    snapshot = transit_snapshot(chart, when)
    by_house: dict[int, list[str]] = {}
    for name in PLANETS:
        # `natal_house`, not `house`: the tick marks where a transit stands
        # relative to THIS chart's lagna, which is the only frame in which
        # "your 8th" means anything.
        house = snapshot.planets[name].natal_house
        by_house.setdefault(house, []).append(ABBR[name])
    return [{"house": h, "label": " ".join(marks),
             "x": TICK_POS[h][0], "y": TICK_POS[h][1]}
            for h, marks in sorted(by_house.items())]


def _and_words(items) -> str:
    items = list(items)
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + " and " + items[-1]


def _owned(planet: str, names) -> str:
    """'your Moon, Sun and Venus' — one 'your' for the list, the reader's
    rising degree after it, and the transit's own natal place last, since
    'its gaze falls on its own natal place, your Sun…' reads the return
    before the contact and the contact is the news."""
    grahas = [n for n in names if n not in (planet, "Lagna")]
    parts = []
    if grahas:
        parts.append("your " + _and_words(
            voice.plain(n).removeprefix("the ") for n in grahas))
    if "Lagna" in names:
        parts.append(voice.yours("Lagna"))
    if planet in names:
        parts.append("its own natal place")
    if len(parts) > 1 and " and " in parts[0]:
        # "your Sun, Mercury and Venus, and its own natal place" — the
        # comma keeps the second "and" from running into the list's own.
        return ", ".join(parts[:-1]) + ", and " + parts[-1]
    return _and_words(parts)


def _house_words(house: int) -> str:
    """What a house is for, in rule.house.<h>'s own first clause — the same
    words the Today entries use, never a number."""
    return HOUSE_MATTERS[house].split(",")[0].strip()


SLOW_MOVERS = ("Saturn", "Jupiter", "Rahu", "Ketu")


def _title(planet: str) -> str:
    """'The north node', 'Saturn' — a row's title is top-layer text and
    says the plain name, as the Today entries above it do."""
    name = voice.plain(planet)
    return name[:1].upper() + name[1:]


def _daylabel(iso: str | None) -> str:
    """'03 Jun 27' from an ISO date; the column is 74px wide."""
    if not iso:
        return "—"
    return datetime.fromisoformat(iso).strftime("%d %b %y")


def _natal_longitude(chart, point: str) -> float:
    return (chart.lagna.longitude if point == "Lagna"
            else chart.planets[point].longitude)


def transits_panel(chart, when, facts) -> dict:
    """SCREEN 1 — the glance's Transits pane: NOW and UPCOMING.

    The pane used to print four of the lifeline's ingress markers with a
    house number under each — "Saturn → Aries · your 9th house". That is a
    label, not an effect: the 9th is the 9th for everyone with this lagna,
    the number is banned on the top layer, and the pane said nothing about
    today's sky at all. Re-pinned 2026-09-14 from a review of the live site.

    EVERY NOUN ON A ROW IS COPIED FROM A LEDGER FACT, so a gate can rebuild
    the row from the ledger and compare word for word:

      NOW       transit.<p>           the sign it is in, the natal house, and
                                      the contact facts that govern it
                transit.<p>.aspects   the natal houses under its drishti, and
                                      when it leaves the sign
                contact.<t>-<n>       the natal point it is sitting on
                house.<h>             the natal points its gaze falls on
      UPCOMING  transit.<p>.aspects   when it leaves — which is when it enters
                                      the next sign
                house.<h>             what the new sign is in this chart, the
                                      points it lands on, and the points under
                                      its gaze from there

    The house is named by what it holds (HOUSE_MATTERS, rule.house.<h>).
    "Sitting on" is a conjunction within orb; "its gaze falls on" is
    drishti — the classical word is sight, and it is the plain one. No
    sentence here interprets: it says what is touching what, and until when.

    NOW is the four slow movers, always, plus any fast mover standing on a
    natal point today. UPCOMING is each planet's next sign change — the slow
    movers whenever it falls, the fast ones only inside today.HORIZON_DAYS,
    the same window the Today entries call news. The Moon is left out for
    the reason today.py gives: it changes sign every two and a half days.
    """
    now_rows = []
    order = list(SLOW_MOVERS) + [p for p in PLANETS if p not in SLOW_MOVERS]
    for p in order:
        t = facts[f"transit.{p.lower()}"].value
        a = facts[f"transit.{p.lower()}.aspects"].value
        if not (t["slow_mover"] or t["governing_contacts"]):
            continue
        sits = [facts[c].value["point"] for c in t["governing_contacts"]]
        gaze_houses = [h for h in a["aspects"]
                       if facts[f"house.{h}"].value["occupants"]]
        gaze = [n for h in gaze_houses
                for n in facts[f"house.{h}"].value["occupants"]]
        house_words = _house_words(t["natal_house"])
        effect = f"Works the part of your chart that holds {house_words}"
        if sits:
            effect += f", sitting on {_owned(p, sits)}"
        if gaze:
            effect += f"; its gaze falls on {_owned(p, gaze)}"
        effect += "."
        # UNTIL WHEN. A slow mover's row is about its passage through the
        # sign, so the sign exit is its end. A fast mover is here only
        # because it is standing on a natal point, and that contact ends
        # days before the sign does — so its end is the contact's end,
        # found the way the Today entries find it.
        if t["slow_mover"]:
            until = a["until_iso"]
        else:
            leaves = [today.contact_window(
                          p, _natal_longitude(chart, facts[c].value["point"]),
                          when)[1]
                      for c in t["governing_contacts"]]
            leaves = [x for x in leaves if x is not None]
            until = (max(leaves).date().isoformat() if leaves
                     else a["until_iso"])
        now_rows.append({
            "planet": p, "title": _title(p) + f" in {t['sign']}",
            "sign": t["sign"], "retro": t["retrograde"],
            "until": until,
            "until_label": _daylabel(until),
            "natal_house": t["natal_house"],
            "house_words": house_words, "sits_on": sits, "gaze": gaze,
            "effect": effect,
            "ids": ([f"transit.{p.lower()}", f"transit.{p.lower()}.aspects"]
                    + list(t["governing_contacts"])
                    + [f"house.{h}" for h in gaze_houses]),
        })

    upcoming = []
    horizon = when + timedelta(days=today.HORIZON_DAYS)
    for p in PLANETS:
        if p == "Moon":
            continue
        slow = p in SLOW_MOVERS
        ing = next_sign_ingress(
            p, when, max_days=4000 if slow else today.HORIZON_DAYS + 1)
        if ing is None or (not slow and ing.when > horizon):
            continue
        house = (ing.to_sign_index - chart.lagna.sign_index) % 12 + 1
        gaze_houses = [
            h for h in sorted((s - chart.lagna.sign_index) % 12 + 1
                              for s in aspected_signs(p, ing.to_sign_index))
            if facts[f"house.{h}"].value["occupants"]]
        lands = facts[f"house.{house}"].value["occupants"]
        gaze = [n for h in gaze_houses
                for n in facts[f"house.{h}"].value["occupants"]]
        house_words = _house_words(house)
        effect = f"Moves into the part of your chart that holds {house_words}"
        if lands:
            effect += f", landing on {_owned(p, lands)}"
        if gaze:
            effect += f"; its gaze will fall on {_owned(p, gaze)}"
        effect += "."
        upcoming.append({
            "planet": p, "title": _title(p) + f" → {ing.to_sign}",
            "to_sign": ing.to_sign, "when": ing.when,
            "daylabel": _daylabel(ing.when.date().isoformat()),
            "natal_house": house, "house_words": house_words,
            "lands_on": lands, "gaze": gaze, "effect": effect,
            "ids": ([f"transit.{p.lower()}.aspects", f"house.{house}"]
                    + [f"house.{h}" for h in gaze_houses if h != house]),
        })
    upcoming.sort(key=lambda r: r["when"])
    return {"now": now_rows, "upcoming": upcoming}


# Where a tick sits for each house: in the margin OUTSIDE the 0..300 frame,
# which is why the D1 plate's viewBox is widened to -30..330. Inside the
# frame they collided with the plate's own sign numerals at every width —
# the overlap gate caught it immediately.
TICK_POS = {
    1: (150, -12), 2: (60, -12), 3: (-14, 60), 4: (-14, 150), 5: (-14, 240),
    6: (60, 320), 7: (150, 320), 8: (240, 320), 9: (320, 240), 10: (320, 150),
    11: (320, 60), 12: (240, -12),
}

ABBR = {
    "Sun": "Su", "Moon": "Mo", "Mars": "Ma", "Mercury": "Me",
    "Jupiter": "Ju", "Venus": "Ve", "Saturn": "Sa", "Rahu": "Ra", "Ketu": "Ke",
}

# The astronomical glyphs, which are what a printed plate actually carries.
# They travel WITH the two-letter abbreviations rather than replacing them:
# the glyph is recognisable at a glance and at small sizes, the letters are
# unambiguous, and the legend under every plate teaches both. ☊/☋ are the
# ascending and descending nodes — Rāhu and Ketu.
GLYPH = {
    "Sun": "☉", "Moon": "☽", "Mars": "♂", "Mercury": "☿",
    "Jupiter": "♃", "Venus": "♀", "Saturn": "♄", "Rahu": "☊", "Ketu": "☋",
}

# --- North-Indian plate geometry — ONE source of truth ------------------------
#
# STYLE: North Indian. Houses are FIXED cells; the SIGNS rotate with the
# lagna, which is why each cell carries a sign number rather than a house
# number. House 1 is the top-centre diamond and the count runs anticlockwise.
#
# This table is the single authority. The Python placement layer indexes it
# directly, and the browser's aspect/highlight layer receives THIS dict via
# the template — previously each had its own copy, which is exactly the kind
# of duplication that lets two layers drift apart silently.
HOUSE_POLY = {
    1:  [(150, 3), (223.5, 76.5), (150, 150), (76.5, 76.5)],
    2:  [(3, 3), (150, 3), (76.5, 76.5)],
    3:  [(3, 3), (76.5, 76.5), (3, 150)],
    4:  [(3, 150), (76.5, 76.5), (150, 150), (76.5, 223.5)],
    5:  [(3, 150), (3, 297), (76.5, 223.5)],
    6:  [(3, 297), (150, 297), (76.5, 223.5)],
    7:  [(150, 297), (76.5, 223.5), (150, 150), (223.5, 223.5)],
    8:  [(150, 297), (297, 297), (223.5, 223.5)],
    9:  [(297, 297), (297, 150), (223.5, 223.5)],
    10: [(297, 150), (223.5, 223.5), (150, 150), (223.5, 76.5)],
    11: [(297, 150), (297, 3), (223.5, 76.5)],
    12: [(297, 3), (150, 3), (223.5, 76.5)],
}
HOUSE_CENTER = {
    1: (150, 77), 2: (76, 28), 3: (28, 76), 4: (76, 150), 5: (28, 223),
    6: (76, 272), 7: (150, 223), 8: (223, 272), 9: (272, 223), 10: (223, 150),
    11: (272, 76), 12: (223, 28),
}
# Sign numbers hug the OUTER border of their cell; the graha labels take the
# cell body. In the eight triangles both were competing for the same space,
# and a sign number sitting under a degree stack is unreadable — the number
# is one or two characters and moves easily, a three-line stack does not.
NUMBER_POS = {
    1: (150, 70), 2: (76, 15), 3: (20, 42), 4: (75, 146),
    5: (20, 264), 6: (76, 291), 7: (150, 222), 8: (224, 291),
    9: (280, 264), 10: (225, 146), 11: (280, 42), 12: (224, 15),
}
PLANET_POS = {
    1: (150, 92), 2: (75, 40), 3: (28, 92), 4: (90, 164),
    5: (28, 240), 6: (75, 254), 7: (150, 240), 8: (225, 254),
    9: (272, 240), 10: (210, 164), 11: (272, 92), 12: (225, 40),
}
# Anchors for the wider degree labels.
#
# These were once PLANET_POS with x clamped to [62, 238] to keep long text
# inside the plate border. That clamp moved houses 3, 5, 9 and 11 — the four
# narrow triangles — ACROSS a cell boundary: house 9's label landed at x=238
# while its own cell begins at x=240 on that row, so a 9th-house graha was
# drawn in the 8th-house cell. The text said 9th and the plate said 8th.
#
# A label must never leave its own cell; slight crowding is a cosmetic
# problem, a label in the wrong house is a wrong chart. These anchors sit
# inside their own polygons, verified by test_degree_anchors_stay_in_cell.
# Each anchor sits near its own cell's CENTROID, not pulled toward the plate
# centre. Anchors nudged toward the middle converge at the vertices the cells
# share, so two houses' stacks visually run together — which is how a 9th-house
# graha can *read* as 8th even when it is drawn in the right cell.
DEG_POS = {
    1: (150, 92),  2: (76, 38),  3: (34, 92),  4: (90, 164),
    5: (34, 220),  6: (76, 264), 7: (150, 240), 8: (223, 264),
    9: (262, 223), 10: (210, 164), 11: (266, 88), 12: (223, 38),
}


def cell_span(house: int, y: float) -> tuple[float, float] | None:
    """How wide a house cell is at a given height, in plate user units.

    The four narrow triangles taper: house 3 is 73 units across at its
    widest and 20 at y=130. A degree label is set at a fixed size and does
    not taper, so whether it fits is a question about THIS number, and it
    is the question `kundli_houses` has to answer before it decides to draw
    degrees in a cell at all.
    """
    poly = HOUSE_POLY[house]
    xs, n = [], len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if (y1 > y) != (y2 > y):
            xs.append((x2 - x1) * (y - y1) / (y2 - y1) + x1)
    return (min(xs), max(xs)) if len(xs) >= 2 else None


# Advance widths in ems, MEASURED in the browser at the size the plate uses
# rather than guessed: an estimate that ran 20% generous dropped cells to
# compact marks that had room, and one that ran short would draw a label
# across a house boundary, which is a wrong chart. Digits are tabular here,
# so their advance is a constant.
#
#   ☽ ♄ ♂ ♃ ☉  12.55 units at size 14 = .897em   (☿ .61, ♀ .73 — narrower)
#   0-9          8.90                  = .636em
#   °            7.00                  = .500em
#   ′            3.38                  = .241em
#   M           12.07                  = .862em  (the widest letter)
#
# "letter" is .78 rather than .70 because of the capital in Mo/Ma/Me: at
# .70 the estimate for "Mo 22°23′" came in 0.25 units UNDER the real box.
#
# Each figure below is rounded UP from the measurement, so the estimate errs
# toward "does not fit". `test_no_label_overflows_its_cell_in_a_browser`
# measures the real boxes and fails if this ever drifts optimistic.
_EM = {"glyph": 0.92, "digit": 0.65, "°": 0.52, "′": 0.26, " ": 0.28,
       "letter": 0.78}


def _label_width(text: str, size: float) -> float:
    total = 0.0
    for ch in text:
        if ch in _EM:
            total += _EM[ch]
        elif ch.isdigit():
            total += _EM["digit"]
        elif ord(ch) > 0x2000:      # an astronomical glyph
            total += _EM["glyph"]
        else:
            total += _EM["letter"]
    return size * total


def _rows_fit(house: int, anchor: tuple[float, float],
              rows: list[str], size: float, leading: float) -> bool:
    """Would these rows, centred on the anchor, all stay inside the cell?"""
    cx, cy = anchor
    top = cy - leading * (len(rows) - 1) / 2
    for i, text in enumerate(rows):
        y = top + leading * i
        half = _label_width(text, size) / 2
        # The baseline row and the row the ascenders reach into.
        for probe in (y, y - size * 0.72):
            span = cell_span(house, probe)
            if span is None or cx - half < span[0] or cx + half > span[1]:
                return False
    return True


def _pack(house: int, anchor: tuple[float, float], items: list[str],
          size: float, leading: float) -> list[list[int]] | None:
    """Distribute `items` over as few rows as fit inside the cell.

    Returns the item indices per row, or None if no arrangement fits. Tried
    from one row upward, distributing as evenly as possible: a cell that can
    take three marks side by side should, and one that cannot should stack
    rather than run through its own diagonal.
    """
    n = len(items)
    for count in range(1, n + 1):
        per = -(-n // count)                    # ceil
        groups = [list(range(i, min(i + per, n)))
                  for i in range(0, n, per)]
        if len(groups) != count:
            continue
        texts = [" ".join(items[i] for i in g) for g in groups]
        if _rows_fit(house, anchor, texts, size, leading):
            return groups
    return None


def _dot_positions(house: int, count: int) -> list[tuple[float, float]]:
    """`count` dots, in a row (or two) at the cell centroid."""
    cx, cy = cell_centroid(house)
    per = min(count, 3)
    rows = -(-count // per)
    out = []
    n = count
    for r in range(rows):
        here = min(per, n)
        n -= here
        y = cy + 14 * (r - (rows - 1) / 2)
        for i in range(here):
            out.append((cx + 13 * (i - (here - 1) / 2), y))
    return out


def cell_centroid(house: int) -> tuple[float, float]:
    poly = HOUSE_POLY[house]
    return (sum(p[0] for p in poly) / len(poly),
            sum(p[1] for p in poly) / len(poly))


def plate_layout(house: int, anchor: tuple[float, float],
                 grahas: list[dict], size: float, leading: float,
                 with_degrees: bool,
                 glyph_only: bool = False) -> dict | None:
    """How this cell's marks are actually laid out — or None if they cannot
    be.

    THE PLATE'S ONE CORRECTNESS PROPERTY is that a mark never leaves the
    cell it belongs to; a label drawn across a diagonal says the graha is in
    a house it is not in. The anchor tables guarantee where a stack is HUNG.
    They cannot see how WIDE it is, and width is what actually left the
    cell: three marks side by side in house 9 measured 104 units in a cell
    73 across.

    So the arrangement is decided here, geometrically, and the template only
    draws what it is handed. Richest form first — glyph, letters and degree
    — falling back a step at a time rather than all the way to nothing:

        ☉Su 29°09′   glyph, abbreviation, degree
        Su 29°09′    the glyph is the widest character; drop it first
        ☉Su          the degree needs the most room; drop it next
        Su           letters alone always fit
    """
    if glyph_only:
        # A thumbnail: one glyph per graha and nothing else. Letters at that
        # scale measured under four rendered pixels.
        groups = _pack(house, anchor, [g["glyph"] for g in grahas],
                       size, leading)
        if groups is None:
            groups = _pack(house, cell_centroid(house),
                           [g["glyph"] for g in grahas], size, leading)
            anchor = cell_centroid(house)
        if groups is None:
            return None
        return {"form": "glyph-only", "glyph": True, "degrees": False,
                "at": anchor, "rows": groups}

    forms = []
    if with_degrees:
        forms.append(("glyph-deg", [g["glyph"] + g["abbr"]
                                    + (" " + g["deg"] if g["deg"] else "")
                                    for g in grahas], True, True))
        forms.append(("deg", [g["abbr"] + (" " + g["deg"] if g["deg"] else "")
                              for g in grahas], False, True))
    forms.append(("glyph", [g["glyph"] + g["abbr"] for g in grahas],
                  True, False))
    forms.append(("plain", [g["abbr"] for g in grahas], False, False))
    # RICHNESS OUTRANKS POSITION. The form loop is outside the anchor loop
    # on purpose: dropping a graha's degree is a real loss of information,
    # while moving its label 18 units down inside its own cell costs
    # nothing. With the loops the other way round the table anchor's poorer
    # form won, and four of six occupied houses lost their degrees to a
    # nudge that would have fitted them.
    #
    # The anchors are tuned for one or two marks; a triangle simply has more
    # room lower down, and moving the whole block there keeps it inside the
    # cell, which is the only property that matters.
    for name, items, glyph, deg in forms:
        for point in (anchor, cell_centroid(house)):
            # A degree stack is one graha to a row by definition; the
            # compact marks may share a row.
            if deg:
                if _rows_fit(house, point, items, size, leading):
                    return {"form": name, "glyph": glyph, "degrees": True,
                            "at": point,
                            "rows": [[i] for i in range(len(grahas))]}
                continue
            groups = _pack(house, point, items, size, leading)
            if groups is not None:
                return {"form": name, "glyph": glyph, "degrees": False,
                        "at": point, "rows": groups}
    return None


def house_at(x: float, y: float) -> int | None:
    """Which house cell a point falls in. Shared by the tests and by any
    caller that needs to reason about the plate geometrically."""
    for house, poly in HOUSE_POLY.items():
        inside, n = False, len(poly)
        for i in range(n):
            x1, y1 = poly[i]
            x2, y2 = poly[(i + 1) % n]
            if (y1 > y) != (y2 > y):
                cross = (x2 - x1) * (y - y1) / (y2 - y1) + x1
                if x < cross:
                    inside = not inside
        if inside:
            return house
    return None


def _deg_min(degree_in_sign: float) -> str:
    """15.56° → '15°33′' (minutes truncated, matching printed almanacs)."""
    d = int(degree_in_sign)
    return f"{d}°{int((degree_in_sign - d) * 60):02d}′"


def kundli_houses(lagna_sign_index: int, house_of: dict[str, int],
                  degrees: dict[str, tuple[float, bool]] | None = None,
                  lagna_degree: float | None = None,
                  marks: dict[str, dict] | None = None,
                  sav: dict[int, int] | None = None) -> list[dict]:
    """Per-house render data for the North-Indian SVG plate.

    `degrees` maps planet -> (degree_in_sign, retrograde) and yields the
    detail labels ('Ju 15°33′', 'Sa 9°29′ R'). Divisional charts pass None —
    varga positions are sign-level, so degree labels apply to D1 only.

    `marks` maps planet -> {'nature', 'combust'} from `planet_marks()`. It is
    what lets a plate be READ rather than merely plotted: a graha carries its
    glyph, its two-letter abbreviation, whether it is retrograde and whether
    it is burnt, and it is set in the ink weight of its own nature. Passing
    None gives the plain marks, which is what an unread thumbnail wants.
    """
    labels: dict[int, list[str]] = {h: [] for h in range(1, 13)}
    detail: dict[int, list[str]] = {h: [] for h in range(1, 13)}
    grahas: dict[int, list[dict]] = {h: [] for h in range(1, 13)}
    labels[1].append("As")
    if lagna_degree is not None:
        detail[1].append(f"As {_deg_min(lagna_degree)}")
    # THE LAGNA LEADS ITS OWN HOUSE. It is not a graha, so it carries no
    # glyph, no nature and no burnt mark — but it does sit in the same
    # stack, at the head of it, in the accent. Drawn as a separate floating
    # mark it landed on top of house 1's sign numeral at every width.
    grahas[1].append({
        "planet": "Lagna", "abbr": "Asc", "glyph": "",
        "deg": _deg_min(lagna_degree) if lagna_degree is not None else None,
        "retro": False, "combust": False, "nature": "lagna",
        "is_lagna": True,
    })
    for name in PLANETS:
        h = house_of[name]
        labels[h].append(ABBR[name])
        mark = (marks or {}).get(name, {})
        retro = False
        deg = None
        if degrees is not None:
            deg_val, retro = degrees[name]
            deg = _deg_min(deg_val)
            detail[h].append(
                f"{ABBR[name]} {_deg_min(deg_val)}" + (" R" if retro else ""))
        grahas[h].append({
            "planet": name,
            "abbr": ABBR[name],
            "glyph": GLYPH[name],
            "deg": deg,
            # ℞ is the retrograde mark and ⊙ the burnt one; both are printed
            # in the margin of the label rather than mixed into its letters,
            # so a graha reads as one word with a diacritic on it.
            "retro": retro,
            "combust": bool(mark.get("combust")),
            "nature": mark.get("nature", "benefic"),
            "is_lagna": False,
        })

    houses = []
    for h in range(1, 13):
        row = labels[h]
        line1, line2 = row, []
        if len(row) > 3:  # wrap crowded houses onto two lines
            mid = (len(row) + 1) // 2
            line1, line2 = row[:mid], row[mid:]
        houses.append({
            "house": h,
            "sign_num": (lagna_sign_index + h - 1) % 12 + 1,
            "num_pos": NUMBER_POS[h],
            "pl_pos": PLANET_POS[h],
            "deg_pos": DEG_POS[h],
            "line1": "·".join(line1),
            "line2": "·".join(line2),
            "detail_lines": detail[h],
            "grahas": grahas[h],
            # The Sarvāṣṭakavarga total for this house, printed in the
            # cell's outward corner beside the sign numeral — the number is
            # about the HOUSE, so it belongs on the plate rather than only
            # in a table. D1 only: the tables are defined against the birth
            # chart and mean nothing rotated into a division.
            # The Sarvāṣṭakavarga total for this house. It rides WITH the
            # sign numeral, in one text node — "5 · 27" — rather than as a
            # third mark in the cell. Given its own anchor it collided with
            # the numeral and with the graha stack in every crowded cell,
            # and a plate has no room for a third number per house.
            "sav": (sav or {}).get(h),
            # Three stacked degree labels fill a narrow triangle completely.
            # The sign number underneath them is then unreadable, so it is
            # dropped WHILE THE DEGREE LAYER IS ON — the compact view still
            # shows it, and the sign is never lost (it is in the graha
            # table). Better one legible number fewer than two illegible
            # overlapping texts.
            "crowded": len(grahas[h]) >= 3,
        })

    # HOW EACH CELL IS LAID OUT — decided here, where the polygons are,
    # and handed to the template ready to draw. See `plate_layout`.
    for row in houses:
        if not row["grahas"]:
            row["deg_layout"] = row["compact_layout"] = None
            continue
        row["deg_layout"] = plate_layout(
            row["house"], row["deg_pos"], row["grahas"],
            DEG_SIZE, DEG_LEADING, with_degrees=degrees is not None)
        row["compact_layout"] = plate_layout(
            row["house"], row["pl_pos"], row["grahas"],
            COMPACT_SIZE, COMPACT_LEADING, with_degrees=False)
        # The two small plates — the glance mini and the gallery thumbnail
        # — are the same figure at a quarter of the size, so their marks
        # need their own arrangement AND their own type size. 26 user units
        # renders at 13 on the 132px thumbnail and 17 on the 200px mini,
        # both of which clear the floor; the 15-unit compact marks render
        # at 6.6 and 10.
        row["mini_layout"] = plate_layout(
            row["house"], row["pl_pos"], row["grahas"],
            MINI_SIZE, MINI_LEADING, with_degrees=False, glyph_only=True)
        # Which cells must give up their sign numeral: a stack of two or
        # more rows reaches the numeral's corner, and a numeral under a
        # graha mark is unreadable. The sign is never lost — it is in the
        # graha table, and the compact view shows it whenever it fits.
        row["hide_signnum"] = bool(
            (row["deg_layout"] and len(row["deg_layout"]["rows"]) >= 3)
            or (row["compact_layout"]
                and len(row["compact_layout"]["rows"]) >= 2))
        # A cell that cannot take even glyphs at a legible size gets DOTS:
        # one per graha, in the accent, at the cell centroid. House 12 holds
        # four grahas in a triangle 73 units tall whose top edge is the
        # plate border — two rows of 26-unit glyphs do not go in it at any
        # anchor, and shrinking them to fit would put them under the
        # legibility floor, which is the thing being fixed.
        #
        # A dot is not a compromise on truth: it says exactly what a 132px
        # figure can say — this house is occupied, by this many — and the
        # plate it opens says the rest.
        row["mini_dots"] = (
            _dot_positions(row["house"], len(row["grahas"]))
            if row["mini_layout"] is None else [])
    return houses


# The degree layer's type size and leading, in plate user units. Named
# because `degrees_fit` and the template must agree about them exactly — a
# fit computed at one size and drawn at another is worse than no fit test.
DEG_SIZE = 14.0
DEG_LEADING = 10.0
COMPACT_SIZE = 15.0
COMPACT_LEADING = 17.0
# 32 user units. The gallery thumbnail draws its 300-unit viewBox at 140px
# nominal — but the grid squeezes it to about 125 at 390px, a scale of .417,
# so 26 units rendered at 11 effective pixels and 29 at 12.1. 32 clears the
# floor at the squeezed size, which is the size that has to clear it.
MINI_SIZE = 32.0
MINI_LEADING = 34.0


def planet_marks(chart) -> dict[str, dict]:
    """What each graha IS, for the plate: its nature and whether it is burnt.

    Computed once per request and handed to every plate, so the D1, the D9
    and the thumbnails cannot disagree about which grahas are malefic.
    Nature and combustion are properties of the BIRTH chart — a divisional
    chart is sign-level here and has no degrees to burn with.
    """
    return {name: {"nature": natural_nature(chart, name),
                   "combust": combust(chart, name)}
            for name in PLANETS}


def _fmt(dt: datetime) -> str:
    return dt.strftime("%b %Y")


def planet_explorer(chart) -> dict:
    """Per-planet payload for the tap-to-explore chart: drishti targets
    (with the natal planets they strike), nakshatra-lord wiring, dignity."""
    out = {}
    for name in PLANETS:
        pos = chart.planets[name]
        nak = nakshatra_of(pos.longitude)
        aspects = []
        for off in DRISHTI_OFFSETS[name]:
            house = (pos.house - 1 + off - 1) % 12 + 1
            aspects.append({
                "offset": off,
                "house": house,
                "hits": [p for p in PLANETS
                         if chart.planets[p].house == house],
            })
        out[name] = {
            "abbr": ABBR[name],
            "glyph": GLYPH[name],
            "house": pos.house,
            # The chips ARE the plate's name legend, so they carry what the
            # plate marks: the glyph, and the two states a reader has to be
            # able to look up when they meet ℞ or ⊙ on the figure.
            "combust": combust(chart, name),
            "nature": natural_nature(chart, name),
            "label": f"{pos.sign} {pos.dms}",
            "retro": pos.retrograde,
            "dignity": dignity_grade(chart, name) or dignity(chart, name),
            "nakshatra": f"{nak.name} pada {nak.pada}",
            "nak_lord": nak.lord,
            "nak_lord_house": chart.planets[nak.lord].house,
            # Said in the card, in words, since 2026-09-14: the plate used
            # to draw a dashed line from the graha's house to its star-lord's,
            # and a line joining two houses reads as an aspect.
            "nak_lord_house_matters": _house_words(chart.planets[nak.lord].house),
            "aspects": aspects,
        }
    return out


def build_dashboard(profile: Profile) -> dict:
    birth = profile.birth
    chart = compute_chart(birth)
    d9, d10 = navamsa(chart), dasamsa(chart)
    marks = planet_marks(chart)
    timeline = vimshottari(chart)
    now = datetime.now(timezone.utc)
    snapshot = transit_snapshot(chart, now)
    contacts = transit_contacts(chart, snapshot)
    current = timeline.at(now)

    mahadashas = []
    for md in timeline.mahadashas:
        mahadashas.append({
            "lord": md.lord,
            "start": _fmt(max(md.start, timeline.birth)),
            "end": _fmt(md.end),
            "current": bool(current and md is current[0]),
            "balance": md.start < timeline.birth,
        })

    antardashas = []
    if current:
        cur_md, cur_ad = current
        for ad in cur_md.antardashas:
            if ad.end < timeline.birth:
                continue
            antardashas.append({
                "lord": ad.lord,
                "start": _fmt(max(ad.start, timeline.birth)),
                "end": _fmt(ad.end),
                "current": ad is cur_ad,
            })

    planets = []
    for name in PLANETS:
        pos = chart.planets[name]
        nak = nakshatra_table(chart)[name]
        planets.append({
            "name": name, "sign": pos.sign, "dms": pos.dms,
            "house": pos.house, "retro": pos.retrograde,
            "nakshatra": nak.name, "pada": nak.pada, "lord": nak.lord,
            "dignity": dignity(chart, name),
            "d9_sign": d9.planets[name].sign,
            "d10_sign": d10.planets[name].sign,
            "vargottama": d9.planets[name].vargottama,
        })

    transits = []
    for name in PLANETS:
        tp = snapshot.planets[name]
        transits.append({
            "name": name, "sign": tp.sign, "dms": tp.position.dms,
            "natal_house": tp.natal_house, "retro": tp.retrograde,
        })

    # ONE ledger for the page. The domain readings and the Transits pane
    # are both composed from it, and a second build would only be a second
    # place for the two to disagree.
    facts = chartfacts.fact_index(chart, now)

    lagna_nak = nakshatra_table(chart)["Lagna"]
    today_moon_nak = nakshatra_of(snapshot.planets["Moon"].position.longitude)
    panca = pancanga_for(birth, now)
    born = birth.local_datetime.strftime("%-d %B %Y, %H:%M")
    headline = f"Chart of {profile.name}" if profile.name else "Janma kundli"
    subline = born + (f" · {birth.place}" if birth.place else "")
    return {
        "profile": profile,
        "headline": headline,
        "subline": subline,
        "birth": birth,
        "chart": chart,
        "lagna_sign": chart.lagna.sign,
        "lagna_dms": chart.lagna.dms,
        "lagna_nak": lagna_nak,
        "moon": chart.planets["Moon"],
        "moon_nak": timeline.moon_nakshatra,
        "today_moon_nak": today_moon_nak,
        "pancanga": panca,
        "reading": read_day(chart, timeline, panca, now,
                            person_key=f"{birth.year}{birth.month}{birth.day}"
                                       f"{birth.hour}{birth.minute}"
                                       f"{birth.latitude}"),
        "match": (guna_milan(profile.name or "You", chart,
                             profile.partner_name or "Partner",
                             compute_chart(profile.partner_birth))
                  if profile.partner_birth else None),
        "statement_theme": DASHA_THEME[current[1].lord] if current else "",
        "ayanamsa": chart.ayanamsa,
        "kundli_d1": kundli_houses(
            chart.lagna.sign_index,
            {p: chart.planets[p].house for p in PLANETS},
            degrees={p: (chart.planets[p].degree_in_sign,
                         chart.planets[p].retrograde) for p in PLANETS},
            lagna_degree=chart.lagna.degree_in_sign,
            marks=marks,
            sav=av_mod.ashtakavarga(chart).sav_by_house),
        "kundli_d9": kundli_houses(
            d9.lagna_sign_index, {p: d9.planets[p].house for p in PLANETS},
            marks=marks),
        "kundli_d10": kundli_houses(
            d10.lagna_sign_index, {p: d10.planets[p].house for p in PLANETS},
            marks=marks),
        # Nature and combustion are properties of the BIRTH chart, so the
        # same table serves every plate — the D9 cannot disagree with the D1
        # about which grahas are burnt.
        "marks": marks,
        "d9_lagna": d9.lagna_sign,
        "d10_lagna": d10.lagna_sign,
        "vargottama": [p["name"] for p in planets if p["vargottama"]],
        "planets": planets,
        "mahadashas": mahadashas,
        "antardashas": antardashas,
        "current_md": current[0].lord if current else None,
        "current_ad": current[1].lord if current else None,
        "current_ad_end": _fmt(current[1].end) if current else None,
        "transits": transits,
        "conjunctions": [c for c in contacts if c.kind == "conjunction"],
        "aspect_contacts": [c for c in contacts if c.kind == "aspect"],
        "explorer": planet_explorer(chart),
        "life": life_timeline(chart, timeline, now),
        "weather_framing": WEATHER_FRAMING,
        "weather": transit_weather(chart, snapshot),
        "doshas": doshas_all(chart, now),
        # ONE ENTRY PER PHENOMENON. `combinations()` resolves the
        # overlap between the two lists — see its docstring.
        "combinations": combinations(chart, now),
        "ask": ask_all(ChartContext(chart, timeline, now)),
        "lessons": LESSONS,
        "context_lessons": CONTEXT_LESSONS,
        # A yoga is READ now, not merely detected: whether the divisional
        # charts confirm it, what it classically gives, when its planets'
        # periods run, and which houses it touches. See yogaread.py.
        "yogas": [(r, explain_yoga(chart, r.yoga))
                  for r in yogaread.read_all(chart, now)],
        # Yogas explain inline on their own cards, so the Paṭha feed
        # covers lagna, grahas, nakshatras, dasha and gocara only.
        "patha": explain_dashboard(chart, timeline, snapshot, []),
        "today": now,
        # --- grounded agent panel (v1.1) ---
        "agent_ready": agent.is_configured(),
        "agent_suggestions": agent.SUGGESTED_QUESTIONS,
        "agent_max": agent.MAX_QUESTIONS_PER_SESSION,
        # Per-render id, only ever used as a rate-limit key. Not a login,
        # not stored, and carries nothing about the person.
        "agent_sid": secrets.token_urlsafe(12),
        # Echoed back with each question so no birth record is held server
        # side between requests.
        #
        # THE SCHOOL TRAVELS WITH THE BIRTH DATA, and for the same reason.
        # The selection used to reach /ask only through the ContextVar, which
        # /ask never set — so a question was answered under whatever school
        # the last request in that worker happened to leave behind. A reader
        # who chose "the nodes reach nowhere" got their chart on the form and
        # the default chart in the answer, and a reader who chose nothing
        # could get someone else's school. Same field names as the form
        # (`school_<id>`), so one `schools.normalise` reads both surfaces.
        "agent_birth": {
            "date": f"{birth.year:04d}-{birth.month:02d}-{birth.day:02d}",
            "time": f"{birth.hour:02d}:{birth.minute:02d}",
            "lat": str(birth.latitude), "lon": str(birth.longitude),
            "tz": birth.tz, "place": birth.place,
            **{f"school_{oid}": value
               for oid, value in schools.active().items()},
        },
        # The school behind any section whose numbers depend on one. Printed
        # on the verdict itself, not only on the settings panel the reader
        # has already scrolled past.
        # Three lines, in this order, and they must not wrap to four at
        # 390px — the spec is explicit because an identity strip that
        # reflows is the first thing that makes a phone feel unfinished.
        "identity": [
            f"{chart.lagna.sign} lagna {chart.lagna.dms}",
            f"Moon in {chart.planets['Moon'].sign} · "
            f"{timeline.moon_nakshatra.name} pada "
            f"{timeline.moon_nakshatra.pada}",
            (f"{current[0].lord} mahādaśā · {current[1].lord} antara "
             f"to {_fmt(current[1].end)}" if current else "—"),
        ],
        "domains": domain_cards(chart, now, facts),
        # SCREEN 1 — the glance's Transits pane, NOW and UPCOMING, every noun
        # copied from the same ledger the domain readings were composed from.
        "transits_panel": transits_panel(chart, now, facts),
        # SCREEN 1 — TODAY. Three or four dated lines, each naming a graha,
        # composed by today.py from the ephemeris. See ui-design/DOSSIER.md.
        "day_header": today.day_header(now, panca),
        "today_entries": [
            {"text": e.text, "kind": e.kind, "ids": " · ".join(e.fact_ids)}
            for e in today.entries(chart, now)],
        # The transiting grahas, by the natal house they stand in, for the
        # ticks on the outer edge of the plate.
        "transit_ticks": transit_ticks(chart, now),
        # SCREEN 3 — YOUR CHARTS. What is built, and what is honestly not.
        "vargas": varga_gallery(chart),
        # MILESTONE 2 — Aṣṭakavarga, raw. Verdict first: the strongest and
        # thinnest houses named up front, the 12×8 grid folded under.
        "ashtakavarga": ashtakavarga_view(chart),
        "school_node_reach": schools.chosen("node_reach").school,
        "school_node_position": schools.chosen("node_position").school,
        # The five computations the correctness audit found unreachable.
        "points": points_view(chart),
        "significators": significators_view(chart),
        "strength": strength_view(chart),
        "avasthas": avasthas_view(chart),
        "pratyantar": pratyantar_view(timeline, now),
    }


def points_view(chart) -> dict:
    """The Upapada and the twelve arudhas.

    WHERE THE SCHOOLS SPLIT, THIS IS NOT A HEDGE AND MUST NOT READ AS ONE.
    Two traditions count the arudha of a Scorpio or Aquarius house from
    different lords and arrive at different signs. Both are answers; the
    app has not failed to decide, the tradition has not decided. So the
    view hands the template two NAMED readings — each with its school and
    its reasoning — rather than a value plus a warning. The template sets
    them as a pair of equals; `TestPointsSection` asserts there is no
    error styling and no word of apology anywhere near them.
    """
    view = arudhas.describe(chart)
    both = arudhas.both_schools(chart)
    sole = schools.OPTIONS["dual_lord"].answer("single")
    stronger = schools.OPTIONS["dual_lord"].answer("stronger")
    rows = []
    for house in range(1, 13):
        sign_index = view["arudhas"][house - 1]
        split = both["single"][house - 1] != both["stronger"][house - 1]
        rows.append({
            "house": house,
            "label": f"A{house}",
            "sign": SIGNS[sign_index],
            "house_from_lagna": (sign_index - chart.lagna.sign_index) % 12 + 1,
            "occupants": [p for p in PLANETS
                          if chart.planets[p].sign_index == sign_index],
            "lord": arudhas.SIGN_LORDS[sign_index],
            "split": split,
            "readings": ([
                {"sign": SIGNS[both["single"][house - 1]],
                 "school": sole.school, "text": sole.text},
                {"sign": SIGNS[both["stronger"][house - 1]],
                 "school": stronger.school, "text": stronger.text},
            ] if split else []),
        })
    upapada = rows[11]
    return {
        "rows": rows,
        "upapada": {**upapada, **{
            "sign": view["upapada_sign"],
            "occupants": view["upapada_occupants"],
            "lord": view["upapada_lord"],
            "house_from_lagna": view["upapada_house"],
        }},
        "school": view["school"],
        "contested_houses": list(view["contested_houses"]),
        "schools_agree": view["schools_agree"],
        "why_two": ("Scorpio and Aquarius are each claimed by two lords, "
                    "and an arudha is counted FROM the lord — so the two "
                    "traditions land on different signs. Both readings are "
                    "shown; the one you chose is in force."),
    }


def significators_view(chart) -> dict:
    """The chara karakas, the Kārakāṃśa, and the Dārakāraka.

    The Dārakāraka and the Upapada both speak to marriage and can point
    different ways. They are presented side by side WITHOUT a combined
    verdict: composing them is a reading, and a reading is the resolver's
    job rather than a table's.
    """
    ranked = karakas.karakas(chart)
    return {
        "karakas": [{
            "office": k.office, "abbr": k.abbr, "planet": k.planet,
            "signifies": k.signifies,
            "sign": chart.planets[k.planet].sign,
            "house": chart.planets[k.planet].house,
            "degree": f"{k.degree_in_sign:.2f}°",
            "ranked_by": f"{k.ranked_by:.2f}°",
            "reversed": k.reversed_for_rahu,
        } for k in ranked],
        "karakamsa": karakas.karakamsa(chart),
        "darakaraka": ranked[-1].planet,
        "school": schools.chosen("karaka_count").school,
        "scheme": karakas.scheme(),
        "ties": karakas.tie_groups(chart),
    }


def strength_view(chart) -> dict:
    """Viṃśopaka bala — every graha's score out of twenty, with its working."""
    view = vimsopaka.describe(chart)
    # Formatted from the RAW score, not from `describe`'s 4dp rounding.
    # Rounding twice can move the last displayed digit — 15.074999… rounds
    # to 15.075 and then to 15.08, where the raw value shows 15.07 — and a
    # number the reader can check against the working underneath it must
    # be the number that working produces.
    raw = vimsopaka.scores(chart)
    return {
        **view,
        "rows": [{
            "planet": planet,
            "score": f"{raw[planet]:.2f}",
            "band": view["bands"][planet],
            "working": vimsopaka.working(chart, planet),
        } for planet in vimsopaka.BODIES],
    }


def avasthas_view(chart) -> dict:
    """Bālādi and jāgradādi, keyed by graha so the table can join them."""
    view = avasthas.describe(chart)
    return {"by_planet": {row["planet"]: row for row in view["avasthas"]},
            "at_odds": view["at_odds"],
            "nodes_excluded": view["nodes_excluded"]}


def pratyantar_view(timeline, now) -> dict | None:
    """The running third level, or None outside the cycle."""
    running = timeline.at_depth(now)
    if running is None:
        return None
    maha, antara, pratyantara = running
    return {"maha": maha.lord, "antara": antara.lord,
            "lord": pratyantara.lord,
            "start": _fmt(pratyantara.start), "end": _fmt(pratyantara.end)}


# The five domain cards and their views. Card titles are the reader's
# words; `domains.py` holds the astrology, `domainread.py` the composition.
DOMAIN_TITLES = {
    "marriage": "Love & Marriage",
    "career": "Work & Money",
    "home": "Home & Family",
    "vitality": "Body & Vitality",
    "learning": "Learning & Path",
}
# The order they appear in the grid — what people ask about most, first.
DOMAIN_ORDER = ("marriage", "career", "home", "vitality", "learning")

# Which checklist steps each kind of signal belongs under, so the expanders
# follow the method's own order rather than the order signals happened to be
# composed in.
_STEP_OF_ID = (
    ("NATAL", ("natal.", "house.")),
    ("KARAKA", ("karaka.",)),
    ("VARGA", ("d9.", "d10.", "varga.")),
    ("DASHA", ("dasha.",)),
    ("TRANSIT", ("transit.", "contact.")),
)


def _step_for(fact_ids) -> str:
    """The earliest checklist step any of these facts belongs to."""
    for step, prefixes in _STEP_OF_ID:
        if any(fid.startswith(prefixes) for fid in fact_ids):
            return step
    return "NATAL"


def domain_cards(chart, now: datetime, facts: dict | None = None) -> list[dict]:
    """Everything the arrival grid and the five domain views need.

    Composed once from one build of the ledger — five domains sharing a
    single pass rather than five. `facts` is that build, passed in by the
    dashboard so the Transits pane reads the same ledger rather than
    building a second one.
    """
    import domainread
    from chartfacts import build_facts
    from domains import CHECKLIST, DOMAINS
    if facts is None:
        facts = {f.id: f for f in build_facts(chart, now)}
    steps = dict(CHECKLIST)
    out = []
    for did in DOMAIN_ORDER:
        reading = domainread.read(chart, now, did, facts)
        domain = DOMAINS[did]
        grouped: dict[str, list] = {name: [] for name, _ in CHECKLIST}
        for signal in reading.signals:
            grouped[_step_for(signal.fact_ids)].append(
                {"text": signal.text[0].upper() + signal.text[1:],
                 "ids": " · ".join(signal.fact_ids)})
        out.append({
            "id": did,
            "title": DOMAIN_TITLES[did],
            "label": domain.label,
            "teaser": reading.teaser,
            # The verdict is paragraphs[0]; carried separately so the view can
            # set it in the answering voice and the rest in the working one.
            "verdict": reading.verdict,
            "paragraphs": list(reading.paragraphs[1:]),
            "caveat": reading.caveat,
            "confidence": reading.confidence,
            "houses_label": ", ".join(
                f"the {ordinal(h)}" for h in domain.houses),
            "ask_hint": (
                f"The agent works the same five frames this page just "
                f"showed you — {domain.label} is read from "
                + ", ".join(f"the {ordinal(h)}" for h in domain.houses)
                + f", with {domain.karakas[0]} as its natural significator "
                f"and the {domain.varga} as its test."),
            "steps": [
                {"title": name.title(), "do": steps[name],
                 "count": len(grouped[name]), "rows": grouped[name]}
                for name, _ in CHECKLIST
                if name != "SYNTHESIS" and grouped[name]
            ],
        })
    return out


def life_timeline(chart, timeline, now: datetime) -> dict:
    """Data for the dasha life-graph: 120-year bands with themes, the
    'You are HERE' marker, and dated upcoming transit (ingress) markers."""
    birth = timeline.birth

    def age_of(dt: datetime) -> float:
        return (dt - birth).total_seconds() / (365.25 * 86400)

    bands = []
    for md in timeline.mahadashas:
        start = max(md.start, birth)
        a0, a1 = age_of(start), age_of(md.end)
        status = ("past" if md.end <= now
                  else "current" if md.start <= now else "future")
        bands.append({
            "lord": md.lord,
            "start_age": round(a0, 2), "end_age": round(a1, 2),
            "x": round(a0 / 120 * 1000, 1),
            "w": round((a1 - a0) / 120 * 1000, 1),
            "years": f"{start:%Y}–{md.end:%Y}",
            "status": status,
            "theme": DASHA_THEME[md.lord],
            "elapsed": round(min(1.0, max(
                0.0, (now - start).total_seconds()
                / (md.end - start).total_seconds())), 3),
        })

    lagna_sign = chart.lagna.sign_index
    markers = []
    for e in upcoming_ingresses(now, horizon_days=1095):
        markers.append({
            "date": e.when.strftime("%b %Y"),
            "iso": e.when.strftime("%Y-%m-%d"),
            "planet": e.planet,
            "to_sign": e.to_sign,
            "natal_house": (e.to_sign_index - lagna_sign) % 12 + 1,
            "daylabel": e.when.strftime("%d %b %y"),
            # markers live on their own 3-year strip, not the 120y axis
            "x": round((e.when - now).days / 1095 * 1000, 1),
        })
    markers = markers[:8]

    # De-collision: labels rotate across three rows; within a row each
    # label keeps ≥ MIN_GAP horizontal clearance, sliding right and taking
    # a leader line when displaced from its diamond.
    MIN_GAP = 118.0
    last_x = {0: -1e9, 1: -1e9, 2: -1e9}
    for i, m in enumerate(sorted(markers, key=lambda m: m["x"])):
        row = i % 3
        label_x = min(max(m["x"], last_x[row] + MIN_GAP), 1000 - 4)
        last_x[row] = label_x
        m["row"] = row
        m["label_x"] = round(label_x, 1)
        m["displaced"] = abs(label_x - m["x"]) > 2

    return {
        "bands": bands,
        "here_age": round(age_of(now), 1),
        "here_x": round(age_of(now) / 120 * 1000, 1),
        "markers": markers,
    }


_DATE_DAY_FIRST_RE = re.compile(r"^\s*(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{4})\s*$")
_DATE_BARE_RE = re.compile(r"^\s*(\d{2})(\d{2})(\d{4})\s*$")
_DATE_ISO_RE = re.compile(r"^\s*(\d{4})-(\d{2})-(\d{2})\s*$")


def _parse_date(text: str) -> datetime:
    """Day-first ('25/03/1994'), separator-free ('25031994') or ISO.

    DAY-FIRST IS NOT A PREFERENCE, IT IS THE WHOLE POINT. `<input type="date">`
    renders in the *system* locale, so 03/04/1990 meant 3 April in one
    visitor's browser and 4 March in another's — two different charts, from
    the same keystrokes, with no error shown either time. A wrong date is a
    wrong chart, silently. One order, stated on the field, parsed the same way
    for everyone.

    ISO stays accepted because the agent panel re-posts the birth details as
    'YYYY-MM-DD' on every question (no birth record is held server-side), and
    because it is unambiguous. The two shapes cannot collide: ISO leads with
    four digits, day-first with at most two.
    """
    raw = (text or "").strip()
    m = _DATE_ISO_RE.match(raw)
    if m:
        year, month, day = (int(g) for g in m.groups())
    else:
        m = _DATE_DAY_FIRST_RE.match(raw) or _DATE_BARE_RE.match(raw)
        if not m:
            raise ValueError(
                "Date must be day first — e.g. 25/03/1994 for 25 March 1994.")
        day, month, year = (int(g) for g in m.groups())
    if not 1 <= day <= 31:
        raise ValueError("The day runs 01–31.")
    if not 1 <= month <= 12:
        raise ValueError(
            "The month runs 01–12. Dates here are day first, so 03/04/1990 "
            "is 3 April 1990 — not 4 March.")
    try:
        return datetime(year, month, day)
    except ValueError:
        raise ValueError(
            f"{day:02d}/{month:02d}/{year} is not a real calendar date.")


def schools_from_fields(fields) -> dict[str, str]:
    """The computation-school selection from form or JSON fields.

    The companion to `birth_from_fields`, and stateless for the same reason:
    the selection rides with every request rather than living in worker
    state between them.

    `normalise` does the defending — an unknown option id is dropped, an
    unknown answer falls back to the recommended one, and an option that is
    not live is forced to its default. So a hand-edited request cannot
    switch on a school this build cannot actually compute, and a request
    with no school fields at all gets the documented defaults rather than
    whatever the last caller left in the ContextVar.
    """
    return schools.normalise(
        {oid: (fields.get(f"school_{oid}") or "") for oid in schools.OPTIONS})


def birth_from_fields(fields, prefix: str = "") -> BirthData:
    """A BirthData from form or JSON fields. Shared by / and /ask.

    /ask re-posts the birth details rather than the server holding a chart
    between requests: no birth record is stored server-side, not even for
    the length of a session.
    """
    def get(name: str) -> str:
        return (fields.get(prefix + name) or "").strip()

    date = _parse_date(get("date"))
    hour, minute = parse_time(get("time"))
    tz = get("tz")
    if not tz:
        raise ValueError(
            "No timezone. Pick a city from the suggestions (which sets "
            "it automatically) or enter one manually — the birth "
            "timezone must never be guessed.")
    if not get("lat") or not get("lon"):
        raise ValueError(
            "No coordinates. Pick a city from the suggestions or enter "
            "latitude and longitude manually.")
    return BirthData(
        year=date.year, month=date.month, day=date.day,
        hour=hour, minute=minute,
        latitude=parse_coord(get("lat"), "latitude"),
        longitude=parse_coord(get("lon"), "longitude"),
        tz=tz, place=get("place"),
    )


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "GET":
        # Reset explicitly: a worker thread is reused between requests, and
        # a GET must not inherit the previous visitor's answers.
        schools.set_active({})
        return render_template("index.html", data=None, error=None, form={},
                               schools=schools.payload())

    form = request.form
    # The reader's answers to the computation questions, held for the whole
    # request. Everything downstream — engine, drishti, ledger — reads them
    # from the context, so no signature in six modules had to change.
    selection = schools_from_fields(form)
    schools.set_active(selection)
    try:
        date = _parse_date(form.get("date", ""))
        hour, minute = parse_time(form.get("time", ""))
        tz = form.get("tz", "").strip()
        if not tz:
            raise ValueError(
                "No timezone. Pick a city from the suggestions (which sets "
                "it automatically) or enter one manually — the birth "
                "timezone must never be guessed.")
        if not form.get("lat", "").strip() or not form.get("lon", "").strip():
            raise ValueError(
                "No coordinates. Pick a city from the suggestions or enter "
                "latitude and longitude manually.")
        birth = BirthData(
            year=date.year, month=date.month, day=date.day,
            hour=hour, minute=minute,
            latitude=parse_coord(form["lat"], "latitude"),
            longitude=parse_coord(form["lon"], "longitude"),
            tz=tz, place=form.get("place", "").strip(),
        )
        partner_birth = None
        if form.get("p_date", "").strip():
            p_date = _parse_date(form.get("p_date", ""))
            p_hour, p_minute = parse_time(form.get("p_time", ""))
            p_tz = form.get("p_tz", "").strip()
            if not p_tz or not form.get("p_lat", "").strip():
                raise ValueError(
                    "The partner's place is incomplete — pick a city from "
                    "the suggestions so coordinates and timezone come with "
                    "it, or clear the partner block.")
            partner_birth = BirthData(
                year=p_date.year, month=p_date.month, day=p_date.day,
                hour=p_hour, minute=p_minute,
                latitude=parse_coord(form["p_lat"], "latitude"),
                longitude=parse_coord(form["p_lon"], "longitude"),
                tz=p_tz, place=form.get("p_place", "").strip())
        profile = Profile(name=form.get("name", "").strip(), birth=birth,
                          partner_name=form.get("p_name", "").strip(),
                          partner_birth=partner_birth)
        data = build_dashboard(profile)
    except ValueError as exc:
        return render_template("index.html", data=None, form=form,
                               schools=schools.payload(),
                               error=str(exc)), 400
    except Exception as exc:  # bad date/tz/coords — show it on the form
        return render_template("index.html", data=None, form=form,
                               schools=schools.payload(),
                               error=f"Could not cast the chart: {exc}"), 400
    return render_template("index.html", data=data, error=None, form=form,
                           schools=schools.payload())


@app.route("/ask", methods=["POST"])
def ask_endpoint():
    """One grounded question about a chart.

    The birth details ride along with every request rather than the server
    holding a chart between calls: no birth record is stored server-side,
    and the endpoint stays as stateless as the rest of the app.

    THE SCHOOL RIDES ALONG TOO, and `schools.use` scopes it to this request.
    This endpoint used to set nothing, so everything downstream read the
    ContextVar as the previous request in that worker had left it — the
    reader's own choice was ignored, and under a threaded worker one
    reader's school could answer another reader's question. `use` restores
    the previous value on the way out, so a request can neither inherit a
    selection nor leave one behind.
    """
    body = request.get_json(silent=True) or {}
    session_id = str(body.get("sid", "")).strip()[:64]
    if not session_id:
        return jsonify(error="Missing session id — reload the page."), 400

    ip = (request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
          or request.remote_addr or "unknown")
    allowed, reason, remaining = agent.LIMITER.check(ip, session_id)
    if not allowed:
        return jsonify(error=reason, remaining=remaining), 429

    try:
        birth = birth_from_fields(body)
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    except Exception as exc:
        return jsonify(error=f"Could not read the birth details: {exc}"), 400

    with schools.use(schools_from_fields(body)):
        return _answer_one_question(body, birth, ip, session_id)


def _answer_one_question(body, birth, ip: str, session_id: str):
    """The body of /ask, run inside the caller's school selection.

    Split out so the `with` block is the whole handler and cannot be
    half-applied: every computation below — the chart, the drishti, the
    ledger, the agent's payload — reads the selection from the context.
    """
    try:
        chart = compute_chart(birth)
        when = datetime.now(timezone.utc)
        answer = agent.ask_chart(chart, when, body.get("question", ""))
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    except agent.AgentUnavailable as exc:
        return jsonify(error=str(exc)), 503

    if not answer.ok:
        # The model asserted something the chart does not support. The
        # answer is withheld rather than shown with a warning: a caveat
        # under a fluent wrong sentence is not a correction, and this is
        # exactly the failure the feature exists to prevent.
        #
        # AND IT IS NOT CHARGED. The limiter is recorded below this branch,
        # not above it: a withheld answer is our validator catching our
        # model, and billing the reader a question for it makes them pay
        # for our failure. At five questions a session that is a fifth of
        # what they have. The API call was made and cost us something —
        # that is our problem, not theirs.
        agent.log_correction(
            body.get("question", ""), answer.answer,
            reason="withheld: failed ledger validation",
            facts_used=answer.facts_used, model=answer.model,
            violations=answer.violations)
        why, hint = agent.explain_violations(answer.violations)
        # Answer-first applies to the bad news too. The old wording led with
        # the word "Withheld" and put the one useful sentence — what to ask
        # instead — at the very end, behind an explanation of our own
        # machinery. The action comes first now; the reason follows it, once.
        return jsonify(
            error=f"{hint} That reply {why}, so it was not shown.",
            withheld=True,
            violations=[f"{v.kind}: {v.detail}" for v in answer.violations],
            # Unchanged, and said so out loud: the counter on screen must
            # not move, or the reader is told they were charged.
            remaining=agent.LIMITER.remaining(session_id)), 422

    agent.LIMITER.record(ip, session_id)
    remaining = agent.LIMITER.remaining(session_id)

    import rulelib
    facts = {f.id: f.statement for f in chartfacts.build_facts(chart, when)}
    brief = chartfacts.domain_brief(chart, body.get("question", ""))
    steps = agent.steps_walked(answer, brief)
    return jsonify(
        answer=answer.answer,
        # THE ANSWER SPLIT FOR THE SCREEN. The verdict is a field of its own
        # so answer-first is structural; the rest arrives as paragraphs the
        # page can set without parsing prose in JavaScript.
        verdict=answer.verdict or "",
        paragraphs=[p.strip() for p in answer.answer.split("\n")
                    if p.strip()],
        # Which of the six steps the answer actually worked, from the facts
        # it cited rather than from anything it claimed. See
        # `agent.steps_walked`.
        steps=[{**st,
                "facts": [{"id": fid, "statement": facts.get(fid, "")}
                          for fid in st["facts"]]}
               for st in steps],
        domain=(brief or {}).get("title") or (brief or {}).get("id") or "",
        statements=answer.statements,
        facts_used=[{"id": fid, "statement": facts.get(fid, "")}
                    for fid in answer.facts_used],
        rules_applied=[
            {"id": rid,
             "text": rulelib.RULES[rid].text if rid in rulelib.RULES else rid,
             "source": (rulelib.RULES[rid].source
                        if rid in rulelib.RULES else "")}
            for rid in answer.rules_applied],
        confidence=answer.confidence,
        refused=answer.refused,
        refusal_reason=answer.refusal_reason,
        remaining=remaining,
    )


@app.route("/ask/feedback", methods=["POST"])
def ask_feedback():
    """Thumbs-down: append the Q/A to the corrections log."""
    body = request.get_json(silent=True) or {}
    question = str(body.get("question", ""))[:agent.MAX_QUESTION_CHARS]
    answer = str(body.get("answer", ""))[:4000]
    if not question or not answer:
        return jsonify(error="Nothing to record."), 400
    agent.log_correction(
        question, answer, reason="thumbs-down",
        facts_used=[str(f)[:80] for f in body.get("facts_used", [])][:40],
        model=str(body.get("model", ""))[:64])
    return jsonify(ok=True)


def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name, "").strip().lower()
    if not raw:
        return default
    return raw in ("1", "true", "yes", "on")


if __name__ == "__main__":
    # Local development entry point only. In production the app is served by
    # gunicorn (see Procfile), which imports `app` directly and never runs
    # this block — so debug can never be switched on by deploying.
    app.run(
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "5000")),
        debug=_env_flag("FLASK_DEBUG", default=True),
    )
