# Dashboard restructure — domains, not techniques

**Decided 2026-09-08.** This is information architecture, not a reskin: the
visual language (ink ground, cream text, gold hairlines, Cormorant Garamond /
Lora, square corners) is unchanged, and **nothing is deleted — everything is
re-homed.**

## The problem

The dashboard was 17 sections in a flat scroll behind a sticky bar of 14
links: Glance · Chart · Daśās · Timeline · Transits · Doshas · Myths · Yogas ·
Match · Ask · Agent · Paṭha · Grahas · Learn.

Every one of those is a *technique*. A person arrives asking about their
marriage or their work and is handed a filing cabinet organised by method.
The information is all there and none of it is addressed to them.

## The decision

Reorganise around **what people ask about**, with techniques underneath.
Three options were on the table (domains; one-verdict-then-depth; progressive
by literacy). Domains wins for a reason beyond taste: `domains.py` already
encodes the domain model for `/ask` — houses, why each is in the list,
karakas, the varga that tests it, the six-step checklist. The dashboard and
the agent can share one structure instead of drifting apart.

## Three views, one page

**Client-side panes, not routes.** Sidera holds no birth record between
requests — the record is posted, the chart is cast, and nothing is stored.
Server-side routes for `/domain/marriage` would mean re-posting the birth
details on every tap. So all three views render once and the browser switches
between them, with `#hash` deep links and real browser history.

### 1. ARRIVAL

```
  [ chart wheel ]                     ← the thing they came to see
  Leo lagna 11°05′ · Moon in Rohiṇī   ← 3-line identity strip
  Rāhu daśā · Venus antara to Mar 2027
  ────────────────────────────────────
  “<the Glance verdict, unchanged>”
  ────────────────────────────────────
  ┌──────────────┬──────────────┐
  │ Love &       │ Work &       │     ← domain card grid
  │ Marriage     │ Money        │
  │ <teaser>     │ <teaser>     │
  ├──────────────┼──────────────┤
  │ Home &       │ Body &       │
  │ Family       │ Vitality     │
  ├──────────────┼──────────────┤
  │ Learning &   │ Ask about    │
  │ Path         │ this chart   │
  ├──────────────┴──────────────┤
  │ Explore the full chart      │
  └─────────────────────────────┘
```

Five domain cards, plus **Ask** and **Explore the full chart**. Each domain
card carries a **one-line teaser drawn from its own checklist** — not a
prediction, a condition: what supports the matter, what strains it, and
whether the running period touches it.

### 2. DOMAIN VIEW

Verdict-first, in this order:

1. **The synthesis** — two or three short paragraphs: what supports, what
   delays, what the running period emphasises. Composed deterministically
   from the checklist (see *Where the reading comes from*).
2. **The checklist as expanders**, in the method's own order — NATAL (each
   house with **why it is in the list**), KARAKA, VARGA, DASHA, TRANSIT
   (occupancy *and* drishti, with dates).
3. **Ask about this** — one tap to put the domain's question to the agent,
   when it is configured.

Everything stays one tap from its computation, exactly as now: each expander
names the fact ids behind it.

### 3. EXPLORE THE FULL CHART

Every technical section, unchanged, behind the existing sticky nav: Grahas ·
Paṭha · Yogas · Doshas · Myths · Timeline · Daśās · Transits · Match · Learn.
Same markup, same tests, same behaviour — re-homed, not rewritten.

## Where the reading comes from

**The core dashboard must not need an API key.** "No language model writes
readings" is a standing property of this build, and the domain synthesis is a
reading.

So the synthesis and the card teasers are **composed deterministically** by
`domainread.py` from the same ledger facts the agent's checklist cites:

| Signal | Read from |
|---|---|
| Support / strain per house | the house lord's dignity and placement, benefics and malefics aspecting the house, occupants |
| Karaka condition | `karaka.<planet>` — dignity, house, affliction |
| Varga confirmation | the domain house in D9/D10 and its lord |
| Period relevance | whether the running MD/AD lord rules or occupies a domain house |
| Live transits | slow movers occupying **or aspecting** a domain house, with dates |

Every sentence it emits is traceable to a fact id, and the same
`Interpretive` confidence tag the rest of the app uses applies. The LLM agent
remains **optional and additive**: where configured, "Ask about this" gets the
full six-step synthesis; where not, the deterministic reading stands alone and
the panel says so, as it already does.

## Mobile-first (390px)

- Card grid is **one column at 390px, two from 560px**. Not three: the body
  is capped at 640px by the existing layout, so a third column would only
  narrow the cards. (Corrected during the build — the spec first said three.)
- Cards are `<a>`/`<button>` elements with a ≥44px tap target and the whole
  card tappable, not just the title.
- The wheel is the first thing on screen; the identity strip is three lines
  and must not wrap to four at 390px.
- Pane switching scrolls to top and moves focus, so a screen reader and a
  thumb agree about where they are.
- No horizontal scroll at 390px anywhere — enforced by the existing
  measurement test.

## Non-negotiables carried forward

- **Square corners.** Border-radius is 0 or 50%, nothing else
  (`test_framework_non_negotiable_tokens`).
- **One geometry table.** The plate's placement and aspect layers keep
  reading `HOUSE_POLY` from the server
  (`TestPlateGeometry`, `TestPlateGeometryAgainstAnIndependentRenderer`).
- **No build step.** Hand-written CSS and vanilla JS, no bundler, no
  framework (`ui-design/RENDERER-EVALUATION.md`).
- **No fear language** (`test_no_fear_language_anywhere`).
- **Every reading shows its computation** — the expander pattern is the
  point of the domain view, not decoration.
- **The chosen school prints on affected verdicts** (`schools.py`).

## What this unblocks

Milestone 2 (Ashtakavarga) was queued behind this restructure. Its
verdict-first dashboard domain — strongest and weakest houses named up front,
the 12×8 grid folded under — now has an obvious home: a sixth card, or a
section within each domain view showing that domain's houses' SAV. That
choice is deferred to when the module lands.

## Explicitly out of scope

- Any change to the visual language, palette, or type scale.
- Any change to what is computed. This moves things; it does not add
  astrology.
- Accounts, saved charts, or server-side state. The birth record is still
  posted per request and never stored.
