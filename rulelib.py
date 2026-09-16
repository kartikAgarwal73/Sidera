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

# Natal drishti onto a HOUSE. The interim domain reading cited
# rule.transit.aspect for it, which is a rule about transiting grahas; this
# is the natal one. Approved 2026-09-16.
_DRISHTI = dict([
    _r("rule.drishti.on_house",
       "A graha casts its drishti onto houses as well as onto grahas. A "
       "natural benefic's drishti on a house is read as protection over "
       "that house's matters; a natural malefic's as pressure on them.",
       "Graha drishti and the śubha and pāpa influence on bhavas, Brihat "
       "Parashara Hora Shastra; the benefic and malefic classes per "
       "rule.graha.nature"),
])

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
    _r("rule.varga.degree_convention",
       "This build computes divisional positions to the DEGREE. The "
       "position a graha holds inside its part of a sign is stretched over "
       "a full 30 degrees, so every divisional placement has a longitude "
       "and not merely a sign. That stretch is a SCALING CONVENTION, not a "
       "classical statement: the texts assign a divisional sign and say "
       "nothing about a position within it. It may be used for varga "
       "nakshatra and dignity by degree; it must never be quoted as a "
       "classical figure.",
       "Standard varga longitude construction (Jagannatha Hora, PyJHora "
       "and other modern implementations); the convention, not the text"),
    _r("rule.varga.drekkana_school",
       "The drekkana is counted two ways. Parasari sends each third of a "
       "sign to that sign, the 5th from it and the 9th — the three signs "
       "of one element, which is why it is read for siblings. The "
       "parivritti-traya counts the thirds straight on through the zodiac "
       "instead. Sidera computes whichever the reader chose and names the "
       "school on the plate.",
       "Parasari drekkana (BPHS ch. 6) vs parivritti-traya — a genuine "
       "divergence, recorded rather than resolved"),
    _r("rule.varga.bhamsa_school",
       "The bhamsa begins from the sign of the element — fire from Aries, "
       "earth from Cancer, air from Libra, water from Capricorn. Whether "
       "the even signs then count backward from the far end, as the "
       "trimsamsa openly does, is disputed, and the two readings move any "
       "graha that falls in an even sign.",
       "Nakshatramsa counting direction — texts differ on the even-sign "
       "reversal"),
    _r("rule.varga.hora_school",
       "The D2 (hora) is computed here as the TWELVE-SIGN hora: odd signs "
       "count forward from twice the sign, even signs backward from one "
       "past it, giving all twelve signs. The older and better-known hora "
       "assigns only two signs — the Sun's Leo and the Moon's Cancer — and "
       "is a different question rather than a variant of this one. Which is "
       "in use is stated on the plate.",
       "Twelve-sign hora as implemented in Jagannatha Hora (PVR Narasimha "
       "Rao); the two-sign hora is BPHS"),
    _r("rule.varga.trimsamsa_school",
       "The D30 (trimsamsa) sign comes from the classical UNEQUAL bands — "
       "5, 5, 8, 7 and 5 degrees ruled by Mars, Saturn, Jupiter, Mercury "
       "and Venus in an odd sign, and the reverse order with each planet's "
       "other sign in an even one. The equal 1-degree division is used only "
       "to scale the degree, never to choose the sign: a graha inside an "
       "8-degree band has no equal-part position to take.",
       "Trimsamsa, Brihat Parashara Hora Shastra; the unequal bands are the "
       "classical statement and the equal division is a modern shortcut"),
    _r("rule.varga.shastyamsa_school",
       "The D60 (shastyamsa) is counted half a degree per division, "
       "straight on from the sign itself. Some texts reverse the count in "
       "even signs; this build does not, and says so on the plate.",
       "Shastyamsa, Brihat Parashara Hora Shastra; the even-sign reversal "
       "is carried by some commentaries and not by others"),
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


# --- doshas: a pattern and its cancellations, cited together ----------------
#
# WHY THIS GROUP EXISTS
# Mangal dosha had no rule id. `doshas.py` carried its own prose rule, which
# made it a second citation authority: the validator could not check a
# statement about the dosha against anything, and the interim marriage
# reading could not cite it at all. The texts below are the library's; the
# dosha module reads them from here. Approved 2026-09-16 with the four
# cancellation conditions as they stand — Neecha Bhanga is NOT one of them,
# because it is not a classical Mangal cancellation and adding it would be
# a Sidera invention.

MANGAL_HOUSES = (1, 2, 4, 7, 8, 12)

