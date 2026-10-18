"""The reference — nine grahas, twelve bhavas.

Two tabs, nothing else. Every entry is a plain-English account of what a
planet or a house GOVERNS, drawn from the texts named at the foot of each
card. Grades follow the ledger convention used everywhere in Sidera:

    [verse]       a numbered verse in a primary text (BPHS, Phaladīpikā,
                  Jātaka Pārijāta, Sārāvalī, Uttara Kālāmṛta)
    [convention]  what the living tradition agrees on without one
                  governing verse — maturity ages, most kāraka lists
    [lore]        widely repeated, weakly sourced; shown, never relied on

Nothing in this module computes. It is text, and the gate that applies to
it is the editorial one: answer first, no throat-clearing, every claim
carries its grade.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Section:
    title: str
    body: str            # paragraphs split on "\n\n"
    grade: str = ""      # verse / convention / lore / ""


@dataclass(frozen=True)
class Graha:
    key: str
    name: str
    sanskrit: str
    glyph: str
    tagline: str                      # ≤20 words
    lead: str                         # ≤120 words, the verdict paragraph
    facts: list[tuple[str, str]]      # the table on the right
    sections: list[Section]
    sources: list[str]


@dataclass(frozen=True)
class Bhava:
    number: int
    name: str
    sanskrit: str
    tagline: str
    lead: str
    facts: list[tuple[str, str]]
    governs: list[str]
    sections: list[Section]
    lord_in: list[tuple[int, str]]    # BPHS ch. 24 — lord of this house in each house
    sources: list[str]


# ---------------------------------------------------------------------------
# GRAHAS
# ---------------------------------------------------------------------------

_BPHS3 = "Bṛhat Parāśara Horā Śāstra, ch. 3 (graha characters and natures)"
_BPHS32 = "Bṛhat Parāśara Horā Śāstra, ch. 32 (kārakatvas of the grahas)"
_PHAL = "Phaladīpikā (Mantreśvara), ch. 2 (graha significations)"
_JP = "Jātaka Pārijāta (Vaidyanātha Dīkṣita), ch. 2"
_SARA = "Sārāvalī (Kalyāṇa Varma), ch. 4"
_UK = "Uttara Kālāmṛta (Kālidāsa), kāṇḍa 5 (kārakatvas)"
_MAT = ("Maturity ages: a convention of the living tradition (quoted in "
        "Jātaka Tattva and by later authors); no single governing verse")

GRAHAS: list[Graha] = [
    Graha(
        key="sun", name="Sun", sanskrit="Sūrya · Ravi", glyph="☉",
        tagline="The self, the father, authority, the body's vitality, and what you are seen to be.",
        lead=(
            "The Sun is the soul of the chart — Parāśara calls it the ātmā. "
            "It stands for who you are before anyone has shaped you: your "
            "constitution, your dignity, your father, and your standing in "
            "the world. Where it sits is where you want to be recognised; "
            "how strong it is tells whether that recognition comes easily or "
            "has to be fought for. It burns what it touches: a planet within "
            "a few degrees of it is combust and loses its own voice to the "
            "Sun's. It matures at 22."),
        facts=[
            ("Nature", "Malefic (cruel, krūra); male; fire; sattva; kṣatriya"),
            ("Rules", "Leo"),
            ("Exalted", "Aries 10°  ·  Debilitated Libra 10°"),
            ("Mūlatrikoṇa", "Leo 0°–20°"),
            ("Friends", "Moon, Mars, Jupiter  ·  Neutral Mercury  ·  Enemies Venus, Saturn"),
            ("Aspect", "7th house"),
            ("Daśā", "6 years"),
            ("Matures", "22 [convention]"),
            ("Kāraka of houses", "1st, 9th, 10th"),
            ("Direction", "East  ·  Deity Agni / Śiva  ·  Metal gold, copper"),
            ("Body", "Bones, heart, right eye, vitality"),
        ],
        sections=[
            Section("What it signifies",
                    "The self and its dignity. The father. Kings, government, "
                    "rank, office, authority of every kind. The soul (ātmā) and "
                    "the vital force. Health in general and the bones and heart "
                    "in particular. Fame, honour, courage, temples, forests, "
                    "mountains, the east, the colour copper-red, the metal "
                    "gold.", "verse"),
            Section("Self and mind",
                    "A strong Sun gives a clear sense of who you are and a "
                    "steady confidence that does not need an audience. It "
                    "makes a person direct, proud without being brittle, and "
                    "able to hold a position under pressure. A weak or "
                    "afflicted Sun shows as a self that needs confirming from "
                    "outside — either shrinking from notice or demanding it — "
                    "and a difficulty standing alone.\n\n"
                    "Because it is a malefic by nature, its presence is "
                    "heat: it dries and burns the house it occupies. That is "
                    "excellent in houses of effort and struggle (3rd, 6th, "
                    "10th, 11th) and harder on houses of relationship and "
                    "comfort (2nd, 4th, 7th).", "convention"),
            Section("Family",
                    "The Sun is the father in every chart, and the 9th house "
                    "is read with it. Its condition describes the father's "
                    "standing and the quality of the bond — a dignified Sun "
                    "gives a father who is respected and present; an "
                    "afflicted one a father who is distant, dominating, or "
                    "lost early. It also stands for ancestors on the paternal "
                    "side and the family's public name.", "verse"),
            Section("Work and standing",
                    "As kāraka of the 10th it governs the career's dignity "
                    "rather than its income: position, title, recognition, "
                    "work for the state or for large institutions, medicine, "
                    "administration, leadership of any kind. A Sun strong in "
                    "the 10th or aspecting it gives authority early; a Sun in "
                    "the 12th or 8th gives authority that is held out of "
                    "sight or arrives late.", "convention"),
            Section("Marriage and partnership",
                    "The Sun is not a marriage significator, but it decides "
                    "how much of yourself you keep in one. In the 7th it is "
                    "classically difficult — separative, because two suns do "
                    "not share a sky — and its heat on Venus (conjunction "
                    "within 8°, combustion) dims the capacity for softness. In "
                    "a woman's chart the Sun also stands for the husband's "
                    "standing and health [Strī Jātaka convention].",
                    "convention"),
            Section("Children",
                    "Through the 5th house, which it rules naturally as the "
                    "house of Leo. A strong Sun supports a first son and "
                    "children who carry the family name; an afflicted Sun in "
                    "the 5th delays children or brings pride between "
                    "generations.", "convention"),
            Section("Health",
                    "The heart, the spine and bones, the right eye (left in a "
                    "woman's chart by some authors), body heat, digestion's "
                    "fire, eyesight generally. Weakness: low vitality, poor "
                    "immunity, fevers, heart and eye complaints. Strength: "
                    "recovery that surprises doctors.", "verse"),
            Section("Spirit",
                    "The Sun is the ātmakāraka of the natural zodiac, the "
                    "soul's own planet. Its sign and house show where the "
                    "soul is trying to become visible to itself. Weakness "
                    "here is read as a life of borrowed purpose until the Sun "
                    "matures at 22 and a daśā or transit forces the question.",
                    "convention"),
            Section("Strong and weak",
                    "Strong: exalted, own sign, in a kendra or the 10th or "
                    "11th, in the first half of the day, high ṣaḍbala. Gives "
                    "health, authority, a known father, and a self that does "
                    "not bend.\n\n"
                    "Weak: debilitated in Libra, in the 6th, 8th or 12th, "
                    "besieged by Saturn and Rahu, eclipsed (within a few "
                    "degrees of a node). Gives difficulty with authority — "
                    "one's own and other people's — a father who could not "
                    "be leaned on, and a vitality that must be guarded.",
                    "convention"),
        ],
        sources=[_BPHS3, _BPHS32, _PHAL, _UK, _MAT],
    ),
    Graha(
        key="moon", name="Moon", sanskrit="Candra · Soma", glyph="☽",
        tagline="The mind, the mother, the emotional body, the public, and what you need in order to feel safe.",
        lead=(
            "The Moon is the mind — manas — and the mother. It is the fastest "
            "planet, which is why it carries mood and the day-to-day texture "
            "of a life. Vedic astrology reads a whole second chart from it "
            "(the candra-lagna) and runs the whole daśā system from its "
            "nakṣatra, so nothing in the chart is more consulted. A strong "
            "Moon gives a settled mind, a present mother, and ease with "
            "people; a weak one gives a mind that can be moved by anything "
            "and needs a steadier planet near it. It matures at 24."),
        facts=[
            ("Nature", "Benefic when waxing (bright half), malefic when dark; female; water; sattva; vaiśya"),
            ("Rules", "Cancer"),
            ("Exalted", "Taurus 3°  ·  Debilitated Scorpio 3°"),
            ("Mūlatrikoṇa", "Taurus 4°–30°"),
            ("Friends", "Sun, Mercury  ·  Neutral Mars, Jupiter, Venus, Saturn  ·  Enemies none"),
            ("Aspect", "7th house"),
            ("Daśā", "10 years"),
            ("Matures", "24 [convention]"),
            ("Kāraka of houses", "4th"),
            ("Direction", "North-west  ·  Deity Varuṇa / Pārvatī  ·  Metal silver"),
            ("Body", "Blood, fluids, left eye, breasts, stomach, mind"),
        ],
        sections=[
            Section("What it signifies",
                    "The mind and its moods. The mother. The public, crowds, "
                    "popularity. Water, the sea, travel by water, liquids, "
                    "milk, pearls, silver, white things. Comfort, sleep, "
                    "home as a place of rest, nourishment, fertility, the "
                    "womb. Memory, imagination, receptivity.", "verse"),
            Section("Self and mind",
                    "The Moon is where you live between decisions. Its sign "
                    "colours how you receive the world — a fire-sign Moon "
                    "reacts, an earth Moon holds, an air Moon talks it "
                    "through, a water Moon absorbs. Its nakṣatra sets the "
                    "whole daśā sequence, so the Moon is also the clock of "
                    "the life.\n\n"
                    "A Moon with benefics beside it or in a kendra from it "
                    "(sunaphā, anaphā, durudharā, kendra yogas) is a supported "
                    "mind; a Moon alone with nothing in the 2nd or 12th from "
                    "it (kemadruma) is a mind that must build its own "
                    "supports. A Moon conjunct Saturn is grave and slow to "
                    "trust; conjunct Rahu it is restless and prone to "
                    "obsession; conjunct Mars it is quick and hot; conjunct "
                    "Jupiter (gajakesarī when in a kendra) it is generous and "
                    "well-regarded.", "convention"),
            Section("Family",
                    "The mother, first and always: her health, her nature, "
                    "and the quality of early nurture. The 4th house is read "
                    "with the Moon. A waning or afflicted Moon speaks of a "
                    "mother who was unwell, absent or anxious; a bright "
                    "well-placed Moon of a mother who was the centre of the "
                    "home. It also stands for the home's emotional climate "
                    "and for the maternal line.", "verse"),
            Section("Work and standing",
                    "The Moon governs work with the public: trade in "
                    "liquids, food, hospitality, nursing and care, shipping, "
                    "the sea, anything that depends on being liked by many "
                    "people. The 10th house from the Moon is the career as "
                    "the person experiences it, and is read alongside the "
                    "10th from the lagna. Popularity and reputation are "
                    "Moon matters before they are Sun matters.", "convention"),
            Section("Marriage and partnership",
                    "In a man's chart the Moon is the wife's emotional "
                    "presence and the house's comfort; in any chart it is what "
                    "the person needs from a partner in order to feel at home. "
                    "Compatibility (aṣṭakūṭa) is counted from the Moon's "
                    "nakṣatra alone, which is why two Moons in the same star "
                    "or friendly stars bind, and two in rajju or nāḍī "
                    "conflict are flagged. A Moon in the 7th makes partnership "
                    "central to wellbeing.", "convention"),
            Section("Children",
                    "The Moon is fertility and the womb. A strong Moon, "
                    "especially with Jupiter or in Cancer or Taurus, supports "
                    "children; an afflicted Moon in the 5th or with Saturn "
                    "and the nodes delays them or brings worry around them. "
                    "The Moon also stands for the mother's role one plays "
                    "toward one's own children.", "convention"),
            Section("Health",
                    "Fluids, blood, lymph, the stomach, the breasts, the "
                    "left eye, the lungs by some authors, sleep and "
                    "menstruation. Mental health is the Moon's domain "
                    "entirely: an afflicted Moon with Saturn, Rahu or Ketu, "
                    "or a dark-half Moon in the 8th or 12th, is the first "
                    "thing read for anxiety and low mood.", "verse"),
            Section("Spirit",
                    "The Moon is the devotional mind — bhakti — and the "
                    "capacity for stillness. The texts give it to Pārvatī "
                    "and to the waters. A Moon in the 12th or in Pisces turns "
                    "inward easily; a Moon in the 1st or 10th needs the world "
                    "as a mirror before it can turn inward at all.",
                    "convention"),
            Section("Strong and weak",
                    "Strong: bright (within ~72° of opposition to the Sun), "
                    "exalted or in Cancer, in a kendra, with benefics in the "
                    "2nd and 12th from it, in a watery or earthy sign, at "
                    "night. Gives a calm mind, a good mother, popularity, "
                    "comfort.\n\n"
                    "Weak: dark (new-Moon side), in Scorpio, in the 6th, 8th "
                    "or 12th, alone (kemadruma), with Saturn or the nodes. "
                    "Gives a mind that is moved by every wind, trouble around "
                    "the mother, and a need to be with a steadying person.",
                    "convention"),
        ],
        sources=[_BPHS3, _BPHS32, _PHAL, _SARA, _MAT],
    ),
    Graha(
        key="mars", name="Mars", sanskrit="Maṅgala · Kuja · Bhauma", glyph="♂",
        tagline="Energy, courage, siblings, land, conflict, and the will to act on what you want.",
        lead=(
            "Mars is strength in the chart — Parāśara gives it to the body's "
            "power and to courage. It is the commander: it moves things, "
            "breaks things, defends things. It stands for younger siblings, "
            "property and land, soldiers, surgeons, engineers, and every "
            "kind of fight. Where Mars sits is where you push; where it "
            "aspects (4th, 7th, 8th from itself) is where you cut. A strong "
            "Mars gives drive and a body that heals; a weak one gives either "
            "hesitation or anger that leaks sideways. It matures at 28."),
        facts=[
            ("Nature", "Malefic; male; fire; tamas; kṣatriya"),
            ("Rules", "Aries, Scorpio"),
            ("Exalted", "Capricorn 28°  ·  Debilitated Cancer 28°"),
            ("Mūlatrikoṇa", "Aries 0°–12°"),
            ("Friends", "Sun, Moon, Jupiter  ·  Neutral Venus, Saturn  ·  Enemy Mercury"),
            ("Aspects", "4th, 7th, 8th houses"),
            ("Daśā", "7 years"),
            ("Matures", "28 [convention]"),
            ("Kāraka of houses", "3rd, 6th"),
            ("Direction", "South  ·  Deity Kārttikeya / Bhūmi  ·  Metal copper"),
            ("Body", "Muscle, marrow, blood (red), head, bile"),
        ],
        sections=[
            Section("What it signifies",
                    "Courage, strength, aggression, heat. Younger brothers "
                    "and sisters. Land, property, houses as buildings, the "
                    "earth itself (Bhūmi-putra, son of the earth). Weapons, "
                    "fire, surgery, cuts, accidents, blood. Soldiers, "
                    "police, athletes, engineers, cooks, butchers. Enemies "
                    "and disputes. Debt, by Mars's lordship of the 6th in "
                    "the natural zodiac.", "verse"),
            Section("Self and mind",
                    "Mars is the capacity to want something and move toward "
                    "it without asking permission. A dignified Mars gives "
                    "decisiveness, physical confidence, and a temper that "
                    "flares and is gone. An afflicted Mars gives one of two "
                    "things: rashness that creates its own enemies, or — "
                    "when debilitated or hemmed in — a will that stalls, "
                    "with the anger turned inward or let out on the wrong "
                    "target.\n\n"
                    "Mars conjunct the Moon heats the mind; with Mercury it "
                    "sharpens the tongue; with Saturn it is the classic "
                    "frustration pair — the accelerator and the brake pressed "
                    "together; with Rahu it is explosive.", "convention"),
            Section("Family",
                    "Younger siblings above all: their number, their "
                    "fortunes, and the bond. Mars in the 3rd or aspecting it "
                    "gives brothers; Mars afflicted there gives quarrels "
                    "with them or their loss. It also stands for the home as "
                    "a building and for land owned — the 4th house's "
                    "brick-and-mortar side belongs to Mars, its comfort side "
                    "to the Moon.", "verse"),
            Section("Work and standing",
                    "Work that needs force, speed or risk: the military, "
                    "police and security, surgery, engineering, construction, "
                    "real estate, sport, metal and fire trades, anything "
                    "competitive. A strong Mars in the 10th or 3rd gives "
                    "initiative in the career; in the 6th it wins disputes "
                    "and competitions. Mars with the 10th lord gives a "
                    "career built by one's own push rather than inheritance.",
                    "convention"),
            Section("Marriage and partnership",
                    "Mars is the most-discussed planet in marriage matching "
                    "because of kuja doṣa: Mars in the 1st, 2nd, 4th, 7th, "
                    "8th or 12th from the lagna (and by many authors from "
                    "the Moon and Venus) is said to bring heat, friction or "
                    "separation into marriage unless matched or cancelled. "
                    "The texts give many cancellations — Mars in its own or "
                    "exaltation sign, aspected by Jupiter, the same doṣa in "
                    "the partner's chart — and the doṣa is a question of "
                    "degree, not a verdict.\n\n"
                    "Beyond the doṣa, Mars describes passion and the ability "
                    "to fight for a relationship; in a woman's chart it is "
                    "also read for the husband's vigour alongside Jupiter "
                    "[Strī Jātaka convention].", "convention"),
            Section("Children",
                    "Not a direct significator, but Mars in the 5th is "
                    "classically read as difficulty with the first "
                    "conception or a forceful, athletic child; Mars "
                    "aspecting the 5th from the 11th (its 7th aspect) is "
                    "protective of children.", "lore"),
            Section("Health",
                    "Blood, muscle, bone marrow, the head and face, bile and "
                    "heat in the body. Accidents, cuts, burns, surgery, "
                    "fevers, inflammation, high blood pressure. A strong Mars "
                    "heals fast and tolerates pain; a weak Mars bruises "
                    "easily and tires. Mars in the 6th is good for fighting "
                    "disease; in the 8th it is read for operations and "
                    "sudden injury.", "verse"),
            Section("Spirit",
                    "Mars is the warrior's discipline — tapas, austerity as "
                    "effort rather than withdrawal. It is given to "
                    "Kārttikeya, the general of the gods. Its spiritual "
                    "question is what the force is for: Mars in the 9th or "
                    "12th, or with Ketu, turns the fight inward and makes "
                    "an ascetic or a crusader.", "convention"),
            Section("Strong and weak",
                    "Strong: exalted in Capricorn, in Aries or Scorpio, in "
                    "the 10th or 3rd or 6th, with the Sun or Jupiter, in the "
                    "southern direction (10th house gives dig-bala). Gives "
                    "courage, siblings, property, a body that performs.\n\n"
                    "Weak: debilitated in Cancer, in the 7th or 4th from the "
                    "lagna with no dignity, combust, with Saturn in a "
                    "mutual-aspect lock, with Rahu. Gives either timidity or "
                    "misdirected anger, disputes over land, trouble with "
                    "brothers, and accidents in Mars periods. Note that a "
                    "debilitated Mars in the navāṃśa of its exaltation, or "
                    "whose dispositor is strong (nīca-bhaṅga), recovers much "
                    "of its force.", "convention"),
        ],
        sources=[_BPHS3, _BPHS32, _PHAL, _JP, _MAT],
    ),
    Graha(
        key="mercury", name="Mercury", sanskrit="Budha", glyph="☿",
        tagline="Intellect, speech, trade, skill, friends, and the capacity to learn anything.",
        lead=(
            "Mercury is speech and intellect — Parāśara gives it vāṇī, the "
            "voice. It is the prince: young, quick, adaptable, and coloured "
            "entirely by whoever it stands with. Alone it is a benefic; "
            "beside a malefic it becomes one. It governs learning, writing, "
            "calculation, commerce, communication, the nervous system, and "
            "maternal uncles. A strong Mercury gives wit and the ability to "
            "turn any skill to account; a weak one gives a mind that knows "
            "but cannot say, or says but cannot land. It matures at 32."),
        facts=[
            ("Nature", "Benefic alone; takes the nature of its company; neuter; earth; rajas; vaiśya"),
            ("Rules", "Gemini, Virgo"),
            ("Exalted", "Virgo 15°  ·  Debilitated Pisces 15°"),
            ("Mūlatrikoṇa", "Virgo 16°–20°"),
            ("Friends", "Sun, Venus  ·  Neutral Mars, Jupiter, Saturn  ·  Enemy Moon"),
            ("Aspect", "7th house"),
            ("Daśā", "17 years"),
            ("Matures", "32 [convention]"),
            ("Kāraka of houses", "4th, 10th"),
            ("Direction", "North  ·  Deity Viṣṇu  ·  Metal brass, bronze"),
            ("Body", "Skin, nerves, speech, lungs, hands"),
        ],
        sections=[
            Section("What it signifies",
                    "Speech, intellect, education, writing, mathematics, "
                    "astrology, trade and commerce, merchants, accounts, "
                    "messengers, friends, maternal uncles, skill of the "
                    "hands, humour, youth, the skin, green things, mixed "
                    "things. It is the planet of the in-between: the broker, "
                    "the translator, the student.", "verse"),
            Section("Self and mind",
                    "Mercury is how you think out loud and how fast you "
                    "learn. Its sign sets the style: in Gemini it is broad "
                    "and quick, in Virgo exact and critical, in a fire sign "
                    "persuasive, in a water sign intuitive but sometimes "
                    "unclear. Its company sets its morals: Mercury with "
                    "Jupiter is the scholar, with Venus the artist or "
                    "diplomat, with Mars the debater or the liar, with Saturn "
                    "the slow careful thinker, with Rahu the clever operator.\n\n"
                    "Budha-āditya — Mercury with the Sun — is the commonest "
                    "yoga in the sky and gives intelligence that serves "
                    "position, but only if Mercury is not too close "
                    "(combust within ~12°, or ~14° if retrograde).",
                    "convention"),
            Section("Family",
                    "Maternal uncles and the mother's family. Friends who "
                    "function like family. Mercury in the 3rd or 11th gives "
                    "a wide circle; afflicted in the 4th it is friction in "
                    "the household's conversation. In many lists it also "
                    "stands for adopted children and for the younger "
                    "co-born alongside Mars.", "convention"),
            Section("Work and standing",
                    "Trade, accounting, writing, teaching, publishing, law, "
                    "astrology, information technology, brokerage, sales, "
                    "translation, any work done with words, numbers or the "
                    "hands. Mercury is kāraka of the 10th with the Sun, "
                    "Jupiter and Saturn, and its strength tells whether skill "
                    "converts into position. Mercury in the 10th gives many "
                    "lines of work rather than one.", "convention"),
            Section("Marriage and partnership",
                    "Not a marriage planet, but Mercury decides whether two "
                    "people can talk. In the 7th it gives a young, clever, "
                    "talkative partner and a relationship that lives on "
                    "conversation; afflicted there, a partner who is evasive "
                    "or a relationship argued to death. Its neutrality makes "
                    "it the planet of friendship inside a marriage.",
                    "convention"),
            Section("Children",
                    "Mercury rules the 5th from Virgo and Gemini and is the "
                    "planet of the child's education and quickness. Mercury "
                    "in the 5th gives clever children and a love of games and "
                    "study; some authors read it for fewer children, because "
                    "it is neuter.", "convention"),
            Section("Health",
                    "The nervous system, the skin, speech organs, the lungs "
                    "and breath (shared with the Moon), the hands and arms. "
                    "Afflictions: stammering, skin complaints, nervous "
                    "exhaustion, anxiety that speaks in the body, allergies. "
                    "A combust Mercury is read for a voice that is not "
                    "heard.", "verse"),
            Section("Spirit",
                    "Mercury is given to Viṣṇu and to the study of scripture "
                    "— jñāna through learning rather than through "
                    "renunciation. Mercury in the 9th or 12th, or with Ketu, "
                    "makes the seeker who reads; with Jupiter in a trine, "
                    "the teacher.", "convention"),
            Section("Strong and weak",
                    "Strong: exalted in Virgo (its own sign and exaltation "
                    "both), in Gemini, in the 1st (dig-bala), with Jupiter or "
                    "Venus, free of combustion, direct. Gives learning, "
                    "wealth by trade, friends, a quick tongue that lands.\n\n"
                    "Weak: debilitated in Pisces, combust, in the 8th or "
                    "12th with malefics, hemmed by Mars and Saturn. Gives "
                    "a mind that cannot finish, speech trouble, bad "
                    "contracts, and friends who cost money. Retrograde "
                    "Mercury is not weak — it is inward, and often stronger "
                    "in ṣaḍbala — but it thinks twice before it speaks once.",
                    "convention"),
        ],
        sources=[_BPHS3, _BPHS32, _PHAL, _UK, _MAT],
    ),
    Graha(
        key="jupiter", name="Jupiter", sanskrit="Guru · Bṛhaspati", glyph="♃",
        tagline="Wisdom, children, wealth, the teacher, the husband in a woman's chart, and grace.",
        lead=(
            "Jupiter is the great benefic — Parāśara gives it knowledge and "
            "happiness. It is the priest and the teacher: it expands, "
            "protects, and gives meaning to what it touches. It stands for "
            "children, wealth that comes as blessing rather than effort, "
            "higher learning, dharma, the guru, elder brothers, and — in a "
            "woman's chart — the husband. Its aspects (5th, 7th, 9th) are "
            "the chart's best protection: a house Jupiter looks at is "
            "rarely destroyed, whatever else sits there. It matures first, "
            "at 16."),
        facts=[
            ("Nature", "Benefic (the greatest); male; ether; sattva; brāhmaṇa"),
            ("Rules", "Sagittarius, Pisces"),
            ("Exalted", "Cancer 5°  ·  Debilitated Capricorn 5°"),
            ("Mūlatrikoṇa", "Sagittarius 0°–10°"),
            ("Friends", "Sun, Moon, Mars  ·  Neutral Saturn  ·  Enemies Mercury, Venus"),
            ("Aspects", "5th, 7th, 9th houses"),
            ("Daśā", "16 years"),
            ("Matures", "16 [convention]"),
            ("Kāraka of houses", "2nd, 5th, 9th, 10th, 11th"),
            ("Direction", "North-east  ·  Deity Indra / Brahmā  ·  Metal gold"),
            ("Body", "Fat, liver, thighs, ears, growth"),
        ],
        sections=[
            Section("What it signifies",
                    "Wisdom, knowledge, scripture, the teacher and the "
                    "priest. Children, especially sons. Wealth, gold, "
                    "treasure. Fortune, grace, dharma, faith. Elder "
                    "brothers. The husband in a woman's chart. Ministers, "
                    "judges, bankers, advisers. Expansion, generosity, "
                    "optimism, the colour yellow, the north-east.", "verse"),
            Section("Self and mind",
                    "Jupiter is the part of you that believes life means "
                    "something and acts accordingly. Strong, it gives "
                    "judgement — the ability to see the larger shape and "
                    "choose well — along with generosity, humour, and a "
                    "steadiness that comes from faith rather than control. "
                    "Weak or afflicted, it gives either over-confidence (the "
                    "preacher who does not practise) or a loss of meaning, a "
                    "life that is competent but hollow.\n\n"
                    "Jupiter on the lagna or Moon, or in a kendra from the "
                    "Moon (gajakesarī), is the mark of a person others trust "
                    "with advice. Jupiter in the 12th from the Moon or lagna "
                    "is a quieter faith, lived rather than taught.",
                    "convention"),
            Section("Family",
                    "Elder brothers and sisters, the family's teachers and "
                    "elders, and the family's wealth across generations. "
                    "Jupiter's house shows where the family's blessing is "
                    "concentrated; its aspect on the 2nd or 4th protects the "
                    "home and the family's reputation. In a woman's chart "
                    "Jupiter's condition is read for the husband's character "
                    "and the marriage's dignity [Strī Jātaka, BPHS ch. 80 "
                    "convention].", "convention"),
            Section("Money",
                    "Jupiter is the chief dhana-kāraka: wealth that comes by "
                    "grace, by knowledge, by advice, by children, by "
                    "inheritance. Jupiter in the 2nd, 5th, 9th or 11th, or "
                    "aspecting them, gives money that arrives without being "
                    "chased; Jupiter in the 6th, 8th or 12th gives money "
                    "spent on others, on learning, or on faith. Jupiter "
                    "with Venus is a wealth pair; with Saturn, wealth that "
                    "comes late and stays.", "convention"),
            Section("Work and standing",
                    "Teaching, law, religion, counselling, finance and "
                    "banking, publishing, philosophy, medicine (the "
                    "physician as healer rather than surgeon), any work that "
                    "advises or expands others. Jupiter in the 10th gives a "
                    "respected career; aspecting the 10th, a career that is "
                    "clean. Jupiter also stands for the employer who is a "
                    "mentor and for honours granted rather than won.",
                    "convention"),
            Section("Marriage and partnership",
                    "In a woman's chart Jupiter IS the husband — the "
                    "husband-significator — and its house, sign, dignity and "
                    "the planets around it describe him and the marriage's "
                    "quality. Jupiter in a kendra or trine, strong, gives a "
                    "husband of standing and a stable marriage; afflicted by "
                    "Saturn, Mars or the nodes, a marriage delayed or "
                    "burdened. In any chart Jupiter's aspect on the 7th or "
                    "its lord is the single most protective factor for a "
                    "marriage, and Jupiter transiting the 7th or aspecting "
                    "the 7th lord is the classical timing for one.",
                    "convention"),
            Section("Children",
                    "Jupiter is putra-kāraka — the children's planet. The "
                    "5th house and Jupiter are read together; a strong "
                    "Jupiter aspecting or occupying the 5th gives children "
                    "and happiness through them; Jupiter in the 5th itself "
                    "is the kāraka-in-own-house paradox (kārako bhāva "
                    "nāśāya) and some authors read it for delay. Jupiter "
                    "debilitated with the 5th afflicted is the classical "
                    "difficulty.", "convention"),
            Section("Health",
                    "The liver, fat, the thighs and hips, the ears, growth "
                    "and the body's bulk, the pancreas by modern authors. "
                    "Afflictions: diabetes, obesity, liver complaints, "
                    "tumours by excess growth. Jupiter's aspect on the lagna "
                    "or 6th is read as long life and recovery.", "verse"),
            Section("Spirit",
                    "Jupiter is dharma itself — the path, the guru, the "
                    "scriptures, the capacity for faith. Its sign shows the "
                    "form faith naturally takes; its house, where faith is "
                    "tested. Jupiter in the 9th or 12th, or with Ketu, makes "
                    "the renunciate or the pilgrim; Jupiter in the 1st or "
                    "5th, the teacher. Jupiter's daśā is read as the period "
                    "when meaning arrives, whatever else does.",
                    "convention"),
            Section("Strong and weak",
                    "Strong: exalted in Cancer, in Sagittarius or Pisces, in "
                    "the 1st or any kendra (dig-bala in the 1st), aspecting "
                    "the lagna, Moon or 7th, in a trine. Gives children, "
                    "wealth, wisdom, a good marriage for a woman, and a life "
                    "that is protected even in bad periods.\n\n"
                    "Weak: debilitated in Capricorn, in the 6th, 8th or 12th "
                    "with malefics, combust, with Rahu (guru-caṇḍāla) or "
                    "Saturn without dignity. Gives children late or with "
                    "worry, teachers who disappoint, faith that is tested, "
                    "and wealth that leaks. Retrograde Jupiter is not weak; "
                    "it is a faith that was earned rather than inherited.",
                    "convention"),
        ],
        sources=[_BPHS3, _BPHS32, _PHAL, _JP, _MAT],
    ),
    Graha(
        key="venus", name="Venus", sanskrit="Śukra", glyph="♀",
        tagline="Love, marriage, beauty, pleasure, vehicles, the arts, and the wife in a man's chart.",
        lead=(
            "Venus is desire and its refinement — Parāśara gives it semen "
            "and all that is sweet. It is the minister of the asuras, the "
            "guru of the other side, and it knows what people want. It "
            "stands for love, marriage, the spouse (the wife in a man's "
            "chart, the capacity for partnership in any), beauty, art, "
            "music, comfort, vehicles, jewels, luxury, and the sexual life. "
            "A strong Venus gives charm, taste, and a marriage worth "
            "having; a weak one gives either appetite without satisfaction "
            "or a coldness that does not know what it wants. It matures at "
            "25."),
        facts=[
            ("Nature", "Benefic; female; water; rajas; brāhmaṇa"),
            ("Rules", "Taurus, Libra"),
            ("Exalted", "Pisces 27°  ·  Debilitated Virgo 27°"),
            ("Mūlatrikoṇa", "Libra 0°–15°"),
            ("Friends", "Mercury, Saturn  ·  Neutral Mars, Jupiter  ·  Enemies Sun, Moon"),
            ("Aspect", "7th house"),
            ("Daśā", "20 years"),
            ("Matures", "25 [convention]"),
            ("Kāraka of houses", "7th"),
            ("Direction", "South-east  ·  Deity Indrāṇī / Lakṣmī  ·  Metal silver"),
            ("Body", "Semen, reproductive organs, face, eyes, kidneys"),
        ],
        sections=[
            Section("What it signifies",
                    "Marriage and the spouse. Love, romance, sexual "
                    "pleasure. Beauty, art, music, dance, poetry, perfume, "
                    "flowers, fine clothes, jewels, silver. Vehicles and "
                    "conveyances. Comfort, luxury, wealth in the form of "
                    "things enjoyed. Diplomacy, charm, the courtesan and the "
                    "minister. Sweet taste, the south-east, white and "
                    "variegated colours.", "verse"),
            Section("Self and mind",
                    "Venus is taste — what you are drawn to and how you make "
                    "yourself pleasing. Strong, it gives grace of manner, an "
                    "eye for beauty, the ability to enjoy, and a wish for "
                    "harmony that makes rooms easier when you are in them. "
                    "Afflicted, it gives either excess (pleasure as escape) "
                    "or its mirror, a difficulty receiving pleasure at all.\n\n"
                    "Venus with Mercury is the artist and the diplomat; "
                    "with Mars, strong desire and a love of risk in love; "
                    "with Saturn, loyalty that lasts and love that comes "
                    "late; with Rahu, unconventional attractions; with the "
                    "Sun (combust within ~10°), a heart burnt by the ego's "
                    "needs. Venus with Jupiter is wealth and a good marriage, "
                    "though the two gurus are formally enemies.",
                    "convention"),
            Section("Family",
                    "The wife in a man's chart, and through her the "
                    "in-laws. In every chart, the home's comforts — "
                    "furnishings, vehicles, pleasures shared — and the "
                    "women of the household. Venus in the 4th gives a "
                    "beautiful home and vehicles; in the 2nd, wealth and a "
                    "sweet tongue; afflicted in the 7th, trouble in the "
                    "marriage house itself.", "convention"),
            Section("Money",
                    "Wealth as enjoyment rather than accumulation. Venus in "
                    "the 2nd, 11th or 4th gives money and the things money "
                    "buys; Venus with Jupiter or Mercury in a wealth house "
                    "is the classical fortune. Venus in the 12th is "
                    "excellent — the 12th is bed-pleasure and foreign "
                    "comfort, both Venus's — and is one of the few benefic "
                    "placements there.", "convention"),
            Section("Work and standing",
                    "The arts, music, fashion, film, design, beauty, "
                    "hospitality, luxury goods, jewellery, vehicles, "
                    "diplomacy, law as advocacy, anything that trades in "
                    "pleasure or taste. Venus in the 10th gives a public "
                    "career in such fields or a career advanced by charm; "
                    "Venus as 10th lord, work that must be beautiful to be "
                    "done.", "convention"),
            Section("Marriage and partnership",
                    "Venus is the kāraka of the 7th house for both sexes: "
                    "the capacity for partnership and for sexual love. In a "
                    "man's chart it is also the wife herself, as Jupiter is "
                    "the husband in a woman's. The 7th house, its lord, and "
                    "Venus are read together for every marriage question; "
                    "Venus's condition tells whether the marriage is "
                    "enjoyed, however the 7th says it is arranged.\n\n"
                    "Venus in the 7th is the kāraka-in-own-house case: "
                    "strong desire for partnership and, by some authors, "
                    "more than one. Venus afflicted by Saturn delays; by "
                    "Mars, heats; by Rahu, complicates; combust, dims the "
                    "capacity for tenderness. Venus and the Moon together "
                    "describe the emotional and sensual life as one.",
                    "convention"),
            Section("Children",
                    "Venus is fertility's pleasure side and stands for "
                    "daughters by several authors. Venus in the 5th gives "
                    "romance, creative work, and children who are loved; "
                    "it is also the classic 'love affair' placement.",
                    "convention"),
            Section("Health",
                    "The reproductive system, semen and ovaries, the "
                    "kidneys, the face and complexion, the eyes (with the "
                    "luminaries), the throat by some authors. Afflictions: "
                    "venereal and reproductive complaints, kidney trouble, "
                    "diabetes by sweetness, disorders of appetite.", "verse"),
            Section("Spirit",
                    "Venus is bhakti as beauty — devotion through art, "
                    "music and love. It is also the guru who knows the "
                    "mantra of revival (mṛta-sañjīvanī), the knowledge that "
                    "brings back the dead: Venus in the 8th or 12th, or with "
                    "Ketu, is the mystic of the senses, and a strong Venus in "
                    "Pisces is the tradition's picture of love perfected.",
                    "convention"),
            Section("Strong and weak",
                    "Strong: exalted in Pisces, in Taurus or Libra, in the "
                    "4th (dig-bala), in a kendra or the 2nd, 11th or 12th, "
                    "with Mercury or Jupiter, free of combustion. Gives "
                    "marriage, comfort, vehicles, art, and a life with "
                    "pleasure in it.\n\n"
                    "Weak: debilitated in Virgo, combust, in the 6th or 8th "
                    "with malefics, between Saturn and Mars, with Rahu or "
                    "Ketu by degree. Gives marriage delayed or disappointed, "
                    "appetite that does not satisfy, and in Venus periods "
                    "losses through pleasure or partners. A debilitated "
                    "Venus in the navāṃśa of Pisces or with Mercury strong "
                    "recovers (nīca-bhaṅga).", "convention"),
        ],
        sources=[_BPHS3, _BPHS32, _PHAL, _SARA, _MAT],
    ),
    Graha(
        key="saturn", name="Saturn", sanskrit="Śani", glyph="♄",
        tagline="Time, work, discipline, grief, servants, longevity, and what you must earn rather than receive.",
        lead=(
            "Saturn is sorrow in Parāśara's list — duḥkha — and it is also "
            "the planet of time, work and endurance. It is the servant and "
            "the judge: slow, cold, exact, impartial. It stands for "
            "longevity, labour, discipline, delay, old age, the poor, the "
            "oppressed, iron, oil, and everything that must be built over "
            "years. Where Saturn sits is where life asks for patience; "
            "where it aspects (3rd, 7th, 10th from itself) is where it "
            "restricts. A strong Saturn gives staying power and authority "
            "that lasts; a weak one gives fear, delay without reward, and a "
            "body that ages before its time. It matures last, at 36."),
        facts=[
            ("Nature", "Malefic (the greatest); neuter; air; tamas; śūdra"),
            ("Rules", "Capricorn, Aquarius"),
            ("Exalted", "Libra 20°  ·  Debilitated Aries 20°"),
            ("Mūlatrikoṇa", "Aquarius 0°–20°"),
            ("Friends", "Mercury, Venus  ·  Neutral Jupiter  ·  Enemies Sun, Moon, Mars"),
            ("Aspects", "3rd, 7th, 10th houses"),
            ("Daśā", "19 years"),
            ("Matures", "36 [convention]"),
            ("Kāraka of houses", "6th, 8th, 10th, 12th"),
            ("Direction", "West  ·  Deity Brahmā / Yama  ·  Metal iron, lead"),
            ("Body", "Nerves, sinews, legs, knees, teeth, chronic conditions"),
        ],
        sections=[
            Section("What it signifies",
                    "Longevity and death. Sorrow, grief, fear, delay. Work, "
                    "labour, service, servants and the serving classes. "
                    "Discipline, austerity, renunciation. Old age, the old, "
                    "the poor, the sick, the oppressed. Iron, lead, oil, "
                    "black things, the west. Debt, disease, obstacles. "
                    "Agriculture, mining, real estate as land worked. "
                    "Justice, karma, the long consequence.", "verse"),
            Section("Self and mind",
                    "Saturn is the capacity to keep going when nothing is "
                    "rewarding it. Strong, it gives seriousness, patience, "
                    "method, a conscience, and the kind of authority that "
                    "comes from having done the work. Weak or afflicted, it "
                    "gives fear dressed as caution, chronic delay, "
                    "pessimism, and a feeling of being outside the room.\n\n"
                    "Saturn on the Moon is the gravest of the mind "
                    "placements — steadiness bought with heaviness; on the "
                    "lagna, a serious person who looks older than their "
                    "years; with the Sun, a difficult father or difficulty "
                    "with authority; with Mars, frustration; with Venus, "
                    "love that waits; with Jupiter, faith made of "
                    "discipline (the brahma yoga pair when both are strong); "
                    "with Rahu, dread.", "convention"),
            Section("Family",
                    "Saturn is not a family planet; it is the family's "
                    "burdens. Servants, employees, dependents, the elderly "
                    "in the home, the sick who must be cared for. Saturn in "
                    "the 4th presses on the mother and the home; in the 2nd, "
                    "on the family's money and speech; in the 9th, on the "
                    "father and the family's faith. Its aspect on a family "
                    "house slows that house but seldom breaks it.",
                    "convention"),
            Section("Money",
                    "Wealth that is earned, kept and arrives late. Saturn in "
                    "the 2nd or 11th gives money by labour and holds it; in "
                    "the 6th, income through service or disputes won slowly; "
                    "in the 12th, expense on the long term. Saturn as the "
                    "lord of a wealth house gives property, land, old "
                    "assets, and a fortune that is built rather than "
                    "found. Saturn in the 8th is one of the classical "
                    "long-life placements and gives inheritance late.",
                    "convention"),
            Section("Work and standing",
                    "Saturn is the karma-kāraka — the planet of the 10th as "
                    "work itself, as distinct from the Sun's dignity and "
                    "Mercury's skill. Labour, service, administration, "
                    "engineering, mining, agriculture, oil, iron, "
                    "construction, law as judgement, anything structural or "
                    "institutional. Saturn in the 10th gives authority "
                    "earned over years, often after a fall (the classic "
                    "reading is rise, fall, and a second rise); Saturn "
                    "aspecting the 10th slows the career and makes it "
                    "last.", "convention"),
            Section("Marriage and partnership",
                    "Saturn in the 7th, or aspecting the 7th or its lord, is "
                    "the tradition's delay: marriage late, with an older or "
                    "serious partner, or a marriage that is a duty before it "
                    "is a pleasure. The books read it for trouble; the "
                    "better reading is weight — Saturn binds, and what it "
                    "binds is hard to leave and hard to enjoy at once. "
                    "Saturn's aspect on Venus or the 7th lord from a "
                    "dignified position makes a marriage that endures; from "
                    "a weak one, a marriage that is endured. In a woman's "
                    "chart Saturn on Jupiter is a husband who is older, "
                    "stern, or long in coming.", "convention"),
            Section("Children",
                    "Saturn in the 5th or aspecting it is the classical "
                    "delay in children, or fewer, or children who are "
                    "serious and responsible early. Saturn with the 5th "
                    "lord or with Jupiter is read for obstacles that lift "
                    "after Saturn's maturity.", "convention"),
            Section("Health",
                    "Chronic rather than acute: the nerves, sinews, joints, "
                    "knees and legs, teeth, bones in old age, the colon, "
                    "the ears by some authors. Cold diseases, wasting, "
                    "paralysis, depression, long fevers, conditions that "
                    "take years. Saturn is also āyuṣ-kāraka — the planet of "
                    "lifespan — and a strong Saturn in the 8th or in "
                    "Aquarius or Libra gives long life.", "verse"),
            Section("Spirit",
                    "Saturn is vairāgya — detachment earned by loss — and "
                    "the discipline of practice. It is the renunciate's "
                    "planet alongside Ketu: Saturn in the 12th, 9th or 8th, "
                    "or with Ketu or Jupiter, makes the long practitioner "
                    "rather than the sudden convert. Its spiritual gift is "
                    "the ability to sit with what cannot be changed; its "
                    "spiritual test is whether that becomes peace or "
                    "resignation.", "convention"),
            Section("Sade Sati and the Saturn returns",
                    "Saturn takes about 29½ years to circle the zodiac. Its "
                    "transit through the sign before the natal Moon, over "
                    "it, and the sign after — seven and a half years, sāḍhe "
                    "sātī — is the tradition's season of pressure and "
                    "reorganisation, worst in the middle passage over the "
                    "Moon itself. Its return to its natal sign at about 29 "
                    "and 58 marks the two great adulthoods. None of these "
                    "is a verdict; each is a period in which Saturn's "
                    "questions are asked louder.", "convention"),
            Section("Strong and weak",
                    "Strong: exalted in Libra, in Capricorn or Aquarius, in "
                    "the 7th (dig-bala), in the 3rd, 6th, 10th or 11th, "
                    "retrograde, in the dark half of the month. Gives long "
                    "life, lasting authority, property, discipline, and "
                    "the respect of people who work.\n\n"
                    "Weak: debilitated in Aries, in the 1st, 4th, 5th or 8th "
                    "with no dignity, with the Moon or Sun, combust. Gives "
                    "chronic illness, delay without reward, fear, "
                    "servitude, loss through the oppressed or the old. "
                    "A debilitated Saturn whose dispositor Mars is strong, "
                    "or that sits in a kendra from the Moon, recovers "
                    "(nīca-bhaṅga) — and a retrograde debilitated Saturn is "
                    "read by Uttara Kālāmṛta as acting like an exalted one "
                    "[verify-list].", "convention"),
        ],
        sources=[_BPHS3, _BPHS32, _PHAL, _UK, _MAT],
    ),
    Graha(
        key="rahu", name="Rahu", sanskrit="Rāhu · the north node", glyph="☊",
        tagline="Hunger, obsession, the foreign, the unconventional, sudden rise, and what you have not yet had.",
        lead=(
            "Rahu is the severed head of the demon who drank the nectar — "
            "appetite with no stomach. It is a shadow, not a body: it has "
            "no sign of its own and acts through the lord of the sign it "
            "occupies and the planets it touches. It stands for the "
            "foreign, the new, the technological, the illicit, the "
            "sudden; for paternal grandparents; for poison, illusion, "
            "fame and scandal. Where Rahu sits is where you want more than "
            "the house can give, and where you will go furthest from where "
            "you began. It matures at 42."),
        facts=[
            ("Nature", "Malefic; shadow (chāyā-graha); female by most authors; air; tamas; outcaste"),
            ("Rules", "No sign of its own. Strong in Taurus / Gemini / Virgo; co-lord of Aquarius by convention"),
            ("Exalted", "Taurus (some: Gemini)  ·  Debilitated Scorpio (some: Sagittarius) — school-dependent"),
            ("Friends", "Mercury, Venus, Saturn  ·  Neutral Jupiter  ·  Enemies Sun, Moon, Mars"),
            ("Aspect", "7th [Parāśara: none stated]; 5th and 9th also [Uttara Kālāmṛta, node school]"),
            ("Daśā", "18 years"),
            ("Matures", "42 (some: 48) [convention]"),
            ("Kāraka of", "Paternal grandfather; foreigners; the 6th and 12th by extension [convention]"),
            ("Direction", "South-west  ·  Deity Durgā / Sarpa  ·  Metal lead, mixed metals"),
            ("Body", "Poison, skin, breath, the unexplained"),
        ],
        sections=[
            Section("What it signifies",
                    "Illusion, ambition, worldly hunger. Foreigners, foreign "
                    "lands, foreign languages, emigration. Technology, "
                    "electricity, photography, the mass and the viral. "
                    "Poison, smoke, intoxicants, the serpent. Scandal, "
                    "fame, fraud, gambling. The paternal grandfather. Sudden "
                    "gain, sudden loss, eclipse. Outcastes, rebels, the "
                    "self-made and the unplaceable.", "convention"),
            Section("How a shadow acts",
                    "Rahu gives the results of its sign-lord and of any "
                    "planet it conjoins — amplified and bent. Rahu with the "
                    "Sun eclipses the self and makes a person who needs to be "
                    "seen; with the Moon, obsession and a restless mind; "
                    "with Mars, explosive force; with Mercury, cleverness "
                    "that can cheat; with Jupiter, guru-caṇḍāla — faith "
                    "distorted or faith beyond convention; with Venus, "
                    "unconventional love; with Saturn, dread and a long "
                    "labour in a foreign place. Rahu in a sign with no "
                    "planet is read through its dispositor's condition.\n\n"
                    "Rahu in the 3rd, 6th, 10th and 11th (upacaya houses) "
                    "is the tradition's best Rahu: hunger that becomes "
                    "achievement. In the 1st, 4th, 5th, 7th, 8th and 12th it "
                    "is more trouble than fuel, though a Rahu in a friend's "
                    "sign or with its dispositor strong does well "
                    "anywhere.", "convention"),
            Section("Self and mind",
                    "Rahu is the part of you that is never satisfied and "
                    "that therefore moves the whole chart forward. It is "
                    "ambition, risk, the appetite for the new. Afflicting "
                    "the Moon or lagna it is anxiety, fixation, and a "
                    "feeling of not belonging; supported, it is originality "
                    "and nerve. Rahu's lesson is the one the tradition names "
                    "— its hunger is real and the thing it hungers for is "
                    "an illusion, which is why Rahu periods give the thing "
                    "and then show its hollowness.", "convention"),
            Section("Family, work, marriage",
                    "Family: the paternal grandfather; estrangement from the "
                    "family's conventions; a home in a foreign place (Rahu "
                    "in the 4th). Work: technology, aviation, foreign "
                    "trade, media, politics, pharmaceuticals, anything new "
                    "or mass; Rahu in the 10th is the self-made career and "
                    "the sudden fall. Marriage: Rahu in the 7th or on Venus "
                    "or the 7th lord is the partner from outside — another "
                    "caste, country, religion or convention — and a "
                    "marriage that is intense and unsettled; Rahu on the "
                    "husband-significator in a woman's chart is a husband "
                    "who is foreign or unconventional [convention].",
                    "convention"),
            Section("Health",
                    "Poisons, skin disorders, phobias, insomnia, breathing "
                    "trouble, conditions that cannot be diagnosed, "
                    "addictions, epidemics. Rahu with the Moon or in the 6th "
                    "is read for mental unrest; in the 8th, for mysterious "
                    "illness; its transit over the Moon or lagna for "
                    "confusion.", "convention"),
            Section("Spirit",
                    "Rahu is māyā — the illusion that the tradition says "
                    "must be gone through, not around. Rahu in the 12th or "
                    "9th, or with Jupiter or Ketu, can give the unorthodox "
                    "mystic, the tāntrika, the one who finds the sacred in "
                    "the forbidden. Its spiritual maturity is the "
                    "recognition that the hunger was never for the object.",
                    "convention"),
            Section("The Rahu–Ketu axis",
                    "Rahu and Ketu are always opposite. Whatever house "
                    "Rahu occupies, Ketu occupies the 7th from it, and the "
                    "two are read as one axis: Rahu is where you are going "
                    "and have not yet been, Ketu where you have already "
                    "been and are leaving. The nodes move backwards, take "
                    "about 18½ years to circle, and return to their natal "
                    "places at about 18½, 37 and 55½ — the nodal returns, "
                    "each a reset of direction.", "convention"),
        ],
        sources=[_BPHS3, _UK, _PHAL, _JP, "School note: Parāśara gives the nodes no aspects of their own; Uttara Kālāmṛta gives 5th, 7th, 9th. Sidera tags every node-aspect reading '(node school)'.", _MAT],
    ),
    Graha(
        key="ketu", name="Ketu", sanskrit="Ketu · the south node", glyph="☋",
        tagline="Detachment, loss, liberation, past mastery, the maternal grandfather, and what you already know.",
        lead=(
            "Ketu is the demon's body without its head — experience with no "
            "appetite. A shadow like Rahu, it acts through its dispositor "
            "and its companions. It stands for mokṣa (liberation), "
            "renunciation, loss that frees, intuition, mathematics and "
            "astrology, the maternal grandfather, dogs, wounds, and the "
            "flag. Where Ketu sits is where you are already fluent and "
            "strangely indifferent — a skill that came easily and a house "
            "that does not hold your interest. It cuts, and what it cuts "
            "away it was never going to let you keep. It matures at 48."),
        facts=[
            ("Nature", "Malefic; shadow (chāyā-graha); neuter / male by authors; fire; tamas; outcaste"),
            ("Rules", "No sign of its own. Strong in Scorpio / Sagittarius / Pisces; co-lord of Scorpio by convention"),
            ("Exalted", "Scorpio (some: Sagittarius)  ·  Debilitated Taurus (some: Gemini) — school-dependent"),
            ("Friends", "Mars, Venus, Saturn  ·  Neutral Mercury, Jupiter  ·  Enemies Sun, Moon"),
            ("Aspect", "7th [Parāśara: none stated]; 5th and 9th also [Uttara Kālāmṛta, node school]"),
            ("Daśā", "7 years"),
            ("Matures", "48 [convention]"),
            ("Kāraka of", "Maternal grandfather; mokṣa; the 12th by extension [convention]"),
            ("Direction", "North-west / none  ·  Deity Gaṇeśa / Citragupta  ·  Metal mixed"),
            ("Body", "Wounds, fevers of unknown cause, the spine's base, intuition"),
        ],
        sections=[
            Section("What it signifies",
                    "Liberation, renunciation, detachment, the ascetic. "
                    "Loss, separation, sudden ending. Intuition, "
                    "clairvoyance, mathematics, astrology, languages known "
                    "without learning. Wounds, surgery, fevers, infections, "
                    "dogs, flags, smoke. The maternal grandfather. Secrets, "
                    "hidden knowledge, past lives in the tradition's own "
                    "framing. Mokṣa-kāraka — the planet of release.",
                    "convention"),
            Section("How a shadow acts",
                    "Ketu gives the results of its sign-lord and its "
                    "companions — narrowed, intensified, and emptied of "
                    "appetite. Ketu with the Sun is a self that does not "
                    "want to be seen; with the Moon, a mind prone to "
                    "detachment or sudden absence; with Mars, surgical "
                    "precision or injury; with Mercury, intuitive "
                    "intelligence and a dislike of small talk; with Jupiter, "
                    "the renunciate or the heterodox teacher; with Venus, "
                    "love that is spiritual or that ends in withdrawal; with "
                    "Saturn, the long ascetic discipline.\n\n"
                    "Ketu in the 3rd, 6th, 9th, 11th and 12th is "
                    "productive: it removes obstacles, enemies and "
                    "attachments. In the 1st, 2nd, 4th, 5th and 7th it "
                    "withdraws something the person wanted — identity, "
                    "family wealth, home, children, partnership — and is "
                    "the house to watch for a feeling of 'I did it, but it "
                    "did not feel like mine'.", "convention"),
            Section("Self and mind",
                    "Ketu is the part of you that has already finished and "
                    "does not know why everyone else is still interested. It "
                    "gives insight without effort, concentration that "
                    "forgets the body, and a dislike of pretence. Afflicting "
                    "the Moon or lagna it is dissociation, confusion about "
                    "who one is, and a chronic feeling of being half "
                    "elsewhere; supported, it is the natural contemplative "
                    "and the person who sees through things. Ketu periods "
                    "take things away; what remains is what was real.",
                    "convention"),
            Section("Family, work, marriage",
                    "Family: the maternal grandfather; detachment from the "
                    "family's story; a home that never quite settles (Ketu in "
                    "the 4th). Work: mathematics, astrology, computing, "
                    "surgery, research, the occult, languages, medicine of "
                    "the subtle kind; Ketu in the 10th is mastery without "
                    "ambition, often a career that happens rather than one "
                    "that is built. Marriage: Ketu in the 7th or on Venus or "
                    "the 7th lord is the classic withdrawal — a partner who "
                    "is spiritual, distant, or already known from before; "
                    "a marriage that teaches detachment; Ketu on the "
                    "husband-significator in a woman's chart is a husband "
                    "who is ascetic, older in spirit, or absent "
                    "[convention].", "convention"),
            Section("Health",
                    "Wounds, surgical conditions, fevers and infections of "
                    "unknown origin, parasites, skin eruptions, the base of "
                    "the spine, conditions that are misdiagnosed. Ketu in "
                    "the 6th is strong against disease; in the 8th, sudden "
                    "operations; with the Moon, psychosomatic complaints.",
                    "convention"),
            Section("Spirit",
                    "Ketu is mokṣa itself — the planet that lets go. It is "
                    "given to Gaṇeśa, remover of obstacles, and its best "
                    "houses are the mokṣa houses: 4th, 8th and especially "
                    "12th. Ketu in the 12th with a strong Jupiter is the "
                    "tradition's picture of liberation in this life; Ketu "
                    "in the 9th questions inherited faith until a personal "
                    "one is found; Ketu with the ātmakāraka in the "
                    "karakāṃśa is the Jaimini mark of the spiritual "
                    "adept. Its prayer is the one that feels empty until "
                    "it does not.", "convention"),
            Section("The Rahu–Ketu axis",
                    "Ketu is always opposite Rahu, and the two are read as "
                    "one line through the chart: Ketu is the house already "
                    "mastered and now being left, Rahu the house being "
                    "walked toward. Transits of the nodes run backwards "
                    "through the signs, about 18 months in each; Ketu "
                    "crossing a natal planet is a removal or a reckoning, "
                    "and its passage over the Moon, Venus, or the 7th lord "
                    "is among the dates the tradition watches most "
                    "closely.", "convention"),
        ],
        sources=[_BPHS3, _UK, _PHAL, _JP, "Jaimini Upadeśa Sūtra 1.2 (Ketu in the karakāṃśa — verify-list)", "School note as for Rahu.", _MAT],
    ),
]


# ---------------------------------------------------------------------------
# BHAVAS
# ---------------------------------------------------------------------------

_BPHS11 = "Bṛhat Parāśara Horā Śāstra, ch. 11 (bhāva significations)"
_BPHS24 = "Bṛhat Parāśara Horā Śāstra, ch. 24 (effects of bhāva lords in the twelve bhāvas)"
_PHAL1 = "Phaladīpikā, ch. 1 (bhāva significations) and ch. 15 (bhāva lords)"
_UK5 = "Uttara Kālāmṛta, kāṇḍa 5 (bhāva kārakatvas — the long lists)"
_JP_B = "Jātaka Pārijāta, ch. 11–12"

BHAVAS: list[Bhava] = [
    Bhava(
        number=1, name="First house", sanskrit="Tanu bhāva · Lagna",
        tagline="The body, the self, the beginning, and the lens every other house is seen through.",
        lead=(
            "The first house is you — the body you were given, the "
            "temperament it carries, the way you enter a room, and the "
            "health that lets you stay in it. It is the lagna, the sign "
            "rising in the east at birth, and every other house is counted "
            "from it. Its lord is the chart's chief planet: where the lagna "
            "lord goes, the life goes. A strong first house holds a "
            "difficult chart together; a weak one lets an easy chart "
            "leak."),
        facts=[
            ("Class", "Kendra (angle) and trikoṇa (trine) both — the only house that is"),
            ("Kārakas", "Sun (the self, vitality)"),
            ("Natural sign", "Aries · natural lord Mars"),
            ("Body", "Head, brain, general constitution, complexion"),
            ("Dig-bala", "Mercury and Jupiter are strongest here"),
            ("Also read from", "The Moon (candra-lagna) and the Sun (sūrya-lagna)"),
        ],
        governs=[
            "The physical body, build, complexion and appearance",
            "Health, vitality, immunity, and the general run of life",
            "Temperament, character, self-image, confidence",
            "Birth and early infancy; the start of any undertaking",
            "Fame, dignity and how the world receives you at first sight",
            "The head and the brain",
            "The lens for every other house — the lagna lord's placement is the first thing read in any question",
        ],
        sections=[
            Section("How it works",
                    "The lagna sign gives the body and temperament; its lord "
                    "gives the direction; the planets in it colour the "
                    "person directly; the planets aspecting it shape how "
                    "the person is met. A benefic in or aspecting the lagna "
                    "is protection for the whole life; a malefic in it marks "
                    "the body or the character with that planet's nature "
                    "(Saturn: serious, lean, early-ageing; Mars: scars, "
                    "heat, drive; Rahu: unplaceable, driven).\n\n"
                    "The lagna lord's house is where the life is spent: in "
                    "the 10th, work; in the 7th, partnership; in the 12th, "
                    "abroad or in retreat. Its strength tells whether the "
                    "person can carry what the chart promises.", "convention"),
            Section("Reading it with the Moon and Sun",
                    "Parāśara reads every house from three places — the "
                    "lagna, the Moon, and the Sun — and weighs the result "
                    "that two of three agree on (sudarśana). The Moon-lagna "
                    "shows the life as felt; the lagna, the life as lived in "
                    "the body; the Sun-lagna, the life as seen. A planet "
                    "that is a benefic from all three is a benefic in "
                    "fact.", "convention"),
            Section("Strength and weakness",
                    "Strong: lagna lord in a kendra or trine, exalted or in "
                    "own sign, benefics in or aspecting the lagna, Jupiter "
                    "or Mercury rising. Gives health, presence, and the "
                    "ability to turn a difficult chart to account.\n\n"
                    "Weak: lagna lord in the 6th, 8th or 12th or "
                    "debilitated, malefics in the lagna with no benefic "
                    "aspect, lagna hemmed between malefics (pāpa-kartari). "
                    "Gives poor health early, a self that is easily moved, "
                    "and a life whose promises are hard to collect — though "
                    "a strong Moon or a strong 9th can carry much of it.",
                    "convention"),
        ],
        lord_in=[
            (1, "Self-made, strong body, long life; the person is their own chief support."),
            (2, "Gains through family and speech; wealthy, learned, with a tendency to many partners by some authors."),
            (3, "Courageous, with brothers; a self expressed through effort and skill; sometimes irreligious."),
            (4, "Happy at home, with property and the mother's blessing; comfort through land and vehicles."),
            (5, "Intelligent, with children (moderate), and inclined to study and devotion; a person whose identity is in what they create."),
            (6, "Health troubled, enemies, debts; the self spent on service or struggle unless the lord is strong (then victory)."),
            (7, "A life lived through the partner; marriage central; travel; the lord's dignity decides whether the partner lifts or drains."),
            (8, "A long life by the texts' paradox, but one of transformations; occult interest, inheritances, a self that must be rebuilt."),
            (9, "Fortunate, devout, the father's blessing, learning and long journeys; one of the best placements."),
            (10, "A self defined by work and standing; honoured, self-made in the career; the lord's dignity sets how high."),
            (11, "Gains, friends, elder siblings; a life of accumulation and wide networks."),
            (12, "A life spent abroad, in retreat, or in giving; losses early that turn to liberation if the lord is strong."),
        ],
        sources=[_BPHS11, _BPHS24, _PHAL1, _UK5],
    ),
    Bhava(
        number=2, name="Second house", sanskrit="Dhana bhāva · Kuṭumba",
        tagline="Wealth held, the family you were born into, speech, food, the face, and the right eye.",
        lead=(
            "The second house is what you hold: money saved, the family of "
            "origin, the voice and the words it makes, food and drink, the "
            "face, the right eye. Parāśara also makes it a māraka — a "
            "house that can take life — because it is the 7th from the 8th. "
            "It is read with Jupiter for wealth, Mercury for speech, Venus "
            "for the family's comforts, and with the 11th for income "
            "flowing in."),
        facts=[
            ("Class", "Paṇaphara (succedent) · māraka (killer) house · a dhana (wealth) house"),
            ("Kārakas", "Jupiter (wealth, family); Mercury (speech)"),
            ("Natural sign", "Taurus · natural lord Venus"),
            ("Body", "Face, mouth, teeth, tongue, right eye, throat"),
            ("Also", "The 7th from the 8th — hence māraka; 11th from the 4th — the mother's gains"),
        ],
        governs=[
            "Wealth accumulated, savings, liquid assets, precious things kept",
            "The family of birth (kuṭumba) and the family's standing",
            "Speech, the voice, truthfulness, the power of words",
            "Food and drink, what is taken into the mouth; diet and its vices",
            "The face, the right eye, the teeth and tongue",
            "Early education and the learning carried in memory",
            "Death — as a māraka house, with the 7th",
        ],
        sections=[
            Section("How it works",
                    "Planets in the 2nd colour speech and the family: "
                    "Jupiter gives a sweet, learned tongue and family "
                    "wealth; Mercury, wit; Venus, charm and good food; Mars, "
                    "a sharp tongue and quarrels at home; Saturn, few words "
                    "and a family of duty; Rahu, a tongue that can mislead "
                    "and a family of mixed origins; the Sun, authority in "
                    "speech and a proud family.\n\n"
                    "The 2nd lord's placement shows where the money goes "
                    "and where the family's weight is felt. The 2nd and "
                    "11th together are the wealth axis: the 2nd is what is "
                    "kept, the 11th what arrives. A dhana yoga joins their "
                    "lords with each other or with the 1st, 5th or 9th "
                    "lords.", "convention"),
            Section("Marriage through the 2nd",
                    "The 2nd is the family that marriage makes: the "
                    "household after the wedding, the in-laws as a unit, "
                    "and in many lists the second marriage. A malefic in the "
                    "2nd with a weak 7th is read for friction in the marital "
                    "home; the 2nd lord with the 7th lord binds marriage and "
                    "family wealth together. The 2nd is also the 8th from "
                    "the 7th — the partner's longevity and transformations.",
                    "convention"),
            Section("Strength and weakness",
                    "Strong: 2nd lord in a kendra or trine or in the 11th, "
                    "Jupiter or Venus in the 2nd, benefic aspects. Gives "
                    "savings, a stable family, a voice people listen to.\n\n"
                    "Weak: 2nd lord in the 6th, 8th or 12th, Saturn or the "
                    "nodes in the 2nd without aid, Mars or Ketu there "
                    "(harsh speech, broken family ties). Gives money that "
                    "does not stay, trouble with the family of origin, and "
                    "complaints of the mouth and eyes.", "convention"),
        ],
        lord_in=[
            (1, "Wealth by one's own effort; family-minded; sometimes quarrelsome; sons by some authors."),
            (2, "Wealthy, proud, with a strong family; two or more marriages by the texts; the lord in its own house keeps what it holds."),
            (3, "Wealth through siblings or one's own courage; miserly or valorous by dignity; some texts: irreligious."),
            (4, "Wealth from land, vehicles and the mother; all kinds of property; comfort."),
            (5, "Wealth through children, speculation and learning; a sweet and learned speaker."),
            (6, "Wealth through enemies, disputes and service; or debts and loss — the lord's dignity decides; a biting tongue."),
            (7, "Wealth through the partner or in foreign lands; dependence on others' money; a partner who speaks for the house."),
            (8, "Loss of wealth, inheritance after struggle, few holdings; health of the family strained; wealth from the dead."),
            (9, "Wealth by fortune and the father; devout, learned, charitable; one of the best placements for money."),
            (10, "Wealth through the career and honours; respected speaker; the family's name raised by work."),
            (11, "Great gains; the two wealth houses joined; famous, with many sources of income."),
            (12, "Wealth spent, given or lost; expenditure on good causes or on vice by dignity; often earns abroad."),
        ],
        sources=[_BPHS11, _BPHS24, _PHAL1, _UK5],
    ),
    Bhava(
        number=3, name="Third house", sanskrit="Sahaja bhāva · Parākrama",
        tagline="Courage, younger siblings, effort, skill of the hands, short journeys, and the voice as communication.",
        lead=(
            "The third house is what you do by your own effort: courage, "
            "initiative, skill, the arts and crafts, writing and "
            "communication, short journeys, and the younger brothers and "
            "sisters who were the first people you competed with. It is an "
            "upacaya — a growing house — where malefics are welcome because "
            "struggle improves it. Mars is its kāraka; a strong 3rd is a "
            "person who finishes things."),
        facts=[
            ("Class", "Āpoklima (cadent) · upacaya (growing) · a kāma (desire) house"),
            ("Kārakas", "Mars (courage, siblings); Mercury (communication) by convention"),
            ("Natural sign", "Gemini · natural lord Mercury"),
            ("Body", "Arms, hands, shoulders, right ear, throat, collar-bones"),
            ("Also", "The 12th from the 4th — loss of comfort by effort; 8th from the 8th — longevity"),
        ],
        governs=[
            "Courage, valour, initiative, the will to act (parākrama)",
            "Younger brothers and sisters, and neighbours",
            "Skills, crafts, the arts of the hands, music and dance as practice",
            "Writing, communication, media, messages, correspondence",
            "Short journeys and movement within familiar territory",
            "Effort and its reward; the capacity to begin and persist",
            "The arms, hands, shoulders and right ear",
        ],
        sections=[
            Section("How it works",
                    "The 3rd is read for whether the person can push: a "
                    "strong 3rd lord or Mars there gives nerve and younger "
                    "siblings who are allies; a weak 3rd gives timidity and "
                    "trouble with them. Because it is an upacaya, Saturn, "
                    "Mars, Rahu and the Sun do well here — they give "
                    "persistence, drive and nerve — while a lone benefic "
                    "may give talent without push (Jupiter in the 3rd is "
                    "classically mixed for this reason).\n\n"
                    "Planets in the 3rd also describe the siblings: a "
                    "benefic, siblings who help; Mars, brothers; Venus, "
                    "sisters by some authors; Saturn or Ketu, few or "
                    "estranged.", "convention"),
            Section("The 3rd and longevity",
                    "The 3rd is the 8th from the 8th and so a secondary "
                    "longevity house; Saturn, the āyuṣ-kāraka, is "
                    "classically good here. The 3rd lord in the 8th or "
                    "the 8th lord in the 3rd is one of the dīrghāyu "
                    "(long-life) combinations by the texts.", "convention"),
            Section("Strength and weakness",
                    "Strong: Mars or Saturn in the 3rd, 3rd lord in a "
                    "kendra or upacaya, the Sun there. Gives courage, "
                    "skill, finished work, helpful siblings, a voice that "
                    "carries.\n\n"
                    "Weak: 3rd lord debilitated or in the 6th, 8th or 12th, "
                    "a lone afflicted benefic in it, Ketu there (sibling "
                    "loss or estrangement). Gives hesitation, projects "
                    "abandoned, and trouble with younger co-born.",
                    "convention"),
        ],
        lord_in=[
            (1, "Self-made through effort; courageous; wealth by one's own hands; some texts: few siblings."),
            (2, "Courage applied to wealth; a family of the siblings; wealth that grows by work; harsh speech."),
            (3, "Happy siblings, valour, wealth through skill; the lord strong in its own house."),
            (4, "Happy, wealthy, with property; the sibling close to home; the mother and brothers allied or at odds by dignity."),
            (5, "Children from effort; a wicked or clever mind by texts; sons and siblings tied."),
            (6, "Enemies among siblings; courage spent on disputes; wealth through conflict by dignity."),
            (7, "Marriage through siblings or in a foreign place; a partner who is a sibling's friend; some texts: a servant's marriage."),
            (8, "Loss of siblings; a thief by the harshest texts; longevity combination with the 8th lord strong."),
            (9, "Siblings fortunate; the father's help in effort; a wandering, devout, or merchant life."),
            (10, "Self-made career; honoured for effort; wealth by work and siblings' support."),
            (11, "Gains through courage and siblings; many friends; a trader's fortune."),
            (12, "Effort spent abroad or in loss; siblings separated; some texts: the father ill-fated."),
        ],
        sources=[_BPHS11, _BPHS24, _PHAL1, _UK5],
    ),
    Bhava(
        number=4, name="Fourth house", sanskrit="Sukha bhāva · Bandhu · Mātṛ",
        tagline="The mother, the home, happiness, land and vehicles, education, and the heart.",
        lead=(
            "The fourth house is where you come from and where you rest: "
            "the mother, the home as building and as feeling, land, "
            "vehicles, inner peace (sukha), formal education, the heart, "
            "and the end of life. It is the nadir, the root of the chart. "
            "Read it with the Moon for the mother and comfort, with Mars "
            "for land and buildings, with Venus for vehicles and the "
            "home's pleasures, with Mercury for schooling. A troubled 4th "
            "is a person who has success and nowhere to put it down."),
        facts=[
            ("Class", "Kendra (angle) · a mokṣa (liberation) house"),
            ("Kārakas", "Moon (mother, comfort); Mars (land); Venus (vehicles); Mercury (education)"),
            ("Natural sign", "Cancer · natural lord Moon"),
            ("Body", "Chest, heart, lungs, breasts"),
            ("Dig-bala", "Moon and Venus are strongest here"),
            ("Also", "The 10th from the 7th — the partner's career; 7th from the 10th — the private life opposite the public"),
        ],
        governs=[
            "The mother, her health and the bond with her",
            "The home: the house lived in, the household, the birthplace",
            "Happiness, contentment, peace of mind (sukha)",
            "Land, real estate, fixed property; vehicles and conveyances",
            "Formal education, schooling, degrees",
            "The heart and chest; the emotional core",
            "The end of life and the circumstances of it (with the 8th and 12th)",
        ],
        sections=[
            Section("How it works",
                    "Benefics in the 4th give comfort, property and a "
                    "present mother; malefics press on all three. Saturn in "
                    "the 4th is the classic unsettled home and a mother who "
                    "could not be leaned on; Mars there gives property with "
                    "disputes and a hot household; Rahu, a home abroad or a "
                    "home that is never quite one's own; Ketu, detachment "
                    "from roots. Jupiter, Venus or a strong Moon here are "
                    "among the best placements for a peaceful life.\n\n"
                    "The 4th lord's house shows where the home is found: "
                    "in the 10th, home and work are one; in the 12th, home "
                    "abroad; in the 7th, home through the partner. The 4th "
                    "lord and the Moon together are read for the mother's "
                    "fortunes.", "convention"),
            Section("The 4th and marriage",
                    "The 4th is the 10th from the 7th — the partner's "
                    "standing and work — and the house the couple lives in. "
                    "Planets in the 4th act on the marriage's home "
                    "directly: a malefic 4th with a sound 7th is a bond that "
                    "holds while the household strains, and the texts' "
                    "answer is a home set apart from the family of birth. "
                    "Venus in the 4th gives a beautiful married home; "
                    "Saturn, one that must be built slowly.", "convention"),
            Section("Strength and weakness",
                    "Strong: 4th lord in a kendra or trine, Moon or Venus in "
                    "the 4th, Jupiter's aspect on it, benefics in the 4th "
                    "from the Moon as well. Gives property, vehicles, a good "
                    "mother, education, and peace.\n\n"
                    "Weak: 4th lord in the 6th, 8th or 12th, Saturn, Rahu "
                    "or Ketu in the 4th unaided, the Moon afflicted "
                    "alongside. Gives a restless home, the mother's "
                    "illness or absence, interrupted education, and "
                    "success that does not comfort.", "convention"),
        ],
        lord_in=[
            (1, "Property and comfort by one's own effort; the mother's blessing; learned; a home that is the self's expression."),
            (2, "Wealth from land and the mother; family property; comforts of food and speech."),
            (3, "Comfort through effort; valorous; property with siblings; a home that is rebuilt by one's own hands."),
            (4, "Great comfort, property, vehicles, a long-lived mother; a minister's placement."),
            (5, "Happiness through children and learning; the mother devoted; comfort from study."),
            (6, "Mother troubled; property lost in disputes; comfort found in service or in overcoming."),
            (7, "Home through the partner or in a foreign place; the partner's standing high; learned."),
            (8, "Mother's health strained; property lost or inherited; comfort found late or through the occult."),
            (9, "Fortunate home, devout mother, property by inheritance from the father; comfort through faith."),
            (10, "Home and work made one; honoured; property through the career; the mother's ambitions carried."),
            (11, "Gains from property; vehicles; comfort through friends and elders; the mother long-lived."),
            (12, "Home abroad or lost; the mother distant; comfort in solitude; expenditure on property."),
        ],
        sources=[_BPHS11, _BPHS24, _PHAL1, _UK5],
    ),
    Bhava(
        number=5, name="Fifth house", sanskrit="Putra bhāva · Buddhi",
        tagline="Children, intelligence, creativity, romance, the past life's merit, mantra, and speculation.",
        lead=(
            "The fifth house is what comes out of you: children, ideas, "
            "art, love affairs, the quality of the intelligence, and the "
            "merit the tradition says you brought in with you "
            "(pūrva-puṇya). It is a trine — one of the three houses of "
            "fortune — and its lord is always a friend of the chart. Read "
            "it with Jupiter for children and wisdom, with Mercury for "
            "intellect, with Venus for romance, and with the 9th for "
            "dharma. A strong 5th is a mind that bears fruit."),
        facts=[
            ("Class", "Trikoṇa (trine) · paṇaphara · a dharma house"),
            ("Kārakas", "Jupiter (children, wisdom); Mercury (intellect) by convention"),
            ("Natural sign", "Leo · natural lord Sun"),
            ("Body", "Stomach, upper abdomen, heart by some authors, the womb's fruit"),
            ("Also", "The 11th from the 7th — the partner's gains; 9th from the 9th — the father's fortune, the guru's guru"),
        ],
        governs=[
            "Children — their coming, their number, their nature, and happiness through them",
            "Intelligence (buddhi), discrimination, memory, learning that is one's own",
            "Creativity: art, authorship, performance, invention",
            "Romance, love affairs, courtship before marriage",
            "Mantra, devotion, iṣṭa-devatā; the merit of past lives (pūrva-puṇya)",
            "Speculation, gambling, investments, sudden gains by wit",
            "Counsel: ministers, advisers, and the ability to advise",
        ],
        sections=[
            Section("How it works",
                    "Jupiter aspecting or occupying the 5th, or its lord "
                    "strong, is the first mark of children and a sound "
                    "mind. Malefics in the 5th act on children and "
                    "judgement: Saturn delays or limits; Mars heats and may "
                    "cost a first conception; Rahu gives unusual children "
                    "or obsession; Ketu, detachment from them or a child "
                    "who is a seeker; the Sun, pride between generations. "
                    "Benefics give intelligence, romance, and creative "
                    "fruit.\n\n"
                    "The 5th lord in the 6th, 8th or 12th, or the 5th "
                    "hemmed by malefics, is the classical obstacle to "
                    "children; the texts' remedies run through Jupiter "
                    "and the 9th. The 5th also shows the kind of love one "
                    "falls into before marrying: Venus there, romance; "
                    "Saturn, a love that waits or is denied; Rahu, a love "
                    "outside the lines.", "convention"),
            Section("Mind and merit",
                    "The 5th is buddhi — the discriminating intellect, as "
                    "opposed to Mercury's quickness and the Moon's mood. A "
                    "strong 5th lord with Jupiter or Mercury gives "
                    "judgement; afflicted, a clever mind that chooses "
                    "badly. The tradition reads the 5th for pūrva-puṇya, "
                    "the merit carried in: a well-placed 5th lord is a life "
                    "that is helped by what it cannot see.", "convention"),
            Section("Strength and weakness",
                    "Strong: 5th lord in a kendra or trine, Jupiter in or "
                    "aspecting the 5th, benefics there, the 5th lord with "
                    "the 9th or 1st lord (rāja yoga). Gives children, "
                    "intelligence, creative success, and good counsel.\n\n"
                    "Weak: 5th lord in the 6th, 8th or 12th or debilitated, "
                    "Saturn, Mars or the nodes in the 5th unaided, Jupiter "
                    "afflicted alongside. Gives delay or worry around "
                    "children, judgement that fails under pressure, and "
                    "losses by speculation.", "convention"),
        ],
        lord_in=[
            (1, "Learned, with children; a self defined by intellect and offspring; proud."),
            (2, "Wealth through children and intellect; a family of learning; a famous speaker."),
            (3, "Children and siblings allied; valorous; a mind applied to craft; some texts: a talebearer."),
            (4, "Happy, with a devoted mother; learned; comfort through children; a minister's placement."),
            (5, "Children, intelligence and fame; the lord in its own house gives sons and a clear mind."),
            (6, "Trouble through children or enemies among them; adoption by some texts; a mind spent on disputes."),
            (7, "Children who travel; a learned partner; marriage for love; honoured abroad."),
            (8, "Few children or loss of them; a mind turned to the occult; asthma and chest trouble by texts."),
            (9, "Fortunate children; a devout and famous mind; the father and sons allied; one of the great rāja-yoga pairs."),
            (10, "Children who rise; a mind that earns honour; rāja yoga with the 10th lord strong."),
            (11, "Children and gains; learned, authorial, famous; the 5th and 11th are the axis of ideas and their reward."),
            (12, "Children abroad or lost; a mind turned to liberation; expenditure on children's education; secret learning."),
        ],
        sources=[_BPHS11, _BPHS24, _PHAL1, _UK5],
    ),
    Bhava(
        number=6, name="Sixth house", sanskrit="Ripu bhāva · Roga · Ṛṇa",
        tagline="Enemies, disease, debt, service, competition, maternal uncles, and the daily struggle that makes you strong.",
        lead=(
            "The sixth house is what you fight: enemies, illness, debt, "
            "litigation, servants and employees, the daily work of "
            "service, maternal uncles, and the obstacles that have to be "
            "overcome rather than avoided. It is a duṣṭhāna — a difficult "
            "house — and also an upacaya, so malefics here are welcome: "
            "they win. Benefics in the 6th are the gentle person who loses "
            "the fight. Read it with Mars for enemies and competition, "
            "Saturn for disease and service, Mercury for maternal uncles."),
        facts=[
            ("Class", "Duṣṭhāna (difficult) · upacaya (growing) · āpoklima · an artha (means) house"),
            ("Kārakas", "Mars (enemies); Saturn (disease, service); Mercury (maternal relatives)"),
            ("Natural sign", "Virgo · natural lord Mercury"),
            ("Body", "Intestines, lower abdomen, digestion, the navel"),
            ("Also", "The 12th from the 7th — the partner's losses; 3rd from the 4th — the mother's siblings"),
        ],
        governs=[
            "Enemies, rivals, competitors, open opposition",
            "Disease, especially acute illness, and the body's capacity to resist it",
            "Debt, loans, obligations owed",
            "Service, employment under others, daily work, employees and servants",
            "Litigation, disputes, courts, theft and loss by wrongdoing",
            "Maternal uncles and aunts; pets and small animals",
            "Effort against resistance — the house of the fight won",
        ],
        sections=[
            Section("How it works",
                    "The 6th is read upside down: strong malefics there "
                    "defeat enemies, resist disease and pay down debt; "
                    "benefics there are kind to the enemy and soft against "
                    "illness. Mars in the 6th wins disputes; Saturn there "
                    "outlasts them; the Sun there defeats rivals and may "
                    "have a father who is one; Rahu there is strong against "
                    "enemies and foreign in its work; Ketu removes them.\n\n"
                    "The 6th lord is the planet to watch: wherever it goes, "
                    "it brings enemies, disease or debt to that house. The "
                    "6th lord in the 6th, 8th or 12th (vipārīta rāja yoga) "
                    "turns the trouble on itself and gives gain through "
                    "others' loss; the 6th lord in the 1st or 7th brings "
                    "the fight to the body or the marriage.", "convention"),
            Section("Work through the 6th",
                    "The 6th is employment as distinct from the 10th's "
                    "career: the daily job, the employer, the staff, the "
                    "service rendered. A strong 6th gives a good employee "
                    "and good employees; the 6th lord with the 10th lord is "
                    "work in medicine, law, the military, or any field that "
                    "fights something.", "convention"),
            Section("Strength and weakness",
                    "Strong (for the native): malefics in the 6th, the 6th "
                    "lord weak or in another duṣṭhāna, the lagna lord "
                    "stronger than the 6th lord. Gives victory, health that "
                    "recovers, and debts repaid.\n\n"
                    "Weak: benefics alone in the 6th, the 6th lord strong "
                    "and in a kendra or on the lagna, the lagna lord in the "
                    "6th without dignity. Gives chronic illness, enemies "
                    "who win, debt that compounds, and a life of service "
                    "without reward.", "convention"),
        ],
        lord_in=[
            (1, "Illness and enemies on the body; a self in service; famous, but with a sickly constitution by texts."),
            (2, "Wealth through disputes and service; harsh speech; a family of enemies; trouble with the mouth."),
            (3, "Enemies among siblings; valorous; wins by effort; the fight carried by one's own hands."),
            (4, "The mother troubled; property disputed; an unhappy home unless the lord is strong; mental unrest."),
            (5, "Children troubled; a mind in dispute; enmity with offspring; wealth fluctuates by texts."),
            (6, "Enemies destroyed by their own kind; vipārīta rāja yoga; good health late; strong against disease."),
            (7, "Marriage brings disputes; a partner who is an enemy or an employee; the 6th's trouble on the 7th."),
            (8, "Enemies and illness self-destroy; vipārīta rāja yoga; long life by texts; wealth through the dead."),
            (9, "The father troubled; fortune by service or litigation; trade in timber and stone by texts."),
            (10, "Career in service, medicine, law or the military; honoured through fights won; employer troubled."),
            (11, "Gains through enemies and disputes; wealth by service; elder siblings at odds."),
            (12, "Enemies lost; vipārīta rāja yoga; expenditure on illness or litigation; debts dissolved abroad."),
        ],
        sources=[_BPHS11, _BPHS24, _PHAL1, _UK5],
    ),
    Bhava(
        number=7, name="Seventh house", sanskrit="Kalatra bhāva · Jāyā · Dyūna",
        tagline="Marriage, the spouse, partnership of every kind, the public, desire, and the second māraka.",
        lead=(
            "The seventh house is the other: the spouse, the business "
            "partner, the open enemy, the public you face. It is the "
            "descendant, exactly opposite the self, and the house every "
            "marriage question begins with. Its lord describes the partner "
            "and where they are found; the planets in it, the partner's "
            "nature and the marriage's weather; Venus is its kāraka for "
            "both sexes, Jupiter the husband in a woman's chart. It is "
            "also a māraka house and the seat of desire (kāma). A strong "
            "7th is a life that is shared."),
        facts=[
            ("Class", "Kendra (angle) · māraka (killer) · a kāma (desire) house"),
            ("Kārakas", "Venus (spouse, partnership — both sexes); Jupiter (husband, woman's chart)"),
            ("Natural sign", "Libra · natural lord Venus"),
            ("Body", "Kidneys, lower back, reproductive organs, the pelvis"),
            ("Dig-bala", "Saturn is strongest here"),
            ("Also", "The 4th from the 4th — the mother's home; 10th from the 10th — the career's career; the house of the partner's lagna"),
        ],
        governs=[
            "Marriage: its coming, its timing, its quality, and its number",
            "The spouse — nature, appearance, standing, origin, and the bond itself",
            "Partnership in business, contracts, alliances, the open opponent",
            "Sexual desire and its satisfaction (kāma)",
            "The public, trade, dealings with others, foreign travel and residence",
            "Death — as a māraka, with the 2nd",
            "The kidneys, lower back and reproductive system",
        ],
        sections=[
            Section("How it works",
                    "Three things are read together for every marriage: "
                    "the 7th house (occupants and aspects), its lord "
                    "(house, sign, dignity, company), and the kāraka — "
                    "Venus for both, Jupiter for a woman's husband. A "
                    "benefic 7th with a dignified lord and an unafflicted "
                    "kāraka is a marriage that comes in time and holds. "
                    "The same houses are then read from the Moon, and from "
                    "Venus, and the result two of three agree on is taken.\n\n"
                    "Planets in the 7th describe the partner and the "
                    "marriage's climate: Jupiter, a wise and protective "
                    "partner; Venus, a beautiful one and strong desire "
                    "(the kāraka in its own house — some texts: more than "
                    "one); Mercury, a young, talkative partner; the Moon, "
                    "an emotional, changeable one; the Sun, a proud one and "
                    "a marriage of two authorities; Mars, heat, quarrels, "
                    "the kuja doṣa; Saturn, an older or serious partner "
                    "and delay, but a bond that lasts (dig-bala); Rahu, a "
                    "partner from outside convention; Ketu, a spiritual or "
                    "distant one and a marriage that teaches detachment.",
                    "convention"),
            Section("Timing a marriage",
                    "The tradition times marriage by the daśā of the 7th "
                    "lord, of planets in the 7th, of Venus or Jupiter as "
                    "kāraka, or of the lord of the 7th from the Moon — "
                    "together with transits: Jupiter aspecting or "
                    "occupying the 7th, the 7th lord, the lagna or the "
                    "Moon; Saturn adding its aspect (the modern double "
                    "transit rule); the nodes crossing the 7th or its lord. "
                    "A period that lights the 7th from two of the three "
                    "lagnas is the one to watch.", "convention"),
            Section("Delay and difficulty",
                    "Saturn in or aspecting the 7th or its lord: late and "
                    "serious. Mars there: friction, the doṣa, haste. The "
                    "nodes there: a marriage outside the usual lines, or "
                    "one that is unsettled. The 7th lord in the 6th, 8th or "
                    "12th: a partner met through struggle, loss or abroad, "
                    "and a marriage that must be worked for. Venus "
                    "combust or debilitated: the capacity for tenderness "
                    "dimmed. None of these alone ends a marriage; the "
                    "texts count them, weigh Jupiter's aspect against "
                    "them, and read the navāṃśa before they speak.",
                    "convention"),
            Section("The navāṃśa (D9)",
                    "The 7th is the one house the tradition insists be read "
                    "in a second chart. The navāṃśa — the ninth division — "
                    "is the chart of marriage and of the self in it: its "
                    "lagna is the married person, its 7th the married "
                    "partner, and a planet weak in the birth chart but "
                    "strong in the navāṃśa keeps its promise in marriage. "
                    "Venus and Jupiter in the navāṃśa are read with the "
                    "same care as in the birth chart.", "convention"),
            Section("Strength and weakness",
                    "Strong: 7th lord in a kendra or trine with dignity, "
                    "Jupiter or Venus in or aspecting the 7th, Saturn there "
                    "with dignity (it holds), benefics in the 7th from the "
                    "Moon and Venus as well. Gives a marriage that comes "
                    "and stays, good partnerships, and a public that "
                    "receives one well.\n\n"
                    "Weak: 7th lord in the 6th, 8th or 12th or debilitated, "
                    "malefics in the 7th without benefic aspect, Venus "
                    "afflicted, the 7th hemmed between malefics. Gives "
                    "delay, friction, separation, partnerships that cost, "
                    "and the kidneys or pelvis as the body's weak point.",
                    "convention"),
        ],
        lord_in=[
            (1, "A partner met early or through one's own circle; the self defined by marriage; travel; some texts: licentious."),
            (2, "Wealth through the partner; a partner from the family's circle; many partners by texts if afflicted."),
            (3, "A partner through siblings; courage in partnership; a partner who is a friend of the younger co-born."),
            (4, "A partner who brings home and property; a happy married home; a devoted partner; the mother and partner close."),
            (5, "Marriage for love; a learned partner; children from the union; honour through the partner."),
            (6, "A partner met through work, illness or dispute; marriage troubled by enemies or debt; the partner's health strained."),
            (7, "A partner of standing; the lord strong in its own house; a happy marriage, with some pride."),
            (8, "A partner who is ill, distant, or lost; marriage that transforms the person; wealth through the partner's inheritance."),
            (9, "A fortunate partner, devout, from a good family; marriage that brings fortune; a partner met through travel or teachers."),
            (10, "A partner of position; marriage and career joined; a partner who works; honour through alliance."),
            (11, "A partner who brings gains and friends; marriage through elders or networks; more than one by some texts."),
            (12, "A partner from abroad or marriage abroad; expenditure through the partner; bed-pleasure; separation if afflicted."),
        ],
        sources=[_BPHS11, _BPHS24, _PHAL1, _UK5, _JP_B],
    ),
    Bhava(
        number=8, name="Eighth house", sanskrit="Āyur bhāva · Mṛtyu · Randhra",
        tagline="Longevity, death and rebirth, sudden events, inheritance, the occult, the partner's wealth, and chronic illness.",
        lead=(
            "The eighth house is what happens to you: longevity and its "
            "end, sudden change, accidents, inheritance, insurance, the "
            "partner's money, secrets, the occult, chronic and hidden "
            "disease, and the transformations a life goes through without "
            "asking. It is the hardest of the duṣṭhānas and also a mokṣa "
            "house — what it takes, it takes to free. Saturn is its kāraka "
            "and, paradoxically, does well here for long life. A strong "
            "8th is a person who survives what should have ended them."),
        facts=[
            ("Class", "Duṣṭhāna (the most difficult) · paṇaphara · a mokṣa house"),
            ("Kārakas", "Saturn (longevity, chronic conditions)"),
            ("Natural sign", "Scorpio · natural lord Mars (co-lord Ketu by convention)"),
            ("Body", "Reproductive and excretory organs, the perineum, chronic and hidden conditions"),
            ("Also", "The 2nd from the 7th — the partner's wealth and family; 12th from the 9th — loss of fortune and the father"),
        ],
        governs=[
            "Longevity (āyus) and the manner of death",
            "Sudden events, accidents, crises, the unforeseen",
            "Inheritance, legacies, insurance, the partner's money and debts",
            "The occult, research, secrets, what is hidden and dug up",
            "Chronic and hidden disease; surgery",
            "Transformation, loss that remakes, rebirth within the life",
            "Disgrace and recovery from it; obstacles of the deep kind",
        ],
        sections=[
            Section("How it works",
                    "The 8th lord is the chart's most dangerous planet: "
                    "wherever it goes it brings sudden change, loss or "
                    "scandal to that house, unless it is the lagna lord too "
                    "(Aries and Libra rising) or it falls in another "
                    "duṣṭhāna (vipārīta rāja yoga — gain through others' "
                    "loss). Planets in the 8th are weakened for their own "
                    "significations but strengthened for longevity and "
                    "the occult: Saturn there is long life; Jupiter, "
                    "inheritance and a protected end; the Sun, the father's "
                    "loss or distance; the Moon, a mind drawn to the "
                    "hidden; Mars, accidents and surgery; Venus, wealth "
                    "through the partner and a sensual nature; Mercury, "
                    "research; Rahu, mysterious illness and sudden gain; "
                    "Ketu, the occultist.\n\n"
                    "Longevity is never read from the 8th alone: the "
                    "texts weigh the lagna lord, the 8th lord, Saturn, "
                    "the Moon and the 3rd together, and Sidera does not "
                    "state lifespans.", "convention"),
            Section("The 8th and marriage",
                    "The 8th is the 2nd from the 7th — the partner's wealth, "
                    "family and speech — and the house of the marital bed's "
                    "secrets. In a woman's chart the 8th is also māṅgalya, "
                    "the husband's longevity and the marriage's "
                    "continuance [Strī Jātaka convention]: benefics there "
                    "protect it, malefics press on it. The 8th lord with "
                    "the 7th lord binds marriage to transformation.",
                    "convention"),
            Section("Strength and weakness",
                    "Strong (for the native): the 8th lord weak or in a "
                    "duṣṭhāna, benefics in the 8th, Saturn there with "
                    "dignity, the lagna lord stronger than the 8th lord. "
                    "Gives long life, inheritance, deep research, and "
                    "survival of crises.\n\n"
                    "Weak: the 8th lord strong and on the lagna, Moon or "
                    "7th, malefics in the 8th without aid, the 8th lord "
                    "with the lagna lord. Gives chronic illness, sudden "
                    "losses, scandal, and a life that keeps being "
                    "interrupted.", "convention"),
        ],
        lord_in=[
            (1, "Health troubled, the body marked; a self rebuilt; famous for the wrong reasons unless the lord is also lagna lord."),
            (2, "Loss of wealth and family; trouble with the mouth and eyes; wealth after the death of another."),
            (3, "Loss of siblings or a sibling's loss; cowardice by texts; longevity combination with the 3rd lord strong."),
            (4, "The mother's health or the home disturbed; property lost or inherited; a home that must be left."),
            (5, "Children troubled or few; a dull or occult mind; loss of offspring by harsh texts."),
            (6, "Vipārīta rāja yoga: enemies and disease destroyed; wealth through others' loss; victory after crisis."),
            (7, "A partner who is ill or lost; marriage that transforms; two marriages by texts; the partner's wealth."),
            (8, "Long life; the lord in its own house; a researcher of the hidden; inheritance; a quiet end."),
            (9, "The father troubled or lost early; fortune delayed; a heterodox faith; the guru's loss."),
            (10, "Career interrupted or transformed; a fall and recovery; work in insurance, research, surgery, the occult."),
            (11, "Gains lost suddenly or gained suddenly; elder siblings troubled; wealth through inheritance late."),
            (12, "Vipārīta rāja yoga: losses lost; expenditure on illness; liberation through crisis; a death abroad or in retreat."),
        ],
        sources=[_BPHS11, _BPHS24, _PHAL1, _UK5],
    ),
    Bhava(
        number=9, name="Ninth house", sanskrit="Dharma bhāva · Bhāgya · Pitṛ",
        tagline="Fortune, the father, the guru, faith, higher learning, long journeys, and the law one lives by.",
        lead=(
            "The ninth house is what carries you: fortune (bhāgya), the "
            "father, the teacher, religion and philosophy, higher learning, "
            "long journeys and pilgrimage, law and ethics, and grace — the "
            "help that arrives without being earned. It is the best of the "
            "trines, the house the tradition calls the most auspicious in "
            "the chart. Its lord is the chart's most benefic planet, "
            "whatever its nature. Read it with the Sun for the father and "
            "Jupiter for the guru and dharma. A strong 9th is a life that "
            "lands on its feet."),
        facts=[
            ("Class", "Trikoṇa (the best trine) · āpoklima · a dharma house"),
            ("Kārakas", "Sun (the father); Jupiter (the guru, dharma, fortune)"),
            ("Natural sign", "Sagittarius · natural lord Jupiter"),
            ("Body", "Hips, thighs, the arterial system by some authors"),
            ("Also", "The 3rd from the 7th — the partner's siblings and courage; 5th from the 5th — grandchildren; 6th from the 4th — the mother's illness"),
        ],
        governs=[
            "Fortune, luck, grace — bhāgya; the general favour of the life",
            "The father, his standing, and the bond with him",
            "The guru, teachers, mentors, and the wisdom received",
            "Religion, faith, philosophy, dharma — the law one lives by",
            "Higher education, universities, scholarship",
            "Long journeys, foreign travel, pilgrimage",
            "Law, ethics, justice; the grandchildren (5th from the 5th)",
        ],
        sections=[
            Section("How it works",
                    "The 9th lord is always benefic for the chart and its "
                    "placement shows where fortune enters: in the 10th, "
                    "through work (the dharma-karma-adhipati yoga, one of "
                    "the greatest); in the 1st, through the self; in the "
                    "7th, through the partner; in the 12th, abroad. "
                    "Benefics in the 9th give faith, a good father, "
                    "learning and luck; malefics test them: Saturn, a "
                    "stern father and a faith made of discipline; Mars, a "
                    "father who fights and a crusading faith; Rahu, a "
                    "foreign or heterodox faith; Ketu, faith that must be "
                    "found again after inherited faith goes empty; the "
                    "Sun, the father's authority as the law.\n\n"
                    "The 9th and 5th together are the dharma axis — what "
                    "one receives from above and passes below — and their "
                    "lords in exchange or conjunction are among the "
                    "strongest rāja yogas.", "convention"),
            Section("The father",
                    "The father is read from the 9th (Parāśara) and from "
                    "the Sun; some southern authors use the 10th. His "
                    "health is the 9th's 8th (the 4th), his fortunes the "
                    "9th lord's dignity, the bond the planets between the "
                    "Sun and the 9th lord. A strong 9th with a weak Sun is "
                    "a fortunate life and a difficult father; the reverse, "
                    "a strong father and a life that must earn its luck.",
                    "convention"),
            Section("Strength and weakness",
                    "Strong: 9th lord in a kendra or trine with dignity, "
                    "Jupiter in or aspecting the 9th, benefics there, the "
                    "9th lord with the 10th or 1st lord. Gives fortune, a "
                    "good father, teachers who matter, faith, and long "
                    "journeys that pay.\n\n"
                    "Weak: 9th lord in the 6th, 8th or 12th or debilitated, "
                    "malefics in the 9th unaided, the Sun afflicted "
                    "alongside. Gives luck that arrives late, trouble "
                    "with the father, teachers who disappoint, and a faith "
                    "tested before it is held.", "convention"),
        ],
        lord_in=[
            (1, "Fortunate, honoured, devout; the father's blessing on the self; a learned and handsome person by texts."),
            (2, "Wealth by fortune and the father; a learned family; a sweet and truthful speaker."),
            (3, "Fortune through siblings and effort; a wandering, devout life; valorous."),
            (4, "Fortune in home and property; the mother and father allied; a comfortable, devout home; vehicles."),
            (5, "Fortunate children; devout; a great rāja yoga with the 5th lord; famous for learning."),
            (6, "Fortune delayed by enemies or illness; the father troubled; fortune through service or litigation; maternal relatives."),
            (7, "A fortunate marriage; the partner brings luck; fortune abroad; a devout partner."),
            (8, "Fortune lost or hidden; the father's loss or distance; inheritance; a heterodox faith."),
            (9, "Great fortune; the lord in its own house; devout, learned, with a long-lived father; a teacher of teachers."),
            (10, "Dharma-karma yoga: fortune through work; high office; honoured; the father's standing carried forward."),
            (11, "Gains by fortune; wealth from the father and elders; friends in high places; many journeys."),
            (12, "Fortune abroad or spent; the father distant; a pilgrim; expenditure on faith and learning; liberation."),
        ],
        sources=[_BPHS11, _BPHS24, _PHAL1, _UK5],
    ),
    Bhava(
        number=10, name="Tenth house", sanskrit="Karma bhāva · Rājya",
        tagline="Work, career, standing, authority, public life, the deed, and what you are known for.",
        lead=(
            "The tenth house is what you do in the world and what the "
            "world calls you for it: career, profession, authority, "
            "reputation, public office, achievement, the deed (karma). It "
            "is the midheaven, the highest point, and the most powerful of "
            "the kendras. Four planets share its kārakatva — the Sun "
            "(dignity), Mercury (skill), Jupiter (honour) and Saturn (the "
            "labour itself) — and the 10th from the Moon is read as "
            "carefully as the 10th from the lagna. A strong 10th is a life "
            "that is seen."),
        facts=[
            ("Class", "Kendra (the strongest angle) · upacaya (growing) · an artha house"),
            ("Kārakas", "Sun (authority); Mercury (skill); Jupiter (honour); Saturn (work)"),
            ("Natural sign", "Capricorn · natural lord Saturn"),
            ("Body", "Knees, joints, the spine's bearing"),
            ("Dig-bala", "Sun and Mars are strongest here"),
            ("Also", "The 4th from the 7th — the partner's home and mother; 2nd from the 9th — the father's wealth; 7th from the 4th — public against private"),
        ],
        governs=[
            "Career, profession, vocation; the nature of the work",
            "Authority, rank, office, government and public position",
            "Reputation, fame, honour, how one is known",
            "Achievement, ambition, success and its height",
            "Karma — the deed, action in the world, and its consequence",
            "The employer, the boss, the state; one's own command over others",
            "The knees and joints; the body's bearing in public",
        ],
        sections=[
            Section("How it works",
                    "Career is read from four things: the 10th house and "
                    "its occupants, the 10th lord's house and sign, the "
                    "planets in the 10th from the Moon, and the lord of the "
                    "navāṃśa the 10th lord occupies (the classical pointer "
                    "to the field of work). Planets in the 10th act in "
                    "public: the Sun gives authority and government; the "
                    "Moon, popularity and public-facing work; Mars, "
                    "command, engineering, the forces (dig-bala); Mercury, "
                    "commerce and many lines; Jupiter, a respected "
                    "profession and honours; Venus, the arts and work done "
                    "by charm; Saturn, labour, administration and authority "
                    "earned late, with the classic rise-fall-rise; Rahu, "
                    "the self-made and the sudden; Ketu, mastery without "
                    "ambition.\n\n"
                    "The 10th lord's house shows where the work is done "
                    "and for whom: in the 1st, self-employed; in the 7th, "
                    "in partnership or trade; in the 9th, through teaching, "
                    "law or faith; in the 12th, abroad or in institutions; "
                    "in the 6th, in service, medicine or law. The 10th "
                    "lord with the 9th lord is the dharma-karma yoga; with "
                    "the 1st lord, a self-made standing; with the 11th "
                    "lord, work that pays.", "convention"),
            Section("The 10th from the Moon",
                    "The 10th from the lagna is the career as the world "
                    "sees it; the 10th from the Moon is the career as the "
                    "person experiences it. The tradition weighs both and "
                    "gives the result two of three lagnas agree on. A "
                    "planet in the 10th from the Moon colours the work as "
                    "much as one in the 10th from the lagna, and the "
                    "transit of Jupiter or Saturn through the 10th from the "
                    "Moon is one of the standard timings for a change in "
                    "position.", "convention"),
            Section("Strength and weakness",
                    "Strong: 10th lord in a kendra or trine with dignity, "
                    "the Sun or Mars in the 10th, Jupiter aspecting it, "
                    "benefics in the 10th from the Moon, the 10th lord "
                    "with the 9th or 1st lord. Gives career, authority, "
                    "reputation and a public that remembers.\n\n"
                    "Weak: 10th lord in the 6th, 8th or 12th or "
                    "debilitated, the 10th empty and unaspected with a weak "
                    "lord, malefics there without dignity, Saturn or Rahu "
                    "afflicting both the 10th and its lord. Gives a career "
                    "that starts late or changes often, authority that is "
                    "resisted, and work that does not match the person.",
                    "convention"),
        ],
        lord_in=[
            (1, "Self-made; famous by one's own deeds; learned, wealthy; a career that is the self."),
            (2, "Wealth through work; a family of standing; career in speech, finance, food; honoured in the family."),
            (3, "Career through effort, siblings, writing or communication; valorous; a self-employed worker."),
            (4, "Career in property, vehicles, education or the home; honoured mother; work and home made one; a minister's placement."),
            (5, "Career through intellect, children, speculation or the arts; a minister or adviser; famous for learning."),
            (6, "Career in service, medicine, law or the military; enemies at work; work that fights something; trouble with the employer."),
            (7, "Career through partnership, trade or the public; a partner of standing; work abroad; honoured through alliance."),
            (8, "Career interrupted, transformed, or in the hidden professions; a fall and recovery; work in research, insurance, the occult."),
            (9, "Dharma-karma yoga: career through teaching, law, faith or long journeys; the father's standing; honoured and devout."),
            (10, "The lord in its own house: a high career, authority, fame; a self fulfilled in work."),
            (11, "Career that pays; gains through work and elders; many sources; famous and wealthy."),
            (12, "Career abroad, in institutions, hospitals, ashrams or the foreign service; expenditure through work; authority behind the scenes."),
        ],
        sources=[_BPHS11, _BPHS24, _PHAL1, _UK5],
    ),
    Bhava(
        number=11, name="Eleventh house", sanskrit="Lābha bhāva · Āya",
        tagline="Gains, income, elder siblings, friends and networks, hopes, and the fulfilment of desire.",
        lead=(
            "The eleventh house is what comes to you: income, profit, "
            "gains of every kind, elder brothers and sisters, friends, "
            "networks, patrons, and the fulfilment of wishes. It is the "
            "strongest of the upacaya houses — every planet in it grows — "
            "and malefics do as well here as benefics. Jupiter is its "
            "kāraka for gains; the 2nd is its partner in wealth. Its lord "
            "is formally a malefic by Parāśara's rule (a trisadāya lord), "
            "because gain without measure is greed. A strong 11th is a "
            "life whose wishes are met."),
        facts=[
            ("Class", "Upacaya (the strongest) · paṇaphara · a kāma house · trisadāya (3-6-11) by Parāśara"),
            ("Kārakas", "Jupiter (gains); Mars by some authors (the elder brother)"),
            ("Natural sign", "Aquarius · natural lord Saturn (co-lord Rahu by convention)"),
            ("Body", "Calves, shins, left ear, the circulation by some authors"),
            ("Also", "The 5th from the 7th — the partner's children and intellect; 3rd from the 9th — the father's siblings"),
        ],
        governs=[
            "Income, profit, gains, the fruit of the career",
            "Elder brothers and sisters",
            "Friends, allies, networks, patrons, the community one belongs to",
            "Hopes, wishes, ambitions and their fulfilment",
            "Recovery from illness (the 6th from the 6th)",
            "The left ear, calves and shins",
            "Desire fulfilled — the last of the kāma houses",
        ],
        sections=[
            Section("How it works",
                    "Every planet in the 11th gives gains in its own "
                    "manner: the Sun, through authority; the Moon, through "
                    "the public; Mars, through courage, property and "
                    "brothers; Mercury, through trade and friends; Jupiter, "
                    "through wisdom and children; Venus, through the arts "
                    "and partners; Saturn, through labour, late and large; "
                    "Rahu, through the foreign and the sudden; Ketu, "
                    "through detachment or in ways that do not satisfy.\n\n"
                    "The 11th lord's house shows where the gains come "
                    "from — in the 2nd, the dhana axis complete; in the "
                    "10th, work that pays; in the 7th, through the partner; "
                    "in the 5th, through children, speculation or the "
                    "mind. Parāśara's warning that the 11th lord is a "
                    "functional malefic is read as: its gains come with "
                    "the trisadāya's hunger, and its daśā gives wealth "
                    "with worry.", "convention"),
            Section("Friends and elders",
                    "The 11th is read for elder siblings as the 3rd is for "
                    "younger, and for the friends who function as patrons. "
                    "A malefic there can mean elder siblings who are "
                    "difficult or lost; a benefic, siblings and friends who "
                    "lift. The 11th from the Moon is the person's felt "
                    "community.", "convention"),
            Section("Strength and weakness",
                    "Strong: any dignified planet in the 11th, the 11th "
                    "lord in a kendra, trine or the 2nd, Jupiter's aspect, "
                    "benefics in the 11th from the Moon. Gives income, "
                    "friends, elder siblings who help, and wishes that "
                    "come true.\n\n"
                    "Weak: the 11th empty with its lord in the 6th, 8th or "
                    "12th or debilitated, the 11th hemmed by malefics. "
                    "Gives income that does not match effort, friends who "
                    "take, and hopes deferred.", "convention"),
        ],
        lord_in=[
            (1, "Gains by one's own effort; wealthy, with elder siblings; a self that attracts; sometimes a poet by texts."),
            (2, "Great wealth; the two wealth houses joined; a prosperous family; a sweet speaker; charitable."),
            (3, "Gains through siblings and effort; skilled; valorous; sometimes a loss of a sibling."),
            (4, "Gains from property, vehicles and the mother; a comfortable home; the mother long-lived."),
            (5, "Gains through children, learning and speculation; a famous, learned person; children who prosper."),
            (6, "Gains through enemies, disputes, service or illness; income with struggle; maternal relatives."),
            (7, "Gains through the partner and partnerships; a generous or many-partnered person by texts; trade abroad."),
            (8, "Gains lost or gained suddenly; inheritance; a long life by texts; setbacks in income."),
            (9, "Gains by fortune and the father; devout; wealthy and charitable; friends among teachers."),
            (10, "Gains through the career; honoured; a king's favourite by texts; wealth by work."),
            (11, "The lord in its own house: great gains, many friends, elder siblings who prosper; wishes fulfilled."),
            (12, "Gains spent or earned abroad; friends who cost; charitable; income through institutions or in foreign lands."),
        ],
        sources=[_BPHS11, _BPHS24, _PHAL1, _UK5],
    ),
    Bhava(
        number=12, name="Twelfth house", sanskrit="Vyaya bhāva · Mokṣa",
        tagline="Loss, expense, foreign lands, bed-pleasure, sleep, isolation, charity, the hidden, and liberation.",
        lead=(
            "The twelfth house is what leaves you: expenditure, loss, "
            "foreign residence and emigration, hospitals and institutions, "
            "prisons and ashrams, sleep and dreams, the pleasures of the "
            "bed, charity, secret enemies, and mokṣa — liberation, the "
            "final letting-go. It is the last duṣṭhāna and the last mokṣa "
            "house, the one that empties so the cycle can begin again. "
            "Saturn and Ketu are its kārakas. Benefics here lose their "
            "worldly force and gain in the subtle; Venus is the exception "
            "and thrives. A strong 12th is a person who knows how to give "
            "things up."),
        facts=[
            ("Class", "Duṣṭhāna (difficult) · āpoklima · a mokṣa house"),
            ("Kārakas", "Saturn (loss, isolation); Ketu (liberation) by convention"),
            ("Natural sign", "Pisces · natural lord Jupiter"),
            ("Body", "Feet, the left eye, sleep, the lymphatic system by some authors"),
            ("Also", "The 6th from the 7th — the partner's illness and enemies; 4th from the 9th — the father's home; 2nd from the 11th — the gains' wealth"),
        ],
        governs=[
            "Expenditure, loss, waste; what is spent and what is given",
            "Foreign lands, emigration, residence far from the birthplace",
            "Isolation: hospitals, prisons, monasteries, retreats, confinement",
            "Sleep, dreams, the subconscious; bed-pleasure (śayana-sukha)",
            "Charity, donation, renunciation; secret enemies and hidden losses",
            "Liberation, mokṣa; the end of the cycle; the life after",
            "The feet and the left eye",
        ],
        sections=[
            Section("How it works",
                    "The 12th is read for where the life leaks and where "
                    "it lets go. The 12th lord's house shows where the "
                    "expense is: in the 2nd, on family and food; in the 4th, "
                    "on property and the mother; in the 7th, on the partner; "
                    "in the 10th, on the career; in the 9th, on faith and "
                    "journeys. The 12th lord in the 6th or 8th turns loss on "
                    "itself (vipārīta rāja yoga) and is a gain; on the "
                    "lagna, a person who spends themselves.\n\n"
                    "Planets in the 12th act abroad, in private, or in the "
                    "subtle: the Sun, a father distant or a life in foreign "
                    "service; the Moon, a mind that wanders and sleeps "
                    "badly, or a mystic; Mars, expenditure by anger, "
                    "surgery, work abroad; Mercury, secret learning; "
                    "Jupiter, charity, a faith lived quietly, and a "
                    "protected end; Venus, bed-pleasure, foreign comfort "
                    "and a partner from afar — the classic good placement; "
                    "Saturn, isolation, the long ascetic discipline, "
                    "expenditure on the old and the sick; Rahu, foreign "
                    "residence and strange dreams; Ketu, liberation.",
                    "convention"),
            Section("The 12th and marriage",
                    "The 12th is bed-pleasure in the texts — the intimate "
                    "life of a marriage — and the 6th from the 7th, the "
                    "partner's enemies and illness. Venus or the Moon here "
                    "give an intimate life that is a refuge; Saturn or Ketu, "
                    "one that is sparse or renounced; Mars, heat; Rahu, "
                    "the foreign partner. The 12th lord in the 7th is a "
                    "marriage abroad or a partner through whom expenditure "
                    "flows; the 7th lord in the 12th, separation by "
                    "distance.", "convention"),
            Section("Strength and weakness",
                    "Strong (for the native): the 12th lord in a "
                    "duṣṭhāna, benefics in the 12th with the lagna strong, "
                    "Venus or Jupiter there, Ketu there with a strong "
                    "Jupiter. Gives expenditure on good causes, a fruitful "
                    "life abroad, deep sleep, a generous hand, and the "
                    "tradition's last gift.\n\n"
                    "Weak: the 12th lord strong on the lagna or 2nd, "
                    "malefics in the 12th with the lagna weak, the Moon "
                    "afflicted there. Gives losses that compound, "
                    "insomnia, isolation that is not chosen, hidden "
                    "enemies, and a life spent elsewhere than it wished.",
                    "convention"),
        ],
        lord_in=[
            (1, "A person who spends themselves; weak body or wanderer; expenditure on the self; some texts: a miser or a sage."),
            (2, "Expenditure on family and food; loss of wealth; a sweet speaker abroad; charitable with the family's money."),
            (3, "Expenditure through siblings or effort; a sibling lost or abroad; courage spent; some texts: hateful to all."),
            (4, "Loss of home, mother or property; a home abroad; the mother distant; comfort in solitude."),
            (5, "Expenditure on children and learning; a child abroad or lost; a mind turned to liberation; pilgrimage."),
            (6, "Vipārīta rāja yoga: losses on enemies, debts and disease — they dissolve; victory by expenditure; a hostile family by texts."),
            (7, "Expenditure through the partner; marriage abroad; a partner from afar; separation by distance if afflicted."),
            (8, "Vipārīta rāja yoga: loss of loss; long life; a hidden fortune; a quiet or sudden end abroad."),
            (9, "Expenditure on faith, journeys and the father; a pilgrim; the father distant or abroad; a heterodox seeker."),
            (10, "Expenditure through the career; work abroad or in institutions; authority spent; a fall by extravagance if afflicted."),
            (11, "Gains spent as they come; friends who cost; income abroad; charitable to elders."),
            (12, "The lord in its own house: a life abroad, in retreat, or in giving; expenditure that frees; liberation; a sound sleeper."),
        ],
        sources=[_BPHS11, _BPHS24, _PHAL1, _UK5],
    ),
]


# ---------------------------------------------------------------------------
# Lookups and the gate
# ---------------------------------------------------------------------------

GRAHA_BY_KEY = {g.key: g for g in GRAHAS}
BHAVA_BY_NUMBER = {b.number: b for b in BHAVAS}

BANNED_OPENERS = ("It is important to note", "In Vedic astrology,", "Astrology tells us",
                  "As we know", "Interestingly,", "Let's", "Let us")


def check() -> list[str]:
    """Editorial gate: nine grahas, twelve bhavas, every card complete,
    no throat-clearing, taglines ≤ 20 words, leads ≤ 130 words, every
    section graded or explicitly ungraded, every bhava with all twelve
    lord-in rows."""
    problems: list[str] = []
    if len(GRAHAS) != 9:
        problems.append(f"{len(GRAHAS)} grahas, expected 9")
    if [b.number for b in BHAVAS] != list(range(1, 13)):
        problems.append("bhavas are not 1..12 in order")
    for card in [*GRAHAS, *BHAVAS]:
        name = getattr(card, "name")
        if len(card.tagline.split()) > 20:
            problems.append(f"{name}: tagline over 20 words")
        if len(card.lead.split()) > 130:
            problems.append(f"{name}: lead over 130 words ({len(card.lead.split())})")
        if not card.sources:
            problems.append(f"{name}: no sources")
        for s in card.sections:
            if s.grade not in ("verse", "convention", "lore", ""):
                problems.append(f"{name}/{s.title}: bad grade {s.grade!r}")
            for opener in BANNED_OPENERS:
                if opener in s.body or opener in card.lead:
                    problems.append(f"{name}/{s.title}: banned opener {opener!r}")
    for b in BHAVAS:
        if [n for n, _ in b.lord_in] != list(range(1, 13)):
            problems.append(f"{b.name}: lord_in is not 1..12")
        if len(b.governs) < 5:
            problems.append(f"{b.name}: fewer than five 'governs' lines")
    return problems


if __name__ == "__main__":
    for p in check() or ["reference: clean"]:
        print(p)
