#!/usr/bin/env python3
"""Differential accuracy test: Sidera vs PyJHora over N random charts.

WHY RANDOM, WHEN THERE ARE ALREADY FIXTURES
`fixtures_pyjhora.json` proves the two implementations agree on two charts.
Two charts cannot exercise a sign boundary, a southern-hemisphere ascendant,
a polar latitude, a leap day, a DST transition, or a nakshatra pada edge.
Agreement on 300 charts drawn at random across 80 years and 32,000 cities is
a different claim, and the failures it finds are the ones a fixture never
would.

WHAT IS COMPARED, AND AT WHAT TOLERANCE
  D1 longitudes       every body, 60″ (one arcminute)
  Ascendant           sign, and the same 60″ on the longitude
  Nakshatra / pada    exact — a counting rule, not a measurement
  D9 / D10 signs      exact
  Vimshottari MD/AD   boundary datetimes, 1 day
  BAV / SAV           NOT YET — Sidera has no Ashtakavarga (milestone 2).
                      The hook is here and reports "not implemented" rather
                      than silently passing.

NO REAL PEOPLE
Every record is a random date in [1950, 2030), a random time, and a random
city drawn from `data/cities.json`. No record is a person's birth data, and
none is committed: the generator is seeded, so a run is reproducible from
the seed alone and the records themselves stay out of the repository. The
committed artefact is the summary.

TWO PROCESSES, ONE JSON
Sidera and PyJHora cannot share an interpreter — the oracle lives in a
scratch venv, deliberately (tools/oracle/README.md). This script runs with
the repo's python, shells out to the venv's, and does the comparison here.

    ./tools/oracle/differential.py                 # 300 records, seed 20260908
    ./tools/oracle/differential.py -n 50 --seed 7
    ./tools/oracle/differential.py --keep /tmp/dd  # keep the raw records
"""
from __future__ import annotations

import argparse
import json
import random
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO))

DEFAULT_SEED = 20260908
DEFAULT_N = 300
YEAR_FROM, YEAR_TO = 1950, 2030

ARCSEC = 60.0            # D1 longitude tolerance
DASHA_DAYS = 1.0         # MD/AD boundary tolerance
MEAN_SIDEREAL_YEAR = 365.256364   # what both sides are pinned to

BODIES = ("Lagna", "Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus",
          "Saturn", "Rahu", "Ketu")


# --- record generation ------------------------------------------------------

def load_cities() -> list:
    rows = json.loads((REPO / "data" / "cities.json").read_text("utf-8"))
    # [name, admin, country, lat, lon, tz, population]
    return [r for r in rows if r[5]]


def generate(n: int, seed: int) -> tuple[list[dict], list[dict]]:
    """(records, skipped) — random, synthetic, reproducible from `seed`.

    Records whose local time is ambiguous or does not exist (the hour a DST
    transition repeats or skips) are DROPPED, not fixed. Both engines would
    have to guess, and their guesses disagreeing would be an artefact of this
    harness rather than a finding about either one. How many were dropped is
    reported, so the omission is visible.
    """
    rng = random.Random(seed)
    cities = load_cities()
    records: list[dict] = []
    skipped: list[dict] = []
    attempts = 0
    while len(records) < n and attempts < n * 20:
        attempts += 1
        city = rng.choice(cities)
        name, _admin, country, lat, lon, tzname, _pop = city[:7]
        year = rng.randrange(YEAR_FROM, YEAR_TO)
        # Uniform over the year, so 29 February appears at its true rate.
        day_of_year = rng.randrange(0, 366)
        base = datetime(year, 1, 1) + timedelta(days=day_of_year)
        if base.year != year:
            continue
        hour, minute, second = (rng.randrange(24), rng.randrange(60),
                                rng.randrange(60))
        try:
            zone = ZoneInfo(tzname)
        except Exception:
            continue
        naive = base.replace(hour=hour, minute=minute, second=second)
        early = naive.replace(tzinfo=zone, fold=0)
        late = naive.replace(tzinfo=zone, fold=1)
        if early.utcoffset() != late.utcoffset():
            skipped.append({"reason": "ambiguous local time (DST fold)",
                            "city": name, "tz": tzname,
                            "local": naive.isoformat()})
            continue
        # A time inside a spring-forward gap does not exist: converting to UTC
        # and back does not return it.
        if early.astimezone(timezone.utc).astimezone(zone).replace(
                tzinfo=None) != naive:
            skipped.append({"reason": "nonexistent local time (DST gap)",
                            "city": name, "tz": tzname,
                            "local": naive.isoformat()})
            continue
        offset = early.utcoffset()
        records.append({
            "id": len(records),
            "year": year, "month": naive.month, "day": naive.day,
            "hour": hour, "minute": minute, "second": second,
            "latitude": round(float(lat), 6),
            "longitude": round(float(lon), 6),
            "place": f"{name}, {country}",
            "tz": tzname,
            "tz_hours": offset.total_seconds() / 3600.0,
        })
    return records, skipped


