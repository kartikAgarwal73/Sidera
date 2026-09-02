# Sidera Build Framework v1 — conformance audit

Source: `Sidera Framework.pdf` (9 pages, 22 Aug 2026). The document declares
itself "the source of truth for structure"; the design files remain the source
of truth for appearance.

**Headline finding: the framework specifies a different stack than the one this
build was commissioned on.** The original master prompt fixed Python/Flask +
pyswisseph; the framework fixes React + Vite + TypeScript + swisseph-WASM as a
PWA. That is a product decision, not a defect on either side — see *Decision
required* at the end. Everything below maps what the current build already
satisfies, what diverges, and what is missing regardless of stack.

---

## ONE · THE STACK — **divergent (decision required)**

| Framework | This build |
|---|---|
| React + Vite PWA, TypeScript | Python 3.11 + Flask, server-rendered Jinja |
| swisseph-WASM in a Web Worker, on-device | pyswisseph in-process, server-side |
| Ephemeris `.se1` precached, offline-capable | Swiss built-in ephemeris, needs the server |
| Dexie/IndexedDB + Zustand | Stateless per request; localStorage for ratings/lesson state |
| Installable, no store review | Browser page, deploy target was Render |

The framework's argument is sound on its own terms: the browser is the one
runtime with an official Swiss Ephemeris WASM build, which removes the binding
problem and gets offline + install for free. It is the right stack **for the
phone app the design files depict**. It is not reachable by editing the current
build; it is a port.

## TWO · ARCHITECTURE — **partially conformant**

| Layer rule | Status |
|---|---|
| Dependencies point one way | ✅ `engine → dashas/vargas/transits → yogas/doshas → ask/explain → app` — no upward imports |
| Engine isolated, tropical never leaves it | ✅ `engine.py` is the only module importing `swisseph`… |
| …behind a worker/promise API | ❌ synchronous, in-process |
| Domain pure, moment passed as argument | ✅ every domain function takes `when`; nothing reads the clock except `app.py` |
| Domain has the tests | ✅ suite is overwhelmingly domain-level; counts generated below, never hand-written |
| View models: one hook per screen, all formatting | ❌ formatting is split between `build_dashboard()` and Jinja |
| Persistence with `id/updatedAt/deletedAt` | ❌ no durable records at all |
| Natal chart memoised per session | ❌ recomputed per request (~30 ms; not yet a problem) |
| Fixture persona snapshot-tested for drift | ✅ this is exactly the gate suite (different persona — see note) |

**Note on the fixture persona.** The framework names Aisha Rao (14 Aug 1998,
04:32, Jaipur — Siṃha lagna, Rohiṇī pada 2, Śani mahādaśā) as the snapshot
persona. As of 2026-08-26 the corrected Aisha chart **is** this build's
reference fixture: the commissioner's own record was removed from the
repository, and the fictional persona took its place across the whole gate
suite. The two artefacts are now directly comparable — and the framework's
own stated values are pinned as an external anchor by
`TestFrameworkFixturePersona`, including the two that do not reconcile.

## THREE · DOMAIN MODEL — **7 of 9 types present**

| Framework type | This build |
|---|---|
| `BirthData` | ✅ `engine.BirthData` — ❌ missing `timeKnown` |
| `Graha` | ✅ `engine.PlanetPosition` — ❌ missing `combust` |
| `Chart` | ✅ `engine.Chart` + `vargas.VargaChart` — ❌ no `chalit` varga (D9/D10 instead) |
| `Pancanga` | ✅ **added this pass** — `pancanga.py` |
| `DasaNode` | ✅ `dashas.MahaDasha` / `Period` — 2 levels, framework allows 3 (pratyantar) |
| `GocaraEvent` | ✅ `transits.Ingress` + `Contact` — ❌ no `relativeToMoon` on the event itself |
| `SadheSati` | ✅ `doshas.sade_sati_status()` — phase, dates, progress |
| `KutaScore` | ✅ **added** — `gunamilan.KutaScore` (+ rule, detail, confidence) |
| `GunaMilan` | ✅ **added** — `gunamilan.guna_milan()`, 8 kūṭas / 36, Maṅgala doṣa with cancellation, verdict |

