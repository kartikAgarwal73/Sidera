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
- **Where sources genuinely differ, the app says so** instead of inventing a
  table cell — see the yoni and vaśya notes in `gunamilan.py`.

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
production. No database, no API keys, no network calls at runtime — the city
lookup is a bundled offline GeoNames extract. Front end is hand-written CSS
and vanilla JS with no build step.

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
ask.py            question → weighted lenses → verdict
reading/          the daily reading: detect · select · compose · fragments
explain.py        three-layer explanations with confidence tags
lessons.py        the 20-card literacy path
test_gates.py     the gate suite       test_hygiene.py   guards on the gates
```

## Credits

Built by [Kartik Agarwal](https://www.linkedin.com/in/kartikagarwal73/).
City data © [GeoNames](https://www.geonames.org/) (CC BY 4.0); region names ©
[dr5hn/countries-states-cities-database](https://github.com/dr5hn/countries-states-cities-database)
(ODbL). Both are bundled offline.
