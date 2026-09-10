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

# --- what a graha means in its own right, and when a transit lands on one ----
#
# WHY THIS GROUP EXISTS
# A live reading called transit Ketu "supportive" because Ketu stood 3rd from
# the natal Moon — while sitting 2.66° from natal Venus. Both rules were in
# the library; nothing said which one wins, so the general one was reported as
# the verdict and the specific one was dropped. The precedence is classical;
# it just was not written down here.

KARAKATVAS = {
    "Sun": "authority, the father, vitality and standing",
    "Moon": "the mind, the mother, comfort and receptivity",
    "Mars": "energy, courage, siblings, land and contention",
    "Mercury": "speech, commerce, analysis and correspondence",
    "Jupiter": "wisdom, teachers, children, counsel and increase",
    "Venus": "love, marriage, beauty, comfort, vehicles and refinement",
    "Saturn": "labour, endurance, structure, delay and the long view",
    "Rahu": "appetite, the foreign, amplification and the unfamiliar",
    "Ketu": "detachment, loosened grip, insight and release",
}

# Naisargika (natural) benefics. Moon and Mercury are conditional in the
# tradition — the Moon by paksha, Mercury by company — and the rule text
# below says so rather than silently flattening it.
NATURAL_BENEFICS = ("Jupiter", "Venus", "Moon", "Mercury")