Invariants — ✅ all longitudes sidereal, normalised; ✅ instants tz-aware UTC;
✅ nakṣatra/pada derived from longitude only, never stored.
❌ **Unknown birth time** (noon + candra lagna + suppress bhāva claims) is not
implemented; the form requires a time.

## FOUR · READING ENGINE — **built** (`reading/`)

Implemented as the framework splits it, so a port is a translation:
`detect.py` · `select.py` · `compose.py` · `fragments.py`. The weighted
condition table is reproduced exactly (100 daśā turn … 10 weekday lord), ties
break by natural graha order, and a day with nothing above 25 falls to the
pañcāṅga floor, which always yields. Fourteen fragments, three variants per
slot — the framework's 27 phrasings per condition. Word limits hold on all
365 sampled days.

Two documented refinements to the seed formula, neither silent:

1. **The slot is folded into the seed.** The framework's own arithmetic
   requires it — "three variants per slot gives 27 phrasings" is 3×3×3, which
   only holds if the slots are drawn independently. One seed for all three
   would move equal-length lists in lockstep and yield 3, not 27.
2. **SHA-256, not `hash()`.** Python's built-in hash is salted per process; a
   reading would change on every restart, which is the exact
   non-reproducibility the framework forbids.

The earlier machinery that shares its philosophy remains:

- `explain.py` — three-layer explanations, template-composed, mandatory
  confidence tags.
- `ask.py` — question → weighted lenses → verdict, deterministic, disagreement
  displayed rather than resolved.
