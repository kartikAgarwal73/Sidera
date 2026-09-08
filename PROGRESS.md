# PROGRESS

## /ask becomes a reading method, not a lookup ✅ (2026-09-08)

**The failure.** Asked *"will I marry?"*, the agent found the 7th house, said
something about it, and stopped. That is fact retrieval wearing a reading's
clothes. An astrologer doing the work reads the 7th **and** the houses that
support it, each house's **lord**, the **karaka's** condition, the
**divisional** chart that tests whether the promise holds, the **period**
actually running, and what the slow **transits** are doing to those houses —
by drishti as well as by occupancy — and only then says anything.

### The method, encoded

`domains.py` writes it down: which houses each domain owns and **why each one
is in the list** (marriage: 7th, plus the 2nd because a marriage adds to the
household, the 5th for the courtship that precedes it, the 8th as the 2nd from
the 7th, the 11th for a desire fulfilled), the natural significators, and the
divisional chart that tests it. Five domains ship: marriage, career, vitality,
home, learning.

The question selects the domain, and the ledger then carries a `domain` block
with the checklist **and the exact fact ids each step is answerable from** —
so a skipped step is visible rather than plausible. The prompt requires
`NATAL → KARAKA → VARGA → DASHA → TRANSIT → SYNTHESIS`, in order, and the
synthesis is two to four paragraphs weaving all five rather than five labelled
sections.

### The ledger had to grow to make the checklist answerable

Steps 1–3 were asking for things that were *derivable* from other facts and
therefore, in practice, skipped. 81 → **140 facts** (66 KB):

| New | What it carries |
|---|---|
| `natal.1L` … `natal.12L` | each house's lord, where it sits, its dignity, what else it rules, and the drishti falling on that house |
| `karaka.venus` … (×9) | the significator's **condition** — sign, house, dignity, retrogression, lordships, what aspects it — not just its meanings |
| `d9.7th`, `d10.10th` … (×24) | the domain house of a divisional chart in one citation, instead of nine per-planet facts the agent had to assemble |
| `transit.saturn.aspects` (×9) | **the natal houses each transit aspects**, with the dates it entered and leaves |
| `transit.rahu.station` | retrogrades, and the note that the nodes are always so |

### Step 5 is the substantive one

A transit reading built on occupancy alone drops most of what the classical
method looks at. *"Transiting Saturn in your 4th also aspects your 10th, so
the career house is under its discipline until Jun 2027"* is the sentence the
step exists to produce, and it needs three things the ledger did not have: the
aspect list, the entry date, and the exit date. Without the **entry** date the
agent has half a window and invents the other half — which
`find_invented_dates` then withholds the whole answer for.

The offsets come from `transits.drishti_offsets`, so the nodes' rows follow
the reader's answer to *"How far does the influence of Rahu and Ketu reach?"*.

### The validator gained a class of claim, not a loophole

`find_bad_transit_aspects` checks drishti claims against the table the ledger
published **for the selected school**. Under *"they do not reach out at all"*
any nodal aspect claim is a violation. Natal drishti claims are deliberately
not checked here — a different table — because checking them against the
transit one would withhold true sentences, which is the exact bug class that
made transits unusable before frames existed.

The scope guard is unchanged: *"will she marry me?"*, *"does Priya love me?"*
still refuse, and a refusal is still not a way to smuggle placement claims
past the checks.

### One cost, and what was done about it

The ledger doubled, and a session may ask ten questions of the same chart. The
user message is now two content blocks — the ledger marked `ephemeral`, the
question outside it — so questions two through ten read the ledger from cache
instead of paying for it again. A session that switches domains pays one cache
miss, which is the right trade.

346 passing (external 70 / invariant 186 / characterization 80).

## Computation options, asked in plain English ✅ (2026-09-08)

Jyotisha is not one method, and on a handful of points the sources genuinely
disagree. Every astrology app silently picks a side; Sidera now asks — in a
form a person who has never met the word *drishti* can actually use.

**The pattern.** Each option is a plain-English **question**, two or three
plain-English **answers**, and the technical **school name in small text
underneath** — available to anyone who wants it, required of nobody. Each
question carries a one-line **consequence** before you choose; each answer an
**"explain this"** expander of two or three sentences. The recommended answer
is pre-selected and labelled.

