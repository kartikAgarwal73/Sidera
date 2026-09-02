# Vedic Astrology App — Master Plan

> "The astrology app that makes you need it less."

**Stack:** Python/Flask · pyswisseph for ALL calculations · Sidereal, Lahiri ayanamsa
(`swe.set_sid_mode(swe.SIDM_LAHIRI)`) · Whole Sign houses from Lagna · timezone-aware inputs.

**Modules (final layout):** `engine.py`, `dashas.py`, `vargas.py`, `yogas.py`,
`transits.py`, `explain.py`, `app.py`, plus `requirements.txt` and `test_gates.py`
(automated tests running all phase gates).

**Process rules:**
- Execute one phase at a time. After each phase: run all gates, update `PROGRESS.md`,
  commit, then HALT for manual verification before starting the next phase.
- Never approximate ephemeris values manually — pyswisseph only.
- No stubbing of future-phase modules.

**Reference gate birth data:** originally the commissioner's own birth
record, supplied and independently verified by him. **Removed from this
repository on 2026-08-26**; the committed reference is now a fictional
chart in `fixtures.py`. Supply a real record at run time with
`SIDERA_FIXTURES=/path/to/fixtures.json`.

---

## Phase 1 — Core engine (`engine.py`) ← CURRENT
- Timezone-aware birth input (local date/time + tz + lat/long) → UTC → Julian Day.
- Sidereal Lagna (sign + degree) via `swe.houses_ex(..., b'W', FLG_SIDEREAL)`.
- Sidereal longitudes for Sun–Saturn, Rahu (mean node), Ketu (Rahu + 180°),
  each with sign, degree-in-sign, retrograde flag (speed < 0).
- Whole Sign house mapping from Lagna sign.
- Deliverables: `engine.py`, `requirements.txt`, `test_gates.py`, `PROGRESS.md`.

**GATE:** reference birth → Lagna plus all nine grahas, each with sign,
degree-in-sign and retrograde flag, to a 1° tolerance.
**[Expected values redacted 2026-08-26 — derived from a real birth record.]**
The equivalent gate now runs against the fictional fixture, cross-checked
against a second ephemeris in `TestIndependentEphemerisCrossCheck`.

## Phase 2 — Nakshatras & Vimshottari (`dashas.py`)
- Nakshatra + pada for every planet (27 × 13°20′; pada = 3°20′).
- Lords: Ketu, Venus, Sun, Moon, Mars, Rahu, Jupiter, Saturn, Mercury
  (years 7, 20, 6, 10, 7, 18, 16, 19, 17; total 120).
- Full Mahadasha timeline from Moon nakshatra with birth balance; nested Antardashas;
  lookup of current MD/AD for any date.

**GATE:** Moon nakshatra and pada; the first three mahādaśā transitions; one
antardaśā anchor. **[Expected values redacted 2026-08-26 — derived from a real
birth record.]** Note for the record: the originally stated MD dates were
~5 months adrift of the computed ones, and the gate's own antardaśā anchor
agreed with the computation, not the stated dates — see PROGRESS.md.

## Phase 3 — Divisional charts (`vargas.py`)
- D9 (Navamsa) and D10 (Dasamsa), standard Parashari rules.
- Planet → divisional sign + house from divisional lagna. Vargottama detection.

**GATE:** D9 lagna; the Moon's D9 sign with its Vargottama flag; Mars's D9
sign; D10 lagna. **[Expected values redacted 2026-08-26 — derived from a real
birth record.]**

## Phase 4 — Transits & aspects (`transits.py`)
- Current transits mapped to natal houses.
- Graha drishti: all planets 7th; Mars 4/8; Jupiter 5/9; Saturn 3/10; nodes 5/9.
- Natal aspect table; transit-to-natal contacts (conjunction within 3°, sign-level aspects).

## Phase 5 — Yoga detection (`yogas.py`)
- Full house-lordship mapping for all 12 lagnas.
- Pancha Mahapurusha (own/exalted sign in Kendra), Gaja Kesari, Budhaditya,
  Dhana yogas (1/2/5/9/11 lord combinations), Viparita Raja (6/8/12 lords in 6/8/12),
  Neecha Bhanga (standard conditions), Kemadruma (with exceptions).

## Phase 6 — Flask UI (`app.py`) ← v1 SHIPS HERE
- Single page: birth form → dashboard. North-Indian SVG chart; tabs D1/D9/D10;
  dasha timeline; transits; yogas; nakshatra table. Dark theme, minimal.

## Phase 7 — Explanation Engine (`explain.py`)
- Every output expandable in 3 layers: (1) fact, (2) mechanism with counting shown,
  (3) classical meaning + mandatory confidence tag (High / Moderate / Interpretive).

## Phase 8 — Show-Your-Working visuals
- Tap planet → highlight its aspects (arcs, animated house counting),
  nakshatra-lord wiring lines, dignities.
- "Why?" button per yoga → highlights forming planets + rule verbatim.

## Phase 9 — Life Timeline
- Visual dasha life-graph; past periods themed; user self-verification ratings stored;
  "You are HERE" marker; upcoming dated transit markers.

## Phase 10 — Anti-anxiety design
- No fear language. Doshas always shown WITH auto-run cancellation checks.
- Difficult transits always show end date + progress bar.
- "Weather, not Verdict" framing module; myth-buster auto-generation for feared
  placements with classical citations.

## Phase 11 — Learn-as-you-go
- Contextual 60-second micro-lesson cards.
- 20-card literacy path from "what is a lagna" to "read your own D9".