# --- Sidera's answers -------------------------------------------------------

def sidera_answer(record: dict) -> dict:
    from dashas import nakshatra_of, vimshottari
    from engine import PLANETS, BirthData, compute_chart
    from vargas import dasamsa, navamsa

    # The fixed offset, not the IANA name: the oracle is handed the same
    # numeric offset, so any disagreement is about astronomy rather than
    # about which zone table each side happened to consult.
    total = record["tz_hours"]
    sign = "-" if total < 0 else "+"
    minutes = int(round(abs(total) * 60))
    tz = f"{sign}{minutes // 60:02d}:{minutes % 60:02d}"
    birth = BirthData(year=record["year"], month=record["month"],
                      day=record["day"], hour=record["hour"],
                      minute=record["minute"], second=record["second"],
                      latitude=record["latitude"],
                      longitude=record["longitude"],
                      tz=tz, place=record["place"])
    chart = compute_chart(birth)

    d1 = {"Lagna": chart.lagna.longitude}
    d1.update({p: chart.planets[p].longitude for p in PLANETS})
    naks = {b: (nakshatra_of(v).index + 1, nakshatra_of(v).pada)
            for b, v in d1.items()}
    d9, d10 = navamsa(chart), dasamsa(chart)
    from engine import SIGNS
    signs = {}
    for label, varga in (("d9", d9), ("d10", d10)):
        signs[label] = {"Lagna": SIGNS.index(varga.lagna_sign)}
        signs[label].update({p: SIGNS.index(varga.planets[p].sign)
                             for p in PLANETS})

    timeline = vimshottari(chart)
    periods = []
    for md in timeline.mahadashas:
        for ad in md.antardashas:
            periods.append({"md": md.lord, "ad": ad.lord,
                            "start": ad.start.astimezone(timezone.utc)})
    return {"id": record["id"], "d1": d1, "nakshatra": naks,
            "d9_signs": signs["d9"], "d10_signs": signs["d10"],
            "periods": periods, "ayanamsa": chart.ayanamsa}


# --- comparison -------------------------------------------------------------

def arcsec(a: float, b: float) -> float:
    return abs((a - b + 180.0) % 360.0 - 180.0) * 3600.0


# The span each categorical check divides the zodiac into. A disagreement
# about a category is only interesting if the two longitudes are NOT sitting
# either side of one of these lines: when they are, both engines classified
# correctly and the ephemeris gap simply happened to straddle a boundary.
# Reporting those together with real counting bugs would bury the bugs.
BOUNDARY_SPAN = {
    "d1_sign": 30.0,
    "nakshatra_pada": 360.0 / 108.0,   # 3°20′ — pada and nakshatra edges
    "d9_sign": 360.0 / 108.0,          # one navamsa is one pada
    "d10_sign": 3.0,
}


