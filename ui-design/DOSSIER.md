# The editorial dossier — visual direction

**Decided 2026-09-09.** Sidera calls itself *a Vedic almanac*. It should look
like one: typeset, numbered, printed matter with unhurried pacing — not an app
skin over a chart engine.

**Visual layer only.** The information architecture, the verdict-first
structure, the word budgets, the validator and every computed value are
untouched. Nothing here changes what the app says or does; it changes how it
is set.

## Subject, audience, job

A **pañcāṅga** — an almanac. Read by someone who wants their chart read and is
not an astrologer. Its job is to hand over a verdict they can trust, with the
working available underneath.

That matters for the design because a pañcāṅga is not a magazine. It is a
**table-first** document: dense numeric tables ruled into columns, read by
someone looking something up. The design leans on that rather than on
editorial columns.

> **REVISED 2026-09-09 — the light paper almanac.** An approved Claude Design
> mockup moved the primary reading to **light paper**, cut the palette from
> six to two, and added a scroll choreography. The typography, the structural
> signature (the rule above the heading), the pagination and the contents-page
> layout below are unchanged; the colour section and the new *Choreography*
> section at the end carry the revision. `ui-design/DESIGN-HANDOFF.md` holds
> the superseding token table.

## Tokens

### Colour — one ground, one ink, one bronze

**Revised to the light paper almanac (2026-09-09).** Two readings, not six:
the four retired palettes were variations nobody was choosing between.

| Token | Paper (default) | Night reading | Role |
|---|---|---|---|
| `--paper` | `#f3f2f2` | `#1a1826` | the ground |
| `--surface` | `#e2dfda` | `#2b2839` | what sits behind the reading |
| `--ink` | `#201f1d` | `#ece5d8` | text |
| `--accent` | `#a37129` | `#dcb877` | the plate's ink, rules, large display |
| `--accent-ink` | `#7d5518` | `#e2c48c` | links, text below 24px |
| `--hairline` / `--divider` | 16% / 24% ink | same | rules |

`--ink` used to name the GROUND. It names the text now, and `--paper` is the
ground — the rename is the honest one for a paper-first design, and the gate
that used to catch "text painted the colour behind it" follows the new name
rather than retiring.

Decorative gradients were already banned by
`test_framework_non_negotiable_tokens`; so are shadows and any radius but 0
and 50%.

### Type — the face this subject is actually set in

**Tiro Devanagari Sanskrit** (display: verdicts, titles, plate figures) and
**IBM Plex Sans** (working text, tables, labels). One Google Fonts request.

Tiro Devanagari Sanskrit is not a decorative pick. John Hudson drew it to set
**Sanskrit**, and it carries three things this app specifically needs:

1. the full transliteration range — `ā ṃ ś ṛ ṣ ṭ ṇ ḷ` (`U+0100–02BA`,
   `U+1E00–1E9F`) — so *Navāṃśa* and *kṛṣṇa* set in one face instead of
   falling back mid-word;
2. the **Devanagari block itself**, matched to the same Latin design;
3. a single upright weight, which is the correct instrument for large, calm,
   unhurried display setting. Bookfaces are set large and light; only
   advertising sets them heavy.

The outgoing Cormorant Garamond could do none of the three.

IBM Plex Sans is chosen for **true tabular figures**, which is what an
ephemeris table needs, and for a drawing-office neutrality that leaves the
display face as the only voice in the room.

### Scale — four sizes with real gaps

| Role | Mobile | Desktop | Face |
|---|---|---|---|
| Verdict | 34px | 52px | Tiro, 1.18 leading |
| Page title | 27px | 36px | Tiro |
| Section head | 19px | 21px | Tiro |
| Working text | 15px | 15.5px | Plex, 1.72 leading |
| Table / data | 13px | 13px | Plex, tabular |
| Marker / label | 10px | 10px | Plex small-caps, .16em |

No 18px headings. The gap between the verdict and the working is deliberately
large: the verdict is the answer and the working is the evidence, and the type
should say so before anyone reads a word.

## The structural signature — the rule goes ABOVE

Devanagari does not sit on a baseline. It **hangs from a headline** — the
śiro-rekhā, the stroke drawn across the top of a word.

So every section marker in this design is a **rule above the heading, with the
heading hanging beneath it**, rather than the Western convention of a rule
underneath. It is one inversion, applied consistently, and it is the thing
that stops a hairline-and-small-caps layout from reading as a newspaper. It
comes from the writing system the subject is actually written in.

