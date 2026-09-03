"""Automated gate tests. One class per phase; every phase's gates stay green forever.

Run with: pytest test_gates.py -v
"""
import json
import re
from datetime import date, datetime, timedelta, timezone

import pytest
from pathlib import Path

import fixtures

from dashas import DASHA_SEQUENCE, nakshatra_of, nakshatra_table, vimshottari
from engine import BirthData, compute_chart
from transits import (
    DRISHTI_OFFSETS,
    angular_distance,
    aspected_signs,
    aspects_on_house,
    houses_aspected_by,
    natal_aspect_table,
    transit_contacts,
    transit_snapshot,
)
from vargas import dasamsa, dasamsa_sign, navamsa, navamsa_sign
from yogas import (
    detect_all,
    detect_budhaditya,
    detect_dhana,
    detect_gaja_kesari,
    detect_kemadruma,
    detect_neecha_bhanga,
    detect_pancha_mahapurusha,
    detect_viparita_raja,
    dignity,
    house_lords,
    mutual_natural_enemies,
    natural_relation,
)

# The gate birth record. Parameterised in fixtures.py — set SIDERA_FIXTURES
# to substitute your own; the anchored assertions skip when you do.
GATE_BIRTH = fixtures.birth("reference")

HERE = Path(__file__).resolve().parent

TOLERANCE_DEG = 1.0


@pytest.fixture(scope="module")
def chart():
    return compute_chart(GATE_BIRTH)


class TestPhase1CoreEngine:
    # (sign, approx degree-in-sign, retrograde) for the reference chart.
    EXPECTED = {
        "Sun": ("Cancer", 29.2, False),
        "Moon": ("Taurus", 15.3, False),
        "Mars": ("Cancer", 3.1, False),
        "Mercury": ("Cancer", 25.5, True),
        "Jupiter": ("Pisces", 2.9, True),
        "Venus": ("Cancer", 9.4, False),
        "Saturn": ("Aries", 9.8, True),
        "Rahu": ("Leo", 7.9, None),  # node retro flag not gated
        "Ketu": ("Aquarius", 7.9, None),
    }

    def test_lagna_sign_and_degree(self, chart):
        assert chart.lagna.sign == "Leo"
        assert abs(chart.lagna.degree_in_sign - 11.09) <= TOLERANCE_DEG

    @pytest.mark.parametrize("planet", list(EXPECTED))
    def test_planet_position(self, chart, planet):
        sign, degree, retro = self.EXPECTED[planet]
        pos = chart.planets[planet]
        assert pos.sign == sign, f"{planet}: expected {sign}, got {pos.sign}"
        assert abs(pos.degree_in_sign - degree) <= TOLERANCE_DEG, (
            f"{planet}: expected ~{degree}° {sign}, got {pos.degree_in_sign:.2f}°"
        )
        if retro is not None:
            assert pos.retrograde == retro, f"{planet}: retrograde flag mismatch"

    def test_ketu_opposite_rahu(self, chart):
        diff = (chart.planets["Ketu"].longitude - chart.planets["Rahu"].longitude) % 360
        assert abs(diff - 180.0) < 1e-9

    def test_whole_sign_house_mapping(self, chart):
        # Lagna Leo → house 1 = Leo, so:
        assert chart.house_signs[1] == "Leo"
        assert chart.house_signs[12] == "Cancer"
        assert chart.planets["Rahu"].house == 1      # Leo
        assert chart.planets["Ketu"].house == 7      # Aquarius
        assert chart.planets["Jupiter"].house == 8   # Pisces
        assert chart.planets["Saturn"].house == 9    # Aries
        assert chart.planets["Moon"].house == 10     # Taurus
        # The Cancer stellium all falls in the 12th:
        for p in ("Sun", "Mars", "Mercury", "Venus"):
            assert chart.planets[p].house == 12, p

    def test_all_planets_present(self, chart):
        assert set(chart.planets) == {
            "Sun", "Moon", "Mars", "Mercury", "Jupiter",
            "Venus", "Saturn", "Rahu", "Ketu",
        }

    def test_iana_timezone_matches_fixed_offset(self, chart):
        kolkata = BirthData(
            year=GATE_BIRTH.year, month=GATE_BIRTH.month, day=GATE_BIRTH.day,
            hour=GATE_BIRTH.hour, minute=GATE_BIRTH.minute,
            latitude=GATE_BIRTH.latitude, longitude=GATE_BIRTH.longitude,
            tz="Asia/Kolkata", place=GATE_BIRTH.place,
        )
        other = compute_chart(kolkata)
        assert abs(other.lagna.longitude - chart.lagna.longitude) < 1e-6
        assert abs(
            other.planets["Moon"].longitude - chart.planets["Moon"].longitude
        ) < 1e-6

    def test_ayanamsa_is_lahiri_range(self, chart):
        # Lahiri ayanamsa in 1998 is ~23.8°; a wrong sid-mode or tropical slip
        # would land far outside this band.
        assert 23.5 <= chart.ayanamsa <= 24.2


class TestAstronomicalAnchors:
    """External anchors that involve no person at all.

    The committed reference chart is fictional, so its expected positions
    are computed by this build and can only ever be characterization. The
    anchoring those gates used to carry lives here instead: published,
    person-free astronomical facts that anyone can check against any
    ephemeris, textbook or almanac. If sidereal mode, ayanamsa or the
    ephemeris source ever drifts, these go red first and unambiguously.
    """

    def test_spica_sits_at_180_degrees_sidereal(self):
        # The Chitrapaksha (Lahiri) ayanamsa is DEFINED by placing Citrā —
        # Spica, α Virginis — at 180° sidereal. This is not a value this
        # build chose; it is what the ayanamsa means.
        import swisseph as swe
        from engine import _init_sidereal
        _init_sidereal()
        jd = swe.julday(2000, 1, 1, 12.0)  # J2000.0
        res = swe.fixstar_ut("Spica", jd,
                             swe.FLG_SWIEPH | swe.FLG_SIDEREAL)
        longitude = res[0][0]
        assert abs(longitude - 180.0) < 0.05, longitude

    def test_lahiri_ayanamsa_at_epoch_2000(self):
        # The standard published Lahiri value for 2000 Jan 1 is 23°51.4′.
        # (Indian Astronomical Ephemeris / Rashtriya Panchang.)
        import swisseph as swe
        from engine import _init_sidereal
        _init_sidereal()
        ayan = swe.get_ayanamsa_ut(swe.julday(2000, 1, 1, 12.0))
        assert abs(ayan - 23.857) < 0.005          # 23°51.4′
        degrees, minutes = int(ayan), (ayan % 1) * 60
        assert (degrees, round(minutes, 1)) == (23, 51.4)

    def test_total_solar_eclipse_2024_04_08(self):
        # A catalogued event: greatest eclipse 2024-04-08 18:17 UTC. A total
        # solar eclipse is a new moon AT a node, so it pins THREE things at
        # once — Sun–Moon conjunction, nodal alignment, and (because the
        # Sun's sidereal sign is asserted) the ayanamsa.
        from engine import julian_day_ut, sidereal_positions
        pos = sidereal_positions(
            julian_day_ut(datetime(2024, 4, 8, 18, 17, tzinfo=timezone.utc)))
        sun, moon, rahu = pos["Sun"], pos["Moon"], pos["Rahu"]
        separation = angular_distance(sun.longitude, moon.longitude)
        assert separation * 60 < 5.0, f"{separation * 60:.2f}′"   # arcminutes
        assert angular_distance(sun.longitude, rahu.longitude) < 5.0
        # Sidereal, the April 2024 eclipse fell in Pisces — tropically it
        # was in Aries. This assertion alone would catch a lost sid-mode.
        assert sun.sign == "Pisces" and moon.sign == "Pisces"

    def test_ketu_is_exactly_opposite_rahu_always(self):
        # An invariant of the model, not of any chart.
        from engine import julian_day_ut, sidereal_positions
        for year in (1900, 1975, 2024, 2099):
            pos = sidereal_positions(
                julian_day_ut(datetime(year, 6, 1, tzinfo=timezone.utc)))
            diff = (pos["Ketu"].longitude - pos["Rahu"].longitude) % 360
            assert abs(diff - 180.0) < 1e-9, year


class TestIndependentEphemerisCrossCheck:
    """The reference chart's positions, checked against a SECOND ephemeris.

    Asserting that this build reproduces its own swisseph output proves
    nothing — that is circular, and after the personal chart was removed it
    was the only thing left holding up the Phase 1 table. So the expected
    values below were computed independently with ERFA (pyerfa, the Python
    binding of the IAU's SOFA-derived library) and are pasted here as
    literals. ERFA shares no code with swisseph: the Sun comes from epv00
    (VSOP87-derived Earth), the Moon from moon98 (ELP/Meeus), the planets
    from plan94 (Simon et al. 1994), the node from the IAU fundamental
    argument faom03, and the lagna from gst06a + obl06.

    Reproduce with:  pip install pyerfa  (dev-only; not an app dependency)

    Residuals are the expected apparent-vs-geometric terms — annual
    aberration is ~20″ for the Sun, light-time a little more for the
    planets — so the tolerance is one arcminute, which is far tighter
    than anything the app renders (whole degrees and minutes) and far
    tighter than any nakshatra pada boundary.
    """

    # Sidereal longitudes, Lahiri, at 1998-08-16 01:27:00 UTC.
    ERFA_SIDEREAL = {
        "Sun": 119.1695, "Moon": 45.2901, "Mars": 93.1071,
        "Mercury": 115.5324, "Jupiter": 332.8814, "Venus": 99.4395,
        "Saturn": 9.7960, "Rahu": 127.8657,
    }
    ERFA_LAGNA = 131.0836
    TOLERANCE = 1.0 / 60.0            # one arcminute

    def test_birth_instant_is_the_one_erfa_was_given(self, chart):
        # The constants above are only meaningful for this exact instant.
        assert chart.birth.utc_datetime == datetime(
            1998, 8, 16, 1, 27, tzinfo=timezone.utc)
        assert abs(chart.birth.julian_day_ut - 2451041.560417) < 1e-5

    @pytest.mark.parametrize("planet", list(ERFA_SIDEREAL))
    def test_planet_agrees_with_erfa(self, chart, planet):
        expected = self.ERFA_SIDEREAL[planet]
        got = chart.planets[planet].longitude
        delta = abs((got - expected + 180) % 360 - 180)
        assert delta <= self.TOLERANCE, (
            f"{planet}: swisseph {got:.4f}° vs ERFA {expected:.4f}° "
            f"— {delta * 3600:.1f}″ apart")

    def test_lagna_agrees_with_erfa(self, chart):
        delta = abs((chart.lagna.longitude - self.ERFA_LAGNA + 180) % 360 - 180)
        assert delta <= self.TOLERANCE, f"{delta * 3600:.1f}″ apart"

    def test_cross_check_pins_the_nakshatra_and_pada(self, chart):
        # The whole Vimshottari timeline hangs off the Moon's position, so
        # the cross-check has to be tight enough to fix the pada. Rohini
        # pada 2 spans 43°20′–46°40′; ERFA puts the Moon 1.6° inside it,
        # which is 60× the disagreement between the two ephemerides.
        moon = self.ERFA_SIDEREAL["Moon"]
        assert 43 + 1 / 3 <= moon <= 46 + 2 / 3
        assert nakshatra_of(moon).name == "Rohini"
        assert nakshatra_of(moon).pada == 2
        assert nakshatra_of(chart.planets["Moon"].longitude).pada == 2


@pytest.fixture(scope="module")
def timeline(chart):
    return vimshottari(chart)


class TestPhase2NakshatrasVimshottari:
    def test_moon_nakshatra_rohini(self, timeline):
        # 15.29° Taurus → Rohini (Taurus 10°00′–23°20′) pada 2, lord Moon.
        assert timeline.moon_nakshatra.name == "Rohini"
        assert timeline.moon_nakshatra.pada == 2
        assert timeline.moon_nakshatra.lord == "Moon"

    def test_nakshatra_boundaries(self):
        assert nakshatra_of(0.0).name == "Ashwini"
        assert nakshatra_of(0.0).pada == 1
        assert nakshatra_of(13.34).name == "Bharani"
        assert nakshatra_of(359.9).name == "Revati"
        assert nakshatra_of(359.9).pada == 4
        # Lord cycle repeats thrice: Magha (index 9) restarts at Ketu.
        assert nakshatra_of(9 * (360 / 27) + 1).lord == "Ketu"

    def test_nakshatra_table_covers_lagna_and_planets(self, chart):
        table = nakshatra_table(chart)
        assert table["Lagna"].name == "Magha"
        assert table["Sun"].name == "Ashlesha"
        assert table["Saturn"].name == "Ashwini"

    def test_dasha_sequence_totals_120_years(self):
        assert sum(y for _, y in DASHA_SEQUENCE) == 120

    def test_md_sequence_and_dates(self, timeline):
        # A Rohini Moon is Moon-ruled, so the sequence opens Moon → Mars →
        # Rahu → Jupiter. The Moon stood 39.7% through Rohini, leaving 60.3%
        # of its 10 years — a birth balance of 6.032y, so the Moon MD closes
        # 6.032 × 365.25 days after 16 Aug 1998.
        lords = [md.lord for md in timeline.mahadashas]
        assert lords[:4] == ["Moon", "Mars", "Rahu", "Jupiter"]
        moon, mars, rahu = timeline.mahadashas[:3]
        assert abs(timeline.balance_years - 6.032) < 0.005
        assert moon.end.date() == date(2004, 8, 27)
        assert mars.start.date() == date(2004, 8, 27)
        assert mars.end.date() == date(2011, 8, 28)
        assert abs(mars.years - 7) < 0.01
        assert rahu.start.date() == date(2011, 8, 28)
        assert rahu.end.date() == date(2029, 8, 27)
        assert abs(rahu.years - 18) < 0.01

    def test_rahu_venus_antardasha_spans_2023_to_2026(self, timeline):
        rahu = timeline.mahadashas[2]
        assert [ad.lord for ad in rahu.antardashas[:3]] == [
            "Rahu", "Jupiter", "Saturn",
        ]
        venus_ad = next(a for a in rahu.antardashas if a.lord == "Venus")
        # Rahu 18y × Venus 20y ÷ 120 = exactly 3 years.
        assert abs(venus_ad.years - 3.0) < 0.01
        assert venus_ad.start.date() == date(2023, 3, 16)
        assert venus_ad.end.date() == date(2026, 3, 16)

    def test_current_md_ad_lookup(self, timeline):
        md, ad = timeline.at(datetime(2026, 7, 11, tzinfo=timezone.utc))
        assert (md.lord, ad.lord) == ("Rahu", "Sun")
        # Well inside Mars MD, Mars's opening AD:
        md, ad = timeline.at(datetime(2004, 10, 1, tzinfo=timezone.utc))
        assert (md.lord, ad.lord) == ("Mars", "Mars")
        # Before the notional start of the first MD → None.
        assert timeline.at(datetime(1980, 1, 1, tzinfo=timezone.utc)) is None

    def test_antardashas_partition_each_md(self, timeline):
        for md in timeline.mahadashas:
            ads = md.antardashas
            assert len(ads) == 9
            assert ads[0].lord == md.lord  # first AD is the MD lord's own
            assert ads[0].start == md.start
            assert ads[-1].end == md.end
            for a, b in zip(ads, ads[1:]):
                assert a.end == b.start
            # AD length proportional: md_years × ad_years / 120.
            for ad in ads:
                expected = md.years * dict(DASHA_SEQUENCE)[ad.lord] / 120
                assert abs(ad.years - expected) < 0.01

    def test_timeline_spans_120_years(self, timeline):
        first, last = timeline.mahadashas[0], timeline.mahadashas[-1]
        total = (last.end - first.start).days / 365.25
        assert abs(total - 120) < 0.02