- Both are **template-composed with no free-text generation**, which is the
  framework's central constraint ("no network, no model, no randomness that
  isn't reproducible"). The seeded-variant mechanism (`hash(personId + isoDate
  + fragmentId) % variants.length`) is the one piece with no analogue.

## FIVE · SCREENS & ROUTES — **divergent**

Framework: 9 screens, 5 tabs, one pushed route, onboarding as a gate.
This build: **one route** (`/`) — a long dashboard with a sticky section nav
and progressive disclosure, plus `/api/cities`. Section-for-section the content
maps (Glance≈Today, Chart, Transits, Paṭha, Grahas…), but Match has no
counterpart and there is no tab bar or per-route local state.

## SIX · TOKENS — **conformant after this pass**

| Rule | Status |
|---|---|
| Six palettes, switched by custom properties on the root | ✅ **added this pass** — `[data-palette]`, picker persisted |
| Pastel default | ✅ |
| Type scale (Cormorant/Lora, the seven sizes) | ✅ |
| 4px base, gutters 24/26, panel min-height 196, kundli 140/224 | ✅ 140 on the glance panel; the main plate is deliberately larger (commissioner's request: ~78vw, 900px cap) |
| Square corners, bezel the only radius | ✅ **fixed this pass** — the three 9px pills are now square; the only radius left is the 50% score ring |
| Colour as 1px stroke / hairline / text tint; fills only for active chip or segment | ✅ |
| No shadows, no gradients, no elevation | ✅ (test-enforced) |
| Ghost glyphs 11–16% accent, `pointer-events:none`, not announced | ✅ |
| All numerals tabular; degrees `11°04′`; scores as vulgar fractions | ✅ degrees; ✅ vulgar fractions (`24½/36`) |

## SEVEN · BUILD ORDER — where this build actually stands

| # | Milestone | Status |
|---|---|---|
| 01 | Engine, verified against the fixture before any UI | ✅ done (Phase 1 gates) |
| 02 | Domain layer with fixtures | ✅ **complete** — chart/houses/daśā/gocara/pañcāṅga/guṇa milan |
| 03 | Theme, tokens, Kundli | ✅ complete after this pass |
| 04 | Onboarding → first chart | ✅ **accepted** by the commissioner in its single-form form (no Dexie persistence, no unknown-time fallback — both deferred deliberately) |
| 05 | Chart, Transits, Match | ✅ **complete** — Match added, design 2d |
| 06 | Reading engine and Today | ✅ **complete** — `reading/`, statement + full day on the glance |
| 07 | Profile, Paṭha, offline | ⚠️ Paṭha ✅ palette picker ✅ profile/settings ❌ service worker ❌ |

---

## ⚠ Defect in the framework's TESTING RULE — the fixture persona

The framework instructs (TWO · ARCHITECTURE, and again at milestone 01):

> Snapshot the sample persona — Aisha Rao, 14 Aug 1998, 04:32, Jaipur —
> against known values: Siṃha lagna, Candra in Rohiṇī pada 2, Śani mahādaśā.
> Any drift is a regression.

**Written literally, that test fails on day one.** For 14 Aug 1998, 04:32 at
Jaipur the ephemeris gives **Cancer lagna** and the Moon in **Bharaṇī** — not
Siṃha and not Rohiṇī. The danger is not the failing test; it is that someone
"fixes" the engine to match values that were never computed.

The derived values are real, though — they come from a chart, just not that
one. Reconciled:

| Claim | As written (14 Aug 04:32) | Reconciles at **16 Aug 1998, 06:57 IST** |
|---|---|---|
| Siṃha lagna 11°04′ | Cancer | **Leo 11°05′** ✅ |
| Candra Rohiṇī pada 2 | Bharaṇī p1 | **Rohiṇī pada 2** ✅ |
| Śani mahādaśā | Moon | Rāhu (2011–2029) ❌ |

The date is two days early and the time about 2½ hours; correcting both
reproduces the first two claims to the arc-minute. **The third claim cannot be
reconciled by any birth data**: a Rohiṇī Moon is Moon-ruled, so Vimśottarī
must run Moon → Mars → Rāhu → Jupiter, putting Rāhu (not Śani) in the 2020s.
"Śani mahādaśā" — and the design mockup's "Śani · 2019–38" — is an
inconsistency, not a typo.

Recommended edit to the framework: change the persona's birth data to
**16 Aug 1998, 06:57, Jaipur**, keep the lagna and nakṣatra claims, and
replace the daśā claim with **Rāhu mahādaśā (Jun 2011 – Jun 2029)**.

This build now carries the corrected persona as a second snapshot fixture
alongside its own, with four tests — including one that pins the discrepancy
itself so this finding cannot silently rot.

## Delivered in this pass (stack-independent)

1. **`pancanga.py`** — the missing domain contract. Tithi (30, with pakṣa),
   nakṣatra, yoga (27), karaṇa (60, correct fixed/movable naming), sunrise and
   sunset at the birth place, weekday and its lord, plus `endsAt` for every
   limb via bisection. 9 tests, verified against independent checks: the
   29 Jun 2026 Pūrṇimā, the 13 Jul Amāvāsyā, and Jaipur sunrise/sunset to the
   minute (05:42 / 19:23 IST).
2. **Six-palette token system** — all six stored on the root and switched by
   `[data-palette]`, picker in the header, persisted per browser.
3. **Token non-negotiables enforced** — square corners restored; a test now
   fails the build if a radius other than `0`/`50%`, a shadow, or a gradient
   appears.
4. **Pañcāṅga surfaced** — the Glance kicker now reads the real tithi
   ("Sat 22 August · śukla Daśamī") and design 1c's four-cell strip sits under
   the statement with sunrise/sunset and the tithi's end time.

## Delivered in the second pass (path B)

5. **`gunamilan.py`** — the last missing domain contract. All eight kūṭas
   (Varṇa 1, Vaśya 2, Tārā 3, Yoni 4, Graha Maitrī 5, Gaṇa 6, Bhakūṭa 7,
   Nāḍī 8 = 36), each returning its score, its classical rule verbatim, the
   computed working, a confidence tag, and — when withheld — the classical
   easing that accompanies it. Maṅgala doṣa read from both charts with mutual
   cancellation. Verdict against the 18-point threshold. **Where authorities
   genuinely differ** (the finer yoni tiers, some vaśya cells) the module
   implements the attested extremes, defaults the rest to neutral, says so in
   the rule text, and drops to Moderate confidence — it does not invent cells
   to look complete.
6. **Match screen (design 2d)** — optional partner block on the birth form
   with its own city autocomplete; ghost "36", names with ✕, 104px score ring
   in vulgar fractions, italic verdict, eight expandable kūṭa rows with the
   withheld ones in accent, Maṅgala footnote. The glance's third chip becomes
   **Match** when a partner is present, per design 5a.
7. **Corrected fixture persona** — see the defect section above.

## Memory hygiene — what actually protects this build

Eight months and many sessions in, the honest question about any green suite
is *which* guarantee it gives. This build's answer, enforced rather than
asserted:

- **A red `external` or `invariant` test means the code is wrong.** Do not
  edit the expectation; go back to the named source.
- **A red `characterization` test may legitimately be re-baselined** — it only
  froze observed output. Say so in the commit message when you do.

Every test declares which it is (`conftest.py`), and `test_hygiene.py` fails
if any test is undeclared, if the registry names tests that no longer exist,
if the counts below drift from reality, or if a dependency loses its pin.

<!-- HYGIENE-COUNTS: generated, do not hand-edit -->
| Provenance | Tests | Share | What a failure means |
|---|---|---|---|
| `external` | 46 | 24% | anchored outside this build — a red one means the code is wrong |
| `invariant` | 69 | 35% | true by definition or product rule — a red one means the code is wrong |
| `characterization` | 80 | 41% | froze observed output — protects continuity, not correctness |
| **total** | 195 | | |
<!-- /HYGIENE-COUNTS -->

**Failure modes this build has actually suffered**, and what now catches them:

| Failure mode | Evidence from this build | Caught by |
|---|---|---|
| Decorative values promoted to ground truth | the framework's own fixture ("Siṃha lagna, Rohiṇī p2") does not compute; design-mockup pañcāṅga likewise | `TestFrameworkFixturePersona` pins the discrepancy itself |
| Confident but wrong upstream claims | briefing asserted Mars in Leo, Saturn retrograde — both false | nothing interpretive holds hand-entered ephemeris; the app recomputes |
| Prose summary drifting from code | a Phase-4 "missing aspect" report aimed at a lossy chat summary, not the code | assertions now pin the row |
| Environment collapse read as regression | a system package install wiped site-packages; suite went green → `ModuleNotFoundError` | pinned `requirements.txt` + `test_dependencies_are_pinned` |
| Audit prose drifting from reality | this file claimed "125 tests" while the suite stood at 144 | counts are generated; `test_audit_counts_match_reality` |
| Expectation edited instead of code | several red tests this build were resolved by correcting my prediction — the same motion that would bless a real regression | provenance classes: only `characterization` may be re-baselined |

**Known residual risk.** Provenance is declared by the author, so a
mis-declared test (calling a frozen value "external") defeats the scheme.
Nothing automated can catch that; it is why the source note is mandatory and
specific — a note that cannot be written honestly is the tell.

## Deployment posture (added 2026-08-22)

Served by **gunicorn** (`Procfile`, pinned in requirements); `app.py`'s
`__main__` block is local-development only, so no deploy path can switch the
debugger on — a test asserts `app.debug is False` on import. `PORT` is read
from the environment.

**No ephemeris files are shipped**, and that is deliberate rather than an
oversight: swisseph falls back from the requested SWIEPH to its built-in
Moshier ephemeris, which is sub-arcsecond over the dates this app handles and
needs nothing mounted on the container. The fallback is silent inside
swisseph, so `engine.ephemeris_backend()` surfaces it and a test pins it —
adding `.se1` files via `SE_EPHE_PATH` becomes a visible change of numerical
source requiring gate re-verification, not a silent improvement.

**Secrets posture: nothing to leak.** No API keys, no database, no network at
runtime. A repo-history scan found no keys, tokens or absolute local paths;
`.gitignore` now covers env files, virtualenvs, caches, OS cruft and `.se1`
binaries. The verification birth records are parameterised into `fixtures.py`
and removable in one edit — `SIDERA_FIXTURES` substitutes them, and the
anchored gates then skip rather than fail, because their expected values
belong to those specific charts.

## Decision required

The framework cannot be "implemented" further without choosing:

- **A · Port to the framework stack.** Rebuild as React + Vite + TS with
  swisseph-WASM, five layers, nine routes, Dexie. The Python build becomes the
  reference oracle — differential-test every domain function against it so the
  hard-won correctness (gates, daśā arithmetic, varga rules, BPHS dignity
  segmentation) transfers instead of being re-derived. Large, and the right
  move if the phone app in the designs is the product.
- **B · Keep Flask for the public v1, treat the framework as the v2 target.**
  Continue applying everything stack-independent — guṇa milan, the reading
  engine, unknown-time fallback, chalit, combustion, `timeKnown` — so that a
  later port is a translation rather than a redesign. Ships sooner (Render was
  already the plan); never becomes offline or installable.

Recommendation: **B now, A when the phone app is the priority** — the domain
work in B is exactly milestone 02, which A would need first anyway.