_CONTACT = dict([
    _r("rule.transit.contact",
       "A transiting graha within about 3° of a natal graha or of the lagna "
       "is in contact with that point. It then acts on THAT point — the "
       "houses that graha rules in this chart and its natural karakatvas — "
       "and not merely on the house the transit happens to occupy. The "
       "contact lasts while the orb holds: a season for the slow movers, "
       "days for the fast ones.",
       "Gochara by conjunction with natal points; standard transit practice"),
    _r("rule.transit.node_on_natal",
       "Rahu or Ketu on a natal graha eclipses it. While the contact holds, "
       "that graha's significations are obscured, withheld or distorted "
       "rather than delivered — Ketu by withdrawal and severance, Rahu by "
       "inflation and adulteration. On a natural benefic the reading is "
       "suppression of exactly what that benefic protects, so the "
       "significations must be named concretely: the houses it lords here, "
       "and its karakatvas.",
       "Eclipse read into gochara; nodal nature per Uttara Kalamrita and "
       "standard nodal-transit commentary"),
    _r("rule.transit.contact_over_gocara",
       "PRECEDENCE. Where a close contact with a natal point and the generic "
       "gocara-from-the-Moon verdict point different ways, the contact "
       "governs: the specific reading displaces the general one. A sign that "
       "is 3rd from the Moon is not simply 'supportive' while a node sits on "
       "a natal graha inside it.",
       "Visesa over samanya — the specific displaces the general; standard "
       "interpretive priority in jyotisha"),
    _r("rule.precedence.name_both",
       "When two rules bear on the same fact and disagree, the reading must "
       "name BOTH, state which one governs, and say why. Presenting the "
       "outranked rule as the verdict, or dropping it in silence, both "
       "misreport the chart.",
       "Interpretive method: conflicting gochara and yoga indications are "
       "weighed in the open in the classical commentaries"),
    _r("rule.graha.karakatva",
       "A graha carries natural significations independent of what it rules "
       "in any one chart. When a graha is strengthened or suppressed, name "
       "both registers: the houses it lords in THIS chart, and its "
       "karakatvas.",
       "Naisargika karakatva, Brihat Parashara Hora Shastra"),
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

# --- how a divisional chart is read -------------------------------------------

_VARGA = dict([
    _r("rule.varga.purpose",
       "Each divisional chart is read for one department of life and is not "
       "a second birth chart. The D9 (navamsa) is read for inner strength, "
       "marriage and whether a natal promise holds up; the D10 (dasamsa) for "
       "work, standing and the field of action.",
       "Shodasavarga, Brihat Parashara Hora Shastra"),
    _r("rule.varga.confirms",
       "A varga confirms or weakens what the birth chart proposes; it does "
       "not overrule it. A promise strong in D1 and repeated in the relevant "
       "varga is read as durable; strong in D1 and absent in the varga, as "
       "something that does not carry.",
       "Standard varga method (BPHS; Phaladeepika)"),
    _r("rule.varga.vargottama",
       "A graha holding the same sign in D1 and D9 is vargottama, and is "
       "read as notably strengthened — the two charts agree about it.",
       "Vargottama, Brihat Parashara Hora Shastra"),
    _r("rule.varga.from_varga_lagna",
       "Houses in a divisional chart are counted from that chart's own "
       "lagna, not from the birth lagna.",
       "Standard varga construction"),
    _r("rule.varga.sign_level",
       "This build computes divisional positions to the SIGN only. Degree "
       "within a divisional sign, and therefore varga nakshatra and "
       "dignity-by-degree in a varga, are not available and must not be "
       "asserted.",
       "Implementation limit of this build, not a classical rule"),
])

# --- the state of a graha in itself --------------------------------------------

_GRAHA_STATE = dict([
    _r("rule.graha.combust",
       "A graha within the classical orb of the Sun in longitude is asta — "
       "combust, or burnt — and is read as unable to deliver its own "
       "results plainly while the placement stands. The standard orbs are "
       "Moon 12°, Mars 17°, Mercury 14°, Jupiter 11°, Venus 10°, Saturn "
       "15°, with Mercury tightened to 12° and Venus to 8° when retrograde. "
       "The nodes are shadow points and are never combust.",
       "Asta (combustion) orbs, Brihat Parashara Hora Shastra; the "
       "retrograde tightening is carried in Phaladeepika"),
    _r("rule.graha.nature",
       "Jupiter and Venus are natural benefics; the Sun, Mars, Saturn, "
       "Rahu and Ketu natural malefics. Two are conditional: the Moon is "
       "benefic while waxing and malefic while waning, and Mercury takes "
       "the nature of the grahas it shares a sign with — benefic when "
       "alone or in benefic company.",
       "Naisargika śubha/pāpa classification, Brihat Parashara Hora "
       "Shastra"),
    _r("rule.graha.yoga_varga",
       "A yoga is formed in the birth chart and TESTED in the divisional "
       "charts. Its forming grahas holding dignity in the D9 is read as "
       "confirmation that the promise carries; losing dignity there is read "
       "as a promise thinner than the birth chart makes it look. Career and "
       "wealth yogas are tested the same way in the D10.",
       "Varga confirmation method (BPHS Shodasavarga; Phaladeepika)"),
    _r("rule.graha.yoga_activation",
       "A yoga formed in the birth chart is latent until a period of one of "
       "its forming grahas runs. The mahadasha or antardasha of a forming "
       "graha is when it is read as delivering; a transit of a forming "
       "graha over another's natal degree is read as a shorter, dated "
       "prompt of the same combination.",
       "Dasha as the timing mechanism of a yoga (BPHS dasha chapters; "
       "Phaladeepika)"),
])


# --- what a yoga classically gives ---------------------------------------------
#
# WHY THESE EXIST
# The app detected yogas and stated what each family means, in prose that
# cited nothing. A reading that says "gains through adversity" without a rule
# id behind it is exactly the improvisation this library exists to prevent —
# the validator could check the FACT and not the MEANING. One rule per
# family, and `yogaread.GIVES_RULE` maps each plain sentence to one of them.

_YOGA = dict([
    _r("rule.yoga.mahapurusha",
       "A Pancha Mahapurusha yoga forms when one of the five non-luminary "
       "grahas stands in its own or exaltation sign AND in a kendra from "
       "the lagna. Each is read for the character of its own graha carried "
       "into the person's bearing: Ruchaka for command and decisiveness, "
       "Bhadra for analysis and speech, Hamsa for judgement and counsel, "
       "Malavya for comfort and refinement, Shasha for authority built "
       "slowly.",
       "Pancha Mahapurusha yogas, Brihat Parashara Hora Shastra; "
       "Phaladeepika"),
    _r("rule.yoga.chandra",
       "Gaja Kesari forms when Jupiter stands in a kendra counted from the "
       "Moon, and is read for durable reputation, discerning judgement, and "
       "resources that recover after a loss.",
       "Chandra yogas, Brihat Parashara Hora Shastra"),
    _r("rule.yoga.solar",
       "Budhaditya forms when the Sun and Mercury share a sign, and is read "
       "for intelligence joined to authority — analysis, administration and "
       "being understood. Mercury's combustion is read as a qualification "
       "of it, not a cancellation.",
       "Budhaditya yoga, standard compilations"),
    _r("rule.yoga.dhana",
       "A Dhana yoga is a connection among the lords of the houses of "
       "wealth (1, 2, 5, 9, 11) — by conjunction, exchange, mutual aspect, "
       "or one such lord placed in another such house. It is read as "
       "earning capacity flowing along the significations of the lords "
       "actually connected, and not as a quantity of money.",
       "Dhana yogas, Brihat Parashara Hora Shastra"),
    _r("rule.yoga.viparita",
       "Viparita Raja Yoga forms when the lord of a dusthana (6, 8 or 12) "
       "occupies a dusthana. The two afflictions are read as undoing one "
       "another: gains arriving through difficulty, and reversals resolving "
       "in the person's favour.",
       "Viparita Raja Yoga, Phaladeepika; Uttara Kalamrita"),
    _r("rule.yoga.neecha_bhanga",
       "Neecha Bhanga cancels a debilitation when a named condition holds — "
       "the debilitated graha's dispositor or its exaltation lord in a "
       "kendra from the lagna or the Moon, or the graha itself in a kendra. "
       "It is read as strength restored, classically after an early "
       "setback, rather than as debilitation never having applied.",
       "Neecha Bhanga Raja Yoga, Brihat Parashara Hora Shastra"),
    _r("rule.yoga.kemadruma",
       "Kemadruma forms when no graha other than the Sun stands in the 2nd "
       "or 12th from the Moon, and none joins it. It is defined together "
       "with its exceptions and must never be reported without running "
       "them.",
       "Kemadruma and its cancellations, Chandra yoga chapters"),
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
    **_DASHA, **_TRANSIT_GENERAL, **_TRANSIT_GRAHA, **_CONTACT, **_VARGA,
    **_GRAHA_STATE, **_YOGA, **_HOUSE,
}

# The general rule a contact displaces, and the rule that says so. Kept as
# named constants because `chartfacts` writes both ids into the ledger and
# the tests assert the pairing — a precedence that only exists in prose is
# the state we are fixing.
GENERAL_GOCARA_RULE = "rule.transit.from_moon"
CONTACT_PRECEDENCE_RULE = "rule.transit.contact_over_gocara"
NAME_BOTH_RULE = "rule.precedence.name_both"

_SLOW = ("Saturn", "Jupiter", "Rahu", "Ketu")


def rules_for(*, dasha_lords=(), transit_planets=(),
              houses=(), vargas=(), contacts=()) -> list[Rule]:
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
    if contacts:
        # `contacts` is the transiting grahas that are within orb of a natal
        # point. The precedence rules ride along with them, because they are
        # only in play when there is a conflict to resolve.
        wanted += ["rule.transit.contact", CONTACT_PRECEDENCE_RULE,
                   NAME_BOTH_RULE, "rule.graha.karakatva"]
        if any(c in ("Rahu", "Ketu") for c in contacts):
            wanted.append("rule.transit.node_on_natal")
    if vargas:
        wanted += ["rule.varga.purpose", "rule.varga.confirms",
                   "rule.varga.from_varga_lagna", "rule.varga.sign_level"]
        if "D9" in [v.upper() for v in vargas]:
            wanted.append("rule.varga.vargottama")
    wanted += [f"rule.house.{h}" for h in houses if f"rule.house.{h}" in RULES]

    seen, out = set(), []
    for rid in wanted:
        if rid not in seen:
            seen.add(rid)
            out.append(RULES[rid])
    return out


def is_known(rule_id: str) -> bool:
    return rule_id in RULES