_DOSHA = dict([
    _r("rule.dosha.mangal",
       "Mangal dosha forms when Mars occupies the 1st, 2nd, 4th, 7th, 8th "
       "or 12th house from the Lagna. It is read for strain on the marriage "
       "and the partner's wellbeing, and it is never read bare: the "
       "cancellation conditions are run with it and the result is stated "
       "with them.",
       "The lagne vyaye ca pātāle verse, as carried in the marriage-matching "
       "compendia rather than in Brihat Parashara Hora Shastra; the "
       "six-house form is the common carrying, some carriers omit the 2nd"),
    _r("rule.dosha.mangal_cancelled",
       "Mangal dosha is held cancelled when any of these stands: Mars in "
       "the sign the exception verse pairs with its house (Aries in the "
       "1st, Scorpio in the 4th, Capricorn in the 7th, Cancer in the 8th, "
       "Sagittarius in the 12th); Mars in its own or exaltation sign; "
       "Jupiter joining Mars or casting drishti on it; the Moon joining "
       "Mars. A cancelled dosha is cited, not dropped: the reading says it "
       "formed and what cancelled it.",
       "Standard modern practice for the cancellation conditions; the "
       "sign-exception pairing is the verse's own second half"),
])

# --- employment: the 6th as service, and the period that brings it forward --
#
# The 6th is in the career domain's house list as "employment, in the plain
# sense, as against vocation" and had no rule to fire on. The source line
# says what each source actually says: BPHS's own 6th-house list is enemies,
# disease, debts and the maternal uncle; service as employment is the
# Phaladeepika and Jataka Parijata reading.

_EMPLOYMENT = dict([
    _r("rule.house.6_service",
       "The 6th house is the house of service: work done for another, "
       "employment in the plain sense as against the vocation and standing "
       "of the 10th. Its lord's condition and what occupies it are read for "
       "the holding and keeping of a job.",
       "The 6th as service and servants, Phaladeepika ch. 1 and Jataka "
       "Parijata; Brihat Parashara Hora Shastra's own 6th-house list is "
       "enemies, disease, debts and the maternal uncle"),
    _r("rule.career.employment_period",
       "A period run by the lord of the 6th or of the 10th brings "
       "employment forward, because a dasha lord delivers the affairs of "
       "the houses it owns. The window is the period's own dates from the "
       "ledger; the rule times the season, never the day.",
       "Vimshottari dasha phala, Brihat Parashara Hora Shastra — the lord's "
       "period delivers its houses' matters, applied to the 6th and the "
       "10th"),
])

# --- what each house carries --------------------------------------------------
#
# THE ONE TABLE. Every surface that names a house by what it holds reads it
# from here — the weather cards, the Explore explanations, the Today lines,
# the Transits pane, the yoga rows, the Aṣṭakavarga grid, the planet
# explorer — through `house_words()` for the short form or `house_matters()`
# for the whole clause, which is also rule.house.<h>'s own text.
#
# There were three tables once: this one, HOUSE_MEANING_BRIEF in doshas.py
# and HOUSE_THEME in explain.py, each written for its own screen. On the
# reference chart the 8th read as "shared and other people's resources" on
# the Transits pane beside "transformation and the hidden" on the weather
# card, one scroll apart. Merged 2026-09-16 as the precondition to the
# resolver, which cites rule.house.<h> and must find the same words the
# reader saw. `TestOneHouseWordTable` fails if a second twelve-house table
# appears in any app module.

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


def house_matters(house: int) -> str:
    """The whole clause — rule.house.<h>'s own words for what it governs."""
    return HOUSE_MATTERS[house]


def house_words(house: int) -> str:
    """The short form: the first clause, for a line that names the house in
    passing — "the part of your chart that holds partnership". Always a
    prefix of `house_matters(house)`, so the two can never disagree."""
    return HOUSE_MATTERS[house].split(",")[0].strip()

# --- arudhas: the image a house casts ----------------------------------------

