# PROGRESS

## Milestone 2 — Aṣṭakavarga, raw ✅ (2026-09-12)

Unblocked by the restructure, and shipped to the scope agreed on 2026-09-03:
raw BAV and SAV, **reductions deferred**, verdict-first presentation, and the
SAV numbers on the D1 plate.

### The gate that bit, exactly as the plan predicted it would

The plan recorded, before any code existed, that the 337 checksum "gates the
56-row table, not the computation" — the per-graha totals are identical for
every chart because they count rows in the benefic-point tables and depend on
no birth moment. That turned out to be the whole story of this milestone.

**Four rows of the table were wrong when first written down, and every
checksum passed.** Sun 48, Moon 49, Mars 39, Mercury 54, Jupiter 56, Venus 52,
Saturn 39, total 337 — all correct, with a bindu sitting at the wrong offset
in four places. A misplaced bindu moves where it lands, not how many there
are. Only the per-sign comparison against PyJHora, across both fictional
charts, found them:

| table | row | was | is |
|---|---|---|---|
| Moon | from Moon | missing 9 | `1 3 6 7 9 10 11` |
| Moon | from Mars | spurious 9 | `2 3 5 6 10 11` |
| Moon | from Jupiter | 12 | `1 2 4 7 8 10 11` |
| Venus | from Mars | 5 | `3 4 6 9 11 12` |

Each correction was checked two further ways before being taken, because
editing until an oracle agrees is fitting rather than verifying: it is the
**minimum edit** that reconciles both charts (an exhaustive solver over one,
two and three rows found nothing smaller and no alternative at that size), and
each corrected row is the one the standard published enumeration carries.

`test_the_checksum_is_blind_to_a_misplaced_bindu` now demonstrates the point
rather than asserting it — it moves one bindu, shows every classical total
still passes, and shows the per-sign comparison fail.

### Presentation

Verdict first, in the founder's own shape:

> **Your strongest houses are the 10th at 38 and the 6th at 31; the thinnest
> are the 2nd at 24 and the 12th at 25.**

then the strongest and thinnest named with what those houses carry, the total
with the note that it is the same in every chart, one line of caveat, and the
12×8 grid folded under it.

**On the plate, the totals take the sign numerals' slot rather than joining
them.** A North-Indian cell already carries a numeral and a graha stack;
measured, a third number collided with one or the other in every arrangement
tried — beside the numeral it grew the label wide enough to reach across a
diagonal into a neighbouring cell, and below it, it landed on the grahas.
Shrinking it to fit would have put it under the legibility floor set two days
ago. So it is a toggle, the way the degrees are: one number to a cell, and the
reader chooses which.

### The three capture hazards, handled in the types

1. **Per sign, not per house.** Every array in `ashtakavarga.py` is indexed
   Aries→Pisces, and `by_house` is an explicit call — a table silently rotated
   once is indistinguishable from one rotated twice. The rotation happens in
   one named place, `ashtakavarga_view`.
2. **Raw, before reductions.** Stated in `REDUCTIONS_NOTE`, printed in the
   app, and carried on every ledger fact as `raw: True` so the agent cannot
   quote a raw figure as a reduced one.
3. **Seven BAVs, not eight.** The lagna's row is computed, reported and never
   summed in. A gate asserts SAV equals the seven, and that seven plus the
   lagna would be 386.

### The ledger

Nineteen facts as designed — `sav.house.N` ×12 and `bav.<planet>` ×7, each
carrying a twelve-value array — plus `sav.summary`. Per-planet-per-house ids
would have needed 84 more and buried the useful facts.

**Still open, and still worth having:** a third source. Two agreeing
implementations cannot catch a shared misreading of the method. The
commissioner's BPHS confirmation remains welcome.

**Tests:** 546 passed.

## Type floors, one entry per phenomenon, plates that can be read, and a yoga that answers ✅ (2026-09-12)

Six findings from a founder's walk. All six shipped, each with a gate.

### 1. The type scale had drifted to 9px

103 of 155 `font-size` declarations were under 16px; 53 selectors rendered
under 13. Four floors now — `--t-head` 20, `--t-body` 16, `--t-table` 15,
`--t-label` 13 — and every sub-floor size in the stylesheet was rewritten to
name its role instead of a number, so a future edit that wants smaller has
to introduce a token rather than type a smaller literal.

**A stylesheet scan could not have settled this.** Half the small type is SVG,
sized in user units the viewBox then scales: the same `font-size: 13px` was 7
rendered pixels in the daśā graph (a 1000-unit viewBox drawn at 560) and 24 in
the plate (300 units drawn at 560). `TestTypeFloors` walks every visible text
node at 390 and 1280 across fifteen views and multiplies by the element's own
CTM scale, so it judges what the eye receives. It found, and these are fixed:

| | was | now |
|---|---|---|
| gallery thumbnail glyphs | 3.9px | 32 user units → 13.4 |
| daśā graph labels | 5.6–7.3px | graph draws 1:1; labels at the floor |
| glance mini plate | 6.5px | plate 200px, glyph-only marks |
| plate degree labels at 390 | 7.6px | hidden below 560px — glyphs carry it |
| chips, `th`, kickers, folios | 9–10px | `--t-label`, 13 |

Explore's section titles were 10px small-caps; they are `--t-head` now.

### 2. One entry per phenomenon

"Mars in house 8 (Mangal Dosha pattern)" and "Mars in the 8th house" printed
as two myth-vs-record entries — one placement, described twice, so a reader
comparing them found two classical records for the same fact. Sade Sati
printed in full under Doshas *and* under Myths.

Every entry declares a canonical `subject` — `(what, condition)` — with
exactly one home. Doshas is home to anything the cancellation machinery runs
on, because that is where the dates and the checks live; the myth-vs-record
framing of the same subject is **folded into** that entry, and Myths carries a
cross-reference line. Nothing was deleted:
`test_nothing_a_myth_card_said_was_dropped` asserts every classical record is
still printed somewhere.

### 3. A yoga is read, not just detected

`yogaread.py`. Before this, an entry gave a name, a rule, and a sentence of
meaning true of the yoga rather than of the reader's chart — and answered
neither question anyone asks. Four answers now, in order:

> **Thinner than it looks: Mars weakens in the ninth division, so its promise
> on the body and fortune asks more of you. Its period runs until Feb 2027.**

then **Gives** (one plain sentence, cited to a new `rule.yoga.*` in the rule
library), **Where** (the houses, in plain words, never by number), **D9** and
— for a combination touching held resources, visible work or gains — **D10**,
and **Now/Next** (the periods of its forming grahas, dated off the
Vimshottari timeline, labelled past, running or ahead).

The ledger gained `yoga.<slug>.varga` and `yoga.<slug>.activation`, so the two
things a reading asserts about a yoga are checkable. Varga dignity is computed
from the SIGN only and never returns moolatrikona, which needs a degree this
build does not hold.

### 4. Numerology was never built

Not a stub, not a route, not a line: `grep -i numerolog` over the whole
repository returned nothing. It is listed in the tab row and marked *in
preparation* — the same honesty the unbuilt divisional charts get — and
`test_nothing_in_the_build_pretends_numerology_exists` fails if a half-built
module ever makes that tab a lie in the other direction.

### 5. The plates carry real marks

