"""Sidera — single-page Flask UI: birth form → dashboard.

Implements the "Colophon" direction from ui-design/Astrology App.dc.html:
ink ground, cream text, gold hairlines, Cormorant Garamond / Lora,
North-Indian kundli plate with D1/D9/D10 tabs, dasha ledger, gocara
(transits), yogas and nakshatra table.
"""
from __future__ import annotations

import json
import os
import secrets
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, jsonify, render_template, request

from dashas import nakshatra_of, nakshatra_table, vimshottari
from ask import ChartContext, ask_all
from pancanga import pancanga_for
from gunamilan import fraction, guna_milan
from reading import read_day
from doshas import WEATHER_FRAMING, doshas_all, myth_busters, transit_weather
from lessons import CONTEXT_LESSONS, LESSONS
from engine import SIGNS, PLANETS, BirthData, compute_chart
from explain import DASHA_THEME, explain_dashboard, explain_yoga, ordinal
from transits import (
    DRISHTI_OFFSETS,
    transit_contacts,
    transit_snapshot,
    upcoming_ingresses,
)
from vargas import dasamsa, navamsa
import agent
import chartfacts
from yogas import detect_all, dignity, dignity_grade

app = Flask(__name__)
app.template_filter("ordinal")(ordinal)  # '3' → '3rd', app-wide
app.template_filter("fraction")(fraction)  # 28.5 → '28½'


@app.context_processor
def _plate_geometry():
    """The plate tables, available to every template render.

    Injected rather than duplicated in the template so the browser's
    highlight layer and the server's placement layer cannot disagree.
    """
    return {"house_poly": HOUSE_POLY, "house_center": HOUSE_CENTER}


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
# Separator-free fallback: '1312' or '812'. The field is <input type="time">,
# which submits 'HH:MM', but a browser that does not support it degrades to a
# plain text box — and on a phone that box may only offer digits.
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


ABBR = {
    "Sun": "Su", "Moon": "Mo", "Mars": "Ma", "Mercury": "Me",
    "Jupiter": "Ju", "Venus": "Ve", "Saturn": "Sa", "Rahu": "Ra", "Ketu": "Ke",
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
                  lagna_degree: float | None = None) -> list[dict]:
    """Per-house render data for the North-Indian SVG plate.

    `degrees` maps planet → (degree_in_sign, retrograde) and yields the
    detail labels ('Ju 15°33′', 'Sa 9°29′ R'). Divisional charts pass None —
    varga positions are sign-level, so degree labels apply to D1 only.
    """
    labels: dict[int, list[str]] = {h: [] for h in range(1, 13)}
    detail: dict[int, list[str]] = {h: [] for h in range(1, 13)}
    labels[1].append("As")
    if lagna_degree is not None:
        detail[1].append(f"As {_deg_min(lagna_degree)}")
    for name in PLANETS:
        h = house_of[name]
        labels[h].append(ABBR[name])
        if degrees is not None:
            deg, retro = degrees[name]
            detail[h].append(
                f"{ABBR[name]} {_deg_min(deg)}" + (" R" if retro else ""))

    houses = []
    for h in range(1, 13):
        row = labels[h]
        line1, line2 = row, []
        if len(row) > 3:  # wrap crowded houses onto two lines
            mid = (len(row) + 1) // 2
            line1, line2 = row[:mid], row[mid:]
        x, y = PLANET_POS[h]
        houses.append({
            "house": h,
            "sign_num": (lagna_sign_index + h - 1) % 12 + 1,
            "num_pos": NUMBER_POS[h],
            "pl_pos": PLANET_POS[h],
            "deg_pos": DEG_POS[h],
            "line1": "·".join(line1),
            "line2": "·".join(line2),
            "detail_lines": detail[h],
            # Three stacked degree labels fill a narrow triangle completely.
            # The sign number underneath them is then unreadable, so it is
            # dropped WHILE THE DEGREE LAYER IS ON — the compact view still
            # shows it, and the sign is never lost (it is in the graha
            # table). Better one legible number fewer than two illegible
            # overlapping texts.
            "crowded": len(detail[h]) >= 3,
        })
    return houses


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
            "house": pos.house,
            "label": f"{pos.sign} {pos.dms}",
            "retro": pos.retrograde,
            "dignity": dignity_grade(chart, name) or dignity(chart, name),
            "nakshatra": f"{nak.name} pada {nak.pada}",
            "nak_lord": nak.lord,
            "nak_lord_house": chart.planets[nak.lord].house,
            "aspects": aspects,
        }
    return out


