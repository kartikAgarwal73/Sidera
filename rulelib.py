"""The classical rule library the agent interprets through.

WHY THIS EXISTS
"Answer only from computed facts" was read too narrowly and the agent started
listing facts and declining to read them — honest and useless. A chart's
facts are not the reading; the reading is what the tradition says those facts
mean. That meaning is not something the model should improvise, so it lives
here, with IDs, exactly as the fact ledger does.

The line the agent works to:

  FORBIDDEN   asserting an outcome as certain, or a date the ledger does not
              contain. "You will be offered a job in December" is both.
  REQUIRED    reading the active facts through these rules, labelled
              INTERPRETIVE and citing the rule id it used.

So `rule_ids` are checkable the same way `fact_ids` are: an interpretation
resting on a rule that does not exist here is a violation, not a flourish.

Sources are named per rule. Where the tradition genuinely varies, the text
says so rather than picking a winner silently.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

from engine import PLANETS


@dataclass(frozen=True)
class Rule:
    id: str
    text: str
    source: str

    def as_dict(self) -> dict:
        return asdict(self)


def _r(rule_id: str, text: str, source: str) -> tuple[str, Rule]:
    return rule_id, Rule(rule_id, text, source)


# --- how a dasha lord is read -------------------------------------------------

_DASHA = dict([
    _r("rule.dasha.lordship",
       "A dasha lord delivers the affairs of the houses it rules. The period "
       "brings those houses' matters forward — they become the material the "
       "years are made of.",
       "Vimshottari dasha phala, Brihat Parashara Hora Shastra"),
    _r("rule.dasha.placement",
       "The house a dasha lord occupies colours how its results arrive: the "
       "lord carries its own houses' affairs into the field of the house it "
       "sits in.",
       "Standard dasha-phala method (BPHS; Phaladeepika)"),
    _r("rule.dasha.dignity",
       "The lord's dignity sets the ease, not the outcome. Exalted or in its "
       "own sign, its themes arrive with less friction; debilitated, the same "
       "themes still arrive but ask more effort of the person.",
       "Dignity as a modifier of dasha results (BPHS)"),
    _r("rule.dasha.antara",
       "The antardasha inflects the mahadasha rather than replacing it: read "
       "the sub-lord's houses as the particular shape the era's themes take "
       "during that window.",
       "Nested dasha reading, standard practice"),
    _r("rule.dasha.node",
       "Rahu and Ketu rule no sign, so a nodal period is read from the house "
       "occupied and from the dispositor. Rahu amplifies and pushes into "
       "unfamiliar territory; Ketu withdraws attention and refines.",
       "Nodal dasha treatment (Uttara Kalamrita; standard commentary)"),
    _r("rule.dasha.relationship",
       "The natural relationship between mahadasha and antardasha lords "
       "describes whether the two agendas cooperate or pull apart.",
       "Naisargika maitri applied to nested periods"),
])

# --- how a transit is read ----------------------------------------------------

_TRANSIT_GENERAL = dict([
    _r("rule.transit.house",
       "A transiting graha activates the house it occupies: that department "
       "of life is where its nature is felt for as long as it stays there.",
       "Gochara, standard treatment"),
    _r("rule.transit.from_moon",
       "Gochara is counted from the natal Moon as well as the Lagna. The "
       "3rd, 6th, 10th and 11th from the Moon are read as supportive; the "
       "4th, 8th and 12th as demanding.",
       "Gochara chapters, classical almanac tradition"),
    _r("rule.transit.aspect",
       "A transiting graha also acts on the houses it aspects by drishti, "
       "not only the one it occupies.",
       "Graha drishti applied to gochara"),
    _r("rule.transit.dignity",
       "A transiting graha in its exaltation or own sign acts with more of "
       "its own character; debilitated, it works through obstruction.",
       "Dignity applied to transits"),
    _r("rule.transit.window",
       "A transit is bounded. Its effects are read as a season with a start "
       "and an end, not as a permanent condition.",
       "Gochara as time-bound (standard)"),
])

_TRANSIT_GRAHA = dict([
    _r("rule.transit.saturn",
       "Saturn transiting a house tests and consolidates it: slow, "
       "structural, rewarding what is built to last and wearing down what is "
       "not. Classically the most demanding transit and the most durable in "
       "its results.",
       "Sani gochara, classical Saturn-transit literature"),
    _r("rule.transit.jupiter",
       "Jupiter transiting a house expands and protects it, bringing "
       "opportunity, teachers and permission. Classically the most "
       "favourable transit, though expansion is not the same as ease.",
       "Guru gochara, standard treatment"),
    _r("rule.transit.rahu",
       "Rahu transiting a house amplifies and unsettles it, pulling "
       "attention toward the unfamiliar and toward appetite.",
       "Nodal gochara (standard commentary)"),
    _r("rule.transit.ketu",
       "Ketu transiting a house thins interest in it, turning attention "
       "inward and toward what can be let go.",
       "Nodal gochara (standard commentary)"),
    _r("rule.transit.fast",
       "Sun, Moon, Mercury, Venus and Mars move quickly; their transits "
       "colour days and weeks, and are read as texture over the slow "
       "movers, not as the main current.",
       "Standard distinction between fast and slow gochara"),
])

# --- what each house carries --------------------------------------------------

HOUSE_MATTERS = {
    1: "the body, vitality and how one is met",
    2: "held resources, speech and family of origin",
    3: "effort, initiative, siblings and one's own hands",
    4: "home, the mother, land, and inner ground",
    5: "intelligence, creativity, children and speculation",
    6: "work done for others, service, obstacles and health routines",
    7: "partnership, marriage and dealings with others",
    8: "shared and other people's resources, research, and what transforms",
    9: "fortune, the father, teachers, law and long journeys",
    10: "visible work, standing and the field of action",
    11: "gains, networks and what arrives through others",
    12: "expenditure, retreat, foreign places and release",
}

_HOUSE = dict(
    _r(f"rule.house.{h}",
       f"The {h}th house governs {matters}.",
       "Bhava significations, Brihat Parashara Hora Shastra")
    for h, matters in HOUSE_MATTERS.items()
)

RULES: dict[str, Rule] = {
    **_DASHA, **_TRANSIT_GENERAL, **_TRANSIT_GRAHA, **_HOUSE,
}

_SLOW = ("Saturn", "Jupiter", "Rahu", "Ketu")


def rules_for(*, dasha_lords=(), transit_planets=(),
              houses=()) -> list[Rule]:
    """The subset of the library that applies to one chart's active facts.

    Sending the whole library every request would be noise; sending the
    applicable slice keeps the prompt honest about what is in play.
    """
    wanted: list[str] = []
    if dasha_lords:
        wanted += ["rule.dasha.lordship", "rule.dasha.placement",
                   "rule.dasha.dignity", "rule.dasha.antara",
                   "rule.dasha.relationship"]
        if any(lord in ("Rahu", "Ketu") for lord in dasha_lords):
            wanted.append("rule.dasha.node")
    if transit_planets:
        wanted += ["rule.transit.house", "rule.transit.from_moon",
                   "rule.transit.aspect", "rule.transit.dignity",
                   "rule.transit.window"]
        for planet in transit_planets:
            key = f"rule.transit.{planet.lower()}"
            if key in RULES:
                wanted.append(key)
        if any(p in PLANETS and p not in _SLOW for p in transit_planets):
            wanted.append("rule.transit.fast")
    wanted += [f"rule.house.{h}" for h in houses if f"rule.house.{h}" in RULES]

    seen, out = set(), []
    for rid in wanted:
        if rid not in seen:
            seen.add(rid)
            out.append(RULES[rid])
    return out


def is_known(rule_id: str) -> bool:
    return rule_id in RULES