> **How far does the influence of Rahu and Ketu reach?**
> *This changes which planets Rahu and Ketu touch — and so which patterns the
> chart reports and which transits it calls significant.*
> ◉ They reach three places, the way Jupiter does · **recommended**
>   <sub>Parāśarī — the 5th, 7th and 9th signs from themselves</sub>
> ○ Only straight across the chart  <sub>Conservative — the 7th sign only</sub>
> ○ They do not reach out at all  <sub>Chāyā-graha — shadow points cast no drishti</sub>

Two questions ship **live**: nodal reach, and *where* the nodes are placed
(mean vs true node — up to 1.8°, measured at 1.48° on the partner fixture in
the differential run, enough to change a sign).

**Two rules give the feature its integrity, and both are tests, not
intentions.**

* **No fake controls.** `test_every_live_answer_actually_changes_a_computed_value`
  computes a chart under each answer and fails if none of them moves a real
  value. The Upapada question — "When a sign has two possible rulers, who
  decides?" — is therefore shown, explained, and **disabled**, because Sidera
  does not compute arudha padas yet (milestone 3). Offering it would have been
  a switch wired to nothing. It says so on the page, and `normalise()` refuses
  to select it even from a hand-edited request.
* **The choice travels with the result.** Every school-dependent statement
  names its school — nodal aspect facts in the ledger, the node placements and
  their transits, the transit section and the graha table on the dashboard,
  and a line under the chart heading that turns accent-coloured when a setting
  is away from the default. Asserted both ways: the stamp is on the affected
  facts and *not* on the unaffected ones, because noise everywhere is the same
  as provenance nowhere.

**A latent bug this surfaced.** `explain.py` described the drishti rule with a
hardcoded "…the nodes 5/9". Under two of the three answers that sentence was
simply false. It is now computed from the live table.

**How the selection reaches the engine.** A `contextvars.ContextVar` set for
the span of one request. No signature in six modules had to change, and unlike
a module global it cannot leak between readers on a reused worker thread —
which `test_the_selection_does_not_leak_between_requests` checks.

The reader can change a setting from the dashboard without retyping anything:
the panel re-posts the birth details already on the page.

330 passing (external 70 / invariant 170 / characterization 80).

## Differential accuracy test — 300 random charts; one Sidera bug fixed ✅ (2026-09-08)

`tools/oracle/differential.py` generates **300 random birth records** — random
date in 1950–2030, random time, random city from `data/cities.json` — and diffs
Sidera against PyJHora on D1 longitudes (1′), ascendant, nakshatra/pada, D9/D10
signs and every Vimshottari MD/AD boundary (1 day). **No record is any person's
birth data and none is committed**: the generator is seeded, so a run is
reproducible from the seed alone. The committed artefact is
`tools/oracle/DIFFERENTIAL.md`.

### Final result: zero disagreements across all 300 charts

…but only after three findings, which is the point of running it.

**1 · A Sidera bug: the daśā year was the wrong year.**
`dashas.DAYS_PER_YEAR` was 365.25, the **Julian** year. That was the *only*
thing separating our Vimshottari from PyJHora's — every MD and AD boundary
drifted at exactly 0.0064 days/year and nothing else differed at all. Setting
it to the **sidereal** year (365.256364) took the disagreement to **0.0000
days** on every boundary of every chart.

It is also the coherent choice on its own terms: Vimshottari is measured
against the Moon's position among fixed stars, so its year is the sidereal one.
365.25 was a computing convenience with no jyotisha claim behind it. JHora uses
this value and PyJHora carries it forward citing JHora.

The shift is small and invisible in the UI — at most 0.73 days at the far end
of a 120-year cycle, and **no displayed period month changes**, because periods
render as "Mon YYYY". No characterization test needed re-baselining.
`TestVimshottariAgainstTheOracle` now pins all 81 boundaries for both fictional
charts, and asserts that restoring the old constant breaks the gate.

**2 · The arcsecond residual was `FLG_TRUEPOS`, all of it.**
PyJHora sets swisseph's true-geometric-position flag; Sidera computes apparent
(light-time corrected) positions. Clearing it made the two ephemerides agree to
the last printed digit. The offsets are the planet's own motion across its
light-time — the Sun's 20.2″ is 8.3 light-minutes × 0.986°/day, which is why it
was the same 20.2″ on every chart.

