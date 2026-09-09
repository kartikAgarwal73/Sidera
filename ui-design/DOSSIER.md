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

## Tokens

### Colour — one ground, one ink, one accent

The six palettes stay and keep their stored values; what changes is
**discipline**, which is what the brief actually asks for: *one accent, used
only for verdict emphasis and links.*

| Token | Role | Pastel (default) |
|---|---|---|
| `--ink` | the ground. Legacy name — it is the paper | `#585270` |
| `--cream` | the ink laid on it | `#ece5d8` |
| `--accent-300` | THE accent. Verdict emphasis and links, nothing else | `#cfc4e4` |
| `--accent-400` | plate strokes only — the engraver's line | `#bcafd7` |
| `--divider` / `--hairline` | rules | cream at .14 / .10 |

`--accent` and `--ghost` remain defined because the framework gate requires
the full ramp on every palette, but they are no longer painted onto ordinary
UI. Decorative gradients were already banned by
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
| Verdict | 30px | 40px | Tiro, 1.18 leading |
| Page title | 26px | 34px | Tiro |
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
