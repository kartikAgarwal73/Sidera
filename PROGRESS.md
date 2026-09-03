# PROGRESS

## Varga positions in the ledger; Ashtakavarga roadmap ✅ (2026-09-03)

**Inventory that prompted this.** Sidera computes exactly two divisional
charts, D9 and D10, **sign-level only** — `vargas.py` maps a natal longitude
to a divisional sign and discards the position within it, so there is no
varga degree, no varga nakshatra and no dignity-by-degree. Absent entirely:
Ashtakavarga (BAV/SAV), arudha padas, Upapada, Bhrigu Bindu, avasthas,
shadbala, vimsopaka.

**Milestone 1 of 3, delivered here.** The app computed and rendered per-planet
D9/D10 placements all along while the ledger carried only the two lagnas and
the vargottama list — so the agent had to decline D9 questions it held the
answers to. The ledger now carries `varga.d9.<planet>` and
`varga.d10.<planet>` for all nine grahas: 21 varga facts, ledger 63 → 81,
payload 25 KB → 33 KB.

**A hazard caught before it shipped.** Adding those facts without touching the
validator would have re-run the transit bug in a new coat: Venus is in Cancer
at birth and Virgo in the D9, so a *true* D9 sentence would have been withheld
as a wrong natal placement. Verified that it did exactly that, then gave the
validator four frames — natal, transit, d9, d10 — plus a `varga` frame for
"in the divisional chart" without saying which, which passes if either varga
supports it. Saying "in the D9" cannot launder an invented placement: it is
still checked, against the D9.

Five `rule.varga.*` entries added so the facts can be interpreted rather than
only recited, including `rule.varga.sign_level`, which states the build's own
limit so the agent does not reach for a varga degree that does not exist.

248 passing.

### Milestone 2 — Ashtakavarga (BAV + SAV). QUEUED, blocked on the UX restructure.

Agreed scope: raw BAV and SAV, **reductions deferred** (trikona and
ekadhipatya shodhana, Sodhya Pinda — where implementations genuinely
diverge). Verdict-first dashboard domain: strongest and weakest houses named
up front, the 12×8 grid folded under. Ledger design agreed as `sav.house.N`
×12 plus `bav.<planet>` ×7 carrying 12-value arrays — 19 facts rather than
the 96 that `bav.<planet>.house.N` would need, which would have tripled the
prompt payload and buried the useful facts.

⚠ **VERIFICATION CONSTRAINT — read before starting.** The gate is meant to be
the classical checksum: each planet's BAV total (Sun 48, Moon 49, Mars 39,
Mercury 54, Jupiter 56, Venus 52, Saturn 39) and their sum, 337. Those
figures are currently **recalled, not verified** — they came from the
commissioner and from model training data, and this environment cannot reach
a source to check them (wisdomlib and archive.org both refused egress,
HTTP 000, on 2026-09-03).

Under this build's own provenance rules a recalled number cannot be an
`external` gate. So either:
  (a) verify the 56-row benefic-point table and the totals against a BPHS
      text off-machine, and gate on them as `external`; or
  (b) implement, compute the totals, and declare them `characterization`
      until someone checks them — labelled honestly, not promoted.
Option (a) is much better: the checksum is exactly the kind of anchor this
suite is short of, and it catches transcription errors in the 56-row table
that are otherwise silent and produce plausible-looking bindus.

Estimated 1.5–2 days: ~250-line module, ~12 tests, a dashboard domain, the
ledger entries. The compute is easy; the table transcription is the risk.

### Milestone 3 — QUEUED

Degree-level vargas; D2, D7, D12, D16, D30, D60; arudha padas and Upapada.
Degree-level means extending `VargaPosition` with a divisional longitude,
which unlocks varga nakshatras and dignity-by-degree and is a prerequisite
for taking any of the finer vargas seriously.

## Personal birth data removed; fictional reference fixture ✅ (2026-08-26)

The commissioner's own birth record is gone from this repository — from
`fixtures.py`, and from every derived value in `PROGRESS.md`, `PLAN.md` and
`ui-design/FRAMEWORK-AUDIT.md`. A full natal chart uniquely determines a birth
moment, so the chart tables were personal data too, not just the birth line.
Redacted entries say so in place rather than being silently deleted.

**The committed fixtures are now fictional.** `reference` is the corrected
Aisha Rao persona from the Sidera Framework (16 Aug 1998, 06:57 IST, Jaipur —
Leo 11°05′, Rohiṇī pada 2); `partner` is a second fictional record so the
aṣṭakūṭa gates pair two *different* charts. Pairing a chart with itself would
have made the tables look symmetric and every kūṭa full — the opposite of what
those tests exist to prove. All 70 chart-specific expectations were recomputed
and rewritten; the suite stands at **196 passed**.

**What this cost, stated plainly.** The Phase 1–5 gate values were external
because a real person supplied them and had verified them independently.
A fictional chart cannot carry that: recomputing its positions with the same
ephemeris and asserting they match is circular. So those declarations were
**downgraded to `characterization`** in `conftest.py` — not relabelled to keep
the counts looking strong. External fell 58 → 46; characterization rose 42 →
80 of 190 (42%), still under the 60% tripwire.

