# Handoff: Sidera — Vedic Astrology App

## Overview
Sidera is a mobile Vedic astrology app: daily reading (panchanga-based), North-Indian natal chart (kundli), transits (gochara), compatibility (Guna Milan / Ashtakuta), a learn/chant page, onboarding and profile. The design explores several Home directions plus a full screen flow in a dark "Colophon" direction, and a final concise "expand-on-selection" pattern.

## About the Design Files
The files in this bundle are **design references created in HTML** — prototypes showing intended look and behavior, not production code to copy directly. The task is to **recreate these designs in the target codebase's environment** (React Native, Flutter, SwiftUI, etc.) using its established patterns and libraries — or, if no app codebase exists yet, choose the most appropriate mobile framework and implement the designs there.

`Astrology App.dc.html` renders as a design-review canvas: multiple phone mockups grouped by iteration turn (newest at top). Each mockup carries a visible id badge (1a…5a). Open it in a browser to inspect; the desktop canvas chrome (headers, labels) is NOT part of the app design — only the phone frames are.

## Fidelity
**High-fidelity.** Colors, typography, spacing and copy are final-intent. Recreate pixel-perfectly, substituting real computed astrology data for the sample data (sample persona: Aisha Rao, 14 Aug 1998, 04:32, Jaipur — Simha lagna, Moon in Rohini pada 2, Shani mahadasha).

## Direction chosen
- App-wide visual direction: **1c "Colophon"** (dark ink screens) — full flow in screens 2a–2e, 3a.
- Home/Today pattern direction: **turn 4/5 "concise, expand on selection"** — final merged candidate is **5a (light paper)** and **4b (dark)**; both share the same structure.
- Active palette: **Pastel** (see Design Tokens; five alternates included).

## Screens / Views

All phones: 340px wide frame, 36px corner radius (device bezel only — app screens are edge-to-edge, no rounded content cards). Status bar: 12px/24px padding, 13px 600 body font. Bottom tab bar: 5 items (Today, Chart, Transits, Match, You), top hairline divider, active item in accent, inactive at 50% opacity.

### Header pattern (all screens)
App/screen name left in Cormorant Garamond 600 19px, letter-spacing .04em; right-side meta in Lora 10px uppercase, letter-spacing .1em, 50% opacity. Bottom hairline: 1px, 14% opacity (dark) / divider token (light). Padding 14px 24px 12px.

### 5a — Home / Today (light, FINAL candidate)
- Hero block, padding 30px 26px 22px: kicker "TUE 11 JULY · KRSNA CATURTHI" (Lora 10px, ls .14em, uppercase, accent-700); statement in Cormorant 400 27px/1.22, key phrase tinted accent-700; italic underlined text link "Read the full day" (12px).
- Ghost glyph "☾" behind hero: Cormorant 120px, ~11–16% alpha accent (`--pal-ghost`), top-right, no pointer events.
- Chip row (3 equal chips, 8px gap): Cormorant 600 13px, ls .05em, 8px vertical padding, square corners, 1px border. Inactive: divider border, 65% text. Active: accent bg, surface-color text.
- Panel below chips (min-height 196px, 1px divider border, surface bg): swaps by selected chip —
  - Chart: 140px kundli SVG + caption "Simha 11°04′ · Candra in Rohini p.2" (11px, tabular numerals)
  - Transits: 4 ledger rows "date — event", 42px date column, hairline separators
  - Match: 76px circle (1px accent border) with score "28½/36", name "Aisha ✕ Aarav" + 2-line summary
- Only one panel visible at a time; chip selection is instant swap.

### 4b — Home / Today (dark twin of 5a)
Same structure on ink background. Cream text #ece5d8; hairlines rgba(236,229,216,.10–.18); chips active = accent-300 bg with ink text.

### 4a — Home alternative: "Ledger" accordion (dark)
Title block, then 4 rows (The reading / Panchanga / Grahas / The chart). Row: title Cormorant 600 16px + 1-line summary (10.5px, 50%), "+/−" toggle in accent-300 Cormorant 22px. One open at a time; opening one closes the last. Bodies: justified 12.5px paragraph; 4 bordered panchanga cells; 3-row graha ledger; 150px kundli SVG.