Glyph + abbreviation (`☉Su`), ink weight for natural benefic against natural
malefic (weight, never hue — the palette has one accent and it means "look
here"), `℞` for retrograde and `⊙` for combust, with the lagna at the head of
its own house's stack in the accent. Combustion is new computation:
`yogas.combust()` with the standard Parāśari orbs and the retrograde
tightening for Mercury and Venus, cited as `rule.graha.combust`.

**And the plate learned what fits.** The anchor tables say where a stack is
hung; they cannot see how wide it is, and width is what left the cell — three
marks side by side in house 9 measured 104 user units in a cell 73 across, and
four degree labels in the 12th ran through the diagonal into house 1. The
anchors were right and the plate was wrong the whole time.

`app.plate_layout` now decides the arrangement from the polygons, falling back
one step at a time — glyph+letters+degree, then letters+degree, then
glyph+letters, then letters — and packing marks onto as few rows as fit.
Advance widths are **measured in a browser**, not estimated: an estimate that
ran 20% generous dropped cells that had room, and one that ran short would
draw a label into the wrong house.
`test_no_label_overflows_its_cell_in_a_browser` reads the real `getBBox()` and
checks all four corners of every label against the polygon it belongs to;
`test_the_fit_estimate_is_never_optimistic` guards the calibration.

### 6. Every division is wired

D1, D9 and D10 render. D2, D3, D7, D12, D16, D30 and D60 are named, described
and drawn as dashed empty frames. The gallery is generic over
`vargas.SUPPORTED`: adding a sign function to that registry is the whole of
what it takes to light a division up, and
`test_every_computed_varga_is_plotted` fails if a computation lands and the
gallery does not plot it.

### Two things worth writing down

**The template drew at a size the layout had not reserved.** The plate's type
sizes were literals in `app.py`, where the fit is computed, *and* in the
template, where the text is drawn. Raising `MINI_SIZE` to clear the
legibility floor changed what `plate_layout` reserved room for and not one
pixel of what rendered — the glyphs stayed at 26 units and stayed illegible,
and every gate passed. They come from the context processor now, and
`test_the_template_draws_at_the_size_the_layout_reserved` fails on a bare
pixel size in the plate macros.

**`str.replace("", x)` inserts between every character.** A scripted edit took
`s[s.index(a):s.index(b)]` where `b` occurred *before* `a`, got an empty
slice, and grew `templates/index.html` from 89KB to 258MB. Recovered exactly
by splitting on the inserted block and rejoining — 89,000 insertions for
88,999 characters, which is the arithmetic that proves the reconstruction is
the original. Anchored edits, not computed slices, for anything structural.

**Tests:** 525 passed.

## Five screens: Today, Readings, Your charts, Explore, Ask ✅ (2026-09-11)

The dashboard was one long arrival page. It is five peers now, reached from a
tab row in the masthead, with two-level folios — `P. 02·1` is the first
reading, `P. 03·2` the second plate.

### Today (new)

`today.py` composes three or four dated lines from the ephemeris. The ledger
knew a transit was inside 3° of a natal point and knew when a planet changes
sign; it did **not** know when a contact *ends*, because the orb has no
boundary in the fact. `contact_window()` finds both edges the way
`next_sign_ingress` finds a sign boundary — coarse scan, then bisect to the
hour. Without that date the line reads "Ketu is on your Venus", which is the
vague register the doctrine exists to refuse.

The plate is pinned beside it with today's transits ticked around its
**outer** edge. Inside the frame they collided with the plate's own sign
numerals at every width, which `TestNothingOverlaps` caught immediately; the
D1 viewBox is widened to `-30 -30 360 360` and the ticks live in the margin.

Two faults found only by reading the rendered screen:

- **Every ingress line was generic.** "The Sun moves into Virgo on the 17th,
  carrying authority with it" is true of every reader alive, under a heading
  that reads *Today for this chart*. Each line now names the part of **this**
  chart the sign is — Whole Sign from the lagna, in plain words, never by
  number. `test_a_sign_change_is_told_against_this_chart` recomputes the house
  from the chart and asserts the line carries it; **verified red** against the
  old wording.
- **On a phone the day was ~1000px down.** Arrival on a 390px screen showed a
  wheel and nothing else, because the plate came first in source order. The
  leaf is a flex column below 1000px with `.daycol { order: -1 }`.

### Your charts (new)

D1, D9, D10 as small plates; D2, D7, D12, D30, D60 as dashed empty frames
marked *in preparation* — listing only the three that exist would imply the
list is complete.

Each opens to its own page with a reading composed from that division's own
placements: the lagna lord and where it stands, which planets keep their sign
into the ninth, what occupies the tenth of the tenth. The first version showed
the plate and the gallery's one-line summary, which says what a Navāṃśa *is*
and nothing about this one — a gallery of charts with no reading is a filing
cabinet. `test_a_plate_reading_is_computed_not_canned` casts a second chart
and asserts the three readings differ, because a constant would satisfy every
other assertion.

The plate on its own page is a figure at the measure of its column (560px),
not the 900px breakout `.kundli` takes by default — measured; it had been
arriving twice the size of the title above it.

### Readings

IA unchanged. The contents used to start at **02**, because entry 01 was the
day's glance sitting above it on the same screen; with Today its own fold the
list read as a page missing its first line. The numbers are the folios the
entries open, and the two that leave the fold entirely are unnumbered.

### Repairs along the way

- A template slice taken with `split("\n")[6:]` cut mid-block, leaving a
  duplicated `<p class="readlong">`, a dangling `</details>`, and 26 `<section>`
  against 27 `</section>`. The pañcāṅga strip and the three-pane glance are
  back inside a real `<section class="glance">`.
- `TestEditorialDossier.measured` was measuring `#view-arrival` for `.dcard`,
  `.identity` and `.statement` — all of which had moved to Readings, so it was
  reading zero-height rects and passing for the wrong reason. It navigates to
  `#readings` now, captures the plate strokes on arrival first (asserting the
  set is non-empty), and measures the display hero that fold actually has.

**Tests:** 483 passed.

## The collision, the hierarchy, the index, and verdicts that name something ✅ (2026-09-10)

Four findings from a live walk. All four fixed, each with a gate.

### 1. The arrival collision was a NAME, not a layout

The headline and identity strip rendered on top of the pinned plate. Measured
rather than reasoned about: `.identity` sat at `x=160` — column 1, under the
plate — while `.glance` sat at `x=748`.

**The cause was a class/id collision.** The leaf's second section is
`class="chartof" id="glance"`; a *different* section is `class="glance"`. The
rule `.leaf > .glance` placed the wrong one, so the headline block was never
placed and grid **auto-placement** dropped it into the plate's column. It only
showed once the page scrolled, which is why every screenshot had missed it.

Every leaf child is placed explicitly now. That is the second time a name
collision has bitten this file — `.pane` was the first.

`TestNothingOverlaps` walks 4 widths × 4 scroll positions × 4 views. Getting
it to mean anything took three passes: a closed `<details>` lays its content
out and hides it with `content-visibility` (37 phantom collisions); an inline
element that wraps returns a bounding box spanning every line it touches (4
more); and a sticky bar with an opaque background is a deliberate overlay, not
a collision — a rule that still catches the plate, which is sticky with no
background. **Verified red: restoring the old rule fails it with 50
overlaps.**

The ☾, ॐ and 36 watermarks are gone — the only elements drawn on top of text
by design. I offered to cut them two rounds ago; the "nothing overlaps" rule
settles it.

### 2. The type hierarchy was upside down

| | before | after |
|---|---|---|
| fold title | 27–36px | **clamp(44px, 7.2vw, 72px)** |
| verdict | 34–52px | **clamp(22px, 2.35vw, 30px)** at 52ch, 1.35 |
| folio numeral | in flow, behind the title | upper corner, clear |

### 3. Explore is an index, not a dump

Eight categories, each with a one-line description at 16px, each opening into
its own fold. No fold shows two categories at once; inside one, body is 16px
and tables 15px with real row spacing.

**The sections were not moved.** They carry a `data-cat` and the CSS does the
showing — a first attempt that moved the blocks cut through the Jinja
conditionals wrapping several of them and four sections stopped rendering.

Two bugs of my own on the way: I used `data-cat` for both "this section
belongs to X" and "this link opens X", so the hide rule hid the index's own
rows and it rendered with nothing on it; and two untagged blocks leaked onto
the index. A gate now asserts nothing in Explore is untagged.

### 4. Verdicts name something

`voice.py` gained a **vagueness** list. *"Work and money is one of the
stronger parts of your chart — the planet that rules it is strong"* passed
every existing gate and said nothing. A verdict now names at least one graha
and, where a dated influence runs, says when:

> **Work and money asks real work: Saturn, the planet of labour, sits at its
> weakest. The north node's period holds it until Aug 2029.**

Budgets unchanged — that is 15 words against a 20-word cap. Dates are checked
against the ledger, the same rule the agent's validator enforces.

Three writing bugs found by looking: `"the the north node period"` (the plain
form already carries its article), `"moolatrikona"` reaching the plain layer
(Sanskrit, banned there), and the balance clause itself being the vaguest
thing on the page.

`pytest` → **462 passed** (external 70 · invariant 302 · characterization 80).

## The light paper almanac, and the scroll choreography ✅ (2026-09-09)

An approved Claude Design mockup moved the app to **light paper** and asked
for a scroll choreography. Re-skin and staging only: the IA, the verdict-first
voice doctrine, the word budgets and the validator are untouched, and
`TestDomainRestructure`, `TestEditorialDoctrine` and `TestPaperPalette` all
pass together, which is the proof.

### Contrast was computed, not chosen

The brief flagged one pair and was right about it: **`#b68235` on `#f3f2f2` is
3.02:1** — enough for graphics and large display (AA for non-text objects is
3.0), and **not** enough for a link. On the surface tone it is 2.78:1 and
fails outright.

So the bronze **splits by role**: `--accent` `#b68235` draws the plate and
sets large display; `--accent-ink` `#8a5f1c` — the same hue at 36°, darkened
until it clears — takes links and every text below 24px at **5.03:1** on paper
and **4.64:1** on surface. Every muted ink step was recomputed too; the floor
is **4.73:1**. `TestPaperPalette` reads the hexes back out of
`static/style.css` and recomputes all of it on every run, so a future tweak
that lightens the bronze fails here rather than in someone's eyes.

Six palettes became two — **Paper** and **Night reading**. A browser still
holding a retired palette name falls back rather than rendering an undefined
theme, which would have left the page unstyled.

### `--ink` changed meaning, on purpose

It named the **ground**; it names the **text** now, with `--paper` as the
ground. That is the honest naming for a paper-first design, and it was a
mechanical rename over 743 lines — including 23 hardcoded `rgba(236,229,216,…)`
literals that became `rgba(var(--ink-rgb), …)` so they follow the theme.

The gate that used to catch *"text painted the same colour as the page behind
it"* — a real bug that once shipped three invisible buttons — **follows the
new name** instead of retiring.

### Two external gates had to be re-anchored

`test_design_handoff_pastel_tokens` and
`test_framework_six_palettes_by_root_attribute` are declared `external`,
meaning they answer to `DESIGN-HANDOFF.md` rather than to the build. An
approved design supersedes that document, so **the document was updated first**
and the gates now answer to its new token table. They were not deleted: an
external gate whose source changed should follow the source, or it stops
meaning anything. The framework gate is in fact stricter now — it also fails
if any component carries a palette hex directly.

### The choreography

Six moves, one duration (620ms), one curve. Fold rules **draw in** left to
right; the plate **pins** beside the day's verdict and **releases at the last
contents entry** (no JavaScript decides that — the sticky column sits in a
grid that ends there); a **ghost folio numeral** at 12% ink carries down-leaf
with the title overlapping it; each domain opens on a **full-viewport verdict**
that rises 22px (8px on a phone); the working then **fades in as one block**
in two columns. CSS scroll-driven animation where the browser has it, an
IntersectionObserver everywhere else, both ending at the same final state.

**`prefers-reduced-motion: reduce` turns all of it off and keeps the pin** — a
sticky element is layout, not motion, and dropping it would take the plate
away from the reading it belongs beside.

### Three things looking caught that reasoning did not

- **The plate rendered with no lines at all.** The token rename ran over the
  stylesheet but not the template, so `var(--accent-400)` stopped resolving
  and the wheel computed `stroke: none`. A DOM probe found it; a screenshot
  had already shown it. Rebuilt to the brief: ink frame and diagonals, one
  bronze line for the diamond, both in CSS so the two readings can restate
  them.
- **The ghost numeral left a 200px hole.** Absolutely positioned against a
  centring flex container it hung at the top of the screenful while the title
  centred below. It is in flow now with a negative bottom margin, so the group
  travels together at any viewport height.
- **Two pre-existing `infinite` animations** — a marching-ants dash and a
  pulsing ring on the plate's highlight layer. An engraved plate does not have
  crawling ants on it, and an animation that never ends is the one thing on
  the page a reader cannot scroll away from. The dash is static now; the ring
  pulses twice and holds.

### A gate that passed for the wrong reason

`TestReducedMotionInARealBrowser` went green **with the entire reduced-motion
block deleted** — because it measured the arrival view, where the revealed
elements sit inside hidden domain folds and were filtered out for having no
client rects. Every assertion passed vacuously. It now navigates to a domain
fold first and asserts it actually measured a `.reveal-rise` and a `.working`
before judging them. Re-verified: deleting the block now turns it red.

`pytest` → **443 passed** (external 70 · invariant 283 · characterization 80).

## The editorial dossier — a full visual redesign ✅ (2026-09-09)

Sidera calls itself *a Vedic almanac*. It did not look like one. This makes
the visual layer match the claim: typeset, numbered, printed matter with
unhurried pacing.

**Visual layer only.** The IA, the verdict-first structure, the word budgets,
the validator and every computed value are untouched. `TestDomainRestructure`
and `TestEditorialDoctrine` pass unchanged, which is the proof.

The direction was written first as
[`ui-design/DOSSIER.md`](ui-design/DOSSIER.md), reviewed against the brief for
genericness, and only then built.

### The typeface is the argument

**Tiro Devanagari Sanskrit** replaces Cormorant Garamond. John Hudson drew it
to set **Sanskrit**, and it carries three things this app specifically needs
and Cormorant could not supply:

1. the full transliteration range — `ā ṃ ś ṛ ṣ ṭ ṇ ḷ` — so *Navāṃśa* and
   *kṛṣṇa* set in one face instead of falling back mid-word;
2. the **Devanagari block itself**, matched to the same Latin design;
3. one upright weight, which is the right instrument for large, calm display
   setting. Bookfaces are set large and light; only advertising sets them
   heavy.

**IBM Plex Sans** takes the working text, chosen for true tabular figures —
what an ephemeris table actually needs — and a drawing-office neutrality that
leaves the display face as the only voice in the room. One Google Fonts
request, as specified.

### The structural signature — the rule goes ABOVE

Devanagari does not sit on a baseline. It **hangs from a headline**, the
śiro-rekhā drawn across the top of a word.

So every section marker inverts the Western convention: the rule is drawn
first and the heading hangs beneath it. One move, applied consistently, and it
is the thing that stops a hairline-and-small-caps layout from reading as a
newspaper. It comes from the writing system the subject is written in.

That is where the boldness is spent. Everything else stays quiet.

### What changed, concretely

| | before | after |
|---|---|---|
| domain cards | bordered app-cards, two-up at 560px | a numbered contents page, one column, hairline-ruled |
| the wheel | a screen graphic, 1.8px strokes | **Plate I**, 0.75px, captioned with its cast date and ayanāṃśa |
| expanders | chunky accordions | footnote lines: `show the working ↓` |
| tables | rule under every row | printed ephemeris: rule under the head only |
| boxes | 24 bordered rectangles | **2**, both earned — the city dropdown floats over text, and the two score rings are circles |
| verdict / body ratio | 27 / 15 px | 40 / 15.5 px on desktop |

### The one place the brief and an existing test disagreed

`test_the_card_grid_is_one_column_on_a_phone` pinned the domain grid going
two-up at 560px. A contents page is a single column at every width — rules
*between* entries only work down one column, and that is what makes it read
as a contents page rather than as cards with lines on them. The test is
re-pinned to the contents-list contract and now also forbids any width
reintroducing a second column. **No IA changed**: the same seven
destinations, in the same order, behind the same links.

### Caught by looking rather than reasoning

- The footnote marker `show the working ↓` is a CSS `::after`, and it landed
  on the **"Ask about this in your own words"** fold too, because that fold
  shares the `.dstep` class. That silently changed what the app says — out of
  scope for a visual pass. Scoped to summaries that carry a step count.
- The printer's device (ॐ) was cropping off the top-right corner. An
  almanac's device sits whole on the page; resized and inset.
- The colophon was set at .4 opacity on a mid-tone ground — below any
  reasonable contrast floor, and it carries the AGPL source link the licence
  requires. Lifted to `--cream-60`.

### Measured, not eyeballed

`TestEditorialDossier` adds 17 gates, six of which drive a real browser at
390px and 1280px: no horizontal overflow, the contents page is one column at
both widths, every entry clears the 44px tap target, both faces actually
load, the display type really is ≥1.8× the body, the folio stays on the page,
and the imprint is still exactly three lines.

Four of those seventeen failed on first run — **all four were my test bugs,
not design faults**: a `preconnect` hint counted as a stylesheet request, an
HTML-escaped `&amp;`, a `paint-order` text halo judged as a drawn stroke, and
a line count that divided a mixed-size block by one line-height.

`pytest` → **415 passed** (external 70 · invariant 255 · characterization 80).

## Answer first, one breath, then the working ✅ (2026-09-09)

**From the founder's live walk.** The app over-explained and buried the
answer — the same over-hedging disease the readings are built to avoid, in
text form. Someone arriving with a question about their marriage was handed
three hundred words that opened on the word *"Mixed"* and never quite said
anything.

**This changes the ORDER and the ECONOMY of speech, not its honesty.** Every
fact id, rule citation, confidence label and validator check is untouched, and
`TestEditorialDoctrine` permits no sentence that was forbidden yesterday.

### The doctrine, as code

`voice.py` holds the budgets, the banned patterns and the checkers, so the
prose and the tests that police it cannot drift apart: answer first in one
breath · 20-word teaser, 120-word synthesis, 80-word agent lead · no
throat-clearing · one caveat, at the end, one line · plain register on top.

### Measured, before and after

| | before | after |
|---|---|---|
| domain synthesis, visible | 255–301 words | **73–90** |
| card teaser | 16–21 words, opening on "Mixed —" | **14–20**, opening on the verdict |
| signals shown | all of them, in the top layer | the sharpest; **all 59 still in the expanders** |

The marriage card used to read *"Mixed — a strong 5th lord and a debilitated
7th lord. Live now: Saturn on it until Jun 2027."* It now reads:

> **Marriage is more contested than helped — the planet that rules it is weak.
> Right now, Saturn is on it until Jun 2027.**

Same facts, same fact ids, same rules. The verdict is in the first clause, and
"5th lord" has moved one tap down to where it can be glossed.

### The plain register is a translation, not a dumbing-down

Each `Signal` now carries three registers: `text` (full, technical, for the
expander), `brief`, and `plain` (no Sanskrit, no house numbers, for the top
layer). An empty `plain` means the signal has no top-layer form and stays in
the working — which is the right answer for a supporting-house detail nobody
needs in the first breath. A test asserts the expanders still contain
"house", "lord" and "drishti", because an app that went plain all the way
down would have lost the thing that makes it checkable.

### Answer-first as structure, not as a habit

Three places where the doctrine is now a property of the shape rather than
something to remember:

- **The caveat is a field**, not a sentence buried in prose. "One caveat, at
  the end" is enforced by there being exactly one slot for it.
- **The agent's `verdict` is a required schema field.** A model cannot forget
  it or bury it mid-paragraph if the reply will not validate without it. Its
  style section is rewritten around *"answer like a confident astrologer in
  two sentences, then show the working."*
- **The verdict is validated exactly as the answer is.** The headline is the
  worst possible place for a claim to escape, so it is folded into the same
  prose the validator reads. A test moves a certainty into each field in turn
  and asserts both are caught.

### Also fixed, and worth naming

The withheld message opened on the word *"Withheld"* and put the one useful
sentence — what to ask instead — last, behind an explanation of our own
machinery. It leads with the action now. The deterministic `/ask` lenses led
with their own scoring (*"The strongest agreement (75%) points toward…"*); the
finding opens the sentence.

**Two things the tests caught that I had not:**

- The **"Explore the full chart" card** read *"Grahas, daśās, the timeline,
  transits, yogas, doshas…"* — the arrival screen, the most-read surface in
  the app, written entirely in Sanskrit. It tells a newcomer nothing.
- My **first banned-phrase pattern was too greedy**: unanchored `before i`
  flagged the innocent word "before it" in the app's own copy. Openers like
  "First," and "That said," are only throat-clearing where a sentence begins,
  so they are matched there and nowhere else. A test now asserts both halves —
  that the list catches eleven real offenders, and that it fires on none of
  seven honest sentences the app should keep saying.

**Verified red before being kept:** restoring the old verbose, hedged
synthesis fails **4** gates independently — preamble, budget, throat-clearing
and jargon.

`pytest` → **398 passed** (external 70 · invariant 238 · characterization 80).

## The birth fields stop following the viewer's system locale ✅ (2026-09-08)

**Reported live.** On sidera.onrender.com, macOS Safari with a 12-hour system
clock rendered the birth-time field with am/pm segments and answered a typed
`13` with *"Invalid value"*.

### The diagnosis, and a wrong guess corrected

The suspicion was that the restructure had created a second form template and
the fix was landing in the wrong one. It had not: `templates/index.html` is the
only template in the repo, and the restructure re-homed sections *inside* it.

The truth was simpler and worse — **the masked field had never existed here**.
Every commit since `eb03cc6` served `<input type="time">`, checked one by one.
The diagnosis was made against the *rendered* page, not the source: the app was
run from the public repo at the deployed commit and `/` fetched.

### Why the previous fix was the opposite of this one

`eb03cc6` deliberately *chose* the native picker, and for a real reason. The
field before it was `type="text" inputmode="numeric"` with **no mask**, which
hands a phone a digits-only keypad with no colon key — a required field no
mobile user could fill. That was found in a live smoke-test too.

So the two failures pull in opposite directions:

| | native picker | text + numeric keypad |
|---|---|---|
| macOS Safari, 12-hour clock | `13` rejected | fine |
| any phone | fine | **no colon key — untypeable** |

**Masking satisfies both, and nothing else does.** The field types the
separator itself: `1312` becomes `13:12`, `25031994` becomes `25/03/1994`.
Digits alone are now a complete answer, so the numeric keypad is safe *because*
of the mask. The replacement test pins the two together, since dropping either
one resurrects one of the two bugs.

### The date field had the worse version of the same bug

`<input type="date">` renders MM/DD in a US locale and DD/MM elsewhere. Nobody
saw an error: **the same keystrokes cast two different charts.** `03/04/1990`
was 3 April to one visitor and 4 March to another. Now one stated order —
day-first — parsed identically for everyone, with the order on the field and a
refusal that names it when a month-first date arrives.

ISO stays accepted: the agent panel re-posts `YYYY-MM-DD` with every question,
since no birth record is held server-side. The shapes cannot collide — ISO
leads with four digits, day-first with at most two.

### The guard is a browser, because the bug was a browser

Markup assertions prove the attributes are right. They cannot prove Safari
rejects a typed `13`. `TestMaskedBirthFieldsInARealBrowser` drives the rendered
form in Chromium under `en-US` / `America/Los_Angeles` — the locale that
produced the report — and types, reads back, and submits.

**Verified red before being kept:** restoring `type="time"` on `#time` alone
fails **7** tests, including the browser reproducing the original bug — typing
`13` into the native control does not yield `13`.

A skipping test guards nothing, so the fixture falls back to any chromium on
the box (`SIDERA_CHROMIUM`, `PLAYWRIGHT_BROWSERS_PATH`, the usual system paths)
before it skips.

Playwright went into `requirements.txt` first — and that would have added
**142 MB to every Render build** for a package the app never imports. It now
lives in `requirements-dev.txt`, `test_hygiene` pins both files, and a new
assertion fails if playwright ever reappears in the production install.

### Two existing guards caught me mid-fix

The hint example was first `16/08/1998` — which is the fixture chart's own
birth date. `test_birth_form_renders_blank_and_universal` failed twice over it,
once for the hint and once for the same date inside a JS comment that ships to
the browser. The example is now `25/03/1994`, where the day is over 12 and so
shows the order at a glance.

`pytest` → **378 passed** (external 70 · invariant 218 · characterization 80).

## Domains, not techniques — the dashboard restructure ✅ (2026-09-08)

**The problem.** Seventeen sections in a flat scroll behind a sticky bar of
fourteen links: Glance · Chart · Daśās · Timeline · Transits · Doshas · Myths ·
Yogas · Match · Ask · Agent · Paṭha · Grahas · Learn. Every one of those is a
*technique*. Someone arrives asking about their marriage and is handed a filing
cabinet organised by method — all the information present, none of it addressed
to them.

The spec was written first, as
[`ui-design/RESTRUCTURE.md`](ui-design/RESTRUCTURE.md), so the decision is on
record independently of what got built.

### Three views on one page

**Client-side panes, not routes.** Sidera stores no birth record between
requests — it is posted, the chart is cast, nothing persists. A server route
for `/domain/marriage` would mean re-posting birth details on every tap. So all
three views render once and the browser switches, with `#hash` deep links,
`history.pushState`, `popstate`, scroll-to-top and focus movement.

| View | What it holds |
|---|---|
| **Arrival** | the wheel · a three-line identity strip (lagna · Moon and nakṣatra · running MD/AD) · the Glance verdict · seven cards |
| **Domain** ×5 | the synthesis first, then the six-step working as expanders, each row naming its fact ids |
| **Explore** | all nineteen technical sections, unchanged, behind the existing sticky nav |

Nothing was deleted. Everything was re-homed.

### The card teasers had to be real

A card that says "Love & Marriage →" and nothing else is a menu, not a reading.
Each card carries a **one-line condition drawn from the domain's own checklist**
— the same checklist `/ask` works through. On the fixture chart the marriage
card reads *"Mixed — a strong 5th lord and a debilitated 7th lord. Live now:
Saturn on it until Jun 2027."*

### No language model writes readings — including these

The core dashboard must work with no API key, and the domain synthesis **is** a
reading, so it could not be handed to the agent. `domainread.py` (378 lines)
composes it deterministically from the same ledger facts the agent cites:
support and strain weighted per house from the lord's dignity and placement,
the drishti falling on the house, occupants, the karaka's condition, the varga's
confirmation or contradiction, whether the running MD/AD lord touches the
domain, and which slow transits occupy **or aspect** it, with dates. It reports
condition, never outcome. The agent stays optional and additive: where
configured, "Ask about this" runs the full six-step synthesis; where not, the
deterministic reading stands alone and the panel says so.

### A collision worth recording

The chart plate has used `class="pane"` for its D1/D9/D10 tabs since Phase 6.
Naming the three new view containers `.pane` made the view switcher hide
`#pane-d1` — the wheel, the first thing anyone sees. Renamed to
`.view` / `#view-*` / `data-view`, and
`test_the_view_switcher_does_not_capture_the_plates_own_panes` now pins it. The
test was verified red under the restored collision before being kept.

Separately: a downscaled screenshot led me to conclude briefly that the wheel
was not rendering at all. It was. `getBoundingClientRect` in the browser
(`#pane-d1` at 353px, SVG at 304px) settled it, and a tightly-clipped
screenshot confirmed. Measure, do not squint.

### Measured, at 390px and 1280px

| | 390px | 1280px |
|---|---|---|
| horizontal overflow | none | none |
| identity strip | 3 lines (65.6px = 3 × 21.875) | 3 lines |
| cards | 7, one column, 342 × 122px | 7, two columns, 291 × 162px |
| smallest tap target | 122px — well over the 44px floor | — |

The grid is one column then **two**, not three: the body is capped at 640px by
the existing layout, so a third column would only narrow the cards. The spec
said three; the measurement said two, and the spec now carries the correction
rather than hiding it.

**Tests:** `TestDomainRestructure` — 21 tests, declared `invariant`.
`pytest` → **367 passed** (external 70 · invariant 207 · characterization 80).

**What this unblocks:** Milestone 2 (Ashtakavarga) was queued behind this
restructure. Its verdict-first presentation — strongest and weakest houses named
up front, the 12 × 8 grid folded under — now has an obvious home.

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
