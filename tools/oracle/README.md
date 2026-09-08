# The oracle

`fixtures_pyjhora.json` is a **second implementation's answers** for Sidera's
two fictional fixture charts, produced by
[PyJHora](https://github.com/naturalstupid/PyJHora) (AGPL-3.0).

```bash
./tools/oracle/make_oracle.sh
```

Builds a scratch venv **outside** the repository, installs PyJHora and the
subset of its dependencies the computation path actually needs (no PyQt6),
runs it against `fixtures.py`'s charts with Lahiri pinned, and writes
`fixtures_pyjhora.json` at the repo root. **Only that JSON is committed.**

## Why it is fenced off

Sidera is already AGPL-3.0 (pyswisseph forces that), so linking PyJHora would
raise no licence question. The reason it stays outside the app package is
different and more important:

> An oracle that shares code with the thing it checks is not an oracle.

The whole value of this file is that PyJHora shares no line of *interpretation*
code with Sidera — no varga counting, no arudha derivation, no Ashtakavarga
tables. If the app imported `jhora`, an agreement would prove only that a
function agrees with itself. `test_hygiene.py::test_no_app_module_imports_the_oracle`
fails if any application module ever does.

The second reason is weight: PyJHora's own `requirements.txt` pins PyQt6,
img2pdf and geocoder's full stack. A web deploy should not carry a GUI toolkit
to check a fixture.

## The four settings that make or break it

Every one defaults to something Sidera does not use. Left alone, each would
produce a fixture that disagrees with Sidera for a reason that has nothing to
do with either being wrong.

| | PyJHora default | Used here | Size of the difference |
|---|---|---|---|
| Ayanāṃśa | `TRUE_PUSHYA` | `LAHIRI` | 4106″ (1.14°) |
| Nodes | true node | mean node | up to ~1.8°; 1.48° on the partner fixture |
| Positions | `FLG_TRUEPOS` (geometric) | apparent (light-time corrected) | 20.2″ Sun, 0.72″ Moon |
| Daśā year | `TRUE_SIDEREAL_YEAR` | `MEAN_SIDEREAL_YEAR` | up to a full day |

Each needs pinning at a different depth:

- The **ayanāṃśa** in two places — `drik.set_ayanamsa_mode()` *and*
  `const._DEFAULT_AYANAMSA_MODE`, because internal call sites read the latter
  and would silently put True Pushya back.
- The **nodes** in three — `const.set_node_mode()` updates the constants, but
  `drik`'s planet tables were built from them at import time, so those dicts
  must be rebuilt.
- The **position flag** by clearing `swe.FLG_TRUEPOS` from `drik.PLANET_FLAGS`.
  Its effect on a chart is arcseconds; its effect on a *daśā* is hours, because
  the Moon's 0.72″ is 1.5 × 10⁻⁵ of a nakshatra and moves the balance at birth.
- The **daśā year** by passing `dhasa_duration_type=MEAN_SIDEREAL_YEAR`.
  PyJHora's default calls `drik.true_sidereal_year()`, which returns values up
  to a day too long on some charts — impossible for a sidereal year, which
  varies by minutes. See DIFFERENTIAL.md.

The last two were found by the differential run, not by reading the source.

Every chart in the output records the value it was *not* computed with — the
True Pushya ayanāṃśa, the true-node positions, the raw `true_sidereal_year` —
so the file carries its own proof of which settings produced it.

## The differential test

`differential.py` is the other half of this directory. It generates N random
synthetic birth records (random date 1950–2030, random time, random city from
`data/cities.json`), runs both engines over them, and writes
`DIFFERENTIAL.md`.

```bash
./tools/oracle/differential.py                 # 300 records, seed 20260908
./tools/oracle/differential.py -n 50 --seed 7
./tools/oracle/differential.py --keep /tmp/dd  # keep the raw records
```

The **records are never committed**. They are regenerable from the seed, and
no record is any person's birth data. Only the summary is committed.

It runs two passes: one with the position convention matched, which isolates
*logic* disagreements, and one with PyJHora at its own default, which measures
what that convention costs in changed padas and navamsa signs. Categorical
disagreements where the two longitudes straddle a dividing line are reported
separately as benign — both engines classified their own longitude correctly,
and burying a real counting bug among them would defeat the exercise.

## What it contains, per chart

- `rasi` — D1 with degrees, the agreement gate
- `vimsottari` — all 81 MD/AD boundaries, year length pinned and recorded
- `divisional_charts` — all 23 standard Dn **with the degree inside the
  divisional sign**, which is the half Sidera does not compute
- `bhava_arudhas` — A1–A12 under **both** the Parashari and Jaimini schools,
  with the Upapada (A12) called out and the houses where they diverge listed
- `chara_karakas` — the 8-karaka scheme as PyJHora ships it, and a 7-karaka
  list *derived here* by excluding Rahu (labelled as derived; it is a weaker
  gate than the rest of the file)
- `ashtakavarga` — raw BAV per sign, the Lagna row separately, SAV, totals
- `sphutas` — fourteen
- `shadbala` — six components, totals in shashtiamsas and rupas, and the
  ratio to the classical requirement

## How to read a disagreement

Provenance is `external`: if a Sidera test against this file goes red, the
presumption is that **Sidera is wrong**. Before concluding that, check in this
order — these are the differences that are methodological rather than
defects:

1. **Does D1 still agree?** Nothing downstream means anything until it does.
   With all four settings pinned it agrees to ~0.002″ — JSON rounding — so any
   real gap here means a convention has drifted apart again.
2. **Raw vs reduced Ashtakavarga.** These are raw bindus, no trikona or
   ekadhipatya śodhana. Comparing raw against reduced is the classic false
   failure.
3. **Sign index vs house number.** The BAV/SAV arrays are indexed by SIGN
   (0 = Aries). Sidera's dashboard presents by house; that conversion is ours.
4. **Which arudha school.** A7 already differs between them on the reference
   chart.
5. **Chart method.** PyJHora offers several counting methods per varga
   (`chart_method=`); this export takes each function's default, which is the
   Parāśarī one for the standard vargas.