class TestPhase3DivisionalCharts:
    def test_d9_lagna_cancer(self, chart):
        # Lagna 11.09° Leo. Leo is fixed, so navamsas count from the 9th
        # from it (Aries); 11.09 ÷ 3°20′ → the 4th navamsa → Cancer.
        assert navamsa(chart).lagna_sign == "Cancer"

    def test_d9_gate_planets(self, chart):
        d9 = navamsa(chart)
        # Moon 15.29° Taurus → 5th navamsa from Capricorn → Taurus, so it
        # repeats its D1 sign: Vargottama.
        assert d9.planets["Moon"].sign == "Taurus"
        assert d9.planets["Moon"].vargottama is True
        # Mars 3.10° Cancer → 1st navamsa; Cancer is movable, counting from
        # itself → Cancer. Also Vargottama.
        assert d9.planets["Mars"].sign == "Cancer"
        assert d9.planets["Mars"].vargottama is True
        # Jupiter 2.89° Pisces → 1st navamsa from Cancer (Pisces is dual,
        # counting from the 5th) → Cancer, a different sign.
        assert d9.planets["Jupiter"].sign == "Cancer"
        assert d9.planets["Jupiter"].vargottama is False

    def test_d10_lagna_scorpio(self, chart):
        # Lagna 11.09° Leo. Leo is odd, so dasamsas count from itself;
        # 11.09 ÷ 3° → the 4th part → Scorpio.
        assert dasamsa(chart).lagna_sign == "Scorpio"

    def test_d9_houses_from_divisional_lagna(self, chart):
        d9 = navamsa(chart)
        # Moon D9 Taurus from Cancer lagna → 11th house (Whole Sign).
        assert d9.planets["Moon"].house == 11
        # Mars D9 Cancer from Cancer lagna → 1st house.
        assert d9.planets["Mars"].house == 1
        assert d9.house_signs[1] == "Cancer"
        placed = [p for names in d9.houses.values() for p in names]
        assert sorted(placed) == sorted(chart.planets)

    def test_navamsa_counting_rules(self):
        # Movable sign counts from itself: first navamsa of Aries is Aries,
        # ninth is Sagittarius.
        assert navamsa_sign(0.0) == 0
        assert navamsa_sign(29.99) == 8
        # Fixed sign counts from the 9th from it: Taurus 0° → Capricorn.
        assert navamsa_sign(30.0) == 9
        # Dual sign counts from the 5th from it: Gemini 0° → Libra.
        assert navamsa_sign(60.0) == 6
        # Sign boundary is exact: last navamsa of Pisces → Pisces (vargottama
        # corner), first of Aries → Aries.
        assert navamsa_sign(359.99) == 11

    def test_dasamsa_counting_rules(self):
        # Odd sign from itself: Aries 0° → Aries; Aries 29.9° → 10th → Capricorn.
        assert dasamsa_sign(0.0) == 0
        assert dasamsa_sign(29.9) == 9
        # Even sign from the 9th from it: Taurus 0° → Capricorn.
        assert dasamsa_sign(30.0) == 9
        # Part boundary at exactly 3°: Aries 3° → second dasamsa → Taurus.
        assert dasamsa_sign(3.0) == 1


# Fixed instant so ephemeris-derived assertions are deterministic.
TRANSIT_WHEN = datetime(2026, 7, 11, 12, 0, tzinfo=timezone.utc)


@pytest.fixture(scope="module")
def snapshot(chart):
    return transit_snapshot(chart, TRANSIT_WHEN)


class TestPhase4TransitsAspects:

    def test_drishti_offsets_per_spec(self):
        # All 7th; Mars 4/8; Jupiter 5/9; Saturn 3/10; nodes 5/9.
        assert all(7 in offs for offs in DRISHTI_OFFSETS.values())
        assert DRISHTI_OFFSETS["Mars"] == (4, 7, 8)
        assert DRISHTI_OFFSETS["Jupiter"] == (5, 7, 9)
        assert DRISHTI_OFFSETS["Saturn"] == (3, 7, 10)
        assert DRISHTI_OFFSETS["Rahu"] == DRISHTI_OFFSETS["Ketu"] == (5, 7, 9)
        for p in ("Sun", "Moon", "Mercury", "Venus"):
            assert DRISHTI_OFFSETS[p] == (7,)

    def test_aspected_signs_counting(self):
        # Saturn in Pisces (11): 3rd → Taurus (1), 7th → Virgo (5),
        # 10th → Sagittarius (8).
        assert aspected_signs("Saturn", 11) == (1, 5, 8)
        # Mars in Cancer (3): 4th → Libra (6), 7th → Capricorn (9),
        # 8th → Aquarius (10).
        assert aspected_signs("Mars", 3) == (6, 9, 10)

    def test_natal_aspect_table(self, chart):
        table = {(a.aspecting, a.aspected): a.offset
                 for a in natal_aspect_table(chart)}
        # Hand-derived from the natal signs:
        assert table[("Mars", "Ketu")] == 8        # Cancer → Aquarius
        assert table[("Rahu", "Saturn")] == 9      # Leo → Aries
        assert table[("Rahu", "Ketu")] == 7        # Leo → Aquarius
        assert table[("Ketu", "Rahu")] == 7        # and back again
        # Jupiter in Pisces casts its 5th onto the whole Cancer stellium —
        # four separate rows, not one summarised entry.
        for occupant in ("Sun", "Mars", "Mercury", "Venus"):
            assert table[("Jupiter", occupant)] == 5, occupant
        # No planet aspects itself; conjunction (offset 1) is not drishti.
        assert all(a != b for a, b in table)

    def test_aspect_completeness_every_graha(self, chart):
        # Every graha casts at least the 7th aspect, so every graha must
        # emit ≥1 aspect entry AT SIGN/HOUSE LEVEL — always, in any chart.
        for planet in DRISHTI_OFFSETS:
            houses = houses_aspected_by(chart, planet)
            assert len(houses) >= 1, f"{planet} emits no aspect"
            assert len(houses) == len(DRISHTI_OFFSETS[planet])
        # Planet-to-planet entries additionally require an OCCUPANT in the
        # aspected sign. Here the four Cancer planets all cast their 7th
        # into empty Capricorn, so exactly those four are absent from the
        # natal table — asserted so the omission is a verified fact, not a
        # bug. (Mars is present only via its 8th, not its 7th.)
        emitters = {a.aspecting for a in natal_aspect_table(chart)}
        assert emitters == {"Mars", "Jupiter", "Rahu", "Ketu"}
        assert houses_aspected_by(chart, "Sun") == (6,)      # Capricorn
        assert houses_aspected_by(chart, "Venus") == (6,)
        assert houses_aspected_by(chart, "Mercury") == (6,)
        assert houses_aspected_by(chart, "Moon") == (4,)     # Scorpio, empty
        assert houses_aspected_by(chart, "Mars") == (3, 6, 7)
        assert houses_aspected_by(chart, "Saturn") == (3, 6, 11)
        assert houses_aspected_by(chart, "Jupiter") == (2, 4, 12)

    def test_aspects_on_house(self, chart):
        # House 12 = Cancer, holding four planets: Jupiter's 5th from Pisces
        # lands there. Occupation is not drishti, so the four occupants do
        # not appear.
        assert aspects_on_house(chart, 12) == ["Jupiter"]
        # House 6 = Capricorn, empty, yet aspected by five grahas — the
        # 7th from the Cancer stellium plus Saturn's 10th from Aries.
        assert aspects_on_house(chart, 6) == [
            "Sun", "Mars", "Mercury", "Venus", "Saturn"]
        # House 8 and 10 receive no drishti at all.
        assert aspects_on_house(chart, 8) == []
        assert aspects_on_house(chart, 10) == []

    def test_transits_mapped_to_natal_houses(self, snapshot):
        # 2026-07-11: Saturn transits Pisces = natal 8th; Jupiter Cancer =
        # natal 12th; Rahu Aquarius = natal 7th; Sun Gemini = natal 11th.
        assert snapshot.planets["Saturn"].sign == "Pisces"
        assert snapshot.planets["Saturn"].natal_house == 8
        assert snapshot.planets["Jupiter"].sign == "Cancer"
        assert snapshot.planets["Jupiter"].natal_house == 12
        assert snapshot.planets["Rahu"].sign == "Aquarius"
        assert snapshot.planets["Rahu"].natal_house == 7
        assert snapshot.planets["Sun"].natal_house == 11
        assert snapshot.planets["Mercury"].retrograde is True
        assert snapshot.by_natal_house[10] == ["Moon", "Mars"]  # Taurus

    def test_transit_contacts_conjunctions(self, chart, snapshot):
        conj = {(c.transit_planet, c.natal_planet): c.orb
                for c in transit_contacts(chart, snapshot)
                if c.kind == "conjunction"}
        # Lunar return that day (orb 1.31°); transit Mars on the natal Moon.
        assert ("Moon", "Moon") in conj and conj[("Moon", "Moon")] < 2.0
        assert ("Mars", "Moon") in conj and conj[("Mars", "Moon")] < 1.0
        # Transit nodes back on the natal nodal axis, reversed.
        assert conj[("Rahu", "Ketu")] < 0.1
        assert conj[("Ketu", "Rahu")] < 0.1
        # Transit Saturn 20.3° Pisces vs natal Jupiter 2.9° — no conjunction.
        assert ("Saturn", "Jupiter") not in conj

    def test_transit_contacts_sign_level_aspects(self, chart, snapshot):
        asp = {(c.transit_planet, c.natal_planet): c.offset
               for c in transit_contacts(chart, snapshot)
               if c.kind == "aspect"}
        # Transit Saturn in Pisces casts its 3rd onto natal Taurus (Moon).
        assert asp[("Saturn", "Moon")] == 3
        # Transit Jupiter in Cancer: 9th → Pisces → natal Jupiter.
        assert asp[("Jupiter", "Jupiter")] == 9
        # Transit Mars in Taurus: 4th → Leo → natal Rahu.
        assert asp[("Mars", "Rahu")] == 4
        # Transit Ketu in Leo: 9th → Aries → natal Saturn.
        assert asp[("Ketu", "Saturn")] == 9

    def test_angular_distance_wraparound(self):
        assert angular_distance(359.0, 1.0) == 2.0
        assert angular_distance(0.0, 180.0) == 180.0
        assert angular_distance(10.0, 10.0) == 0.0


def synthetic_chart(lagna_sign: int, planet_signs: dict):
    """Build a Chart from bare placements so yoga/dignity rules can be
    exercised on constructed configurations. Values are a sign index
    (mid-sign longitude assumed) or a (sign_index, degree) tuple."""
    from engine import Chart, PlanetPosition, Position

    planets = {}
    for name, spec in planet_signs.items():
        sign, deg = spec if isinstance(spec, tuple) else (spec, 15.0)
        planets[name] = PlanetPosition(
            longitude=sign * 30 + deg, name=name,
            house=(sign - lagna_sign) % 12 + 1,
        )
    return Chart(birth=GATE_BIRTH, lagna=Position(longitude=lagna_sign * 30 + 15.0),
                 planets=planets, ayanamsa=0.0)


