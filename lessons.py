"""Learn-as-you-go: 60-second micro-lessons.

A 20-card literacy path from "what is a lagna" to "read your own D9",
plus a contextual index mapping dashboard sections to the card that
explains them. Each body is sized for a ~60-second read.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Lesson:
    number: int  # 1–20, path order
    key: str
    title: str
    body: str


LESSONS = [
    Lesson(1, "lagna", "What is a lagna?",
           "Stand outside at the moment of a birth and face east: one of the "
           "twelve signs is climbing over the horizon. That sign is the "
           "lagna — the ascendant. It is the fastest-moving part of a chart "
           "(a new sign rises roughly every two hours), which is why the "
           "birth time matters so much. The lagna anchors everything: it "
           "becomes house 1, the chart's 'self', and every other house is "
           "counted from it. Same planets, different lagna — a different "
           "chart entirely."),
    Lesson(2, "kundli", "What is a kundli?",
           "A kundli is a map of the sky frozen at one moment, drawn from "
           "one place on Earth. Nothing mystical happens in the drawing "
           "itself: it records which sign held each of the nine grahas and "
           "which sign rose in the east. Everything else — houses, dashas, "
           "yogas — is a way of reading that single recorded sky. The whole "
           "map is fixed by three inputs: date, time, and place."),
    Lesson(3, "signs-houses", "Signs vs houses",
           "Signs and houses answer different questions. The twelve signs "
           "are fixed slices of the sky — they describe HOW a planet "
           "behaves, like the terrain it stands on. The twelve houses are "
           "areas of life — career, home, partnership — and they depend on "
           "the lagna, not the sky alone. A planet is always in one sign "
           "AND one house at once: Saturn in Pisces (sign) might be your "
           "4th house of home, or someone else's 10th of career."),
    Lesson(4, "whole-sign", "Whole Sign houses",
           "This app uses the oldest house system: Whole Sign. The sign "
           "that rises is house 1 — all thirty degrees of it. The next "
           "sign is house 2, and so on around the zodiac. No fractions, no "
           "unequal slices: each house IS a sign. When you read 'Mars in "
           "the 8th house', it means Mars occupies the eighth sign counted "
           "inclusively from your lagna sign."),
    Lesson(5, "grahas", "The nine grahas",
           "Vedic astrology tracks nine 'seizers': Sun, Moon, Mars, "
           "Mercury, Jupiter, Venus, Saturn — the seven visible movers — "
           "plus Rahu and Ketu, the Moon's north and south nodes. The "
           "nodes are not bodies but the two points where the Moon's path "
           "crosses the Sun's; they always sit exactly opposite each "
           "other. Each graha carries its own significations: the Moon "
           "the mind, Mercury speech, Saturn time and labour."),
    Lesson(6, "plate", "Reading the North-Indian plate",
           "The diamond-in-square chart keeps HOUSES in fixed positions: "
           "house 1 is always the top-centre diamond, then houses run "
           "anticlockwise. The numbers written in each cell are SIGN "
           "numbers (1 = Aries … 12 = Pisces), telling you which sign "
           "occupies that house. Planets are written into their houses by "
           "abbreviation. Tap any graha chip under the plate and the app "
           "will show its reach."),
    Lesson(7, "sidereal", "Sidereal, and the ayanamsa",
           "Western charts usually measure from the equinox point "
           "(tropical); Vedic charts measure against the fixed stars "
           "(sidereal). The two zodiacs drift apart by about one degree "
           "every 72 years; the accumulated gap — currently around 24° — "
           "is the ayanamsa. This app subtracts the Lahiri ayanamsa, "
           "India's official standard, from tropical positions. That is "
           "why your 'sign' here may differ from the one in a newspaper "
           "column."),
    Lesson(8, "retrograde", "Retrograde motion",
           "Planets never actually reverse; they only appear to, as Earth "
           "overtakes them or is overtaken — the same illusion as a "
           "slower train seeming to roll backwards. The chart marks these "
           "spells with an R. Classical texts read a retrograde planet as "
           "strong but inward or revisionary in expression. Rahu and Ketu "
           "move retrograde perpetually; for them it is simply their "
           "direction of travel."),
    Lesson(9, "dignity", "Dignity: own, exalted, debilitated",
           "Terrain matters. A planet in its OWN sign is at home and acts "
           "with full resources. In its EXALTATION sign it is honoured — "
           "at its strongest around one exact degree. Opposite that sign "
           "it is DEBILITATED: working uphill. Debilitation is never the "
           "end of the analysis — the texts immediately list cancellation "
           "conditions (Neecha Bhanga) that can restore, even amplify, "
           "the planet's results. The dignity column on the graha table "
           "shows each state."),
    Lesson(10, "nakshatra", "Nakshatras: the 27 moon-mansions",
           "Underneath the twelve signs runs a finer wheel: twenty-seven "
           "nakshatras of 13°20′ each — the distance the Moon travels in "
           "about a day. Each has a ruling deity, a temperament, and a "
           "planetary lord. Your Moon's nakshatra is the most personal "
           "point in the chart: it colours the mind itself and — "
           "crucially — its lord sets your dasha clock."),
    Lesson(11, "pada", "Padas: quarters of a nakshatra",
           "Each nakshatra divides into four padas of 3°20′. The pada "
           "refines the reading — and it is also the bridge to the D9: "
           "one pada corresponds exactly to one navamsa. Traditional name "
           "syllables for newborns are chosen by pada. When the app says "
           "'Rohini pada 2', it has divided the Moon's position twice: "
           "once by 13°20′, then the remainder by 3°20′."),
    Lesson(12, "moon", "The Moon's special role",
           "In Vedic practice the Moon is a second lagna. Many "
           "classical results — Gaja Kesari, Kemadruma, Sade Sati — are "
           "counted from the Moon's sign, not the ascendant. The Moon "
           "carries the mind, so transits relative to it describe felt "
           "weather. When a reading says 'the 10th from your Moon', it is "
           "using this lunar frame."),
    Lesson(13, "dasha", "Vimshottari: the dasha clock",
           "Dashas answer WHEN. The Vimshottari system assigns each graha "
           "a fixed number of years — Ketu 7, Venus 20, Sun 6, Moon 10, "
           "Mars 7, Rahu 18, Jupiter 16, Saturn 19, Mercury 17 — totalling "
           "120. Your starting point comes from the Moon's nakshatra lord, "
           "with credit for the arc already travelled: that is the 'birth "
           "balance'. The sequence then unrolls in fixed order for the "
           "rest of the cycle."),
    Lesson(14, "antardasha", "Mahadasha and antardasha",
           "Each mahadasha (major period) subdivides into nine "
           "antardashas in the same fixed order, each lasting the major "
           "period's length × the sub-lord's years ÷ 120. The first "
           "antardasha always belongs to the mahadasha lord itself. Read "
           "them as season and month: the mahadasha sets the era's theme, "
           "the antardasha inflects it. The ledger highlights where you "
           "are in both."),
    Lesson(15, "drishti", "Graha drishti: aspects",
           "Every graha 'sees' the 7th sign from itself — the full-strength "
           "gaze across the axis. Three get extra reach: Mars also sees "
           "the 4th and 8th, Jupiter the 5th and 9th, Saturn the 3rd and "
           "10th; the nodes are read with the 5th and 9th. Counting is "
           "always inclusive, sign to sign. Tap a planet on the plate and "
           "watch the app count the houses out loud."),
    Lesson(16, "gocara", "Transits: weather, not verdict",
           "Transits (gocara) are where the sky is NOW, laid over where it "
           "was at your birth. A transit cannot rewrite the natal promise "
           "— it times it. Slow movers (Saturn, Jupiter, the nodes) set "
           "seasons lasting months to years; the Moon changes felt tone "
           "in hours. Every transit has an entry date and an exit date, "
           "which is why each card here carries a progress bar and an "
           "end."),
    Lesson(17, "yoga", "Yogas: named combinations",
           "A yoga is a rule that fires when planets stand in a defined "
           "relationship — Jupiter in a kendra from the Moon is Gaja "
           "Kesari; Sun with Mercury is Budhaditya. Thousands are "
           "catalogued; a handful matter for any one chart. Treat a yoga "
           "as a labelled circuit: the 'Why?' button shows exactly which "
           "placements close the circuit, and the rule text it must "
           "satisfy."),
    Lesson(18, "dosha", "Doshas and their cancellations",
           "A dosha is a flagged pattern — Mangal, Kaal Sarpa, Sade Sati. "
           "What popular accounts omit is that the classical texts define "
           "each one TOGETHER with its exceptions, and the exceptions "
           "fire constantly. That is why this app never shows a dosha "
           "without auto-running its cancellation checks, and never shows "
           "a difficult transit without its end date. The pattern is a "
           "hypothesis; the checks are the verdict."),
    Lesson(19, "varga", "What is a varga?",
           "A varga is a division chart: slice every sign into N equal "
           "parts and reassign each part to a sign by rule, and you get a "
           "new twelve-sign chart that magnifies one life area. The D9 "
           "(navamsa, ninths) concerns marriage and the soul of the "
           "planets; the D10 (dasamsa, tenths) magnifies career. A planet "
           "weak in the D1 but strong in a varga has hidden reserves."),
    Lesson(20, "d9", "Read your own D9",
           "Open the Navāṃśa tab. First find the D9 lagna — top-centre "
           "diamond — and read the chart exactly like the D1: fixed "
           "houses, sign numbers, same aspect rules. Check three things: "
           "which sign your Moon reaches (its 'soul position'), whether "
           "any planet repeats its D1 sign — that is Vargottama, a planet "
           "standing in its own truth, marked by the app — and how the "
           "7th house looks, since the D9 speaks first about "
           "partnership. You are now reading divisional charts."),
]

# dashboard section → lesson key
CONTEXT_LESSONS = {
    "idline": "lagna",
    "plate": "plate",
    "d9tab": "d9",
    "dasha": "dasha",
    "antardasha": "antardasha",
    "lifeline": "dasha",
    "weather": "gocara",
    "doshas": "dosha",
    "yogas": "yoga",
    "nakshatra": "nakshatra",
    "dignity": "dignity",
}

_BY_KEY = {lesson.key: lesson for lesson in LESSONS}


def lesson(key: str) -> Lesson:
    return _BY_KEY[key]
