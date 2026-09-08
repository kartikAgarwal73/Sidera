# Kundali renderer and component-library evaluation

Commissioned before the dashboard restructure: evaluate two MIT-licensed
kundali SVG renderers and shadcn/ui, and report **licence, size and fit before
adopting**. Measured 2026-09-08 against the real packages, not their READMEs.

## The constraint everything is measured against

Sidera is a **Flask app that server-renders one Jinja template**. There is no
Node toolchain, no bundler, no `package.json`, no build step. The North-Indian
plate is inline SVG, and its geometry lives in **one table in `app.py`**
(`HOUSE_POLY`, `HOUSE_CENTER`, `NUMBER_POS`, `PLANET_POS`, `DEG_POS` — 2.7 KB,
a 300×300 coordinate space) injected into the browser by a context processor so
the server-side placement layer and the client-side aspect layer share a single
source of truth. That sharing was not incidental: the launch-blocking wheel bug
was two layers disagreeing about geometry, and the fix was to make disagreement
impossible.

So "fit" here is not "does it draw a nice chart". It is:

1. Does it run without a build step?
2. Can the **aspect layer** (drishti arcs, animated house counting, click-to-
   highlight) use the same geometry as the placement layer?
3. Does it carry degree labels, crowded-cell handling, and the theme tokens?
4. What does it cost to leave, if it is abandoned?

---

## Renderer A — `react-native-kundli-chart`

| | |
|---|---|
| Licence | **MIT** ✅ |
| Version / age | 1.0.0, published 2026-07-16 (first release; 8 weeks old) |
| Size | 332 KB unpacked, 66 files; the chart component itself is 8.0 KB |
| Dependencies | none direct; **peer: `react`, `react-native`, `react-native-svg`** |
| North Indian | Yes — genuine diamond plate |
| Repo | github.com/mobile-dev-ci/react-native-kundli-chart |

**The good part is uncomfortably familiar.** Its `constants/geometry.ts`
authors the plate in a *fixed 300×300 coordinate space scaled through the SVG
viewBox*, with per-house anchor points for the sign label, the planet block and
the house number, and per-anchor `text-anchor` values so labels do not spill out
of the narrow corner cells. That is, line for line, the design Sidera arrived at
independently — including the detail that kendra houses fit three glyphs per row
and the others two. Convergent evidence that the geometry is right.

**It cannot run here.** `react-native-svg` renders to native iOS/Android views;
in a browser it needs `react-native-web` plus React plus a bundler. Adopting an
8 KB component would mean adopting a JavaScript build pipeline for a Python app.

**It also does not do the thing that matters.** Grepping the whole source for
`aspect`, `drishti` or `degree` returns exactly one hit — `degree?: number` in a
type declaration. There is **no aspect layer at all**. Sidera's "show your
working" feature — tap a graha, watch its drishti count round the houses — is the
part this would have to replace, and it is the part that is missing.

**Verdict: reject.** Right architecture, wrong runtime, and missing the feature
that justifies the swap. Worth reading `docs/GEOMETRY.md` for cross-checking our
anchor table; not worth depending on.

---

## Renderer B — `vedic-astrology-chart-solid`

| | |
|---|---|
| Licence | **MIT** ✅ (Copyright © 2024 koa137) |
| Version / age | 1.2.3, published 2026-07-17; first release 2025-10-09 |
| Size | 77 KB unpacked, 25 files; **26 KB ESM bundle + 2.6 KB CSS** |
| Dependencies | none direct; **peer: `solid-js`** |
| North Indian | Yes — `NorthIndianChart` and `SouthIndianChart` both ship |
| Repo | github.com/koa137/vedic-astrology-chart-solid |

The smallest credible option, and the only one whose runtime is plausibly
liftable: SolidJS is ~7 KB gzipped and can be loaded from a CDN. The bundle is
compiled Solid templates, so it renders `<line>` elements for the plate rather
than polygons — no per-house polygon table, and no point-in-polygon.

**Same fatal gap, plus a new one.** `grep -c aspect` over the built bundle
returns **0**. And because the plate is drawn as lines rather than addressable
per-house shapes, there is nothing for an aspect highlight to attach to; we
would be re-deriving cell geometry from the outside, which is precisely the
class of bug the shared `HOUSE_POLY` table was introduced to kill.

It also ships its own `style.css` with a `.vedic-chart` class hierarchy that
would have to be reconciled with Sidera's token system (the framework's six
palettes, set by a root attribute).

**Verdict: reject.** Closest to viable, but it does less than the code it would
replace and costs a rendering framework to get there.

### Also examined and rejected earlier