class TestPhase5Yogas:
    def test_full_lordship_mapping(self, chart):
        # Leo lagna: the complete house → lord map.
        assert house_lords(chart) == {
            1: "Sun", 2: "Mercury", 3: "Venus", 4: "Mars",
            5: "Jupiter", 6: "Saturn", 7: "Saturn", 8: "Jupiter",
            9: "Mars", 10: "Venus", 11: "Mercury", 12: "Moon",
        }

    def test_dignity_states_bphs_segmentation(self, chart):
        # Classical BPHS segmentation, read off the reference chart:
        assert dignity(chart, "Moon") == "moolatrikona"  # 15.29° Taurus, >3°
        assert dignity(chart, "Jupiter") == "own sign"   # Pisces
        assert dignity(chart, "Mars") == "debilitated"   # Cancer
        assert dignity(chart, "Saturn") == "debilitated"  # Aries
        assert dignity(chart, "Sun") == "neutral"        # Cancer
        assert dignity(chart, "Mercury") == "neutral"    # Cancer
        # Virgo band edges for Mercury: 15° = deep exaltation (inclusive),
        # 16–20° moolatrikona, 20–30° own sign.
        assert dignity(synthetic_chart(8, {"Mercury": (5, 15.0)}),
                       "Mercury") == "exalted"
        assert dignity(synthetic_chart(8, {"Mercury": (5, 17.0)}),
                       "Mercury") == "moolatrikona"
        assert dignity(synthetic_chart(8, {"Mercury": (5, 25.0)}),
                       "Mercury") == "own sign"
        # Moon in Taurus: 0–3° exaltation, then moolatrikona.
        assert dignity(synthetic_chart(8, {"Moon": (1, 2.0)}),
                       "Moon") == "exalted"
        assert dignity(synthetic_chart(8, {"Moon": (1, 10.0)}),
                       "Moon") == "moolatrikona"
        # Single-status moolatrikona/own splits: Sun in Leo 0–20 MT.
        assert dignity(synthetic_chart(8, {"Sun": (4, 5.0)}),
                       "Sun") == "moolatrikona"
        assert dignity(synthetic_chart(8, {"Sun": (4, 25.0)}),
                       "Sun") == "own sign"
        # A sole-status exaltation is whole-sign: Sun 2° Aries.
        assert dignity(synthetic_chart(8, {"Sun": 0}), "Sun") == "exalted"

    def test_dignity_grades(self, chart):
        from yogas import dignity_grade
        # Mars 3.10° Cancer — short of the 28° deep-fall degree.
        assert dignity_grade(chart, "Mars") == \
            "debilitated (early degree, approaching deep fall at 28°)"
        # Moon 15.29° Taurus — moolatrikona names its span.
        assert dignity_grade(chart, "Moon") == "moolatrikona (3°–30° span)"
        # The exaltation zone graded from below, on a constructed chart —
        # no planet is exalted in the reference chart.
        assert dignity_grade(synthetic_chart(8, {"Mercury": (5, 1.0)}),
                             "Mercury") == \
            "exalted (early degree, rising toward deep exaltation at 15°)"
        # At the peak itself:
        assert dignity_grade(synthetic_chart(8, {"Mercury": (5, 15.0)}),
                             "Mercury") == \
            "exalted (at the deep exaltation degree, 15°)"
        # Past the peak, easing:
        assert dignity_grade(synthetic_chart(8, {"Sun": (0, 20.0)}),
                             "Sun") == \
            "exalted (past the deep exaltation degree at 10°, easing)"
        # Moolatrikona names its span; plain states grade to empty.
        assert dignity_grade(synthetic_chart(8, {"Sun": (4, 5.0)}),
                             "Sun") == "moolatrikona (0°–20° span)"
        # Plain states grade to empty: own sign and neutral carry no degree
        # story to tell.
        assert dignity_grade(chart, "Jupiter") == ""
        assert dignity_grade(chart, "Venus") == ""

    def test_natural_relations(self):
        assert mutual_natural_enemies("Sun", "Saturn") is True
        assert natural_relation("Sun", "Moon") == "friend"
        # Asymmetry: Moon treats no one as enemy, Mercury resents the Moon.
        assert natural_relation("Mercury", "Moon") == "enemy"
        assert natural_relation("Moon", "Mercury") == "friend"
        assert mutual_natural_enemies("Moon", "Mercury") is False

    def test_pancha_mahapurusha_absent(self, chart):
        # None of the five qualify: Jupiter IS in its own sign (Pisces) but
        # in house 8, not a Kendra; Mars and Saturn are debilitated; Mercury
        # and Venus sit in Cancer, neither own nor exalted. The yoga needs
        # BOTH dignity and a Kendra, so a near-miss must produce nothing.
        assert detect_pancha_mahapurusha(chart) == []
        assert dignity(chart, "Jupiter") == "own sign"
        assert chart.planets["Jupiter"].house == 8

    def test_pancha_mahapurusha_fires_on_a_kendra(self):
        # Same Jupiter dignity, moved to a Kendra → Hamsa appears. This
        # pins the Kendra half of the rule, which the reference chart alone
        # can only disprove.
        c = synthetic_chart(11, {                  # Pisces lagna & Jupiter
            "Sun": 4, "Moon": 2, "Mars": 3, "Mercury": 4, "Jupiter": 11,
            "Venus": 5, "Saturn": 0, "Rahu": 6, "Ketu": 0,
        })
        found = {y.name: y for y in detect_pancha_mahapurusha(c)}
        assert "Hamsa Yoga" in found
        assert found["Hamsa Yoga"].houses == (1,)

    def test_gaja_kesari_absent(self, chart):
        # Jupiter (Pisces) stands the 11th from the Moon (Taurus) and casts
        # no drishti onto it — neither Kendra nor aspect, so no Gaja Kesari.
        assert detect_gaja_kesari(chart) == []

    def test_budhaditya(self, chart):
        found = detect_budhaditya(chart)
        assert len(found) == 1
        assert found[0].houses == (12,)  # Sun + Mercury in Cancer

    def test_dhana_yogas(self, chart):
        found = {y.name: y for y in detect_dhana(chart)}
        # Leo lagna puts the lords of 1 (Sun), 2 & 11 (Mercury) and 9 (Mars)
        # all in Cancer — every pair among them forms a conjunction Dhana.
        assert set(found) == {
            "Dhana Yoga (lords of 1 & 2 conjoined)",
            "Dhana Yoga (lords of 1 & 9 conjoined)",
            "Dhana Yoga (lords of 1 & 11 conjoined)",
            "Dhana Yoga (lords of 2 & 9 conjoined)",
            "Dhana Yoga (lords of 9 & 11 conjoined)",
        }
        # None of these three pairs are mutual natural enemies, so no
        # friction tag is stored — the absence is asserted, not assumed.
        assert all(y.notes == () for y in found.values())
        assert not mutual_natural_enemies("Sun", "Mercury")
        assert not mutual_natural_enemies("Sun", "Mars")
        assert not mutual_natural_enemies("Mercury", "Mars")

    def test_dhana_friction_tag_on_enemy_lords(self):
        # The friction machinery needs two wealth lords that ARE mutual
        # enemies; the reference chart has none, so it is pinned on a
        # constructed one. Sagittarius lagna: 2nd lord Saturn in Pisces,
        # 9th lord Sun in Virgo — mutual 7th, and natural enemies.
        c = synthetic_chart(8, {
            "Sun": 5, "Moon": 2, "Mars": 3, "Mercury": 5, "Jupiter": 8,
            "Venus": 4, "Saturn": 11, "Rahu": 5, "Ketu": 11,
        })
        found = {y.name: y for y in detect_dhana(c)}
        mutual = found["Dhana Yoga (lords of 2 & 9 in mutual aspect)"]
        assert any("natural enemies" in n for n in mutual.notes)
        # A placement-based yoga (single planet) carries no enmity note.
        assert found["Dhana Yoga (lord of 11 in house 9)"].notes == ()

    def test_viparita_raja(self, chart):
        found = detect_viparita_raja(chart)
        # Jupiter, lord of 8, stands in house 8 → Sarala. The 6th lord
        # Saturn is in 9 and the 12th lord Moon in 10 → no Harsha/Vimala.
        assert [y.name for y in found] == ["Sarala (Viparita Raja) Yoga"]
        assert found[0].houses == (8, 8)

    def test_neecha_bhanga_mars_only(self, chart):
        found = detect_neecha_bhanga(chart)
        # TWO planets are debilitated — Mars in Cancer and Saturn in Aries —
        # but only Mars meets a cancellation condition, so only Mars emits.
        # An uncancelled debilitation must stay silent rather than produce
        # a hollow entry.
        assert dignity(chart, "Saturn") == "debilitated"
        assert [y.name for y in found] == ["Neecha Bhanga (Mars)"]
        y = found[0]
        assert y.planets == ("Mars", "Moon")
        # Moon (Cancer's lord) sits in Taurus — the 10th from Leo, a Kendra.
        assert "dispositor Moon is in a Kendra" in y.detail

    def test_kemadruma_absent_in_reference_chart(self, chart):
        # Saturn sits in Aries, the 12th sign from the Moon → the Moon is
        # flanked, so no Kemadruma.
        assert detect_kemadruma(chart) == []

    def test_kemadruma_formed_and_effective_synthetic(self):
        # Moon alone in Aries, lagna Aquarius (Moon in house 3, not Kendra),
        # no planet flanking, in Kendra from Moon, or Jupiter-aspecting it.
        c = synthetic_chart(10, {
            "Sun": 4, "Moon": 0, "Mars": 5, "Mercury": 5, "Jupiter": 2,
            "Venus": 7, "Saturn": 10, "Rahu": 4, "Ketu": 10,
        })
        found = detect_kemadruma(c)
        assert len(found) == 1
        assert found[0].cancelled is False
        assert found[0].cancellation == ()

    def test_kemadruma_formed_but_cancelled_synthetic(self):
        # As above but Saturn moves to Cancer: 4th from the Moon — still no
        # flanking planet (2nd/12th), but a Kendra-from-Moon exception.
        c = synthetic_chart(10, {
            "Sun": 4, "Moon": 0, "Mars": 5, "Mercury": 5, "Jupiter": 2,
            "Venus": 7, "Saturn": 3, "Rahu": 4, "Ketu": 10,
        })
        found = detect_kemadruma(c)
        assert len(found) == 1
        assert found[0].cancelled is True
        assert any("Kendra from the Moon" in r and "Saturn" in r
                   for r in found[0].cancellation)

    def test_detect_all_summary(self, chart):
        names = {y.name for y in detect_all(chart)}
        assert names == {
            "Budhaditya Yoga",
            "Dhana Yoga (lords of 1 & 2 conjoined)",
            "Dhana Yoga (lords of 1 & 9 conjoined)",
            "Dhana Yoga (lords of 1 & 11 conjoined)",
            "Dhana Yoga (lords of 2 & 9 conjoined)",
            "Dhana Yoga (lords of 9 & 11 conjoined)",
            "Sarala (Viparita Raja) Yoga", "Neecha Bhanga (Mars)",
        }
        # Every detection must carry its rule verbatim and working shown.
        for y in detect_all(chart):
            assert y.rule and y.detail


GATE_FORM = {
    "date": f"{GATE_BIRTH.year:04d}-{GATE_BIRTH.month:02d}-{GATE_BIRTH.day:02d}",
    "time": f"{GATE_BIRTH.hour:02d}:{GATE_BIRTH.minute:02d}",
    "lat": str(GATE_BIRTH.latitude), "lon": str(GATE_BIRTH.longitude),
    "tz": GATE_BIRTH.tz, "place": GATE_BIRTH.place,
}


@pytest.fixture(scope="module")
def client():
    from app import app
    app.config["TESTING"] = True
    return app.test_client()


@pytest.fixture(scope="module")
def page(client):
    resp = client.post("/", data=GATE_FORM)
    assert resp.status_code == 200
    return resp.get_data(as_text=True)