_ARUDHA = dict([
    _r("rule.arudha.pada",
       "A house's arudha is found by reflection: count from the house to "
       "its lord, then count that same distance on from the lord. The house "
       "is the matter itself; its arudha is how the matter appears to "
       "others.",
       "Bhava arudha, Brihat Parashara Hora Shastra ch. 29; Jaimini Sutras "
       "1.1"),
    _r("rule.arudha.exception",
       "An arudha may fall neither on its own house nor on the 7th from it "
       "— an image cannot stand where the thing itself stands, nor directly "
       "opposite it. Where the count lands there, the 10th from that place "
       "is taken instead.",
       "Brihat Parashara Hora Shastra ch. 29"),
    _r("rule.arudha.upapada",
       "The Upapada Lagna is the arudha of the 12th house, and is read for "
       "marriage and for the spouse: the 12th is the house of what is given "
       "away, and a marriage is read through what one gives to it.",
       "Upapada, Jaimini Sutras 1.4; Brihat Parashara Hora Shastra ch. 30"),
    _r("rule.arudha.upapada_occupants",
       "Grahas sitting on the Upapada colour the marriage directly: "
       "benefics there support it, malefics ask more of it. The lord of the "
       "Upapada's sign, and where that lord sits, carries the same weight.",
       "Upapada reading, Jaimini Sutras 1.4 with Parasara's bhava rules"),
    _r("rule.arudha.upapada_lord",
       "The lord of the Upapada's sign speaks for the marriage where "
       "nothing occupies the Upapada: its dignity and its house describe "
       "how the marriage is carried and where it is worked out.",
       "Upapada reading, Jaimini Sutras 1.4 with Parasara's bhava rules"),
    _r("rule.arudha.second_from_upapada",
       "The 2nd from the Upapada is read for the durability of the "
       "marriage, as the 2nd from any house is read for the sustenance of "
       "that house's matter.",
       "Bhavat bhavam applied to the Upapada — standard Jaimini practice"),
    _r("rule.arudha.colord_school",
       "Scorpio and Aquarius have two claimed lords each — Mars and Ketu, "
       "Saturn and Rahu — and an arudha is counted from the lord, so the "
       "two readings can place it in different signs. Parasari counts from "
       "the sole classical lord; Jaimini counts from whichever co-lord is "
       "stronger in the chart at hand. Sidera computes whichever the reader "
       "chose and names the school on the verdict.",
       "Parasari sole lordship vs Jaimini co-lord strength — a genuine "
       "divergence, recorded rather than resolved"),
    _r("rule.arudha.colord_strength",
       "Where the stronger co-lord decides, the comparison runs in order: "
       "a graha occupying the disputed sign yields the count to its "
       "fellow; then the graha with more bodies in its sign, the lagna "
       "counted among them; then the one better attended by Jupiter, "
       "Mercury or its own dispositor, whether by company or by rasi "
       "drishti; then the exalted one; then the one in the sign of the "
       "stronger nature, dual above fixed above movable.",
       "Jaimini Sutras 1.2 (bala), as applied to co-lordship"),
    _r("rule.arudha.rasi_drishti",
       "Rasi drishti is a sign-to-sign aspect and is not the same as graha "
       "drishti: movable signs look upon the fixed and fixed upon the "
       "movable, each excepting its immediate neighbour, and dual signs "
       "look upon one another.",
       "Rasi drishti, Jaimini Sutras 1.1"),
])

# --- chara karakas: the significators the chart assigns -----------------------

_KARAKA = dict([
    _r("rule.karaka.chara",
       "A chara karaka is assigned by the chart rather than fixed by "
       "nature: rank the grahas by how far each has advanced into its "
       "sign, highest first, and the offices fall out in order — "
       "Atmakaraka for the self at the greatest degree, down to "
       "Darakaraka for the spouse at the least.",
       "Chara karakas, Jaimini Sutras 1.1; Brihat Parashara Hora Shastra "
       "ch. 32"),
    _r("rule.karaka.rahu_reversed",
       "Rahu travels backwards, so its degree is counted backwards: a Rahu "
       "seven degrees into a sign has twenty-three degrees behind it in its "
       "own direction of travel, and is ranked accordingly.",
       "Reverse reckoning for Rahu in the chara karaka scheme — standard "
       "where the eight-karaka count is used"),
    _r("rule.karaka.count_school",
       "The number of offices is disputed. The seven-karaka scheme shares "
       "them among the visible grahas alone, holding that the nodes are "
       "shadows and signify nothing of their own. The eight-karaka scheme "
       "admits Rahu, which inserts a Pitrikaraka and moves every office "
       "below it down one — so the graha standing for the spouse often "
       "differs between the two. Ketu takes no office under either.",
       "Seven vs eight chara karakas — a genuine divergence between "
       "Parasari and later Jaimini practice"),
    _r("rule.karaka.tie_convention",
       "Where two grahas stand at the identical degree of their signs, the "
       "classical sources are silent, so Sidera compares at full precision "
       "and, only if that is equal too, gives the more senior office to the "
       "graha earlier in the natural order. This is a stated convention, "
       "not a classical rule.",
       "Sidera convention, recorded because a tie decided silently is not a "
       "rule"),
    _r("rule.karaka.darakaraka",
       "The Darakaraka signifies the spouse, and is read alongside the 7th "
       "house and the Upapada rather than instead of them: its sign, its "
       "house, its dignity and what aspects it describe the partner and "
       "the partnership.",
       "Darakaraka, Jaimini Sutras 1.1 with Parasara's bhava rules"),
    _r("rule.karaka.by_sex",
       "The natural significator of the spouse depends on the chart's "
       "owner: Venus stands for the wife in a man's chart, Jupiter for the "
       "husband in a woman's. The other remains a general significator of "
       "partnership and is read second.",
       "Kalatra karaka Venus, Brihat Parashara Hora Shastra; Jupiter as the "
       "husband's karaka in a woman's chart, Brihat Parashara Hora Shastra, "
       "Strī Jātaka chapter"),
    _r("rule.karaka.by_sex_unset",
       "Where the chart's owner has not said, Sidera reads both Venus and "
       "Jupiter as spouse significators, Venus first, and says so. This is "
       "a stated convention, not a classical rule.",
       "Sidera convention, recorded because a karaka chosen silently is not "
       "a rule"),
    _r("rule.karaka.maturation",
       "Each karaka is held to mature at a classical age, after which its "
       "matters come properly into play — the tradition gives the "
       "Darakaraka's maturity late among them. Ages are indicative of when "
       "a significator's affairs ripen, not a date on which anything "
       "happens.",
       "Karaka maturity ages, Brihat Parashara Hora Shastra ch. 32"),
    _r("rule.karaka.karakamsa",
       "The Karakamsa is the navamsa sign the Atmakaraka occupies. The "
       "Atmakaraka is what the life is for and the navamsa is where a natal "
       "promise is tested, so the sign where the two meet is read as the "
       "field in which the self is worked out.",
       "Karakamsa, Jaimini Sutras 1.2; Brihat Parashara Hora Shastra ch. 33"),
])