The Moon's 0.72″ looks negligible and is not: it is 1.5 × 10⁻⁵ of a nakshatra,
and it shifts the **balance at birth**, which moved every daśā boundary in the
committed fixture by a constant 1.32 h (reference) and 2.40 h (partner). That
was caught only because the new Vimshottari gate is tolerant to a minute rather
than a day. `fixtures_pyjhora.json` now pins positions to apparent as well.

**3 · A defect in the oracle, not in us.** PyJHora's default daśā year is
`TRUE_SIDEREAL_YEAR` — `drik.true_sidereal_year()` measured per chart. A real
sidereal year oscillates about its mean by *minutes*; that function returns
values up to a **full day** longer on some (date, place) pairs. Unpinned it
produced 254 boundary disagreements across 7 records, the worst 112 days. The
comparison and the fixture both pin `MEAN_SIDEREAL_YEAR`, and the raw value is
recorded per record so the incidence is counted rather than guessed.

### What the D1 comparison now proves — and does not

With the ayanāṃśa, nodes, position flag and year length all pinned to match,
both sides are the same swisseph called the same way, and D1 agreement is
0.002″ — pure JSON rounding. That is a check on **conventions and plumbing**,
not on the ephemeris. Said plainly in the test rather than left to be assumed:
the ephemeris is anchored by ERFA, and PyJHora's independence is spent where it
is worth more — nakshatras, vargas, daśās, arudhas, Ashtakavarga.

### Design notes worth keeping

* **Two passes.** Pass A matches the position convention and isolates *logic*
  disagreements. Pass B leaves PyJHora at its default and measures what the
  convention costs — 9 categorical flips across 6 of 300 charts, a changed
  pada or navamsa sign. Arcseconds are invisible; a changed navamsa is not.
* **Benign boundary straddles are separated.** When two longitudes lie either
  side of a dividing line, both engines classified correctly and the split is
  arithmetic. Reported apart from real counting bugs so the bugs stay visible.
* **DST-ambiguous and nonexistent local times are dropped, and counted.** Both
  engines would have to guess; their guesses disagreeing would be an artefact
  of the harness.
* **BAV/SAV reports "not implemented" rather than skipping silently.** A
  differential test that quietly skips what it was asked to check reads later
  as a thing that passed.

### An external anchor for the chart wheel, from the UI evaluation

`react-native-kundli-chart` (MIT) authors the North-Indian plate in the same
300×300 space, and its `HOUSE_POLYGONS` table is **vertex-for-vertex identical
to ours** once our 3-unit stroke inset is removed — all twelve cells. That is a
second, independent derivation of the mapping the launch-blocking wheel bug was
about. `TestPlateGeometry` proves our two layers agree with *each other*, which
a wholesale rotation would survive; `TestPlateGeometryAgainstAnIndependentRenderer`
cannot be satisfied by any rotation, and was verified to go red under one.

The package itself is **not adopted** — see below.

### UI evaluation: adopt none

`ui-design/RENDERER-EVALUATION.md` has the measurements. In short:

| Candidate | Licence | Size | Verdict |
|---|---|---|---|
| `react-native-kundli-chart` | MIT | 332 KB; chart 8 KB | React Native only; **no aspect layer** |
| `vedic-astrology-chart-solid` | MIT | 26 KB ESM + 2.6 KB CSS | Needs SolidJS; **no aspect layer**; plate drawn as lines, nothing for a highlight to attach to |
| `erajasekar/astrochartjs` | MIT | 392 KB (Snap.svg 224 KB) | **South Indian** grid; last commit 2016 |
| `Kibo/AstroChart` | MIT | 3.3 MB | Western circular wheel — wrong shape |
| `jyotichart` | **none** | 384 KB | Unlicensed; writes SVG files, not a DOM |
| `ngx-kundali-north-chart` | **Apache-2.0** | 1.76 MB, 108 files | Angular + Angular Material |
| shadcn/ui | MIT (+ Apache-2.0, ISC deps) | CLI 840 KB; `lucide-react` alone 34.5 MB | Is React + Tailwind; no subset works in Jinja |

Neither MIT renderer has a drishti/aspect layer — the feature that justifies
the swap is the feature that is missing — and all of them require a JavaScript
runtime this app does not have. The dashboard restructure is a layout problem;
`<details>` and CSS cover it. Take shadcn's *patterns*, not its code.

308 passing (external 70 / invariant 148 / characterization 80).

## AGPL licence, and a PyJHora oracle for milestones 2 and 3 ✅ (2026-09-08)

### The licence was always AGPL; only the file was missing