**What was built to recover the anchoring** — two things that need no person:

1. `TestIndependentEphemerisCrossCheck` — every position in the reference
   chart recomputed with **ERFA** (pyerfa, the IAU SOFA-derived library, no
   shared code with swisseph) and asserted to agree within one arcminute.
   Worst disagreement 41.1″, all of it the expected apparent-vs-geometric
   terms; the Moon agrees to 1.8″, which fixes Rohiṇī pada 2 sixty times over
   and therefore the whole Vimśottarī timeline. Reproduce with
   `python tools/erfa_cross_check.py`. A second ephemeris is a real outside
   source in a way our own never is.
2. `TestAstronomicalAnchors` — published, person-free facts: Spica at 180°
   sidereal (the *definition* of the Lahiri ayanāṃśa), the ayanāṃśa's standard
   epoch value 23°51.4′, and the 2024-04-08 total solar eclipse (Sun–Moon
   2.29′, Sun–Rāhu under 5°, both in sidereal Pisces — an assertion that alone
   would catch a lost sid-mode).

**Two real defects the new fixture exposed**, both fixed rather than papered
over:

- **Kaal Sarpa had no myth-buster card.** The fictional chart genuinely forms
  it — all seven grahas inside the Ketu→Rāhu arc — and it is the most
  fear-marketed pattern in popular jyotiṣa, exactly what Phase 10 exists for.
  Added, and it says the honest thing: the pattern is *absent* from BPHS,
  Phaladeepika and Saravali. `detect_kaal_sarpa` now also shows the margins,
  since one graha crossing the axis dissolves the whole thing.
- **`ask.py` rendered "Rahu rules houses  and stands in the 1st".** The nodes
  rule no sign, so the lordship list came out empty. Now says so explicitly.

Also: `_agreement_label` extracted in `ask.py` so the low-convergence branch
stays testable — the reference chart never reaches it, and a branch no
committed chart exercises will rot unnoticed.

## Deployable state — production readiness, safety scan, public repo ✅ (2026-08-22)

Milestone 04 accepted as-is (single-form cast; Dexie persistence and the
unknown-time fallback deferred deliberately).

**1 · Production readiness.** `gunicorn==23.0.0` pinned; `Procfile` runs
`gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 120`;
`app.py` reads `PORT`/`HOST` from the environment and its `__main__` block is
development-only, so no deploy path can enable the debugger (asserted).
Verified by actually serving under gunicorn: GET and POST both 200, chart
renders, no debugger leak.

**Ephemeris finding.** The app was never using Swiss `.se1` files — swisseph
silently falls back to its built-in Moshier ephemeris because none are
present. Good for Render (nothing to mount) and accurate to well under an
arcsecond, but it was invisible. Now surfaced by
`engine.ephemeris_backend()`, pinned by a test, and `SE_EPHE_PATH` resolves
relative to the module rather than the working directory.

**2 · Safety scan.** Full history and working tree: no API keys, tokens or
private keys; no absolute local paths (`/Users/...` never entered this repo);
no env or cache files tracked. `.gitignore` extended to env files, venvs,
caches, OS cruft and `.se1` binaries. **Personal birth data parameterised** —
the verification charts moved to `fixtures.py`, zero occurrences left in
`test_gates.py`, overridable by `SIDERA_FIXTURES`, with anchored gates
skipping (not failing) when substituted: 6 passed, 156 skipped under an
alternate fixture. Also fixed a latent fragility found on the way: tests read
files relative to the module now, not the working directory.

**3 · Repo.** README written for a public reader — what it is in two lines,
the accuracy thesis, the external/invariant/characterization test
distinction, stack, local run, layout, credits. **The rename to `sidera` is
yours to do** — no admin-scoped tool exists here, and the repo root still
holds unrelated real-estate files, so DEPLOY.md step 0 gives both routes (new
clean repo vs rename + Root Directory).

**4 · Landing copy.** Above the fold: what Sidera is, "Every reading shows
its computation", one CTA. Footer: built-by link to LinkedIn plus a Feedback
placeholder to swap for the Google Form.

**5 · Audit hygiene.** `DEPLOY.md` added with exact Render settings; audit
gains a deployment-posture section and marks milestone 04 accepted; counts
regenerated — **58 external · 64 invariant · 42 characterization**.

`pytest` → **170 passed**.


## Milestone 06 — the reading engine ✅ (2026-08-22)

`reading/` mirrors the framework's own split — `detect.py` · `select.py` ·
`compose.py` · `fragments.py` — so a later port is a translation.

**Pipeline** exactly as specified: DETECT runs every condition predicate over
chart + pañcāṅga + gocara; RANK sorts by weight, keeps subject and qualifier,
ties breaking by natural graha order; SELECT draws one variant per slot by
seeded hash; COMPOSE assembles stem + emphasis + close with the emphasis span
returned separately for the accent tint. The weight table is reproduced to the
number (100 daśā turn · 90 sāḍhe sātī phase · 80 station · 70 slow ingress ·
60 transit over natal · 40 candra gocara · 25 tithi/yoga · 10 weekday lord),
and the pañcāṅga floor always yields.