### 4c — Home alternative: "Contents" index (light)
Numbered folios 01–04 (numeral in accent, Cormorant 15px tabular), title Cormorant 600 17px, +/− toggle. Bodies indented 33px to align past the numeral.

### 1a / 1b / 1c — earlier Home directions (reference)
1a light "Almanac": justified reading + graha table + small chart plate. 1b "Celestial plate": 300px photographic sky hero (user image slot), gradient scrim, serif overlay, reading pull-quote, chart plate row, match card. 1c dark "Colophon": centered 212px kundli with giant ghost numeral "5", 4-cell panchanga strip (hairline-boxed), graha ledger with degrees. These remain in the file for provenance.

### 2a — Onboarding (dark)
"Cast your kundli" intro (Cormorant 34px), explainer 12.5px, underline-field form: NAME / DATE OF BIRTH + TIME (row, flex 1.4/1) / PLACE OF BIRTH with lat-long right-aligned. Labels 9px uppercase ls .14em 50%; values Cormorant 19px, cream, 1px bottom border 22% opacity. Link "Birth time unknown?" italic underlined. CTA: full-width outlined button (1px accent-300 border, accent-300 text, Cormorant 600 15px, 13px pad) — no fill. Footnote 10px 40%: "Sidereal · North-Indian · used only to cast your chart". Step marker "STEP 1 OF 2" in header.

### 2b — Natal chart (dark)
Segmented control Rasi / Navamsa / Chalit: 1px hairline box, active segment = accent-300 fill with ink text, Cormorant 600 13px. 224px kundli. Beneath: "Lagna Simha 11°04′" and "Candra Rohini p.2" (11px). Vimshottari dasha ledger: current mahadasha row in accent-300, antara rows indented with "·", right column dates, hairline separators.

### 2c — Transits / Gochara (dark)
Week strip: 7 equal columns, day label 9px, date Cormorant 15px; event days get 3px accent dot; today outlined 1px accent-300. Fortnight ledger: date column 44px, event text 13px, current event in accent-300. Standing-condition card: 1px hairline box, "SADHE SATI · YEAR 3 OF 7½" kicker in accent-300 + 12px explainer.

### 2d — Guna Milan (dark)
Names "Aisha ✕ Aarav" Cormorant 20px; nakshatra line 10.5px; ghost "36" numeral behind. Score: 104px circle, 1px accent-300 border, "28½" Cormorant 34px + "/36" 12px. Verdict line italic Cormorant 14px. Ashtakuta ledger: 2 CSS columns, 8 rows "kuta — score/max", weak kuta (Nadi 4/8) highlighted in accent-300. Footnote on Mangal dosha at 11px 55%.

### 2e — Profile (dark)
Ghost initial "A"; name Cormorant 30px centered; birth-data line 11px tabular. 3-cell strip: Lagna / Candra rasi / Nakshatra (nakshatra value in accent-300). Settings ledger rows: Ayanamsha (Lahiri), Chart style (North Indian), Daily reading (6:00 AM), Saved people (3) — 13px, chevron "›" right at 55%. "Sign out →" in accent-300.

### 3a — Learn / "Patha" page (dark)
Reachable from Chart/Today. Ghost "ॐ" glyph. Title "The sky you were born under" Cormorant 30px. 3 entries (Lagna / Nakshatra / Dasha): heading row = term Cormorant 600 15px + value chip in accent-300 11px right; body 12px/1.6 justified at 62% opacity. Chant card: 1px accent-300 border, centered — kicker "YOUR CHANT · CANDRA MANTRA" 9px accent-300; Devanagari "ॐ सोमाय नमः" Cormorant 26px; transliteration italic 13px 70%; instruction 10.5px 55% ("108 repetitions, Monday at dawn, facing north-east…").

## Interactions & Behavior
- Tab bar: 5 tabs, active = accent tint. Screens: Today(4b/5a), Chart(2b), Transits(2c), Match(2d), You(2e); Learn(3a) pushed from Chart or Today.
- Accordion (4a/4c): tapping a row toggles it; opening a row closes the open one (exclusive). Toggle glyph swaps "+"/"−". Recommend 200–250ms ease-out height transition (mockups swap instantly).
- Chip panel (4b/5a): exclusive selection, instant panel swap; keep panel min-height 196px to prevent layout jump.
- Chart segments (2b): swap chart data D-1/D-9/Chalit.
- Onboarding: place field geocodes to lat/long (shown right-aligned); "Birth time unknown?" leads to a no-time fallback flow (chandra-lagna based).
- All ghost glyphs: pointer-events none, user-select none.