class TestPhase6FlaskUI:
    def test_birth_form_renders_blank_and_universal(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        html = resp.get_data(as_text=True)
        for field in ("name", "date", "time", "lat", "lon", "tz", "place"):
            assert f'name="{field}"' in html
        assert "Cast the chart" in html
        # Completely blank: no prefilled values in the birth form itself.
        # (The palette picker's <option value="…"> lives outside it.)
        form_html = html[html.index('<form method="post"'):html.index("</form>")]
        assert 'value=""' in form_html
        assert re.search(r'value="[^"]', form_html) is None
        # The reference chart lives ONLY in this test file — never in the UI.
        for leak in (GATE_BIRTH.place, str(GATE_BIRTH.year),
                     f"{GATE_BIRTH.hour}:{GATE_BIRTH.minute}",
                     str(GATE_BIRTH.latitude), str(GATE_BIRTH.longitude)):
            assert leak not in html, f"reference-chart leak: {leak}"

    def test_time_parsing_24h_and_12h(self):
        from app import parse_time
        assert parse_time("14:20") == (14, 20)
        assert parse_time("2:20 PM") == (14, 20)
        assert parse_time("12:05 am") == (0, 5)
        assert parse_time("12:05 pm") == (12, 5)
        assert parse_time("08.45") == (8, 45)
        # Separator-free, for a browser that degrades <input type="time"> to
        # a text box a phone keypad can only put digits into.
        assert parse_time("1420") == (14, 20)
        assert parse_time("0845") == (8, 45)
        assert parse_time("845") == (8, 45)
        assert parse_time("0005") == (0, 5)
        for bad in ("25:00", "14:20 PM", "0:00 AM", "10:75", "noonish", "",
                    "2500", "1075", "84500"):
            with pytest.raises(ValueError):
                parse_time(bad)

    def test_birth_time_field_is_a_native_time_input(self, client):
        """Mobile regression: the field was type=text inputmode=numeric.

        That combination hands a phone a digits-only keypad with no colon
        key, so a birth time could not be entered on mobile at all — found
        in a live smoke-test on Render. `type="time"` gives the native
        picker and submits 24-hour "HH:MM", which parse_time already reads.
        """
        html = client.get("/").get_data(as_text=True)
        form = html[html.index('<form method="post"'):html.index("</form>")]
        for field in ("time", "p_time"):
            tag = re.search(rf'<input id="{field}"[^>]*>', form, re.S)
            assert tag, f"{field} input missing"
            assert 'type="time"' in tag.group(0), (
                f"{field} must be a native time input: {tag.group(0)}")
            assert 'step="60"' in tag.group(0), (
                f"{field} needs minute granularity, not seconds")
            assert 'inputmode="numeric"' not in tag.group(0), (
                f"{field} must not force a digits-only keypad")

    def test_no_birth_field_traps_a_mobile_keyboard(self, client):
        """Sweep: no field may demand characters its keyboard cannot type.

        `inputmode="numeric"` is a digits-only keypad — no colon, no minus,
        no decimal point on several mobile browsers. Any field whose valid
        values need one of those must not declare it.
        """
        html = client.get("/").get_data(as_text=True)
        form = html[html.index('<form method="post"'):html.index("</form>")]
        tags = {m.group(1): m.group(0) for m in
                re.finditer(r'<input id="(\w+)"[^>]*>', form, re.S)}
        # Dates and times get native pickers — no free typing to trap.
        for field in ("date", "p_date"):
            assert 'type="date"' in tags[field], field
        for field in ("time", "p_time"):
            assert 'type="time"' in tags[field], field
        # Coordinates are signed decimals; a numeric keypad may offer no
        # minus key, which would make the southern and western hemispheres
        # unreachable. They take a full keyboard, and the parser also
        # accepts a hemisphere letter so a bare keypad still suffices.
        for field in ("lat", "lon"):
            assert 'inputmode="numeric"' not in tags[field], field
            assert 'type="number"' not in tags[field], field
        from app import parse_coord
        assert parse_coord("33.87 S", "latitude") == -33.87
        assert parse_coord("70.67 W", "longitude") == -70.67

    def test_coordinate_parsing_shapes_and_refusals(self):
        from app import parse_coord
        assert parse_coord("19.07", "latitude") == 19.07
        assert parse_coord("-33.87", "latitude") == -33.87
        assert parse_coord("33.87 S", "latitude") == -33.87
        assert parse_coord("33,87S", "latitude") == -33.87     # comma decimal
        assert parse_coord("19.07° N", "latitude") == 19.07     # pasted
        assert parse_coord("−70.67", "longitude") == -70.67  # unicode −
        # Refusals that protect the chart from a silently wrong sign:
        for bad, axis in (("33.87 E", "latitude"),      # wrong hemisphere
                          ("-33.87 S", "latitude"),     # sign AND letter
                          ("99.9", "latitude"),         # out of range
                          ("200", "longitude"),
                          ("abc", "longitude"), ("", "latitude")):
            with pytest.raises(ValueError):
                parse_coord(bad, axis)

    def test_native_time_value_casts_the_same_chart(self, client):
        """The <input type="time"> wire format must reach the engine intact.

        A shifted hour would move the Lagna by ~15° and could move the Moon
        across a pada boundary, changing the whole Vimśottarī timeline — so
        this asserts the identity end to end, not just the parse.
        """
        import re as _re
        signatures = set()
        for spelling in ("06:57", "6:57 AM", "0657"):
            html = client.post(
                "/", data={**GATE_FORM, "time": spelling}
            ).get_data(as_text=True)
            signatures.add((
                _re.search(r"Leo \d+°\d+′\d+″", html).group(0),
                _re.search(r"Candra in (\w+) p\.(\d)", html).groups(),
                _re.search(r"(\w+) mahādaśā · (\w+) antara", html).groups(),
            ))
        assert len(signatures) == 1, signatures
        lagna, nak, dasha = signatures.pop()
        assert lagna == "Leo 11°05′08″"
        assert nak == ("Rohini", "2")
        assert dasha == ("Rahu", "Sun")

    def test_twelve_hour_input_casts_identical_chart(self, client, page):
        # 06:57 posted as "6:57 AM" must cast the same lagna.
        resp = client.post("/", data={**GATE_FORM, "time": "6:57 AM"})
        assert resp.status_code == 200
        assert "Leo 11°05′" in resp.get_data(as_text=True)

    def test_friendly_inline_time_error(self, client):
        resp = client.post("/", data={**GATE_FORM, "time": "25:00"})
        assert resp.status_code == 400
        html = resp.get_data(as_text=True)
        assert "the hour runs 0–23" in html
        assert f'value="{GATE_FORM["date"]}"' in html  # values preserved

    def test_missing_timezone_is_never_guessed(self, client):
        resp = client.post("/", data={**GATE_FORM, "tz": ""})
        assert resp.status_code == 400
        assert "must never be guessed" in resp.get_data(as_text=True)

    def test_optional_name_on_dashboard(self, client):
        resp = client.post("/", data={**GATE_FORM, "name": "Test Person"})
        assert "Chart of Test Person" in resp.get_data(as_text=True)
        # Anonymous fallback:
        resp = client.post("/", data=GATE_FORM)
        assert "Janma kundli" in resp.get_data(as_text=True)

    def test_cities_api_offline_lookup(self, client):
        resp = client.get("/api/cities?q=mumb")
        top = resp.get_json()["results"][0]
        assert top["label"] == "Mumbai, Maharashtra, India"
        assert top["tz"] == "Asia/Kolkata"
        assert abs(top["lat"] - 19.07) < 0.1
        # Under 3 characters: no suggestions.
        assert client.get("/api/cities?q=mu").get_json()["results"] == []
        # Diacritic folding: plain ASCII finds São Paulo.
        labels = [r["label"] for r in
                  client.get("/api/cities?q=sao paulo").get_json()["results"]]
        assert any("São Paulo, São Paulo, Brazil" == x for x in labels)

    def test_non_reference_chart_renders(self, client):
        resp = client.post("/", data={
            "name": "", "date": "1990-03-15", "time": "08:45",
            "lat": "19.07283", "lon": "72.88261", "tz": "Asia/Kolkata",
            "place": "Mumbai, Maharashtra, India",
        })
        assert resp.status_code == 200
        html = resp.get_data(as_text=True)
        assert "Mumbai" in html
        assert 'id="pane-d9"' in html and "Paṭha" in html

    def test_dashboard_identity_line(self, page):
        assert "Leo 11°05′" in page            # lagna sign + degree
        assert "Rohini p.2" in page            # Moon nakshatra

    def test_chart_degree_labels(self, page):
        # 'Abbr D°MM′' with R for retrograde, reference-chart values:
        assert "Ju 2°53′ R" in page
        assert "Sa 9°47′ R" in page
        assert "As 11°05′" in page          # lagna degree in house 1
        assert "Mo 15°17′" in page
        # Both label modes render; the toggle switches between them.
        assert "grahas-deg" in page and "grahas-compact" in page
        assert 'id="degToggle"' in page

    def test_dashboard_has_three_chart_tabs(self, page):
        for pane in ("pane-d1", "pane-d9", "pane-d10"):
            assert f'id="{pane}"' in page
        assert "D9 lagna Cancer" in page
        assert "D10 lagna Scorpio" in page
        assert "Vargottama: Moon, Mars" in page

    def test_dashboard_dasha_ledger(self, page):
        assert "Jupiter mahādaśā" in page
        assert "Mercury mahādaśā" in page
        assert "Venus antara" in page

    def test_dashboard_transits_and_yogas(self, page):
        assert "Gocara" in page
        assert "Budhaditya Yoga" in page
        assert "Sarala (Viparita Raja) Yoga" in page
        assert "Neecha Bhanga (Mars)" in page
        assert "own sign" in page              # dignity column
        assert "moolatrikona" in page          # graded dignity surfaced

    def test_dashboard_nakshatra_table(self, page):
        assert "Ashwini" in page               # Saturn's nakshatra
        assert "Magha" in page                 # Lagna's nakshatra

    def test_bad_input_returns_form_error(self, client):
        resp = client.post("/", data={**GATE_FORM, "date": "not-a-date"})
        assert resp.status_code == 400
        assert "a real calendar date" in resp.get_data(as_text=True)


@pytest.fixture(scope="module")
def yogas(chart):
    return detect_all(chart)


class TestPhase7ExplanationEngine:
    def test_confidence_is_mandatory_and_validated(self):
        from explain import Explanation
        with pytest.raises(ValueError):
            Explanation(fact="f", mechanism="m", meaning="x",
                        confidence="Certain")
        with pytest.raises(TypeError):
            Explanation(fact="f", mechanism="m", meaning="x")  # no tag

    def test_every_explanation_has_three_layers_and_tag(
            self, chart, timeline, snapshot, yogas):
        from explain import CONFIDENCE_LEVELS, explain_dashboard
        items = explain_dashboard(chart, timeline, snapshot, yogas)
        # Lagna + lagna nakshatra + 9 planets ×2 + dasha + gocara + 8 yogas
        assert len(items) == 2 + 18 + 2 + len(yogas)
        for item in items:
            xp = item.explanation
            assert xp.fact and xp.mechanism and xp.meaning
            assert xp.confidence in CONFIDENCE_LEVELS

    def test_planet_mechanism_shows_counting(self, chart):
        from explain import explain_planet
        xp = explain_planet(chart, "Sun")
        # Full Whole-Sign count from the Lagna, every step shown.
        assert "Leo 1" in xp.mechanism
        assert "Cancer 12" in xp.mechanism
        assert "12th house" in xp.mechanism
        assert xp.confidence == "Interpretive"

    def test_moon_mechanism_shows_dignity_working(self, chart):
        from explain import explain_planet
        xp = explain_planet(chart, "Moon")
        assert "In Taurus, Moon is moolatrikona" in xp.mechanism
        # The graded field flows into the explanation layer.
        assert "Graded: moolatrikona (3°–30° span)" in xp.mechanism
        assert "moolatrikona (3°–30° span)" in xp.fact

    def test_exaltation_zone_mechanism_is_shown(self):
        # No planet is exalted in the reference chart, so the BPHS
        # segmentation copy is pinned on a constructed one.
        from explain import explain_planet
        xp = explain_planet(synthetic_chart(8, {"Mercury": (5, 1.0)}),
                            "Mercury")
        assert "own and exaltation sign" in xp.mechanism
        assert "exaltation zone" in xp.mechanism
        assert "15°00′" in xp.mechanism  # deep-exaltation degree shown
        assert ("Graded: exalted (early degree, rising toward deep "
                "exaltation at 15°)") in xp.mechanism
        assert "exalted (early degree" in xp.fact

    def test_nakshatra_mechanism_shows_arithmetic(self, chart):
        from explain import explain_nakshatra
        xp = explain_nakshatra("Moon", chart.planets["Moon"].longitude)
        assert "13°20′" in xp.mechanism
        assert "Rohini" in xp.mechanism
        assert "pada 2" in xp.mechanism
        assert "Prajapati" in xp.meaning
        assert xp.confidence == "Moderate"

    def test_dasha_mechanism_shows_balance_arithmetic(self, chart, timeline):
        from explain import explain_dasha_now
        xp = explain_dasha_now(timeline,
                               datetime(2026, 7, 11, tzinfo=timezone.utc))
        assert "Rahu mahādaśā" in xp.fact
        assert "6.03 years" in xp.mechanism        # birth balance shown
        assert "md_years × ad_years ÷ 120" in xp.mechanism
        assert "Ketu 7y → Venus 20y" in xp.mechanism  # fixed order shown

    def test_yoga_explanations(self, chart, yogas):
        from explain import explain_yoga
        by_name = {y.name: explain_yoga(chart, y) for y in yogas}
        assert by_name["Sarala (Viparita Raja) Yoga"].confidence == "High"
        assert by_name["Neecha Bhanga (Mars)"].confidence == "High"
        assert by_name["Budhaditya Yoga"].confidence == "Moderate"
        # Rule appears verbatim.
        for y in yogas:
            assert y.rule in by_name[y.name].mechanism

    def test_yoga_friction_note_reaches_the_mechanism(self):
        # Pinned on the constructed enemy-lords chart (see Phase 5), since
        # the reference chart forms no friction-bearing Dhana yoga.
        from explain import explain_yoga
        c = synthetic_chart(8, {
            "Sun": 5, "Moon": 2, "Mars": 3, "Mercury": 5, "Jupiter": 8,
            "Venus": 4, "Saturn": 11, "Rahu": 5, "Ketu": 11,
        })
        y = next(y for y in detect_dhana(c) if y.notes)
        assert "natural enemies" in explain_yoga(c, y).mechanism

    def test_ui_renders_patha_and_chips(self, page):
        assert "Paṭha" in page
        assert "Mechanism" in page and "Meaning" in page
        for tag in ("High", "Moderate", "Interpretive"):
            assert f">{tag}</span>" in page


class TestPhase8ShowYourWorking:
    def test_explorer_payload_jupiter(self, chart):
        from app import planet_explorer
        px = planet_explorer(chart)["Jupiter"]
        # Jupiter in Pisces (house 8): 5th → h12, 7th → h2, 9th → h4.
        assert px["house"] == 8 and px["dignity"] == "own sign"
        by_off = {a["offset"]: a for a in px["aspects"]}
        assert by_off[5]["house"] == 12
        assert sorted(by_off[5]["hits"]) == [
            "Mars", "Mercury", "Sun", "Venus"]
        assert by_off[7]["house"] == 2 and by_off[7]["hits"] == []
        assert by_off[9]["house"] == 4 and by_off[9]["hits"] == []

    def test_explorer_carries_graded_dignity(self, chart):
        from app import planet_explorer
        px = planet_explorer(chart)
        # The graded field, not the bare state, reaches the explorer card.
        assert px["Saturn"]["dignity"] == \
            "debilitated (early degree, approaching deep fall at 20°)"
        assert px["Moon"]["dignity"] == "moolatrikona (3°–30° span)"

    def test_explorer_nakshatra_wiring(self, chart):
        from app import planet_explorer
        px = planet_explorer(chart)
        # Saturn in Ashwini → star-lord Ketu, sitting in house 7.
        assert px["Saturn"]["nak_lord"] == "Ketu"
        assert px["Saturn"]["nak_lord_house"] == 7
        # Moon in Rohini — its own star, so lord and planet share a house.
        assert px["Moon"]["nak_lord"] == "Moon"
        assert px["Moon"]["nak_lord_house"] == px["Moon"]["house"]

    def test_page_has_explorer_ui(self, page):
        assert page.count('class="chip-planet"') == 9
        assert "EXPLORER" in page and "HOUSE_SHAPES" in page
        assert 'id="xcard"' in page
        # Every yoga card carries a Why? button with its forming planets.
        assert page.count('class="whybtn"') == 8
        assert 'data-planets="Mars,Moon"' in page      # Neecha Bhanga
        assert 'data-planets="Sun,Mercury"' in page    # Budhaditya

    def test_house_shapes_cover_all_twelve(self, page):
        for h in range(1, 13):
            assert f"\n  {h}: " in page or f" {h}:  [" in page or \
                re.search(rf"\b{h}:\s+\[\[", page), f"house {h} shape missing"


class TestPhase9LifeTimeline:
    NOW = datetime(2026, 7, 13, tzinfo=timezone.utc)

    def test_ingress_finder_known_events(self):
        from transits import next_sign_ingress, sign_entry_before
        sat = next_sign_ingress("Saturn", self.NOW)
        assert sat.to_sign == "Aries"
        assert date(2027, 4, 1) <= sat.when.date() <= date(2027, 8, 1)
        jup = next_sign_ingress("Jupiter", self.NOW)
        assert jup.to_sign == "Leo"
        assert date(2026, 9, 1) <= jup.when.date() <= date(2026, 12, 15)
        rahu = next_sign_ingress("Rahu", self.NOW)
        assert rahu.to_sign == "Capricorn"  # nodes move backwards
        assert date(2026, 10, 15) <= rahu.when.date() <= date(2027, 1, 31)
        # Saturn's real Pisces entry was 29 Mar 2025 (sidereal Lahiri).
        entry = sign_entry_before("Saturn", self.NOW)
        assert abs((entry.date() - date(2025, 3, 29)).days) <= 7

    def test_upcoming_ingresses_sorted_and_bounded(self):
        from transits import upcoming_ingresses
        events = upcoming_ingresses(self.NOW, horizon_days=1095)
        assert events == sorted(events, key=lambda e: e.when)
        assert all(e.when <= self.NOW + timedelta(days=1100) for e in events)
        assert {e.planet for e in events} == {"Saturn", "Jupiter", "Rahu"}

    def test_life_timeline_data(self, chart, timeline):
        from app import life_timeline
        life = life_timeline(chart, timeline, self.NOW)
        assert len(life["bands"]) == 9
        cur = [b for b in life["bands"] if b["status"] == "current"]
        assert len(cur) == 1 and cur[0]["lord"] == "Rahu"
        assert 0 < cur[0]["elapsed"] < 1
        past = [b["lord"] for b in life["bands"] if b["status"] == "past"]
        assert past == ["Moon", "Mars"]
        assert abs(life["here_age"] - 27.9) < 0.3
        # Bands tile the 120 years in order.
        assert life["bands"][0]["start_age"] == 0.0
        # 120y cycle minus the 3.97y of Moon MD already elapsed at birth.
        assert abs(life["bands"][-1]["end_age"] - 116.03) < 0.3
        assert life["markers"], "expected dated upcoming transit markers"
        assert all(m["date"] and 1 <= m["natal_house"] <= 12
                   for m in life["markers"])

    def test_page_renders_lifeline(self, page):
        assert "You are HERE" in page
        assert 'class="lifegraph"' in page
        assert page.count('class="rated"') == 3  # Jupiter, Saturn, Mercury
        assert 'class="star"' in page and "rate the fit" in page
        assert 'class="tmarker"' in page


class TestPhase10AntiAnxiety:
    NOW = datetime(2026, 7, 13, tzinfo=timezone.utc)

    def test_mangal_formed_but_cancelled(self, chart):
        from doshas import detect_mangal
        d = detect_mangal(chart)
        # Mars in the 12th forms the pattern; Jupiter's 5th drishti from
        # Pisces lands on Cancer, which is a classical tempering exception.
        assert d.formed is True and d.active is False
        assert any("Jupiter tempers Mars" in c for c in d.cancellations)
        assert len(d.checks_run) == 4  # every check auto-ran

    def test_kaal_sarpa_formed_and_its_margins_shown(self, chart):
        from doshas import detect_kaal_sarpa
        d = detect_kaal_sarpa(chart)
        # All seven grahas fall in the Ketu→Rahu arc. The pattern is the
        # single most fear-marketed configuration in popular jyotisha, so
        # the detail must show the geometry that produced it — including
        # how narrowly it holds.
        assert d.formed is True
        assert "Ketu→Rahu arc" in d.detail
        assert "Sun closest to Rahu" in d.detail
        assert "would dissolve the pattern" in d.detail

    def test_kaal_sarpa_not_formed_when_a_graha_crosses(self, chart):
        from doshas import detect_kaal_sarpa
        # Move the Sun — the graha nearest the axis — across it, and the
        # pattern must dissolve. This pins the rule, not just the chart.
        from engine import Chart, PlanetPosition
        sun = chart.planets["Sun"]
        moved = dict(chart.planets)
        moved["Sun"] = PlanetPosition(
            longitude=(sun.longitude + 20) % 360, speed=sun.speed,
            name="Sun", house=sun.house)
        d = detect_kaal_sarpa(Chart(birth=chart.birth, lagna=chart.lagna,
                                    planets=moved, ayanamsa=chart.ayanamsa))
        assert d.formed is False and d.active is False
        assert "both sides" in d.detail and "Sun" in d.detail

    def test_sade_sati_inactive_with_dated_next_window(self, chart):
        from doshas import sade_sati_status
        d = sade_sati_status(chart, self.NOW)
        # Saturn in Pisces is the 11th from a Taurus Moon — not running.
        assert d.active is False and "11th sign" in d.detail
        # The next window must be dated: Saturn enters Aries, the 12th from
        # the Moon, in mid-2027.
        assert d.next_window == "Jun 2027"

    def test_transit_weather_always_dated(self, chart):
        from doshas import transit_weather
        from transits import transit_snapshot
        snap = transit_snapshot(chart, self.NOW)
        cards = transit_weather(chart, snap)
        # Both nodes render — they share motion but occupy different houses.
        assert {c["planet"] for c in cards} == {
            "Saturn", "Jupiter", "Rahu", "Ketu"}
        for c in cards:
            assert c["until"] is not None       # end date ALWAYS shown
            assert c["progress"] is not None and 0 <= c["progress"] <= 1
        sat = next(c for c in cards if c["planet"] == "Saturn")
        # Saturn in Pisces is the 11th from the Taurus Moon — outside the
        # 4/8/12-from-Moon and sade-sati windows, so NOT demanding.
        assert sat["from_moon"] == 11 and sat["demanding"] is False
        # Ketu in Leo is the 4th from Moon — that one IS demanding, and the
        # module must say so rather than reassure by default.
        ketu = next(c for c in cards if c["planet"] == "Ketu")
        assert ketu["from_moon"] == 4 and ketu["demanding"] is True
        assert "already part-done and dated above" in ketu["note"]

    def test_myth_busters_generated_for_present_placements(self, chart):
        from doshas import myth_busters
        cards = myth_busters(chart, self.NOW)
        placements = " | ".join(m.placement for m in cards)
        assert "Mangal dosha pattern" in placements
        assert "Debilitated Mars" in placements
        assert "Kaal Sarpa" in placements
        assert "Sade Sati" in placements
        for m in cards:
            assert m.myth and m.classical_record and m.citation
            assert m.confidence in ("High", "Moderate", "Interpretive")

    def test_myth_buster_claims_are_read_off_the_chart(self):
        """No myth-buster may assert a chart-specific fact it did not compute.

        Regression: the Mars-in-8th card hard-coded "this chart's Mars is the
        12th lord in the 8th — Vimala yoga", which was true only of the
        original reference chart. The card fires on `mars.house == 8` alone,
        so every OTHER user with that placement was told about a yoga they
        may not have. It survived because the committed fixture has Mars in
        the 12th, so the card never fired in the suite.
        """
        from doshas import myth_busters
        from yogas import detect_viparita_raja, house_lords

        checked = 0
        for month in range(1, 13):
            for day in (7, 21):
                for hour in (3, 11, 19):
                    c = compute_chart(BirthData(
                        year=1988, month=month, day=day, hour=hour,
                        minute=30, latitude=19.07, longitude=72.88,
                        tz="+05:30"))
                    if c.planets["Mars"].house != 8:
                        continue
                    card = next(m for m in myth_busters(c, self.NOW)
                                if m.placement == "Mars in the 8th house")
                    record = card.classical_record
                    mars_yogas = [y for y in detect_viparita_raja(c)
                                  if "Mars" in y.planets]
                    if mars_yogas:
                        # It must name the yoga this chart actually forms.
                        assert mars_yogas[0].detail in record
                    else:
                        # …and never invent one when there is none.
                        assert "Viparita logic" not in record
                        owned = [h for h, lord in house_lords(c).items()
                                 if lord == "Mars"]
                        assert all(str(h) in record for h in owned)
                    for name in ("Vimala", "Sarala", "Harsha"):
                        if name in record:
                            assert any(name in y.name for y in mars_yogas), (
                                f"card names {name} but the chart forms "
                                f"{[y.name for y in mars_yogas]}")
                    checked += 1
        assert checked >= 5, f"only exercised {checked} charts"

    def test_kaal_sarpa_card_names_its_late_provenance(self, chart):
        # The honest answer to Kaal Sarpa is that the foundational texts do
        # not contain it. A myth-buster that softened this into "opinions
        # differ" would be doing the thing this module exists to stop.
        from doshas import myth_busters
        card = next(m for m in myth_busters(chart, self.NOW)
                    if "Kaal Sarpa" in m.placement)
        assert "Brihat Parashara" in card.classical_record
        assert "absent" in card.classical_record.lower()
        assert card.confidence == "Interpretive"
        # It still shows the computed geometry rather than only debunking.
        assert "Ketu→Rahu arc" in card.classical_record

    def test_no_fear_language_anywhere(self, page):
        import doshas as doshas_mod
        import explain as explain_mod
        banned = re.compile(
            r"\b(doom|curse|cursed|disaster|catastroph\w*|fatal|dread\w*|"
            r"terrible|ruin\w*|widow\w*|death|dangerous|suffer\w*|"
            r"misfortune)\b", re.IGNORECASE)
        for name, src in (("dashboard", page),
                          ("doshas.py", open(doshas_mod.__file__).read()),
                          ("explain.py", open(explain_mod.__file__).read())):
            hit = banned.search(src)
            assert hit is None, f"fear language in {name}: {hit.group()!r}"

    def test_page_renders_weather_doshas_mythbusters(self, page):
        assert "Weather, not verdict" in page
        assert "checks always run" in page.lower() or "Checks run" in page
        assert 'class="pbar"' in page          # progress bars present
        assert "Myth vs classical record" in page
        assert "Next window opens" in page     # dated sade-sati forecast
        assert "formed · cancelled" in page    # Mangal shown WITH checks


class TestPhase11LearnAsYouGo:
    def test_twenty_card_path_lagna_to_d9(self):
        from lessons import LESSONS
        assert len(LESSONS) == 20
        assert [l.number for l in LESSONS] == list(range(1, 21))
        assert LESSONS[0].title == "What is a lagna?"
        assert LESSONS[-1].title == "Read your own D9"
        keys = [l.key for l in LESSONS]
        assert len(set(keys)) == 20  # unique keys

    def test_lessons_are_sixty_second_reads(self):
        from lessons import LESSONS
        for l in LESSONS:
            words = len(l.body.split())
            assert 40 <= words <= 170, f"{l.key}: {words} words"

    def test_contextual_index_resolves(self):
        from lessons import CONTEXT_LESSONS, lesson
        assert len(CONTEXT_LESSONS) >= 8
        for section, key in CONTEXT_LESSONS.items():
            assert lesson(key).title, f"{section} → {key} unresolved"

    def test_no_fear_language_in_lessons(self):
        import lessons as lessons_mod
        banned = re.compile(
            r"\b(doom|curse|cursed|disaster|catastroph\w*|fatal|dread\w*|"
            r"terrible|ruin\w*|widow\w*|dangerous|suffer\w*|misfortune)\b",
            re.IGNORECASE)
        hit = banned.search(open(lessons_mod.__file__).read())
        assert hit is None, f"fear language in lessons: {hit.group()!r}"

    def test_page_renders_learn_ui(self, page):
        assert "Learn the sky · 20 cards" in page
        assert page.count('class="learn"') >= 8      # contextual ⓘ chips
        assert page.count("lessoncard") >= 20        # full path rendered
        assert 'id="lmodal"' in page                 # micro-lesson modal
        assert "What is a lagna?" in page
        assert "Read your own D9" in page
        assert 'id="learnprogress"' in page          # read-progress counter


WALKTHROUGH_NOW = datetime(2026, 7, 15, tzinfo=timezone.utc)


@pytest.fixture(scope="module")
def weather(chart):
    from doshas import transit_weather
    from transits import transit_snapshot
    return transit_weather(chart, transit_snapshot(chart, WALKTHROUGH_NOW))


class TestUIRevisionWalkthrough:
    """Commissioner's walkthrough fixes (items A–F)."""

    NOW = WALKTHROUGH_NOW

    def test_b_exalted_jupiter_line(self, weather):
        # Jupiter transits Cancer — its exaltation sign. The note must be
        # generated from the dignity engine, never a generic fallback.
        jup = next(c for c in weather if c["planet"] == "Jupiter")
        assert jup["dignity"] == "exalted"
        assert "exalted" in jup["note"]
        assert "strongest terrain" in jup["note"]
        # The graded field flows through: past the 5° deep-exaltation
        # degree, so the note says 'easing' rather than flatly 'exalted'.
        assert "past the deep exaltation degree at 5°, easing" in jup["note"]
        # Moon-relative quality consumed too: Cancer is 3rd from a Taurus
        # Moon — neutral for Jupiter.
        assert jup["from_moon"] == 3 and jup["quality"] == "neutral"
        assert jup["confidence"] == "Interpretive"
        # The lazy fallback is gone from every card.
        for c in weather:
            assert "ordinary working transit" not in c["note"]
            assert c["until"] is not None

    def test_b_jupiter_on_natal_venus_contact(self, weather):
        # Mid-July 2026: transit Jupiter sits 0.45° from natal Venus
        # (9.43° Cancer) — must surface prominently with the end date.
        jup = next(c for c in weather if c["planet"] == "Jupiter")
        assert jup["sign"] == "Cancer" and jup["natal_house"] == 12
        venus = next(c for c in jup["contacts"] if c["natal"] == "Venus")
        assert venus["orb"] < 1.0 and venus["exact"] is True
        assert "exact contact" in jup["contact_note"]
        assert "Venus" in jup["contact_note"]
        assert "Oct 2026" in jup["contact_note"]  # dated end

    def test_b_nodal_return_surfaces_on_both_nodes(self, weather):
        # Transit Rahu is back on natal Ketu and vice versa, inside 0.3°.
        # Both cards must carry it — a node is not a footnote of its twin.
        for node, natal in (("Rahu", "Ketu"), ("Ketu", "Rahu")):
            card = next(c for c in weather if c["planet"] == node)
            hit = next(c for c in card["contacts"] if c["natal"] == natal)
            assert hit["orb"] < 0.3 and hit["exact"] is True
            assert "exact contact" in card["contact_note"]

    def test_c_ketu_has_its_own_row(self, page):
        assert "Ketu in Leo" in page

    def test_d_no_broken_ordinals(self, page):
        # '3th', '2th', '21th' … must never render; 11th/12th/13th are fine.
        bad = re.findall(r"\b\d*(?<!1)[123]th\b", page)
        assert bad == [], f"broken ordinals: {bad}"
        assert "9th house" in page or "9th sign" in page  # filter in use

    def test_e_marker_labels_decollided(self, chart, timeline):
        from app import life_timeline
        life = life_timeline(chart, timeline, self.NOW)
        by_row: dict = {}
        for m in life["markers"]:
            assert m["row"] in (0, 1, 2) and "label_x" in m
            by_row.setdefault(m["row"], []).append(m["label_x"])
        for row, xs in by_row.items():
            xs = sorted(xs)
            gaps = [b - a for a, b in zip(xs, xs[1:])]
            assert all(g >= 117.9 for g in gaps), f"row {row} collides: {xs}"

    def test_f_favicon_served(self, client):
        for path in ("/favicon.ico", "/apple-touch-icon.png"):
            resp = client.get(path)
            assert resp.status_code == 200
            assert b"<svg" in resp.data

    def test_design_handoff_pastel_tokens(self):
        # DESIGN-HANDOFF.md: "Active palette: Pastel" — it is the default,
        # i.e. the values on bare :root before any [data-palette] applies.
        css = open(HERE / "static/style.css").read()
        default = css[css.index(":root,"):css.index('[data-palette="gold"]')]
        assert "--ink: #585270" in default
        assert "--accent: #a99bc9" in default
        assert "--accent-300: #cfc4e4" in default
        fav = open(HERE / "static/favicon.svg").read()
        assert "#585270" in fav and "#cfc4e4" in fav

    def test_framework_six_palettes_by_root_attribute(self):
        # Build framework, SIX · TOKENS: all six stored centrally and
        # switched by custom properties on the root — never conditional
        # colour in components.
        css = open(HERE / "static/style.css").read()
        for pal in ("pastel", "gold", "sindoor", "twilight", "rose",
                    "verdigris"):
            assert f':root[data-palette="{pal}"]' in css, pal
        # every palette supplies the full accent ramp + ghost + ink
        block = css[:css.index("* { box-sizing")]
        for token in ("--ink", "--accent", "--accent-300", "--accent-400",
                      "--ghost"):
            assert block.count(token) >= 6, token

    def test_framework_non_negotiable_tokens(self):
        # "Square corners everywhere. The device bezel is the only radius"
        # — the sole exception in-app is a circular score ring.
        css = open(HERE / "static/style.css").read()
        radii = re.findall(r"border-radius:\s*([^;]+);", css)
        assert sorted(set(radii)) == ["0", "50%"], radii
        # "No shadows, no gradients, no elevation."
        assert "box-shadow" not in css and "gradient" not in css

    def test_design_handoff_glance_pattern(self, page):
        # 4b/5a: kicker date line, statement, ghost ☾, three chips, panel.
        assert 'class="glance"' in page
        assert "☾" in page
        assert 'class="statement"' in page
        assert page.count('class="gchip') == 3
        for pane in ("gpane-chart", "gpane-transits", "gpane-dasha"):
            assert f'id="{pane}"' in page
        # chart pane caption keeps the identity facts
        assert "Candra in Rohini p.2" in page
        # Re-baselined 2026-08-22: the statement is now composed by the
        # reading engine (milestone 06), not the old MD/AD template. What
        # the design requires is a one-statement hero with a tinted span.
        assert "A Mercury season, Venus antara" not in page
        assert 'class="statement"' in page
        assert '<span class="accent">' in page
        # dasha pane ring + transits pane dated rows
        assert 'class="gring"' in page
        assert 'class="growlist"' in page

    def test_a_navigation_and_disclosure(self, page):
        assert 'class="secnav"' in page
        for anchor in ("#glance", "#plate", "#dashas", "#lifeline",
                       "#weather", "#doshas", "#myths", "#yogas", "#ask",
                       "#patha", "#grahas", "#learnpath"):
            assert f'href="{anchor}"' in page, anchor
        # progressive disclosure: antardashas, gocara table, doshas and
        # myth cards are all summary-first now
        assert page.count('class="fold"') >= 2
        assert page.count("<details class=\"yoga\">") >= 7  # doshas + myths


# The framework's own sample place; a fixed instant for determinism.
PANCANGA_WHEN = datetime(2026, 7, 11, 6, 0, tzinfo=timezone.utc)
JAIPUR = (26.9, 75.8)

# The build framework names a snapshot persona (TWO · ARCHITECTURE,
# TESTING RULE) — "Aisha Rao, 14 Aug 1998, 04:32, Jaipur — Siṃha lagna,
# Candra in Rohiṇī pada 2". Those two claims are NOT satisfied by that birth
# data: at 14 Aug 04:32 the lagna is Cancer and the Moon is in Bharaṇī. The
# derived values are real, though — they are reproduced to the arc-minute by
# 16 Aug 1998, 06:57 IST, which is the fixture used here. See
# ui-design/FRAMEWORK-AUDIT.md for the full reconciliation.
#
# This is also the committed REFERENCE chart, so AISHA_BIRTH == GATE_BIRTH:
# the whole suite runs on the fictional persona and no real birth record is
# committed. PARTNER_BIRTH is a second fictional record ("Dev Menon"), which
# the aṣṭakūṭa gates need — pairing a chart with itself would make the
# tables look symmetric and every kūṭa full.
AISHA_BIRTH = fixtures.birth("aisha")
PARTNER_BIRTH = fixtures.birth("partner")


@pytest.fixture(scope="module")
def p():
    from pancanga import compute_pancanga
    return compute_pancanga(PANCANGA_WHEN, *JAIPUR)


class TestDeployability:
    """Production readiness — the app must run under gunicorn on a container
    with nothing mounted and no secrets set."""

    def test_ephemeris_backend_is_explicit(self):
        # swisseph silently falls back from SWIEPH to Moshier when no .se1
        # files are present. That fallback is what makes the app deployable
        # with nothing to mount — so it is asserted, not assumed. If this
        # goes red, the numerical source changed and every gate value must
        # be re-verified before the failure is "fixed".
        from engine import ephemeris_backend
        assert ephemeris_backend() == "moseph"

    def test_no_ephemeris_files_are_required(self):
        assert not list(HERE.glob("**/*.se1"))
        assert not list(HERE.glob("**/*.se2"))

    def test_data_files_resolve_independently_of_cwd(self):
        # The city dataset is opened relative to the module, not the working
        # directory — Render starts the process elsewhere.
        import subprocess, sys
        out = subprocess.run(
            [sys.executable, "-c",
             "import sys; sys.path.insert(0, %r);"
             "from app import app;"
             "c = app.test_client();"
             "print(c.get('/api/cities?q=mumb').status_code)" % str(HERE)],
            cwd="/", capture_output=True, text=True)
        assert out.stdout.strip() == "200", out.stderr[-400:]

    def test_procfile_matches_documented_start_command(self):
        procfile = (HERE / "Procfile").read_text()
        assert "gunicorn app:app" in procfile
        assert "--bind 0.0.0.0:$PORT" in procfile
        deploy = (HERE / "DEPLOY.md").read_text()
        assert "gunicorn app:app --bind 0.0.0.0:$PORT" in deploy

    def test_gunicorn_is_pinned(self):
        reqs = (HERE / "requirements.txt").read_text()
        assert "gunicorn==" in reqs

    def test_debug_is_not_enabled_by_import(self):
        # gunicorn imports `app` and never runs __main__, so no deploy path
        # can turn the debugger on.
        from app import app as flask_app
        assert flask_app.debug is False

    def test_no_secrets_or_local_paths_in_source(self):
        import re as _re
        banned = _re.compile(
            r"(/Users/|C:\\Users|sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{20,}|"
            r"AKIA[0-9A-Z]{16}|BEGIN [A-Z ]*PRIVATE KEY)")
        # The scanners necessarily contain the patterns they search for.
        scanners = {"test_gates.py", "test_hygiene.py", "conftest.py"}
        paths = [p for p in list(HERE.glob("*.py"))
                 + list(HERE.glob("reading/*.py"))
                 + list(HERE.glob("templates/*.html"))
                 + list(HERE.glob("static/*.css"))
                 if p.name not in scanners]
        for path in paths:
            hit = banned.search(path.read_text(encoding="utf-8"))
            assert hit is None, f"{path.name}: {hit.group()!r}"

    def test_landing_states_what_and_why_with_one_cta(self, client):
        html = client.get("/").get_data(as_text=True)
        assert "sidereal Vedic chart" in html          # what it is
        assert "Every reading shows its computation" in html   # differentiator
        assert html.count('class="cta"') == 1          # a single CTA
        assert 'href="#cast"' in html
        assert "Built by" in html and "linkedin.com/in/" in html
        assert "Feedback" in html


class TestPancanga:
    """Domain contract from the build framework (THREE · DOMAIN MODEL)."""

    WHEN = PANCANGA_WHEN
    JAIPUR = JAIPUR

    def test_five_limbs_present(self, p):
        assert p.tithi.name and p.nakshatra.name and p.yoga.name
        assert p.karana.name and p.weekday_name
        assert p.sunrise and p.sunset

    def test_tithi_and_paksa(self, p):
        # Full moon fell 29 Jun 2026; 11 Jul is twelve tithis into the dark
        # fortnight → kṛṣṇa Dvādaśī, tithi 27 of 30.
        assert p.tithi.index == 27
        assert p.paksa == "kṛṣṇa"
        assert p.tithi.name == "Dvādaśī"
        assert p.tithi_label == "kṛṣṇa Dvādaśī"

    def test_full_and_new_moon_edges(self):
        from pancanga import compute_pancanga
        full = compute_pancanga(
            datetime(2026, 6, 29, 12, tzinfo=timezone.utc), *self.JAIPUR)
        assert full.tithi.index == 15 and full.tithi.name == "Pūrṇimā"
        assert full.paksa == "śukla"
        # Amāvāsyā is tithi 30, closing the dark fortnight — a ~20-hour
        # window here, entered during the evening of 13 Jul.
        new = compute_pancanga(
            datetime(2026, 7, 13, 18, tzinfo=timezone.utc), *self.JAIPUR)
        assert new.tithi.index == 30 and new.tithi.name == "Amāvāsyā"
        assert new.paksa == "kṛṣṇa"

    def test_karana_naming_rule(self):
        from pancanga import karana_name
        assert karana_name(1) == "Kiṃstughna"     # fixed, opens the lunation
        assert karana_name(2) == "Bava"           # movable cycle starts
        assert karana_name(8) == "Viṣṭi"
        assert karana_name(9) == "Bava"           # cycle repeats
        assert karana_name(57) == "Viṣṭi"
        assert karana_name(58) == "Śakuni"        # fixed, closes it
        assert karana_name(59) == "Catuṣpāda"
        assert karana_name(60) == "Nāga"

    def test_nakshatra_agrees_with_dasha_module(self, p):
        # One source of truth: the Moon's nakṣatra comes from longitude only.
        from dashas import nakshatra_of
        from engine import julian_day_ut, sidereal_positions
        moon = sidereal_positions(julian_day_ut(self.WHEN))["Moon"]
        assert p.nakshatra.name == nakshatra_of(moon.longitude).name
        assert p.nakshatra.name == "Rohini"

    def test_angas_carry_end_times(self, p):
        # Every limb gives way; the framework's contract requires endsAt.
        for anga in (p.tithi, p.nakshatra, p.yoga, p.karana):
            assert anga.ends_at is not None
            assert anga.ends_at > self.WHEN
            assert anga.ends_at < self.WHEN + timedelta(days=2)
        # Karana is half a tithi, so it never outlasts its tithi.
        assert p.karana.ends_at <= p.tithi.ends_at

    def test_sunrise_sunset_at_place(self, p):
        # Jaipur mid-July: sunrise ~05:42 IST, sunset ~19:23 IST (UTC+5:30).
        assert p.sunrise.strftime("%H:%M") == "00:12"
        assert p.sunset.strftime("%H:%M") == "13:53"
        assert p.sunset > p.sunrise

    def test_weekday_and_lord(self, p):
        # 11 July 2026 is a Saturday — Śanivāra, ruled by Saturn.
        assert p.weekday_name == "Śanivāra"
        assert p.weekday_lord == "Saturn"

    def test_deterministic(self):
        from pancanga import compute_pancanga
        a = compute_pancanga(self.WHEN, *self.JAIPUR)
        b = compute_pancanga(self.WHEN, *self.JAIPUR)
        assert (a.tithi, a.yoga, a.karana, a.sunrise) == \
               (b.tithi, b.yoga, b.karana, b.sunrise)


@pytest.fixture(scope="module")
def aisha():
    return compute_chart(AISHA_BIRTH)


@pytest.fixture(scope="module")
def partner():
    return compute_chart(PARTNER_BIRTH)


@pytest.fixture(scope="module")
def match(chart, partner):
    from gunamilan import guna_milan
    return guna_milan("Aisha", chart, "Dev", partner)


class TestFrameworkFixturePersona:
    """Milestone 01: 'Prove Aisha's Siṃha lagna at 11°04′ in a test before
    writing anything else.' Proven here — against corrected birth data."""

    def test_simha_lagna_at_eleven_degrees(self, aisha):
        assert aisha.lagna.sign == "Leo"                  # Siṃha
        assert abs(aisha.lagna.degree_in_sign - 11.07) < 0.05   # 11°04′

    def test_candra_in_rohini_pada_two(self, aisha):
        from dashas import vimshottari
        nak = vimshottari(aisha).moon_nakshatra
        assert nak.name == "Rohini" and nak.pada == 2

    def test_stated_birth_data_does_not_yield_stated_values(self):
        # The discrepancy itself is pinned, so the audit's claim stays true.
        as_written = compute_chart(BirthData(
            year=1998, month=8, day=14, hour=4, minute=32,
            latitude=AISHA_BIRTH.latitude, longitude=AISHA_BIRTH.longitude,
            tz=AISHA_BIRTH.tz))
        assert as_written.lagna.sign == "Cancer"          # not Siṃha
        from dashas import vimshottari
        assert vimshottari(as_written).moon_nakshatra.name == "Bharani"

    def test_sani_mahadasa_claim_is_unreachable(self, aisha):
        # A Rohiṇī Moon is Moon-ruled, so the Vimśottarī sequence runs
        # Moon → Mars → Rāhu → Jupiter; Śani cannot be current in the 2020s
        # for ANY birth data giving Rohiṇī. The third stated value is not a
        # data-entry slip but an inconsistency.
        from dashas import vimshottari
        tl = vimshottari(aisha)
        assert [md.lord for md in tl.mahadashas[:4]] == [
            "Moon", "Mars", "Rahu", "Jupiter"]
        now = datetime(2026, 8, 22, tzinfo=timezone.utc)
        assert tl.at(now)[0].lord == "Rahu"


class TestGunaMilan:
    """Domain contract: KutaScore / GunaMilan (THREE · DOMAIN MODEL)."""

    def test_shape_matches_framework_contract(self, match):
        assert len(match.rows) == 8
        assert match.max == 36
        assert sum(r.max for r in match.rows) == 36
        assert match.total == sum(r.score for r in match.rows)
        assert 0 <= match.total <= 36
        assert match.verdict
        for r in match.rows:
            assert r.kuta and r.rule and r.detail
            assert 0 <= r.score <= r.max
            assert r.confidence in ("High", "Moderate", "Interpretive")
            # A withheld kūṭa must always carry its classical easing.
            assert (r.score > 0) or r.note

    def test_kuta_names_and_maxima(self, match):
        assert [(r.kuta, r.max) for r in match.rows] == [
            ("Varṇa", 1.0), ("Vaśya", 2.0), ("Tārā", 3.0), ("Yoni", 4.0),
            ("Graha Maitrī", 5.0), ("Gaṇa", 6.0), ("Bhakūṭa", 7.0),
            ("Nāḍī", 8.0)]

    def test_reference_pairing_scores(self, match):
        # Aisha (Rohiṇī p2, Taurus Moon) ✕ Dev (Ārdrā, Gemini Moon).
        by = {r.kuta: r.score for r in match.rows}
        assert by["Nāḍī"] == 8.0          # differing nāḍī — full marks
        assert by["Gaṇa"] == 6.0
        assert by["Graha Maitrī"] == 5.0
        assert by["Yoni"] == 2.0
        assert by["Tārā"] == 1.5          # one direction auspicious
        assert by["Vaśya"] == 1.0
        assert by["Varṇa"] == 0.0
        assert by["Bhakūṭa"] == 0.0       # Taurus→Gemini is the 2/12 axis
        assert match.total == 23.5
        assert match.voids == ("Varṇa", "Bhakūṭa")
        assert "workable agreement" in match.verdict

    def test_pairing_order_changes_the_reckoning(self, chart, partner):
        # The aṣṭakūṭa tables are asymmetric, so bride/groom order is part
        # of the computation. Reversed, Varṇa is no longer withheld and the
        # total moves — this is a real property of the method, not a bug,
        # and the app must never quietly normalise the order away.
        from gunamilan import guna_milan
        reverse = guna_milan("Dev", partner, "Aisha", chart)
        assert reverse.total == 24.5
        assert reverse.voids == ("Bhakūṭa",)
        assert {r.kuta: r.score for r in reverse.rows}["Varṇa"] == 1.0

    def test_nadi_and_bhakuta_rules(self):
        from gunamilan import _nadi, _bhakuta, partner_from_chart
        # Same nakṣatra → same nāḍī → withheld; and the 6/8 axis annuls.
        a = compute_chart(AISHA_BIRTH)
        pa = partner_from_chart("a", a)
        assert _nadi(pa, pa).score == 0.0
        assert _nadi(pa, pa).note and "Nāḍī withheld" in _nadi(pa, pa).note
        assert _bhakuta(pa, pa).score == 7.0        # same sign is permitted

    def test_gana_matrix_is_asymmetric(self):
        # The tables are order-sensitive: Manuṣya bride + Deva groom scores 5,
        # the reverse scores 6. Order is computation, not display.
        from gunamilan import GANA_MATRIX
        assert GANA_MATRIX[("Manuṣya", "Deva")] == 5.0
        assert GANA_MATRIX[("Deva", "Manuṣya")] == 6.0
        assert GANA_MATRIX[("Deva", "Rākṣasa")] == 0.0

    def test_yoni_sworn_enemies_only_zero(self):
        from gunamilan import YONI_SWORN_ENEMIES, YONI
        assert len(YONI_SWORN_ENEMIES) == 7
        assert len(YONI) == 27
        assert frozenset(("Cow", "Tiger")) in YONI_SWORN_ENEMIES

    def test_mangal_mutual_cancellation(self, match):
        assert match.mangal_cancelled is True
        assert "Maṅgala doṣa" in match.mangal_note

    def test_fraction_rendering(self):
        from gunamilan import fraction
        assert fraction(28.5) == "28½"       # framework's numeral rule
        assert fraction(25.0) == "25"
        assert fraction(1.5) == "1½"
        assert fraction(0.5) == "½"

    def test_deterministic(self, chart, partner):
        from gunamilan import guna_milan
        a = guna_milan("A", chart, "B", partner)
        b = guna_milan("A", chart, "B", partner)
        assert a.total == b.total
        assert [r.score for r in a.rows] == [r.score for r in b.rows]


class TestReadingEngine:
    """Milestone 06 — detect → rank → select → compose (framework FOUR)."""

    WHEN = datetime(2026, 8, 22, 6, tzinfo=timezone.utc)

    def _read(self, chart, timeline, when=None, key="ref"):
        from pancanga import pancanga_for
        from reading import read_day
        when = when or self.WHEN
        return read_day(chart, timeline, pancanga_for(GATE_BIRTH, when),
                        when, person_key=key)

    def test_condition_weights_match_the_framework_table(self):
        from reading import FRAGMENTS
        weights = {f.id: f.weight for f in FRAGMENTS}
        assert weights["dasa.turn"] == 100
        assert weights["sadhesati.phase"] == 90
        assert weights["station.direct"] == 80
        assert weights["station.retrograde"] == 80
        assert weights["ingress.slow"] == 70
        assert weights["transit.over_natal"] == 60
        assert weights["candra.favourable"] == 40
        assert weights["candra.testing"] == 40
        assert weights["tithi.purnima"] == 25
        assert weights["yoga.harsh"] == 25
        assert weights["weekday.agrees"] == 10

    def test_every_fragment_has_three_variants_per_slot(self):
        from reading import FRAGMENTS
        for f in FRAGMENTS:
            assert len(f.stem) == 3, f.id
            assert len(f.emphasis) == 3, f.id
            assert len(f.close) == 3, f.id
        # 3 slots × 3 variants = the framework's 27 phrasings per condition.
        assert 3 ** 3 == 27

    def test_rank_keeps_subject_and_qualifier_only(self):
        from reading.detect import Hit
        from reading.select import rank
        hits = [Hit("a", 40, "Moon", "f"), Hit("b", 100, "", "f"),
                Hit("c", 70, "Jupiter", "f")]
        subject, qualifier = rank(hits)
        assert subject.fragment_id == "b" and qualifier.fragment_id == "c"

    def test_ties_break_by_natural_graha_order(self):
        from reading.detect import Hit
        from reading.select import rank
        # Same weight: Mars precedes Saturn in the classical sequence.
        subject, _ = rank([Hit("s", 80, "Saturn", "f"),
                           Hit("m", 80, "Mars", "f")])
        assert subject.fragment_id == "m"

    def test_seeded_selection_is_stable_and_process_independent(self):
        from reading.select import pick_variant, seed_for
        variants = ("one", "two", "three")
        a = pick_variant(variants, "person", "2026-08-22", "frag", "stem")
        b = pick_variant(variants, "person", "2026-08-22", "frag", "stem")
        assert a == b
        # A different day, person or slot draws independently.
        assert seed_for("p", "2026-08-22", "f", "stem") != \
            seed_for("p", "2026-08-23", "f", "stem")
        assert seed_for("p", "2026-08-22", "f", "stem") != \
            seed_for("p", "2026-08-22", "f", "close")
        # Not Python's salted hash(): SHA-256 gives the same digest in
        # every process, so this constant pins the algorithm itself.
        assert seed_for("p", "2026-08-22", "f", "stem") % 1000 == 955

    def test_reading_is_deterministic(self, chart, timeline):
        a = self._read(chart, timeline)
        b = self._read(chart, timeline)
        assert (a.statement, a.long, a.subject_id) == \
            (b.statement, b.long, b.subject_id)

    def test_different_people_read_differently(self, chart, timeline):
        a = self._read(chart, timeline, key="one")
        b = self._read(chart, timeline, key="two")
        assert a.subject_id == b.subject_id      # same sky
        assert (a.statement, a.long) != (b.statement, b.long)

    def test_reading_carries_its_working(self, chart, timeline):
        r = self._read(chart, timeline)
        assert r.facts and all(f.strip().endswith(".") for f in r.facts)
        assert r.subject_id
        assert r.emphasis and r.emphasis in r.statement

    def test_voice_word_limits_hold_all_year(self, chart, timeline):
        """The framework fixes the counts; one sample day proves nothing."""
        for d in range(0, 365, 7):
            r = self._read(chart, timeline,
                           self.WHEN + timedelta(days=d))
            assert len(r.statement.split()) < 15, (d, r.statement)
            assert 25 <= r.word_count <= 40, (d, r.word_count, r.long)

    def test_voice_forbids_predictions_about_money_health_death(self):
        from reading import FRAGMENTS
        banned = re.compile(
            r"\b(money|wealth|rich|salary|income|profit|illness|disease|"
            r"cure|heal|die|death|lucky|blessed|destined|guaranteed)\b",
            re.IGNORECASE)
        for f in FRAGMENTS:
            for text in f.stem + f.emphasis + f.close:
                assert not banned.search(text), f"{f.id}: {text!r}"

    def test_pancanga_floor_always_yields(self, chart, timeline):
        from reading import FRAGMENTS
        floor = [f for f in FRAGMENTS if f.id == "pancanga.day"]
        assert len(floor) == 1 and floor[0].weight <= 25
        # Every sampled day produces a reading, fallback or not.
        for d in range(0, 60, 11):
            r = self._read(chart, timeline, self.WHEN + timedelta(days=d))
            assert r.statement and r.long

    def test_ui_renders_the_reading(self, page):
        assert 'class="statement"' in page
        assert "Read the full day" in page
        assert "Why this reading" in page


MATCH_FORM = {
    **GATE_FORM,
    "p_name": "Dev",
    "p_date": f"{PARTNER_BIRTH.year:04d}-{PARTNER_BIRTH.month:02d}-"
              f"{PARTNER_BIRTH.day:02d}",
    "p_time": f"{PARTNER_BIRTH.hour:02d}:{PARTNER_BIRTH.minute:02d}",
    "p_lat": str(PARTNER_BIRTH.latitude),
    "p_lon": str(PARTNER_BIRTH.longitude),
    "p_tz": PARTNER_BIRTH.tz, "p_place": "Pune, Maharashtra, India",
}


@pytest.fixture(scope="module")
def match_page(client):
    resp = client.post("/", data=MATCH_FORM)
    assert resp.status_code == 200
    return resp.get_data(as_text=True)


class TestMatchUI:
    def test_match_section_renders(self, match_page):
        assert 'id="match"' in match_page
        assert 'href="#match"' in match_page          # nav link appears
        assert "Guṇa Milan · aṣṭakūṭa" in match_page
        for kuta in ("Varṇa", "Vaśya", "Tārā", "Yoni", "Graha Maitrī",
                     "Gaṇa", "Bhakūṭa", "Nāḍī"):
            assert kuta in match_page, kuta
        assert "Maṅgala doṣa" in match_page

    def test_score_uses_vulgar_fraction(self, match_page):
        # Aisha ✕ Dev in this order scores 23½ — the tables are asymmetric,
        # so the reversed order (24½) is a different reckoning.
        assert "23½" in match_page
        assert "/36" in match_page

    def test_withheld_kuta_carries_its_easing(self, match_page):
        assert "Bhakūṭa withheld" in match_page
        assert "Varṇa withheld" in match_page
        assert "gmrow void" in match_page

    def test_glance_third_chip_becomes_match(self, match_page):
        assert ">Match</button>" in match_page
        assert ">Daśā</button>" not in match_page

    def test_no_partner_leaves_dasha_chip(self, page):
        assert ">Daśā</button>" in page
        assert 'id="match"' not in page

    def test_partner_place_without_coords_is_refused(self, client):
        resp = client.post("/", data={**MATCH_FORM, "p_tz": "", "p_lat": ""})
        assert resp.status_code == 400
        # the apostrophe renders escaped, so match either side of it
        html = resp.get_data(as_text=True)
        assert "place is incomplete" in html
        assert "clear the partner block" in html


@pytest.fixture(scope="module")
def ask_ctx(chart, timeline):
    from ask import ChartContext
    return ChartContext(chart, timeline,
                        datetime(2026, 7, 16, tzinfo=timezone.utc))


class TestAskYourChart:
    def test_registry_structure(self):
        from ask import REGISTRY
        assert set(REGISTRY) == {
            "spouse-profession", "career-field", "wealth-timing",
            "marriage-timing", "current-dasha"}
        for q in REGISTRY.values():
            assert q.text and q.category and q.techniques and q.answer_frame
            assert len(q.lenses) >= 2
            for lens in q.lenses:
                assert lens.rule and 0 < lens.weight <= 1
                assert lens.confidence in ("High", "Moderate", "Interpretive")
            assert abs(sum(l.weight for l in q.lenses) - 1.0) < 1e-9

    def test_verdict_carries_all_five_outputs(self, ask_ctx):
        from ask import ask
        v = ask("career-field", ask_ctx)
        assert v.answer                                   # (1) plain answer
        assert all(f.placements for f in v.findings)      # (2) placements
        assert all(f.rule for f in v.findings)            # (3) rules
        assert 0 <= v.convergence <= 1 and v.agreement    # (4) convergence
        assert v.confidence in ("High", "Moderate", "Interpretive")  # (5)

    def test_career_field_lens_split(self, ask_ctx):
        from ask import ask
        v = ask("career-field", ask_ctx)
        # 10th lord Venus (Cancer) and the Scorpio D10 lagna (Mars) agree on
        # a craft/design-and-engineering reading; the 10th occupant, the
        # Moon, testifies to public and caring work instead.
        assert v.convergence == 0.7
        assert v.agreement == "partial convergence"
        assert "design" in v.modal_indications
        assert v.disagreement is not None
        assert "10th occupants" in v.disagreement
        values = " | ".join(p.value for f in v.findings for p in f.placements)
        assert "Moon in Taurus (10th house), moolatrikona" in values

    def test_spouse_profession_disagreement_displayed(self, ask_ctx):
        from ask import ask
        v = ask("spouse-profession", ask_ctx)
        # 7th lord Saturn and the D9 7th (also Saturn) agree; Venus karaka
        # in Cancer testifies to something else entirely. Core principle:
        # the split is shown, never resolved.
        assert v.disagreement is not None
        assert "unresolved" in v.disagreement
        assert "Venus karaka" in v.disagreement
        assert "not averaged away" in v.answer
        # Two of three lenses agreeing is not unanimity, and the tag must
        # not claim more confidence than the split supports.
        assert v.convergence == 0.75
        assert v.confidence == "Interpretive"

    def test_disagreement_is_never_averaged_into_one_answer(self, ask_ctx):
        # The product principle, asserted across the whole registry rather
        # than one question: whenever lenses diverge, BOTH readings survive
        # into the output. A verdict that reported only the majority would
        # pass every other test in this class.
        from ask import ask_all
        for v in ask_all(ask_ctx):
            if v.convergence < 1.0:
                assert v.disagreement, v.answer
                assert "not averaged away" in v.answer
                # the dissenting lens is named, not summarised away
                assert any(f.lens in v.disagreement for f in v.findings)
            else:
                assert v.disagreement is None

    def test_wealth_timing_dated_windows(self, ask_ctx):
        from ask import ask
        v = ask("wealth-timing", ask_ctx)
        stmts = " | ".join(f.statement for f in v.findings)
        # The running Rahu–Sun period (1st lord) must appear dated, and
        # transit Jupiter's wealth-house touches likewise.
        assert "Rahu–Sun" in stmts and "Feb 2027" in stmts
        assert "Jupiter" in stmts and "Dec 2028" in stmts
        assert any("running" in p.label
                   for f in v.findings for p in f.placements)
        # Both lenses land on 2027–2029 — the one question in the registry
        # this chart answers unanimously.
        assert v.convergence == 1.0
        assert v.modal_indications == ("2027", "2028", "2029")

    def test_marriage_timing_lens_overlap(self, ask_ctx):
        from ask import ask
        v = ask("marriage-timing", ask_ctx)
        stmts = " | ".join(f.statement for f in v.findings)
        assert "Jupiter–Saturn" in stmts         # 7th lord Saturn's period
        assert "Leo" in stmts                    # Jupiter aspecting Aquarius
        assert "2027" in stmts
        assert v.convergence >= 0.5

    def test_current_dasha_node_rules_no_house(self, ask_ctx):
        from ask import ask
        v = ask("current-dasha", ask_ctx)
        stmts = " | ".join(f.statement for f in v.findings)
        values = " | ".join(p.value for f in v.findings for p in f.placements)
        # Rahu rules no sign, so the mahadasha lens must say so rather than
        # leave a gap where the lordships would go.
        assert "Rahu rules no house — a shadow graha borrows from its "\
               "dispositor" in stmts
        assert "natural neutral" in values
        assert "Rahu in Leo (1st house)" in values
        # AD lens diverges (Sun themes) — displayed explicitly.
        assert v.disagreement is not None and "Antardasha" in v.disagreement

    def test_answers_deterministic_no_free_text(self, ask_ctx):
        from ask import ask_all
        a = [(v.answer, v.convergence, v.confidence) for v in ask_all(ask_ctx)]
        b = [(v.answer, v.convergence, v.confidence) for v in ask_all(ask_ctx)]
        assert a == b  # pure function of chart + registry — no generation

    def test_ui_renders_ask_section(self, page):
        assert "Ask your chart" in page
        assert page.count('class="yoga askcard"') == 5
        assert 'class="convpill' in page
        assert "partial convergence" in page      # split verdict visible
        assert "shown side by side" in page.lower() or "unresolved" in page
        assert "not averaged away" in page

    def test_lenses_disagree_label_exists_for_low_convergence(self):
        # The reference chart never drops far enough for the third label,
        # so the threshold itself is asserted directly — otherwise the
        # branch could rot unnoticed behind a chart that never reaches it.
        from ask import _agreement_label
        assert _agreement_label(0.9) == "strong convergence"
        assert _agreement_label(0.6) == "partial convergence"
        assert _agreement_label(0.3) == "lenses disagree"

# --- v1.1: 'Ask about this chart' grounded agent ------------------------------

AGENT_WHEN = datetime(2026, 9, 3, tzinfo=timezone.utc)


class FakeMessages:
    """Stands in for `client.messages`, returning canned JSON.

    The agent's guarantee is enforced by `validate_payload`, which is pure.
    Driving it through a fake transport exercises the real assembly, parsing
    and validation path without an API key, a network call, or a dependence
    on how the model happens to behave the day CI runs — and lets the suite
    assert the ADVERSARIAL cases, which a live model would rarely produce
    on demand.
    """

    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        payload = self.replies.pop(0)

        class _Block:
            type = "text"
            text = json.dumps(payload)

        class _Response:
            stop_reason = "end_turn"
            content = [_Block()]

        return _Response()


class FakeClient:
    def __init__(self, replies):
        self.messages = FakeMessages(replies)


def _reply(answer, *, statements=None, facts=(), rules=(),
           confidence="Interpretive", refused=False, reason=""):
    return {
        "answer": answer,
        "answer_statements": statements if statements is not None else [
            {"text": answer, "label": "COMPUTED",
             "fact_ids": list(facts), "rule": ""}],
        "facts_used": list(facts),
        "rules_applied": list(rules),
        "confidence": confidence,
        "refused": refused,
        "refusal_reason": reason,
    }


@pytest.fixture(scope="module")
def agent_facts(chart):
    from chartfacts import build_facts
    return {f.id: f for f in build_facts(chart, AGENT_WHEN)}


class TestChartFactLedger:
    def test_every_fact_has_a_unique_stable_id(self, agent_facts):
        from chartfacts import build_facts
        assert len(agent_facts) >= 40
        ids = [f.id for f in build_facts(GATE_BIRTH and compute_chart(
            GATE_BIRTH), AGENT_WHEN)]
        assert len(ids) == len(set(ids)), "duplicate fact ids"
        # IDs are the citation vocabulary — they must be addressable, not
        # positional, so a stored answer survives a re-computation.
        assert "lagna" in agent_facts
        for planet in ("sun", "moon", "mars", "saturn", "rahu", "ketu"):
            assert f"planet.{planet}" in agent_facts
        for house in range(1, 13):
            assert f"house.{house}" in agent_facts

    def test_all_nine_transits_are_in_the_ledger(self, chart, agent_facts):
        """A forecast answer is mostly transits. A position the agent does
        not have is one it omits or invents — and the validator can only
        check a transit claim against a transit fact."""
        from transits import transit_snapshot
        snap = transit_snapshot(chart, AGENT_WHEN)
        for planet in ("Sun", "Moon", "Mars", "Mercury", "Jupiter",
                       "Venus", "Saturn", "Rahu", "Ketu"):
            fact = agent_facts[f"transit.{planet.lower()}"]
            assert fact.value["sign"] == snap.planets[planet].sign
            assert fact.value["natal_house"] == snap.planets[planet].natal_house
            # The statement must mark itself as a transit, so the model
            # cannot mistake it for a birth placement.
            assert "TRANSIT" in fact.statement

    def test_ledger_matches_the_chart_it_came_from(self, chart, agent_facts):
        moon = agent_facts["planet.moon"].value
        assert moon["sign"] == chart.planets["Moon"].sign
        assert moon["house"] == chart.planets["Moon"].house
        assert agent_facts["lagna"].value["sign"] == chart.lagna.sign
        for house in range(1, 13):
            assert (agent_facts[f"house.{house}"].value["sign"]
                    == chart.house_signs[house])

    def test_payload_is_deterministic_so_the_prefix_caches(self, chart):
        from chartfacts import facts_payload
        a = json.dumps(facts_payload(chart, AGENT_WHEN), sort_keys=True)
        b = json.dumps(facts_payload(chart, AGENT_WHEN), sort_keys=True)
        assert a == b


class TestGroundedAgent:
    """The constraint, asserted: answers come only from the ledger."""

    # Five questions, each paired with a plausible-sounding answer that
    # asserts a placement THIS CHART DOES NOT HAVE. Every one must be
    # caught — a fluent sentence about the wrong Mars is the exact failure
    # this feature must not ship.
    INVENTED = [
        ("What does my Mars do?",
         "Mars is in Leo in the 1st house, which sharpens the personality."),
        ("Tell me about my career.",
         "With a Sagittarius lagna, the 10th house falls in Virgo."),
        ("Where is my Moon?",
         "The Moon stands in Gemini, giving a restless mind."),
        ("Is Saturn difficult for me?",
         "Saturn occupies the 4th house, pressing on home life."),
        ("What about Jupiter?",
         "Jupiter is in Sagittarius, its own sign, in the 5th house."),
    ]

    @pytest.mark.parametrize("question,answer", INVENTED)
    def test_invented_placements_are_always_caught(
            self, chart, question, answer):
        from agent import ask_chart
        client = FakeClient([_reply(answer, facts=["planet.mars"])])
        result = ask_chart(chart, AGENT_WHEN, question, client=client,
                           model="test-model")
        assert not result.ok, (
            f"invented placement passed validation: {answer!r}")
        assert any(v.kind in ("wrong-natal-sign", "wrong-natal-house",
                              "wrong-lagna")
                   for v in result.violations), result.violations

    def test_no_placement_in_an_accepted_answer_is_absent_from_the_ledger(
            self, chart, agent_facts):
        """The positive half: a true answer passes, and everything it
        asserts is present in the ledger."""
        from agent import ask_chart
        moon = chart.planets["Moon"]
        truthful = (
            f"The Moon is in {moon.sign} in the "
            f"{moon.house}th house, and the lagna is {chart.lagna.sign}.")
        client = FakeClient([_reply(truthful,
                                    facts=["planet.moon", "lagna"])])
        result = ask_chart(chart, AGENT_WHEN, "Where is my Moon?",
                           client=client, model="test-model")
        assert result.ok, result.violations
        for fid in result.facts_used:
            assert fid in agent_facts

    def test_transit_statements_pass_validation(self, chart):
        """Regression from the live deploy: 'how does the rest of 2026 look
        professionally?' was withheld.

        The failing claim was `wrong-sign: Jupiter is in Pisces, not Cancer`
        — natal Jupiter IS in Pisces and transiting Jupiter IS in Cancer,
        so the reply was right and the validator was wrong. It read a
        transit sentence as a natal placement.

        The irony is the point: a forward-looking answer must talk about
        transits, so the check fired hardest on correct answers to exactly
        the questions the feature exists for.
        """
        from agent import ask_chart
        from transits import transit_snapshot
        snap = transit_snapshot(chart, AGENT_WHEN)
        tj, ts = snap.planets["Jupiter"], snap.planets["Saturn"]
        # The two frames genuinely disagree — otherwise this proves nothing.
        assert tj.sign != chart.planets["Jupiter"].sign
        assert ts.sign != chart.planets["Saturn"].sign

        answer = (
            f"Transiting Jupiter is in {tj.sign} until October 2026, "
            f"crossing your {tj.natal_house}th house, while transiting "
            f"Saturn is in {ts.sign}. Your natal Jupiter is in "
            f"{chart.planets['Jupiter'].sign}.")
        client = FakeClient([_reply(answer, facts=[
            "transit.jupiter", "transit.saturn", "planet.jupiter"])])
        result = ask_chart(chart, AGENT_WHEN, "What do the transits touch?",
                           client=client, model="test-model")
        assert result.ok, result.violations

    def test_transit_claims_are_still_checked_against_the_real_sky(
            self, chart):
        """Relaxing natal-vs-transit must not create a loophole: saying
        'transiting' cannot make an invented position acceptable."""
        from agent import ask_chart
        client = FakeClient([_reply(
            "Transiting Saturn is in Capricorn right now, and transiting "
            "Jupiter is moving through your 3rd house.",
            facts=["transit.saturn", "transit.jupiter"])])
        result = ask_chart(chart, AGENT_WHEN, "Where are the slow movers?",
                           client=client, model="test-model")
        assert not result.ok
        kinds = {v.kind for v in result.violations}
        assert "wrong-transit-sign" in kinds
        assert "wrong-transit-house" in kinds

    def test_a_bare_planet_claim_is_still_read_as_natal(self, chart):
        """The default stays strict: with no 'transiting' anywhere, the
        claim is about the birth chart."""
        from agent import ask_chart
        from transits import transit_snapshot
        moving = transit_snapshot(chart, AGENT_WHEN).planets["Jupiter"].sign
        client = FakeClient([_reply(f"Jupiter is in {moving}.",
                                    facts=["planet.jupiter"])])
        result = ask_chart(chart, AGENT_WHEN, "Where is Jupiter?",
                           client=client, model="test-model")
        assert not result.ok
        assert any(v.kind == "wrong-natal-sign" for v in result.violations)

    def test_forecast_question_gets_the_redirect_refusal(self, chart):
        """A broad forecast must refuse AND hand back the dated facts.

        The ledger holds no outcomes, only dated windows. A refusal that
        gives those windows is a useful answer; a hedged forecast is not.
        """
        from agent import ask_chart
        from chartfacts import build_facts
        facts = {f.id: f for f in build_facts(chart, AGENT_WHEN)}
        dasha = facts["dasha.current"].value
        tj = facts["transit.jupiter"].value
        redirect = (
            "This chart does not forecast how a stretch of time will go. "
            f"What it does say for the rest of 2026: the {dasha['mahadasha']} "
            f"mahadasha with the {dasha['antardasha']} antardasha is running, "
            f"and transiting Jupiter is in {tj['sign']} until {tj['until']}, "
            f"crossing your {tj['natal_house']}th house. Ask instead which "
            "house a particular graha is transiting.")
        client = FakeClient([_reply(
            redirect,
            statements=[{"text": redirect, "label": "COMPUTED",
                         "fact_ids": ["dasha.current", "transit.jupiter"],
                         "rule": ""}],
            facts=["dasha.current", "transit.jupiter"],
            refused=True,
            reason="The chart carries dated windows, not outcomes.")])
        result = ask_chart(
            chart, AGENT_WHEN,
            "How does the rest of 2026 look professionally?",
            client=client, model="test-model")
        assert result.refused is True
        assert result.ok, result.violations      # the redirect must survive
        assert result.answer, "a redirect must carry the facts, not be empty"
        assert "dasha.current" in result.facts_used

    def test_prompt_routes_forecasts_and_separates_the_two_skies(self):
        from agent import SYSTEM_PROMPT
        # Forecast routing, so the model redirects rather than attempting.
        assert "BROAD FORECASTS" in SYSTEM_PROMPT
        assert "does not forecast" in SYSTEM_PROMPT or \
               "no outcomes" in SYSTEM_PROMPT
        assert "narrower question" in SYSTEM_PROMPT
        # And the instruction that prevents the false positive at source.
        assert "NATAL AND TRANSIT ARE DIFFERENT FACTS" in SYSTEM_PROMPT
        assert "never a bare" in SYSTEM_PROMPT

    def test_withheld_message_says_why_and_suggests_a_narrower_question(self):
        from agent import Violation, explain_violations
        why, hint = explain_violations(
            [Violation("wrong-natal-sign", "Mars is in Leo", "not Leo")])
        assert "placement claim" in why and "computed chart" in why
        assert "narrower" in hint
        why, _ = explain_violations(
            [Violation("wrong-transit-sign", "x", "not Capricorn")])
        assert "transit" in why and "today" in why
        why, _ = explain_violations(
            [Violation("unknown-fact-id", "planet.pluto", "not in ledger")])
        assert "ledger" in why

    def test_citing_a_fact_that_does_not_exist_is_a_violation(self, chart):
        from agent import ask_chart
        client = FakeClient([_reply(
            "Your chart is balanced.",
            facts=["planet.moon", "planet.pluto", "house.13"])])
        result = ask_chart(chart, AGENT_WHEN, "How am I?", client=client,
                           model="test-model")
        assert not result.ok
        bad = {v.claim for v in result.violations
               if v.kind == "unknown-fact-id"}
        assert bad == {"planet.pluto", "house.13"}

    def test_out_of_scope_question_is_refused_not_answered(self, chart):
        from agent import ask_chart
        client = FakeClient([_reply(
            "", statements=[], refused=True,
            reason=("Your partner's birth details are not in this chart's "
                    "fact ledger, so their placements are not derivable "
                    "from it."))])
        result = ask_chart(
            chart, AGENT_WHEN,
            "What is my future husband's mother's profession?",
            client=client, model="test-model")
        assert result.refused is True
        assert result.ok, "a refusal must not itself be a violation"
        assert "not derivable" in result.refusal_reason

    def test_interpretive_statements_must_name_their_rule(self, chart):
        from agent import ask_chart
        client = FakeClient([_reply(
            "This is a chart of steady work.",
            statements=[{"text": "This is a chart of steady work.",
                         "label": "INTERPRETIVE", "fact_ids": ["planet.moon"],
                         "rule": ""}])])
        result = ask_chart(chart, AGENT_WHEN, "Summarise me?", client=client,
                           model="test-model")
        assert not result.ok
        assert any(v.kind == "uncited-interpretation"
                   for v in result.violations)

    def test_computed_statements_must_cite_a_fact(self, chart):
        from agent import ask_chart
        client = FakeClient([_reply(
            "The chart is Leo rising.",
            statements=[{"text": "The chart is Leo rising.",
                         "label": "COMPUTED", "fact_ids": [], "rule": ""}])])
        result = ask_chart(chart, AGENT_WHEN, "What is my lagna?",
                           client=client, model="test-model")
        assert not result.ok
        assert any(v.kind == "uncited-computed" for v in result.violations)

    def test_the_ledger_is_the_whole_context_sent(self, chart):
        """The model must not be handed anything it could compute from."""
        from agent import ask_chart
        client = FakeClient([_reply("Fine.", facts=[])])
        ask_chart(chart, AGENT_WHEN, "Anything?", client=client,
                  model="test-model")
        sent = client.messages.calls[0]
        body = sent["messages"][0]["content"]
        # Facts, yes. The BIRTH RECORD — from which a chart could be
        # recomputed, and which is the one thing that must never leave the
        # server — no.
        assert '"facts"' in body
        assert str(GATE_BIRTH.latitude) not in body
        assert str(GATE_BIRTH.longitude) not in body
        assert GATE_BIRTH.tz not in body
        assert f"{GATE_BIRTH.hour:02d}:{GATE_BIRTH.minute:02d}" not in body
        assert "julian" not in body.lower()
        # The system prompt carries the constraint verbatim.
        system = sent["system"][0]["text"]
        assert "ONLY the fact ledger" in system
        assert "COMPUTED" in system and "INTERPRETIVE" in system
        assert "medical, legal, financial" in system
        assert "refusal is a correct answer" in system
        # Structured output is enforced by schema, not by asking nicely.
        schema = sent["output_config"]["format"]["schema"]
        assert schema["required"] == [
            "answer", "answer_statements", "facts_used", "rules_applied",
            "confidence", "refused", "refusal_reason"]
        assert schema["additionalProperties"] is False

    def test_question_length_is_bounded(self, chart):
        from agent import ask_chart
        with pytest.raises(ValueError):
            ask_chart(chart, AGENT_WHEN, "x" * 401, client=FakeClient([]))
        with pytest.raises(ValueError):
            ask_chart(chart, AGENT_WHEN, "   ", client=FakeClient([]))

    def test_missing_api_key_is_a_clear_message_not_a_crash(self, chart,
                                                            monkeypatch):
        from agent import AgentUnavailable, ask_chart
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        with pytest.raises(AgentUnavailable) as exc:
            ask_chart(chart, AGENT_WHEN, "Where is my Moon?")
        assert "ANTHROPIC_API_KEY" in str(exc.value)


class TestAgentLimitsAndLog:
    def test_session_cap_is_ten_questions(self):
        from agent import MAX_QUESTIONS_PER_SESSION, RateLimiter
        assert MAX_QUESTIONS_PER_SESSION == 10
        limiter = RateLimiter()
        for i in range(10):
            allowed, _, remaining = limiter.check("1.2.3.4", "sess")
            assert allowed, f"blocked at question {i + 1}"
            assert remaining == 10 - i
            limiter.record("1.2.3.4", "sess")
        allowed, reason, remaining = limiter.check("1.2.3.4", "sess")
        assert not allowed and remaining == 0
        assert "10-question limit" in reason
        # A different session is unaffected — the cap is per session.
        assert limiter.check("1.2.3.4", "other")[0] is True

    def test_ip_window_limits_independently_of_session(self):
        from agent import RateLimiter
        limiter = RateLimiter(window=3600, per_window=3, per_session=100)
        for i in range(3):
            assert limiter.check("9.9.9.9", f"s{i}")[0] is True
            limiter.record("9.9.9.9", f"s{i}")
        allowed, reason, _ = limiter.check("9.9.9.9", "fresh-session")
        assert not allowed and "this address" in reason
        # Another IP is unaffected…
        assert limiter.check("8.8.8.8", "fresh-session")[0] is True

    def test_ip_window_expires(self):
        from agent import RateLimiter
        limiter = RateLimiter(window=60, per_window=1, per_session=100)
        limiter.record("7.7.7.7", "s", now=1000.0)
        assert limiter.check("7.7.7.7", "s2", now=1030.0)[0] is False
        assert limiter.check("7.7.7.7", "s2", now=1100.0)[0] is True

    def test_corrections_log_appends_and_never_holds_birth_data(self, tmp_path):
        from agent import log_correction
        log = tmp_path / "corrections.jsonl"
        log_correction("Q1?", "A1.", reason="thumbs-down",
                       facts_used=["planet.moon"], model="m", path=log)
        log_correction("Q2?", "A2.", reason="thumbs-down", path=log)
        lines = log.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 2                       # append-only
        first = json.loads(lines[0])
        assert first["question"] == "Q1?" and first["answer"] == "A1."
        assert first["reason"] == "thumbs-down"
        assert first["at"].endswith("+00:00")
        # The log records the exchange, never the birth record.
        blob = log.read_text(encoding="utf-8")
        for leaked in (str(GATE_BIRTH.latitude), str(GATE_BIRTH.longitude),
                       GATE_BIRTH.place, str(GATE_BIRTH.year)):
            assert leaked not in blob


class TestAgentEndpoint:
    def _body(self, **over):
        body = {"sid": "test-session", "question": "Where is my Moon?",
                **{k: v for k, v in GATE_FORM.items()}}
        body.update(over)
        return body

    def test_ask_requires_a_session_id(self, client):
        r = client.post("/ask", json=self._body(sid=""))
        assert r.status_code == 400
        assert "session id" in r.get_json()["error"]

    def test_ask_reports_unconfigured_rather_than_500(self, client,
                                                      monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        r = client.post("/ask", json=self._body(sid="unconfigured-session"))
        assert r.status_code == 503
        assert "ANTHROPIC_API_KEY" in r.get_json()["error"]

    def test_ask_rejects_incomplete_birth_details(self, client):
        r = client.post("/ask", json=self._body(sid="bad-birth", tz=""))
        assert r.status_code == 400
        assert "timezone" in r.get_json()["error"]

    def test_feedback_appends_to_the_log(self, client, tmp_path,
                                         monkeypatch):
        import agent as agent_mod
        log = tmp_path / "c.jsonl"
        monkeypatch.setattr(agent_mod, "CORRECTIONS_LOG", log)
        r = client.post("/ask/feedback",
                        json={"question": "Q?", "answer": "A.",
                              "facts_used": ["planet.moon"]})
        assert r.status_code == 200 and r.get_json()["ok"] is True
        entry = json.loads(log.read_text(encoding="utf-8").strip())
        assert entry["reason"] == "thumbs-down"
        assert entry["facts_used"] == ["planet.moon"]
        # Empty feedback is refused rather than logged as noise.
        assert client.post("/ask/feedback", json={}).status_code == 400

    def test_ground_colour_is_never_used_as_text_colour(self):
        """Regression: `--ink` is the GROUND, `--cream` is the text.

        The agent panel first shipped with `color: var(--ink)` on its
        suggestion buttons, which painted the text the same colour as the
        page behind it — the buttons rendered as three empty boxes. The
        markup was correct and the DOM had the text, so nothing but looking
        at the render caught it.

        Inverted elements (a light `--accent-300` background with dark text)
        are the legitimate use, so the rule is not "never" — it is "never
        without a background in the same block".
        """
        css = (HERE / "static/style.css").read_text(encoding="utf-8")
        offenders = []
        for block in re.finditer(r"\{([^{}]*)\}", css):
            body = block.group(1)
            if re.search(r"color:\s*var\(--ink\)", body) and \
                    not re.search(r"background(-color)?:", body):
                offenders.append(" ".join(body.split())[:70])
        assert offenders == [], (
            "text painted with the ground colour: " + "; ".join(offenders))

    def test_panel_hides_controls_when_unconfigured(self, page):
        """Graceful degradation: the section explains itself and the rest of
        the dashboard is unaffected."""
        assert 'id="agent"' in page
        assert 'href="#agent"' in page
        assert "ANTHROPIC_API_KEY" in page and "not configured" in page
        assert 'id="agentq"' not in page          # no dead input offered

    def test_panel_renders_with_suggestions_and_disclosure(
            self, client, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-not-a-real-key")
        page = client.post("/", data=GATE_FORM).get_data(as_text=True)
        assert 'id="agent"' in page
        assert 'href="#agent"' in page
        assert page.count('class="sugq"') == 3      # three suggested questions
        assert "Facts used" in page                  # the Why? pattern
        assert "thumbdown" in page
        assert 'id="agentq"' in page
        assert "COMPUTED" in page and "INTERPRETIVE" in page
        # The key is set on the server for this render and must not appear
        # anywhere in what the browser receives.
        assert "sk-ant" not in page
        assert "not-a-real-key" not in page
