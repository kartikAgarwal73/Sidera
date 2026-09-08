"""Computation options, asked in plain English.

WHY THIS FILE EXISTS
Jyotisha is not one method. On several questions the classical sources
genuinely disagree, and every piece of astrology software silently picks a
side. Sidera's whole claim is that its numbers are checkable, and a silent
pick is the opposite of checkable: two apps give you different charts and
neither says why.

So the choices are surfaced — and surfaced in a form a person who has never
heard the word "drishti" can actually use.

THE RULES THIS FILE ENFORCES
  1. **The question is plain English.** "How far does the influence of Rahu
     and Ketu reach?" — never "Select nodal drishti scheme".
  2. **The answers are plain English too.** The school name lives underneath,
     in small text, for the reader who wants it. Nobody has to know a term to
     pick.
  3. **There is a recommended default**, pre-selected and labelled. Someone
     who does not care can ignore all of this and get the mainstream answer.
  4. **Every question says what it changes**, in one line, before you choose.
  5. **Every answer can explain itself** in two or three sentences.
  6. **No fake controls.** A choice that would not change a single computed
     value is not offered. Options whose feature has not been built are
     marked `live=False`, say so on the page, and cannot be selected —
     `TestComputationOptions` fails if a live option changes nothing.
  7. **The choice travels with the result.** Anything computed under a
     non-standard school says so, on the verdict itself, not only in a
     settings screen the reader has long since closed.

HOW THE SELECTION REACHES THE ENGINE
Through a `contextvars.ContextVar`, set for the span of one request by
`use()`. That keeps the signature of `aspected_signs()` and friends
unchanged across six modules, and unlike a module global it is safe under
threaded workers — each request sees its own selection, and a task that
never sets one gets the defaults.
"""
from __future__ import annotations

import contextvars
from contextlib import contextmanager
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Answer:
    """One choice, written for someone who has never read a jyotisha text."""

    id: str
    text: str            # plain English. No Sanskrit, no jargon.
    school: str          # the technical name, rendered small beneath `text`
    explain: str         # 2–3 sentences behind an "explain this" expander
    recommended: bool = False
    live: bool = True
    unavailable: str = ""   # shown when live is False

    def as_dict(self) -> dict:
        return {"id": self.id, "text": self.text, "school": self.school,
                "explain": self.explain, "recommended": self.recommended,
                "live": self.live, "unavailable": self.unavailable}


@dataclass(frozen=True)
class Option:
    """One plain-English question with two or three answers."""

    id: str
    question: str        # plain English, ends in a question mark
    consequence: str     # one line: what changes if you switch
    answers: tuple[Answer, ...]
    affects: tuple[str, ...] = ()   # surfaces that must print the school
    live: bool = True
    unavailable: str = ""

    @property
    def default(self) -> str:
        for answer in self.answers:
            if answer.recommended:
                return answer.id
        return self.answers[0].id

    def answer(self, answer_id: str) -> Answer:
        for answer in self.answers:
            if answer.id == answer_id:
                return answer
        return self.answer(self.default)

    def as_dict(self) -> dict:
        return {"id": self.id, "question": self.question,
                "consequence": self.consequence, "live": self.live,
                "unavailable": self.unavailable, "default": self.default,
                "affects": list(self.affects),
                "answers": [a.as_dict() for a in self.answers]}


# --- the questions ----------------------------------------------------------