**Two refinements to the seed formula, both documented rather than silent:**
the slot name is folded into the seed (the framework's own "27 phrasings per
condition" is 3×3×3 and only holds if slots are drawn independently), and the
hash is SHA-256 rather than Python's `hash()`, which is salted per process and
would change the reading on every restart.

**Voice rule enforced, not assumed.** Fourteen fragments, three variants per
slot. A test walks a full year: statements under 15 words and long readings
within 25–40 on every sampled day (the first draft failed both — 61 of 120
days over-long — and the library was tightened until it held). A banned-term
test enforces "no second-person predictions about money, health or death".

**The hygiene system earned its keep the same session it was built.** It
caught all 12 new tests as undeclared and refused to pass until each declared
its provenance. One older test then went red —
`test_design_handoff_glance_pattern`, declared *characterization*, asserting
the retired MD/AD template statement. Under the rule established this morning
a characterization test may be re-baselined and the commit must say so: it was
re-baselined to assert the design's actual requirement (a one-statement hero
with a tinted span) rather than the superseded copy.

`pytest` → **162 passed** (156 gates + 6 hygiene). Chromium-verified.


## Memory hygiene — three fixes before milestone 06 ✅ (2026-08-22)

A detour taken deliberately: after eight months of sessions, the suite could
say "still green" but not "still right". Three fixes, all self-enforcing.

**1 · Test provenance is declared and enforced.** `conftest.py` registers every
test as `external` (anchored to a source outside this build — commissioner's
gate values, classical rules, checkable astronomy, the design/framework docs),
`invariant` (true by definition, mathematics, or an explicit product rule), or
`characterization` (froze observed output). The rule a future session needs:
**a red external/invariant test means the code is wrong — do not edit the
expectation; a red characterization test may be re-baselined, and the commit
must say so.** Current ratio, generated not asserted: **53 external · 51
invariant · 40 characterization (28%)**.

**2 · The audit's numbers are generated.** `tools/refresh_audit_counts.py`
writes the counts block; `test_hygiene.py` fails when it drifts. This closed a
live instance of the failure mode — the audit claimed "125 tests" while the
suite stood at 144.

**3 · Dependencies pinned.** `requirements.txt` now pins exact versions, with
a test that fails on any loosened pin. This build has already had an
environment collapse (a system package install wiped site-packages) read as a
code regression.

`test_hygiene.py` also fails on undeclared tests, on registry entries naming
tests that no longer exist, and when characterization tests exceed 60% of the
suite — a tripwire, not a target. **Each guard was verified to actually fail
when violated**, then restored. The audit gains a "what actually protects this
build" section listing the six failure modes this build has really suffered,
with the evidence and the catch for each — including the residual risk nothing
automated can cover: a mis-declared provenance.

`pytest` → **150 passed** (144 gates + 6 hygiene).


## Path B · milestone 05 — Guṇa Milan + framework fixture defect ✅ (2026-08-22)

Commissioner chose **path B**: keep Flask for the public v1, keep building the
stack-independent domain layer so a later port is a translation. Continuing in
the framework's own build order, which places Match (05) before the reading
engine (06).

**`gunamilan.py`** — the last missing domain contract. Eight kūṭas over 36
points, each carrying score, classical rule verbatim, computed working,
confidence tag, and the classical easing whenever a kūṭa is withheld. Maṅgala
doṣa from both charts with mutual cancellation; verdict against the 18-point
threshold. Where authorities genuinely differ (finer yoni tiers, some vaśya
cells) the attested extremes are implemented and the rest defaults to neutral,
stated in the rule text at Moderate confidence — no invented cells.

**Match screen (design 2d)** — optional partner block with its own city
autocomplete; ghost "36", ✕ names, 104px ring in vulgar fractions (`24½/36`),
italic verdict, eight expandable kūṭa rows, Maṅgala footnote. Glance's third
chip becomes **Match** when a partner exists (design 5a). Note the aṣṭakūṭa
tables are asymmetric — the same pair scores 24½ one way and 22½ the other,
which is computation, not display.

