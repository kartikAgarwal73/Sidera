# Sidera

A sidereal Vedic astrology app: enter a birth date, time and place, and get a
North-Indian kundli with daśās, transits, yogas, doshas and compatibility.
**Every reading shows its computation** — the placement it came from, the
classical rule applied, and how confident that rule is.

![Sidera landing](docs/landing.png)

## The accuracy thesis

Most astrology software asks to be trusted. Sidera is built so it can be
checked instead:

- **Nothing is approximated by hand.** Every position comes from
  [pyswisseph](https://github.com/astrorigin/pyswisseph) — sidereal, Lahiri
  ayanāṃśa, Whole Sign houses from the Lagna.
- **A second ephemeris checks the first.** The reference chart's positions
  are independently recomputed with [ERFA](https://github.com/liberfa/pyerfa)
  (the IAU SOFA-derived library, sharing no code with swisseph) and asserted
  to agree within one arcminute — `tools/erfa_cross_check.py`. Checking our
  ephemeris against itself would prove nothing.
- **Every interpretation carries its working.** Statements expand into the
  computed fact, the mechanism with the house-counting shown, and the
  classical rule verbatim, tagged **High / Moderate / Interpretive**.
- **Disagreement is displayed, not resolved.** Where classical lenses point
  different ways, "Ask your chart" shows the convergence score and lists the
  dissenting lenses side by side rather than averaging them away.
- **No language model writes readings.** The daily reading is composed from an
  authored fragment library by a seeded, deterministic pipeline: the same
  person on the same day gets the same sentence forever.
- **The one LLM feature is fenced in code, not by prompt.** "Ask about this
  chart" reads free-text questions against two things it may not depart from:
  a **fact ledger** (the computed chart, ~140 statements with stable IDs) and a
  **rule library** (`rulelib.py` — classical daśā-phala and gocara rules, each
  with its named source). It never computes. It is *required* to interpret —
  a fact-list is not a reading — and every interpretive statement must cite a
  rule ID that exists.

  For a life-domain question it must also work a **method**, not find a fact.
  `domains.py` names the houses each domain owns and why each is in the list,
  its natural significators, and the divisional chart that tests it; the
  prompt then requires **NATAL → KARAKA → VARGA → DASHA → TRANSIT →
  SYNTHESIS** in order, with the exact fact ids each step is answerable from.
  Step 5 uses drishti, not just occupancy — *"transiting Saturn in your 4th
  also aspects your 10th, so the career house is under its discipline until
  Jun 2027"* — and a claimed transit aspect that the ledger does not support
  **for the selected school** is a violation like any other.

  The line it works to is narrow and specific: **it may say what a period
  favours, asks for or classically tends toward; it may not say what will
  happen.** Answers are parsed and checked before display — an invented
  placement, a transit put in the wrong sign, an outcome asserted as settled
  ("you will get a job"), or a date the chart never produced are each a
  *violation*, and a violated answer is withheld rather than captioned. The
  feature is optional: with no `ANTHROPIC_API_KEY` the panel says so and
  everything else is unaffected.
- **Where sources genuinely differ, the app asks** instead of picking a side
  quietly. `schools.py` puts the handful of real forks to the reader as plain
  English questions — *"How far does the influence of Rahu and Ketu reach?"* —
  with two or three plain-English answers, the school name in small text
  underneath, a one-line note on what changes, an "explain this" expander, and
  the mainstream answer pre-selected and labelled **recommended**. Nobody needs
  the vocabulary to choose. Two rules are enforced by tests rather than
  intended: **no live option may be a control that changes nothing** (a chart
  is computed under each answer to prove it moves), and **the chosen school is
  printed on every verdict that depended on it** — and on none that did not.
  A question whose feature is not built yet (the Upapada's two rulers) is
  shown, explained and disabled rather than offered. See also the yoni and
  vaśya notes in `gunamilan.py`.

### The test suite distinguishes two kinds of guarantee

A green suite can mean "still correct" or merely "still the same". Sidera
separates them: every test declares its provenance in `conftest.py` as

| Class | Meaning | If it goes red |
|---|---|---|
| `external` | Anchored to a source outside this build — a second ephemeris, a classical rule, published astronomy, a design document | **The code is wrong.** Do not edit the expectation |
| `invariant` | True by definition, mathematics, or an explicit product rule | **The code is wrong.** |
| `characterization` | Froze observed output — protects continuity, not correctness | May be re-baselined, and the commit must say so |

`test_hygiene.py` fails if any test is undeclared, if the conformance audit's
counts drift from reality, or if a dependency loses its version pin. Current
split is generated into
[`ui-design/FRAMEWORK-AUDIT.md`](ui-design/FRAMEWORK-AUDIT.md).

Roughly 42% of the suite is `characterization`, and the honest reason is
worth stating: the reference chart is **fictional**, so most chart-derived
expectations cannot be anchored to anything outside this build. They are
labelled accordingly rather than dressed up. What genuinely anchors the
numbers is the ERFA cross-check above and `TestAstronomicalAnchors` —
person-free published facts (Spica at 180°, the epoch ayanāṃśa, a catalogued
eclipse) that anyone can verify in any ephemeris.

## Stack

Python 3.11 · Flask (server-rendered Jinja) · pyswisseph · gunicorn in
production. No database. The city lookup is a bundled offline GeoNames
extract, and every computed section works with no network and no keys. Front
end is hand-written CSS and vanilla JS with no build step.

The single exception is the optional "Ask about this chart" agent, which
calls the Anthropic API server-side using `ANTHROPIC_API_KEY`. It is off
unless that variable is set; see [DEPLOY.md](DEPLOY.md).

**Ephemeris note:** no `.se1` files are shipped, so swisseph uses its built-in
Moshier analytical ephemeris — sub-arcsecond over the dates this app handles,
and the reason the container needs nothing mounted. `engine.ephemeris_backend()`
reports which source is live, and a test asserts it, so adding ephemeris files
via `SE_EPHE_PATH` is a visible change requiring gate re-verification.

## Run it locally

```bash
git clone <this repo>
cd vedic-astro
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python app.py                     # http://localhost:5000
```

Run the suite:

```bash
pytest                            # gates + hygiene
pytest -m external                # only externally anchored tests
```

Serve it the way production does:

```bash
PORT=8000 gunicorn app:app --bind 0.0.0.0:$PORT
```

Deployment steps for Render are in [DEPLOY.md](DEPLOY.md).

## Verification fixtures

**No real person's birth record is committed to this repository.** The gate
suite runs on two fictional charts kept in one place in `fixtures.py`: a
reference chart and a second one so the compatibility gates pair two
different people rather than a chart with itself.

Supply your own with `SIDERA_FIXTURES=/path/to/fixtures.json`; the anchored
gates then skip, because their expected values belong to the built-in charts
and inventing values for another chart would defeat the point of an anchor.

```bash
pip install pyerfa numpy          # dev-only, not an app dependency
python tools/erfa_cross_check.py  # re-derive the cross-check constants
```

## The oracle fixture

`fixtures_pyjhora.json` holds a **second implementation's answers** for the
two fictional charts, computed by [PyJHora](https://github.com/naturalstupid/PyJHora)
— an independently written Vedic astrology library that Sidera does not link,
import or ship. It covers what Sidera does not yet compute: all 23 divisional
charts **with degrees**, bhava arudhas A1–A12, chara karakas, Ashtakavarga
BAV/SAV, sphutas and Shadbala.

It is an *oracle*, not a dependency. The moment our answer and its answer come
from the same code, the agreement proves nothing — so `test_hygiene.py` fails
if any app module imports `jhora`. Regenerate with:

```bash
./tools/oracle/make_oracle.sh     # scratch venv OUTSIDE the repo; only the JSON is committed
```

**Four settings in that script are the whole reason it can be trusted**, and
every one is a trap at its default. Each would have produced a fixture
disagreeing with Sidera for a reason that has nothing to do with either being
wrong:

| | PyJHora default | Pinned to | Size of the difference |
|---|---|---|---|
| Ayanāṃśa | `TRUE_PUSHYA` | `LAHIRI` | 4106″ (1.14°) |
| Nodes | true node | mean node | up to ~1.8°; 1.48° on the partner fixture |
| Positions | `FLG_TRUEPOS` (geometric) | apparent, light-time corrected | 20.2″ Sun, 0.72″ Moon |
| Daśā year | `TRUE_SIDEREAL_YEAR` | `MEAN_SIDEREAL_YEAR` | up to a full day — see below |

The ayanāṃśa needed pinning in *two* places (internal call sites re-read
`const._DEFAULT_AYANAMSA_MODE`); the node switch needed a third (`drik`'s
planet tables are built from the constants at import time). The last two were
found by the 300-chart differential run, not by reading the source.

With all four pinned, all ten bodies agree with Sidera's D1 **to JSON rounding
(~0.002″)**, and every one of the 81 Vimshottari MD/AD boundaries agrees to
under a minute. That is the precondition: a comparison of arudhas or
Ashtakavarga means nothing until the underlying chart matches.

Being that exact also changes what the D1 comparison *proves*. With the
conventions matched, both sides are the same swisseph called the same way, so
this is a check on conventions and plumbing, not on the ephemeris — the
ephemeris is anchored by ERFA, and PyJHora's independence is spent where it
is worth more: nakshatras, vargas, daśās, arudhas, Ashtakavarga.

**Upapada has two schools, and both are exported.** An arudha is counted from
the lord of the house, and Scorpio and Aquarius have two lords each. *Parashari*
counts from the sole classical lord (Mars, Saturn); *Jaimini* counts from the
**stronger** of the two co-lords, so Ketu or Rahu can carry it. The Upapada
Lagna is the arudha of the 12th, and it is read for marriage — so Sidera will
name the school rather than pick a winner silently, the way `gunamilan.py`
already handles the yoni and vaśya splits. On the reference chart the schools
diverge at A7 (Gemini vs Scorpio); the file records exactly where.

### The differential run

Two charts cannot exercise a sign boundary, a polar ascendant, a leap day or a
DST transition. `tools/oracle/differential.py` generates **300 random charts** —
random date in 1950–2030, random time, random city — and diffs both engines
across D1 longitudes, signs, nakshatra/pada, D9/D10 signs and every Vimshottari
MD/AD boundary. The records are synthetic and are **not committed**; the seed
reproduces them, and `tools/oracle/DIFFERENTIAL.md` is the committed summary.

It has already paid for itself three times:

- **Found a Sidera bug.** Our Vimshottari used the Julian year (365.25 days).
  That was the *only* thing separating our timeline from PyJHora's — every
  boundary drifted at 0.0064 days/year and nothing else differed. Fixed to the
  sidereal year (365.256364), which is also the coherent choice for a system
  measured against fixed stars. Pinned by `TestVimshottariAgainstTheOracle`,
  which asserts the old constant would fail.
- **Diagnosed the arcsecond residual.** Every remaining difference was
  `FLG_TRUEPOS` — the Sun's 20.2″ is 8.3 light-minutes × 0.986°/day. The
  Moon's 0.72″ looks negligible and is not: it is 1.5 × 10⁻⁵ of a nakshatra,
  which moved every daśā boundary in the fixture by hours through the balance
  at birth.
- **Found a defect in the oracle.** PyJHora's default daśā year,
  `drik.true_sidereal_year()`, returns values up to a full day too long on
  some charts — impossible for a sidereal year, which varies by minutes.

With all conventions matched: **zero disagreements across all 300 charts**.

One honest caveat recorded in the file itself: the BAV per-planet totals
(48/49/39/54/56/52/39, summing to 337) are **identical for every chart** —
they count rows in the classical benefic-point tables and depend on no birth
moment. They gate the tables, not a chart. The per-sign arrays are what
actually vary and what a real comparison must use.

## Licence

**AGPL-3.0** — see [LICENSE](LICENSE).

This is not a preference; it is inherited. Every position in this app comes
from [pyswisseph](https://github.com/astrorigin/pyswisseph), which is
distributed under the GNU Affero GPL v3 (`License :: OSI Approved :: GNU
Affero General Public License v3`, and the full text ships in its wheel). The
underlying Swiss Ephemeris is dual-licensed by Astrodienst — AGPL, or a paid
Swiss Ephemeris Professional licence — and this build takes the AGPL arm. A
work that links AGPL code and is conveyed must itself be AGPL, so Sidera is.

Two consequences worth stating plainly:

- **§13, the network clause.** Anyone who interacts with a running instance
  over a network must be offered the Corresponding Source. A public repository
  alone does not do that; the *running app* has to point at it, which is why
  the page footer carries a **Source** link. That link is part of the licence,
  not a courtesy.
- **Nothing changes in practice.** The repository is already public, no
  ephemeris `.se1` files are shipped (swisseph falls back to its built-in
  Moshier model, itself AGPL under the same terms), and no proprietary code is
  vendored. The licence file records the position that already held.

`fixtures_pyjhora.json` is generated by PyJHora, also AGPL-3.0 — compatible,
and in any case it is committed data rather than linked code.

## Layout

```
app.py            Flask routes and view assembly
engine.py         ephemeris, Lagna, sidereal positions, Whole Sign houses
dashas.py         nakṣatras and the Vimśottarī tree
pancanga.py       tithi, nakṣatra, yoga, karaṇa, sunrise/sunset
vargas.py         D9 / D10 divisional charts
transits.py       gocara, drishti, ingress finder
yogas.py          lordships, dignities, yoga detection
doshas.py         doshas with auto-run cancellations, transit weather
gunamilan.py      aṣṭakūṭa compatibility
ask.py            question → weighted lenses → verdict (deterministic)
chartfacts.py     the computed fact ledger, with stable citation IDs
schools.py        the computation options, asked in plain English
domains.py        life domains: their houses, karakas, varga and checklist
rulelib.py        classical rules the agent interprets through, each sourced
agent.py          grounded 'Ask about this chart' + its answer validator
reading/          the daily reading: detect · select · compose · fragments
explain.py        three-layer explanations with confidence tags
lessons.py        the 20-card literacy path
test_gates.py     the gate suite       test_hygiene.py   guards on the gates
fixtures_pyjhora.json   a second implementation's answers (external gate)
tools/oracle/     builds that file in a scratch venv; never imported by the app
```

## Credits

Built by [Kartik Agarwal](https://www.linkedin.com/in/kartikagarwal73/).
City data © [GeoNames](https://www.geonames.org/) (CC BY 4.0); region names ©
[dr5hn/countries-states-cities-database](https://github.com/dr5hn/countries-states-cities-database)
(ODbL). Both are bundled offline.