This is where the boldness is spent. Everything else stays quiet.

## Pagination as identity

Seven folds, and they are a real sequence — which is the test for whether
numbering is information or decoration:

| Fold | Page | View |
|---|---|---|
| 1 | p. 01 | Contents (arrival) |
| 2–6 | pp. 02–06 | the five domains |
| 7 | p. 07 | Explore the full chart |

Every view carries a marker top-right: `P. 02 · Love & Marriage · Fold 2 of 7`.

## Layout

### Arrival is the contents page

```
  SIDERA                              P. 01 · CONTENTS
                                          Fold 1 of 7
  ─────────────────────────────────────────────────────

              ┌───────────────────────┐
              │      the wheel        │      thin strokes,
              │   engraved, no glow   │      engraved plate
              └───────────────────────┘

  ᴘʟᴀᴛᴇ ɪ · ʀāśɪ ᴄʜᴀᴋʀᴀ
  cast 9 September 2026 · Lahiri ayanāṃśa
  ─────────────────────────────────────────────────────
  Leo lagna 11°05′                          ← the imprint
  Moon in Taurus · Rohiṇī pada 2
  Rāhu mahādaśā · Sun antara to Feb 2027
  ─────────────────────────────────────────────────────

  The lunar angle is cooperative —          ← the day, set
  small pushes travel further.                 as display

  ═════════════════════════════════════════════════════
  ᴄᴏɴᴛᴇɴᴛs                              ← rule ABOVE
  ─────────────────────────────────────────────────────
  02   Love & Marriage                        Read it →
       Marriage is more contested than helped…
  ─────────────────────────────────────────────────────
  03   Work & Money                           Read it →
       Work and money is one of the harder parts…
  ─────────────────────────────────────────────────────
```

**One column at every width.** A contents page is a list; rules *between
entries* only work down a single column. This is the one place the brief and
the old markup part company — the domain grid went two-up at 560px, and
`test_the_card_grid_is_one_column_on_a_phone` pinned that. The test now pins
the contents-list contract instead. No IA changed: same seven destinations,
same order, same links.

**The number and the page ref are one number.** The brief lists them as
separate columns; entry 02 lives on p. 02, and printing it twice is noise.

### Domain view

Title, then the verdict at the largest size on the page, then the working,
then one caveat, then the folded evidence. Unchanged in order — this is the
verdict-first structure already tested, set properly.

Expanders become **footnote lines**: a rule, the step name, the count, and
`show the working ↓` set small and right. No chunky accordion, no chevron
boxes.

### Tables

Set as printed ephemeris: a rule under the head only, no rule between rows,
no zebra, tabular figures aligned on the decimal, the label column in the
ink at 60% and the value column at full strength.

## Self-review against the brief, before building

The frontend-design skill lists, as the current tells of generated design:
broadsheet hairlines with zero radius; tracked-out all-caps eyebrow labels;
`A · B · C` middle-dot meta strings; `→` appended to links.

**This brief asks for all four by name**, and the brief's own words win. But
where the brief left an axis free, it is not spent on another default:

- **Small-caps, not all-caps.** `font-variant-caps` with real small-cap
  proportions, which is the printed-matter convention — not the web eyebrow.
  And used **only** as section markers, never stacked above every heading.
- **Middle dots confined to the page marker and the plate caption**, which are
  genuine printed-page slugs, not sprinkled through the UI.
- **The rule goes above the heading**, which no broadsheet does.
- **The typeface is chosen from the subject's own script**, not from the
  display-serif shelf.
- **`→` is pre-existing copy** ("Read it →", "Cast the chart →") and the brief
  forbids copy changes, so it stays. It is set as the contents page's
  right-hand column rather than as decoration on a button.

## Out of scope

No functionality, no copy, no IA, no new dependency beyond the one font
request. Every existing test stays green apart from the single column-count
assertion named above.


---

## Choreography (2026-09-09)

Six moves, one duration (`--reveal: 620ms`), one curve. Nothing bounces,
nothing loops, nothing moves that a reader did not scroll into.

1. **The fold rule draws in**, left to right, as its fold enters — and hands
   off to the next one down the page. A border cannot be scaled, so the rule
   is a pseudo-element.
2. **The plate pins** beside the day's verdict and the contents, and
   **releases at the last contents entry**. No JavaScript decides the release
   point: the sticky column sits in a grid that ends there.