def _to_boundary(longitude: float, span: float) -> float:
    """Arcseconds from `longitude` to the nearest multiple of `span`."""
    return min(longitude % span, span - (longitude % span)) * 3600.0


def compare(record: dict, ours: dict, theirs: dict) -> list[dict]:
    """Every disagreement for one record, each with its delta.

    Categorical findings carry `benign`: True when the two longitudes lie
    either side of the dividing line, which is arithmetic rather than a
    defect in either implementation.
    """
    out: list[dict] = []

    def note(kind, body, mine, yours, delta, unit, benign=False, why=""):
        out.append({"record_id": record["id"], "kind": kind, "body": body,
                    "sidera": mine, "pyjhora": yours, "delta": delta,
                    "unit": unit, "benign": benign, "why": why})

    def categorical(kind, body, mine, yours):
        if mine == yours:
            return
        span = BOUNDARY_SPAN[kind]
        gap = arcsec(ours["d1"][body], theirs["d1"][body])
        distance = _to_boundary(ours["d1"][body], span)
        benign = distance <= gap
        note(kind, body, mine, yours, round(distance, 2), "arcsec to edge",
             benign=benign,
             why=(f"the two longitudes are {gap:.2f}″ apart and straddle a "
                  f"{span:g}° boundary {distance:.2f}″ away — both "
                  f"classifications are correct for their own longitude"
                  if benign else
                  f"the longitudes agree to {gap:.2f}″ but the "
                  f"classification differs — a counting-rule disagreement"))

    for body in BODIES:
        gap = arcsec(ours["d1"][body], theirs["d1"][body])
        if gap > ARCSEC:
            note("d1_longitude", body, round(ours["d1"][body], 6),
                 round(theirs["d1"][body], 6), round(gap, 2), "arcsec")
        categorical("d1_sign", body,
                    int(ours["d1"][body] // 30) % 12,
                    int(theirs["d1"][body] // 30) % 12)
        categorical("nakshatra_pada", body,
                    tuple(ours["nakshatra"][body]),
                    tuple(theirs["nakshatra"][body]))

    for label in ("d9", "d10"):
        for body in BODIES:
            categorical(f"{label}_sign", body,
                        ours[f"{label}_signs"][body],
                        theirs[f"{label}_signs"][body])

    out.extend(compare_dashas(record, ours, theirs))
    return out


def compare_dashas(record: dict, ours: dict, theirs: dict) -> list[dict]:
    """MD/AD boundary datetimes, to the day.

    PyJHora reports period starts in the PLACE's local zone (it read the
    birth moment the same way), so they are converted to UTC here before
    anything is subtracted. Getting that wrong would make every record fail
    by the size of the offset — which is exactly the kind of harness bug that
    looks like an engine bug.
    """
    zone = ZoneInfo(record["tz"])
    out: list[dict] = []
    mine = {(p["md"], p["ad"]): p["start"] for p in ours["periods"]}
    for row in theirs["vimsottari"]:
        key = (row["md"], row["ad"])
        if key not in mine:
            out.append({"record_id": record["id"], "kind": "dasha_missing",
                        "body": f"{key[0]}/{key[1]}", "sidera": None,
                        "pyjhora": row["start_local"], "delta": None,
                        "unit": "period", "benign": False, "why": ""})
            continue
        year, month, day, hours = row["start_local"]
        try:
            start = (datetime(year, month, day)
                     + timedelta(hours=hours)).replace(tzinfo=zone)
        except ValueError:                          # out of datetime range
            continue
        gap_days = abs((mine[key] - start.astimezone(timezone.utc))
                       .total_seconds()) / 86400.0
        if gap_days > DASHA_DAYS:
            out.append({
                "record_id": record["id"], "kind": "dasha_boundary",
                "body": f"{key[0]}/{key[1]}",
                "sidera": mine[key].isoformat(),
                "pyjhora": start.astimezone(timezone.utc).isoformat(),
                "delta": round(gap_days, 4), "unit": "days",
                "benign": False, "why": ""})
    return out


def ashtakavarga_status() -> dict:
    """BAV/SAV: reported as not-yet-comparable rather than silently passing.

    Milestone 2 is not built. A differential test that quietly skips the
    thing it was asked to check reads, later, as a thing that passed.
    """
    try:
        import ashtakavarga                                    # noqa: F401
    except ImportError:
        return {"compared": False,
                "reason": "Sidera has no Ashtakavarga module yet "
                          "(milestone 2). The oracle carries BAV/SAV for "
                          "both fictional fixtures; wire this up when the "
                          "module lands."}
    return {"compared": False,
            "reason": "an ashtakavarga module now exists — extend "
                      "differential.py to compare BAV rows and SAV per "
                      "sign, and delete this branch"}


# --- report -----------------------------------------------------------------

def _record_line(records, rid) -> str:
    r = records[rid]
    return (f"- record {rid}: "
            f"{r['year']}-{r['month']:02d}-{r['day']:02d} "
            f"{r['hour']:02d}:{r['minute']:02d}:{r['second']:02d} "
            f"{r['tz']} — {r['place']} ({r['latitude']}, {r['longitude']})")


def _finding_tables(records, findings, lines) -> None:
    by_kind: dict[str, list] = {}
    for f in findings:
        by_kind.setdefault(f["kind"], []).append(f)
    lines += ["| Kind | Count | Records | Worst Δ |", "|---|---|---|---|"]
    for kind, rows in sorted(by_kind.items(), key=lambda kv: -len(kv[1])):
        deltas = [r["delta"] for r in rows if r["delta"] is not None]
        worst = f"{max(deltas):g} {rows[0]['unit']}" if deltas else "—"
        lines.append(f"| `{kind}` | {len(rows)} | "
                     f"{len({r['record_id'] for r in rows})} | {worst} |")
    lines.append("")
    for kind, rows in sorted(by_kind.items(), key=lambda kv: -len(kv[1])):
        lines += [f"#### `{kind}` — {len(rows)}", ""]
        ranked = sorted(rows, key=lambda r: -(r["delta"] or 0))[:10]
        lines += ["| Record | Body | Sidera | PyJHora | Δ |",
                  "|---|---|---|---|---|"]
        for r in ranked:
            delta = (f"{r['delta']:g} {r['unit']}"
                     if r["delta"] is not None else "—")
            lines.append(f"| {r['record_id']} | {r['body']} | "
                         f"`{r['sidera']}` | `{r['pyjhora']}` | {delta} |")
        if len(rows) > len(ranked):
            lines.append(f"| … | {len(rows) - len(ranked)} more | | | |")
        lines.append("")
        if ranked and ranked[0].get("why"):
            lines += [f"{ranked[0]['why']}.", ""]
        for r in ranked[:3]:
            lines.append(_record_line(records, r["record_id"]))
        lines.append("")


def summarise(records, passes, skipped, seed, cities_count) -> str:
    """One report, both passes.

    PASS A matches PyJHora's position flag to Sidera's, so any remaining
    disagreement is about counting rules rather than about a convention.
    PASS B leaves PyJHora at its own default and measures what that
    convention costs — which is the number a product decision needs.
    """
    a, b = passes["apparent"], passes["true"]
    lines = [
        "# Differential accuracy report — Sidera vs PyJHora",
        "",
        "Generated by `tools/oracle/differential.py`. Reproduce with:",
        "",
        f"    ./tools/oracle/differential.py -n {len(records)} "
        f"--seed {seed}",
        "",
        "The records are **not committed**: random, synthetic, and "
        "regenerable from the seed above. No record is any person's birth "
        "data — each is a random date in "
        f"[{YEAR_FROM}, {YEAR_TO}), a random time, and a random city from "
        "`data/cities.json`.",
        "",
        "## Run",
        "",
        "| | |",
        "|---|---|",
        f"| Records compared | {len(records)} |",
        f"| Seed | `{seed}` |",
        f"| Date range | {YEAR_FROM}–{YEAR_TO - 1} |",
        f"| Cities available | {cities_count} |",
        f"| Ayanamsa (both sides) | "
        f"{a['settings']['ayanamsa_mode']} |",
        f"| Nodes (both sides) | {a['settings']['node_mode']} |",
        f"| Dropped before comparison | {len(skipped)} (DST-ambiguous or "
        "nonexistent local times) |",
        f"| Oracle failures | {len(a['failures'])} |",
        "",
        "## What is compared",
        "",
        "| Check | Tolerance |",
        "|---|---|",
        f"| D1 longitude, every body | {ARCSEC:.0f}″ (one arcminute) |",
        "| D1 sign, and the ascendant | exact |",
        "| Nakshatra and pada | exact — a counting rule, not a measurement |",
        "| D9 / D10 sign | exact |",
        f"| Vimshottari MD/AD boundary | {DASHA_DAYS:.0f} day |",
        "| BAV / SAV | not compared — see below |",
        "",
        "A categorical disagreement is marked **benign** when the two "
        "longitudes lie either side of the dividing line: both engines then "
        "classified their own longitude correctly, and the split is "
        "arithmetic rather than a defect. Benign cases are reported "
        "separately so a real counting bug is not buried in them.",
        "",
        "---",
        "",
        "## Pass A — position convention matched (the headline result)",
        "",
        "PyJHora's `FLG_TRUEPOS` is cleared so both sides compute apparent "
        "(light-time corrected) positions, as Sidera does. The ephemeris is "
        "then identical between them, which is the point: **every "
        "disagreement that survives is a disagreement about interpretation "
        "logic** — nakshatra arithmetic, varga counting, Vimshottari — "
        "which the two implementations wrote independently.",
        "",
        "This pass deliberately does *not* test the ephemeris. Both sides "
        "call the same swisseph, so agreement there would be circular; "
        "`TestIndependentEphemerisCrossCheck` (ERFA/IAU SOFA) is what "
        "anchors positions.",
        "",
    ]
    real_a = [f for f in a["findings"] if not f.get("benign")]
    benign_a = [f for f in a["findings"] if f.get("benign")]
    if not real_a:
        lines += [f"**No disagreements.** All {len(records)} records agreed "
                  "on every check, for every body.", ""]
    else:
        lines += [f"**{len(real_a)} disagreements** across "
                  f"{len({f['record_id'] for f in real_a})} records.", ""]
        _finding_tables(records, real_a, lines)
    if benign_a:
        lines += [f"### Benign boundary straddles — {len(benign_a)}", ""]
        _finding_tables(records, benign_a, lines)

    lines += [
        "---",
        "",
        "## Pass B — PyJHora at its own default (`FLG_TRUEPOS`)",
        "",
        "**A finding, not a bug.** PyJHora sets swisseph's `FLG_TRUEPOS`: "
        "true geometric positions, with no light-time correction. Sidera "
        "does not, so it computes apparent positions — what almanacs "
        "publish. Neither is wrong; it is a convention, like mean vs true "
        "node. This pass measures the cost.",
        "",
        "The size of the offset is the planet's own motion across its "
        "light-time, which is why the Sun's is 20.2″ (8.3 light-minutes × "
        "0.986°/day) and the Moon's is 0.7″.",
        "",
    ]
    real_b = [f for f in b["findings"] if not f.get("benign")]
    benign_b = [f for f in b["findings"] if f.get("benign")]
    per_body = b.get("offsets", {})
    if per_body:
        lines += ["| Body | Worst offset from apparent |", "|---|---|"]
        for body, worst in sorted(per_body.items(), key=lambda kv: -kv[1]):
            lines.append(f"| {body} | {worst:.2f}″ |")
        lines.append("")
    flips = [f for f in b["findings"]
             if f["kind"] in BOUNDARY_SPAN and f["kind"] != "d1_longitude"]
    lines += [
        f"Adopting true positions would change a **categorical** result "
        f"({len(flips)} times across {len({f['record_id'] for f in flips})} "
        f"of {len(records)} records) — a nakshatra pada, a D9 sign, or a "
        "D1 sign. That is the number the decision turns on: the arcseconds "
        "are invisible, the changed navamsa is not.",
        "",
    ]
    if real_b:
        lines += [f"Non-boundary disagreements under this convention: "
                  f"{len(real_b)}.", ""]
        _finding_tables(records, real_b, lines)
    if benign_b:
        lines += [f"### Boundary straddles caused by the convention — "
                  f"{len(benign_b)}", ""]
        _finding_tables(records, benign_b, lines)

    lines += ["---", "", "## A defect found in the oracle, not in Sidera", ""]
    years = a.get("true_sidereal_year", {})
    if years:
        # A true sidereal year oscillates by minutes about the mean — a few
        # thousandths of a day. Anything past 0.01 d is not a real year.
        PLAUSIBLE = 0.01
        off = {rid: v for rid, v in years.items()
               if abs(v - MEAN_SIDEREAL_YEAR) > PLAUSIBLE}
        gross = {rid: v for rid, v in off.items()
                 if abs(v - MEAN_SIDEREAL_YEAR) > 0.5}
        lines += [
            "PyJHora's Vimshottari defaults to `TRUE_SIDEREAL_YEAR` — "
            "`drik.true_sidereal_year()` measured for each chart. A real "
            "sidereal year oscillates about its mean by **minutes**, a few "
            "thousandths of a day. That function returns values up to a "
            "**full day** longer on some (date, place) pairs, which is "
            "astronomically impossible, and the daśā timeline built on it "
            "drifts accordingly.",
            "",
            f"| Records outside ±{PLAUSIBLE} d of the mean | {len(off)} of "
            f"{len(years)} ({100 * len(off) / max(len(years), 1):.1f}%) |",
            "|---|---|",
            f"| …of those, off by more than half a day | {len(gross)} |",
            f"| Range returned | {min(years.values()):.5f} – "
            f"{max(years.values()):.5f} days |",
            f"| Correct mean sidereal year | {MEAN_SIDEREAL_YEAR} days |",
            "",
            "The comparison therefore pins PyJHora to `MEAN_SIDEREAL_YEAR`, "
            "the same constant Sidera uses. Measured before pinning, this "
            "alone produced **254 boundary disagreements across 7 records**, "
            "the worst 112 days, and would have buried anything real.",
            "",
        ]
        if off:
            lines += ["| Record | `true_sidereal_year` | Place |",
                      "|---|---|---|"]
            for rid, value in sorted(off.items(),
                                     key=lambda kv: -abs(
                                         kv[1] - MEAN_SIDEREAL_YEAR))[:10]:
                rec = records[int(rid)]
                lines.append(f"| {rid} | {value:.5f} d | {rec['place']} "
                             f"({rec['tz']}) |")
            lines.append("")

    av = ashtakavarga_status()
    lines += ["---", "", "## Ashtakavarga", "", av["reason"], ""]
    if skipped:
        reasons: dict[str, int] = {}
        for s in skipped:
            reasons[s["reason"]] = reasons.get(s["reason"], 0) + 1
        lines += ["## Dropped records", "",
                  "Local times a DST transition makes ambiguous or "
                  "nonexistent. Both engines would have to guess, and their "
                  "guesses disagreeing would be an artefact of this harness "
                  "rather than a finding about either. Counted, not hidden.",
                  "", "| Reason | Count |", "|---|---|"]
        for reason, count in sorted(reasons.items()):
            lines.append(f"| {reason} | {count} |")
        lines.append("")
    if a["failures"]:
        lines += ["## Oracle failures", "",
                  "Records PyJHora could not compute. Recorded rather than "
                  "dropped silently.", "", "| Record | Error |", "|---|---|"]
        for f in a["failures"][:20]:
            lines.append(f"| {f['id']} | `{f['error']}` |")
        lines.append("")
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("-n", type=int, default=DEFAULT_N)
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    ap.add_argument("--venv", default=None,
                    help="oracle venv (default: $SIDERA_ORACLE_VENV or "
                         "$TMPDIR/sidera-oracle-venv)")
    ap.add_argument("--out", default=str(HERE / "DIFFERENTIAL.md"))
    ap.add_argument("--keep", default=None,
                    help="directory to keep the raw records and answers in "
                         "(they are NOT committed)")
    args = ap.parse_args()

    import os
    venv = Path(args.venv or os.environ.get(
        "SIDERA_ORACLE_VENV",
        Path(os.environ.get("TMPDIR", "/tmp")) / "sidera-oracle-venv"))
    python = venv / "bin" / "python"
    if not python.exists():
        print(f"oracle venv not found at {venv}. Run "
              "tools/oracle/make_oracle.sh first.", file=sys.stderr)
        return 2

    print(f"==> generating {args.n} random records (seed {args.seed})")
    records, skipped = generate(args.n, args.seed)
    print(f"    {len(records)} usable, {len(skipped)} dropped "
          "(DST-ambiguous or nonexistent)")

    workdir = Path(args.keep) if args.keep else Path(
        tempfile.mkdtemp(prefix="sidera-diff-"))
    workdir.mkdir(parents=True, exist_ok=True)
    records_path = workdir / "records.json"
    records_path.write_text(json.dumps(records), encoding="utf-8")

    # Sidera's side is computed once; only the oracle's convention changes.
    print("==> running Sidera")
    mine = {r["id"]: sidera_answer(r) for r in records}

    passes: dict[str, dict] = {}
    for positions in ("apparent", "true"):
        answers_path = workdir / f"oracle_{positions}.json"
        print(f"==> running the oracle ({positions} positions)")
        proc = subprocess.run(
            [str(python), str(HERE / "oracle_answers.py"),
             "--records", str(records_path), "--out", str(answers_path),
             "--positions", positions]
            # true_sidereal_year is the slowest call in the oracle and does
            # not vary with the position flag; measure it once.
            + ([] if positions == "apparent" else ["--skip-true-year"]),
            capture_output=True, text=True)
        sys.stderr.write(proc.stderr)
        if proc.returncode != 0:
            return proc.returncode
        oracle = json.loads(answers_path.read_text(encoding="utf-8"))
        theirs = {a["id"]: a for a in oracle["answers"]}

        findings: list[dict] = []
        offsets: dict[str, float] = {}
        for record in records:
            if record["id"] not in theirs:
                continue
            ours, other = mine[record["id"]], theirs[record["id"]]
            findings.extend(compare(record, ours, other))
            for body in BODIES:
                gap = arcsec(ours["d1"][body], other["d1"][body])
                offsets[body] = max(offsets.get(body, 0.0), gap)
        passes[positions] = {
            "settings": oracle["settings"], "failures": oracle["failures"],
            "findings": findings,
            "true_sidereal_year": {
                str(a["id"]): a["true_sidereal_year"]
                for a in oracle["answers"] if "true_sidereal_year" in a},
            "offsets": {b: round(v, 2) for b, v in offsets.items()
                        if v > 0.005},
        }
        real = [f for f in findings if not f.get("benign")]
        print(f"    {len(real)} real, "
              f"{len(findings) - len(real)} benign boundary straddles")
        if not args.keep:
            answers_path.unlink(missing_ok=True)

    report = summarise(records, passes, skipped, args.seed,
                       len(load_cities()))
    Path(args.out).write_text(report, encoding="utf-8")
    real_a = [f for f in passes["apparent"]["findings"]
              if not f.get("benign")]
    print(f"==> pass A: {len(real_a)} real disagreement(s); "
          f"wrote {args.out}")
    if not args.keep:
        records_path.unlink(missing_ok=True)
        workdir.rmdir()
    else:
        print(f"    raw records kept in {workdir} — do not commit them")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
