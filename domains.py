"""Life domains, and the checklist a reading of one must work through.

WHY THIS FILE EXISTS
Asked "will I marry?", a fact-retrieval agent finds the 7th house, says
something about it, and stops. That is not how a chart is read. An astrologer
doing the work looks at the 7th AND the houses that support it, the lord of
each and where it sits, the natural significator's condition, the divisional
chart that tests whether the promise holds, the period actually running, and
what the slow transits are doing to those houses right now — and only then
says anything.

This module is that method, written down: which houses each domain owns, why
each one is in the list, which graha signifies it naturally, and which
divisional chart confirms it. `chartfacts` uses it to make sure every step is
answerable from the ledger, and `agent` uses it to require the steps in order.

The house sets are the standard Parāśarī ones. Where a house is in the list
for a reason a reader would not guess, the reason is written next to it —
these strings are shown, not just stored.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Domain:
    id: str
    label: str              # plain English, for the reader
    houses: tuple[int, ...]  # in order of weight — the first is the main one
    why: dict[int, str]     # why each house is in the list
    karakas: tuple[str, ...]  # natural significators, strongest first
    varga: str              # the divisional chart that tests this promise
    varga_for: str
    triggers: tuple[str, ...]   # words in a question that select this domain

    @property
    def main_house(self) -> int:
        return self.houses[0]

    def as_dict(self) -> dict:
        return {"id": self.id, "label": self.label,
                "houses": list(self.houses),
                "why": {str(h): w for h, w in self.why.items()},
                "karakas": list(self.karakas), "varga": self.varga,
                "varga_for": self.varga_for}


DOMAINS: dict[str, Domain] = {
    "marriage": Domain(
        id="marriage",
        label="love, partnership and marriage",
        houses=(7, 2, 5, 8, 11),
        why={
            7: "the house of marriage and of dealings with any one other "
               "person",
            2: "the house of family — a marriage adds to the household, "
               "which is why it is read for it",
            5: "the house of romance, courtship and the affection that "
               "precedes a commitment",
            8: "the 2nd from the 7th: the durability of the marriage and "
               "what is shared in it",
            11: "the house of gain and of desires fulfilled, read for "
                "whether a wish of this kind lands",
        },
        karakas=("Venus", "Jupiter"),
        varga="D9",
        varga_for="marriage and whether a natal promise holds up",
        triggers=("marry", "marriage", "married", "wedding", "spouse",
                  "wife", "husband", "partner", "relationship", "love",
                  "romance", "dating", "girlfriend", "boyfriend",
                  "settle down", "companion"),
    ),
    "career": Domain(
        id="career",
        label="work, standing and money",
        houses=(10, 11, 6, 2, 1),
        why={
            10: "the house of visible work, standing and the field of "
                "action",
            11: "the house of gains, income and what arrives through "
                "networks",
            6: "the house of service and of work done for others — "
                "employment, in the plain sense, as against vocation",
            2: "the house of held resources and accumulated wealth",
            1: "the house of the self: what one is willing and able to do",
        },
        karakas=("Saturn", "Mercury", "Sun", "Jupiter"),
        varga="D10",
        varga_for="work, standing and the field of action",
        triggers=("job", "career", "work", "profession", "promotion",
                  "business", "salary", "money", "income", "wealth",
                  "finance", "financial", "earning", "employment", "hired",
                  "professionally", "professional"),
    ),
    "vitality": Domain(
        id="vitality",
        label="constitution, energy and the body's routines",
        houses=(1, 6, 8),
        why={
            1: "the house of the body and of vitality itself",
            6: "the house of the routines, disciplines and ailments that "
               "wear on it",
            8: "the house of longevity and of what transforms",
        },
        karakas=("Sun", "Moon", "Saturn"),
        varga="D9",
        varga_for="inner strength and durability",
        triggers=("health", "energy", "vitality", "body", "stamina",
                  "constitution", "wellbeing", "well-being", "fitness",
                  "tired", "exhausted", "burnout"),
    ),
    "home": Domain(
        id="home",
        label="home, land and the mother",
        houses=(4, 2, 12),
        why={
            4: "the house of home, land, the mother and inner ground",
            2: "the house of the family one belongs to",
            12: "the house of foreign places and of leaving",
        },
        karakas=("Moon", "Mars", "Venus"),
        varga="D9",
        varga_for="inner strength and durability",
        triggers=("home", "house", "property", "land", "relocate",
                  "moving abroad", "move abroad", "mother", "family",
                  "immigrate", "emigrate"),
    ),
    "learning": Domain(
        id="learning",
        label="study, children and creative work",
        houses=(5, 9, 4),
        why={
            5: "the house of intelligence, creativity and children",
            9: "the house of higher learning, teachers and fortune",
            4: "the house of formal schooling and of the ground one "
               "studies from",
        },
        karakas=("Jupiter", "Mercury"),
        varga="D9",
        varga_for="inner strength and durability",
        triggers=("study", "studies", "exam", "degree", "education",
                  "children", "child", "kids", "creative", "writing",
                  "research", "learning"),
    ),
}

# The order the reading must be built in. Written here rather than only in
# the prompt so a test can check the prompt against it.
CHECKLIST = (
    ("NATAL", "the domain's houses, their lords' placement and dignity, the "
              "planets in them, and the drishti falling on them"),
    ("KARAKA", "the natural significator's own condition"),
    ("VARGA", "the divisional chart that tests this promise — its lagna, the "
              "domain house in it, and dignities there"),
    ("DASHA", "the running mahadasha and antardasha lords' relationship to "
              "the domain houses, with the dates from the ledger"),
    ("TRANSIT", "where the slow movers are relative to the domain houses — "
                "by occupation AND by drishti — with their end dates"),
    ("SYNTHESIS", "two to four paragraphs weaving those five together: what "
                  "supports, what delays, what the running period emphasises"),
)


def detect(question: str) -> Domain | None:
    """The domain a question is about, or None for a general question.

    Longest trigger wins, so "settle down" beats "down" and a question that
    mentions both work and marriage picks the more specific phrase rather
    than whichever word came first.
    """
    text = f" {(question or '').lower()} "
    best: tuple[int, Domain] | None = None
    for domain in DOMAINS.values():
        for trigger in domain.triggers:
            if trigger in text:
                if best is None or len(trigger) > best[0]:
                    best = (len(trigger), domain)
    return best[1] if best else None


def houses_in_play(question: str) -> tuple[int, ...]:
    domain = detect(question)
    return domain.houses if domain else ()