3. **A ghost numeral** — the folio, at 12% ink, with the title overlapping its
   lower half — carries the plate's presence down-leaf after it releases.
4. **Each domain opens on a full-viewport verdict**, rising 22px into place
   (8px on a phone).
5. **Rhythm:** airy verdict → dense two-column working that fades in as one
   block → a one-line caveat → the next fold.
6. **Driven by CSS scroll-driven animation where the browser has it**, and by
   an IntersectionObserver everywhere else. Both paths end at the same final
   state, which is also what a reduced-motion reader gets immediately.

**`prefers-reduced-motion: reduce` turns all of it off** and keeps the pin: a
sticky element is layout, not motion, and dropping it would take the plate
away from the reading it belongs beside — a content loss dressed up as an
accessibility win. `TestReducedMotionInARealBrowser` drives a browser with the
preference actually set and asserts nothing is left invisible.

### Colour, revised

Two readings — **Paper** and **Night reading**. The bronze splits by role
because one hex cannot do both jobs: `#b68235` is 3.02:1 on paper (graphics
and large display only) and `--accent-ink` `#8a5f1c` is the same hue darkened
to 5.03:1 for links and small text. Every pair is recomputed from
`static/style.css` by `TestPaperPalette` on every run.

### The plate, on light

Ink for the frame and the diagonals; the single bronze line is the diamond
that makes it a North-Indian plate rather than a grid. Both are set in CSS,
not as presentation attributes, so the two readings can restate them.


---

## Revision 2026-09-10 — the collision, the hierarchy, and the index

### The arrival collision was a name, not a layout

The headline and the identity strip rendered **on top of the pinned plate**.
The cause was a class/id collision, not grid overflow: the leaf's second
section is `class="chartof" id="glance"` while a *different* section is
`class="glance"`, so the rule `.leaf > .glance` placed the wrong one and grid
**auto-placement** dropped the headline block into column 1 — under the plate.
It was only visible once the page had scrolled, which is why every screenshot
to that point had missed it.

Every child of the leaf is placed explicitly now
(`.leaf > *:not(.plate) { grid-column: 2 }`), which holds for any section
added later. `TestNothingOverlaps` walks four widths × four scroll positions
across four views and compares every visible text box against every other.

Two false-positive classes had to be handled before the gate meant anything:
a closed `<details>` lays its content out and hides it with
`content-visibility`, and an inline element that wraps returns a bounding box
spanning every line it touches. The gate uses **per-line rects** and walks
every closed-details ancestor. A sticky element **with an opaque background**
is treated as a deliberate overlay — which still catches the plate, because
the plate is sticky with no background.

The ☾, ॐ and 36 watermark glyphs are **gone**. They were the only elements
drawn on top of text by design, and the rule is now that nothing overlaps.

### The type hierarchy was upside down

The fold title rendered *smaller* than the verdict body, and the verdict was
set so large it ran three or four words to the line.

| | before | after |
|---|---|---|
| fold title | 27–36px | **clamp(44px, 7.2vw, 72px)** |
| verdict | 34–52px | **clamp(22px, 2.35vw, 30px)**, 52ch, 1.35 |
| folio numeral | in flow, behind the title | upper corner, clear of the type |

### Explore is an index

Eight categories — The Charts · Periods · The Sky Now · Combinations ·
Tables · Match · Ask · Learn — each with a one-line description at 16px.
Opening one shows that category and hides every other; **no fold presents two
categories at once**. Inside a category, body text is 16px and tables 15px
with real row spacing.

The sections were **not moved**: they carry a `data-cat` and the CSS does the
showing. Moving them would have cut through the Jinja conditionals that wrap
several of them, which is exactly what a first attempt did — four sections
stopped rendering entirely.

### Verdicts name something

`voice.py` gained a **vagueness** list. "Work and money is one of the stronger
parts of your chart — the planet that rules it is strong" passed every
existing gate and told the reader nothing about their own chart. A verdict now
names at least one graha and, where a dated influence is running, says when:

> **Work and money asks real work: Saturn, the planet of labour, sits at its
> weakest. The north node's period holds it until Aug 2029.**

Budgets are unchanged — 15 words, not 20. Specific *and* short.

---

## The five screens

The dashboard used to be one long arrival page with everything on it. It is
five peers now, reached from a tab row that is always in the masthead:

