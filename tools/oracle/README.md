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

## The two settings that make or break it

Both default to something Sidera does not use. Left alone, either would
produce a fixture that disagrees with every Sidera value and looks like a bug
in our engine.

| | PyJHora default | Used here | Size of the difference |
|---|---|---|---|
| Ayanāṃśa | `TRUE_PUSHYA` | `LAHIRI` | 4106″ (1.14°) |
| Nodes | true node | mean node | up to ~1.8°; 1.48° on the partner fixture |

The ayanāṃśa is pinned in **two** places — `drik.set_ayanamsa_mode()` and
`const._DEFAULT_AYANAMSA_MODE`, because internal call sites read the latter
and would silently put True Pushya back. The node switch has to reach further
still: `const.set_node_mode()` updates the constants, but `drik`'s planet
tables were built from them at import time, so those dicts are rebuilt too.

Every chart in the output records the Lahiri value *and* the True Pushya value
it was not computed with, plus the true-node positions and the arcsecond gap.
The file carries its own proof of which settings produced it.

## What it contains, per chart

- `rasi` — D1 with degrees, the agreement gate
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