OPTIONS: dict[str, Option] = {
    "node_reach": Option(
        id="node_reach",
        question="How far does the influence of Rahu and Ketu reach?",
        consequence="This changes which planets Rahu and Ketu touch — and "
                    "so which patterns the chart reports and which transits "
                    "it calls significant.",
        affects=("natal aspects", "transit aspects", "chart explorer",
                 "fact ledger"),
        answers=(
            Answer(
                id="classical",
                text="They reach three places, the way Jupiter does",
                school="Parāśarī — the 5th, 7th and 9th signs from "
                       "themselves",
                explain=(
                    "This is what most astrologers and most software use. "
                    "The nodes are treated like full planets for the "
                    "purpose of reaching across the chart, casting the same "
                    "three-way glance Jupiter does. Choose this if you want "
                    "your chart to match what another astrologer would "
                    "most likely draw."),
                recommended=True,
            ),
            Answer(
                id="opposition",
                text="Only straight across the chart",
                school="Conservative — the 7th sign only",
                explain=(
                    "A more cautious reading: the nodes reach only the "
                    "point directly opposite them, which every planet does. "
                    "Some traditions grant the nodes no special reach "
                    "because they are not bodies. This gives a quieter "
                    "chart with fewer connections."),
            ),
            Answer(
                id="none",
                text="They do not reach out at all",
                school="Chāyā-graha — shadow points cast no drishti",
                explain=(
                    "The strictest reading. Rahu and Ketu are not planets "
                    "but the two points where the Moon's path crosses the "
                    "Sun's, so on this view they colour only the sign they "
                    "sit in and glance nowhere. Their placement still "
                    "matters; their reach does not."),
            ),
        ),
    ),
    "node_position": Option(
        id="node_position",
        question="Where exactly should Rahu and Ketu be placed?",
        consequence="This can move both of them by up to 1.8° — enough to "
                    "put them in a different sign, and change their house.",
        affects=("node placements", "node transits", "fact ledger"),
        answers=(
            Answer(
                id="mean",
                text="On their smooth, averaged path",
                school="Mean node — the standard in Indian software",
                explain=(
                    "The nodes wobble slightly as they travel. This option "
                    "smooths the wobble out and uses the steady average "
                    "path, which is what the classical tables assumed and "
                    "what most Indian software still does. It is the "
                    "safer choice if you want to match a traditional "
                    "almanac."),
                recommended=True,
            ),
            Answer(
                id="true",
                text="At their exact, wobbling position",
                school="True node — used by JHora and most Western software",
                explain=(
                    "This uses the nodes' real position at your moment of "
                    "birth, wobble included. It is astronomically the more "
                    "literal answer and differs from the averaged path by "
                    "up to about 1.8°. Where that gap crosses a sign "
                    "boundary the two options will disagree about which "
                    "sign your nodes are in."),
            ),
        ),
    ),
    # NOT LIVE. Kept visible because it is a real fork in the tradition and
    # the reader deserves to know it is coming — but it is not selectable,
    # because Sidera does not compute arudha padas yet and a control that
    # changes nothing is worse than no control. See PROGRESS.md, milestone 3.
    "dual_lord": Option(
        id="dual_lord",
        question="When a sign has two possible rulers, who decides?",
        consequence="This affects Scorpio and Aquarius only — and through "
                    "them the Upapada, the point read for marriage.",
        affects=("arudha padas", "Upapada"),
        live=False,
        unavailable=("Not yet in play: Sidera does not compute arudha padas "
                     "or the Upapada, so this choice would change nothing. "
                     "It arrives with them."),
        answers=(
            Answer(
                id="single",
                text="The older, single ruler",
                school="Parāśarī — Mars for Scorpio, Saturn for Aquarius",
                explain=(
                    "Every sign was given one ruler long before Rahu and "
                    "Ketu were counted as co-rulers. On this view Scorpio "
                    "answers to Mars and Aquarius to Saturn, always, and "
                    "the shadow points own nothing."),
                recommended=True,
            ),
            Answer(
                id="stronger",
                text="Whichever of the two is stronger in your chart",
                school="Jaimini — the stronger co-lord",
                explain=(
                    "Scorpio is shared by Mars and Ketu, Aquarius by "
                    "Saturn and Rahu. This school compares the two in your "
                    "particular chart and lets the stronger one carry the "
                    "count, so the answer differs from chart to chart. It "
                    "can move the Upapada, which is read for marriage."),
            ),
        ),
    ),
}

DEFAULTS: dict[str, str] = {oid: opt.default for oid, opt in OPTIONS.items()}

# The nodal drishti offsets each answer produces. Every graha aspects the
# 7th; these say what the nodes do beyond that.
NODE_OFFSETS: dict[str, tuple[int, ...]] = {
    "classical": (5, 7, 9),
    "opposition": (7,),
    "none": (),
}


# --- the active selection ---------------------------------------------------

_ACTIVE: contextvars.ContextVar[dict] = contextvars.ContextVar(
    "sidera_schools", default=None)


def normalise(raw) -> dict[str, str]:
    """A clean selection from anything a form or a URL might hand us.

    Unknown option ids are dropped, unknown answers fall back to the
    recommended one, and an option that is not live is forced to its default
    — so a hand-edited request cannot switch on a school the build cannot
    actually compute.
    """
    out = dict(DEFAULTS)
    for key, value in (raw or {}).items():
        option = OPTIONS.get(str(key))
        if option is None or not option.live:
            continue
        answer = option.answer(str(value))
        if answer.live:
            out[option.id] = answer.id
    return out


def active() -> dict[str, str]:
    """The selection in force. Defaults when nothing has been set."""
    current = _ACTIVE.get()
    return dict(current) if current else dict(DEFAULTS)


def set_active(selections) -> None:
    _ACTIVE.set(normalise(selections))


@contextmanager
def use(selections):
    """Run a block under one selection, then restore the previous one."""
    token = _ACTIVE.set(normalise(selections))
    try:
        yield active()
    finally:
        _ACTIVE.reset(token)


def chosen(option_id: str) -> Answer:
    option = OPTIONS[option_id]
    return option.answer(active().get(option_id, option.default))


def is_default(option_id: str) -> bool:
    return active().get(option_id) == OPTIONS[option_id].default


def changed() -> list[Option]:
    """Options the reader has moved away from the recommended answer.

    These are what a summary line should lead with: nobody needs telling
    that the defaults are the defaults.
    """
    return [opt for oid, opt in OPTIONS.items()
            if opt.live and not is_default(oid)]


# --- printing the choice on the verdict -------------------------------------

def note_for(*option_ids: str) -> str:
    """The one-line provenance a verdict carries.

    ALWAYS names the school, default or not. A reader comparing Sidera's
    chart against another astrologer's needs to know which convention
    produced the number in front of them, and "it was the default" is not
    something they can see from the number.
    """
    parts = []
    for option_id in option_ids:
        option = OPTIONS.get(option_id)
        if option is None or not option.live:
            continue
        answer = chosen(option_id)
        parts.append(answer.school)
    return " · ".join(parts)


def summary() -> str:
    """One sentence for the top of the page."""
    moved = changed()
    if not moved:
        return ("Computed with the recommended settings throughout.")
    return ("Computed with " + ", ".join(
        f"{chosen(o.id).school.split(' — ')[0]}" for o in moved)
        + " — not the default. Every affected reading says so.")


def payload() -> dict:
    """The whole registry plus the current selection, for the template."""
    current = active()
    return {
        "options": [o.as_dict() for o in OPTIONS.values()],
        "selected": current,
        "defaults": dict(DEFAULTS),
        "changed": [o.id for o in changed()],
        "summary": summary(),
    }