| Tab | Fold | What it is |
|---|---|---|
| Today | P. 01 | The dated sky, for this chart |
| Readings | P. 02 · P. 02·N | The seven-entry contents, and the verdict-first folds |
| Your charts | P. 03 · P. 03·N | The divisional plates, as a gallery |
| Explore | P. 04 | The eight-category index |
| Ask | (inside Explore) | Correspondence |

The folios are **two-level** now — `P. 02·1` is the first reading, `P. 03·2`
the second plate. Numbering stayed a real sequence, which is the test for
whether it is information or ornament; there are simply two levels of it.

### Screen 1 — Today

Left, a dated day-header set in the display face — *Thursday 10 September ·
Kṛṣṇa Amāvāsyā*, the day named twice, once by the civil calendar and once by
the Moon. Under it three or four dated entries, then one italic verdict line.
Right, the birth plate, pinned, with today's transits ticked around its
**outer** edge — the plate is the birth moment and today is a marginal note
on it, never drawn inside the frame.

`today.py` composes the entries. The ledger already knew a transit was inside
3° of a natal point and it already knew when a planet changes sign; it did
*not* know when a contact **ends**, because the orb has no boundary in the
fact. `contact_window()` finds both edges the way `next_sign_ingress` finds a
sign boundary — coarse scan, then bisect to the hour. Without that date the
entry reads "Ketu is on your Venus", which is exactly the register the voice
doctrine refuses.

Two things were wrong when the rendered screen was finally read rather than
reasoned about:

- **Every ingress line was generic.** "The Sun moves into Virgo on the 17th,
  carrying authority with it" is true of every reader alive, under a heading
  that says *Today for this chart*. The line now names the part of **this**
  chart the sign is — Whole Sign from the lagna, in plain words, never by
  number: *"— the part of your chart that holds gains."*
- **On a phone the day was a thousand pixels down.** The plate came first in
  source order, so arrival on a 390px screen showed a wheel and nothing else.
  The leaf is a flex column below 1000px with `.daycol { order: -1 }`: the
  plate is the illustration, the day is the reading.

### Screen 2 — Readings

Unchanged IA: the same seven contents entries, the same verdict-first folds.
One thing did change — the contents used to start at **02**, because entry 01
was the day's glance sitting above it on the same screen. Today is its own
fold now, so the list read as a page missing its first line. The numbers are
the folios the entries open (01 opens P. 02·1); the two entries that leave
this fold entirely, Ask and Explore, are unnumbered.

### Screen 3 — Your charts

A gallery-index of divisional plates: D1, D9 and D10 cast, and D2, D7, D12,
D30, D60 drawn as **dashed empty frames** marked *in preparation*. Listing
only the three that exist would imply the list is complete — the same honesty
the disabled school options get.

Each plate opens to its own page, and each page carries a reading **composed
from that division's own placements**:

> **Cancer rises in the ninth division, so the Moon carries the inner chart —
> and it keeps the sign it was born in, as does Mercury.**

The first version of this screen showed the plate and the gallery's one-line
summary, which says what a Navāṃśa *is* and nothing about this one. A gallery
of charts with no reading is a filing cabinet.
`test_a_plate_reading_is_computed_not_canned` casts a second chart and
asserts the three readings differ, because a constant would satisfy every
other assertion.

The plate on its own page is a **figure at the measure of its column** —
560px, centred — not the 900px breakout `.kundli` takes by default. Measured:
it had been arriving twice the size of the title above it.

### Scroll choreography, per screen

The four devices are unchanged; what differs is where each one lands.

| Screen | Rules draw in | Pin | Ghost numeral | Verdict moment |
|---|---|---|---|---|
| Today | `Today for this chart` | plate, released at the day verdict | — | the italic day line |
| Readings | `Contents` | plate, released at the last contents entry | fold number, behind the title | the fold verdict, 68vh |
| Your charts | `Divisional charts` | — (the gallery is the figure) | — | the plate's own reading, 68vh |
| Explore | each category rule | — | — | — |

Every entry on Today rises 22px into place (8px at ≤560px) over 620ms on
`cubic-bezier(.22, .61, .36, 1)`, once, never looping. `prefers-reduced-motion`
still turns all of it off and un-pins nothing essential —
`TestReducedMotionInARealBrowser` measures elements that are actually on
screen, after the fix that had it passing vacuously against a hidden fold.

---

## The type floors

