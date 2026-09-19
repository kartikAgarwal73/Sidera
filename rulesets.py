"""The rule sets the resolver answers: what a question is about, and the
frames it is read from.

WHY NOT SIMPLY THE FIVE DOMAINS
The dashboard's five domains (domains.py) are the reader's five cards, and
they stay five. A rule set is what the RESOLVER reads a question through:
the three natal ones the owner named — marriage, career, money — and, for
each of them, its timing twin, which runs only the dated predicates. Money
is not a dashboard card: it is the Dhana houses of rule.yoga.dhana read
for their own sake, and so it lives here and nowhere the cards can see it.

DECLARED FRAMES, NOT A UNION
Each rule set DECLARES the frames it is read from. The alternative — the
union of frames_required over every rule its predicates fire — would drag
the chart of work into a marriage reading through the generic varga rules
and narrate it as consulted and silent, which is a frame nobody read. So
the list is written down, and two invariants are gated: every declared
frame is the primary frame of at least one applicable predicate, and every
applicable predicate's primary frame is declared. Silence is then a real
state — a frame that was read and had nothing weighed — never a frame that
was never looked at.
"""
from __future__ import annotations

from dataclasses import dataclass

from domains import DOMAINS, Domain
from frames import FRAMES
from rulelib import house_words

# The three natal rule sets' frames. The Moon and the Aṣṭakavarga are not
# yet declared anywhere: no rule in the library reads them through a
# predicate today, and the rules that would (a Chandra-lagna house rule, a
# Sarvāṣṭakavarga house rule) need the owner's text and signature first.
# The jaimini frame is marriage-only for the same reason: the library's
# Jaimini rules are about the spouse.
NATAL_FRAMES = {
    "marriage": ("lagna", "d9", "jaimini"),
    "career": ("lagna", "d9", "d10"),
    "money": ("lagna", "d9"),
}
TIMING_FRAMES = ("dasha", "transit")
TIMING_STEPS = ("DASHA", "TRANSIT")
NATAL_STEPS = ("NATAL", "KARAKA", "VARGA")

# Money: the Dhana houses of rule.yoga.dhana — 1, 2, 5, 9 and 11 — read
# for what accumulates, with the 2nd as the matter itself and the 1st left
# to its own domain (it is every domain's house). Jupiter is the natural
# karaka of held resources in the bhava-karaka table; no secondary karaka
# is claimed. The D9 tests the promise as it tests every promise.
MONEY = Domain(
    id="money",
    label="money, earning and what accumulates",
    houses=(2, 11, 5, 9),
    why={
        2: "the house of held resources and accumulated wealth",
        11: "the house of gains, income and what arrives through networks",
        5: "the house of speculation and merit — a house of wealth in the "
           "Dhana reading",
        9: "the house of fortune — a house of wealth in the Dhana reading",
    },
    karakas=("Jupiter",),
    varga="D9",
    varga_for="whether the promise of wealth holds up",
    triggers=("money", "wealth", "income", "salary", "finance", "financial",
              "earning", "earnings", "savings", "rich", "afford"),
)


@dataclass(frozen=True)
class RuleSet:
    id: str                    # marriage | career | money | timing:<base>
    domain: Domain             # the houses, karakas and varga the predicates read
    frames: tuple[str, ...]    # declared, in frames.FRAMES order
    steps: tuple[str, ...]     # the checklist steps whose predicates run
    timing: bool = False

    @property
    def base(self) -> str:
        return self.domain.id

    @property
    def varga(self) -> str:
        return self.domain.varga

    def as_dict(self) -> dict:
        return {"id": self.id, "base": self.base, "frames": list(self.frames),
                "steps": list(self.steps), "timing": self.timing,
                "houses": list(self.domain.houses),
                "karakas": list(self.domain.karakas), "varga": self.varga}


def _ordered(frames) -> tuple[str, ...]:
    return tuple(f for f in FRAMES if f in frames)


_BASES = {"marriage": DOMAINS["marriage"], "career": DOMAINS["career"],
          "money": MONEY}

RULESETS: dict[str, RuleSet] = {}
for _id, _domain in _BASES.items():
    RULESETS[_id] = RuleSet(_id, _domain, _ordered(NATAL_FRAMES[_id]),
                            NATAL_STEPS)
    RULESETS[f"timing:{_id}"] = RuleSet(f"timing:{_id}", _domain,
                                        _ordered(TIMING_FRAMES),
                                        TIMING_STEPS, timing=True)


def ruleset(name: str) -> RuleSet:
    return RULESETS[name]


def detect(question: str) -> RuleSet | None:
    """The rule set a question is about, or None for a general question.

    Money before career, because the career domain's own triggers include
    "money" and "income" for the dashboard card; here those words are the
    money rule set's. Timing when the question asks WHEN."""
    text = f" {(question or '').lower()} "
    when = any(w in text for w in (" when ", " how long", " until ",
                                     " what year", " which year", " soon "))
    for trigger in MONEY.triggers:
        if trigger in text:
            return RULESETS["timing:money" if when else "money"]
    from domains import detect as _detect
    domain = _detect(question)
    if domain is None or domain.id not in ("marriage", "career"):
        return None
    return RULESETS[f"timing:{domain.id}" if when else domain.id]