**⚠ Defect found in the framework's own TESTING RULE.** Its named fixture
("Aisha Rao, 14 Aug 1998, 04:32, Jaipur — Siṃha lagna, Candra in Rohiṇī pada
2, Śani mahādaśā") does not compute: that birth data gives **Cancer lagna and
a Bharaṇī Moon**. Corrected to **16 Aug 1998, 06:57 IST**, the first two
claims reproduce to the arc-minute (Leo 11°05′ vs the stated 11°04′; Rohiṇī
pada 2). The third is unreachable by *any* birth data — a Rohiṇī Moon forces
Moon → Mars → Rāhu → Jupiter, so Rāhu (2011–2029) runs now, never Śani. Both
the corrected fixture and a test pinning the discrepancy are in the suite.

Audit milestones now: 01 ✅ · 02 ✅ **complete** · 03 ✅ · 05 ✅ · 04/06/07 ⚠️.
`test_gates.py` → **144 passed**; Chromium-verified end to end.


## Build framework received + first conformance pass ✅ (2026-08-22)

`Sidera Framework.pdf` imported to `ui-design/` with a full conformance audit
(`ui-design/FRAMEWORK-AUDIT.md`) mapping all seven sections against this build.

**Headline: the framework specifies a different stack** (React + Vite +
swisseph-WASM PWA) than the one commissioned (Python/Flask + pyswisseph).
Documented as a decision, not silently actioned — audit ends with two costed
paths and a recommendation.

**Conformance delivered this pass (all stack-independent):**
- **`pancanga.py`** — the missing domain contract from THREE · DOMAIN MODEL.
  Tithi (30 + pakṣa), nakṣatra, yoga (27), karaṇa (60, fixed/movable naming
  rule), sunrise/sunset at the birth place, weekday + lord, `endsAt` for every
  limb by bisection. Verified against the 29 Jun 2026 Pūrṇimā, the 13 Jul
  Amāvāsyā and Jaipur sunrise/sunset to the minute (05:42 / 19:23 IST).
- **Six-palette token system** per SIX · TOKENS — pastel/gold/sindoor/
  twilight/rose/verdigris on `:root[data-palette]`, header picker, persisted;
  components carry no conditional colour.
- **Non-negotiables enforced** — square corners restored (three 9px pills
  squared; only the 50% score ring remains), and a test now fails the build on
  any stray radius, shadow or gradient.
- **Pañcāṅga surfaced** — Glance kicker reads the real tithi; design 1c's
  four-cell strip renders beneath the statement.

Audit status by milestone: 01 ✅ · 02 ✅ except guṇa milan · 03 ✅ · 04–07 ⚠️.
`test_gates.py` → **125 passed**; Chromium-verified across four palettes.


## "Ask Your Chart" — question-to-evidence engine, framework + 5 samples ✅ (2026-07-16)

**Delivered:** `ask.py`. Question registry — each entry declares text,
category, required techniques, per-lens classical rule (verbatim), and a
stored confidence weighting per lens (weights sum to 1, test-enforced).
`ask()` computes required facts from the existing modules (lordships, vargas,
dignity engine, dasha windows, Jupiter ingress spans — shared per-chart
`ChartContext` cache), applies the stored rules, and returns a Verdict with
all five required outputs: (1) plain-language answer (template-composed —
**no free-text generation**; determinism test-proven), (2) each contributing
placement with its computed value, (3) the rule invoked per lens, (4) a
weighted convergence score (modal-indication share of total lens weight) with
agreement label, (5) an overall confidence tag (weakest lens, downgraded when
convergence < 75%). **Core principle enforced: disagreement is displayed,
never resolved** — dissenting lenses are listed with their own indications
("shown side by side, unresolved"), and the answer says "not averaged away".

**The 5 samples on the reference chart:** spouse-profession → *lenses
disagree, 40%* (Mercury-domains vs D9-Jupiter vs Venus-karaka — the principle
demonstrated); career-field → *100% strong convergence* (triple-Mercury:
10th lord exalted in 10th + occupant + D10 lagna lord); wealth-timing →
dated windows, running Mercury–Venus Feb 2026–Dec 2028 + Jupiter to the
2nd/11th, 100% overlap; marriage-timing → Mercury–Venus period + Jupiter
from Libra aspecting the 7th, converging on 2028–2030; current-dasha →
65% partial, Venus-antara divergence shown. UI: "Ask" nav section, 5
summary-first cards with convergence pills (solid=strong, dashed
italic=disagree), lens blocks with weight + rule disclosures.
`test_gates.py` → **114 passed**; Chromium-verified. Framework awaits
structural review before the full registry is built out.

## Design handoff implemented — Pastel palette + glance pattern ✅ (2026-07-16)

Uploaded handoff bundle imported to `ui-design/` (updated `Astrology
App.dc.html` + `DESIGN-HANDOFF.md`). Per the handoff's chosen direction:
- **Pastel palette** (default) applied app-wide on the dark Colophon ground:
  ink #585270, accent #a99bc9, accent-300 #cfc4e4, accent-400 #bcafd7,
  ghost rgba(207,196,228,.16); favicon re-inked; every gold token removed
  (test-enforced).
- **Home "concise, expand-on-selection" pattern (4b dark twin of 5a)** built
  as the dashboard's Glance block: kicker (today's date + transit-Moon
  nakshatra, computed), one-statement hero composed from live data ("A
  Mercury season, Venus antara — relationship, comfort, art and increase."),
  ☾ ghost glyph, italic "Read the working" link → Paṭha, three chips
  (exclusive, instant swap, 196px min-height panel per spec): **Chart**
  (140px mini-kundli + identity caption) / **Transits** (four dated ingress
  rows, first in accent) / **Daśā** (76px progress ring — 22% — + current
  MD·AD + end date). *Adaptation note:* the design's third chip is Match
  (Guna Milan), which is outside the delivered 11-phase scope — substituted
  with the Daśā panel until a Match module exists.
`test_gates.py` → **105 passed**; Chromium-verified (chip swap + ring).

## UI/UX + content revision — commissioner's walkthrough (items A–F) ✅ (2026-07-15)

**A. Navigation:** sticky section nav (Glance/Chart/Daśās/Timeline/Transits/
Doshas/Myths/Yogas/Paṭha/Grahas/Learn) with scrollspy active-highlight;
progressive disclosure — antardashas, gocara positions table, dosha cards and
myth cards all summary-first expanders; hierarchy pass (section rules,
whitespace).
**B. Transit interpretation from computed facts:** the fallback line is gone.
`dignity_at()`/`dignity_grade_at()` now work on any position, so every
slow-mover note composes (i) transit dignity — Jupiter in Cancer renders
"exalted (past the deep exaltation degree at 5°, easing) … its strongest
terrain"; (ii) natal house + one-line meaning; (iii) Moon-relative gocara
quality (favourability tables); (iv) ≤3° conjunctions with natal planets —
**transit Ketu 0.04° from natal Venus surfaces as a gold "exact contact"
line with its Dec 2026 end date**. Confidence chip per card. Tests pin the
exalted-Jupiter line and the Ketu-on-Venus contact.
**C.** Ketu has its own slow-mover row (Leo, natal 9th, progress bar, ends
Dec 2026) — both nodes render.
**D.** Ordinal suffixes app-wide (Jinja filter + server text): "3th/2th"
class of bugs eliminated, regression-tested (11th/12th/13th unaffected).
**E.** Timeline diamond labels de-collided: three staggered rows with
min-gap spacing and leader lines when a label slides off its marker.
**F.** Favicon (kundli-plate SVG) served at /favicon.ico +
apple-touch-icon routes — log 404s gone; graphs and graha table scroll
horizontally on narrow screens. `test_gates.py` → **103 passed**;
Chromium-verified.

## Dignity revision — classical BPHS segmentation restored ✅ (2026-07-14)

Reverted the earlier project convention on user instruction. `yogas.py` now
reads Virgo for Mercury as BPHS does: **0°–15° exaltation zone (deep
exaltation at 15°), 16°–20° moolatrikona, remainder own sign**; Moon in
Taurus similarly (0°–3° exaltation, then moolatrikona). Moolatrikona is now
modelled for all seven planets as a first-class dignity state (standard
spans: Sun Leo 0–20, Moon Taurus 3–30, Mars Aries 0–12, Mercury Virgo 16–20,
Jupiter Sag 0–10, Venus Libra 0–15, Saturn Aquarius 0–20). **Reference chart
now reports Mercury (0°56′ Virgo) as `exalted`** — confirmed in the engine,
Bhadra Yoga detail, graha table, explorer card and Paṭha layer.

New graded field `dignity_grade()` feeds the Phase 7 explanation layer:
"exalted (early degree, rising toward deep exaltation at 15°)" /
"(at the deep exaltation degree)" / "(past …, easing)", the mirrored
deep-fall phrasing for debilitation (Mars: "approaching deep fall at 28°"),
and moolatrikona spans. Gate suite re-run: **96 passed**.

**ALL 11 PHASES COMPLETE** (2026-07-13) — `pytest test_gates.py` → **95 passed**;
final Chromium end-to-end: autocomplete birth entry (12-hour time) → full
dashboard → lesson modal → literacy-path progress, all green.

## Phase 11 — Learn-as-you-go ✅ (2026-07-13)

**Delivered:** `lessons.py` — a **20-card literacy path** ordered from
"What is a lagna?" (card 1) to "Read your own D9" (card 20), each body sized
for a ~60-second read (word-count enforced by test: 40–170 words) and
fear-language-linted. **Contextual micro-lesson chips** (ⓘ 60s) sit beside
the lagna line, plate, dasha ledger, life timeline, weather, doshas, yogas
and graha table, each opening the relevant card in a modal
(`CONTEXT_LESSONS` index, resolution tested). The **"Learn the sky" section**
renders the full numbered path with read-state tracked in localStorage and a
read-progress counter (n/20). Modal-hidden CSS bug found and fixed during
E2E (display:grid was defeating the `hidden` attribute).
`test_gates.py` → **95 passed**.

## Phase 10 — Anti-anxiety design ✅ (2026-07-13)

**Delivered:** `doshas.py`. **Doshas never shown bare** — cancellation checks
auto-run and render beside every card: Mangal (sign-exception verse, dignity,
Jupiter/Moon influence — reference chart: formed by Mars-in-8th, cancelled by
the Cancer-in-8th exception, all 4 checks listed), Kaal Sarpa (hemicycle test
— absent, breaking planets named), Sade Sati (phase-aware, transit-computed:
inactive for the reference chart, **next window dated Aug 2029**; when active
it carries start/end/progress). **Slow-mover weather cards always show entry
date, end date and a progress bar** — demanding stretches (4/8/12 from Moon,
sade-sati houses) get a calm dated note, never a warning. **"Weather, not
Verdict" framing module** heads the transit area. **Myth-buster
auto-generation** for feared placements actually present (Mangal pattern,
debilitated Mars, Mars-in-8th, Sade Sati) — each with myth / classical record
/ text-level citation / confidence tag. **Fear-language lint test** scans the
rendered dashboard plus doshas.py and explain.py for a banned vocabulary
(doom, fatal, ruin, …) — zero hits enforced forever. `test_gates.py` →
**90 passed**.

## Phase 9 — Life Timeline ✅ (2026-07-13)

**Delivered:** `transits.py` gains an ephemeris-driven ingress engine
(`next_sign_ingress`, `sign_entry_before`, `upcoming_ingresses`: coarse scan +
bisection to <1h; handles retrograde re-entries — validated against real
events: Saturn→Pisces 29 Mar 2025, Saturn→Aries Jun 2027, Rahu→Capricorn Dec
2026). Dashboard gains the **life-graph**: 120-year Vimshottari band SVG
(past bands muted, current band lit with lord initials), age ticks,
**"You are HERE"** dashed marker with age, and a separate 3-year
**upcoming-gocara strip** of dated diamond markers (each slow mover's next
sign entries with the natal house it begins to occupy). **Past periods
themed** from the dasha-theme vocabulary, and **self-verification ratings**:
1–5 stars per finished/running mahadasha, stored in localStorage keyed by
birth data (browser-only, no accounts), persistence Chromium-verified.
`test_gates.py` → **83 passed**.

## Phase 8 — Show-Your-Working visuals ✅ (2026-07-13)

**Delivered:** tap-to-explore chart. Graha chips under the plate; tapping one
(D1) highlights its house, then **animates the inclusive house count** step by
step (intermediate houses flash with their running number; aspected houses
stay lit with the offset badge — 3rd/7th/10th), draws an animated dashed
**nakshatra-lord wiring line** from the planet to its star-lord's house
(self-star noted in text), and opens an info card with dignity, nakshatra and
the full drishti list including which natal planets are struck. **"Why?"
button on every yoga card** opens the rule verbatim, switches to D1, floods
the forming houses and pulses rings on the forming planets. Payload built
server-side (`planet_explorer()`), house polygons/centroids for the
North-Indian plate defined once in the template. Chromium-verified (Saturn:
source + 3 targets highlighted, card lists Sun/Mercury/Rahu 7th + Jupiter
10th; Gaja Kesari Why → 2 pulse rings). `test_gates.py` → **79 passed**.

## Chart rendering feedback ✅ (2026-07-13)

1. **Responsive chart size:** kundli SVG now `min(78vw, 900px)`, breaking out
   of the reading column, square aspect preserved. Chromium-measured: 900px
   at a 1400px viewport, 304px at 390px (mobile) — proportional.
2. **Degrees on the plate:** each planet shows degree-within-sign next to its
   abbreviation ('Ju 15°33′', retrograde as 'Sa 9°29′ R'; minutes truncated,
   almanac-style), lagna as 'As 18°38′', one line per planet. "Show degrees"
   checkbox (default on) toggles back to compact abbreviations. Degrees apply
   to D1 only — varga positions are sign-level, so D9/D10 stay compact.
   Corner-house label anchors clamp inward so degree text never clips the
   plate border. Re-verified in Chromium (desktop + mobile + toggle);
   suite: **75 passed**, all gates green.

## Phase 6 REVISION — Universal blank-canvas UI + input fixes ✅ (2026-07-12)

1. **No user-specific defaults.** Form loads completely blank (E2E-asserted
   field by field); all reference-chart placeholders removed. A regression
   test proves no fixture's place, year, time or coordinates ever appear in
   the form HTML — the reference chart exists only inside the test suite.
2. **Time input.** Text field labelled "24-hour or AM/PM"; `parse_time()`
   accepts '14:20', '2:20 PM', '12:05 am', '08.45'; rejects impossible times
   with friendly inline errors ("In 24-hour time the hour runs 0–23"), form
   values preserved on error. 12h and 24h inputs proven to cast identical
   charts.
3. **Optional Name + Profile model.** `Profile(name, birth)` dataclass (ready
   for multiple saved profiles; no accounts). Dashboard header: "Chart of
   [Name]" + "15 March 1990, 08:45 · Mumbai…", anonymous fallback "Janma
   kundli".
4. **Birthplace autocomplete, fully offline.** `data/cities.json` (32,444
   cities) built by `data/build_cities.py` from geonamescache (GeoNames
   cities15000: name/lat/lon/IANA tz/population, CC BY 4.0) joined with
   dr5hn states.json for region names (FIPS-first join; ISO fallback —
   fixes JP-40 Fukuoka/Tokyo collision). `/api/cities` serves type-ahead at
   3+ chars ("City, Region, Country", population-ranked, diacritic-folded so
   'sao paulo' finds São Paulo); selection auto-fills lat/lon/**IANA
   timezone — never guessed from server/browser**; missing tz is a hard
   validation error. Manual lat/long/tz entry kept as the unlisted-location
   fallback. Attribution in the footer. (GeoNames' own download host is
   blocked by the sandbox network policy; the PyPI geonamescache bundle is
   the same dataset and keeps the build offline-reproducible.)
5. **Re-verified end-to-end in Chromium:** blank form asserted → non-reference
   chart (Asha, 15 Mar 1990, 8:45 AM, Mumbai via autocomplete → Asia/Kolkata
   auto-filled) → full dashboard renders (Aries lagna 6°32′, Moon Swati p.2)
   → full suite re-run: **74 passed**, all reference-chart gates green.

## Phase 7 — Explanation Engine ✅ (2026-07-12) — awaiting manual verification

**Delivered:** `explain.py` — three-layer `Explanation` (fact / mechanism with
counting shown / classical meaning) with a **mandatory, validated confidence
tag** (High · Moderate · Interpretive; constructor raises on anything else).
Documented policy: High = stated outcome of the classical rule itself;
Moderate = widely-agreed classical attribution (nakshatra qualities, dasha
themes, named-yoga fruits); Interpretive = composed synthesis (planet-in-house
blends, transit weather). Explainers for Lagna, every graha (incl. dignity
derivation showing the 15° deep-exaltation working and retrograde speed),
every nakshatra placement (÷13°20′ and ÷3°20′ arithmetic + mod-9 lord),
current dasha (balance % arithmetic + fixed lord order + AD proportionality),
gocara (whole-sign counting example + drishti table), and every yoga (rule
verbatim + working + counting chain for Gaja Kesari; friction/cancellation
propagated). Counting is shown step by step ("Leo 1 · Virgo 2 ·
… · Virgo 10").

**UI:** yoga cards upgraded to full three-layer disclosure; new **Paṭha —
your chart, explained** section: 22 expandable entries (Lagna ×2, 9 grahas
×2, Daśā now, Gocara) each with Fact/Mechanism/Meaning and a confidence chip
(gold = High, cream = Moderate, italic = Interpretive). Verified in Chromium.
`test_gates.py` → **67 passed**.

**Next:** HALTED. Phases 6 & 7 both await your check. Phase 8
(Show-Your-Working visuals) follows.

## Phase 6 — Flask UI ✅ (2026-07-11) — v1 SHIPS HERE — awaiting manual verification

**Delivered:** `app.py` + `templates/index.html` + `static/style.css` —
single-page Flask app implementing the **Colophon** direction (gold palette)
from `ui-design/Astrology App.dc.html`, imported from the user's Claude Design
project via DesignSync. Birth form (underline fields, "Cast the chart →") →
dashboard: North-Indian kundli SVG plate (design geometry verbatim: fixed
houses, sign numbers, anticlockwise) with Rāśi/Navāṃśa/Daśāṃśa tab switcher,
Vimshottari MD+AD ledger with current period highlighted + standing note,
Gocara ledger with transit-to-natal contacts, yoga cards (detail, friction
notes, expandable rule verbatim), graha/nakshatra/dignity table. Ink ground
#211c17, cream #ece5d8, gold hairlines, Cormorant Garamond / Lora.
Verified end-to-end in Chromium (form → dashboard → tab switch) with
screenshots. `test_gates.py` → **59 passed**.

**Phase 5 corrections (user-directed, verified):** `dignity()` now returns
mutually exclusive states; early-degree Virgo Mercury reads **own sign** (exaltation
only from the deep-exaltation degree 15° — project convention; BPHS-style
0–15° zone noted inline as the switchable alternative). Naisargika maitri
table added; the Sun–Saturn lords-of-2-&-9 Dhana yoga now stores a
natural-enmity friction note.

**Next:** HALTED. Phase 7 (Explanation Engine) begins after manual verification.

## Phase 5 — Yoga detection ✅ (2026-07-11) — gate verified manually 2026-07-11
(All nine audit points confirmed; Bhadra acknowledged as new finding.
Corrections applied: distinct dignity states; Dhana enmity tags — see Phase 6
entry.)

**Delivered:** `yogas.py` — full lordship mapping (sign lords, house→lord for
any lagna, dignities: own/exalted/debilitated); detectors for Pancha
Mahapurusha (own/exalted in Kendra), Gaja Kesari (Jupiter in Kendra from
Moon), Budhaditya, Dhana yogas (1/2/5/9/11 lords: conjunction, exchange,
mutual aspect, wealth-lord in wealth house), Viparita Raja
(Harsha/Sarala/Vimala), Neecha Bhanga (4 standard conditions), Kemadruma
(formation + exceptions, reported with cancellation reasons). Every Yoga
carries its classical rule verbatim + chart-specific detail (ready for
Phases 7/8/10). `test_gates.py` → **50 passed**.

**Detection run** (reference chart, all hand-verified): eight yogas fired —
two Pañca Mahāpuruṣa, Gaja Kesari, Budhāditya, two Dhana, a Viparīta Rāja and
a Neecha Bhanga, each with its rule and working. **[Placements redacted
2026-08-26 — they were derived from a real birth record.]** Kemadruma did not
form; its formation and exception logic is exercised via synthetic charts in
the tests instead. The five detectors that correctly stayed silent were
asserted as such, so absence is a verified result rather than an untested
path.

**Aspect-table audit (user-requested):** confirmed Moon→Jupiter 7th was
present in the computed table all along (the chat summary had elided it);
Sun→Saturn/Ketu, Mercury→Saturn/Ketu, Rahu↔Ketu now pinned as explicit test
assertions. Completeness test added at sign/house level (`houses_aspected_by`):
every graha emits ≥1 aspect always. Note: the *planet-to-planet* table
legitimately omits any graha whose aspected signs are empty — asserted
explicitly so the omission is a verified fact, not a bug.

**Next:** HALTED. Phase 6 (Flask UI — v1 ships) begins after manual verification.

## Phase 4 — Transits & aspects ✅ (2026-07-11) — gate verified manually 2026-07-11
(Aspect-table completeness audited on user request; see Phase 5 entry.)

**Delivered:** `transits.py` — graha drishti per spec (all 7th; Mars 4/8;
Jupiter 5/9; Saturn 3/10; nodes 5/9); natal aspect table (sign-level);
drishti-on-house lookup; transit snapshot at any tz-aware datetime mapped to
natal houses (reuses the identical ephemeris path via new
`engine.sidereal_positions`); transit-to-natal contacts — conjunction within
3° orb + sign-level aspects. `test_gates.py` → **38 passed**.

**Verification run** (no numeric gate specified for this phase; values below
are the checkable facts):
- Natal aspect table hand-verified row by row, including the reciprocal rows
  a summary would gloss over.
- Transits at a fixed instant (2026-07-11 12:00 UTC) mapped to natal houses;
  conjunctions and sign-level aspects both checked, orbs to two decimals.
- **[Placements and orbs redacted 2026-08-26 — derived from a real birth
  record.]** The equivalent assertions now run against the fictional
  reference chart in `TestPhase4TransitsAspects`.

**Next:** HALTED. Phase 5 (Yoga detection) begins after manual verification.

## Phase 3 — Divisional charts (D9/D10) ✅ (2026-07-11) — gate verified manually 2026-07-11
(D10 even-sign method confirmed as Parashari 9th-from-sign counting.)

**Delivered:** `vargas.py` — D9 Navamsa (9 × 3°20′; movable from self, fixed from
9th, dual from 5th) and D10 Dasamsa (10 × 3°; odd from self, even from 9th),
standard Parashari. Planet → divisional sign + house from divisional lagna
(Whole Sign). Vargottama flag on D9. `test_gates.py` → **30 passed**.

**Gate run** (reference birth) — all four gate values exact: the D9 lagna, the
Moon's D9 sign with its Vargottama flag, Mars's D9 sign, and the D10 lagna all
matched what the commissioner expected. **[Values redacted 2026-08-26 —
derived from a real birth record.]**

**Next:** HALTED. Phase 4 (Transits & aspects) begins after manual verification.

## Phase 2 — Nakshatras & Vimshottari ✅ (2026-07-11) — gate verified manually 2026-07-11

**Verification note:** the commissioner supplied his authoritative daśā
record, which matched the computed timeline with a constant ~5-day offset
(≈41″ of Moon longitude in the source; ephemeris/rounding). Sequence and
period lengths identical; the dates in the original gate text were the ones
that were wrong. Deviation resolved. **[Dates redacted 2026-08-26 — a daśā
timeline is derived from, and reconstructs, a birth record.]**

**Delivered:** `dashas.py` — nakshatra + pada per point (27 × 13°20′, pada 3°20′),
Vimshottari lords Ketu/Venus/Sun/Moon/Mars/Rahu/Jupiter/Saturn/Mercury
(7/20/6/10/7/18/16/19/17 y = 120), full MD timeline from Moon nakshatra with
birth balance, nested ADs (first AD = MD lord's own, proportional lengths,
exact partition), `timeline.at(date)` → current MD/AD lookup.
`test_gates.py` → **24 passed** (Phase 1 gates still green).

**Gate run** (reference birth): Moon nakshatra, pada and star-lord matched the
gate; the birth balance, the first three mahādaśā transitions and the
antardaśā anchor all reconciled. **[Values redacted 2026-08-26 — they were
derived from a real birth record.]**

**⚠ Gate deviation — needs your call:** the stated MD transitions and the
computed ones differed by ~5 months. The gate's own antardaśā anchor was consistent
only with the *computed* timeline, not the stated one, which is why the
computed dates were kept and flagged rather than fudged toward the gate text.
The commissioner later supplied authoritative transition dates confirming the
computed sequence. **[Specific dates redacted 2026-08-26.]**

**Next:** HALTED. Phase 3 (Divisional charts D9/D10) begins after manual verification.

## Phase 1 — Core engine ✅ (2026-07-11) — gate verified manually 2026-07-11

**Delivered:** `engine.py` (sidereal Lahiri positions via pyswisseph, Lagna via
`swe.houses_ex` Whole Sign, retro flags from longitude speed, Rahu = mean node,
Ketu = Rahu + 180°, Whole Sign house mapping, timezone-aware input supporting
IANA names and fixed offsets), `requirements.txt`, `test_gates.py` (15 tests).

**Gate run** — against the commissioner's own birth record, supplied and
independently verified by him. All ten points landed within 1° of the values
he expected; `pytest test_gates.py` → **15 passed**.

**[Chart table redacted 2026-08-26.]** A full natal chart uniquely determines
a birth moment, so the table itself was personal data. The record and every
value derived from it were removed from this repository when the reference
fixture became fictional — see the 2026-08-26 entry at the top of this file.
