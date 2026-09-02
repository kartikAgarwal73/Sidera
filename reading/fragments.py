"""The authored library.

VOICE (framework, verbatim): "Write fragments as observations, not
instructions or flattery. Name the sky, then name one thing to do about it.
No second-person predictions about money, health or death. Twenty-five to
forty words for the long reading; under fifteen for the statement."

Each fragment carries three variant lists — stem, emphasis, close — giving
3×3×3 = 27 phrasings per condition, drawn by seeded hash so the same person
on the same day always reads the same words.

`fact` returns the computed working: the sky, named concretely. It is never
authored prose — it is assembled from what the engine measured.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from .detect import (
    CANDRA_FAVOURABLE,
    CANDRA_TESTING,
    HARSH_YOGAS,
    RIKTA_TITHIS,
    Conditions,
)


@dataclass(frozen=True)
class Fragment:
    id: str
    weight: int
    graha: str
    when: Callable[[Conditions], bool]
    fact: Callable[[Conditions], str]
    stem: tuple[str, ...]
    emphasis: tuple[str, ...]
    close: tuple[str, ...]
    suppress_if: tuple[str, ...] = field(default=())


def _ordinal(n: int) -> str:
    return {1: "1st", 2: "2nd", 3: "3rd"}.get(n, f"{n}th")


# --- weight 100 · daśā boundaries ----------------------------------------

def _dasa_fact(c: Conditions) -> str:
    kind, lord, when = c.dasa_boundary()
    period = "mahādaśā" if kind == "md" else "antaradaśā"
    return f"{lord}'s {period} turns on {when:%d %b %Y}."


DASA_TURN = Fragment(
    id="dasa.turn", weight=100, graha="",
    when=lambda c: c.dasa_boundary() is not None,
    fact=_dasa_fact,
    stem=("A long season changes hands",
          "One chapter closes, another opens",
          "The clock behind the year turns"),
    emphasis=("the ground shifts under settled habits",
              "old arrangements loosen their hold",
              "routine now asks to be rechosen"),
    close=("Let the handover take its weeks.",
           "Decide slowly; the season is long.",
           "Notice what you need not carry."),
)

# --- weight 90 · sāḍhe sātī phase ------------------------------------------

def _sadhe_fact(c: Conditions) -> str:
    kind, when = c.sade_sati_phase_change()
    return f"Śani {kind} the window around your Moon on {when:%d %b %Y}."


SADHE_SATI_PHASE = Fragment(
    id="sadhesati.phase", weight=90, graha="Saturn",
    when=lambda c: c.sade_sati_phase_change() is not None,
    fact=_sadhe_fact,
    stem=("Śani shifts station beside your Moon",
          "The slow audit changes angle",
          "Saturn's long pass enters a new phase"),
    emphasis=("weight redistributes rather than lifts",
              "pressure changes shape, not size",
              "heaviness moves to another corner"),
    close=("Keep the practices that got you here.",
           "Trade speed for footing this month.",
           "Repair before you build."),
)

# --- weight 80 · stations ---------------------------------------------------

def _station_fact(c: Conditions) -> str:
    planet, direction, when = c.station()
    return f"{planet} stations {direction} on {when:%d %b %Y}."


STATION_DIRECT = Fragment(
    id="station.direct", weight=80, graha="Mercury",
    when=lambda c: (c.station() or (None, None, None))[1] == "direct",
    fact=_station_fact,
    stem=("A delayed answer arrives", "What stalled begins to move",
          "The held thing comes unheld"),
    emphasis=("motion returns to a stopped file",
              "the queue starts moving again",
              "a paused conversation resumes"),
    close=("Send the message you drafted.",
           "Say yes slowly.", "Pick the thread back up."),
)

STATION_RETROGRADE = Fragment(
    id="station.retrograde", weight=80, graha="Saturn",
    when=lambda c: (c.station() or (None, None, None))[1] == "retrograde",
    fact=_station_fact,
    stem=("A planet turns back over old ground",
          "The sky doubles back",
          "Forward motion pauses and reverses"),
    emphasis=("review outruns arrival",
              "the second pass matters more",
              "revision, not launch"),
    close=("Reread before you resend.",
           "Finish rather than start.",
           "Let the plan sit a week."),
)

# --- weight 70 · slow ingress ------------------------------------------------

def _ingress_fact(c: Conditions) -> str:
    planet, sign, when = c.slow_ingress()
    return f"{planet} enters {sign} on {when:%d %b %Y}."


SLOW_INGRESS = Fragment(
    id="ingress.slow", weight=70, graha="Jupiter",
    when=lambda c: c.slow_ingress() is not None,
    fact=_ingress_fact,
    stem=("A slow graha crosses into new ground",
          "One long mover changes rāśi",
          "A multi-year tenant moves house"),
    emphasis=("a whole department changes address",
              "the background music changes key",
              "attention relocates for a long stretch"),
    close=("Give it a season before judging.",
           "Watch where your attention drifts.",
           "Let the new room furnish itself."),
)

# --- weight 60 · transit over natal lagna or Moon ----------------------------

def _over_fact(c: Conditions) -> str:
    planet, point, orb = c.transit_over_natal()
    return f"{planet} passes within {orb}° of your natal {point}."


TRANSIT_OVER_NATAL = Fragment(
    id="transit.over_natal", weight=60, graha="Moon",
    when=lambda c: c.transit_over_natal() is not None,
    fact=_over_fact,
    stem=("A transit crosses a point of yours",
          "Something stands where you began",
          "A graha passes your own degree"),
    emphasis=("the day reads more personally",
              "general weather turns particular",
              "the sky briefly uses your name"),
    close=("Take your reactions as data.",
           "Note what surfaces today.",
           "Move at your own pace."),
)

# --- weight 40 · candra gocara -----------------------------------------------

def _candra_fact(c: Conditions) -> str:
    h = c.candra_house()
    return (f"Candra transits the {_ordinal(h)} from your natal Moon, "
            f"in {c.pancanga.nakshatra.name}.")


CANDRA_EASY = Fragment(
    id="candra.favourable", weight=40, graha="Moon",
    when=lambda c: c.candra_house() in CANDRA_FAVOURABLE,
    fact=_candra_fact,
    stem=("The Moon rides an easy angle",
          "Today's Moon sits well against yours",
          "The lunar angle is cooperative"),
    emphasis=("effort meets less friction",
              "the day gives back",
              "small pushes travel further"),
    close=("Spend the ease on what matters.",
           "Ask for the thing today.",
           "Use it; the window is short."),
)

CANDRA_TESTING_F = Fragment(
    id="candra.testing", weight=40, graha="Moon",
    when=lambda c: c.candra_house() in CANDRA_TESTING,
    fact=_candra_fact,
    stem=("The Moon sits at an awkward angle",
          "Today's Moon runs against the grain",
          "The Moon passes a demanding house"),
    emphasis=("the mind tires before the work",
              "friction arrives before fatigue explains it",
              "attention costs more today"),
    close=("Lower the bar, keep the streak.",
           "Rest early rather than late.",
           "Postpone what can wait."),
)

# --- weight 25 · tithi and yoga quality ---------------------------------------

def _tithi_fact(c: Conditions) -> str:
    p = c.pancanga
    return (f"{p.paksa} {p.tithi.name}, tithi {p.tithi.index} of 30, "
            f"ending {p.tithi.ends_label}.")


PURNIMA = Fragment(
    id="tithi.purnima", weight=25, graha="Moon",
    when=lambda c: c.tithi_index() == 15,
    fact=_tithi_fact,
    stem=("The Moon stands full", "The bright fortnight completes",
          "Pūrṇimā, the lunation tops out"),
    emphasis=("things are as visible as they get",
              "little stays hidden today",
              "the picture is complete enough"),
    close=("Look at the whole before editing.",
           "Mark what is finished.",
           "Say the thing out loud."),
)

AMAVASYA = Fragment(
    id="tithi.amavasya", weight=25, graha="Moon",
    when=lambda c: c.tithi_index() == 30,
    fact=_tithi_fact,
    stem=("The Moon goes dark", "The dark fortnight closes",
          "Amāvāsyā, the lunation empties"),
    emphasis=("the quiet before a beginning",
              "an ending without its sequel",
              "the pause between two sentences"),
    close=("Leave tomorrow undecided tonight.",
           "Clear rather than plan.",
           "Rest at the cycle's bottom."),
)

RIKTA = Fragment(
    id="tithi.rikta", weight=25, graha="Moon",
    when=lambda c: c.tithi_within() in RIKTA_TITHIS,
    fact=_tithi_fact,
    stem=("A riktā tithi, the lean day",
          "The calendar marks this one thin",
          "A tithi kept clear of beginnings"),
    emphasis=("continuation over inauguration",
              "the day suits maintenance",
              "an ordinary day, deliberately"),
    close=("Continue rather than launch.",
           "Clear a backlog instead.",
           "Save the announcement for later."),
)

HARSH_YOGA = Fragment(
    id="yoga.harsh", weight=25, graha="Sun",
    when=lambda c: c.yoga_name() in HARSH_YOGAS,
    fact=lambda c: (f"The yoga is {c.pancanga.yoga.name}, one the almanac "
                    f"reads as rough-textured; it ends "
                    f"{c.pancanga.yoga.ends_label}."),
    stem=("The day's yoga is rough-grained",
          "The almanac gives today coarse texture",
          "A yoga the tradition treats carefully"),
    emphasis=("plans meet more edges",
              "the grain runs the other way",
              "smoothness must be supplied"),
    close=("Build in more time than needed.",
           "Confirm twice, assume once.",
           "Let it end before deciding."),
)

# --- weight 10 · weekday lord vs daśā lord ------------------------------------

def _weekday_fact(c: Conditions) -> str:
    md, ad = c.dasa_lords()
    return (f"{c.pancanga.weekday_name} is ruled by {c.weekday_lord()}; "
            f"the running periods are {md} and {ad}.")


WEEKDAY_AGREES = Fragment(
    id="weekday.agrees", weight=10, graha="Sun",
    when=lambda c: bool(c.dasa_lords())
    and c.weekday_lord() in c.dasa_lords(),
    fact=_weekday_fact,
    stem=("Day and season share a ruler",
          "The weekday's lord runs your period",
          "Week and year share grain"),
    emphasis=("one voice instead of two",
              "day and season pull together",
              "less translation between scales"),
    close=("Do the season's work today.",
           "A good day for the long project.",
           "Keep them aligned while they are."),
)

# --- the pañcāṅga floor: always yields something -------------------------------

PANCANGA_FLOOR = Fragment(
    id="pancanga.day", weight=5, graha="Moon",
    when=lambda c: True,
    fact=_tithi_fact,
    stem=("The five limbs sit ordinary",
          "No single signature dominates",
          "A quiet reading today"),
    emphasis=("an unremarkable day is still usable",
              "the absence of drama is a condition",
              "nothing asks for your attention"),
    close=("Use it on what you postpone.",
           "Ordinary days carry the work.",
           "Let it be uneventful."),
)


FRAGMENTS = (
    DASA_TURN,
    SADHE_SATI_PHASE,
    STATION_DIRECT,
    STATION_RETROGRADE,
    SLOW_INGRESS,
    TRANSIT_OVER_NATAL,
    CANDRA_EASY,
    CANDRA_TESTING_F,
    PURNIMA,
    AMAVASYA,
    RIKTA,
    HARSH_YOGA,
    WEEKDAY_AGREES,
    PANCANGA_FLOOR,
)

BY_ID = {f.id: f for f in FRAGMENTS}