`pip show pyswisseph` reports no `License` field, which is why this went
unnoticed. The wheel's metadata is unambiguous:
`License :: OSI Approved :: GNU Affero General Public License v3`, with the
full AGPL-3.0 text in `LICENSE.txt`. Every position in Sidera comes from that
library, so a conveyed work linking it must itself be AGPL. `LICENSE` is now
that text, byte-identical to the copy pyswisseph ships (sha256 verified).

Nothing changes in practice, as expected: the repository is already public, no
`.se1` files are shipped (swisseph falls back to its built-in Moshier model,
AGPL under the same terms), and nothing proprietary is vendored.

**One thing was not already true.** AGPL **§13** requires that anyone
interacting with the app *over a network* be offered the Corresponding
Source, and a public repository only satisfies that if the running app points
at it. The footer had no such link. It does now — one line, and it is part of
the licence rather than a courtesy. A hygiene test pins the licence to
pyswisseph's so a future session cannot quietly relicense while still linking
it.

### The oracle: a second implementation, fenced off

`fixtures_pyjhora.json` (83 KB) holds
[PyJHora](https://github.com/naturalstupid/PyJHora)'s answers for both
fictional charts: all 23 standard divisional charts **with degrees**, bhava
arudhas A1–A12 under both schools, chara karakas, raw BAV/SAV, 14 sphutas and
Shadbala. Built by `tools/oracle/make_oracle.sh` into a scratch venv
**outside** the repo; only the JSON is committed.

PyJHora is AGPL too, so linking it would raise no licence question. It stays
outside for a different reason: *an oracle that shares code with the thing it
checks is not an oracle.* `test_no_app_module_imports_the_oracle` and
`test_oracle_is_not_installed_in_the_app_environment` enforce that, so the
fence is checked rather than remembered.

**Two defaults that would each have produced a fake bug.**

| | PyJHora default | Pinned to | Difference |
|---|---|---|---|
| Ayanāṃśa | `TRUE_PUSHYA` | `LAHIRI` | 4106″ (1.14°) |
| Nodes | true node | mean node | up to ~1.8°; **1.48° on the partner fixture** |

The ayanāṃśa needed pinning in *two* places (`drik.set_ayanamsa_mode()` and
`const._DEFAULT_AYANAMSA_MODE` — internal call sites read the latter and put
True Pushya back). The node switch needed a third: `const.set_node_mode()`
updates the constants, but `drik`'s planet tables were built from them at
import time and keep the old swisseph body id until those dicts are rebuilt.
The node divergence was found by the D1 comparison itself — Rahu was 5314″
out on the partner chart while every other body was inside 50″, which is the
signature of a convention difference, not an error. Each chart records the
values it was **not** computed with, so the file carries its own proof.

**With both pinned, all ten bodies agree to under 49″ on both charts.** That
is the precondition; nothing downstream means anything without it.

> **Superseded the same day.** The differential run (entry above) traced every
> one of those 49 arcseconds to a *third* default, `FLG_TRUEPOS`, and a fourth,
> the daśā year length. With all four pinned the agreement is 0.002″ — JSON
> rounding. The two settings named here were the two that were known at the
> time, not the two that existed.

**What it buys immediately.** `vargas.py` was characterization only — its
expected D9/D10 signs came from this build, so asserting them proved
continuity, not correctness. PyJHora implements the Parāśarī counting
independently and agrees on **every body in both charts**. External count
50 → 63.

**An honest caveat, recorded in the file and pinned by a test.** The BAV
per-planet totals (48/49/39/54/56/52/39, sum 337) are *identical for both
charts* — they count rows in the classical benefic-point tables and depend on
no birth moment. They gate the **tables**, not a chart. The per-sign arrays
are what vary and what a real comparison must use. Milestone 2 must not
over-claim on the checksum.

### Both Upapada schools ship

An arudha is counted from the lord of the house, and Scorpio and Aquarius have
two lords each. **Parashari** counts from the sole classical lord (Mars,
Saturn); **Jaimini** counts from the *stronger* co-lord, so Ketu or Rahu can
carry it. Upapada Lagna is the arudha of the 12th and is read for marriage, so
Sidera will name the school rather than pick a winner silently — the same
treatment `gunamilan.py` gives the yoni and vaśya splits.

PyJHora exposes exactly that switch
(`const.scorpio_owner_for_dhasa_calculations` / `..aquarius..`), so both are
exported. On the reference chart they **diverge at A7 — Gemini under
Parashari, Scorpio under Jaimini** — a live case for milestone 3 to gate on.
The honest converse is recorded too: neither fixture's 12th house is Scorpio
or Aquarius, so the Upapada itself is uncontested *on these charts*, and that
must not be read as "the schools always agree on UL".

Chara karakas ship both schemes: the 8-karaka list is PyJHora's own, the
7-karaka list is **derived here** by excluding Rahu (the library does not ship
it) and is labelled as derived — a weaker gate, and not to be quoted as
oracle output.

300 passing (external 63 / invariant 147 / characterization 80).

## Rule precedence: a contact outranks the generic gocara verdict ✅ (2026-09-04)

**The bug.** A live reading called transit Ketu *supportive* because Ketu
stood 3rd from the natal Moon — while sitting 2.66° from natal Venus. Every
placement in that answer was correct, so no validator check could see it. What
was wrong was **which rule got reported as the verdict**: both rules were in
the library, and nothing said which one wins.

**Why the ledger was complicit.** `transit.ketu`'s statement ends on the
weather card's own words — "Counted from the Moon it stands 3rd — a supportive
gocara position." The agent quoted the ledger accurately. The contact existed
in `doshas.transit_weather` for the dashboard but never reached the ledger at
all, so the sharper fact was invisible to the agent.

**What shipped.**

* Five rules with named sources: `rule.transit.contact`,
  `rule.transit.node_on_natal` (the eclipse reading — Ketu withdraws and
  severs, Rahu inflates and adulterates), `rule.transit.contact_over_gocara`
  (the precedence — *viśeṣa* displaces *sāmānya*), `rule.precedence.name_both`
  (a conflict is named and resolved in the open, never flattened), and
  `rule.graha.karakatva`. They travel only when a contact exists.
* A new `contact.*` fact kind. Each carries the orb, the natal point's
  **lordships in this chart** and its **karakatvas** — so "Venus is eclipsed"
  becomes "your 6th and 11th, and love, comfort and refinement" — plus the
  outranked verdict *quoted with its own rule id* and the statement that the
  contact governs it.
* `transit.<planet>` now ends on a GOVERNING CONTACT clause when one applies,
  so the generic verdict is never the last thing the fact says.
* A validator check, `find_ungoverned_generic`. It attributes a
  supportive/favourable/easy claim to its **nearest subject graha** — the same
  nearest-marker rule `_frame` uses, and skipping a graha that is only the
  reference point of a count ("3rd *from* the Moon") — and withholds the
  answer if that graha has an unacknowledged contact. Naming the natal point
  anywhere, or citing the `contact.*` fact, satisfies it: the requirement is
  that the conflict is visible, not that it is phrased one way.

**The fixture is synthetic, and built backwards from a real ephemeris.**
Transit Ketu genuinely sits at Leo 14°03′58″ on 2026-03-15; natal Venus is
placed 2.66° ahead of it, the Moon in Gemini so Ketu's sign is 3rd from the
Moon, and the lagna in Sagittarius so Venus lands in the 9th and rules the 6th
and 11th — the reported configuration exactly, with no real birth record
involved. 14 tests; the central one asserts that an answer whose every
placement is correct is still withheld.

279 passing (external 52 / invariant 141 / characterization 80).

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

**GATES — SUPERSEDED 2026-09-08. The oracle now carries both.** The original
plan was route (a): the commissioner verifies the BPHS checksum off-machine
(this environment cannot reach a BPHS text — wisdomlib and archive.org both
refused egress, HTTP 000) and separately supplies AstroSage output as a second
implementation. `fixtures_pyjhora.json` satisfies both, on-machine and
regenerable:

  GATE 1 · the classical checksum. Per-planet BAV totals — Sun 48, Moon 49,
  Mars 39, Mercury 54, Jupiter 56, Venus 52, Saturn 39 — and their sum, 337.
  **PyJHora reproduces every figure exactly.** These were RECALLED, not
  verified, when written down; an implementation that did not get them from
  us now returns them. Gated in
  `TestOracleGatesTheNextMilestones::test_ashtakavarga_is_raw_per_sign_and_sums_to_337`,
  provenance `external`.

  GATE 2 · an independent implementation, per sign. PyJHora's raw BAV rows
  and SAV distribution for both fictional charts, which our module must
  reproduce. This is the gate that actually bites — see the caveat below.

  The commissioner's BPHS confirmation and an AstroSage capture remain
  **welcome but no longer blocking**. A third source would catch a shared
  misreading of the method that two agreeing implementations cannot; that is
  a real gap, not a formality.

**The caveat that decides how much gate 1 is worth.** The per-planet totals
are the SAME for every chart — they count rows in the benefic-point tables and
depend on no birth moment, which is why both fictional charts return the
identical numbers. **They gate the 56-row table, not the computation.** The
per-sign arrays are what vary between charts, and they are the real gate.
`test_the_337_checksum_is_chart_invariant_and_says_so` pins this so milestone
2 cannot quietly over-claim on the checksum.

**Precondition, already met:** the oracle's D1 must match ours, or its
Ashtakavarga differs for reasons unrelated to our BAV code. All ten bodies
agree to under 49″ on both charts, with the Lahiri ayanāṃśa and the mean-node
convention pinned to match — see `TestOracleCrossCheck`.

**The three capture hazards are handled in the export, not left to a reader:**
  1. **Per SIGN, not per house.** `bav_by_sign` / `sav_by_sign` are indexed
     Aries→Pisces and named so. The rotation to houses-from-lagna is ours to
     do in the dashboard, and the fixture must not be assumed rotated.
  2. **RAW, before reductions.** No trikoṇa or ekādhipatya śodhana applied,
     stated in the file's own `note`. Comparing raw against reduced is the
     classic false failure.
  3. **Seven BAVs, not eight.** `bav_by_sign` holds the seven grahas;
     `lagna_bav_by_sign` is carried separately and is NOT part of SAV. A test
     asserts SAV equals the seven summed.

Estimated 1.5–2 days: ~250-line module, ~12 tests, a dashboard domain, the
ledger entries. The compute is easy; the table transcription was the risk —
and the oracle is now what catches a transcription error, per sign.

**Standing rule, restated 2026-09-03 and now enforced by a test:** no real
person's birth record is ever a fixture. Every verification chart is
fictional; external cross-checks (ERFA, AstroSage) run against the fictional
fixture, never against a real one. `test_committed_fixtures_are_all_fictional`
fails if a third record appears in `fixtures.py`.

### Milestone 3 — QUEUED. Gated on the oracle (2026-09-08).

Ordering confirmed: **degree-level vargas FIRST**, then the finer divisionals
(D2, D7, D12, D16, D30, D60), then arudha padas and Upapada. Extending
`VargaPosition` with a divisional longitude is the prerequisite — it unlocks
varga nakshatras and dignity-by-degree, and shipping D30 or D60 at sign level
would mean building six charts that cannot be read properly and then
rebuilding them.

**Every piece of it now has an external gate waiting in
`fixtures_pyjhora.json`**, asserted in shape by
`TestOracleGatesTheNextMilestones` before any of it exists — so regenerating
the oracle into something the gates cannot rest on fails now, not mid-feature.

  * **Degree-level vargas.** All 23 standard Dn, every body, with
    `degree_in_sign` and the full divisional longitude. Today our D9/D10
    *signs* already agree with it exactly; the degree is the half we do not
    compute, and it is the whole point of this step.
  * **The finer divisionals.** D2, D7, D12, D16, D30, D60 are all present, so
    each lands with a reference chart rather than only a reading of the rule.
    One thing to settle when we get there: PyJHora offers several counting
    methods per varga (`chart_method=`) and the export takes each function's
    default, the Parāśarī one for the standard vargas. Where Sidera chooses a
    different method the disagreement is a *decision*, not a defect, and must
    be recorded as one.
  * **Arudhas and Upapada — both schools.** A1–A12 under Parashari and
    Jaimini, with `houses_where_schools_differ` computed. The reference chart
    diverges at A7 (Gemini vs Scorpio), so the two-school UI has a real case
    to be tested against instead of a hypothetical one.
  * **Chara karakas.** The 8-karaka scheme as PyJHora ships it; the 7-karaka
    list derived by excluding Rahu and labelled as derived.

Beyond milestone 3, the file also carries **14 sphutas** and **Shadbala** (six
components, totals in shashtiamsas and rupas, and the ratio to the classical
requirement, with the six asserted to sum to the total) — neither is planned
work, but when either becomes so the gate already exists.

**Bhrigu Bindu and avasthas are still absent from both sides.** PyJHora does
not export them here, so those two remain ungated and should not be built
against this file.


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