The lower half of this scale had drifted to 9 and 10px — a texture on a 27"
display, unreadable on the phone it claimed to be designed for. Four floors,
and below the display range they are the only sizes that exist:

| token | px | what it sets |
|---|---|---|
| `--t-head` | 20 | a section title |
| `--t-body` | 16 | anything anyone reads a sentence of |
| `--t-table` | 15 | a cell in an ephemeris table |
| `--t-label` | 13 | a label, a status chip, a small-caps marker |

`--t-mark` is an alias of `--t-label`: the small-caps section markers are
named by role all through the stylesheet, and a marker is a label.

**A stylesheet scan cannot enforce this.** Half the small type is SVG, sized
in user units the viewBox then scales — the same `font-size: 13px` is 7
rendered pixels in the daśā graph (1000 units drawn at 560) and 24 in the
plate (300 units drawn at 560). `TestTypeFloors` walks every visible text node
at 390 and 1280 across fifteen views and multiplies by the element's own CTM
scale, so what it judges is what the eye receives.

Two consequences worth naming, because both trade information for legibility
rather than shrinking type past the floor:

- **Degrees at the larger sizes only.** On a 390px screen the plate draws its
  360-unit viewBox at about 0.95, so a 9-unit degree label rendered at 7.6px.
  The glyph and abbreviation carry the plate there; the degrees are in the
  graha table, and on any wider screen they are back on the figure.
- **A thumbnail carries glyphs, or dots.** Two-letter abbreviations in the
  140px gallery plate rendered at 3.9px. One glyph at 32 units reads at 13.
  Where even that will not fit — house 12 holds four grahas in a triangle
  whose top edge is the plate border — the cell shows one dot per graha. A dot
  has no legibility floor and says the true thing a thumbnail can say.

## How a graha is marked

Four things, and none of them is a hue. Using red for malefics and green for
benefics would make the plate a traffic light and carry nothing at all to a
colour-blind reader.

| mark | means |
|---|---|
| `☉Su` | the glyph a printed plate uses, and the letters that remove doubt |
| ink weight | natural benefic set light, natural malefic dense and full |
| `℞` | retrograde |
| `⊙` | combust — inside the Sun's orb, burnt; in the accent, the Sun's own mark |
| `Asc` | the lagna, at the head of its house's stack, in the accent |

The legend under every plate teaches all five. On arrival the graha chips
already pair each abbreviation with its name, so the legend there carries only
the marks — a second name list would be the same legend printed twice.

### The plate learned what fits

The anchor tables say where a stack is *hung*. They cannot see how *wide* it
is, and width is what left the cell: three marks side by side in house 9
measured 104 user units in a cell 73 across, and four degree labels in the
12th ran through the diagonal into house 1. The anchors were right and the
plate was wrong the whole time — and the anchor-based gates could not see it,
because the anchor was always inside.

`app.plate_layout` decides the arrangement from the polygons now, richest form
first and falling back one step at a time:

```
☉Su 29°09′   glyph, abbreviation, degree
Su 29°09′    the glyph is the widest character; drop it first
☉Su          the degree needs the most room; drop it next
Su           letters alone always fit
```

…and it moves the block to the cell's centroid before it gives anything up,
because dropping a degree is a real loss and moving a label 18 units down
inside its own cell costs nothing. Advance widths are measured in a browser,
not estimated. `test_no_label_overflows_its_cell_in_a_browser` reads the real
`getBBox()` and checks all four corners of every label against the polygon it
belongs to.

## One entry per phenomenon

Every entry in the Combinations fold declares a canonical `subject` —
`(what, condition)` — with exactly one home. Doshas is home to anything the
cancellation machinery runs on, because that is where the dates and the checks
live; the myth-vs-record framing of the same subject is folded into that
entry, and Myths carries a cross-reference line. Nothing is deleted — a gate
asserts every classical record is still printed somewhere.

## A yoga entry

Verdict first, in two sentences: whether the combination is real, and when it
acts. The name is *not* repeated — it is the heading the sentence sits under,
and repeating it spent a fifth of the budget and put "Yoga", banned from the
plain register, into every verdict in the app.

Under it, four labelled answers in a two-column grid — **Gives**, **Where**,
**D9** (and **D10** for a combination touching held resources, visible work or
gains), **Now** or **Next** — and behind the expander the mechanism, the
classical meaning, the division-by-division dignities, every period of every
forming graha, and the rule ids and fact ids the whole entry rests on.