def build_dashboard(profile: Profile) -> dict:
    birth = profile.birth
    chart = compute_chart(birth)
    d9, d10 = navamsa(chart), dasamsa(chart)
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
            lagna_degree=chart.lagna.degree_in_sign),
        "kundli_d9": kundli_houses(
            d9.lagna_sign_index, {p: d9.planets[p].house for p in PLANETS}),
        "kundli_d10": kundli_houses(
            d10.lagna_sign_index, {p: d10.planets[p].house for p in PLANETS}),
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
        "mythbusters": myth_busters(chart, now),
        "ask": ask_all(ChartContext(chart, timeline, now)),
        "lessons": LESSONS,
        "context_lessons": CONTEXT_LESSONS,
        "yogas": [(y, explain_yoga(chart, y)) for y in detect_all(chart)],
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
        "agent_birth": {
            "date": f"{birth.year:04d}-{birth.month:02d}-{birth.day:02d}",
            "time": f"{birth.hour:02d}:{birth.minute:02d}",
            "lat": str(birth.latitude), "lon": str(birth.longitude),
            "tz": birth.tz, "place": birth.place,
        },
    }


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


def _parse_date(text: str) -> datetime:
    try:
        return datetime.strptime(text.strip(), "%Y-%m-%d")
    except ValueError:
        raise ValueError("Date must be a real calendar date (YYYY-MM-DD).")


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
        return render_template("index.html", data=None, error=None, form={})

    form = request.form
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
                               error=str(exc)), 400
    except Exception as exc:  # bad date/tz/coords — show it on the form
        return render_template("index.html", data=None, form=form,
                               error=f"Could not cast the chart: {exc}"), 400
    return render_template("index.html", data=data, error=None, form=form)


@app.route("/ask", methods=["POST"])
def ask_endpoint():
    """One grounded question about a chart.

    The birth details ride along with every request rather than the server
    holding a chart between calls: no birth record is stored server-side,
    and the endpoint stays as stateless as the rest of the app.
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

    try:
        chart = compute_chart(birth)
        when = datetime.now(timezone.utc)
        answer = agent.ask_chart(chart, when, body.get("question", ""))
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    except agent.AgentUnavailable as exc:
        return jsonify(error=str(exc)), 503

    agent.LIMITER.record(ip, session_id)
    remaining = agent.LIMITER.remaining(session_id)

    if not answer.ok:
        # The model asserted something the chart does not support. The
        # answer is withheld rather than shown with a warning: a caveat
        # under a fluent wrong sentence is not a correction, and this is
        # exactly the failure the feature exists to prevent.
        agent.log_correction(
            body.get("question", ""), answer.answer,
            reason="withheld: failed ledger validation",
            facts_used=answer.facts_used, model=answer.model,
            violations=answer.violations)
        why, hint = agent.explain_violations(answer.violations)
        return jsonify(
            error=(f"Withheld: {why}, so it was not shown. {hint}"),
            withheld=True,
            violations=[f"{v.kind}: {v.detail}" for v in answer.violations],
            remaining=remaining), 422

    import rulelib
    facts = {f.id: f.statement for f in chartfacts.build_facts(chart, when)}
    return jsonify(
        answer=answer.answer,
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