# --- vimsopaka: strength weighed across the divisions ------------------------

_VIMSOPAKA = dict([
    _r("rule.vimsopaka.bala",
       "A graha's strength is weighed across a GROUP of divisional charts "
       "rather than in the birth chart alone. In each chart it is worth "
       "twenty if it sits in its own sign, and otherwise as much as its "
       "standing with that sign's lord allows — eighteen for a great "
       "friend down to five for a great enemy. Each chart carries a weight, "
       "the weights of a group sum to twenty, and the result is a score out "
       "of twenty.",
       "Vimsopaka bala, Brihat Parashara Hora Shastra ch. 7"),
    _r("rule.vimsopaka.group_school",
       "How many charts are weighed is disputed, and it changes the number. "
       "The shadvarga weighs six, the saptavarga seven, the dasavarga ten "
       "and the shodasavarga all sixteen, each with its own weights — so "
       "the same graha scores differently under each, and a score means "
       "nothing without the group it was taken in.",
       "The four varga groups, BPHS ch. 6-7 — a genuine divergence in "
       "practice, recorded rather than resolved"),
    _r("rule.vimsopaka.compound_relation",
       "Standing with the sign's lord is the five-fold relation: the "
       "natural friendship of the two grahas combined with the temporary "
       "friendship they take from this chart, where grahas in the 2nd, "
       "3rd, 4th, 10th, 11th and 12th from each other are temporary "
       "friends and the rest are temporary enemies.",
       "Pancadha maitri, Brihat Parashara Hora Shastra ch. 3"),
    _r("rule.vimsopaka.nodes_excluded",
       "Rahu and Ketu take no vimsopaka score. The measure rests on owning "
       "a sign and on friendship with a sign's lord, and the nodes rule "
       "nothing, so neither half of it is defined for them.",
       "Sidera's reading of the classical scheme, stated because "
       "implementations differ on whether to score the nodes at all"),
])

# --- avasthas: the condition a graha is found in ------------------------------

_AVASTHA = dict([
    _r("rule.avastha.baladi",
       "A sign is divided into five equal parts of six degrees and a graha "
       "is read by how far through it has travelled, as an age: infant, "
       "youth, adult, old, spent. The adult stretch in the middle is the "
       "strongest and the two ends the weakest. In even signs the order "
       "reverses, so the same degree reads as its opposite.",
       "Baladi avastha, Brihat Parashara Hora Shastra ch. 45"),
    _r("rule.avastha.jagradadi",
       "A graha is awake in a sign that supports it — exalted, in its "
       "moolatrikona or in its own — dreaming in a sign that neither helps "
       "nor hinders, and asleep in one that obstructs it. This reads the "
       "graha's dignity, not its degree.",
       "Jagradadi avastha, Brihat Parashara Hora Shastra ch. 45"),
    _r("rule.avastha.independent",
       "The avasthas answer different questions and are not to be combined "
       "into one verdict. A graha at the strongest point of its passage "
       "through a sign that obstructs it is both adult and asleep, and the "
       "disagreement is the reading — averaging the two discards it.",
       "Sidera's reading, stated because the states are routinely conflated"),
])

RULES: dict[str, Rule] = {
    **_DASHA, **_TRANSIT_GENERAL, **_TRANSIT_GRAHA, **_CONTACT, **_VARGA,
    **_GRAHA_STATE, **_YOGA, **_HOUSE, **_ARUDHA, **_KARAKA, **_VIMSOPAKA,
    **_AVASTHA, **_DOSHA, **_EMPLOYMENT, **_DRISHTI,
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
                   "rule.varga.from_varga_lagna",
                   "rule.varga.degree_convention"]
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