## State Management
- `palette`: app-wide theme enum (pastel | sindoor | gold | twilight | rose | verdigris).
- Home accordion: `openSection: int|null` (exclusive).
- Home chips / chart segments: `selected: enum`.
- User profile: name, birth datetime, birth place + lat/long, ayanamsha, chart style, notification time, saved people.
- Derived (from ephemeris engine, sidereal/Lahiri): lagna, moon rasi/nakshatra/pada, graha positions + retrograde flags, panchanga (tithi/nakshatra/yoga/karana/paksha), vimshottari dasha stack, gochara events, sadhe-sati status, guna-milan scores per kuta.

## Design Tokens
Fonts: **Cormorant Garamond** (headings; 400/500/600 + italic) and **Lora** (body; 400/600 + italic) — Google Fonts. Tabular numerals (`font-variant-numeric: tabular-nums`) on all data.

Type scale (px): 9/10 uppercase kickers (ls .1–.16em) · 11–13 body/ledger · 15–17 row titles (600) · 19–20 screen title · 26–34 display · ghost glyphs 120–150.

Spacing: screen gutter 24–26px; ledger row padding 6–11px vertical; hairlines 1px everywhere. Square corners throughout (only circles: score rings; only rounding: device bezel).

Dark-screen constants: text #ece5d8; hairlines/borders rgba(236,229,216,.10/.14/.18/.22); muted text at .5–.7 alpha.

Palettes (light-screen tokens + dark ink; accent-300 is the dark-screen accent, accent/accent-700 the light-screen accents):
- **Pastel (default)**: bg #f6f2f7, surface #fcfafd, text #4a4553, accent #a99bc9, accent-300 #cfc4e4, accent-700 #8173a6, ink #585270
- Sindoor: bg #f4eee8, text #2b1d18, accent #a8402f, accent-300 #dd9a84, accent-700 #7a2c1a, ink #251512
- Gold: bg #f3f0e9, text #26211a, accent #b68235, accent-300 #dcb877, accent-700 #815b23, ink #211c17
- Twilight: bg #eeedf3, text #211f2b, accent #5d58a6, accent-300 #a09bd2, accent-700 #413c78, ink #1a1826
- Rose: bg #f3ecee, text #2b1f26, accent #9d5578, accent-300 #cd9bb4, accent-700 #763f5a, ink #241823
- Verdigris: bg #e8efeb, text #1b2622, accent #3f7d6a, accent-300 #8dbdad, accent-700 #2d5b4c, ink #16221d
Ghost-glyph color: accent at ~11% alpha (16% for pastel).

## Kundli (North-Indian chart) spec
Fixed-house diamond: outer square + both diagonals + inscribed diamond (midpoint-to-midpoint). Houses fixed, signs rotate: house 1 = top-center diamond, then counter-clockwise. Stroke 1.6–1.8px in accent (accent-400 on dark, accent on light); rasi numerals Cormorant ~15px at 42–50% text alpha; graha abbreviations (As, Su, Mo, Ma, Me, Ju, Ve, Sa, Ra, Ke) Lora 600 13–14px in accent-300 (dark) / accent-800 (light), middle-dot separated when conjunct (e.g. "Ve·Mo"). Sample placement: As·Ke H1, Su·Me H12(top-left), Ma H8 area, Ju H9, Ra H11, Ve·Mo H2, Sa H3 — replace with computed positions.

## Assets
- No raster assets. Kundli charts are inline SVG (spec above).
- 1b's sky hero is a **user-image slot** (night-sky photograph, cover-fit, 300px tall, dark gradient scrim top+bottom). Source a licensed photo in production.
- Glyphs ☾ ॐ ✕ ℞ › are text characters, not icons. Tab icons in 1b: 1.5px-stroke 18px line icons (sun, diamond, calendar, heart, person).

## Files
- `Astrology App.dc.html` — all mockups (canvas doc; phone frames are the design). Open in a browser.
- `_ds/styles.css` — Classical design-system tokens the canvas loads (base palette, type, hairline/table/button classes).
- `image-slot.js`, `support.js` — mockup runtime helpers only; not part of the design.
