"""Guṇa Milan — aṣṭakūṭa compatibility, 8 kūṭas over 36 points.

Domain contract from the build framework (THREE · DOMAIN MODEL):
    KutaScore = { kuta, score, max, note? }
    GunaMilan = { a, b, rows, total, max: 36,
                  mangalDosa: { a, b, cancelled }, verdict }

Pure functions over chart output; the moment is always an argument. Both
partners' Moon longitudes drive everything except Maṅgala doṣa, which reads
Mars's house from each Lagna.

ON SOURCE VARIANCE — the aṣṭakūṭa tables are not uniform across texts. Where
a table is universally agreed (nāḍī, gaṇa, bhakūṭa, varṇa, tārā, graha maitrī)
it is implemented outright. Where gradations genuinely differ between
authorities (the finer yoni friend/enemy tiers, some vaśya cells), this module
implements the well-attested extremes and defaults the remainder to neutral,
says so in the rule text, and carries a lower confidence tag. It never invents
a cell to look complete.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from dashas import NAKSHATRAS, nakshatra_of
from engine import SIGNS, Chart
from yogas import natural_relation, sign_lord

MAX_TOTAL = 36.0

# --- kūṭa reference tables ------------------------------------------------------

# Varṇa by Moon rāśi element: water = Brāhmaṇa … air = Śūdra.
VARNA_BY_SIGN = [
    "Kṣatriya", "Vaiśya", "Śūdra", "Brāhmaṇa",      # Ar Ta Ge Cn
    "Kṣatriya", "Vaiśya", "Śūdra", "Brāhmaṇa",      # Le Vi Li Sc
    "Kṣatriya", "Vaiśya", "Śūdra", "Brāhmaṇa",      # Sg Cp Aq Pi
]
VARNA_RANK = {"Brāhmaṇa": 4, "Kṣatriya": 3, "Vaiśya": 2, "Śūdra": 1}

# Vaśya class by Moon rāśi. Sagittarius and Capricorn are split classically;
# the half is decided by the Moon's degree.
VASYA_BY_SIGN = [
    "quadruped", "quadruped", "human", "aquatic",   # Ar Ta Ge Cn
    "wild", "human", "human", "insect",             # Le Vi Li Sc
    "split-sg", "split-cp", "human", "aquatic",     # Sg Cp Aq Pi
]
# Attested cells only; unlisted pairs fall to 1.0 (see module note).
VASYA_MATRIX = {
    ("quadruped", "quadruped"): 2.0, ("human", "human"): 2.0,
    ("aquatic", "aquatic"): 2.0, ("wild", "wild"): 2.0,
    ("insect", "insect"): 2.0,
    ("wild", "quadruped"): 0.0, ("quadruped", "wild"): 0.0,
    ("human", "wild"): 0.0, ("wild", "human"): 0.0,
    ("human", "aquatic"): 0.5, ("aquatic", "human"): 0.5,
}

# Tārā: counted remainders 3, 5 and 7 are the inauspicious tārās
# (Vipat, Pratyari, Vadha).
INAUSPICIOUS_TARA = {3, 5, 7}

# Yoni animal + sex per nakṣatra, in nakṣatra order.
YONI = [
    ("Horse", "m"), ("Elephant", "m"), ("Sheep", "f"), ("Serpent", "m"),
    ("Serpent", "f"), ("Dog", "f"), ("Cat", "f"), ("Sheep", "m"),
    ("Cat", "m"), ("Rat", "m"), ("Rat", "f"), ("Cow", "m"),
    ("Buffalo", "f"), ("Tiger", "f"), ("Buffalo", "m"), ("Tiger", "m"),
    ("Deer", "f"), ("Deer", "m"), ("Dog", "m"), ("Monkey", "m"),
    ("Mongoose", "m"), ("Monkey", "f"), ("Lion", "f"), ("Horse", "f"),
    ("Lion", "m"), ("Cow", "f"), ("Elephant", "f"),
]
# The seven classical pairs of sworn enemies — the only zero-scoring cells.
YONI_SWORN_ENEMIES = {
    frozenset(("Cow", "Tiger")), frozenset(("Elephant", "Lion")),
    frozenset(("Horse", "Buffalo")), frozenset(("Dog", "Deer")),
    frozenset(("Serpent", "Mongoose")), frozenset(("Cat", "Rat")),
    frozenset(("Monkey", "Sheep")),
}

# Gaṇa by nakṣatra index.
GANA = [
    "Deva", "Manuṣya", "Rākṣasa", "Manuṣya", "Deva", "Manuṣya",
    "Deva", "Deva", "Rākṣasa", "Rākṣasa", "Manuṣya", "Manuṣya",
    "Deva", "Rākṣasa", "Deva", "Rākṣasa", "Deva", "Rākṣasa",
    "Rākṣasa", "Manuṣya", "Manuṣya", "Deva", "Rākṣasa", "Rākṣasa",
    "Manuṣya", "Manuṣya", "Deva",
]
# rows = bride's gaṇa, columns = groom's gaṇa (Raman's table).
GANA_MATRIX = {
    ("Deva", "Deva"): 6.0, ("Deva", "Manuṣya"): 6.0, ("Deva", "Rākṣasa"): 0.0,
    ("Manuṣya", "Deva"): 5.0, ("Manuṣya", "Manuṣya"): 6.0,
    ("Manuṣya", "Rākṣasa"): 0.0,
    ("Rākṣasa", "Deva"): 1.0, ("Rākṣasa", "Manuṣya"): 0.0,
    ("Rākṣasa", "Rākṣasa"): 6.0,
}

# Nāḍī by nakṣatra index: Ādi (vāta), Madhya (pitta), Antya (kapha).
NADI = [
    "Ādi", "Madhya", "Antya", "Antya", "Madhya", "Ādi", "Ādi", "Madhya",
    "Antya", "Antya", "Madhya", "Ādi", "Ādi", "Madhya", "Antya", "Antya",
    "Madhya", "Ādi", "Ādi", "Madhya", "Antya", "Antya", "Madhya", "Ādi",
    "Ādi", "Madhya", "Antya",
]

# Bhakūṭa: these mutual rāśi distances annul the kūṭa.
BHAKUTA_VOID = {frozenset((2, 12)), frozenset((5, 9)), frozenset((6, 8))}


# --- result types ---------------------------------------------------------------

@dataclass(frozen=True)
class KutaScore:
    kuta: str
    score: float
    max: float
    rule: str                    # the classical rule, verbatim
    detail: str                  # the computed working
    confidence: str = "High"     # lowered where sources genuinely differ
    note: str | None = None      # flagged when the kūṭa scores zero


@dataclass(frozen=True)
class Partner:
    """The half of a match this module needs, computed from a chart."""

    name: str
    moon_longitude: float
    moon_sign_index: int
    lagna_sign_index: int
    mars_house: int

    @property
    def nakshatra_index(self) -> int:
        return nakshatra_of(self.moon_longitude).index

    @property
    def nakshatra_name(self) -> str:
        return NAKSHATRAS[self.nakshatra_index]

    @property
    def pada(self) -> int:
        return nakshatra_of(self.moon_longitude).pada

    @property
    def moon_sign(self) -> str:
        return SIGNS[self.moon_sign_index]


@dataclass(frozen=True)
class GunaMilan:
    a: Partner                   # bride's side of the classical tables
    b: Partner                   # groom's side
    rows: tuple[KutaScore, ...]
    total: float
    max: float = MAX_TOTAL
    mangal_a: bool = False
    mangal_b: bool = False
    mangal_cancelled: bool = True
    mangal_note: str = ""
    verdict: str = ""

    @property
    def percentage(self) -> float:
        return round(100 * self.total / self.max, 1)

    @property
    def voids(self) -> tuple[str, ...]:
        return tuple(r.kuta for r in self.rows if r.score == 0)


def partner_from_chart(name: str, chart: Chart) -> Partner:
    moon = chart.planets["Moon"]
    return Partner(
        name=name or "—",
        moon_longitude=moon.longitude,
        moon_sign_index=moon.sign_index,
        lagna_sign_index=chart.lagna.sign_index,
        mars_house=chart.planets["Mars"].house,
    )


def _distance(from_sign: int, to_sign: int) -> int:
    """Inclusive rāśi count, 1–12."""
    return (to_sign - from_sign) % 12 + 1


def _vasya_class(partner: Partner) -> str:
    cls = VASYA_BY_SIGN[partner.moon_sign_index]
    deg = partner.moon_longitude % 30
    if cls == "split-sg":       # Sagittarius: first half human, second quadruped
        return "human" if deg < 15 else "quadruped"
    if cls == "split-cp":       # Capricorn: first half quadruped, second aquatic
        return "quadruped" if deg < 15 else "aquatic"
    return cls


# --- the eight kūṭas -------------------------------------------------------------

def _varna(a: Partner, b: Partner) -> KutaScore:
    va, vb = VARNA_BY_SIGN[a.moon_sign_index], VARNA_BY_SIGN[b.moon_sign_index]
    score = 1.0 if VARNA_RANK[vb] >= VARNA_RANK[va] else 0.0
    return KutaScore(
        "Varṇa", score, 1.0,
        "Varṇa is granted when the groom's varṇa, taken from his Moon rāśi, "
        "is not lower than the bride's.",
        f"{a.name}: {va} (Moon in {a.moon_sign}); {b.name}: {vb} "
        f"(Moon in {b.moon_sign}).",
        note=None if score else "Varṇa withheld — a difference of temperament "
                                "in work and duty, the lightest of the eight.",
    )


def _vasya(a: Partner, b: Partner) -> KutaScore:
    ca, cb = _vasya_class(a), _vasya_class(b)
    score = VASYA_MATRIX.get((ca, cb), 1.0)
    return KutaScore(
        "Vaśya", score, 2.0,
        "Vaśya measures mutual sway between the Moon-rāśi classes "
        "(quadruped, human, aquatic, wild, insect).",
        f"{a.name}: {ca}; {b.name}: {cb}.",
        confidence="Moderate",
        note=None if score else "Vaśya withheld — neither naturally yields "
                                "to the other.",
    )


def _tara(a: Partner, b: Partner) -> KutaScore:
    fwd = (b.nakshatra_index - a.nakshatra_index) % 27 + 1
    rev = (a.nakshatra_index - b.nakshatra_index) % 27 + 1
    r1, r2 = fwd % 9, rev % 9
    good1, good2 = r1 not in INAUSPICIOUS_TARA, r2 not in INAUSPICIOUS_TARA
    score = 3.0 if (good1 and good2) else 1.5 if (good1 or good2) else 0.0
    return KutaScore(
        "Tārā", score, 3.0,
        "Count between the two nakṣatras each way and divide by nine; "
        "remainders 3, 5 and 7 (Vipat, Pratyari, Vadha) are the "
        "inauspicious tārās.",
        f"{a.name}→{b.name}: {fwd} ÷ 9 leaves {r1}"
        f" ({'auspicious' if good1 else 'inauspicious'}); "
        f"{b.name}→{a.name}: {rev} ÷ 9 leaves {r2}"
        f" ({'auspicious' if good2 else 'inauspicious'}).",
        note=None if score else "Tārā withheld — both counts fall on "
                                "inauspicious tārās.",
    )


def _yoni(a: Partner, b: Partner) -> KutaScore:
    an, asex = YONI[a.nakshatra_index]
    bn, bsex = YONI[b.nakshatra_index]
    if an == bn:
        score, why = 4.0, "the same yoni"
    elif frozenset((an, bn)) in YONI_SWORN_ENEMIES:
        score, why = 0.0, "one of the seven sworn-enemy pairs"
    else:
        score, why = 2.0, "neither identical nor sworn enemies — neutral"
    return KutaScore(
        "Yoni", score, 4.0,
        "Yoni pairs the animal of each nakṣatra: identical yonis score full, "
        "the seven sworn-enemy pairs score nothing. Finer friend/enemy "
        "gradations differ between authorities, so unattested pairs are read "
        "as neutral here rather than guessed.",
        f"{a.name}: {an} ({asex}); {b.name}: {bn} ({bsex}) — {why}.",
        confidence="Moderate",
        note=None if score else "Yoni withheld — a sworn-enemy pairing; "
                                "classically a caution about physical "
                                "temperament, not a verdict on the union.",
    )


def _graha_maitri(a: Partner, b: Partner) -> KutaScore:
    la, lb = sign_lord(a.moon_sign_index), sign_lord(b.moon_sign_index)
    if la == lb:
        score, rel = 5.0, "the same lord rules both Moons"
    else:
        r1, r2 = natural_relation(la, lb), natural_relation(lb, la)
        pair = {r1, r2}
        if pair == {"friend"}:
            score = 5.0
        elif pair == {"friend", "neutral"}:
            score = 4.0
        elif pair == {"neutral"}:
            score = 3.0
        elif pair == {"friend", "enemy"}:
            score = 1.0
        elif pair == {"neutral", "enemy"}:
            score = 0.5
        else:
            score = 0.0
        rel = f"{la} regards {lb} as {r1}; {lb} regards {la} as {r2}"
    return KutaScore(
        "Graha Maitrī", score, 5.0,
        "The natural friendship between the lords of the two Moon rāśis "
        "(naisargika maitrī) sets this kūṭa.",
        f"{a.name}'s Moon lord {la}, {b.name}'s Moon lord {lb} — {rel}.",
        note=None if score else "Graha Maitrī withheld — the Moon lords are "
                                "mutual natural enemies.",
    )


def _gana(a: Partner, b: Partner) -> KutaScore:
    ga, gb = GANA[a.nakshatra_index], GANA[b.nakshatra_index]
    score = GANA_MATRIX[(ga, gb)]
    return KutaScore(
        "Gaṇa", score, 6.0,
        "Gaṇa sorts the nakṣatras into Deva, Manuṣya and Rākṣasa "
        "temperaments and scores their meeting.",
        f"{a.name}: {ga} ({a.nakshatra_name}); {b.name}: {gb} "
        f"({b.nakshatra_name}).",
        note=None if score else "Gaṇa withheld — a Deva/Manuṣya–Rākṣasa "
                                "meeting; read as differing instincts about "
                                "conduct, and commonly set aside when the "
                                "Moon lords agree.",
    )


def _bhakuta(a: Partner, b: Partner) -> KutaScore:
    fwd = _distance(a.moon_sign_index, b.moon_sign_index)
    rev = _distance(b.moon_sign_index, a.moon_sign_index)
    void = frozenset((fwd, rev)) in BHAKUTA_VOID
    score = 0.0 if void else 7.0
    return KutaScore(
        "Bhakūṭa", score, 7.0,
        "Bhakūṭa reads the mutual rāśi distance between the Moons; the "
        "2/12, 5/9 and 6/8 axes annul it.",
        f"{a.moon_sign} to {b.moon_sign} is {fwd}, and back is {rev}"
        + (" — an annulling axis." if void else " — a permitted axis."),
        note=None if score else "Bhakūṭa withheld — one of the three "
                                "annulling axes; classically eased when "
                                "Graha Maitrī is strong.",
    )


def _nadi(a: Partner, b: Partner) -> KutaScore:
    na, nb = NADI[a.nakshatra_index], NADI[b.nakshatra_index]
    score = 0.0 if na == nb else 8.0
    return KutaScore(
        "Nāḍī", score, 8.0,
        "Nāḍī sorts nakṣatras into Ādi, Madhya and Antya; a shared nāḍī "
        "scores nothing, differing nāḍīs score full.",
        f"{a.name}: {na} ({a.nakshatra_name}); {b.name}: {nb} "
        f"({b.nakshatra_name}).",
        note=None if score else "Nāḍī withheld — the same nāḍī, the "
                                "heaviest of the eight. Classical "
                                "exemptions exist: the same nakṣatra with "
                                "differing pādas, or a shared rāśi lord.",
    )


KUTAS = (_varna, _vasya, _tara, _yoni, _graha_maitri, _gana, _bhakuta, _nadi)


# --- Maṅgala doṣa & verdict -------------------------------------------------------

def _mangal(chart_a: Chart, chart_b: Chart) -> tuple[bool, bool, bool, str]:
    """Maṅgala doṣa on each side, and whether it stands cancelled."""
    from doshas import detect_mangal
    da, db = detect_mangal(chart_a), detect_mangal(chart_b)
    a_active, b_active = da.active, db.active
    if not a_active and not b_active:
        note = "Maṅgala doṣa: absent or already cancelled in both charts."
        return da.formed, db.formed, True, note
    if a_active and b_active:
        return (da.formed, db.formed, True,
                "Maṅgala doṣa stands in both charts — classically the "
                "canonical cancellation: matched, the two annul each other.")
    side = "the first chart" if a_active else "the second"
    return (da.formed, db.formed, False,
            f"Maṅgala doṣa is active in {side} only. Traditional practice "
            "matches it with another Maṅgala chart or applies the standard "
            "remedial counsel; it is a factor to weigh, not a bar.")


def _verdict(total: float, voids: tuple[str, ...], cancelled: bool) -> str:
    if total >= 32:
        base = "An exceptional agreement across the eight kūṭas."
    elif total >= 25:
        base = "A strong agreement across the eight kūṭas."
    elif total >= 18:
        base = "A workable agreement — the classical threshold is met."
    else:
        base = ("Below the classical threshold of 18; the aṣṭakūṭa alone "
                "does not support the match.")
    if voids:
        base += (" Withheld: " + ", ".join(voids)
                 + " — each is shown with its own classical easing above.")
    if not cancelled:
        base += " Maṅgala doṣa is uncancelled on one side."
    return base


def guna_milan(name_a: str, chart_a: Chart, name_b: str,
               chart_b: Chart) -> GunaMilan:
    """The full aṣṭakūṭa reckoning between two charts.

    `a` takes the bride's side of the classical tables and `b` the groom's —
    the tables are asymmetric (varṇa and gaṇa in particular), so the order
    is part of the computation, not a display choice.
    """
    a = partner_from_chart(name_a, chart_a)
    b = partner_from_chart(name_b, chart_b)
    rows = tuple(kuta(a, b) for kuta in KUTAS)
    total = sum(r.score for r in rows)
    m_a, m_b, cancelled, m_note = _mangal(chart_a, chart_b)
    voids = tuple(r.kuta for r in rows if r.score == 0)
    return GunaMilan(
        a=a, b=b, rows=rows, total=total,
        mangal_a=m_a, mangal_b=m_b, mangal_cancelled=cancelled,
        mangal_note=m_note,
        verdict=_verdict(total, voids, cancelled),
    )


def fraction(value: float) -> str:
    """28.5 → '28½' — the framework's numeral rule for scores."""
    whole = int(value)
    if abs(value - whole) < 1e-9:
        return str(whole)
    if abs(value - whole - 0.5) < 1e-9:
        return f"{whole}½" if whole else "½"
    return f"{value:g}"