| Package | Why not |
|---|---|
| `erajasekar/astrochartjs` | MIT, but **South Indian** 4×4 grid (`houseCell.row/col`), last commit **2016**, CoffeeScript, needs Snap.svg (224 KB) |
| `Kibo/AstroChart` (→ AstroDraw) | MIT, but a **Western circular radix wheel** — wrong shape entirely |
| `VicharaVandana/jyotichart` | North Indian and Python, but **no LICENSE file** — unlicensed, so not usable regardless of fit; also writes SVG *files*, not an interactive DOM |
| `ngx-kundali-north-chart` | **Apache-2.0**, not MIT; Angular + Angular Material, 1.76 MB unpacked, 108 files |
| `@roxyapi/ui` | MIT web components (framework-agnostic, the right shape) but **64 MB unpacked**, 1050 files, and coupled to a commercial API |

---

## shadcn/ui

| | |
|---|---|
| Licence | **MIT** ✅ (`shadcn` CLI 4.21.0, published 2026-09-04) |
| Distribution | Not a dependency — a CLI that **copies component source into your repo** |
| Required stack | React 19, Tailwind CSS 4, Radix UI primitives, `class-variance-authority` (**Apache-2.0**), `lucide-react` (ISC) |
| Size | CLI 840 KB with 34 dependencies; `lucide-react` alone is **34.5 MB** unpacked; Tailwind 773 KB; one Radix primitive ~99 KB |

The copy-in model is genuinely attractive — you own the source, there is no
version churn, and the licence is clean. But shadcn/ui **is** React + Tailwind:
the components are `.tsx` files using Radix primitives and Tailwind class
strings. There is no subset of it that works in a Jinja template.

Adopting it means: add Node, a bundler, Tailwind's build, and React to a
server-rendered Python app whose entire client-side surface is currently one
49 KB template and a 28 KB stylesheet. The dashboard restructure is a layout
and information-hierarchy problem — accordions, tabs, a verdict-first ordering.
Every one of those has a native HTML element (`<details>`, which the app already
uses for the "Why?" and "Facts used" disclosures) or a dozen lines of CSS.

**Verdict: reject for the app.** The one thing worth taking is not code: it is
shadcn's *design decisions* — spacing scale, focus rings, the disclosure and tab
patterns, the empty and loading states. Those transfer to hand-written CSS for
free, and Sidera already has a token system (`ui-design/DESIGN-HANDOFF.md`) to
hang them on.

Note also the licence detail: shadcn itself is MIT, but a real installation
pulls in `class-variance-authority` (Apache-2.0) and `lucide-react` (ISC).
Both are permissive and compatible with AGPL-3.0, so nothing here is blocked —
but "shadcn/ui is MIT" is not the whole licence story of a shadcn install.

---

## Recommendation

**Adopt none of them. Restructure the dashboard in the existing stack.**

Not out of preference for hand-rolling. Out of three measured facts:

1. **Neither MIT renderer has an aspect layer.** Sidera's differentiator is
   showing the computation — the drishti animation, the house counting, the
   click-to-highlight. Both candidates would delete that feature and require it
   to be rebuilt on top of geometry we no longer control.
2. **Both require a runtime Sidera does not have.** React Native or SolidJS,
   and in shadcn's case React + Tailwind + a bundler. The current chart has
   *zero* JavaScript dependencies.
3. **The one thing worth copying is free.** `react-native-kundli-chart`'s
   geometry independently reproduces our own 300×300 anchor design. That is
   confirmation, and it costs nothing to take as confirmation.

What to do with the effort instead:

- **Done already: the cross-check.** `react-native-kundli-chart` also ships a
  `HOUSE_POLYGONS` table, and it is **vertex-for-vertex identical to ours** for
  all twelve cells once our 3-unit stroke inset is removed. That is a second,
  independent derivation of the mapping the launch-blocking wheel bug was
  about, and it is now gated:
  `TestPlateGeometryAgainstAnIndependentRenderer`, provenance `external`.

  It closes a real hole. `TestPlateGeometry` proves our placement layer and our
  aspect layer agree with *each other* — which a wholesale rotation of the
  house mapping would survive, and that is precisely the bug class it was
  written after. The new gate cannot be satisfied by any rotation; it was
  verified to go red under one. Two dozen lines of MIT-licensed coordinates,
  and the most valuable thing to come out of this evaluation.
- **Take shadcn's patterns, not its code** — the disclosure, tab and empty-state
  conventions, applied to the existing tokens.
- **Keep the geometry shared.** Whatever the restructure moves, the rule that
  the placement layer and the aspect layer read one table must survive it. That
  invariant is already pinned by `TestPlateGeometry`.

Revisit if a **framework-free web component** with drishti support appears —
`@roxyapi/ui` is the right *shape* (custom elements, no framework) and the wrong
size and coupling today.
