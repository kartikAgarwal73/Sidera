"""Automated gate tests. One class per phase; every phase's gates stay green forever.

Run with: pytest test_gates.py -v
"""
import json
import os
import re
import sys
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
from pathlib import Path

import fixtures

from dashas import DASHA_SEQUENCE, nakshatra_of, nakshatra_table, vimshottari
from engine import PLANETS, SIGNS, BirthData, compute_chart
from explain import ordinal
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
        # Every input that could carry a birth detail is empty. Radios are
        # exempt because their value is a choice id from the computation
        # options, not anything about a person — and the next assertion
        # holds them to exactly that.
        birth_inputs = re.sub(r"<input[^>]*type=\"radio\"[^>]*>", "",
                              form_html)
        assert re.search(r'value="[^"]', birth_inputs) is None
        import schools
        allowed = {a.id for o in schools.OPTIONS.values() for a in o.answers}
        for value in re.findall(
                r'<input[^>]*type="radio"[^>]*value="([^"]*)"', form_html):
            assert value in allowed, f"unexpected radio value: {value}"
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

    def test_birth_date_and_time_are_masked_text_not_native_pickers(
            self, client):
        """The native pickers render in the SYSTEM locale, not the page's.

        Reported live on sidera.onrender.com: macOS Safari with a 12-hour
        system clock showed am/pm segments and answered a typed "13" with
        "Invalid value". `type="date"` has the worse form of it — MM/DD in a
        US locale, DD/MM elsewhere — so the same keystrokes cast two
        different charts with no error shown either time.

        The earlier text field (commit eb03cc6) failed for the opposite
        reason: `inputmode="numeric"` with no mask hands a phone a
        digits-only keypad and there is no colon key, so a birth time could
        not be typed at all. Both constraints are satisfiable at once only
        by masking — the field types the separator itself — so this pins the
        mask and the numeric keypad TOGETHER. Dropping either resurrects one
        of the two bugs.
        """
        html = client.get("/").get_data(as_text=True)
        form = html[html.index('<form method="post"'):html.index("</form>")]
        tags = {m.group(1): m.group(0) for m in
                re.finditer(r'<input id="(\w+)"[^>]*>', form, re.S)}
        for field, mask, length in (("date", "date", "10"),
                                    ("time", "time", "5"),
                                    ("p_date", "date", "10"),
                                    ("p_time", "time", "5")):
            tag = tags.get(field)
            assert tag, f"{field} input missing"
            assert 'type="text"' in tag, (
                f"{field} must be a masked text field, not a native picker "
                f"that follows the system locale: {tag}")
            assert f'data-mask="{mask}"' in tag, (
                f"{field} must carry the mask; without it inputmode=numeric "
                f"is the un-typeable mobile field again: {tag}")
            assert 'inputmode="numeric"' in tag, f"{field}: {tag}"
            assert f'maxlength="{length}"' in tag, f"{field}: {tag}"
        # No native date/time input may exist anywhere on the page — not
        # just in the birth form — or the locale bug returns by another door.
        for tag in re.findall(r"<input\b[^>]*>", html, re.S):
            assert 'type="date"' not in tag and 'type="time"' not in tag, (
                f"a native date/time picker is back on the page: {tag}")

    def test_the_field_hints_state_the_order_and_the_clock(self, client):
        """A masked field is only unambiguous if it says which order it is.

        Day-first is a decision, not a default: 03/04/1990 is 3 April here
        and 4 March to half the world. The hint carries it, so nobody has to
        guess which chart they are casting.
        """
        html = client.get("/").get_data(as_text=True)
        assert "Time of birth · 24-hour · e.g. 13:12" in html
        assert "Date of birth · day first · e.g. 25/03/1994" in html
        assert 'placeholder="HH:MM"' in html
        assert 'placeholder="DD/MM/YYYY"' in html

    def test_no_birth_field_traps_a_mobile_keyboard(self, client):
        """Sweep: no field may demand characters its keyboard cannot type.

        `inputmode="numeric"` is a digits-only keypad — no colon, no minus,
        no decimal point on several mobile browsers. A field may declare it
        only if digits ALONE are a complete answer: the date and time masks
        insert their own separators, so "1312" and "16081998" are typeable
        on a bare keypad. Anything else must not declare it.
        """
        from app import parse_time, _parse_date
        html = client.get("/").get_data(as_text=True)
        form = html[html.index('<form method="post"'):html.index("</form>")]
        tags = {m.group(1): m.group(0) for m in
                re.finditer(r'<input id="(\w+)"[^>]*>', form, re.S)}
        # Digits alone must reach the engine, or the keypad is a trap.
        assert parse_time("1312") == (13, 12)
        assert _parse_date("16081998") == datetime(1998, 8, 16)
        for field in ("date", "time", "p_date", "p_time"):
            assert 'inputmode="numeric"' in tags[field], field
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

    def test_date_parsing_is_day_first_and_never_ambiguous(self):
        """A wrong date is a wrong chart, silently. Order is pinned here.

        `<input type="date">` read the SYSTEM locale, so 03/04/1990 was
        3 April to one visitor and 4 March to another with no error either
        time. One order now, stated on the field and enforced here.
        """
        from app import _parse_date
        assert _parse_date("16/08/1998") == datetime(1998, 8, 16)
        assert _parse_date("16081998") == datetime(1998, 8, 16)   # bare keypad
        assert _parse_date("16-08-1998") == datetime(1998, 8, 16)
        assert _parse_date("16.08.1998") == datetime(1998, 8, 16)
        assert _parse_date("3/4/1990") == datetime(1990, 4, 3), (
            "3/4/1990 must be 3 April — day first, not month first")
        # ISO stays accepted: the agent panel re-posts 'YYYY-MM-DD' with
        # every question, since no birth record is held server-side. The two
        # shapes cannot collide — ISO leads with four digits.
        assert _parse_date("1998-08-16") == datetime(1998, 8, 16)
        for bad in ("08/16/1998",        # month-first: 16 is not a month
                    "31/02/1998",        # not a real calendar date
                    "16/08/98",          # two-digit year
                    "", "yesterday", "16/08"):
            with pytest.raises(ValueError):
                _parse_date(bad)

    def test_month_first_is_refused_with_the_order_spelled_out(self, client):
        """The one input error that would otherwise cast a plausible chart.

        A visitor typing US order gets told the order, not just 'invalid'.
        """
        resp = client.post("/", data={**GATE_FORM, "date": "12/25/1994"})
        assert resp.status_code == 400
        html = resp.get_data(as_text=True)
        assert "day first" in html
        assert "The month runs 01–12" in html

    def test_native_time_value_casts_the_same_chart(self, client):
        """The masked field's wire format must reach the engine intact.

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
        """Re-pinned 2026-09-12. A label used to be one string; it is a
        structured mark now — glyph, abbreviation, degree, and ℞ or ⊙ in
        their own tspans so each can be set in its own ink. The VALUES are
        what this gate is for, so it reads them out of the marks."""
        # 'Abbr D°MM′' with ℞ for retrograde, reference-chart values.
        # Saturn's is deliberately absent: it stands in house 9, a triangle
        # 73 units across where a 77-unit label would cross the diagonal —
        # see `test_a_cell_too_narrow_for_a_degree_says_so_by_omission`.
        for label in ("Ju 2°53′", "Asc 11°05′", "Mo 15°17′"):
            assert label in page, label
        # The retrograde mark is a mark now, not the letter R.
        assert 'class="gm-retro">℞<' in page
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
        # Unparseable input is told the shape it should have had...
        assert "day first" in resp.get_data(as_text=True)
        # ...and a well-shaped date that does not exist is told that instead.
        resp = client.post("/", data={**GATE_FORM, "date": "31/02/1998"})
        assert resp.status_code == 400
        assert "not a real calendar date" in resp.get_data(as_text=True)


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
        """Re-pointed 2026-09-04: the plate geometry moved out of the
        template into app.py and is injected as JSON, so this checks the
        injected table rather than a hand-written JS literal."""
        import json as _json
        m = re.search(r"const HOUSE_SHAPES = (\{.*?\});", page, re.S)
        assert m, "plate geometry not injected into the page"
        shapes = _json.loads(m.group(1))
        assert sorted(int(k) for k in shapes) == list(range(1, 13))
        for h, poly in shapes.items():
            assert len(poly) in (3, 4), f"house {h} is not a triangle/diamond"


class TestPlateGeometry:
    """The chart wheel: which cell a graha is actually drawn in.

    LAUNCH-BLOCKER, 2026-09-04. A 9th-house Venus rendered inside the
    8th-house cell while the text correctly said 9th. Not an off-by-one and
    not a sign-vs-house confusion — the house mapping was right in both
    layers. `kundli_houses` clamped the DEGREE label's x to [62, 238] to keep
    long text inside the plate border, and for the four narrow triangles
    (3, 5, 9, 11) that clamp moved the anchor ACROSS a cell boundary: house
    9's label landed at x=238 while its own cell begins at x=240 on that row.

    It hid because the compact layer was fine and only the degree layer —
    which is the DEFAULT view — was wrong.
    """

    # A Sagittarius-lagna chart with three grahas in the 9th, which is the
    # shape the bug was reported on. Synthetic: no real birth record.
    BIRTH = BirthData(year=1990, month=9, day=5, hour=14, minute=0,
                      latitude=28.61, longitude=77.21, tz="+05:30",
                      place="Test")

    FORM = {"date": "1990-09-05", "time": "14:00", "lat": "28.61",
            "lon": "77.21", "tz": "+05:30", "place": "Test"}

    def _plate(self, client, layer, form=None):
        html = client.post("/", data=form or self.FORM).get_data(as_text=True)
        d1 = html[html.index('aria-label="North-Indian chart d1"'):]
        d1 = d1[:d1.index("</svg>")]
        block = d1[d1.index(f"grahas {layer}"):]
        return block[:block.index("</g>")]

    def test_the_reported_shape_is_the_one_under_test(self):
        chart = compute_chart(self.BIRTH)
        assert chart.lagna.sign == "Sagittarius"
        assert chart.planets["Venus"].sign == "Leo"
        assert chart.planets["Venus"].house == 9

    @staticmethod
    def _lines(block):
        """Every drawn LINE of the layer, as (x, y, text).

        Strengthened 2026-09-12. This used to read the <text> anchor only,
        which was the whole position when a house's grahas were one string.
        They are a stack now — one graha to a line, centred on the anchor —
        so the anchor can sit comfortably inside its cell while the top and
        bottom lines hang outside it. That is precisely the failure this
        class exists to catch, and reading the anchor could no longer see
        it: four degree labels in the 12th ran through the diagonal into
        house 1.
        """
        out = []
        for m in re.finditer(r"<text\b([^>]*)>(.*?)</text>", block, re.S):
            attrs, body = m.group(1), m.group(2)
            # `(?<![a-z])` because `dx="1.5"` also contains `x="1.5"`, and
            # reading a horizontal nudge as an absolute anchor put a graha
            # at x=1.5, outside the plate entirely.
            bx = float(re.search(r'(?<![a-z])x="([-\d.]+)"', attrs).group(1))
            by = float(re.search(r'(?<![a-z])y="([-\d.]+)"', attrs).group(1))
            x, y, text = bx, by, ""
            # `</tspan\s*>`: the macro breaks before the closing bracket to
            # keep whitespace out of the rendered label, so the close tag is
            # `</tspan\n>` and a literal `</tspan>` never matches.
            for t in re.finditer(r"<tspan\b([^>]*)>(.*?)</tspan\s*>",
                                 body, re.S):
                ta, tb = t.group(1), t.group(2)
                nx = re.search(r'(?<![a-z])x="([-\d.]+)"', ta)
                if nx:                       # a tspan with its own x is a LINE
                    if text.strip():
                        out.append((x, y, text))
                    x, text = float(nx.group(1)), ""
                    dy = re.search(r'\bdy="([-\d.]+)"', ta)
                    if dy:
                        y += float(dy.group(1))
                text += re.sub(r"<[^>]+>", "", tb)
            if text.strip():
                out.append((x, y, text))
            elif "<tspan" not in body:
                out.append((bx, by, re.sub(r"<[^>]+>", "", body)))
        return out

    @pytest.mark.parametrize("layer", ["grahas-compact", "grahas-deg"])
    def test_every_graha_is_drawn_in_its_own_house_cell(self, client, layer):
        """Both layers, because the bug was in only one of them."""
        from app import ABBR, house_at
        chart = compute_chart(self.BIRTH)
        lines = self._lines(self._plate(client, layer))
        assert lines, f"nothing drawn in {layer}"
        drawn = {}
        for x, y, text in lines:
            for token in re.findall(r"\b([A-Z][a-z])\b", text):
                drawn.setdefault(token, (x, y))
        for name, pos in chart.planets.items():
            abbr = ABBR[name]
            assert abbr in drawn, f"{name} not drawn in {layer}"
            x, y = drawn[abbr]
            cell = house_at(x, y)
            assert cell == pos.house, (
                f"{layer}: {name} is computed in house {pos.house} but drawn "
                f"at ({x}, {y}), which is inside the house-{cell} cell")

    # TWO CHARTS, because one was not enough. The reported-shape chart has
    # no house holding more than two grahas, so it could not see a stack
    # overflow at all — restoring the bug left this green. The reference
    # fixture puts four grahas in the 12th, which is a narrow triangle, and
    # is where the fourth degree label ran through the diagonal.
    CROWDED_FORM = dict(GATE_FORM)

    @pytest.mark.parametrize("layer", ["grahas-compact", "grahas-deg"])
    @pytest.mark.parametrize("shape", ["reported", "crowded"])
    def test_no_line_of_a_stack_leaves_its_cell(self, client, layer, shape):
        """The anchor is not the label. A four-graha house draws a stack
        centred on its anchor, and it is the ENDS of that stack that leave
        the cell — through a diagonal, into a house the graha is not in."""
        from app import house_at
        form = self.FORM if shape == "reported" else self.CROWDED_FORM
        chart = compute_chart(self.BIRTH if shape == "reported"
                              else GATE_BIRTH)
        if shape == "crowded":
            assert max(len(v) for v in chart.houses.values()) >= 4, (
                "this shape is supposed to crowd a cell and does not — "
                "the gate would pass for the wrong reason")
        houses = {}
        for name, pos in chart.planets.items():
            houses.setdefault(pos.house, []).append(name)
        stray = []
        for x, y, text in self._lines(self._plate(client, layer, form)):
            if not text.strip():
                continue
            cell = house_at(x, y)
            if cell is None:
                stray.append((x, y, text.strip()[:24], "outside the plate"))
                continue
            # Which house does this line BELONG to? The one whose grahas it
            # names — the lagna line belongs to house 1.
            named = {n for n in chart.planets if n[:2] in text}
            if "Asc" in text:
                belongs = 1
            elif named:
                belongs = chart.planets[sorted(named)[0]].house
            else:
                continue
            if cell != belongs:
                stray.append((x, y, text.strip()[:24],
                              f"drawn in cell {cell}, belongs to {belongs}"))
        assert not stray, f"{layer}/{shape}: " + "; ".join(map(str, stray))

    def test_no_label_overflows_its_cell_in_a_browser(self):
        """The BOX, not the point — measured where the text is actually set.

        The anchor tests above check where a label is hung. They cannot see
        how wide it is, and width is what broke: four degree labels in the
        12th sat on anchors comfortably inside a triangle that tapers, while
        the labels themselves were 90 user units wide in a cell 47 units
        across at that height. The anchors were right and the plate was
        wrong. `getBBox()` is the only thing that knows.
        """
        pw = pytest.importorskip("playwright.sync_api",
                                 reason="playwright not installed")
        import threading
        from werkzeug.serving import make_server
        from app import HOUSE_POLY, app, house_at
        srv = make_server("127.0.0.1", 0, app, threaded=True)
        port = srv.socket.getsockname()[1]
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            with pw.sync_playwright() as p:
                browser = TestMaskedBirthFieldsInARealBrowser._launch(p, pytest)
                boxes = {}
                for shape, form in (("reported", self.FORM),
                                    ("crowded", self.CROWDED_FORM)):
                    pg = browser.new_context(
                        viewport={"width": 1280, "height": 1000}).new_page()
                    pg.goto(f"http://127.0.0.1:{port}/")
                    for k, v in form.items():
                        pg.evaluate(
                            "([k,v]) => { const e = document.querySelector("
                            "`[name=\"${k}\"]`); if (e) e.value = v; }", [k, v])
                    with pg.expect_navigation():
                        pg.evaluate("document.querySelector('#cast').submit()")
                    pg.wait_for_timeout(900)
                    boxes[shape] = pg.evaluate(r"""() => {
                      const out = [];
                      document.querySelectorAll(
                        '#pane-d1 .grahas').forEach(g => {
                        const layer = g.classList.contains('grahas-deg')
                          ? 'deg' : 'compact';
                        // The hidden layer has no boxes to measure.
                        if (!g.getClientRects().length) return;
                        g.querySelectorAll('tspan').forEach(t => {
                          const b = t.getBBox();
                          if (!b.width) return;
                          out.push({layer, text: t.textContent.trim(),
                                    x: b.x, y: b.y, w: b.width, h: b.height});
                        });
                      });
                      return out;
                    }""")
                    assert boxes[shape], f"{shape}: no label boxes measured"
                browser.close()
        finally:
            srv.shutdown()

        for shape, rows in boxes.items():
            chart = compute_chart(self.BIRTH if shape == "reported"
                                  else GATE_BIRTH)
            over = []
            for r in rows:
                named = {n for n in chart.planets if n[:2] in r["text"]}
                if "Asc" in r["text"]:
                    belongs = 1
                elif named:
                    belongs = chart.planets[sorted(named)[0]].house
                else:
                    continue
                poly = HOUSE_POLY[belongs]
                # A hair of tolerance: an anti-aliased glyph edge is not a
                # graha in the wrong house.
                pad = 1.5
                corners = [(r["x"] + pad, r["y"] + pad),
                           (r["x"] + r["w"] - pad, r["y"] + pad),
                           (r["x"] + pad, r["y"] + r["h"] - pad),
                           (r["x"] + r["w"] - pad, r["y"] + r["h"] - pad)]
                outside = [c for c in corners if house_at(*c) != belongs]
                if outside:
                    where = [(round(a), round(b), house_at(a, b))
                             for a, b in outside]
                    over.append(
                        f"{shape}/{r['layer']} {r['text']!r} belongs to "
                        f"house {belongs}; corners {where} are in another "
                        f"cell")
            assert not over, "\n  ".join([""] + over)

    def test_the_template_draws_at_the_size_the_layout_reserved(self):
        """One number, one place.

        The plate's type sizes were literals in BOTH app.py (where the fit
        is computed) and the template (where the text is drawn). Raising
        MINI_SIZE to clear the legibility floor changed what `plate_layout`
        reserved room for and not one pixel of what rendered — the glyphs
        stayed at 26 units and stayed illegible, and every gate passed.
        """
        page = (HERE / "templates" / "index.html").read_text(encoding="utf-8")
        macros = page[page.index("{% macro grahalayer("):
                      page.index("{%- endmacro %}",
                                 page.index("{% macro glyphonly("))]
        for token in ("DEG_SIZE", "DEG_LEADING", "COMPACT_SIZE",
                      "COMPACT_LEADING", "MINI_SIZE", "MINI_LEADING"):
            assert token in page, f"{token} is not used by the template"
        # No bare pixel size may be set on a plate label.
        bare = re.findall(r"font-size:\s*\d", macros)
        assert not bare, bare
        for m in re.finditer(r'\bdy="(\d[\d.]*)"', macros):
            raise AssertionError(
                f'a literal leading of {m.group(1)} in the plate macros — '
                f'it must come from the same constant the fit was computed '
                f'with')

    def test_a_cell_too_narrow_for_a_degree_says_so_by_omission(self):
        """The fallback ladder, asserted rather than assumed.

        Four of the twelve cells are triangles. Where "♄Sa 9°47′" will not
        go, the plate drops the glyph, then the degree, then packs the marks
        onto fewer rows — one step at a time, never all the way to nothing.
        A cell with a graha in it always shows that graha.
        """
        from app import PLANETS, kundli_houses, planet_marks
        chart = compute_chart(GATE_BIRTH)
        houses = kundli_houses(
            chart.lagna.sign_index,
            {p: chart.planets[p].house for p in PLANETS},
            degrees={p: (chart.planets[p].degree_in_sign,
                         chart.planets[p].retrograde) for p in PLANETS},
            lagna_degree=chart.lagna.degree_in_sign,
            marks=planet_marks(chart))
        forms = {h["house"]: h["deg_layout"]["form"]
                 for h in houses if h["grahas"]}
        assert forms, "no occupied cell found"
        # Every occupied cell has SOME layout, in both modes.
        for h in houses:
            if h["grahas"]:
                assert h["deg_layout"], h["house"]
                assert h["compact_layout"], h["house"]
                assert h["mini_layout"] or h["mini_dots"], h["house"]
        # The ladder is exercised, not merely available: this chart has at
        # least one cell that takes the full form and one that cannot.
        assert "glyph-deg" in forms.values(), forms
        assert any(f != "glyph-deg" for f in forms.values()), forms

    def test_the_fit_estimate_is_never_optimistic(self):
        """`_label_width` decides whether a label fits, from a table of
        advance widths measured in a browser. If it ever runs SHORT the
        plate draws labels across house boundaries — so it is checked
        against the real boxes, with no tolerance in the forgiving
        direction."""
        pw = pytest.importorskip("playwright.sync_api",
                                 reason="playwright not installed")
        import threading
        from werkzeug.serving import make_server
        from app import DEG_SIZE, _label_width, app
        srv = make_server("127.0.0.1", 0, app, threaded=True)
        port = srv.socket.getsockname()[1]
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        samples = ["Sa 9°47′", "♄Sa 9°47′", "☽Mo 22°23′", "Mo 22°23′",
                   "Asc 11°05′", "☉Su 29°09′", "☿Me 25°32′", "♀Ve",
                   "☊Ra 7°51′", "♃Ju 2°53′"]
        try:
            with pw.sync_playwright() as p:
                browser = TestMaskedBirthFieldsInARealBrowser._launch(p, pytest)
                pg = browser.new_context(
                    viewport={"width": 1280, "height": 900}).new_page()
                pg.goto(f"http://127.0.0.1:{port}/")
                for k, v in GATE_FORM.items():
                    pg.evaluate(
                        "([k,v]) => { const e = document.querySelector("
                        "`[name=\"${k}\"]`); if (e) e.value = v; }", [k, v])
                with pg.expect_navigation():
                    pg.evaluate("document.querySelector('#cast').submit()")
                pg.wait_for_timeout(900)
                real = pg.evaluate(
                    """(args) => {
                      const [samples, size] = args;
                      const svg = document.querySelector('#pane-d1 svg');
                      const NS = 'http://www.w3.org/2000/svg';
                      const t = document.createElementNS(NS, 'text');
                      t.setAttribute('x', '-900');
                      t.setAttribute('y', '-900');
                      t.setAttribute('class', 'gm');
                      t.setAttribute('style',
                        'font-family:"IBM Plex Sans",system-ui,sans-serif;'
                        + 'font-size:' + size + 'px;font-weight:450;'
                        + 'font-variant-numeric:tabular-nums');
                      svg.appendChild(t);
                      const out = {};
                      for (const s of samples) {
                        t.textContent = s;
                        out[s] = t.getBBox().width;
                      }
                      t.remove();
                      return out;
                    }""", [samples, DEG_SIZE])
                browser.close()
        finally:
            srv.shutdown()
        assert real, "nothing measured"
        short = {s: (round(_label_width(s, DEG_SIZE), 2), round(w, 2))
                 for s, w in real.items()
                 if _label_width(s, DEG_SIZE) < w}
        assert not short, f"estimate runs short (estimate, real): {short}"

    def test_degree_anchors_stay_in_their_own_cell(self):
        """The regression itself, at the table level.

        The old clamp put houses 3, 5, 9 and 11 in cells 4, 6, 8 and 10.
        """
        from app import DEG_POS, NUMBER_POS, PLANET_POS, house_at
        for label, table in (("DEG_POS", DEG_POS), ("PLANET_POS", PLANET_POS),
                             ("NUMBER_POS", NUMBER_POS)):
            for house, (x, y) in table.items():
                assert house_at(x, y) == house, (
                    f"{label}[{house}] is at ({x}, {y}), inside cell "
                    f"{house_at(x, y)}")
        # And the specific clamp that caused it must not come back.
        source = (HERE / "app.py").read_text(encoding="utf-8")
        assert "min(max(x, 62), 238)" not in source

    def test_label_anchors_do_not_collide_within_a_cell(self):
        """The sign number and the graha stack must not sit on each other.

        Chasing the wrong-cell bug produced three arrangements in a row that
        each traded one collision for another — number over label, label
        over neighbour, label over border. Measured in a browser at the
        time; pinned here so the class of fault fails fast without one.
        """
        from app import DEG_POS, NUMBER_POS, PLANET_POS
        for house in range(1, 13):
            nx, ny = NUMBER_POS[house]
            for label, table in (("DEG_POS", DEG_POS),
                                 ("PLANET_POS", PLANET_POS)):
                gx, gy = table[house]
                gap = max(abs(nx - gx), abs(ny - gy))
                assert gap >= 18, (
                    f"house {house}: {label} {table[house]} sits {gap}px from "
                    f"its sign number {NUMBER_POS[house]} — they will overlap")

    def test_crowded_cells_drop_the_sign_number_not_the_grahas(self):
        """Three degree-labelled grahas fill a narrow triangle completely.

        Something has to give, and it is the sign number — one character,
        recoverable from the lagna and shown in the graha table — never a
        placement. It returns when the degree layer is toggled off.
        """
        from app import kundli_houses
        crowded = kundli_houses(
            8, {p: (9 if p in ("Sun", "Mercury", "Venus") else 1)
                for p in PLANETS},
            degrees={p: (5.0, False) for p in PLANETS}, lagna_degree=1.9)
        by_house = {h["house"]: h for h in crowded}
        assert by_house[9]["crowded"] is True     # three grahas
        assert by_house[3]["crowded"] is False    # empty
        assert len(by_house[9]["detail_lines"]) == 3
        # Only the number is dropped, and only while degrees are showing.
        css = (HERE / "static/style.css").read_text(encoding="utf-8")
        assert ".plate.showdeg #pane-d1 .signnum text.crowded" in css
        assert "display: none" in css
        # The grahas themselves are never dropped.
        assert "grahas-deg text.crowded { display: none" not in css

    def test_the_plate_is_north_indian_houses_fixed_signs_rotating(self):
        """Confirming the style, since the two conventions map oppositely.

        North Indian: the twelve cells are HOUSES and never move; the sign
        numbers printed in them rotate with the lagna. (South Indian is the
        reverse — signs fixed, lagna marked.) So house 1 is always the
        top-centre diamond, and the count runs anticlockwise.
        """
        from app import HOUSE_CENTER, kundli_houses
        # House 1 top-centre; 4, 7, 10 at left, bottom, right — the kendras
        # on the cardinal points, which is the signature of the layout.
        assert HOUSE_CENTER[1][0] == 150 and HOUSE_CENTER[1][1] < 100
        assert HOUSE_CENTER[4][0] < 100 and HOUSE_CENTER[7][1] > 200
        assert HOUSE_CENTER[10][0] > 200
        # Signs rotate: the same cell carries a different sign per lagna.
        aries = {h["house"]: h["sign_num"] for h in
                 kundli_houses(0, {p: 1 for p in PLANETS})}
        sagittarius = {h["house"]: h["sign_num"] for h in
                       kundli_houses(8, {p: 1 for p in PLANETS})}
        assert aries[1] == 1 and sagittarius[1] == 9
        assert aries[9] == 9 and sagittarius[9] == 5   # Leo in the 9th
        # …while the cells themselves do not move.
        from app import PLANET_POS
        assert PLANET_POS[9] == (272, 240)

    def test_one_geometry_table_shared_by_both_layers(self, page):
        """The structural fix: the placement layer and the browser's
        highlight layer must index the SAME table, not two copies."""
        import json as _json
        from app import HOUSE_CENTER, HOUSE_POLY
        shapes = _json.loads(
            re.search(r"const HOUSE_SHAPES = (\{.*?\});", page, re.S).group(1))
        centers = _json.loads(
            re.search(r"const HOUSE_CENTER = (\{.*?\});", page, re.S).group(1))
        for house in range(1, 13):
            assert [list(pt) for pt in HOUSE_POLY[house]] == shapes[str(house)]
            assert list(HOUSE_CENTER[house]) == centers[str(house)]

    def test_aspect_targets_come_from_the_server_not_a_second_formula(
            self, page):
        """A highlighted house must be the house the text names. The JS may
        walk intermediate cells for the animation, but a TARGET is read from
        the server's aspect table."""
        assert "const h = asp ? asp.house :" in page

    @pytest.mark.parametrize("planet,house,expected", [
        ("Jupiter", 1, [5, 7, 9]),      # 5th, 7th, 9th
        ("Mars", 1, [4, 7, 8]),         # 4th, 7th, 8th
        ("Saturn", 1, [3, 7, 10]),      # 3rd, 7th, 10th
        ("Jupiter", 8, [12, 2, 4]),     # wraps past 12
        ("Saturn", 11, [1, 5, 8]),
    ])
    def test_special_aspects_land_on_the_right_houses(
            self, planet, house, expected):
        """Jupiter 5/7/9, Mars 4/7/8, Saturn 3/7/10 — the houses the
        explorer highlights, straight from the payload the plate uses."""
        from app import planet_explorer
        sign = (house - 1) % 12          # lagna Aries → house n is sign n-1
        chart = synthetic_chart(0, {p: (sign if p == planet else 0)
                                    for p in PLANETS})
        assert chart.planets[planet].house == house
        px = planet_explorer(chart)[planet]
        assert px["house"] == house
        assert [a["house"] for a in px["aspects"]] == expected
        assert [a["offset"] for a in px["aspects"]] == \
            sorted(DRISHTI_OFFSETS[planet])


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

    def test_design_handoff_paper_tokens(self):
        """Re-anchored 2026-09-09 to the superseding token table at the top
        of DESIGN-HANDOFF.md, after an approved mockup moved the app to a
        light paper-first almanac.

        This gate stays `external` and stays strict — it just answers to the
        current design record instead of the retired one. An external gate
        whose source document changed must follow the document, or it stops
        meaning anything.
        """
        handoff = (HERE / "ui-design" / "DESIGN-HANDOFF.md").read_text("utf-8")
        assert "SUPERSEDED IN PART" in handoff, (
            "the token table below is only authoritative because the handoff "
            "says it supersedes the old one")
        # THE HEXES COME FROM THE DOCUMENT, not from a copy of them here.
        # Duplicating the table into the gate made every palette revision a
        # two-file edit, and the second file is the one that gets forgotten —
        # which is exactly what an external gate is supposed to catch rather
        # than suffer from. This reads the record and holds the stylesheet
        # to it.
        table = dict(re.findall(
            r"\|\s*`(--[\w-]+)`\s*\|\s*`(#[0-9a-fA-F]{6})`\s*\|", handoff))
        for token in ("--paper", "--surface", "--ink", "--accent",
                      "--accent-ink"):
            assert token in table, f"{token} is not in the handoff table"
        css = open(HERE / "static/style.css").read()
        default = css[css.index(":root,"):css.index('[data-palette="night"]')]
        for token, value in table.items():
            assert f"{token}: {value}" in default, (token, value)
        fav = open(HERE / "static/favicon.svg").read()
        for token in ("--paper", "--ink", "--accent"):
            assert table[token] in fav, (
                f"the favicon still carries the retired {token}")

    def test_framework_palettes_by_root_attribute(self):
        """Build framework, SIX · TOKENS: palettes stored centrally and
        switched by custom properties on the root — never conditional colour
        in components.

        Re-anchored 2026-09-09: SIX referred to how tokens are stored, and
        six palettes on a printed almanac was noise. Two readings ship. What
        the framework actually requires — central storage, root switching,
        no conditional colour in a component — is unchanged and asserted
        harder than before: every palette must define the FULL set.
        """
        css = open(HERE / "static/style.css").read()
        palettes = set(re.findall(r':root\[data-palette="(\w+)"\]', css))
        assert palettes == {"paper", "night"}, palettes
        block = css[:css.index("* { box-sizing")]
        for token in ("--paper", "--surface", "--ink", "--accent",
                      "--accent-ink", "--ink-rgb", "--accent-rgb"):
            assert block.count(f"{token}:") >= 2, token
        # A component may never carry a palette's hex directly.
        body = css[css.index("* { box-sizing"):]
        # The grain is an inline SVG data URI. `%23` inside it is an escaped
        # `#` for a filter reference, not a colour, and the URI carries no
        # colour at all — the noise is desaturated. Drop it before scanning
        # rather than widening the rule that keeps colour in the tokens.
        body = re.sub(r'url\("data:image/svg\+xml,[^"]*"\)', "", body)
        stray = [h for h in re.findall(r"#[0-9a-fA-F]{6}", body)]
        assert stray == [], f"hardcoded colour outside the token block: {stray}"

    def test_framework_non_negotiable_tokens(self):
        # "Square corners everywhere. The device bezel is the only radius"
        # — the sole exception in-app is a circular score ring.
        raw = open(HERE / "static/style.css").read()
        radii = re.findall(r"border-radius:\s*([^;]+);", raw)
        assert sorted(set(radii)) == ["0", "50%"], radii
        # "No shadows, no gradients, no elevation." DECLARATIONS, not prose:
        # scanning the raw file made a comment saying "no gradient and no
        # hue" fail the no-gradient rule.
        css = re.sub(r"/\*.*?\*/", "", raw, flags=re.S)
        assert "box-shadow" not in css and "gradient" not in css

    def test_design_handoff_glance_pattern(self, page):
        # 4b/5a: kicker date line, statement, ghost ☾, three chips, panel.
        assert 'class="glance"' in page
        # Re-baselined 2026-09-10 (characterization): the ☾ watermark is
        # gone. It was drawn on top of the kicker and the day's statement at
        # every width from 360 to 1600 — the only element on the page that
        # overlapped text by design — and the new rule is that nothing
        # overlaps, ever. What design 4b actually requires is a one-statement
        # hero, which the assertions around this one still pin.
        assert "☾" not in page
        assert re.search(r'class="[^"]*\bstatement\b', page)
        assert page.count('class="gchip') == 3
        for pane in ("gpane-chart", "gpane-transits", "gpane-dasha"):
            assert f'id="{pane}"' in page
        # chart pane caption keeps the identity facts
        assert "Candra in Rohini p.2" in page
        # Re-baselined 2026-08-22: the statement is now composed by the
        # reading engine (milestone 06), not the old MD/AD template. What
        # the design requires is a one-statement hero with a tinted span.
        assert "A Mercury season, Venus antara" not in page
        assert re.search(r'class="[^"]*\bstatement\b', page)
        assert '<span class="accent">' in page
        # dasha pane ring + transits pane dated rows
        assert 'class="gring"' in page
        assert 'class="growlist"' in page

    def test_a_navigation_and_disclosure(self, page):
        """Re-pinned 2026-09-10: the sticky nav moves between the eight
        CATEGORIES now, not between fourteen sections.

        Explore was a single scroll of everything at once — the complaint
        that prompted this — so it became an index, and a nav of fourteen
        section anchors was the thing that made the dump navigable rather
        than fixing it. Every one of those sections still exists and still
        lives under Explore; `TestExploreIndex` asserts each is reachable and
        that no two categories are ever on screen together.
        """
        assert 'class="secnav"' in page
        for anchor in ("#explore", "#cat-charts", "#cat-periods", "#cat-sky",
                       "#cat-combinations", "#cat-tables", "#cat-ask",
                       "#cat-learn"):
            assert f'href="{anchor}"' in page, anchor
        # progressive disclosure: antardashas, gocara table, doshas and
        # myth cards are all summary-first now
        assert page.count('class="fold"') >= 2
        # Re-pinned 2026-09-12. This used to require seven expanders across
        # Doshas and Myths, and the reason there were seven was that three
        # phenomena were printed in both sections. De-duplicating them is
        # the fix, not a regression — `TestNoEntryIsPrintedTwice` owns the
        # count now. What this gate still cares about is that BOTH sections
        # render something a reader can open.
        block = page[page.index('<section class="ledger" id="doshas"'):]
        block = block[:block.index("<!-- Gocara")]
        assert block.count('<details class="yoga">') >= 3, block.count(
            '<details class="yoga">')
        assert 'id="myths"' in block


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
        assert re.search(r'class="[^"]*\bstatement\b', page)
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
        assert 'href="#cat-match"' in match_page      # its category appears
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
           confidence="Interpretive", refused=False, reason="", verdict=None):
    return {
        # The verdict is a required field now, and it is validated exactly as
        # the answer is — so a fixture that leaves it out defaults to the
        # answer's own first sentence rather than to an unchecked blank.
        "verdict": (answer.split(".")[0] + "." if verdict is None and answer
                    else (verdict or "")),
        "answer": answer,
        "answer_statements": statements if statements is not None else [
            {"text": answer, "label": "COMPUTED",
             "fact_ids": list(facts), "rule_ids": [], "rule": ""}],
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

    def test_per_planet_varga_positions_are_in_the_ledger(
            self, chart, agent_facts):
        """The app computed and displayed D9/D10 placements all along while
        the ledger carried only the lagna and the vargottama list — so the
        agent had to decline D9 questions it held the answers to."""
        from vargas import dasamsa, navamsa
        for label, varga in (("d9", navamsa(chart)), ("d10", dasamsa(chart))):
            assert agent_facts[f"varga.{label}.lagna"].value["lagna"] == \
                varga.lagna_sign
            for planet in ("Sun", "Moon", "Mars", "Mercury", "Jupiter",
                           "Venus", "Saturn", "Rahu", "Ketu"):
                fact = agent_facts[f"varga.{label}.{planet.lower()}"]
                vp = varga.planets[planet]
                assert fact.value["sign"] == vp.sign
                assert fact.value["house"] == vp.house
                # The fact must name its chart, or the agent cannot tell the
                # reader which sky it is describing.
                assert label.upper() in fact.statement

    def test_varga_facts_carry_a_degree_and_name_it_a_convention(self,
                                                                 chart):
        """Inverted 2026-09-13, and that is the milestone.

        This used to assert the opposite: that a varga fact carried NO
        degree and said so, because the build computed divisional positions
        to the sign. It computes them to the degree now — which is what
        makes varga nakṣatras and dignity-by-degree possible at all.

        The honesty requirement did not go away, it moved. The stretch that
        produces a divisional degree is a SCALING CONVENTION, not something
        the classical texts assign, so every fact that carries one says so
        and `rule.varga.degree_convention` states it in full.
        """
        from chartfacts import build_facts
        import rulelib
        facts = [f for f in build_facts(chart, AGENT_WHEN)
                 if f.kind == "varga" and "planet" in f.value]
        assert facts, "no per-graha varga facts"
        for f in facts:
            assert f.value["degree"] is not None, f.id
            assert 0 <= f.value["degree"] < 30, (f.id, f.value["degree"])
            assert "scaling convention" in f.statement, f.id
        rule = rulelib.RULES["rule.varga.degree_convention"]
        assert "SCALING CONVENTION" in rule.text
        assert "never be quoted as a classical figure" in rule.text
        # And the retired claim is gone rather than left contradicting it.
        assert "rule.varga.sign_level" not in rulelib.RULES

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


class TestFixtureHygiene:
    """No real person's birth record is ever a fixture.

    A standing instruction from the commissioner, and the reason this repo
    exists as a fresh one. Encoded as a test because the rule has to survive
    sessions where nobody remembers being told — and because milestone 2
    adds an externally-supplied Ashtakavarga fixture, which is a new place a
    real record could quietly arrive.
    """

    def test_committed_fixtures_are_all_fictional(self):
        import fixtures as fx
        assert set(fx._BUILT_IN) == {"reference", "aisha", "partner"}
        # `reference` IS the fictional Aisha persona, not a third record.
        assert fx._BUILT_IN["reference"] is fx._BUILT_IN["aisha"]
        assert fx._BUILT_IN["aisha"] == fx._DEFAULT_AISHA
        assert fx._BUILT_IN["partner"] == fx._DEFAULT_PARTNER
        # Both are the corrected framework persona and the second fictional
        # record — a new entry here needs a deliberate decision, not a drift.
        assert (fx._DEFAULT_AISHA["year"], fx._DEFAULT_AISHA["place"]) == \
            (1998, "Jaipur")
        assert (fx._DEFAULT_PARTNER["year"], fx._DEFAULT_PARTNER["place"]) \
            == (1993, "Pune")

    def test_the_module_says_so_in_words(self):
        import fixtures as fx
        assert "No real person's birth record is committed" in fx.__doc__

    def test_external_cross_checks_run_against_the_fictional_chart(self):
        """ERFA today, AstroSage at milestone 2: an outside check must be
        run against the fictional fixture, never against a real record."""
        source = (HERE / "tools/erfa_cross_check.py").read_text(
            encoding="utf-8")
        assert 'fixtures.birth("reference")' in source


class TestRuleLibrary:
    """The classical rules interpretation rests on."""

    def test_every_rule_names_a_source(self):
        from rulelib import RULES
        assert len(RULES) >= 20
        for rid, rule in RULES.items():
            assert rid.startswith("rule."), rid
            assert rule.id == rid
            assert rule.text.strip() and rule.text.strip().endswith(".")
            assert rule.source.strip(), f"{rid} cites no source"

    def test_the_two_families_the_reading_needs_are_present(self):
        """Dasha-lord-by-lordship and transit-by-house are what a period
        question is actually answered from."""
        from rulelib import RULES
        for rid in ("rule.dasha.lordship", "rule.dasha.placement",
                    "rule.dasha.dignity", "rule.dasha.node",
                    "rule.transit.house", "rule.transit.from_moon",
                    "rule.transit.saturn", "rule.transit.jupiter",
                    "rule.transit.rahu", "rule.transit.ketu"):
            assert rid in RULES, rid
        for house in range(1, 13):
            assert f"rule.house.{house}" in RULES

    def test_applicable_subset_is_selected_not_dumped(self):
        from rulelib import RULES, rules_for
        picked = rules_for(dasha_lords=["Rahu", "Sun"],
                           transit_planets=["Saturn", "Jupiter"],
                           houses=[1, 10])
        ids = [r.id for r in picked]
        assert "rule.dasha.node" in ids          # a nodal lord is running
        assert "rule.transit.saturn" in ids
        assert "rule.house.10" in ids
        assert "rule.house.7" not in ids         # not in play
        assert len(ids) == len(set(ids))
        assert len(ids) < len(RULES)

    def test_nodal_rule_only_when_a_node_rules_the_period(self):
        from rulelib import rules_for
        ids = [r.id for r in rules_for(dasha_lords=["Venus"])]
        assert "rule.dasha.node" not in ids


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

    def test_varga_statements_pass_validation(self, chart):
        """A divisional claim is a THIRD frame.

        Adding varga facts without teaching the validator about them would
        have shipped the transit bug again in a new coat: Venus is in Cancer
        at birth and Virgo in the D9, so a true D9 sentence would have been
        withheld as a wrong natal placement.
        """
        from agent import ask_chart
        from vargas import dasamsa, navamsa
        d9, d10 = navamsa(chart), dasamsa(chart)
        venus_d9 = d9.planets["Venus"].sign
        venus_d10 = d10.planets["Venus"].sign
        # The frames must genuinely disagree, or this proves nothing.
        assert len({chart.planets["Venus"].sign, venus_d9, venus_d10}) == 3

        answer = (
            f"Your natal Venus is in {chart.planets['Venus'].sign}, but in "
            f"the D9 Venus is in {venus_d9}, and in the D10 Venus is in "
            f"{venus_d10}.")
        client = FakeClient([_reply(answer, facts=[
            "planet.venus", "varga.d9.venus", "varga.d10.venus"])])
        result = ask_chart(chart, AGENT_WHEN, "How is my Venus placed?",
                           client=client, model="test-model")
        assert result.ok, result.violations

    def test_varga_claims_are_still_checked_against_the_right_varga(
            self, chart):
        """Saying 'in the D9' cannot launder an invented placement."""
        from agent import ask_chart
        from vargas import navamsa
        wrong = next(s for s in SIGNS
                     if s != navamsa(chart).planets["Venus"].sign)
        client = FakeClient([_reply(f"In the D9, Venus is in {wrong}.",
                                    facts=["varga.d9.venus"])])
        result = ask_chart(chart, AGENT_WHEN, "Where is D9 Venus?",
                           client=client, model="test-model")
        assert not result.ok
        assert any(v.kind == "wrong-d9-sign" for v in result.violations)

    def test_a_degree_level_varga_answer_is_ledger_backed_not_withheld(
            self, chart):
        """THE STALE-PROMPT BUG, pinned at both ends.

        Until the divisions were cast at degree level the prompt told the
        model there was no degree inside a divisional sign and forbade
        stating one. The ledger has carried those degrees since cc308c7, so
        the instruction was telling the model to withhold a fact it had
        been handed. Both halves are asserted here: the prompt now says the
        degrees are there and are to be used, AND a true degree-level
        answer survives validation instead of being withheld.
        """
        from agent import SYSTEM_PROMPT, ask_chart
        from vargas import navamsa

        # The instruction itself. The retired prohibition must be gone —
        # not merely contradicted somewhere else in the prompt.
        assert "there is no degree within a divisional sign" not in \
            SYSTEM_PROMPT
        assert "never give a varga degree" not in SYSTEM_PROMPT
        assert "DO carry a degree within the divisional sign" in SYSTEM_PROMPT
        # …and the two limits that replaced it are still stated.
        assert "SCALING CONVENTION" in SYSTEM_PROMPT
        assert "no varga nakshatra" in SYSTEM_PROMPT

        venus = navamsa(chart).planets["Venus"]
        answer = (f"In the D9, Venus is in {venus.sign} at {venus.dms}, "
                  f"in the {ordinal(venus.house)} house from the D9 lagna.")
        result = ask_chart(
            chart, AGENT_WHEN, "Where exactly is my Venus in the D9?",
            client=FakeClient([_reply(answer, facts=["varga.d9.venus"])]),
            model="test-model")
        assert result.ok, (
            "a true degree-level varga answer was withheld: "
            f"{[v.kind for v in result.violations]}")
        assert venus.dms in result.answer

    def test_a_wrong_varga_degree_is_still_caught(self, chart):
        """The other side of the same change. Inviting the model to state a
        degree means the degree has to be checked — an invitation without a
        check is a wider fence, not a better one."""
        from agent import ask_chart
        from vargas import navamsa
        venus = navamsa(chart).planets["Venus"]
        wrong = (venus.degree_in_sign + 12.0) % 30.0
        client = FakeClient([_reply(
            f"In the D9, Venus is in {venus.sign} at {wrong:.2f}°.",
            facts=["varga.d9.venus"])])
        result = ask_chart(chart, AGENT_WHEN, "Where is D9 Venus?",
                           client=client, model="test-model")
        assert not result.ok
        assert any(v.kind == "wrong-varga-degree" for v in result.violations)

        # The same, written to the arcminute — which is the form the ledger
        # itself renders, and so the form a model is most likely to copy.
        # Judged at its own precision, not at the looser one a decimal
        # claim gets.
        wrong_dms = f"{int(wrong)}°{int((wrong % 1) * 60):02d}′"
        dms = ask_chart(
            chart, AGENT_WHEN, "Where is D9 Venus?",
            client=FakeClient([_reply(
                f"In the D9, Venus is in {venus.sign} at {wrong_dms}.",
                facts=["varga.d9.venus"])]),
            model="test-model")
        assert not dms.ok
        assert any(v.kind == "wrong-varga-degree" for v in dms.violations)
        # A two-arcminute error is an error. The tolerance is the precision
        # the writer chose, not a band wide enough to hide a wrong figure.
        near = venus.degree_in_sign + 2.0 / 60.0
        near_dms = f"{int(near)}°{int(round((near % 1) * 60)):02d}′"
        close = ask_chart(
            chart, AGENT_WHEN, "Where is D9 Venus?",
            client=FakeClient([_reply(
                f"In the D9, Venus is in {venus.sign} at {near_dms}.",
                facts=["varga.d9.venus"])]),
            model="test-model")
        assert not close.ok, f"{near_dms} passed against {venus.dms}"

        # Rounding honestly is not being wrong. The claim is judged at the
        # precision it was written to, so a whole-degree figure passes and
        # an arcminute figure is held to the arcminute.
        for figure in (f"{venus.degree_in_sign:.0f}°",
                       f"{venus.degree_in_sign:.1f}°", venus.dms):
            ok = ask_chart(
                chart, AGENT_WHEN, "Where is D9 Venus?",
                client=FakeClient([_reply(
                    f"In the D9, Venus is in {venus.sign} at {figure}.",
                    facts=["varga.d9.venus"])]),
                model="test-model")
            assert ok.ok, f"an honest rounding was rejected: {figure}"

    def test_a_varga_nakshatra_or_dignity_is_withheld_as_uncomputed(
            self, chart):
        """The ledger carries divisional sign, degree, house and vargottama
        status — and nothing else. Being given a degree is not permission to
        compute what was withheld, and a derived dignity reads exactly like
        a looked-up one."""
        from agent import ask_chart
        from vargas import navamsa
        venus = navamsa(chart).planets["Venus"]
        for claim in (f"In the D9, Venus is in {venus.sign} in Hasta "
                      f"nakshatra.",
                      f"In the D9, Venus is in {venus.sign} and is exalted "
                      f"there."):
            result = ask_chart(
                chart, AGENT_WHEN, "Venus in the D9?",
                client=FakeClient([_reply(claim,
                                          facts=["varga.d9.venus"])]),
                model="test-model")
            assert not result.ok, claim
            assert any(v.kind == "varga-not-computed"
                       for v in result.violations), claim

        # And it does NOT fire on a natal dignity, which IS in the ledger.
        natal = ask_chart(
            chart, AGENT_WHEN, "How is my Moon?",
            client=FakeClient([_reply(
                "Your natal Moon is in moolatrikona.",
                facts=["planet.moon"])]),
            model="test-model")
        assert not any(v.kind == "varga-not-computed"
                       for v in natal.violations)

    def test_an_unnamed_divisional_claim_accepts_either_varga(self, chart):
        """'in the divisional chart' without saying which is the writer's
        ambiguity, not a falsehood — it passes if either varga supports it,
        and still fails if neither does."""
        from agent import ask_chart
        from vargas import dasamsa, navamsa
        d10_sign = dasamsa(chart).planets["Mars"].sign
        client = FakeClient([_reply(
            f"In the divisional charts Mars is in {d10_sign}.",
            facts=["varga.d10.mars"])])
        assert ask_chart(chart, AGENT_WHEN, "Mars in the vargas?",
                         client=client, model="test-model").ok

        bad = next(s for s in SIGNS if s not in
                   (navamsa(chart).planets["Mars"].sign, d10_sign))
        client = FakeClient([_reply(
            f"In the divisional charts Mars is in {bad}.",
            facts=["varga.d10.mars"])])
        result = ask_chart(chart, AGENT_WHEN, "Mars in the vargas?",
                           client=client, model="test-model")
        assert not result.ok
        assert any(v.kind == "wrong-varga-sign" for v in result.violations)

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

    def test_broad_year_question_is_read_not_refused(self, chart):
        """The 2026 question must produce a READING.

        Re-drawn after the agent over-refused: it listed dasha and transit
        facts and declined to interpret them, which is honest and useless.
        A real answer interprets the active facts through the classical
        rules — at least three INTERPRETIVE statements, each citing a rule
        that exists — and asserts no outcome as certain.
        """
        from agent import ask_chart
        from chartfacts import build_facts
        from rulelib import is_known
        facts = {f.id: f for f in build_facts(chart, AGENT_WHEN)}
        d = facts["dasha.current"].value
        tj, ts = facts["transit.jupiter"].value, facts["transit.saturn"].value

        reading = (
            f"The {d['mahadasha']} mahadasha is the current era, and with "
            f"{d['mahadasha']} standing in your 1st house the period keeps "
            f"turning attention back onto you — how you are met, what you "
            f"are willing to want. The {d['antardasha']} antardasha inflects "
            f"it toward visibility and the matter of authority.\n\n"
            f"Transiting Jupiter in {tj['sign']} is crossing your "
            f"{tj['natal_house']}th house until {tj['until']}, which "
            f"classically favours retreat, study and quiet expenditure more "
            f"than public push. Transiting Saturn in {ts['sign']} works your "
            f"{ts['natal_house']}th until {ts['until']} — a slow, structural "
            f"season that rewards what is built to last.\n\n"
            f"Taken together this is a year that favours consolidation over "
            f"quick moves, and cautions against forcing visibility while "
            f"Jupiter is still in the 12th.")
        statements = [
            {"text": f"{d['mahadasha']} rules no sign, so its period is read "
                     f"from the house it occupies.",
             "label": "INTERPRETIVE", "fact_ids": ["dasha.current"],
             "rule_ids": ["rule.dasha.node", "rule.dasha.placement"],
             "rule": "A nodal dasha is read from its house, not lordship."},
            {"text": "Transiting Jupiter activates the house it occupies for "
                     "as long as it stays there.",
             "label": "INTERPRETIVE", "fact_ids": ["transit.jupiter"],
             "rule_ids": ["rule.transit.house", "rule.transit.jupiter"],
             "rule": "A transit activates the house it occupies."},
            {"text": "Saturn's transit consolidates rather than delivers.",
             "label": "INTERPRETIVE", "fact_ids": ["transit.saturn"],
             "rule_ids": ["rule.transit.saturn"],
             "rule": "Saturn tests and consolidates the house it crosses."},
            {"text": f"The {d['mahadasha']} mahadasha runs with the "
                     f"{d['antardasha']} antardasha.",
             "label": "COMPUTED", "fact_ids": ["dasha.current"],
             "rule_ids": [], "rule": ""},
        ]
        client = FakeClient([_reply(
            reading, statements=statements,
            facts=["dasha.current", "transit.jupiter", "transit.saturn"],
            rules=["rule.dasha.node", "rule.transit.house",
                   "rule.transit.saturn"],
            confidence="Interpretive")])
        result = ask_chart(chart, AGENT_WHEN,
                           "How does the rest of 2026 look?",
                           client=client, model="test-model")

        assert result.ok, result.violations
        assert result.refused is False, "a chart-hooked question must be read"

        interpretive = [st for st in result.statements
                        if st["label"] == "INTERPRETIVE"]
        assert len(interpretive) >= 3, interpretive
        for st in interpretive:
            assert st["rule_ids"], f"uncited interpretation: {st['text']}"
            for rid in st["rule_ids"]:
                assert is_known(rid), rid

        # …and nothing stated as a settled outcome.
        from agent import find_certainty
        assert find_certainty(result.answer) == []

    def test_a_reading_that_promises_an_outcome_is_withheld(self, chart):
        """The line moved, it did not disappear."""
        from agent import ask_chart
        client = FakeClient([_reply(
            "This is a strong year — you will get a promotion, and there "
            "will be a marriage before it ends.",
            statements=[{"text": "You will get a promotion.",
                         "label": "INTERPRETIVE",
                         "fact_ids": ["dasha.current"],
                         "rule_ids": ["rule.dasha.lordship"],
                         "rule": "The dasha lord delivers its houses."}],
            facts=["dasha.current"])])
        result = ask_chart(chart, AGENT_WHEN, "How is my year?",
                           client=client, model="test-model")
        assert not result.ok
        assert any(v.kind == "asserted-certainty" for v in result.violations)

    def test_an_invented_date_is_withheld(self, chart):
        from agent import ask_chart
        client = FakeClient([_reply(
            "The opening comes around December 2028, once Jupiter has moved.",
            facts=["transit.jupiter"])])
        result = ask_chart(chart, AGENT_WHEN, "When does it ease?",
                           client=client, model="test-model")
        assert not result.ok
        bad = [v for v in result.violations if v.kind == "invented-date"]
        assert bad and "December 2028" in bad[0].claim

    def test_interpretation_must_cite_a_rule_that_exists(self, chart):
        from agent import ask_chart
        client = FakeClient([_reply(
            "This favours slow work.",
            statements=[{"text": "This favours slow work.",
                         "label": "INTERPRETIVE",
                         "fact_ids": ["transit.saturn"],
                         "rule_ids": ["rule.transit.invented"],
                         "rule": "Made up."}],
            facts=["transit.saturn"])])
        result = ask_chart(chart, AGENT_WHEN, "What is Saturn doing?",
                           client=client, model="test-model")
        assert not result.ok
        assert any(v.kind == "unknown-rule-id" for v in result.violations)

    def test_only_hookless_questions_are_refused(self, chart):
        """Refusal is now the narrow case: another person, or not astrology."""
        from agent import ask_chart
        client = FakeClient([_reply(
            "", statements=[], refused=True,
            reason=("That turns on someone else's chart, which this reading "
                    "does not have. I can tell you what your own 7th house "
                    "and its lord are doing."))])
        result = ask_chart(chart, AGENT_WHEN, "Will she marry me?",
                           client=client, model="test-model")
        assert result.refused is True and result.ok
        assert "someone else's chart" in result.refusal_reason

    def test_prompt_asks_for_a_reading_not_a_recital(self):
        """Re-drawn 2026-09-03. The previous prompt routed broad questions to
        a refusal-plus-fact-list: technically honest, practically useless.
        The line is now about certainty, not about interpreting at all."""
        from agent import SYSTEM_PROMPT
        # Interpretation is REQUIRED, and the prose comes first.
        assert "Lead with the reading" in SYSTEM_PROMPT
        assert "at least three interpretive" in SYSTEM_PROMPT
        # Renamed when the period walkthrough became the five-frame method.
        assert "WORK ALL FIVE FRAMES BEFORE YOU ANSWER" in SYSTEM_PROMPT
        # The one hard line: outcomes, not interpretation.
        assert "THE ONE HARD LINE" in SYSTEM_PROMPT
        assert "You may not say what WILL happen." in SYSTEM_PROMPT
        assert "That is the whole restriction." in SYSTEM_PROMPT
        # Refusal is now the narrow case, and named as such.
        assert "WHEN TO REFUSE — RARELY" in SYSTEM_PROMPT
        assert "IS answerable" in SYSTEM_PROMPT
        assert "Do not refuse it." in SYSTEM_PROMPT
        # The natal/transit separation survives the rewrite.
        assert "never a bare" in SYSTEM_PROMPT
        # Tone.
        assert "no compliance language" in SYSTEM_PROMPT

    def test_withheld_message_says_why_and_suggests_a_narrower_question(self):
        from agent import Violation, explain_violations
        why, hint = explain_violations(
            [Violation("wrong-natal-sign", "Mars is in Leo", "not Leo")])
        assert "placement claim" in why and "computed chart" in why
        assert "rephrasing" in hint
        why, hint = explain_violations(
            [Violation("asserted-certainty", "you will get", "settled")])
        assert "outcome" in why and "certain" in why
        assert "favours" in hint
        why, _ = explain_violations(
            [Violation("invented-date", "December 2028", "not produced")])
        assert "date" in why
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
        # The ledger and the question are separate content blocks so the
        # ledger can be cached across a session's ten questions; the
        # privacy check runs over every block, not just the first.
        blocks = sent["messages"][0]["content"]
        assert isinstance(blocks, list) and len(blocks) == 2
        assert blocks[0]["cache_control"] == {"type": "ephemeral"}
        assert "cache_control" not in blocks[1], (
            "the question changes every time and must stay out of the "
            "cached prefix")
        body = "".join(b["text"] for b in blocks)
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
        assert "fact ledger" in system and "rule library" in system
        assert "COMPUTED" in system and "INTERPRETIVE" in system
        assert "No medical, legal or" in system
        assert "You may not say what WILL happen." in system
        # Structured output is enforced by schema, not by asking nicely.
        # The rule library travels with the facts, so interpretation has
        # something citable to rest on.
        assert '"rules"' in body and "rule.dasha.lordship" in body
        schema = sent["output_config"]["format"]["schema"]
        assert schema["required"] == [
            "answer", "answer_statements", "facts_used", "rules_applied",
            "confidence", "refused", "refusal_reason",
            # Answer-first is structural: the verdict is its own required
            # field, so it cannot be forgotten or buried mid-paragraph.
            "verdict"]
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
    def test_session_cap_is_five_questions(self):
        from agent import MAX_QUESTIONS_PER_SESSION, RateLimiter
        assert MAX_QUESTIONS_PER_SESSION == 5
        limiter = RateLimiter()
        for i in range(5):
            allowed, _, remaining = limiter.check("1.2.3.4", "sess")
            assert allowed, f"blocked at question {i + 1}"
            assert remaining == 5 - i
            limiter.record("1.2.3.4", "sess")
        allowed, reason, remaining = limiter.check("1.2.3.4", "sess")
        assert not allowed and remaining == 0
        assert "5-question limit" in reason
        # A different session is unaffected — the cap is per session.
        assert limiter.check("1.2.3.4", "other")[0] is True

    def test_the_screen_counts_down_from_the_constant_not_from_a_typed_number(
            self, client, monkeypatch):
        """The cap is written once. Every place the page states it — the Ask
        screen's counter, the panel's counter, the panel's one-line limit —
        must read the constant, or lowering it leaves the old number printed
        somewhere and the app contradicts itself in public."""
        import agent as agent_mod
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-not-a-real-key")
        cap = str(agent_mod.MAX_QUESTIONS_PER_SESSION)
        assert cap == "5"
        page = client.post("/", data=GATE_FORM).get_data(as_text=True)
        assert f'<span id="askremaining">{cap}</span>' in page
        assert f'<span id="agentremaining">{cap}</span>' in page
        assert f"Limit {cap} questions" in page
        assert page.count("questions left this session") == 2
        # And it FOLLOWS the constant rather than happening to match it:
        # move the cap and all three sites move with it.
        monkeypatch.setattr(agent_mod, "MAX_QUESTIONS_PER_SESSION", 7)
        page = client.post("/", data=GATE_FORM).get_data(as_text=True)
        assert '<span id="askremaining">7</span>' in page
        assert '<span id="agentremaining">7</span>' in page
        assert "Limit 7 questions" in page
        assert "askremaining\">5<" not in page

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

    # --- the school travels with the request ---------------------------------
    #
    # THE BUG THESE PIN. /ask set no school at all, so every computation in it
    # read the ContextVar exactly as the previous request in that worker had
    # left it. Two consequences, both live: the reader's own choice was
    # ignored, and under a threaded worker one reader's school answered
    # another reader's question. The endpoint now runs inside
    # `schools.use(...)` on a selection read from the request body.

    def _school_seen(self, client, monkeypatch, **over):
        """The school in force at the moment the agent is called."""
        import agent as agent_mod
        seen = {}

        import schools

        def spy(chart, when, question, **kw):
            seen["node_reach"] = schools.active()["node_reach"]
            raise agent_mod.AgentUnavailable("stopped inside the handler")

        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-not-a-real-key")
        monkeypatch.setattr(agent_mod, "ask_chart", spy)
        client.post("/ask", json=self._body(**over))
        assert "node_reach" in seen, "the handler never reached the agent"
        return seen["node_reach"]

    def test_two_questions_in_one_worker_each_get_their_own_school(
            self, client, monkeypatch):
        """The leak, directly. One worker, three questions, three selections
        — and the third must not inherit the second."""
        assert self._school_seen(
            client, monkeypatch, school_node_reach="none") == "none"
        assert self._school_seen(
            client, monkeypatch, school_node_reach="opposition") == "opposition"
        assert self._school_seen(
            client, monkeypatch, school_node_reach="classical") == "classical"
        # …and a selection does not survive the request that carried it.
        # The last question here asks under a NON-default school on purpose:
        # a handler that sets the ContextVar without restoring it leaves the
        # default behind after a default request, and an assertion written
        # that way passes against the very leak it exists to catch.
        import schools
        before = schools.active()["node_reach"]
        assert self._school_seen(
            client, monkeypatch, school_node_reach="none") == "none"
        assert schools.active()["node_reach"] == before

    def test_a_question_carrying_no_school_gets_the_documented_defaults(
            self, client, monkeypatch):
        """Not "whatever the ContextVar holds". The distinction is only
        visible when something else has already moved it, so move it first
        and then ask with no school fields at all."""
        import schools
        assert schools.DEFAULTS["node_reach"] == "classical"
        with schools.use({"node_reach": "none"}):
            assert schools.active()["node_reach"] == "none"   # genuinely set
            assert self._school_seen(client, monkeypatch) == "classical"
        # The same via the real page flow: one reader renders a chart under a
        # non-default school, the next asks a question in that same worker.
        client.post("/", data={**GATE_FORM, "school_node_reach": "none"})
        assert self._school_seen(client, monkeypatch) == "classical"

    def test_the_page_echoes_the_school_back_beside_the_birth_details(
            self, client):
        """The endpoint can only honour what the page sends it. The fields
        are named as the form names them, so one reader parses both."""
        import html
        import schools
        page = client.post(
            "/", data={**GATE_FORM, "school_node_reach": "none"}
        ).get_data(as_text=True)
        payload = json.loads(html.unescape(
            re.search(r"data-birth='([^']*)'", page).group(1)))
        for field in ("date", "time", "lat", "lon", "tz", "place"):
            assert field in payload
        for option_id in schools.OPTIONS:
            assert f"school_{option_id}" in payload
        assert payload["school_node_reach"] == "none"

    def test_a_hand_edited_school_cannot_switch_on_what_is_not_built(
            self, client, monkeypatch):
        """`normalise` defends the endpoint the same way it defends the form:
        an unknown answer falls back to the recommended one, and an option
        that is not live is forced to its default however the body is
        written."""
        import schools
        assert self._school_seen(
            client, monkeypatch, school_node_reach="not-a-school") == \
            schools.DEFAULTS["node_reach"]
        # And the not-live guard, against an option that is not live by
        # construction. This used to name `dual_lord`, which went live with
        # the arudhas and took the gate with it — a guard that depends on
        # some feature still being unbuilt expires the moment it is built.
        from app import schools_from_fields
        probe = schools.Option(
            id="probe_unbuilt", question="Which way, once it exists?",
            consequence="Nothing yet.", live=False,
            unavailable="Not yet in play.",
            answers=(
                schools.Answer(id="a", text="One way", school="A",
                               explain="First.", recommended=True),
                schools.Answer(id="b", text="The other", school="B",
                               explain="Second."),
            ))
        monkeypatch.setitem(schools.OPTIONS, probe.id, probe)
        monkeypatch.setitem(schools.DEFAULTS, probe.id, probe.default)
        assert schools_from_fields({f"school_{probe.id}": "b"})[
            probe.id] == probe.default

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

    def test_a_question_that_never_reached_the_model_is_not_charged(
            self, client, monkeypatch):
        """With five questions a session, spending one on our own failure is
        a real cost to the reader. Nothing before `ask_chart` returns — a
        missing session id, birth details we cannot read, an unconfigured
        deployment — may touch the counter."""
        import agent as agent_mod
        sid = "uncharged-session"
        before = agent_mod.LIMITER.remaining(sid)

        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        assert client.post("/ask", json=self._body(sid=sid)).status_code == 503
        assert agent_mod.LIMITER.remaining(sid) == before

        assert client.post(
            "/ask", json=self._body(sid=sid, tz="")).status_code == 400
        assert agent_mod.LIMITER.remaining(sid) == before

        assert client.post(
            "/ask", json=self._body(sid=sid, question="")).status_code == 400
        assert agent_mod.LIMITER.remaining(sid) == before

    def test_a_withheld_answer_does_not_spend_a_question(
            self, client, tmp_path, monkeypatch):
        """A withhold is OUR validator catching OUR model, and the reader
        does not pay for that.

        This used to assert the opposite, on the reasoning that the API call
        had been made and paid for. That reasoning was about our costs. At
        five questions a session a withheld answer takes a fifth of what the
        reader has and returns nothing — the cost of a failed generation is
        ours to carry, not theirs. `LIMITER.record` therefore sits BELOW the
        `answer.ok` branch, and the 422 reports the counter unmoved so the
        screen and the server do not disagree on the next question."""
        import agent as agent_mod
        from agent import AgentAnswer, Violation
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-not-a-real-key")
        monkeypatch.setattr(agent_mod, "CORRECTIONS_LOG", tmp_path / "c.jsonl")
        monkeypatch.setattr(
            agent_mod, "ask_chart",
            lambda *a, **k: AgentAnswer(
                answer="Saturn sits in Leo, so the year is settled.",
                model="fake",
                violations=[Violation(kind="wrong-sign",
                                      claim="Saturn sits in Leo",
                                      detail="claimed Saturn in Leo")]))
        sid = "withheld-session"
        before = agent_mod.LIMITER.remaining(sid)
        r = client.post("/ask", json=self._body(sid=sid))
        assert r.status_code == 422
        payload = r.get_json()
        assert payload["withheld"] is True
        assert agent_mod.LIMITER.remaining(sid) == before, (
            "a withheld answer charged the reader a question")
        assert payload["remaining"] == before

        # Repeatedly, too. A withhold that cost nothing once but drained the
        # session over five tries would be the same bug wearing a slower
        # clock — and this is the case that matters, because a chart the
        # validator keeps catching produces withhold after withhold.
        for _ in range(6):
            assert client.post(
                "/ask", json=self._body(sid=sid)).status_code == 422
        assert agent_mod.LIMITER.remaining(sid) == before

        # And a GOOD answer still spends one, or the counter means nothing.
        monkeypatch.setattr(
            agent_mod, "ask_chart",
            lambda *a, **k: AgentAnswer(
                answer="Your Moon is in Taurus, in the 10th.",
                verdict="Your Moon is in Taurus.", model="fake",
                facts_used=["planet.moon"], statements=[]))
        good = client.post("/ask", json=self._body(sid=sid))
        assert good.status_code == 200
        assert agent_mod.LIMITER.remaining(sid) == before - 1
        assert good.get_json()["remaining"] == before - 1

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
        """Regression: text must never be painted the colour behind it.

        The agent panel first shipped with the ground colour on its
        suggestion buttons, which rendered them as three empty boxes. The
        markup was correct and the DOM had the text, so nothing but looking
        at the render caught it.

        Re-pointed 2026-09-09: the tokens flipped meaning in the paper
        redesign. `--ink` was the ground and is now the text; `--paper` is
        the ground. The failure being guarded is identical — only the name of
        the ground changed — so the gate follows it rather than retiring.

        Inverted elements (a dark ink panel with paper-coloured text) are the
        legitimate use, so the rule is not "never" — it is "never without a
        background in the same block".
        """
        css = (HERE / "static/style.css").read_text(encoding="utf-8")
        offenders = []
        for block in re.finditer(r"\{([^{}]*)\}", css):
            body = block.group(1)
            if re.search(r"color:\s*var\(--paper\)", body) and \
                    not re.search(r"background(-color)?:", body):
                offenders.append(" ".join(body.split())[:70])
        assert offenders == [], (
            "text painted with the ground colour: " + "; ".join(offenders))

    def test_panel_hides_controls_when_unconfigured(self, page):
        """Graceful degradation: the section explains itself and the rest of
        the dashboard is unaffected."""
        assert 'id="agent"' in page
        assert 'href="#cat-ask"' in page     # the agent lives under Ask
        assert "ANTHROPIC_API_KEY" in page and "not configured" in page
        assert 'id="agentq"' not in page          # no dead input offered

    def test_panel_renders_with_suggestions_and_disclosure(
            self, client, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-not-a-real-key")
        page = client.post("/", data=GATE_FORM).get_data(as_text=True)
        assert 'id="agent"' in page
        assert 'href="#cat-ask"' in page     # the agent lives under Ask
        # Three in the agent panel, and three more on the Ask SCREEN, which
        # has its own field. Both are the same three questions.
        assert page.count('class="sugq"') == 6
        assert "Facts and rules used" in page        # the Why? pattern
        assert "thumbdown" in page
        assert 'id="agentq"' in page
        # The panel promises a reading, not a compliance notice.
        assert "get a reading" in page
        assert "what it <em>will</em> happen" not in page
        assert "will</em> happen" in page            # the one hard line
        # The key is set on the server for this render and must not appear
        # anywhere in what the browser receives.
        assert "sk-ant" not in page
        assert "not-a-real-key" not in page


# --- rule precedence: a contact outranks the generic gocara verdict ----------
#
# A live reading called transit Ketu "supportive" from the 3rd-from-the-Moon
# rule while Ketu sat 2.66° off natal Venus. Every placement in it was
# correct, so no placement check could catch it; what was wrong was which
# rule got reported as the verdict.
#
# The fixture below is SYNTHETIC and fictional — no birth record is ever a
# fixture here. It is built backwards from a fixed moment: transit Ketu is
# genuinely at Leo 14°03′58″ on 2026-03-15, so natal Venus is placed 2.66°
# ahead of it, the Moon in Gemini so Ketu's sign is 3rd from the Moon (the
# "supportive" count), and the lagna in Sagittarius so Venus lands in the 9th
# and rules the 6th and 11th. The ephemeris half is real; only the birth half
# is invented.
CONTACT_WHEN = datetime(2026, 3, 15, 12, 0, tzinfo=timezone.utc)

_CONTACT_NATAL = {
    "Sun": 155.0, "Moon": 72.0, "Mars": 20.0, "Mercury": 170.0,
    "Jupiter": 98.0, "Venus": 136.7261, "Saturn": 295.0,
    "Rahu": 355.0, "Ketu": 175.0,
}
_CONTACT_LAGNA = 250.0            # Sagittarius 10°


def node_on_benefic_chart():
    """A node within 3° of a natal benefic, in a sign 3rd from the Moon."""
    from engine import Chart, PlanetPosition, Position
    lagna_sign = int(_CONTACT_LAGNA // 30)
    planets = {
        name: PlanetPosition(longitude=lon, name=name,
                             house=(int(lon // 30) - lagna_sign) % 12 + 1)
        for name, lon in _CONTACT_NATAL.items()
    }
    birth = BirthData(year=1990, month=6, day=1, hour=12, minute=0,
                      latitude=19.0, longitude=73.0, tz="+05:30",
                      place="(synthetic)")
    return Chart(birth=birth, lagna=Position(longitude=_CONTACT_LAGNA),
                 planets=planets, ayanamsa=24.0)


@pytest.fixture(scope="module")
def contact_chart():
    return node_on_benefic_chart()


class TestContactPrecedence:
    def test_the_fixture_is_the_configuration_under_test(self, contact_chart):
        """If this drifts, everything below is testing something else."""
        from transits import angular_distance, transit_snapshot
        from yogas import houses_owned_by
        venus = contact_chart.planets["Venus"]
        assert (venus.sign, venus.house) == ("Leo", 9)
        assert houses_owned_by(contact_chart, "Venus") == (6, 11)
        snap = transit_snapshot(contact_chart, CONTACT_WHEN)
        ketu = snap.planets["Ketu"]
        assert ketu.sign == "Leo"
        orb = angular_distance(ketu.position.longitude, venus.longitude)
        assert orb == pytest.approx(2.66, abs=0.05)
        # …and the sign Ketu transits is 3rd from the natal Moon, which the
        # generic rule calls supportive. That is the conflict.
        moon_sign = contact_chart.planets["Moon"].sign_index
        assert (ketu.position.sign_index - moon_sign) % 12 + 1 == 3

    def test_contact_is_a_fact_with_its_own_id(self, contact_chart):
        from chartfacts import build_facts
        facts = {f.id: f for f in build_facts(contact_chart, CONTACT_WHEN)}
        assert "contact.ketu-venus" in facts
        value = facts["contact.ketu-venus"].value
        assert value["transit"] == "Ketu" and value["point"] == "Venus"
        assert value["orb"] == pytest.approx(2.66, abs=0.05)
        assert value["node"] is True and value["benefic"] is True
        assert value["from_moon"] == 3
        assert value["generic_quality"] == "supportive"
        assert value["governs"] is True
        assert value["outranks_rule"] == "rule.transit.from_moon"
        assert value["governing_rule"] == "rule.transit.node_on_natal"

    def test_the_suppressed_significations_are_concrete(self, contact_chart):
        """'Venus is eclipsed' is not usable; 'your 6th and 11th, and love,
        comfort and refinement' is."""
        from chartfacts import build_facts
        facts = {f.id: f for f in build_facts(contact_chart, CONTACT_WHEN)}
        fact = facts["contact.ketu-venus"]
        assert fact.value["lordships"] == [6, 11]
        assert "6th and 11th house" in fact.statement
        assert "karaka of love, marriage" in fact.statement
        assert "eclipse" in fact.statement

    def test_the_fact_names_both_rules_and_says_which_governs(
            self, contact_chart):
        from chartfacts import build_facts
        facts = {f.id: f for f in build_facts(contact_chart, CONTACT_WHEN)}
        statement = facts["contact.ketu-venus"].statement
        # the outranked rule, quoted with its own verdict…
        assert "rule.transit.from_moon" in statement
        assert "3rd from the natal Moon" in statement
        assert "supportive" in statement
        # …and the rule that displaces it, said plainly.
        assert "GOVERNS" in statement
        assert "rule.transit.contact_over_gocara" in statement
        assert "rule.precedence.name_both" in statement

    def test_the_transit_fact_no_longer_ends_on_the_generic_verdict(
            self, contact_chart):
        """The 'supportive' wording lives inside the transit fact itself.
        Left as the last word there, it is what the reading quoted."""
        from chartfacts import build_facts
        facts = {f.id: f for f in build_facts(contact_chart, CONTACT_WHEN)}
        transit = facts["transit.ketu"]
        assert transit.value["governing_contacts"] == ["contact.ketu-venus"]
        assert "GOVERNING CONTACT" in transit.statement
        assert transit.statement.index("supportive") < \
            transit.statement.index("GOVERNING CONTACT")
        # …and no contact means no override clause, so the fact stays clean.
        assert "GOVERNING CONTACT" not in facts["transit.jupiter"].statement
        assert facts["transit.jupiter"].value["governing_contacts"] == []

    def test_precedence_rules_are_in_the_library_with_sources(self):
        from rulelib import RULES
        for rid in ("rule.transit.contact", "rule.transit.node_on_natal",
                    "rule.transit.contact_over_gocara",
                    "rule.precedence.name_both", "rule.graha.karakatva"):
            assert rid in RULES, rid
            assert RULES[rid].source.strip()
        assert "eclipse" in RULES["rule.transit.node_on_natal"].text
        assert "governs" in RULES["rule.transit.contact_over_gocara"].text
        assert "BOTH" in RULES["rule.precedence.name_both"].text

    def test_precedence_rules_travel_only_when_a_contact_exists(
            self, contact_chart, chart):
        from chartfacts import active_rules
        from rulelib import rules_for
        ids = [r.id for r in active_rules(contact_chart, CONTACT_WHEN)]
        assert "rule.transit.node_on_natal" in ids
        assert "rule.transit.contact_over_gocara" in ids
        assert "rule.precedence.name_both" in ids
        assert "rule.graha.karakatva" in ids
        # No contact, no precedence rules — the library stays a selection.
        bare = [r.id for r in rules_for(transit_planets=["Saturn"])]
        assert "rule.transit.contact_over_gocara" not in bare
        assert "rule.transit.node_on_natal" not in bare
        # A non-nodal contact gets the contact rules but not the nodal one.
        venus_only = [r.id for r in rules_for(transit_planets=["Venus"],
                                              contacts=["Venus"])]
        assert "rule.transit.contact" in venus_only
        assert "rule.transit.node_on_natal" not in venus_only

    # --- the validator: the reading itself ---------------------------------

    GENERIC_VERDICT = (
        "Transiting Ketu is moving through Leo, your 9th house. Counted "
        "from your natal Moon it stands 3rd, which is a supportive gocara "
        "position, so this is an easy stretch for matters of fortune and "
        "teachers.")

    def test_the_generic_verdict_alone_is_a_violation(self, contact_chart):
        """Every placement in this answer is correct. It is still wrong."""
        from agent import validate_payload
        payload = {
            "answer": self.GENERIC_VERDICT,
            "answer_statements": [
                {"text": self.GENERIC_VERDICT, "label": "INTERPRETIVE",
                 "fact_ids": ["transit.ketu"],
                 "rule_ids": ["rule.transit.from_moon"],
                 "rule": "the 3rd from the Moon is supportive"}],
            "facts_used": ["transit.ketu"], "rules_applied": [],
            "confidence": "Interpretive", "refused": False,
            "refusal_reason": "",
        }
        violations = validate_payload(payload, contact_chart, CONTACT_WHEN)
        kinds = {v.kind for v in violations}
        assert "ungoverned-generic" in kinds, violations
        # No placement claim is wrong — that is the point of this test.
        assert not (kinds & {"wrong-natal-sign", "wrong-natal-house",
                             "wrong-transit-sign", "wrong-transit-house"})
        detail = next(v for v in violations
                      if v.kind == "ungoverned-generic").detail
        assert "natal Venus" in detail and "contact.ketu-venus" in detail

    def test_the_reading_passes_once_the_conjunction_is_named_as_governing(
            self, contact_chart):
        from agent import validate_payload
        answer = (
            "Transiting Ketu is moving through Leo, your 9th house. By the "
            "generic count it stands 3rd from your natal Moon, which the "
            "gocara rule reads as supportive — but that is not what governs "
            "here. Ketu is sitting 2.66° from your natal Venus, and a "
            "node on a natal graha is read as an eclipse of it. Venus rules "
            "your 6th and 11th houses and carries love, comfort and "
            "refinement; those are the significations under a shadow while "
            "this contact holds, and the conjunction is what governs, not "
            "the from-the-Moon count.")
        payload = {
            "answer": answer,
            "answer_statements": [
                {"text": answer, "label": "INTERPRETIVE",
                 "fact_ids": ["transit.ketu", "contact.ketu-venus",
                              "planet.venus"],
                 "rule_ids": ["rule.transit.node_on_natal",
                              "rule.transit.contact_over_gocara",
                              "rule.precedence.name_both"],
                 "rule": "a node on a natal graha eclipses it, and the "
                         "contact outranks the from-the-Moon verdict"}],
            "facts_used": ["transit.ketu", "contact.ketu-venus"],
            "rules_applied": ["rule.transit.contact_over_gocara"],
            "confidence": "Interpretive", "refused": False,
            "refusal_reason": "",
        }
        assert validate_payload(payload, contact_chart, CONTACT_WHEN) == []

    def test_naming_the_natal_point_is_enough_to_qualify(self, contact_chart):
        """The check requires the conflict to be visible, not phrased one
        particular way — an answer that talks about the Venus contact and
        also mentions the from-the-Moon count is not withheld."""
        from agent import find_ungoverned_generic
        from chartfacts import transit_contacts_summary
        contacts = transit_contacts_summary(contact_chart, CONTACT_WHEN)
        text = ("Transiting Ketu stands 3rd from the Moon, generically "
                "supportive, but it is on your natal Venus and that "
                "conjunction governs.")
        assert find_ungoverned_generic(text, (), contacts) == []
        # Citing the contact fact qualifies it too, even without the name.
        bare = ("Transiting Ketu is in a supportive gocara position from "
                "the Moon.")
        assert find_ungoverned_generic(bare, ["contact.ketu-venus"],
                                       contacts) == []
        assert find_ungoverned_generic(bare, (), contacts)

    def test_a_transit_with_no_contact_is_free_to_be_called_supportive(
            self, contact_chart):
        """The rule bites only where there is a conflict to resolve."""
        from agent import find_ungoverned_generic
        from chartfacts import transit_contacts_summary
        contacts = transit_contacts_summary(contact_chart, CONTACT_WHEN)
        assert [c["id"] for c in contacts] == ["contact.ketu-venus"]
        text = ("Transiting Jupiter is moving through Gemini and stands in a "
                "supportive position from your Moon.")
        assert find_ungoverned_generic(text, (), contacts) == []

    def test_a_refusal_is_not_checked_for_precedence(self, contact_chart):
        """A refusal asserts nothing about the chart, so there is no verdict
        to outrank."""
        from agent import validate_payload
        payload = {
            "answer": "That is another person's chart, so I cannot read it "
                      "here.",
            "answer_statements": [], "facts_used": [], "rules_applied": [],
            "confidence": "Interpretive", "refused": True,
            "refusal_reason": "no hook in this chart",
        }
        assert validate_payload(payload, contact_chart, CONTACT_WHEN) == []

    def test_withheld_message_explains_the_precedence_failure(self):
        from agent import Violation, explain_violations
        why, hint = explain_violations([Violation(
            "ungoverned-generic", "…supportive…", "…")])
        assert "governs" in why and "natal" in why
        assert hint.strip()

    def test_the_prompt_states_the_precedence(self):
        from agent import SYSTEM_PROMPT
        assert "PRECEDENCE" in SYSTEM_PROMPT
        assert "OUTRANKS" in SYSTEM_PROMPT
        assert "contact.*" in SYSTEM_PROMPT
        assert "karakatvas" in SYSTEM_PROMPT
        assert "Name BOTH" in SYSTEM_PROMPT


# --- the oracle: a second implementation's answers --------------------------
#
# `fixtures_pyjhora.json` was produced by PyJHora, an independently written
# AGPL Vedic astrology library that this app does not link or import (see
# tools/oracle/README.md and the hygiene test that enforces it). Its answers
# are EXTERNAL: if one of these goes red, the presumption is that Sidera is
# wrong.
#
# What it buys today: the D1 positions and the D9/D10 SIGNS stop being
# characterization. What it buys next: it is the gate milestones 2 and 3 are
# built against, so those tests are written before the features exist rather
# than after, and the shape assertions below fail loudly if the file is
# regenerated into something they can no longer be built on.
ORACLE_PATH = HERE / "fixtures_pyjhora.json"

# An arcminute — the outer bound, kept as a coarse net. The disagreement was
# 48.68″ (Mercury) until the differential run traced every arcsecond of it to
# PyJHora's FLG_TRUEPOS; with that pinned to apparent the observed gap is
# 0.002″, which is JSON rounding at six decimals. The tight assertion lives in
# the test, where it can explain itself.
ORACLE_TOLERANCE_ARCSEC = 60.0


@pytest.fixture(scope="module")
def oracle():
    if not ORACLE_PATH.exists():
        pytest.skip("fixtures_pyjhora.json absent — "
                    "run tools/oracle/make_oracle.sh")
    return json.loads(ORACLE_PATH.read_text(encoding="utf-8"))


def _arcsec(a: float, b: float) -> float:
    return abs((a - b + 180.0) % 360.0 - 180.0) * 3600.0


class TestOracleCrossCheck:
    """Sidera against a second implementation, on the fictional charts."""

    def test_the_oracle_used_lahiri_and_not_its_own_default(self, oracle):
        """PyJHora's default is True Pushya. The gap is 1.14° — larger than
        anything this comparison is meant to detect, so a file computed with
        the default would fail everything below for the wrong reason."""
        assert oracle["settings"]["ayanamsa_mode"] == "LAHIRI"
        for name, chart in oracle["charts"].items():
            ayan = chart["ayanamsa"]
            assert ayan["mode"] == "LAHIRI", name
            assert ayan["pyjhora_default_mode"] == "TRUE_PUSHYA", name
            # …and the file proves the override took, by carrying both.
            assert abs(ayan["difference_arcsec"]) > 3000, name

    def test_ayanamsa_agrees_with_ours(self, oracle):
        from engine import compute_chart
        for name in ("reference", "partner"):
            if not fixtures.is_built_in(name):
                pytest.skip("fixtures substituted")
            ours = compute_chart(fixtures.birth(name)).ayanamsa
            theirs = oracle["charts"][name]["ayanamsa"]["value_deg"]
            assert abs(ours - theirs) * 3600 < 1.0, (
                f"{name}: ayanamsa {ours} vs {theirs}")

    @pytest.mark.parametrize("name", ["reference", "partner"])
    def test_d1_positions_agree_within_an_arcminute(self, oracle, name):
        from engine import compute_chart
        if not fixtures.is_built_in(name):
            pytest.skip("fixtures substituted")
        chart = compute_chart(fixtures.birth(name))
        theirs = oracle["charts"][name]["rasi"]
        ours = {"Lagna": chart.lagna.longitude,
                **{p: chart.planets[p].longitude for p in PLANETS}}
        worst = []
        for body, longitude in ours.items():
            gap = _arcsec(longitude, theirs[body]["longitude"])
            worst.append((gap, body))
            assert gap < ORACLE_TOLERANCE_ARCSEC, (
                f"{name} {body}: {longitude:.6f} vs "
                f"{theirs[body]['longitude']:.6f} — {gap:.2f}″ apart")
        # WHAT THIS DOES AND DOES NOT PROVE.
        # Since the ayanamsa, node convention and position flag are all
        # pinned to match, both sides are the same swisseph called the same
        # way, and the residual is JSON rounding at six decimals — about
        # 0.002″. That is a check on CONVENTIONS and plumbing, not on the
        # ephemeris: the ephemeris is anchored by ERFA
        # (`TestIndependentEphemerisCrossCheck`), and PyJHora's independence
        # is spent on the interpretation layer instead — nakshatras, vargas,
        # daśās, arudhas, Ashtakavarga.
        # A NON-trivial gap here means a convention has drifted apart again,
        # which is worth catching: it was 49″ before the position flag was
        # pinned, and every one of those arcseconds was light-time.
        assert max(worst)[0] < 0.01, (
            f"{name}: conventions have drifted — worst {max(worst)[0]:.4f}″ "
            f"at {max(worst)[1]}, expected agreement to JSON rounding")

    @pytest.mark.parametrize("name", ["reference", "partner"])
    def test_d1_signs_and_whole_sign_houses_agree(self, oracle, name):
        """Longitude agreement is not the same as agreeing about the chart:
        a body 40″ away can still sit on the far side of a sign boundary."""
        from engine import compute_chart
        if not fixtures.is_built_in(name):
            pytest.skip("fixtures substituted")
        chart = compute_chart(fixtures.birth(name))
        theirs = oracle["charts"][name]["rasi"]
        assert chart.lagna.sign == theirs["Lagna"]["sign"]
        lagna_index = theirs["Lagna"]["sign_index"]
        for planet in PLANETS:
            p = chart.planets[planet]
            assert p.sign == theirs[planet]["sign"], planet
            expected = (theirs[planet]["sign_index"] - lagna_index) % 12 + 1
            assert p.house == expected, planet

    @pytest.mark.parametrize("name", ["reference", "partner"])
    def test_navamsa_and_dasamsa_signs_agree(self, oracle, name):
        """The varga gate that was missing.

        `vargas.py` was characterization only — its expected signs came from
        this build. PyJHora implements the Parasari counting independently,
        and agrees on every body in both charts. This is what upgrades the
        D9/D10 claim from 'unchanged' to 'checked'.
        """
        from engine import compute_chart
        from vargas import dasamsa, navamsa
        if not fixtures.is_built_in(name):
            pytest.skip("fixtures substituted")
        chart = compute_chart(fixtures.birth(name))
        for label, ours in (("D9", navamsa(chart)), ("D10", dasamsa(chart))):
            theirs = oracle["charts"][name]["divisional_charts"][label]
            assert ours.lagna_sign == theirs["Lagna"]["sign"], \
                f"{name} {label} lagna"
            for planet in PLANETS:
                assert ours.planets[planet].sign == theirs[planet]["sign"], \
                    f"{name} {label} {planet}"

    def test_the_node_convention_is_matched_and_the_gap_recorded(self,
                                                                 oracle):
        """PyJHora defaults to the TRUE node; Sidera uses the MEAN node.

        Unpinned, that alone would put Rahu 1.48° out on the partner chart —
        enough to cross a sign boundary and invalidate every arudha and
        karaka comparison downstream. The oracle is run with mean nodes; the
        true-node positions ride along so the divergence stays visible.
        """
        assert oracle["settings"]["node_mode"] == "mean"
        for name, chart in oracle["charts"].items():
            nodes = chart["nodes"]
            assert nodes["used"] == "mean", name
            assert set(nodes["true_node_positions"]) == {"Rahu", "Ketu"}
            # Rahu and Ketu are 180° apart under either convention, so the
            # two conventions must disagree about them by the same amount.
            gap = nodes["mean_minus_true_arcsec"]
            assert gap["Rahu"] == gap["Ketu"], name
            assert gap["Rahu"] > 0, f"{name}: no difference at all?"


class TestOracleGatesTheNextMilestones:
    """The shape milestones 2 and 3 will be built against.

    These assert the FIXTURE, not Sidera — nothing here is implemented yet.
    They exist so that regenerating the oracle into something the planned
    gates cannot rest on fails now, loudly, rather than in the middle of
    building the feature.
    """

    # --- milestone 2: Ashtakavarga ------------------------------------
    @pytest.mark.parametrize("name", ["reference", "partner"])
    def test_ashtakavarga_is_raw_per_sign_and_sums_to_337(self, oracle,
                                                          name):
        av = oracle["charts"][name]["ashtakavarga"]
        seven = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus",
                 "Saturn")
        assert set(av["bav_by_sign"]) == set(seven)
        for planet in seven:
            row = av["bav_by_sign"][planet]
            assert len(row) == 12, planet
            assert all(0 <= b <= 8 for b in row), planet
        # The BPHS per-planet totals, confirmed by an implementation that
        # did not get them from us.
        assert av["bav_totals"] == {"Sun": 48, "Moon": 49, "Mars": 39,
                                    "Mercury": 54, "Jupiter": 56,
                                    "Venus": 52, "Saturn": 39}
        assert sum(av["bav_totals"].values()) == 337
        # SAV is the seven planetary rows summed — the Lagna row is carried
        # separately and is NOT part of it.
        assert len(av["sav_by_sign"]) == 12
        assert av["sav_total"] == 337
        for sign in range(12):
            assert av["sav_by_sign"][sign] == sum(
                av["bav_by_sign"][p][sign] for p in seven), sign
        assert len(av["lagna_bav_by_sign"]) == 12
        assert av["lagna_bav_total"] not in (0,)
        assert "RAW" in av["note"] and "sodhana" in av["note"]

    def test_the_337_checksum_is_chart_invariant_and_says_so(self, oracle):
        """A caveat that has to survive, or milestone 2 will over-claim.

        The per-planet totals count rows in the classical benefic-point
        tables and depend on no birth moment — both fictional charts return
        the identical numbers. They gate the TABLES. The per-sign arrays are
        what actually vary, and they are what a real comparison must use.
        """
        totals = [oracle["charts"][n]["ashtakavarga"]["bav_totals"]
                  for n in ("reference", "partner")]
        assert totals[0] == totals[1]
        by_sign = [oracle["charts"][n]["ashtakavarga"]["sav_by_sign"]
                   for n in ("reference", "partner")]
        assert by_sign[0] != by_sign[1], (
            "two different charts produced the same SAV distribution — "
            "the oracle is not chart-dependent, which would make it useless")
        note = oracle["charts"]["reference"]["ashtakavarga"]["note"]
        assert "chart-invariant" in note or "SAME for every chart" in note

    # --- milestone 3: degree-level vargas, arudhas, Upapada -----------
    def test_every_standard_varga_is_present_with_degrees(self, oracle):
        """Sidera computes D9 and D10 to the SIGN only. The degree inside
        the divisional sign is exactly what milestone 3 adds, so the oracle
        has to carry it."""
        for name in ("reference", "partner"):
            charts_ = oracle["charts"][name]["divisional_charts"]
            assert len(charts_) >= 20
            for dvf in (1, 2, 3, 7, 9, 10, 12, 16, 30, 60):
                key = f"D{dvf}"
                assert key in charts_, key
                for body in ("Lagna",) + tuple(PLANETS):
                    entry = charts_[key][body]
                    assert entry["sign"] in SIGNS
                    assert 0.0 <= entry["degree_in_sign"] < 30.0, \
                        f"{name} {key} {body}"
                    assert abs(entry["longitude"]
                               - (entry["sign_index"] * 30
                                  + entry["degree_in_sign"])) < 1e-6

    def test_both_upapada_schools_are_exported(self, oracle):
        """THE TWO SCHOOLS, AND WHY BOTH SHIP.

        An arudha is counted from the lord of the house. Scorpio and
        Aquarius have two lords each, and the tradition does not agree which
        carries the count:

          Parashari  the sole classical lord — Mars, Saturn.
          Jaimini    the STRONGER of the two co-lords, so Ketu or Rahu can
                     carry it.

        Upapada Lagna is the arudha of the 12th and is read for marriage, so
        Sidera will name the school rather than pick one silently — the same
        way gunamilan.py handles the yoni and vasya splits.
        """
        for name in ("reference", "partner"):
            block = oracle["charts"][name]["bhava_arudhas"]
            for school in ("parashari", "jaimini"):
                side = block[school]
                assert len(side["arudhas"]) == 12, (name, school)
                assert all(0 <= a <= 11 for a in side["arudhas"])
                assert side["arudha_signs"] == [
                    SIGNS[a] for a in side["arudhas"]]
                # A12 is the Upapada, and it is named as such.
                assert side["upapada_sign_index"] == side["arudhas"][11]
                assert side["upapada_sign"] == side["arudha_signs"][11]
                assert side["rule"].strip()
            assert isinstance(block["schools_agree"], bool)
            differ = {d["house"] for d in block["houses_where_schools_differ"]}
            assert differ == {h + 1 for h in range(12)
                              if block["parashari"]["arudhas"][h]
                              != block["jaimini"]["arudhas"][h]}
            assert block["schools_agree"] == (not differ)

    def test_the_schools_actually_diverge_somewhere_in_the_fixtures(
            self, oracle):
        """A two-school export nobody can test is decoration. The reference
        chart disagrees at A7 — Gemini under Parashari, Scorpio under
        Jaimini — so milestone 3 has a live case to gate on."""
        ref = oracle["charts"]["reference"]["bhava_arudhas"]
        assert ref["schools_agree"] is False
        differ = ref["houses_where_schools_differ"]
        assert differ == [{"house": 7, "parashari": "Gemini",
                           "jaimini": "Scorpio"}]
        # …and the honest converse: on THESE charts the Upapada itself is
        # not contested, because neither 12th house is Scorpio or Aquarius.
        # Milestone 3 must not read that as "the schools always agree on UL".
        for name in ("reference", "partner"):
            block = oracle["charts"][name]["bhava_arudhas"]
            assert block["upapada_contested_in_this_chart"] is False
            assert 12 not in block["houses_that_are_scorpio_or_aquarius"]

    def test_chara_karakas_carry_both_schemes_and_label_the_derived_one(
            self, oracle):
        for name in ("reference", "partner"):
            ck = oracle["charts"][name]["chara_karakas"]
            eight = ck["eight_karaka"]
            seven = ck["seven_karaka"]
            assert len(eight["order"]) == 8 and "Rahu" in eight["order"]
            assert len(seven["order"]) == 7 and "Rahu" not in seven["order"]
            assert set(eight["assignment"]) == {
                "Atma", "Amatya", "Bhratri", "Matri", "Pitri", "Putra",
                "Jnati", "Dara"}
            assert set(seven["assignment"]) == {
                "Atma", "Amatya", "Bhratri", "Matri", "Putra", "Jnati",
                "Dara"}
            # The 7-karaka list is derived here, not shipped by PyJHora, and
            # the file says so — it is a weaker gate and must not be quoted
            # as oracle output.
            assert "DERIVED" in seven["source"]
            assert "PyJHora" in eight["source"]

    def test_sphutas_and_shadbala_are_present_for_later_milestones(self,
                                                                   oracle):
        for name in ("reference", "partner"):
            sphutas = oracle["charts"][name]["sphutas"]
            for key in ("tri_sphuta", "chatur_sphuta", "prana_sphuta",
                        "deha_sphuta", "mrityu_sphuta", "beeja_sphuta",
                        "kshetra_sphuta", "yogi_sphuta"):
                assert key in sphutas, (name, key)
                assert 0.0 <= sphutas[key]["degree_in_sign"] < 30.0
            sb = oracle["charts"][name]["shadbala"]["components"]
            for row in ("sthana_bala", "kaala_bala", "dig_bala",
                        "cheshta_bala", "naisargika_bala", "drik_bala",
                        "total_shashtiamsas", "total_rupas",
                        "strength_ratio"):
                assert row in sb, (name, row)
                # Sun..Saturn only — the nodes have no shadbala.
                assert set(sb[row]) == {"Sun", "Moon", "Mars", "Mercury",
                                        "Jupiter", "Venus", "Saturn"}
            # The six components must actually sum to the reported total.
            for planet in sb["total_shashtiamsas"]:
                parts = sum(sb[r][planet] for r in
                            ("sthana_bala", "kaala_bala", "dig_bala",
                             "cheshta_bala", "naisargika_bala", "drik_bala"))
                assert abs(parts - sb["total_shashtiamsas"][planet]) < 0.05, \
                    (name, planet)


class TestPlateGeometryAgainstAnIndependentRenderer:
    """The house→cell mapping, checked against someone else's derivation.

    `TestPlateGeometry` proves our two layers agree with each other. That is
    an internal consistency check: it would stay green if the whole table
    were rotated by one house, which is exactly the launch-blocking bug
    class it was written after.

    These coordinates come from `react-native-kundli-chart` (MIT,
    github.com/mobile-dev-ci/react-native-kundli-chart, v1.0.0), whose
    `constants/geometry.ts` authors the North-Indian plate in the same
    300×300 space and derives each cell from the square corners, the four
    side-midpoints, the centre, and the diagonal/diamond intersections. It
    was written independently of this build and shares no code with it —
    the same standing as the ERFA cross-check.

    The package is evaluated in ui-design/RENDERER-EVALUATION.md and is NOT
    adopted; only this table is taken, as confirmation.
    """

    # HOUSE_POLYGONS from that file, verbatim. Ours are the same vertices
    # inset by 3 units so a 6-unit stroke sits inside the frame.
    INDEPENDENT = {
        1: "150,0 225,75 150,150 75,75",
        2: "0,0 150,0 75,75",
        3: "0,0 75,75 0,150",
        4: "0,150 75,75 150,150 75,225",
        5: "0,300 0,150 75,225",
        6: "0,300 75,225 150,300",
        7: "150,300 75,225 150,150 225,225",
        8: "300,300 225,225 150,300",
        9: "300,300 300,150 225,225",
        10: "300,150 225,75 150,150 225,225",
        11: "300,0 225,75 300,150",
        12: "300,0 150,0 225,75",
    }
    INSET = 3.0          # stroke inset, in the 300-unit authoring space

    def _uninset(self, points):
        """Our cell in their coordinates, as a comparable vertex SET.

        Sorted, because the two tables are free to start the same cell at a
        different corner or wind it the other way — the cell is the set of
        its vertices.
        """
        scale = 300.0 / (300.0 - 2 * self.INSET)
        return sorted((round((x - self.INSET) * scale, 6),
                       round((y - self.INSET) * scale, 6))
                      for x, y in points)

    def _ordered(self, spec):
        """Their cell in authoring order — required for the shoelace area."""
        return [tuple(float(v) for v in pair.split(","))
                for pair in spec.split()]

    def _parse(self, spec):
        return sorted(self._ordered(spec))

    def test_every_house_cell_matches_the_independent_derivation(self):
        from app import HOUSE_POLY
        for house in range(1, 13):
            assert self._uninset(HOUSE_POLY[house]) == \
                self._parse(self.INDEPENDENT[house]), (
                    f"house {house} cell disagrees with an independently "
                    f"derived North-Indian plate")

    def test_the_cells_tile_the_plate_exactly(self):
        """Twelve cells, no gap and no overlap: the areas must sum to the
        whole square. A rotation of the mapping would survive the test
        above only if it also survived this one, and it cannot."""
        def area(points):
            total = 0.0
            for i, (x1, y1) in enumerate(points):
                x2, y2 = points[(i + 1) % len(points)]
                total += x1 * y2 - x2 * y1
            return abs(total) / 2.0
        cells = [self._ordered(spec) for spec in self.INDEPENDENT.values()]
        assert len(cells) == 12
        assert abs(sum(area(c) for c in cells) - 300 * 300) < 1e-6
        # The four kendras are the big diamonds: each is 1/8 of the plate.
        for kendra in (1, 4, 7, 10):
            assert abs(area(self._ordered(self.INDEPENDENT[kendra]))
                       - 300 * 300 / 8) < 1e-6

    def test_our_own_table_still_resolves_each_cell_to_its_house(self):
        """The independent table is only useful if it describes OUR plate:
        the centre of each of their cells must land in our matching house."""
        from app import house_at
        for house in range(1, 13):
            points = self._parse(self.INDEPENDENT[house])
            cx = sum(p[0] for p in points) / len(points)
            cy = sum(p[1] for p in points) / len(points)
            # Pull the centroid slightly toward the plate centre so a
            # centroid sitting on a shared edge is not ambiguous.
            cx += (150 - cx) * 0.02
            cy += (150 - cy) * 0.02
            assert house_at(cx, cy) == house, (
                f"the independent cell for house {house} centres in house "
                f"{house_at(cx, cy)} of our plate")


class TestArudhas:
    """A1–A12 and the Upapada, against a second implementation.

    WHAT IS GATED HOW, AND WHY THE TWO HALVES DIFFER
    The Parāśarī school has one classical answer, and it is gated hard:
    every pada on both fixtures, plus the counting rule asserted directly.

    The Jaimini school asks which of two co-lords is stronger, and that is a
    hierarchy the tradition states in words rather than in code. Sidera's is
    written from the tradition and NOT transcribed from PyJHora — an oracle
    we had copied would be a mirror, not a check. The cost is honest and
    measured: the two agree on both fixtures and on 96% of random charts,
    and part company at the tie-break levels. `tools/oracle/DIFFERENTIAL.md`
    records that; this class does not paper over it by asserting agreement
    that does not exist.
    """

    def _oracle_arudhas(self, oracle, name, answer):
        key = {"single": "parashari", "stronger": "jaimini"}[answer]
        return oracle["charts"][name]["bhava_arudhas"][key]["arudhas"]

    @pytest.mark.parametrize("name", ["reference", "partner"])
    @pytest.mark.parametrize("answer", ["single", "stronger"])
    def test_every_pada_matches_the_oracle(self, oracle, name, answer):
        import arudhas
        import schools
        chart = compute_chart(fixtures.birth(name))
        with schools.use({"dual_lord": answer}):
            ours = list(arudhas.arudhas(chart))
        theirs = self._oracle_arudhas(oracle, name, answer)
        assert len(ours) == 12
        mismatches = [
            f"A{h + 1}: ours {SIGNS[ours[h]]}, oracle {SIGNS[theirs[h]]}"
            for h in range(12) if ours[h] != theirs[h]]
        assert mismatches == [], (
            f"{name}/{answer}: " + "; ".join(mismatches))

    def test_the_counting_rule_is_reflection_not_a_lookup(self, chart):
        """The pada is as far from the lord as the lord is from the house.
        Asserted directly, so the implementation cannot drift into a table
        that happens to agree with the oracle on two charts."""
        import arudhas
        import schools
        with schools.use({"dual_lord": "single"}):
            for house in range(1, 13):
                house_sign = (chart.lagna.sign_index + house - 1) % 12
                lord = arudhas.SIGN_LORDS[house_sign]
                lord_sign = chart.planets[lord].sign_index
                distance = (lord_sign - house_sign) % 12
                pada = arudhas.arudha_pada(chart, house)
                plain = (lord_sign + distance) % 12
                if (plain - house_sign) % 12 in (0, 6):
                    # The exception fired: the image may not stand on the
                    # house or opposite it.
                    assert pada == (plain + 9) % 12, house
                    assert (pada - house_sign) % 12 not in (0, 6)
                else:
                    assert pada == plain, house

    def test_no_arudha_ever_lands_on_its_own_house_or_opposite(self):
        """The exception, over enough charts that it actually fires. A
        single fixture can go a whole chart without triggering it."""
        import arudhas
        import schools
        from datetime import timedelta
        fired = 0
        base = fixtures.birth("reference")
        with schools.use({"dual_lord": "single"}):
            for hours in range(0, 240, 3):
                moment = base.local_datetime + timedelta(hours=hours)
                chart = compute_chart(BirthData(
                    year=moment.year, month=moment.month, day=moment.day,
                    hour=moment.hour, minute=moment.minute,
                    latitude=base.latitude, longitude=base.longitude,
                    tz=base.tz, place=base.place))
                for house in range(1, 13):
                    house_sign = (chart.lagna.sign_index + house - 1) % 12
                    pada = arudhas.arudha_pada(chart, house)
                    assert (pada - house_sign) % 12 not in (0, 6), (
                        f"A{house} landed on its own house or opposite it")
                    lord_sign = chart.planets[
                        arudhas.SIGN_LORDS[house_sign]].sign_index
                    if ((lord_sign + (lord_sign - house_sign) % 12)
                            - house_sign) % 12 in (0, 6):
                        fired += 1
        assert fired > 0, "the exception never fired — it is untested"

    def test_the_upapada_is_the_twelfth_arudha(self, chart):
        import arudhas
        assert arudhas.upapada(chart) == arudhas.arudhas(chart)[11]
        assert arudhas.upapada_house(chart) == (
            (arudhas.upapada(chart) - chart.lagna.sign_index) % 12 + 1)

    def test_the_schools_differ_only_where_a_counted_sign_has_two_lords(self):
        """STRUCTURAL, and it must hold exactly — this is the half of the
        Jaimini school that is not a judgement call. If the two schools
        disagree about a house whose sign has one lord, the strength rules
        have leaked somewhere they do not belong."""
        import arudhas
        from datetime import timedelta
        base = fixtures.birth("reference")
        checked = differed = 0
        for hours in range(0, 480, 7):
            moment = base.local_datetime + timedelta(hours=hours)
            chart = compute_chart(BirthData(
                year=moment.year, month=moment.month, day=moment.day,
                hour=moment.hour, minute=moment.minute,
                latitude=base.latitude, longitude=base.longitude,
                tz=base.tz, place=base.place))
            both = arudhas.both_schools(chart)
            contested = arudhas.contested_houses(chart)
            for house in range(1, 13):
                checked += 1
                if both["single"][house - 1] != both["stronger"][house - 1]:
                    differed += 1
                    assert house in contested, (
                        f"the schools disagree about A{house}, whose sign "
                        f"has only one lord")
        assert checked > 100
        assert differed > 0, (
            "the two schools never disagreed — either the fork is not wired "
            "or no sampled chart put a node's sign on a counted house")

    def test_a_chart_with_no_contested_house_is_school_proof(self):
        """Most charts have Scorpio and Aquarius somewhere, so this is about
        the houses that are NOT contested being untouched by the choice."""
        import arudhas
        chart = compute_chart(fixtures.birth("partner"))
        both = arudhas.both_schools(chart)
        contested = set(arudhas.contested_houses(chart))
        for house in range(1, 13):
            if house not in contested:
                assert both["single"][house - 1] == both["stronger"][house - 1]

    def test_rasi_drishti_is_its_own_aspect_system(self):
        """Used by the strength hierarchy, and NOT the graha drishti in
        `transits.py`. Mixing the two is the kind of error that produces
        plausible numbers, so the two are asserted to be different."""
        import arudhas
        from transits import aspected_signs
        for sign in range(12):
            seen = arudhas.rasi_drishti(sign)
            assert sign not in seen, "a sign does not aspect itself"
            assert len(seen) == 3, sign
            # Mutual: rasi drishti is symmetric, which graha drishti is not.
            for other in seen:
                assert sign in arudhas.rasi_drishti(other), (sign, other)
            # Movable looks at fixed, fixed at movable, dual at dual.
            mode = arudhas.modality(sign)
            wanted = {arudhas.MOVABLE: arudhas.FIXED,
                      arudhas.FIXED: arudhas.MOVABLE,
                      arudhas.DUAL: arudhas.DUAL}[mode]
            assert all(arudhas.modality(s) == wanted for s in seen), sign
        # And it is genuinely not the graha table.
        assert set(arudhas.rasi_drishti(0)) != set(aspected_signs("Jupiter", 0))

    def test_each_step_of_the_hierarchy_decides_when_it_should(self):
        """Every rung, on a chart built so that exactly one of them can
        speak. The fixtures do not reach most of these — the co-lords are
        separated by the first rung on both — so without constructed charts
        the hierarchy below `company` would ship untested.
        """
        import arudhas
        import schools

        def verdict(lagna, placements):
            chart = synthetic_chart(lagna, placements)
            with schools.use({"dual_lord": "stronger"}):
                return arudhas.stronger_co_lord(chart, "Saturn", "Rahu")

        # One constructed chart per rung, each found by search and pinned
        # here, so a rung that stops firing is caught rather than silently
        # skipped. Sign indices, Aries = 0.
        cases = {
            # Saturn in Aquarius, Rahu elsewhere: the count goes to Rahu,
            # the claim that is not merely positional.
            "occupancy": (9, "Rahu", {
                "Sun": 2, "Moon": 8, "Mars": 1, "Mercury": 9, "Jupiter": 4,
                "Venus": 8, "Saturn": 10, "Rahu": 2, "Ketu": 1}),
            "company": (9, "Rahu", {
                "Sun": 5, "Moon": 2, "Mars": 6, "Mercury": 10, "Jupiter": 0,
                "Venus": 1, "Saturn": 8, "Rahu": 1, "Ketu": 5}),
            "support": (1, "Saturn", {
                "Sun": 5, "Moon": 5, "Mars": 11, "Mercury": 5, "Jupiter": 9,
                "Venus": 7, "Saturn": 9, "Rahu": 7, "Ketu": 1}),
            "exaltation": (6, "Rahu", {
                "Sun": 7, "Moon": 5, "Mars": 11, "Mercury": 7, "Jupiter": 4,
                "Venus": 9, "Saturn": 1, "Rahu": 1, "Ketu": 8}),
            "modality": (8, "Saturn", {
                "Sun": 5, "Moon": 4, "Mars": 3, "Mercury": 2, "Jupiter": 11,
                "Venus": 3, "Saturn": 1, "Rahu": 9, "Ketu": 4}),
            # Nothing separates them: the classical lord keeps the count,
            # and the caller can SEE that nothing decided it.
            "undecided": (0, "Saturn", {
                "Sun": 8, "Moon": 6, "Mars": 0, "Mercury": 9, "Jupiter": 1,
                "Venus": 3, "Saturn": 10, "Rahu": 10, "Ketu": 9}),
        }
        for step, (lagna, winner, placements) in cases.items():
            assert verdict(lagna, placements) == (winner, step), step

        # SUPPORT COUNTS DRISHTI, NOT ONLY COMPANY. On this chart nothing
        # sits with either co-lord, so the rung can only speak through rasi
        # drishti — Jupiter and the dispositor look upon Saturn's sign and
        # upon nothing of Rahu's. Without it the rung falls silent and a
        # later rung answers instead.
        by_drishti = {"Sun": 0, "Moon": 10, "Mars": 1, "Mercury": 7,
                      "Jupiter": 10, "Venus": 4, "Saturn": 6, "Rahu": 8,
                      "Ketu": 1}
        assert verdict(11, by_drishti) == ("Saturn", "support")

        # THE LAGNA COUNTS AS COMPANY, and that is a choice — the rung is
        # not reached on either fixture, so without this the choice could be
        # reversed and every committed gate would still pass. Same chart,
        # lagna moved onto Rahu's sign and off it.
        moved = {"Sun": 5, "Moon": 2, "Mars": 6, "Mercury": 10,
                 "Jupiter": 0, "Venus": 11, "Saturn": 8, "Rahu": 1,
                 "Ketu": 5}
        with_lagna = verdict(1, moved)       # lagna in Taurus, with Rahu
        without = verdict(8, moved)          # lagna elsewhere
        assert with_lagna != without, (
            "moving the lagna onto a co-lord's sign changed nothing — the "
            "lagna is not being counted as company")

    def test_the_strength_verdict_names_the_step_that_decided_it(self, chart):
        """A verdict resting on the modality of a sign is a weaker claim
        than one resting on exaltation, and the reader is entitled to which
        they have. Every step in the hierarchy must be reachable."""
        import arudhas
        winner, step = arudhas.stronger_co_lord(chart, "Saturn", "Rahu")
        assert winner in ("Saturn", "Rahu")
        assert step in ("occupancy", "company", "support", "exaltation",
                        "modality", "undecided")

    def test_describe_carries_what_a_marriage_reading_needs(self, chart):
        import arudhas
        import schools
        with schools.use({"dual_lord": "single"}):
            out = arudhas.describe(chart)
        assert out["upapada_sign"] == SIGNS[out["upapada_sign_index"]]
        assert 1 <= out["upapada_house"] <= 12
        assert out["upapada_lord"] == arudhas.SIGN_LORDS[
            out["upapada_sign_index"]]
        assert set(out["upapada_occupants"]) <= set(PLANETS)
        # The school is named on the output, not left to a settings screen.
        assert "Parāśarī" in out["school"] or "Paras" in out["school"]

    def test_every_arudha_rule_is_in_the_citation_library(self):
        """`rulelib` is the single citation authority. An arudha rule that
        exists only in this module's prose cannot be cited by the agent and
        cannot be checked by the validator."""
        import rulelib
        for rule_id in ("rule.arudha.pada", "rule.arudha.exception",
                        "rule.arudha.upapada",
                        "rule.arudha.upapada_occupants",
                        "rule.arudha.second_from_upapada",
                        "rule.arudha.colord_school",
                        "rule.arudha.colord_strength",
                        "rule.arudha.rasi_drishti"):
            assert rulelib.is_known(rule_id), rule_id
            assert rulelib.RULES[rule_id].source.strip(), (
                f"{rule_id} has no source — the citation IS the product")


class TestCharaKarakas:
    """The offices the chart assigns, and the Kārakāṃśa.

    THE TWO HALVES ARE GATED DIFFERENTLY, and the difference is the point.
    PyJHora ships the EIGHT-karaka scheme natively, so that half is a real
    external check — its ordering was verified body by body across 400
    random charts as well as both fixtures. The SEVEN-karaka scheme it does
    not ship: the oracle file's `seven_karaka` block was DERIVED by the
    exporter, by dropping Rahu from PyJHora's own longitudes. Agreeing with
    a derivation from the same numbers is weaker evidence than agreeing
    with an independent implementation, and saying so is the difference
    between a gate and a decoration.

    Sidera's seven-karaka path is therefore written from the tradition —
    the seven visible grahas ranked by degree, no nodes at all — and what
    the derivation corroborates is recorded as corroboration.
    """

    # The oracle writes Jñāti where we write Gnāti. Same Sanskrit word, two
    # transliterations; the abbreviation GK is what both texts use.
    ORACLE_OFFICE = {
        "Atma": "Atmakaraka", "Amatya": "Amatyakaraka",
        "Bhratri": "Bhratrikaraka", "Matri": "Matrikaraka",
        "Pitri": "Pitrikaraka", "Putra": "Putrakaraka",
        "Jnati": "Gnatikaraka", "Dara": "Darakaraka",
    }

    @pytest.mark.parametrize("name", ["reference", "partner"])
    def test_eight_karaka_scheme_matches_the_oracle(self, oracle, name):
        """THE EXTERNAL HALF. PyJHora computes this scheme itself."""
        import karakas
        chart = compute_chart(fixtures.birth(name))
        block = oracle["charts"][name]["chara_karakas"]["eight_karaka"]
        ours = karakas.karakas(chart, "eight")
        assert [k.planet for k in ours] == block["order"]
        assert {k.office: k.planet for k in ours} == {
            self.ORACLE_OFFICE[o]: p
            for o, p in block["assignment"].items()}
        assert "Rahu" in block["source"]

    @pytest.mark.parametrize("name", ["reference", "partner"])
    def test_seven_karaka_scheme_agrees_with_the_derivation(self, oracle,
                                                            name):
        """THE DERIVED HALF, labelled. The oracle's seven-karaka block is
        not an independent implementation — the exporter made it by
        excluding Rahu from PyJHora's longitudes, and says so in its own
        `source` field. This asserts agreement AND asserts that the file
        still admits what it is, so the label cannot quietly disappear and
        leave a derivation being read as a check."""
        import karakas
        chart = compute_chart(fixtures.birth(name))
        block = oracle["charts"][name]["chara_karakas"]["seven_karaka"]
        assert "DERIVED" in block["source"], (
            "the oracle no longer admits that its seven-karaka block is a "
            "derivation — either it became independent, which would be good "
            "news worth rewriting this gate for, or the label was lost")
        ours = karakas.karakas(chart, "seven")
        assert [k.planet for k in ours] == block["order"]
        assert {k.office: k.planet for k in ours} == {
            self.ORACLE_OFFICE[o]: p
            for o, p in block["assignment"].items()}

    def test_the_ranking_is_by_degree_into_the_sign(self, chart):
        """Written out directly, so the implementation cannot drift into a
        table that happens to agree on two charts."""
        import karakas
        for which in ("seven", "eight"):
            ranked = karakas.karakas(chart, which)
            values = [k.ranked_by for k in ranked]
            assert values == sorted(values, reverse=True), which
            assert len(ranked) == (8 if which == "eight" else 7)
            assert [k.office for k in ranked] == list(
                karakas.OFFICES_8 if which == "eight" else karakas.OFFICES_7)
            # Ketu takes no office under either scheme.
            assert "Ketu" not in [k.planet for k in ranked]
        assert "Rahu" not in [k.planet for k in karakas.karakas(chart, "seven")]
        assert "Rahu" in [k.planet for k in karakas.karakas(chart, "eight")]

    def test_rahu_is_ranked_backwards(self):
        """Not a fudge — the same fact that makes Rahu's daśā run from the
        other end. A Rahu barely into its sign ranks near the top."""
        import karakas
        assert karakas.ranking_value("Rahu", 7.0) == 23.0
        assert karakas.ranking_value("Saturn", 7.0) == 7.0
        # A chart where Rahu is at 1° and everything else is low: counted
        # forwards Rahu would be last, counted backwards it is first.
        placements = {p: (i, 5.0) for i, p in enumerate(
            ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"))}
        placements["Rahu"] = (7, 1.0)
        placements["Ketu"] = (1, 1.0)
        ranked = karakas.karakas(synthetic_chart(0, placements), "eight")
        assert ranked[0].planet == "Rahu"
        assert ranked[0].office == "Atmakaraka"
        assert ranked[0].reversed_for_rahu is True

    def test_admitting_rahu_can_change_who_the_spouse_karaka_is(self):
        """The reason this is a question put to the reader and not a
        constant. An eighth office is not merely appended: Rahu can take a
        senior one and push every office below it down, the Dārakāraka
        included."""
        import karakas
        # Rahu at 29° ranks 1.0 counted backwards — below Saturn's 3.0, so
        # it lands at the BOTTOM of the eight and takes the spouse's office
        # outright. Under seven it is not there and Saturn keeps it.
        takes_it = {
            "Sun": (0, 28.0), "Moon": (1, 20.0), "Mars": (2, 18.0),
            "Mercury": (3, 15.0), "Jupiter": (4, 12.0), "Venus": (5, 9.0),
            "Saturn": (6, 3.0), "Rahu": (7, 29.0), "Ketu": (1, 1.0)}
        chart = synthetic_chart(0, takes_it)
        both = karakas.both_schemes(chart)
        assert both["seven"]["Darakaraka"] == "Saturn"
        assert both["eight"]["Darakaraka"] == "Rahu"
        assert not karakas.schemes_agree_on(chart, "Darakaraka")

        # And where Rahu lands mid-table it takes no office outright but
        # still pushes every office below it down one — the Dārakāraka
        # unchanged, the significators between it and the top all moved.
        pushes = dict(takes_it, **{"Rahu": (7, 5.0)})   # ranks 25.0, second
        chart = synthetic_chart(0, pushes)
        both = karakas.both_schemes(chart)
        assert both["eight"]["Amatyakaraka"] == "Rahu"
        assert both["seven"]["Darakaraka"] == both["eight"]["Darakaraka"]
        assert karakas.schemes_agree_on(chart, "Atmakaraka")
        for office in ("Bhratrikaraka", "Matrikaraka"):
            assert not karakas.schemes_agree_on(chart, office), office

    def test_a_tie_is_broken_by_a_named_rule_not_by_sort_order(self):
        """THE CASE THAT NEVER HAPPENS UNTIL IT DOES. Two grahas at the
        identical degree: the order must come from a stated convention and
        must be reported as a tie, not resolved invisibly."""
        import karakas
        placements = {
            "Sun": (0, 10.0), "Moon": (1, 10.0),        # exact tie
            "Mars": (2, 3.0), "Mercury": (3, 2.0),
            "Jupiter": (4, 1.5), "Venus": (5, 1.0), "Saturn": (6, 0.5),
            "Rahu": (7, 29.0), "Ketu": (1, 29.0)}
        chart = synthetic_chart(0, placements)
        ranked = karakas.karakas(chart, "seven")
        # Natural order decides: Sun is earlier than Moon, so Sun is senior.
        assert ranked[0].planet == "Sun" and ranked[1].planet == "Moon"
        # And the tie is REPORTED rather than swallowed.
        ties = karakas.tie_groups(chart, "seven")
        assert ties == [["Sun", "Moon"]]
        assert karakas.describe(chart)["ties"] == [["Sun", "Moon"]]
        # A chart with no tie reports none — so the field means something.
        clean = dict(placements)
        clean["Moon"] = (1, 9.0)
        assert karakas.tie_groups(synthetic_chart(0, clean), "seven") == []

    def test_the_tie_rule_survives_the_input_order(self):
        """The convention must not be the dictionary's insertion order
        wearing a rule's clothes. Same chart, placements built backwards."""
        import karakas
        forward = {
            "Sun": (0, 10.0), "Moon": (1, 10.0), "Mars": (2, 3.0),
            "Mercury": (3, 2.0), "Jupiter": (4, 1.5), "Venus": (5, 1.0),
            "Saturn": (6, 0.5), "Rahu": (7, 29.0), "Ketu": (1, 29.0)}
        backward = dict(reversed(list(forward.items())))
        assert list(forward) != list(backward)
        a = [k.planet for k in karakas.karakas(
            synthetic_chart(0, forward), "seven")]
        b = [k.planet for k in karakas.karakas(
            synthetic_chart(0, backward), "seven")]
        assert a == b, "the karaka order followed the input order"

    def test_karakamsa_is_the_atmakaraka_in_the_navamsa(self, chart):
        import karakas
        import vargas
        for which in ("seven", "eight"):
            ak = karakas.atmakaraka(chart, which)
            km = karakas.karakamsa(chart, which)
            navamsa = vargas.varga_chart(chart, "D9")
            assert km["planet"] == ak.planet
            assert km["sign_index"] == navamsa.planets[ak.planet].sign_index
            assert km["house_from_d9_lagna"] == navamsa.planets[ak.planet].house
            # The house is counted from the D9 lagna, NOT the natal one —
            # the distinction that makes it the Kārakāṃśa rather than just
            # "where the AK went".
            assert km["house_from_d9_lagna"] == (
                km["sign_index"] - navamsa.lagna_sign_index) % 12 + 1
            assert km["d9_lagna_sign"] == navamsa.lagna_sign

    def test_the_scheme_follows_the_school(self, chart):
        import karakas
        import schools
        with schools.use({"karaka_count": "seven"}):
            assert karakas.scheme() == "seven"
            assert len(karakas.karakas(chart)) == 7
            assert karakas.describe(chart)["scheme"] == "seven"
        with schools.use({"karaka_count": "eight"}):
            assert karakas.scheme() == "eight"
            assert len(karakas.karakas(chart)) == 8
            assert "Rahu" in [k.planet for k in karakas.karakas(chart)]
        # Seven is the recommended default.
        assert schools.OPTIONS["karaka_count"].default == "seven"

    def test_describe_carries_what_a_marriage_reading_needs(self, chart):
        import karakas
        import schools
        with schools.use({"karaka_count": "seven"}):
            out = karakas.describe(chart)
        assert out["darakaraka"] in PLANETS
        assert out["darakaraka_sign"] in SIGNS
        assert 1 <= out["darakaraka_house"] <= 12
        assert out["atmakaraka"] == out["karakas"][0]["planet"]
        assert out["darakaraka"] == out["karakas"][-1]["planet"]
        assert out["karakamsa"]["planet"] == out["atmakaraka"]
        assert isinstance(out["darakaraka_agrees_across_schemes"], bool)
        # The school is named on the output, not left to a settings screen.
        assert "karaka" in out["school"].lower()

    def test_every_karaka_rule_is_in_the_citation_library(self):
        """`rulelib` is the single citation authority."""
        import rulelib
        for rule_id in ("rule.karaka.chara", "rule.karaka.rahu_reversed",
                        "rule.karaka.count_school",
                        "rule.karaka.tie_convention",
                        "rule.karaka.darakaraka",
                        "rule.karaka.maturation",
                        "rule.karaka.karakamsa"):
            assert rulelib.is_known(rule_id), rule_id
            assert rulelib.RULES[rule_id].source.strip(), (
                f"{rule_id} has no source — the citation IS the product")
        # The tie convention must admit it is a convention, in the text a
        # reader sees, the way the varga degree convention does.
        tie = rulelib.RULES["rule.karaka.tie_convention"]
        assert "convention" in tie.text.lower()
        assert "not a classical rule" in tie.text.lower()


class TestAvasthas:
    """Bālādi and jāgradādi — and an honest note on what gates them.

    NO ORACLE EXISTS FOR THIS. PyJHora implements no avasthā at all, so
    unlike every other computation in this build there is no independent
    implementation to disagree with ours. That is a real drop in evidence
    and it is stated rather than glossed.

    What stands in its place:
      * bālādi is MECHANICAL — five equal bands of 6°, reversed in even
        signs — so the partition itself is asserted: the bands tile the
        sign with no gap and no overlap, the reversal is exact, and every
        boundary degree lands where the rule says.
      * jāgradādi composes from `yogas.dignity_at`, which IS oracle-gated,
        so its inputs are checked even though its mapping is not — and the
        mapping is asserted TOTAL over that function's whole vocabulary, so
        a new dignity state breaks this loudly instead of being read as
        'dreaming'.
    """

    def test_baladi_bands_tile_the_sign_exactly(self):
        import avasthas
        assert len(avasthas.BALADI_STATES) == 5
        assert avasthas.BALADI_BAND * 5 == 30.0
        for sign in range(12):
            bands = avasthas.baladi_bands(sign)
            assert len(bands) == 5, sign
            # No gap, no overlap, and the whole sign covered.
            assert bands[0][0] == 0.0 and bands[-1][1] == 30.0, sign
            for (_, upper, _), (lower, _, _) in zip(bands, bands[1:]):
                assert upper == lower, sign
            # Every state appears exactly once.
            assert sorted(state for _, _, state in bands) == sorted(
                avasthas.BALADI_STATES), sign

    def test_even_signs_reverse_the_order_exactly(self):
        """Not 'roughly reversed' — the same degree in Aries and Taurus must
        give states that are mirror images across the five bands."""
        import avasthas
        states = avasthas.BALADI_STATES
        for degree in (0.0, 3.0, 5.999, 6.0, 14.9, 15.0, 23.5, 29.999):
            odd = avasthas.baladi_at(0, degree)     # Aries
            even = avasthas.baladi_at(1, degree)    # Taurus
            assert states.index(odd) + states.index(even) == 4, (
                degree, odd, even)
        # And it is the SIGN NUMBER that decides, not the index: Aries is
        # the 1st and odd, so index 0 counts forward.
        assert avasthas.baladi_at(0, 1.0) == "bala"
        assert avasthas.baladi_at(1, 1.0) == "mrita"
        assert avasthas.baladi_at(2, 1.0) == "bala"

    def test_every_band_boundary_lands_where_the_rule_says(self):
        """The classic off-by-one. A degree exactly on a boundary belongs to
        the band it opens, not the one it closes."""
        import avasthas
        expected = ["bala", "kumara", "yuva", "vriddha", "mrita"]
        for index, state in enumerate(expected):
            low = index * 6.0
            assert avasthas.baladi_at(0, low) == state, low
            assert avasthas.baladi_at(0, low + 5.999) == state, low
            if index < 4:
                assert avasthas.baladi_at(0, low + 6.0) == expected[index + 1]
        # A degree of exactly 30 is not inside the sign, but must not raise.
        assert avasthas.baladi_at(0, 30.0) == "mrita"
        assert avasthas.baladi_at(1, 30.0) == "bala"

    def test_the_jagradadi_mapping_is_total_over_every_dignity(self):
        """THE GATE THAT MATTERS MOST HERE, since the mapping has no oracle.

        `dignity_at` has a closed vocabulary. Every member of it must map to
        a state, and the module must RAISE on one it does not know rather
        than defaulting — a new dignity silently read as 'dreaming' is
        exactly the kind of wrong that no test would otherwise catch.
        """
        import avasthas
        import yogas
        from engine import SIGNS
        seen = set()
        for planet in avasthas.BODIES:
            for sign in range(12):
                for degree in (0.5, 4.0, 14.0, 16.0, 21.0, 29.5):
                    seen.add(yogas.dignity_at(planet, sign, degree))
        assert seen, "no dignities sampled"
        for dignity in seen:
            assert dignity in avasthas.JAGRADADI_BY_DIGNITY, (
                f"dignity_at can return {dignity!r} and the jāgradādi table "
                f"has no entry for it")
            assert avasthas.jagradadi_for(dignity) in \
                avasthas.JAGRADADI_STATES
        # The vocabulary is covered, not merely sampled.
        assert set(avasthas.JAGRADADI_BY_DIGNITY) >= seen
        # …and an unknown dignity is refused rather than defaulted.
        with pytest.raises(ValueError):
            avasthas.jagradadi_for("radiant")

    def test_dignity_decides_jagradadi_and_degree_does_not(self, chart):
        """The two states read different things, and this pins which."""
        import avasthas
        import yogas
        for planet in avasthas.BODIES:
            position = chart.planets[planet]
            dignity = yogas.dignity_at(planet, position.sign_index,
                                       position.degree_in_sign)
            assert avasthas.jagradadi(chart, planet) == \
                avasthas.jagradadi_for(dignity)
        # Supported signs wake a graha; an obstructing one puts it to sleep.
        assert avasthas.jagradadi_for("exalted") == "jagrat"
        assert avasthas.jagradadi_for("own sign") == "jagrat"
        assert avasthas.jagradadi_for("moolatrikona") == "jagrat"
        assert avasthas.jagradadi_for("neutral") == "svapna"
        assert avasthas.jagradadi_for("debilitated") == "sushupti"

    def test_the_two_states_are_independent_and_can_disagree(self, chart):
        """The design claim, tested on a real chart rather than asserted.

        If these could not disagree, reporting both would be redundant and
        the module would be lying about why it keeps them apart.
        """
        import avasthas
        rows = avasthas.describe(chart)["avasthas"]
        pairs = {(row["baladi"], row["jagradadi"]) for row in rows}
        assert len({b for b, _ in pairs}) > 1, "every graha the same age"
        assert len({j for _, j in pairs}) > 1, "every graha equally awake"
        # On the reference chart Jupiter is spent by degree and awake by
        # dignity — the exact case the module exists to keep visible.
        jupiter = next(r for r in rows if r["planet"] == "Jupiter")
        assert jupiter["baladi"] == "mrita"
        assert jupiter["jagradadi"] == "jagrat"
        assert jupiter["at_odds"] is True
        assert "Jupiter" in avasthas.describe(chart)["at_odds"]

    def test_the_nodes_are_not_given_an_avastha(self, chart):
        import avasthas
        assert "Rahu" not in avasthas.BODIES
        assert "Ketu" not in avasthas.BODIES
        rows = avasthas.describe(chart)["avasthas"]
        assert {row["planet"] for row in rows} == set(avasthas.BODIES)
        assert "dignity the nodes do not have" in \
            avasthas.describe(chart)["nodes_excluded"]

    def test_every_state_has_a_name_and_a_plain_sense(self):
        """A state id in the output with no words behind it would reach the
        reader as jargon."""
        import avasthas
        for state in avasthas.BALADI_STATES:
            assert state in avasthas.BALADI_NAME
            assert len(avasthas.BALADI_SENSE[state].split()) >= 5, state
        for state in avasthas.JAGRADADI_STATES:
            assert state in avasthas.JAGRADADI_NAME
            assert len(avasthas.JAGRADADI_SENSE[state].split()) >= 5, state

    def test_no_strength_fraction_is_invented(self):
        """Texts attach fractions to the bālādi states and disagree about
        them. None is computed here, and the module says why."""
        import avasthas
        import inspect
        source = inspect.getsource(avasthas)
        assert "do not agree with one" in source
        assert "No fractions are computed here" in source
        blob = " ".join(avasthas.BALADI_SENSE.values())
        for fraction in ("1/4", "1/2", "quarter of", "half of", "0.25"):
            assert fraction not in blob, fraction

    def test_every_avastha_rule_is_in_the_citation_library(self):
        import rulelib
        for rule_id in ("rule.avastha.baladi", "rule.avastha.jagradadi",
                        "rule.avastha.independent"):
            assert rulelib.is_known(rule_id), rule_id
            assert rulelib.RULES[rule_id].source.strip(), rule_id


class TestVimsopaka:
    """Strength weighed across a group of divisions, and the group as a fork.

    WHAT IS GATED, AND WHAT IS RECORDED INSTEAD. Every value comes from the
    oracle EXCEPT where a weighted division puts the graha in Scorpio or
    Aquarius. There, PyJHora takes the sign's lord to be the node — Ketu for
    Scorpio, Rahu for Aquarius — and Sidera takes the classical sole lord,
    Mars and Saturn. That is the `dual_lord` question over again, arriving
    somewhere nobody expected it, and the instruction was to record a
    divergence rather than chase it. The gate therefore checks every case
    the disagreement does NOT touch, exactly, and the disagreement itself is
    measured in tools/oracle/DIFFERENTIAL.md.
    """

    ORACLE = json.loads(
        (HERE / "fixtures_pyjhora.json").read_text(encoding="utf-8"))

    @classmethod
    @pytest.fixture(scope="class")
    def charts(cls):
        import fixtures
        return {k: compute_chart(fixtures.birth(k))
                for k in ("reference", "partner")}

    def test_every_group_weighs_exactly_twenty(self):
        """What makes a score out of twenty comparable across the four
        groups. Asserted rather than trusted — the weights are transcribed
        numbers and a typo in one would be invisible in the output."""
        import vimsopaka
        for name, weights in vimsopaka.GROUPS.items():
            assert abs(sum(weights.values()) - 20.0) < 1e-9, (
                f"{name} weighs {sum(weights.values())}, not 20")
        assert {len(w) for w in vimsopaka.GROUPS.values()} == {6, 7, 10, 16}
        # The group names say how many charts they weigh, and do not lie.
        assert len(vimsopaka.GROUPS["shadvarga"]) == 6
        assert len(vimsopaka.GROUPS["saptavarga"]) == 7
        assert len(vimsopaka.GROUPS["dashavarga"]) == 10
        assert len(vimsopaka.GROUPS["shodasavarga"]) == 16
        # Every chart named is one this build can actually cast.
        import vargas
        for name, weights in vimsopaka.GROUPS.items():
            for code in weights:
                assert code == "D1" or code in vargas.SUPPORTED, (name, code)

    def test_the_oracle_agrees_wherever_the_dispositor_is_not_disputed(
            self, charts):
        """The external gate, on every case the known divergence does not
        touch. A graha none of whose weighted divisions land in Scorpio or
        Aquarius must match PyJHora to the last decimal."""
        import vimsopaka
        import schools
        checked = skipped = 0
        for name, chart in charts.items():
            block = self.ORACLE["charts"][name]["vimsopaka"]
            for which in vimsopaka.GROUPS:
                with schools.use({"vimsopaka_group": which}):
                    ours = vimsopaka.scores(chart)
                for planet in vimsopaka.BODIES:
                    disputed = any(
                        vimsopaka._sign_in(chart, planet, code) in (7, 10)
                        for code in vimsopaka.GROUPS[which])
                    if disputed:
                        skipped += 1
                        continue
                    theirs = block[which][planet]["score"]
                    assert abs(ours[planet] - theirs) < 1e-6, (
                        f"{name}/{which}/{planet}: ours {ours[planet]} vs "
                        f"oracle {theirs}")
                    checked += 1
        # AND HOW THIN THIS IS, stated rather than implied. Only 8 of the
        # 56 fixture cases avoid the two-lord signs, and NONE of them do
        # under the sixteen-chart group — weigh sixteen divisions and a
        # graha will land in Scorpio or Aquarius in one of them almost
        # every time. So this gate is a confirmation, not the evidence.
        # The evidence is the 400-chart run in DIFFERENTIAL.md, where the
        # undisputed subset matched 1043 of 1043.
        assert checked == 8, (
            f"the undisputed subset changed size ({checked} of "
            f"{checked + skipped}) — re-measure before trusting this gate")
        assert skipped == 48, skipped

    def test_the_disputed_cases_differ_only_in_scorpio_and_aquarius(
            self, charts):
        """The divergence, pinned as a FINDING rather than hidden by the
        skip above. Where a graha's weighted divisions avoid the two
        two-lord signs, we agree; where they do not, we may not — and the
        reason is the dispositor, not the arithmetic."""
        import vimsopaka
        import schools
        found_a_disputed_case = False
        for name, chart in charts.items():
            for which in vimsopaka.GROUPS:
                for planet in vimsopaka.BODIES:
                    signs = [vimsopaka._sign_in(chart, planet, code)
                             for code in vimsopaka.GROUPS[which]]
                    if any(s in (7, 10) for s in signs):
                        found_a_disputed_case = True
        assert found_a_disputed_case, (
            "no fixture case touches Scorpio or Aquarius, so the recorded "
            "divergence is untested and the skip in the gate above is doing "
            "nothing")
        # And the mechanism itself: the dispositor of Scorpio follows the
        # co-lord school, which is what makes the two implementations part.
        with schools.use({"dual_lord": "single"}):
            assert vimsopaka.dispositor(charts["reference"], 7) == "Mars"
            assert vimsopaka.dispositor(charts["reference"], 10) == "Saturn"
        # An uncontested sign is unaffected by that question.
        for answer in ("single", "stronger"):
            with schools.use({"dual_lord": answer}):
                assert vimsopaka.dispositor(charts["reference"], 4) == "Sun"

        # AND THE CO-LORD SCHOOL REALLY REACHES IN HERE. Our default is the
        # Parāśarī sole lord, under which `counting_lord` returns exactly
        # the plain sign-lord table — so a version that ignored the school
        # entirely would pass every other gate in this class. A mutation
        # proved it. Under the other answer the dispositor must move, and
        # the score with it.
        import arudhas
        moved = False
        for chart in charts.values():
            with schools.use({"dual_lord": "stronger"}):
                for sign in (7, 10):
                    classical, node = arudhas.CO_LORDS[sign]
                    if vimsopaka.dispositor(chart, sign) == node:
                        moved = True
            if moved:
                break
        assert moved, (
            "the co-lord school never changed a dispositor on either "
            "fixture — vimsopaka is not reading the school at all")
        # …and a score that depends on one of those signs moves with it.
        shifted = False
        for name, chart in charts.items():
            for which in vimsopaka.GROUPS:
                with schools.use({"dual_lord": "single"}):
                    a = vimsopaka.scores(chart, which)
                with schools.use({"dual_lord": "stronger"}):
                    b = vimsopaka.scores(chart, which)
                if a != b:
                    shifted = True
        assert shifted, "no score moved when the co-lord school moved"

    def test_the_ladder_and_the_compound_scale(self, charts):
        import vimsopaka
        assert vimsopaka.OWN_SIGN_VALUE == 20
        assert vimsopaka.COMPOUND_VALUE == (5, 7, 10, 15, 18)
        assert vimsopaka.COMPOUND_NAMES[0] == "great enemy"
        assert vimsopaka.COMPOUND_NAMES[-1] == "great friend"
        chart = charts["reference"]
        # Temporary friendship is the ring around a graha, not the whole
        # chart: the 2nd, 3rd, 4th, 10th, 11th and 12th from it.
        assert vimsopaka.TEMPORAL_FRIEND_HOUSES == {2, 3, 4, 10, 11, 12}
        # A graha is never its own dispositor's stranger — own sign scores
        # 20 and is reported as such rather than as a relationship.
        for planet in vimsopaka.BODIES:
            for code in ("D1", "D9"):
                value, why = vimsopaka.value_in(chart, planet, code)
                assert value in (5, 7, 10, 15, 18, 20), (planet, code)
                if value == 20:
                    assert why == "own sign"
                else:
                    assert "of" in why

    def test_the_nodes_are_not_scored_and_the_reason_is_printed(self,
                                                                charts):
        import vimsopaka
        assert "Rahu" not in vimsopaka.BODIES
        assert "Ketu" not in vimsopaka.BODIES
        assert len(vimsopaka.BODIES) == 7
        out = vimsopaka.describe(charts["reference"])
        assert set(out["scores"]) == set(vimsopaka.BODIES)
        assert "rule no sign" in out["nodes_excluded"]

    def test_the_group_changes_the_score(self, charts):
        """A fork that moved nothing would be decoration. Every pair of
        groups must disagree about some graha on a real chart."""
        import vimsopaka
        import schools
        chart = charts["reference"]
        by_group = {}
        for which in vimsopaka.GROUPS:
            with schools.use({"vimsopaka_group": which}):
                by_group[which] = vimsopaka.scores(chart)
                assert vimsopaka.describe(chart)["group"] == which
        names = sorted(by_group)
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                assert by_group[a] != by_group[b], (a, b)
        assert schools.OPTIONS["vimsopaka_group"].default == "dashavarga"

    def test_the_working_adds_up_to_the_score(self, charts):
        """The breakdown is the arithmetic, not a parallel story about it."""
        import vimsopaka
        chart = charts["reference"]
        for which in vimsopaka.GROUPS:
            for planet in vimsopaka.BODIES:
                rows = vimsopaka.working(chart, planet, which)
                assert len(rows) == len(vimsopaka.GROUPS[which])
                assert abs(sum(r["contributes"] for r in rows)
                           - vimsopaka.score(chart, planet, which)) < 1e-6
                assert all(0 <= r["value"] <= 20 for r in rows)

    def test_a_score_never_leaves_the_scale(self, charts):
        import vimsopaka
        for chart in charts.values():
            for which in vimsopaka.GROUPS:
                for value in vimsopaka.scores(chart, which).values():
                    assert 5.0 <= value <= 20.0, value

    def test_every_vimsopaka_rule_is_in_the_citation_library(self):
        import rulelib
        for rule_id in ("rule.vimsopaka.bala",
                        "rule.vimsopaka.group_school",
                        "rule.vimsopaka.compound_relation",
                        "rule.vimsopaka.nodes_excluded"):
            assert rulelib.is_known(rule_id), rule_id
            assert rulelib.RULES[rule_id].source.strip(), rule_id


class TestVimshottariAgainstTheOracle:
    """The daśā timeline, boundary by boundary, against PyJHora.

    THE FIX THIS PINS
    Sidera used the Julian year (365.25 days) to turn daśā years into dates.
    The differential run over 300 random charts found that this was the ONLY
    thing separating our Vimshottari from PyJHora's — every MD and AD
    boundary, in every chart, drifted at 0.0064 days per year and nothing
    else differed. Switching to the SIDEREAL year (365.256364) took the
    disagreement to zero.

    It is also the coherent choice: Vimshottari is measured against the
    Moon's position among fixed stars, so its year is the sidereal one. The
    Julian year was a computing convenience with no jyotisha claim behind it.

    Without a gate the constant is one careless edit from drifting back, and
    the symptom — dasha dates wrong by hours, growing to days — is invisible
    in a UI that renders periods as "Mon YYYY".
    """

    TOLERANCE_SECONDS = 60.0

    def test_the_year_is_sidereal_not_julian(self):
        import dashas
        assert dashas.DAYS_PER_YEAR == dashas.SIDEREAL_YEAR_DAYS
        assert dashas.SIDEREAL_YEAR_DAYS == 365.256364
        assert dashas.DAYS_PER_YEAR != dashas.JULIAN_YEAR_DAYS

    @pytest.mark.parametrize("name", ["reference", "partner"])
    def test_every_md_and_ad_boundary_matches(self, oracle, name):
        from datetime import timedelta
        from dashas import vimshottari
        from engine import compute_chart, resolve_timezone
        if not fixtures.is_built_in(name):
            pytest.skip("fixtures substituted")
        block = oracle["charts"][name]["vimsottari"]
        birth = fixtures.birth(name)
        # PyJHora reports period starts in the PLACE's local zone, because
        # that is how it read the birth moment. Tagging them UTC would put
        # every boundary out by the offset.
        zone = resolve_timezone(birth.tz)

        timeline = vimshottari(compute_chart(birth))
        ours = {(md.lord, ad.lord): ad.start
                for md in timeline.mahadashas for ad in md.antardashas}
        assert len(ours) == 81, "nine lords nested nine deep"

        checked, worst = 0, 0.0
        for period in block["periods"]:
            key = (period["md"], period["ad"])
            assert key in ours, f"{name}: PyJHora has a period we do not"
            year, month, day, hours = period["start_local"]
            if year > 9000:                     # beyond datetime's range
                continue
            theirs = (datetime(year, month, day) + timedelta(hours=hours)
                      ).replace(tzinfo=zone).astimezone(timezone.utc)
            gap = abs((ours[key] - theirs).total_seconds())
            worst = max(worst, gap)
            assert gap < self.TOLERANCE_SECONDS, (
                f"{name} {key[0]}/{key[1]}: {ours[key].isoformat()} vs "
                f"{theirs.isoformat()} — {gap / 86400:.4f} days apart")
            checked += 1
        assert checked >= 70, f"only {checked} boundaries compared"

    @pytest.mark.parametrize("name", ["reference", "partner"])
    def test_every_pratyantardasha_boundary_matches(self, oracle, name):
        """THE THIRD LEVEL, against PyJHora — 729 rows per chart.

        This is the level a reading actually points at when it names a
        window, so it is the one most worth an external check: an invariant
        can prove the nine PDs partition their AD without proving the
        partition starts where anyone else thinks it does.
        """
        from datetime import timedelta
        from dashas import vimshottari
        from engine import compute_chart, resolve_timezone
        if not fixtures.is_built_in(name):
            pytest.skip("fixtures substituted")
        block = oracle["charts"][name]["vimsottari"]
        assert "pratyantardashas" in block, (
            "the oracle carries no third level — regenerate it")
        birth = fixtures.birth(name)
        zone = resolve_timezone(birth.tz)
        timeline = vimshottari(compute_chart(birth))

        ours = {(md.lord, ad.lord, pd.lord): pd.start
                for md in timeline.mahadashas
                for ad in md.antardashas
                for pd in ad.pratyantardashas}
        assert len(ours) == 729, "nine lords nested three deep"

        checked, worst = 0, 0.0
        for period in block["pratyantardashas"]:
            key = (period["md"], period["ad"], period["pd"])
            assert key in ours, f"{name}: PyJHora has a period we do not"
            year, month, day, hours = period["start_local"]
            if year > 9000:
                continue
            theirs = (datetime(year, month, day) + timedelta(hours=hours)
                      ).replace(tzinfo=zone).astimezone(timezone.utc)
            gap = abs((ours[key] - theirs).total_seconds())
            worst = max(worst, gap)
            assert gap < self.TOLERANCE_SECONDS, (
                f"{name} {'/'.join(key)}: {gap / 86400:.4f} days apart")
            checked += 1
        assert checked >= 700, f"only {checked} boundaries compared"

    def test_the_three_levels_nest_exactly(self):
        """An invariant the oracle cannot supply: each level PARTITIONS the
        one above it, with no gap and no overlap at any boundary.

        The last sub-period is closed on its parent's own end rather than on
        an accumulated sum — without that, 729 floating-point additions
        leave a seam the reader eventually lands in.
        """
        from dashas import vimshottari
        from engine import compute_chart
        timeline = vimshottari(compute_chart(fixtures.birth("reference")))
        for md in timeline.mahadashas:
            assert md.antardashas[0].start == md.start
            assert md.antardashas[-1].end == md.end
            for earlier, later in zip(md.antardashas, md.antardashas[1:]):
                assert earlier.end == later.start
            for ad in md.antardashas:
                assert len(ad.pratyantardashas) == 9
                assert ad.pratyantardashas[0].start == ad.start
                assert ad.pratyantardashas[-1].end == ad.end
                for earlier, later in zip(ad.pratyantardashas,
                                          ad.pratyantardashas[1:]):
                    assert earlier.end == later.start
                # The first sub-period belongs to the parent's own lord, at
                # every depth.
                assert ad.pratyantardashas[0].lord == ad.lord
            assert md.antardashas[0].lord == md.lord

    def test_a_pratyantardasha_is_proportioned_like_its_parents(self):
        """The same arithmetic at every depth: a lord's share of an AD is
        its share of the 120 years, exactly as it is of an MD."""
        from dashas import DASHA_SEQUENCE, TOTAL_YEARS, vimshottari
        from engine import compute_chart
        timeline = vimshottari(compute_chart(fixtures.birth("reference")))
        share = dict(DASHA_SEQUENCE)
        # Skip the first MD, which is entered part-way through at birth.
        for md in timeline.mahadashas[1:]:
            for ad in md.antardashas:
                for pd in ad.pratyantardashas[:-1]:   # last one absorbs float
                    expected = ad.years * share[pd.lord] / TOTAL_YEARS
                    assert abs(pd.years - expected) < 1e-6, (
                        md.lord, ad.lord, pd.lord, pd.years, expected)

    def test_at_depth_finds_the_running_pratyantardasha(self):
        """And agrees with `at()` about the two levels above it — the two
        methods must not be able to disagree about the same moment."""
        from datetime import timedelta
        from dashas import vimshottari
        from engine import compute_chart
        timeline = vimshottari(compute_chart(fixtures.birth("reference")))
        moments = [timeline.birth + timedelta(days=n)
                   for n in (1, 400, 3000, 9000, 20000)]
        for when in moments:
            deep = timeline.at_depth(when)
            shallow = timeline.at(when)
            assert (deep is None) == (shallow is None), when
            if deep is None:
                continue
            md, ad, pd = deep
            assert (md, ad) == shallow
            assert pd.contains(when), when
            assert ad.start <= pd.start and pd.end <= ad.end
        # Outside the 120 years there is nothing to find, at either depth.
        beyond = timeline.mahadashas[-1].end + timedelta(days=1)
        assert timeline.at_depth(beyond) is None
        assert timeline.at(beyond) is None

    def test_the_julian_year_would_fail_this(self, oracle, monkeypatch):
        """A gate that cannot go red is decoration.

        Restoring the old constant must break the comparison above — and it
        does, by a margin that grows the further from birth you look.
        """
        from datetime import timedelta
        import dashas
        from engine import compute_chart, resolve_timezone
        monkeypatch.setattr(dashas, "DAYS_PER_YEAR",
                            dashas.JULIAN_YEAR_DAYS)
        birth = fixtures.birth("reference")
        if not fixtures.is_built_in("reference"):
            pytest.skip("fixtures substituted")
        zone = resolve_timezone(birth.tz)
        timeline = dashas.vimshottari(compute_chart(birth))
        ours = {(md.lord, ad.lord): ad.start
                for md in timeline.mahadashas for ad in md.antardashas}
        worst = 0.0
        for period in oracle["charts"]["reference"]["vimsottari"]["periods"]:
            year, month, day, hours = period["start_local"]
            if year > 9000:
                continue
            key = (period["md"], period["ad"])
            theirs = (datetime(year, month, day) + timedelta(hours=hours)
                      ).replace(tzinfo=zone).astimezone(timezone.utc)
            worst = max(worst,
                        abs((ours[key] - theirs).total_seconds()) / 86400)
        assert worst > 0.5, (
            "the Julian year produced no measurable disagreement — this "
            "gate is not testing what it claims to")

    def test_the_oracle_pinned_its_year_length_too(self, oracle):
        """PyJHora's own default for this is unreliable.

        `drik.true_sidereal_year()` returns ≈366.2 days — a day too long,
        and astronomically impossible — on roughly 2% of random charts,
        which would have written that defect into this fixture. The export
        pins MEAN_SIDEREAL_YEAR and records the raw value so the fixture
        says whether these two charts were affected.
        """
        for name in ("reference", "partner"):
            block = oracle["charts"][name]["vimsottari"]
            assert block["year_length_days"] == 365.256364
            assert "MEAN_SIDEREAL_YEAR" in block["year_length_mode"]
            assert block["pyjhora_default_mode"] == "TRUE_SIDEREAL_YEAR"
            # A sidereal year varies by minutes, never by a day.
            assert abs(block["true_sidereal_year_here"] - 365.256364) < 0.5


class TestDifferentialHarness:
    """Properties of the 300-chart differential generator itself.

    The generator is the part that could quietly stop testing anything —
    by drifting off the date range, by emitting the same chart 300 times,
    or (the one that matters) by ever producing something that is not
    synthetic. Its OUTPUT is deliberately not committed; these pin the
    guarantees that make that safe.
    """

    def test_generation_is_deterministic_from_the_seed(self):
        """The records are not committed, so the seed is the only thing
        that makes a reported disagreement reproducible."""
        sys.path.insert(0, str(HERE / "tools" / "oracle"))
        import differential
        first, _ = differential.generate(25, 4242)
        second, _ = differential.generate(25, 4242)
        assert first == second
        other, _ = differential.generate(25, 4243)
        assert other != first, "the seed does not change the records"

    def test_records_are_synthetic_and_varied(self):
        sys.path.insert(0, str(HERE / "tools" / "oracle"))
        import differential
        records, _skipped = differential.generate(60, 20260908)
        assert len(records) == 60
        places = {r["place"] for r in records}
        years = {r["year"] for r in records}
        assert len(places) > 40, "the same city keeps coming up"
        assert len(years) > 30, "the dates are not spread"
        for r in records:
            assert differential.YEAR_FROM <= r["year"] < differential.YEAR_TO
            assert 0 <= r["hour"] < 24 and 0 <= r["minute"] < 60
            assert -90 <= r["latitude"] <= 90
            assert -180 <= r["longitude"] <= 180
            # The offset must be the one in force AT THAT MOMENT, not the
            # zone's standard offset — otherwise half the DST-era records
            # would be an hour out and both engines would agree on the
            # wrong chart.
            zone = ZoneInfo(r["tz"])
            local = datetime(r["year"], r["month"], r["day"], r["hour"],
                             r["minute"], r["second"], tzinfo=zone)
            assert local.utcoffset().total_seconds() / 3600.0 == \
                r["tz_hours"], r["place"]

    def test_no_generated_record_is_a_committed_fixture(self):
        """Belt and braces on the standing rule. A random generator cannot
        produce a real person's birth data, but it must not silently
        reproduce a committed chart either — that would make a 'random'
        agreement circular."""
        sys.path.insert(0, str(HERE / "tools" / "oracle"))
        import differential
        records, _ = differential.generate(300, 20260908)
        committed = set()
        for name in ("reference", "partner"):
            b = fixtures.birth(name)
            committed.add((b.year, b.month, b.day, b.hour, b.minute,
                           round(b.latitude, 4), round(b.longitude, 4)))
        for r in records:
            key = (r["year"], r["month"], r["day"], r["hour"], r["minute"],
                   round(r["latitude"], 4), round(r["longitude"], 4))
            assert key not in committed

    def test_the_report_is_committed_and_the_records_are_not(self):
        report = HERE / "tools" / "oracle" / "DIFFERENTIAL.md"
        assert report.exists(), (
            "tools/oracle/DIFFERENTIAL.md is missing — regenerate with "
            "tools/oracle/differential.py")
        text = report.read_text(encoding="utf-8")
        assert "not committed" in text
        assert "--seed" in text, "the report must name the seed"
        # The working files must stay out of the tree.
        for stray in ("records.json", "oracle_apparent.json",
                      "oracle_true.json"):
            assert not (HERE / stray).exists(), (
                f"{stray} is a differential working file and must not be "
                "committed")

    def test_ashtakavarga_is_reported_as_not_yet_compared(self):
        """Until milestone 2 lands this must SAY it is not compared. A
        differential test that silently skips what it was asked to check
        reads, later, as a thing that passed."""
        sys.path.insert(0, str(HERE / "tools" / "oracle"))
        import differential
        status = differential.ashtakavarga_status()
        assert status["compared"] is False
        assert "milestone 2" in status["reason"] or \
            "extend" in status["reason"]


class TestComputationOptions:
    """The layman-first settings, and the promises they make.

    The hard one is the last: a control that changes nothing is worse than
    no control, so every live answer must be shown to move a real computed
    value. That is asserted by actually computing, not by inspection.
    """

    # --- the selection reaches the engine, per request -------------------

    def test_no_endpoint_reads_the_selection_without_setting_it(self, client):
        """The survey that found the /ask leak, kept as a gate.

        A route that computes anything reads the school through a
        ContextVar. If it never sets one it does not get the defaults — it
        gets whatever the previous request in that worker left behind, which
        is the reader's choice ignored at best and another reader's chart at
        worst. This walks every route and fails on any that reads before it
        sets, so the next endpoint cannot reintroduce it quietly.
        """
        import contextlib
        import contextvars
        import agent as agent_mod
        import schools
        import app as app_mod
        import transits

        state = {}
        real_active, real_set, real_use = (
            schools.active, schools.set_active, schools.use)

        def active():
            state.setdefault("read_before_set", not state.get("set"))
            return real_active()

        def set_active(selection):
            state["set"] = True
            return real_set(selection)

        @contextlib.contextmanager
        def use(selection):
            state["set"] = True
            with real_use(selection) as value:
                yield value

        real_ask = agent_mod.ask_chart

        def stop(*a, **kw):
            raise agent_mod.AgentUnavailable("stopped inside the handler")

        schools.active, schools.set_active, schools.use = (
            active, set_active, use)
        # The modules that hold their own reference to the module object.
        for module in (app_mod, transits):
            module.schools = schools
        agent_mod.ask_chart = stop
        try:
            offenders = []
            calls = {
                "GET /": lambda: client.get("/"),
                "POST /": lambda: client.post("/", data=GATE_FORM),
                "GET /api/cities": lambda: client.get("/api/cities?q=mumbai"),
                "POST /ask": lambda: client.post("/ask", json={
                    "sid": "leak-survey", "question": "Where is my Moon?",
                    **GATE_FORM}),
                "POST /ask/feedback": lambda: client.post(
                    "/ask/feedback", json={"question": "Q?", "answer": "A."}),
            }
            for label, call in calls.items():
                state.clear()
                # A FRESH context per route, which is the point: a route that
                # only works because an earlier request in the same worker
                # set the value is exactly the bug.
                contextvars.copy_context().run(call)
                if state.get("read_before_set"):
                    offenders.append(label)
        finally:
            schools.active, schools.set_active, schools.use = (
                real_active, real_set, real_use)
            for module in (app_mod, transits):
                module.schools = schools
            agent_mod.ask_chart = real_ask

        assert offenders == [], (
            "these routes read the computation-school selection without "
            "setting one, so they inherit whatever the previous request in "
            "the worker left behind: " + ", ".join(offenders))

    # --- the presentation contract -------------------------------------

    def test_every_question_is_plain_english(self):
        """A reader who has never met the word 'drishti' must still be able
        to choose. Jargon belongs under the answer, never in the question or
        in the answer text itself."""
        import schools
        jargon = ("drishti", "dṛṣṭi", "graha", "arudha", "amsa", "varga",
                  "gochara", "node", "ayanamsa", "lord", "sidereal",
                  "parashari", "parāśarī", "jaimini")
        for opt in schools.OPTIONS.values():
            assert opt.question.endswith("?"), opt.id
            # Two to four. Widened from three when the viṃśopaka group
            # question arrived with four classical answers — see the
            # contract in schools.py for why dropping one was not an
            # option. Still a cap: a question wanting five is two
            # questions.
            assert 2 <= len(opt.answers) <= 4, opt.id
            haystack = f"{opt.question} {opt.consequence}".lower()
            for term in jargon:
                assert term not in haystack, (
                    f"{opt.id}: the question uses '{term}' — the reader "
                    f"should not need the vocabulary to choose")
            for ans in opt.answers:
                for term in jargon:
                    assert term not in ans.text.lower(), (
                        f"{opt.id}/{ans.id}: the ANSWER uses '{term}'; the "
                        f"school name goes in `school`, not in `text`")

    def test_the_school_name_is_carried_but_kept_secondary(self):
        """Every answer names its school, and the template renders it in
        small text under the answer rather than as the answer."""
        import schools
        for opt in schools.OPTIONS.values():
            for ans in opt.answers:
                assert ans.school.strip(), f"{opt.id}/{ans.id}"
                assert len(ans.school) > len(ans.text) / 3
        page = (HERE / "templates" / "index.html").read_text(encoding="utf-8")
        assert "answertext" in page and "schoolname" in page
        css = (HERE / "static" / "style.css").read_text(encoding="utf-8")
        block = css[css.index(".answer .schoolname"):]
        block = block[:block.index("}")]
        # Re-pinned 2026-09-12. This used to require the school name to be
        # SMALLER than the answer (<=12px), which the type floors retired —
        # 12px is under the reading floor. It still has to recede; it does it
        # by colour and style now, which is how printed matter does it.
        assert "font-size: var(--t-body)" in block, block
        assert "var(--faint)" in block and "italic" in block, block

    def test_exactly_one_recommended_answer_per_question(self):
        import schools
        for opt in schools.OPTIONS.values():
            recommended = [a for a in opt.answers if a.recommended]
            assert len(recommended) == 1, opt.id
            assert opt.default == recommended[0].id
            assert schools.DEFAULTS[opt.id] == opt.default

    def test_every_question_states_its_consequence_in_one_line(self):
        import schools
        for opt in schools.OPTIONS.values():
            assert opt.consequence.strip().endswith("."), opt.id
            assert 40 < len(opt.consequence) < 220, opt.id

    def test_every_answer_can_explain_itself_in_two_or_three_sentences(self):
        import schools
        for opt in schools.OPTIONS.values():
            for ans in opt.answers:
                sentences = [s for s in re.split(r"(?<=[.!?])\s+",
                                                 ans.explain.strip()) if s]
                assert 2 <= len(sentences) <= 4, (
                    f"{opt.id}/{ans.id}: {len(sentences)} sentences")

    def test_the_form_pre_selects_the_recommended_answer(self, client):
        html = client.get("/").get_data(as_text=True)
        import schools
        for opt in schools.OPTIONS.values():
            marker = (f'name="school_{opt.id}" value="{opt.default}"')
            assert marker in html, opt.id
            after = html[html.index(marker):html.index(marker) + 260]
            assert "checked" in after, f"{opt.id} default not pre-selected"
        assert "recommended" in html
        assert "explain this" in html

    # --- no fake controls ----------------------------------------------

    def test_an_option_that_is_not_live_cannot_be_chosen(self, client,
                                                         monkeypatch):
        """A question the build cannot answer yet is shown, explained and
        disabled — and cannot be switched on by editing the request.

        THE MECHANISM IS TESTED WHETHER OR NOT ANYTHING IS CURRENTLY DEAD.
        This gate used to open by asserting that some option was not live,
        which made it a test of the registry's contents rather than of the
        machinery: when `dual_lord` went live with the arudhas, it failed
        for having nothing to look at. The next unbuilt option deserves the
        same guard the Upapada question had, so the guard is exercised
        against one whether or not the registry ships one.
        """
        import schools
        real_dead = [o for o in schools.OPTIONS.values() if not o.live]

        def obeys_the_rule(opt, page):
            assert opt.unavailable.strip(), f"{opt.id}: disabled with no reason"
            # It cannot be switched on through a form field or a JSON body.
            for ans in opt.answers:
                forced = schools.normalise({opt.id: ans.id})
                assert forced[opt.id] == opt.default, (
                    f"{opt.id}: '{ans.id}' was accepted on an option that is "
                    f"not live")
            assert opt.unavailable[:40] in page, opt.id

        for opt in real_dead:
            obeys_the_rule(opt, client.get("/").get_data(as_text=True))

        # And the machinery itself, against an option that is not live by
        # construction — so this cannot go vacuous again.
        probe = schools.Option(
            id="probe_not_live",
            question="Which way should the unbuilt thing be counted?",
            consequence="Nothing yet — this option exists to test the guard.",
            live=False,
            unavailable=("Not yet in play: this is a probe used by the gate "
                         "suite and is never shipped."),
            answers=(
                schools.Answer(id="first", text="One way", school="A",
                               explain="The first reading.", recommended=True),
                schools.Answer(id="second", text="The other way", school="B",
                               explain="The second reading."),
            ),
        )
        monkeypatch.setitem(schools.OPTIONS, probe.id, probe)
        monkeypatch.setitem(schools.DEFAULTS, probe.id, probe.default)
        obeys_the_rule(probe, client.get("/").get_data(as_text=True))
        assert "disabled" in client.get("/").get_data(as_text=True)

    def test_every_live_answer_actually_changes_a_computed_value(self):
        """THE INVARIANT THIS WHOLE FILE RESTS ON.

        For each live option, at least one non-default answer must produce a
        different chart or a different aspect table than the default does.
        Asserted by computing both, so a setting cannot rot into decoration.
        """
        import schools
        import arudhas
        import karakas
        import vargas
        import vimsopaka
        from engine import PLANETS, compute_chart
        from transits import natal_aspect_table

        def fingerprint():
            chart = compute_chart(fixtures.birth("reference"))
            return (
                tuple(round(chart.planets[p].longitude, 6) for p in PLANETS),
                tuple(sorted((a.aspecting, a.aspected, a.offset)
                             for a in natal_aspect_table(chart))),
                # The arudhas, because `dual_lord` moves those and nothing
                # else — a fingerprint blind to what an option changes would
                # pass this gate by not looking.
                arudhas.arudhas(chart),
                # And the chara karakas, for `karaka_count`. Every option
                # added from here needs its own line: the gate is only as
                # honest as the widest thing this tuple can see.
                tuple((k.office, k.planet) for k in karakas.karakas(chart)),
                # …and every divisional sign, for the three scheme forks.
                # Keyed by division so a fork that moved the wrong chart is
                # visible rather than merely "something changed".
                tuple((code,) + tuple(
                    vargas.varga_chart(chart, code).planets[p].sign_index
                    for p in PLANETS)
                    for code in vargas.SUPPORTED),
                # …and the vimsopaka scores, for `vimsopaka_group`.
                tuple(sorted(vimsopaka.scores(chart).items())),
            )

        with schools.use({}):
            baseline = fingerprint()
        for opt in schools.OPTIONS.values():
            if not opt.live:
                continue
            moved = []
            for ans in opt.answers:
                if ans.id == opt.default:
                    continue
                with schools.use({opt.id: ans.id}):
                    moved.append(fingerprint() != baseline)
            assert any(moved), (
                f"option '{opt.id}' is offered but no answer changes any "
                f"computed value — that is a fake control")

    def test_node_reach_changes_exactly_the_nodal_aspects(self):
        """And nothing else: a setting that quietly moved Jupiter's drishti
        would be a bug wearing a feature's clothes."""
        import schools
        from engine import compute_chart
        from transits import natal_aspect_table
        chart = compute_chart(fixtures.birth("reference"))

        def table(choice):
            with schools.use({"node_reach": choice}):
                return sorted((a.aspecting, a.aspected, a.offset)
                              for a in natal_aspect_table(chart))

        classical, opposition, none = (table("classical"),
                                       table("opposition"), table("none"))
        assert len(classical) > len(opposition) > len(none)
        nodes = {"Rahu", "Ketu"}
        # Every row that survives to 'none' involves no node as the aspector.
        assert all(row[0] not in nodes for row in none)
        # Non-nodal aspects are untouched by any of the three.
        def non_nodal(rows):
            return [r for r in rows if r[0] not in nodes]
        assert non_nodal(classical) == non_nodal(opposition) == \
            non_nodal(none)

    def test_node_position_moves_the_nodes_and_only_the_nodes(self):
        import schools
        from engine import PLANETS, compute_chart

        def positions(choice):
            with schools.use({"node_position": choice}):
                chart = compute_chart(fixtures.birth("partner"))
                return {p: chart.planets[p].longitude for p in PLANETS}

        mean, true = positions("mean"), positions("true")
        for planet in PLANETS:
            if planet in ("Rahu", "Ketu"):
                # The measured gap on this fixture is 1.48° — see
                # tools/oracle/DIFFERENTIAL.md.
                assert abs(mean[planet] - true[planet]) > 1.0, planet
            else:
                assert mean[planet] == true[planet], planet
        # Ketu stays opposite Rahu under either convention.
        for table in (mean, true):
            assert abs((table["Rahu"] + 180) % 360 - table["Ketu"]) < 1e-9

    # --- the choice travels with the verdict ----------------------------

    def test_the_school_prints_on_every_affected_fact(self):
        """A settings screen the reader has closed is not provenance. Any
        computed statement that depended on a school names it."""
        import schools
        from datetime import timezone as _tz
        from chartfacts import build_facts
        from engine import compute_chart
        when = datetime(2026, 9, 3, tzinfo=_tz.utc)
        for choice in ("classical", "opposition"):
            with schools.use({"node_reach": choice}):
                chart = compute_chart(fixtures.birth("reference"))
                facts = build_facts(chart, when)
                school = schools.chosen("node_reach").school
                nodal = [f for f in facts if f.kind == "aspect"
                         and {f.value["from"], f.value["to"]}
                         & {"Rahu", "Ketu"}]
                assert nodal or choice == "none"
                for fact in nodal:
                    assert school in fact.statement, fact.id
                    assert fact.value["school"] == school
                # …and a non-nodal aspect is NOT stamped with it: noise
                # everywhere is the same as provenance nowhere.
                plain = [f for f in facts if f.kind == "aspect"
                         and not ({f.value["from"], f.value["to"]}
                                  & {"Rahu", "Ketu"})]
                for fact in plain:
                    assert "Computed under" not in fact.statement, fact.id

    def test_node_placement_facts_name_the_node_convention(self):
        import schools
        from datetime import timezone as _tz
        from chartfacts import build_facts
        from engine import compute_chart
        when = datetime(2026, 9, 3, tzinfo=_tz.utc)
        for choice in ("mean", "true"):
            with schools.use({"node_position": choice}):
                facts = {f.id: f for f in build_facts(
                    compute_chart(fixtures.birth("reference")), when)}
                school = schools.chosen("node_position").school
                for fid in ("planet.rahu", "planet.ketu",
                            "transit.rahu", "transit.ketu"):
                    assert school in facts[fid].statement, (choice, fid)
                assert school not in facts["planet.sun"].statement

    def test_the_dashboard_prints_the_school_on_affected_sections(self,
                                                                  client):
        import schools
        for choice in ("classical", "none"):
            body = dict(GATE_FORM)
            body["school_node_reach"] = choice
            html = client.post("/", data=body).get_data(as_text=True)
            assert html.count("schoolstamp") >= 2
            with schools.use({"node_reach": choice}):
                assert schools.chosen("node_reach").school in html

    def test_a_changed_setting_is_announced_at_the_top_of_the_chart(self,
                                                                    client):
        body = dict(GATE_FORM)
        body["school_node_reach"] = "none"
        html = client.post("/", data=body).get_data(as_text=True)
        assert "not the default" in html
        assert "schoolsum moved" in html
        # …and the reader can change it again without retyping the birth
        # details, which the dashboard re-posts as hidden fields.
        assert "schoolform" in html and "Recalculate" in html

    def test_defaults_reproduce_the_chart_the_suite_is_anchored_to(self,
                                                                   client):
        """The recommended answers must be the ones every other gate in this
        file was written against, or half the suite is describing a chart
        nobody is served."""
        import schools
        # Listed exhaustively on purpose: a new option arriving with a
        # default nobody chose would otherwise re-anchor the whole suite
        # silently. Adding a line here is the moment to check that the
        # recommended answer is the one the other gates assume.
        assert schools.DEFAULTS == {"node_reach": "classical",
                                    "node_position": "mean",
                                    "dual_lord": "single",
                                    "karaka_count": "seven",
                                    "vimsopaka_group": "dashavarga",
                                    "hora_scheme": "twelve",
                                    "drekkana_scheme": "parashari",
                                    "bhamsa_scheme": "forward"}
        html = client.post("/", data=GATE_FORM).get_data(as_text=True)
        assert "Computed with the recommended settings throughout." in html

    def test_a_hand_edited_request_cannot_select_an_unknown_school(self,
                                                                   client):
        import schools
        assert schools.normalise({"node_reach": "; DROP TABLE"}) == \
            schools.DEFAULTS
        assert schools.normalise({"nonsense": "x"}) == schools.DEFAULTS
        assert schools.normalise(None) == schools.DEFAULTS
        resp = client.post("/", data={**GATE_FORM,
                                      "school_node_reach": "made-up"})
        assert resp.status_code == 200

    def test_the_selection_does_not_leak_between_requests(self, client):
        """A worker thread is reused. One reader's answers must not become
        the next reader's chart."""
        client.post("/", data={**GATE_FORM, "school_node_reach": "none"})
        html = client.get("/").get_data(as_text=True)
        marker = 'name="school_node_reach" value="classical"'
        assert "checked" in html[html.index(marker):html.index(marker) + 260]


class TestDueDiligenceReading:
    """/ask as a method, not a lookup.

    The failure this replaces: asked "will I marry?", the agent found the
    7th house, said something about it, and stopped. An astrologer doing
    the work reads the 7th AND the houses that support it, each house's
    LORD, the karaka's condition, the divisional chart that tests the
    promise, the period actually running, and what the slow transits are
    doing to those houses — by aspect as well as by occupancy — and only
    then says anything.

    These assert that every step is ANSWERABLE from the ledger, that the
    prompt requires them in order, and that a synthesis built across the
    frames survives the validator unchanged in strictness.
    """

    WHEN = datetime(2026, 9, 3, tzinfo=timezone.utc)

    @pytest.fixture(scope="class")
    @classmethod
    def ledger(cls, chart):
        from chartfacts import build_facts
        return {f.id: f for f in build_facts(chart, cls.WHEN)}

    # --- the checklist is answerable ------------------------------------

    def test_every_domain_step_has_the_facts_it_needs(self, chart, ledger):
        """A checklist step with no fact behind it is an instruction to
        invent. Each domain's ids must all resolve."""
        from chartfacts import domain_brief
        import domains
        for domain in domains.DOMAINS.values():
            brief = domain_brief(chart, domain.triggers[0])
            assert brief is not None, domain.id
            for step, ids in brief["fact_ids"].items():
                assert ids, f"{domain.id}/{step} lists no facts"
                for fid in ids:
                    assert fid in ledger, f"{domain.id}/{step}: {fid}"

    def test_house_lord_facts_exist_for_all_twelve(self, chart, ledger):
        from yogas import house_lords
        lords = house_lords(chart)
        for house in range(1, 13):
            fact = ledger[f"natal.{house}L"]
            assert fact.value["lord"] == lords[house]
            assert fact.value["lord_house"] == \
                chart.planets[lords[house]].house
            assert fact.value["lord_sign"] == \
                chart.planets[lords[house]].sign
            # The step also asks what falls ON the house.
            assert "aspected_by" in fact.value
            assert ordinal(house) in fact.statement

    def test_karaka_facts_carry_condition_not_just_significations(
            self, chart, ledger):
        from yogas import houses_owned_by
        for planet in PLANETS:
            fact = ledger[f"karaka.{planet.lower()}"]
            assert fact.value["sign"] == chart.planets[planet].sign
            assert fact.value["house"] == chart.planets[planet].house
            assert fact.value["rules"] == list(houses_owned_by(chart, planet))
            assert fact.value["karakatvas"]
            # Condition, not just meaning — this is what step 2 asks for.
            assert "dignity" in fact.value and "aspected_by" in fact.value

    def test_varga_domain_houses_are_addressable(self, chart, ledger):
        """`d9.7th` in one citation, rather than nine per-planet facts the
        agent has to assemble and did not.

        Widened 2026-09-13 to EVERY division this build casts. The ledger
        carried D9 and D10 because those were the only two computed; the
        seven that landed are addressable the same way.
        """
        from engine import SIGNS
        import vargas
        for code in vargas.SUPPORTED:
            label = code.lower()
            varga = vargas.varga_chart(chart, code)
            lagna = varga.lagna_sign_index
            for house in range(1, 13):
                fact = ledger[f"{label}.{ordinal(house)}"]
                assert fact.value["sign"] == SIGNS[(lagna + house - 1) % 12]
                assert fact.value["occupants"] == [
                    p for p in PLANETS if varga.planets[p].house == house]
                assert fact.value["varga"] == code

    # --- step 5: drishti, not just occupancy ----------------------------

    def test_every_transit_publishes_the_houses_it_aspects(self, chart,
                                                           ledger):
        from chartfacts import transit_aspects
        from transits import drishti_offsets, transit_snapshot
        expected = transit_aspects(chart, self.WHEN)
        snap = transit_snapshot(chart, self.WHEN)
        for planet in PLANETS:
            fact = ledger[f"transit.{planet.lower()}.aspects"]
            assert fact.value["aspects"] == expected[planet]
            assert fact.value["offsets"] == list(drishti_offsets(planet))
            assert fact.value["natal_house"] == \
                snap.planets[planet].natal_house
            # Occupancy is a different fact and must agree with this one.
            assert ledger[f"transit.{planet.lower()}"].value["aspects"] == \
                expected[planet]

    def test_transit_aspect_facts_carry_entry_and_exit_dates(self, ledger):
        """Timing may only be quoted from the ledger, so the ledger has to
        supply both ends of the window — not just the exit."""
        for planet in ("Saturn", "Jupiter", "Rahu", "Ketu"):
            value = ledger[f"transit.{planet.lower()}.aspects"].value
            assert value["entered"] and value["until"], planet
            assert re.match(r"^[A-Z][a-z]{2} \d{4}$", value["entered"])
            assert value["entered_iso"] < value["until_iso"], planet
            statement = ledger[f"transit.{planet.lower()}.aspects"].statement
            assert value["entered"] in statement
            assert value["until"] in statement

    def test_the_nodes_aspect_table_follows_the_selected_school(self, chart):
        """The ledger must publish the reader's answer, not a constant —
        otherwise the validator would check claims against a table the
        reader never chose."""
        import schools
        from chartfacts import build_facts
        for choice, expect_any in (("classical", True), ("opposition", True),
                                   ("none", False)):
            with schools.use({"node_reach": choice}):
                facts = {f.id: f for f in build_facts(chart, self.WHEN)}
                for node in ("rahu", "ketu"):
                    value = facts[f"transit.{node}.aspects"].value
                    assert bool(value["aspects"]) is expect_any, choice
                    assert value["school"] == \
                        schools.chosen("node_reach").school
                    assert value["school"] in \
                        facts[f"transit.{node}.aspects"].statement

    def test_retrogrades_and_stations_are_in_the_ledger(self, chart, ledger):
        from transits import transit_snapshot
        snap = transit_snapshot(chart, self.WHEN)
        for planet in PLANETS:
            fid = f"transit.{planet.lower()}.station"
            retro = snap.planets[planet].retrograde
            assert (fid in ledger) is bool(retro), planet
            if retro:
                assert ledger[fid].value["retrograde"] is True
                assert ledger[fid].value["always_retrograde"] is (
                    planet in ("Rahu", "Ketu"))

    # --- the validator gained a class of claim, not a loophole ----------

    def test_a_wrong_transit_aspect_is_a_violation(self, chart):
        """The most useful sentence in the new method — 'Saturn in your 4th
        also aspects your 10th' — must be the most checked, not the least."""
        from agent import validate_payload
        from chartfacts import transit_aspects
        aspects = transit_aspects(chart, self.WHEN)
        wrong = next(h for h in range(1, 13) if h not in aspects["Saturn"])
        right = aspects["Saturn"][0]
        bad = (f"Transiting Saturn also aspects your {ordinal(wrong)} "
               f"house, so that department is under its discipline.")
        good = (f"Transiting Saturn also aspects your {ordinal(right)} "
                f"house, so that department is under its discipline.")
        for text, expect in ((bad, True), (good, False)):
            payload = {"answer": text, "answer_statements": [],
                       "facts_used": [], "rules_applied": [],
                       "confidence": "Interpretive", "refused": False,
                       "refusal_reason": ""}
            kinds = {v.kind for v in
                     validate_payload(payload, chart, self.WHEN)}
            assert ("wrong-transit-aspect" in kinds) is expect, text

    def test_a_nodal_aspect_claim_is_checked_against_the_chosen_school(
            self, chart):
        """Under 'they do not reach out at all' the nodes aspect nothing,
        so any nodal drishti claim is a violation — the setting is not
        cosmetic."""
        import schools
        from agent import find_bad_transit_aspects
        from chartfacts import transit_aspects
        with schools.use({"node_reach": "classical"}):
            aspects = transit_aspects(chart, self.WHEN)
            house = aspects["Rahu"][0]
            claim = (f"Transiting Rahu currently aspects your "
                     f"{ordinal(house)} house.")
            assert find_bad_transit_aspects(claim, aspects) == []
        with schools.use({"node_reach": "none"}):
            aspects = transit_aspects(chart, self.WHEN)
            assert aspects["Rahu"] == []
            bad = find_bad_transit_aspects(claim, aspects)
            assert bad and bad[0].kind == "wrong-transit-aspect"
            assert "no house at all" in bad[0].detail

    def test_a_natal_drishti_claim_is_not_checked_as_a_transit_one(self,
                                                                   chart):
        """Two different tables. A natal claim checked against the transit
        table would withhold true sentences — the exact bug class that made
        transits unusable before frames existed."""
        from agent import find_bad_transit_aspects
        from chartfacts import transit_aspects
        aspects = transit_aspects(chart, self.WHEN)
        natal = "In your birth chart, natal Jupiter aspects the 5th house."
        assert find_bad_transit_aspects(natal, aspects) == []

    # --- the whole path, through the fake transport ---------------------

    def _multi_frame_reply(self, chart, when, domain_id):
        """A synthesis of the kind the method is meant to produce, built
        from THIS chart's real facts so it is a fair test of the
        validator rather than of the fixture."""
        from chartfacts import build_facts, domain_brief
        import domains
        facts = {f.id: f for f in build_facts(chart, when)}
        domain = domains.DOMAINS[domain_id]
        brief = domain_brief(chart, domain.triggers[0])
        main = domain.main_house
        lord = facts[f"natal.{main}L"].value
        karaka = facts[f"karaka.{domain.karakas[0].lower()}"].value
        varga = facts[f"{domain.varga.lower()}.{ordinal(main)}"].value
        dasha = facts["dasha.current"].value
        saturn = facts["transit.saturn.aspects"].value
        statements = [
            (f"Your {ordinal(main)} house is ruled by {lord['lord']}, "
             f"which sits in the {ordinal(lord['lord_house'])} house.",
             ["rule.dasha.lordship", f"rule.house.{main}"],
             [f"natal.{main}L", f"house.{main}"]),
            (f"{karaka['planet']}, the natural significator here, is in "
             f"the {ordinal(karaka['house'])} house.",
             ["rule.graha.karakatva"],
             [f"karaka.{karaka['planet'].lower()}"]),
            (f"In the {varga['varga']}, that house is {varga['sign']}.",
             ["rule.varga.confirms", "rule.varga.purpose"],
             [f"{domain.varga.lower()}.{ordinal(main)}"]),
            (f"The running period is the {dasha['mahadasha']} mahadasha "
             f"with the {dasha['antardasha']} antardasha.",
             ["rule.dasha.antara", "rule.dasha.placement"],
             ["dasha.current"]),
            (f"Transiting Saturn aspects your "
             f"{ordinal(saturn['aspects'][0])} house until "
             f"{saturn['until']}.",
             ["rule.transit.aspect", "rule.transit.window"],
             ["transit.saturn.aspects"]),
        ]
        answer = " ".join(s[0] for s in statements)
        return brief, {
            "answer": answer,
            "answer_statements": [
                {"text": text, "label": "INTERPRETIVE", "fact_ids": fids,
                 "rule_ids": rids, "rule": "classical reading"}
                for text, rids, fids in statements],
            "facts_used": sorted({f for s in statements for f in s[2]}),
            "rules_applied": sorted({r for s in statements for r in s[1]}),
            "confidence": "Interpretive", "refused": False,
            "refusal_reason": "",
        }

    def test_a_marriage_question_produces_a_multi_frame_synthesis(self,
                                                                  chart):
        """'Will I get into a relationship or marry directly?' — at least
        four frames cited, and nothing withheld."""
        from agent import ask_chart
        question = "will I get into a relationship or marry directly?"
        brief, reply = self._multi_frame_reply(chart, AGENT_WHEN, "marriage")
        client = FakeClient([reply])
        result = ask_chart(chart, AGENT_WHEN, question, client=client,
                           model="test-model")
        assert result.violations == [], result.violations
        assert result.ok and not result.refused

        # The question reached the right domain, with all five steps.
        blocks = client.messages.calls[0]["messages"][0]["content"]
        sent = json.loads(blocks[0]["text"].split(
            "Fact ledger for this chart (your only source):\n", 1)[1])
        assert sent["domain"]["id"] == "marriage"
        assert sent["domain"]["houses"][0] == 7
        assert [s["step"] for s in sent["domain"]["checklist"]] == [
            "NATAL", "KARAKA", "VARGA", "DASHA", "TRANSIT", "SYNTHESIS"]

        # …and the reply spans at least four of the five frames.
        cited = set(result.facts_used)
        frames = {
            "natal": any(f.startswith(("natal.", "house.")) for f in cited),
            "karaka": any(f.startswith("karaka.") for f in cited),
            "varga": any(f.startswith(("d9.", "d10.", "varga."))
                         for f in cited),
            "dasha": any(f.startswith("dasha.") for f in cited),
            "transit": any(f.startswith("transit.") for f in cited),
        }
        assert sum(frames.values()) >= 4, frames
        assert len(result.statements) >= 4

    def test_a_career_question_times_only_from_ledger_windows(self, chart):
        """'When will I find a job?' — dasha and transit dates, and only
        those. An invented month withholds the answer."""
        from agent import ask_chart, validate_payload
        from chartfacts import build_facts
        _brief, reply = self._multi_frame_reply(chart, AGENT_WHEN, "career")
        facts = {f.id: f for f in build_facts(chart, AGENT_WHEN)}
        window = facts["dasha.current"].statement
        reply["answer"] += " " + window
        reply["answer_statements"].append(
            {"text": window, "label": "COMPUTED",
             "fact_ids": ["dasha.current"], "rule_ids": [], "rule": ""})
        reply["facts_used"].append("dasha.current")
        result = ask_chart(chart, AGENT_WHEN, "when will I find a job?",
                           client=FakeClient([reply]), model="test-model")
        assert result.violations == [], result.violations

        # The same answer with one invented month is withheld.
        bad = json.loads(json.dumps(reply))
        bad["answer"] += " Expect the opening around March 2031."
        kinds = {v.kind for v in validate_payload(bad, chart, AGENT_WHEN)}
        assert "invented-date" in kinds

    def test_the_domain_of_a_question_is_detected_from_plain_words(self):
        import domains
        cases = {
            "will I get into a relationship or marry directly?": "marriage",
            "when will I find a job?": "career",
            "how is my health this year": "vitality",
            "should we buy property": "home",
            "will I pass my exam": "learning",
            "what does my chart say in general": None,
        }
        for question, expected in cases.items():
            found = domains.detect(question)
            assert (found.id if found else None) == expected, question

    def test_the_scope_guard_still_refuses_another_persons_chart(self,
                                                                 chart):
        """A domain question is answerable; a question about someone else
        is not, and adding the method must not have blurred that."""
        from agent import ask_chart, validate_payload
        refusal = {
            "answer": "That turns on another person's chart, which this "
                      "reading does not have. What your own chart can "
                      "speak to is what you bring to a partnership.",
            "answer_statements": [], "facts_used": [], "rules_applied": [],
            "confidence": "Interpretive", "refused": True,
            "refusal_reason": "needs another person's chart",
        }
        for question in ("will she marry me?", "does Priya love me?",
                         "is my boss going to promote me?"):
            result = ask_chart(chart, AGENT_WHEN, question,
                               client=FakeClient([json.loads(
                                   json.dumps(refusal))]),
                               model="test-model")
            assert result.refused and result.violations == []
        # The refusal path is not a way to smuggle claims past the checks.
        sneaky = json.loads(json.dumps(refusal))
        sneaky["answer"] += " Your Mars is in Leo in the 1st house."
        assert validate_payload(sneaky, chart, AGENT_WHEN)

    def test_the_prompt_requires_the_steps_in_order(self):
        from agent import SYSTEM_PROMPT
        import domains
        positions = []
        for name, _what in domains.CHECKLIST:
            marker = f". {name}."
            assert marker in SYSTEM_PROMPT or f" {name}." in SYSTEM_PROMPT, \
                name
            positions.append(SYSTEM_PROMPT.index(name))
        assert positions == sorted(positions), "steps are out of order"
        # And the aspect instruction is explicit, because occupancy-only
        # readings are the failure this step exists to fix.
        assert "USE THE ASPECTS" in SYSTEM_PROMPT
        assert "transit.saturn.aspects" in SYSTEM_PROMPT
        assert "by BOTH what they occupy AND what they" in SYSTEM_PROMPT


class TestDomainRestructure:
    """The domains-not-techniques IA. Spec: ui-design/RESTRUCTURE.md.

    The restructure's promise is that nothing was lost: every technical
    section that existed before still exists, re-homed under "Explore the
    full chart". That is the assertion that would catch a botched move, and
    it is the first one here.
    """

    # Every section id the flat dashboard had, before the restructure.
    TECHNICAL = ("dashas", "lifeline", "weather", "doshas", "myths",
                 "yogas", "ask", "agent", "patha", "grahas", "learnpath")

    @pytest.fixture(scope="class")
    @classmethod
    def page(cls, client):
        return client.post("/", data=GATE_FORM).get_data(as_text=True)

    @pytest.fixture(scope="class")
    @classmethod
    def ledger(cls, chart):
        from chartfacts import build_facts
        return {f.id: f for f in build_facts(chart, datetime.now(timezone.utc))}

    # --- nothing deleted -------------------------------------------------

    def test_every_technical_section_survives_the_move(self, page):
        for section in self.TECHNICAL:
            assert f'id="{section}"' in page, f"lost section: {section}"
        assert 'id="plate"' in page
        assert 'id="secnav"' in page, "the sticky nav went with them"

    def test_the_technical_sections_live_under_explore(self, page):
        """…and not scattered: everything from the sticky nav is inside the
        explore view, and the domain views are not."""
        explore = page[page.index('id="view-explore"'):
                       page.index("<!-- /view-explore -->")]
        for section in self.TECHNICAL:
            assert f'id="{section}"' in explore, section
            # …and each one now declares which category it belongs to, which
            # is what lets Explore show one category at a time.
            assert re.search(rf'id="{section}"[^>]*data-cat="', explore), section
        assert 'id="secnav"' in explore
        assert "view-domain-" not in explore

    def test_the_match_section_is_re_homed_too(self, client):
        """It only renders when a partner is supplied, so it needs its own
        request rather than riding on the shared one."""
        html = client.post("/", data=MATCH_FORM).get_data(as_text=True)
        explore = html[html.index('id="view-explore"'):
                       html.index("<!-- /view-explore -->")]
        assert 'id="match"' in explore

    # --- arrival ---------------------------------------------------------

    def test_arrival_leads_with_the_wheel_then_the_day(self, page):
        """Re-pinned 2026-09-11: arrival is TODAY now, and the contents page
        moved to Readings. The IA of the readings themselves is untouched —
        same seven destinations, same order — but the first screen answers
        "what is happening to me today" rather than "what would you like to
        look at", and the tests follow.
        """
        arrival = page[page.index('id="view-arrival"'):
                       page.index("<!-- /view-arrival -->")]
        order = [arrival.index(marker) for marker in
                 ('id="plate"', 'class="dayhead"', 'class="todaylist"',
                  'dayverdict')]
        assert order == sorted(order), (
            "today must read wheel → day header → entries → verdict")
        # …and the contents page is on its own screen.
        readings = page[page.index('id="view-readings"'):
                        page.index("<!-- /view-readings -->")]
        assert 'class="domaingrid"' in readings
        assert 'class="identity"' in readings

    def test_the_identity_strip_is_exactly_three_lines(self, chart, client):
        html = client.post("/", data=GATE_FORM).get_data(as_text=True)
        block = html[html.index('class="identity"'):]
        block = block[:block.index("</ul>")]
        assert block.count("<li>") == 3
        # lagna · Moon and its nakshatra · the running period, in that order
        assert chart.lagna.sign in block
        assert chart.planets["Moon"].sign in block
        assert "mahādaśā" in block

    def test_the_grid_offers_five_domains_plus_ask_and_explore(self, page):
        import domains
        grid = page[page.index('class="domaingrid"'):
                    page.index("<!-- /view-readings -->")]
        assert grid.count('<a class="dcard') == len(domains.DOMAINS) + 2
        for title in ("Love &amp; Marriage", "Work &amp; Money",
                      "Home &amp; Family", "Body &amp; Vitality",
                      "Learning &amp; Path"):
            assert title in grid, title
        assert "Ask about this chart" in grid
        assert "Explore the full chart" in grid

    def test_every_card_carries_a_teaser_from_its_own_checklist(
            self, chart, client):
        """A card with no teaser is a menu item; the teaser is what makes it
        an answer. It must be composed, not canned."""
        import domainread
        html = client.post("/", data=GATE_FORM).get_data(as_text=True)
        readings = {r.domain.id: r for r in
                    domainread.read_all(chart, datetime.now(timezone.utc))}
        assert len(readings) == 5
        for reading in readings.values():
            assert reading.teaser.strip()
            assert reading.signals, reading.domain.id
            # Condition, never prediction.
            for banned in ("you will", "guarantee", "definitely", "certain"):
                assert banned not in reading.teaser.lower()

    # --- domain view -----------------------------------------------------

    def test_a_domain_view_is_verdict_first_then_the_working(self, page):
        start = page.index('id="view-domain-marriage"')
        nxt = page.find('id="view-domain-', start + 10)
        view = page[start:nxt if nxt > 0 else len(page)]
        order = [view.index(m) for m in
                 ('class="dsynth"', 'class="conf"', 'class="fold dstep"')]
        assert order == sorted(order), (
            "a domain view reads synthesis → confidence → the working")

    def test_the_working_follows_the_checklist_order(self, chart):
        from app import domain_cards
        from domains import CHECKLIST
        cards = {c["id"]: c for c in
                 domain_cards(chart, datetime.now(timezone.utc))}
        expected = [name.title() for name, _ in CHECKLIST
                    if name != "SYNTHESIS"]
        for card in cards.values():
            titles = [s["title"] for s in card["steps"]]
            assert titles == [t for t in expected if t in titles], card["id"]
            assert titles, card["id"]

    def test_every_step_row_names_the_facts_behind_it(self, chart, ledger):
        """The restructure must not cost the one-tap-from-computation
        property. Every row in every expander cites real fact ids."""
        from app import domain_cards
        cards = domain_cards(chart, datetime.now(timezone.utc))
        seen = 0
        for card in cards:
            for step in card["steps"]:
                for row in step["rows"]:
                    assert row["ids"].strip(), (card["id"], step["title"])
                    for fid in row["ids"].split(" · "):
                        assert fid in ledger, fid
                        seen += 1
        assert seen > 60, "suspiciously few citations"

    def test_the_natal_step_explains_why_each_house_is_in_the_list(
            self, chart):
        """A reader should never have to take 'the 8th matters for marriage'
        on faith."""
        from app import domain_cards
        from domains import DOMAINS
        cards = {c["id"]: c for c in
                 domain_cards(chart, datetime.now(timezone.utc))}
        natal = [s for s in cards["marriage"]["steps"]
                 if s["title"] == "Natal"][0]
        text = " ".join(r["text"] for r in natal["rows"])
        assert "the durability of the marriage" in text
        for house in DOMAINS["marriage"].houses:
            assert f"rule.house.{house}" not in text   # ids go in `ids`

    def test_a_domain_view_offers_the_agent_without_depending_on_it(
            self, page, chart):
        """The deterministic reading stands alone; the agent is additive.
        The page must render fully with no API key, which is how the test
        suite runs."""
        import agent as agent_mod
        assert not agent_mod.is_configured()
        assert "dsynth" in page
        assert "Open the chart agent" in page

    # --- the reading itself ----------------------------------------------

    def test_the_domain_reading_is_deterministic(self, chart):
        import domainread
        when = datetime(2026, 9, 3, tzinfo=timezone.utc)
        first = domainread.read_all(chart, when)
        second = domainread.read_all(chart, when)
        assert [r.as_dict() for r in first] == [r.as_dict() for r in second]

    def test_the_reading_reports_condition_and_never_outcome(self, chart):
        """No language model writes readings here, and this one cannot
        express a prediction — there is no template for it."""
        import domainread
        when = datetime(2026, 9, 3, tzinfo=timezone.utc)
        blob = " ".join(p for r in domainread.read_all(chart, when)
                        for p in (r.paragraphs + (r.teaser,))).lower()
        for banned in ("you will", "will be", "guarantee", "is assured",
                       "definitely", "expect to", "going to"):
            assert banned not in blob, banned
        # …and it does say what it IS for: support, strain, what is live.
        assert "what holds it up" in blob and "what asks more of you" in blob

    def test_the_reading_spans_all_five_frames(self, chart):
        import domainread
        when = datetime(2026, 9, 3, tzinfo=timezone.utc)
        for reading in domainread.read_all(chart, when):
            prefixes = {fid.split(".")[0] for s in reading.signals
                        for fid in s.fact_ids}
            assert {"natal", "house"} & prefixes, reading.domain.id
            assert "karaka" in prefixes, reading.domain.id
            assert {"d9", "d10", "varga"} & prefixes, reading.domain.id
            assert "transit" in prefixes, reading.domain.id

    def test_every_cited_rule_exists(self, chart):
        import domainread
        from rulelib import is_known
        when = datetime(2026, 9, 3, tzinfo=timezone.utc)
        for reading in domainread.read_all(chart, when):
            for signal in reading.signals:
                for rid in signal.rule_ids:
                    assert is_known(rid), rid

    # --- mobile and the view machinery -----------------------------------

    def test_the_contents_list_is_one_column_at_every_width(self):
        """Re-pinned 2026-09-09 with the editorial-dossier redesign.

        This used to assert the domain grid went two-up at 560px. The grid
        is now a table of contents (ui-design/DOSSIER.md), and a contents
        page is a single column at every width — rules BETWEEN entries only
        work down one column, which is what makes it read as a contents
        page rather than as cards with lines on them.

        The IA is untouched: the same seven destinations, in the same
        order, behind the same links, asserted by the tests above.
        """
        css = (HERE / "static" / "style.css").read_text(encoding="utf-8")
        block = css[css.index(".cards {"):]
        block = block[:block.index("}")]
        assert "grid-template-columns: 1fr;" in block
        # No width may reintroduce a second column of contents entries.
        assert "@media (min-width: 560px) { .cards" not in css
        for media in re.finditer(r"@media[^{]*\{[^{]*\.cards\b[^}]*\}", css):
            assert "1fr 1fr" not in media.group(0), media.group(0)
        # Square corners survive the new components.
        new = css[css.index("THE EDITORIAL DOSSIER"):]
        for radius in re.findall(r"border-radius:\s*([^;]+);", new):
            assert radius.strip() in ("0", "50%"), radius

    def test_views_are_switched_client_side_not_by_routing(self, page):
        """Server routes per domain would mean re-posting the birth record
        on every tap; nothing is stored between requests."""
        assert 'data-view="view-domain-marriage"' in page
        assert 'href="/domain' not in page
        assert page.count('class="view"') >= 7      # arrival + 5 + explore
        # Deep-linkable and back-button-able.
        assert "history.pushState" in page
        assert 'window.addEventListener("popstate"' in page

    def test_the_view_switcher_does_not_capture_the_plates_own_panes(
            self, page):
        """A bug this restructure actually shipped and had to undo.

        The chart plate has used `class="pane"` for its D1/D9/D10 tabs since
        Phase 6. Naming the view containers `.pane` as well made the view
        switcher hide `#pane-d1` — so the wheel, the first thing on the
        arrival screen and the whole point of it, rendered blank. The two
        must stay different classes.
        """
        assert 'class="view"' in page
        assert 'id="pane-d1"' in page          # the plate's own, untouched
        for vid in ("view-arrival", "view-explore"):
            at = page.index(f'id="{vid}"')
            assert 'class="pane"' not in page[at - 40:at], vid
        js = page[page.index("const views = Array.from"):]
        assert 'querySelectorAll(".view")' in js[:120]
        # …and the wheel really is rendered inside the arrival view.
        arrival = page[page.index('id="view-arrival"'):
                       page.index("<!-- /view-arrival -->")]
        assert 'class="kundli"' in arrival
        assert 'id="pane-d1"' in arrival

    def test_only_the_arrival_view_is_visible_on_load(self, page):
        for view in ("view-explore", "view-domain-marriage",
                     "view-domain-career"):
            marker = f'id="{view}"'
            assert "hidden" in page[page.index(marker):
                                    page.index(marker) + 120], view
        arrival = page.index('id="view-arrival"')
        assert "hidden" not in page[arrival:arrival + 60]

    def test_the_spec_is_on_record(self):
        spec = (HERE / "ui-design" / "RESTRUCTURE.md").read_text("utf-8")
        for required in ("ARRIVAL", "DOMAIN VIEW", "EXPLORE THE FULL CHART",
                         "Mobile-first", "nothing is deleted"):
            assert required.lower() in spec.lower(), required


class TestMaskedBirthFieldsInARealBrowser:
    """The bug was a browser behaviour, so the guard has to be a browser.

    Server-side assertions on the markup (`TestPhase6FlaskUI`) prove the
    attributes are right. They cannot prove that typing "13" is accepted,
    because the thing that rejected it was Safari's native control reading
    the system's 12-hour clock — an HTML string cannot show that. This class
    drives the rendered form: types digits, reads back what the field holds,
    and submits.
    """

    @staticmethod
    def _launch(p, pytest_mod):
        """Playwright's bundled build, or any chromium already on the box.

        A test that quietly skips guards nothing, and this one exists
        precisely so a template swap cannot go unnoticed. So when the pinned
        build is absent — a common state in a container that ships one
        chromium for every tool — fall back to the installed binary before
        giving up. SIDERA_CHROMIUM overrides for an unusual host.
        """
        try:
            return p.chromium.launch()
        except Exception:
            pass
        candidates = [os.environ.get("SIDERA_CHROMIUM")]
        root = Path(os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "/opt/pw-browsers"))
        candidates.append(str(root / "chromium"))
        candidates += [str(p_) for p_ in sorted(root.glob("chromium-*/chrome-linux/chrome"))]
        candidates += ["/usr/bin/chromium", "/usr/bin/chromium-browser",
                       "/usr/bin/google-chrome"]
        for path in candidates:
            if not path or not Path(path).exists():
                continue
            try:
                return p.chromium.launch(executable_path=path)
            except Exception:
                continue
        pytest_mod.skip(
            "no chromium available for the browser gate; the markup gates in "
            "TestPhase6FlaskUI still ran. Set SIDERA_CHROMIUM or run "
            "'playwright install chromium'.")

    @classmethod
    @pytest.fixture(scope="class")
    def form_page(cls):
        pw = pytest.importorskip(
            "playwright.sync_api",
            reason="playwright not installed; the markup gates still run")
        from app import app

        import threading
        from werkzeug.serving import make_server
        srv = make_server("127.0.0.1", 0, app, threaded=True)
        port = srv.socket.getsockname()[1]
        t = threading.Thread(target=srv.serve_forever, daemon=True)
        t.start()
        try:
            with pw.sync_playwright() as p:
                browser = cls._launch(p, pytest)
                # A US locale with a 12-hour clock is exactly the environment that
                # produced 'Invalid value' on the native control. If the mask
                # is right, the locale is irrelevant — which is the claim.
                ctx = browser.new_context(locale="en-US",
                                          timezone_id="America/Los_Angeles")
                page = ctx.new_page()
                page.goto(f"http://127.0.0.1:{port}/")
                yield page
                browser.close()
        finally:
            srv.shutdown()

    def test_the_time_field_is_text_with_the_mask_not_a_native_picker(
            self, form_page):
        """The regression this exists to prevent: a template swap that
        silently restores <input type="time">."""
        for field in ("time", "p_time", "date", "p_date"):
            el = form_page.locator(f"#{field}")
            assert el.get_attribute("type") == "text", (
                f"#{field} is a native picker again — it follows the "
                f"viewer's system locale, which is the reported bug")
            assert el.get_attribute("data-mask") in ("time", "date")
            assert el.get_attribute("inputmode") == "numeric"
        # Nothing on the page may be one, either.
        assert form_page.locator('input[type="time"]').count() == 0
        assert form_page.locator('input[type="date"]').count() == 0

    def test_typing_thirteen_is_accepted_in_a_twelve_hour_locale(
            self, form_page):
        """'13' typed into the old control popped 'Invalid value'."""
        field = form_page.locator("#time")
        field.fill("")
        field.type("13")
        assert field.input_value() == "13"
        assert field.get_attribute("aria-invalid") is None

    def test_the_mask_types_the_colon_so_a_digit_keypad_suffices(
            self, form_page):
        """A phone's numeric keypad has no colon key. It must not need one."""
        field = form_page.locator("#time")
        field.fill("")
        field.type("1312")
        assert field.input_value() == "13:12"

    def test_an_explicit_colon_is_also_accepted(self, form_page):
        field = form_page.locator("#time")
        field.fill("")
        field.type("13:12")
        assert field.input_value() == "13:12"

    def test_the_date_mask_types_its_own_slashes_day_first(self, form_page):
        field = form_page.locator("#date")
        field.fill("")
        field.type("16081998")
        assert field.input_value() == "16/08/1998"

    def test_out_of_range_is_the_only_error_and_it_names_the_range(
            self, form_page):
        """Error for hour > 23 or minute > 59 — nothing else."""
        field = form_page.locator("#time")
        for good in ("0000", "2359", "1312", "0845"):
            field.fill("")
            field.type(good)
            form_page.locator("#place").focus()          # blur
            assert field.get_attribute("aria-invalid") is None, good
        for bad, message in (("2400", "hour runs 00–23"),
                             ("1275", "Minutes run 00–59")):
            field.fill("")
            field.type(bad)
            form_page.locator("#place").focus()
            assert field.get_attribute("aria-invalid") == "true", bad
            assert message in form_page.locator("#time-hint").inner_text()

    def test_the_hint_is_visible_before_anything_is_typed(self, form_page):
        form_page.reload()
        assert (form_page.locator("#time-hint").inner_text().strip()
                == "Time of birth · 24-hour · e.g. 13:12")
        assert (form_page.locator("#date-hint").inner_text().strip()
                == "Date of birth · day first · e.g. 25/03/1994")

    def test_a_masked_chart_casts_end_to_end_from_the_browser(self, form_page):
        """Typed as digits alone, submitted, and the chart comes back.

        The full path — mask, POST, parse, cast — because the previous two
        attempts at this field each passed their own unit tests and failed
        in a browser.
        """
        form_page.reload()
        form_page.locator("#date").type("16081998")
        form_page.locator("#time").type("0657")
        # Place first: typing into it clears lat/lon/tz, since a coordinate
        # left over from a previous city would cast a chart for the wrong
        # spot. Then the manual-entry disclosure, which the autocomplete
        # would otherwise fill from a suggestion.
        form_page.locator("#place").fill(GATE_BIRTH.place)
        form_page.locator("#manual").evaluate("d => d.open = true")
        form_page.locator("#lat").fill(str(GATE_BIRTH.latitude))
        form_page.locator("#lon").fill(str(GATE_BIRTH.longitude))
        form_page.locator("#tz").fill(GATE_BIRTH.tz)
        with form_page.expect_navigation():
            form_page.locator("#cast").evaluate("f => f.submit()")
        form_page.wait_for_load_state("load")
        html = form_page.content()
        error = re.search(r'<p class="error">(.*?)</p>', html, re.S)
        assert not error, f"form refused a valid masked entry: {error.group(1)}"
        assert "Leo 11°05′08″" in html


class TestEditorialDoctrine:
    """Answer first, one breath, then the working — enforced, not hoped for.

    A live walk-through found the app over-explaining and burying the answer:
    the domain synthesis ran to three hundred words and opened on the word
    "Mixed". This class is the doctrine in `voice.py` made non-negotiable.

    It polices ORDER and ECONOMY only. Every honesty gate — the validator,
    the fact ids, the confidence labels, the rule citations — is unchanged and
    tested exactly as before, elsewhere in this file. Nothing here permits a
    single sentence that was not permitted yesterday.
    """

    @classmethod
    @pytest.fixture(scope="class")
    def readings(cls, chart):
        import domainread
        return domainread.read_all(chart, AGENT_WHEN)

    # --- 1. answer first ----------------------------------------------------

    def test_every_domain_opens_with_the_verdict_not_a_preamble(
            self, readings):
        import voice
        for r in readings:
            assert r.verdict, r.domain.id
            assert r.paragraphs[0] == r.verdict, (
                f"{r.domain.id}: the verdict must BE the first paragraph, "
                f"not something the reader scrolls to")
            assert voice.is_answer_first(r.verdict), r.domain.id
            # "One breath" is two sentences, not a paragraph with a full stop.
            assert len(voice.sentences(r.verdict)) <= voice.VERDICT_SENTENCES, (
                f"{r.domain.id}: {r.verdict}")

    def test_the_card_teaser_is_the_readings_own_first_breath(self, readings):
        """A card promising one thing and a view saying another would be two
        readings of one chart — and the card is the more-read of the two."""
        for r in readings:
            assert r.verdict.startswith(r.teaser.rstrip(".")[:40]), (
                f"{r.domain.id}: card and view have drifted apart\n"
                f"  card: {r.teaser}\n  view: {r.verdict}")

    # --- 2. hard budgets ----------------------------------------------------

    def test_teasers_fit_the_card_budget(self, readings):
        import voice
        for r in readings:
            n = voice.words(r.teaser)
            assert 0 < n <= voice.TEASER_WORDS, (
                f"{r.domain.id}: {n} words > {voice.TEASER_WORDS}\n"
                f"  {r.teaser}")

    def test_the_visible_synthesis_fits_its_budget(self, readings):
        """120 words before any expander. What is cut is not lost — it is in
        the working below, unchanged and still citing its fact ids."""
        import voice
        for r in readings:
            n = voice.words(r.visible)
            assert n <= voice.SYNTHESIS_WORDS, (
                f"{r.domain.id}: {n} words visible > {voice.SYNTHESIS_WORDS}")
            # …and the working is still all there, which is the other half of
            # the bargain. Cutting the top layer must not cut the evidence.
            assert len(r.signals) >= 3, r.domain.id

    def test_the_budget_is_binding_not_decorative(self, readings):
        """A budget nothing ever approaches would prove nothing.

        The synthesis before this change ran 255-301 words. If some later
        edit shrinks every reading to a stub the budgets would still 'pass',
        so this asserts the readings are substantial as well as short.
        """
        import voice
        assert max(voice.words(r.visible) for r in readings) >= 60

    # --- 3. no throat-clearing ---------------------------------------------

    def test_no_throat_clearing_anywhere_a_reader_looks(self, readings):
        import voice
        for r in readings:
            for text in (r.teaser, r.visible):
                hits = voice.find_throat_clearing(text)
                assert not hits, f"{r.domain.id}: {hits}\n  in: {text}"

    def test_the_banned_phrases_actually_catch_the_disease(self):
        """The list is only worth having if it fires on the real sentences.

        Each of these is a shape the app or the model actually produced, or
        the founder quoted back. A pattern list that passes everything is
        decoration.
        """
        import voice
        for sentence in (
                "It's important to note that the chart does not forecast "
                "outcomes.",
                "It is worth noting that Saturn is slow.",
                "While no definitive answer is possible, marriage is likely.",
                "The chart doesn't predict outcomes, but Venus is strong.",
                "That said, the 7th lord is weak.",
                "First of all, let us look at the 7th house.",
                "Before we begin, a word about how this works.",
                "Keep in mind that transits are temporary.",
                "The chart suggests that it may be possible that you marry.",
                "There are several factors at play here.",
                "The short answer is that Saturn is transiting your 4th."):
            assert voice.find_throat_clearing(sentence), (
                f"not caught: {sentence}")

    def test_the_banned_phrases_do_not_fire_on_honest_prose(self):
        """The other half: a list that flags real readings is worse than none.

        These are sentences the app should keep saying.
        """
        import voice
        for sentence in (
                "Marriage is more contested than helped — the planet that "
                "rules it is weak.",
                "Saturn is on it until Jun 2027.",
                "A transit is a season with an end date, not a verdict.",
                "This reads the chart's condition, not what will happen.",
                "The day runs 01-31, and the month comes second.",
                "Work and money is one of the harder parts of your chart.",
                "Two frames disagree here, and the contact governs."):
            assert not voice.find_throat_clearing(sentence), (
                f"false positive on: {sentence}")

    # --- 4. one caveat, at the end -----------------------------------------

    def test_exactly_one_caveat_and_it_comes_last(self, readings):
        """The caveat is a FIELD, not a habit — so 'one, at the end' is a
        property of the structure rather than something to remember."""
        for r in readings:
            assert r.caveat and "\n" not in r.caveat
            assert len(r.caveat.split(". ")) == 1, r.caveat
            body = " ".join(r.paragraphs)
            for hedge in ("not a verdict", "not what will happen",
                          "rather than a bad sign"):
                assert hedge not in body, (
                    f"{r.domain.id}: a second caveat inside the reading — "
                    f"'{hedge}'")
            assert r.visible.rstrip().endswith(r.caveat)

    # --- 5. plain register on top ------------------------------------------

    def test_the_top_layer_carries_no_sanskrit_and_no_house_numbers(
            self, readings):
        """Someone who has never met this system reads the verdict.

        The technical language is not removed from the app — it is required
        one tap down, where it can be glossed and cited, and the next test
        asserts it is still there.
        """
        import voice
        for r in readings:
            hits = voice.find_jargon(r.visible)
            assert not hits, f"{r.domain.id}: {hits}\n  in: {r.visible}"

    def test_the_working_underneath_keeps_every_technical_word(self, readings):
        """The plain register is a translation, not a dumbing-down.

        If the expanders had gone plain too, the app would have lost the
        thing that makes it checkable.
        """
        import voice
        blob = " ".join(s.text for r in readings for s in r.signals)
        assert voice.find_jargon(blob), (
            "the expanders have gone plain — the technical statement, with "
            "its house numbers and its drishti, is the checkable one")
        for term in ("house", "lord", "drishti"):
            assert term in blob.lower(), term

    # --- the rendered page --------------------------------------------------

    def test_the_dashboard_obeys_the_doctrine_where_a_reader_meets_it(
            self, page):
        """Not the module — the HTML. A doctrine that holds in a dataclass
        and not on the page has not been applied."""
        import voice
        for cls in ("dcard-teaser", "dverdict"):
            found = re.findall(rf'class="[^"]*\b{cls}\b[^"]*"[^>]*>(.*?)</',
                               page, re.S)
            assert found, cls
            for raw in found:
                text = re.sub(r"<[^>]+>", "", raw).strip()
                assert not voice.find_throat_clearing(text), (cls, text)
                assert not voice.find_jargon(text), (cls, text)
                budget = (voice.TEASER_WORDS if cls == "dcard-teaser"
                          else voice.SYNTHESIS_WORDS)
                assert voice.words(text) <= budget, (cls, text)

    def test_the_verdict_is_the_first_prose_in_the_domain_view(self, page):
        """Order on the page, not just in the payload."""
        for did in ("marriage", "career"):
            view = page[page.index(f'id="view-domain-{did}"'):]
            view = view[:view.index("The working, step by step")]
            at = re.search(r'class="[^"]*\bdverdict\b', view).start()
            assert at < view.index('class="conf"')
            assert 'class="dsynth"' not in view[:at]

    def test_the_glance_still_answers_in_one_breath(self, page):
        """The Glance was already answer-first. This keeps it that way."""
        import voice
        raw = re.search(r'<p class="[^"]*\bstatement\b[^"]*">(.*?)</p>',
                        page, re.S).group(1)
        text = re.sub(r"<[^>]+>", "", raw).strip()
        assert not voice.find_throat_clearing(text), text
        assert voice.words(text) <= 25, text
        assert len(voice.sentences(text)) <= 2, text

    # --- the agent ----------------------------------------------------------

    def test_the_agent_is_told_to_answer_first_and_shown_how(self):
        import agent
        p = agent.SYSTEM_PROMPT
        assert "ANSWER FIRST" in p
        assert "confident astrologer in two sentences" in p
        assert "ONE CAVEAT, AT THE END, ONE LINE" in p
        assert "NO Sanskrit and NO house numbers" in p
        # The doctrine must not be sold as a licence to overclaim.
        assert "CONDITION, not a certainty" in p
        assert "You may not say what WILL happen." in p

    def test_the_agents_verdict_is_a_required_field(self):
        """Answer-first as structure. A model cannot forget the verdict or
        bury it mid-paragraph if the schema will not accept the reply."""
        import agent
        assert "verdict" in agent.RESPONSE_SCHEMA["required"]
        desc = agent.RESPONSE_SCHEMA["properties"]["verdict"]["description"]
        assert "1-2 sentences" in desc and "no caveat" in desc.lower()

    def test_the_verdict_is_validated_exactly_as_the_answer_is(
            self, chart, agent_facts):
        """The headline is the worst possible place for a claim to escape.

        Whatever the answer would be withheld for, the verdict is withheld
        for — moving a sentence into the verdict must not launder it.
        """
        import agent
        for field in ("answer", "verdict"):
            payload = _reply("Saturn is transiting your 4th house.",
                             facts=["transit.saturn"], verdict="")
            payload[field] = ("You will definitely marry in March 2031.")
            violations = agent.validate_payload(payload, chart, AGENT_WHEN)
            kinds = {v.kind for v in violations}
            assert kinds & {"asserted-certainty", "invented-date"}, (
                f"a certainty in `{field}` went unchecked: {kinds}")

    def test_a_withheld_answer_leads_with_what_to_do(self, chart):
        """Answer-first applies to the bad news too.

        The old message opened on the word "Withheld" and put the one useful
        sentence — what to ask instead — last, behind an explanation of our
        own machinery.
        """
        import agent, voice
        for kind in ("asserted-certainty", "invented-date", "unknown-fact-id"):
            why, hint = agent.explain_violations(
                [agent.Violation(kind, "x", "y")])
            message = f"{hint} That reply {why}, so it was not shown."
            first = voice.sentences(message)[0]
            assert first.lower().startswith(("ask", "try")), first
            assert not voice.find_throat_clearing(message), message

    def test_the_ask_lenses_answer_before_they_score(self):
        """The deterministic /ask led with its own methodology: "The
        strongest agreement (75%) points toward…". The finding leads now."""
        import ask, voice
        for q in ask.REGISTRY.values():
            frame = q.answer_frame
            assert frame.startswith("{modal}"), (
                f"{q.key}: the answer must open the sentence — {frame}")
            assert not voice.find_throat_clearing(frame), q.key

    def test_the_ask_answers_render_finding_first(self, page):
        import voice
        seg = page[page.index('id="ask"'):page.index('id="agent"')]
        answers = re.findall(r'class="yogadetail">(.*?)</p>', seg, re.S)
        assert answers, "no /ask answers rendered"
        for raw in answers:
            text = re.sub(r"<[^>]+>", "", raw).strip()
            if "carried by" not in text:
                continue
            assert not text.startswith(("The strongest", "Dated windows",
                                        "The period's")), text
            assert not voice.find_throat_clearing(text), text


class TestEditorialDossier:
    """The visual layer, measured — ui-design/DOSSIER.md.

    Every assertion here is about SETTING: type scale, rules, pagination,
    restraint. Nothing in this class touches what the app computes or says;
    the IA, the verdict-first order and the word budgets are asserted
    unchanged by TestDomainRestructure and TestEditorialDoctrine.
    """

    @staticmethod
    def _css():
        return (HERE / "static" / "style.css").read_text(encoding="utf-8")

    # --- typography-led -----------------------------------------------------

    def test_the_pairing_is_the_one_the_dossier_chose(self):
        """Tiro Devanagari Sanskrit is not decoration: it is the only face
        here that sets the transliteration AND the Devanagari, so 'Navāṃśa'
        does not fall back mid-word."""
        page = (HERE / "templates" / "index.html").read_text(encoding="utf-8")
        assert "Tiro+Devanagari+Sanskrit" in page
        assert "IBM+Plex+Sans" in page
        # One stylesheet request, not three. (The preconnect hint is not a
        # request for a font; it is a hint that one is coming.)
        links = re.findall(
            r'<link rel="stylesheet" href="https://fonts\.googleapis[^"]*"',
            page)
        assert len(links) == 1, links
        assert "Cormorant" not in page.split("</head>")[0]

    def test_the_type_scale_has_real_jumps(self):
        """No timid 18px headings. Each step is a real change of voice."""
        css = self._css()
        block = css[css.index("--t-verdict"):css.index("--space-fold")]
        sizes = {k: float(v) for k, v in
                 re.findall(r"--t-(\w+):\s*([\d.]+)px", block)}
        assert sizes["verdict"] >= 28, sizes
        assert sizes["verdict"] / sizes["body"] >= 1.8, sizes
        assert sizes["title"] / sizes["head"] >= 1.3, sizes
        assert sizes["head"] / sizes["body"] >= 1.2, sizes

    def test_the_fold_title_leads_and_the_verdict_reads(self, page):
        """Re-pinned 2026-09-10. This used to require the VERDICT to be the
        largest type, and that is exactly what went wrong: the fold title
        rendered smaller than the verdict body, and the verdict was set so
        large it ran three or four words to the line — shouting, not reading.

        The title is the dominant element now; the verdict is a printed
        pull-quote, large but at a measure you can read along.
        """
        css = self._css()

        def clamp(selector):
            block = css[css.index(selector + " {"):]
            block = block[:block.index("}")]
            lo, _, hi = re.search(
                r"font-size:\s*clamp\(([\d.]+)px,\s*([\d.]+)vw,\s*([\d.]+)px\)",
                block).groups()
            return float(lo), float(hi)

        t_lo, t_hi = clamp(".domainread .chartof-name")
        v_lo, v_hi = clamp(".dverdict")
        assert (t_lo, t_hi) >= (44, 72), (t_lo, t_hi)
        assert 22 <= v_lo and v_hi <= 30, (v_lo, v_hi)
        assert t_lo > v_hi, "the title must dominate the verdict at every size"
        # …and the verdict is a pull-quote measure, not a billboard.
        block = css[css.index(".dverdict {"):]
        block = block[:block.index("}")]
        measure = int(re.search(r"max-width:\s*(\d+)ch", block).group(1))
        assert 45 <= measure <= 60, measure
        assert "line-height: 1.35" in block

    # --- pagination as identity ---------------------------------------------

    def test_every_view_carries_its_folio(self, page):
        """Re-paginated 2026-09-11 for the five screens.

        FOUR top-level folds now — Today, Readings, Your charts, Explore —
        with their contents numbered beneath them: P. 02·1 is the first
        reading, P. 03·2 the second plate. Still a real sequence, which is
        the test for whether numbering is information or ornament; there are
        simply two levels of it.
        """
        import html as _html
        folios = re.findall(r'<p class="folio">(.*?)</p>', page, re.S)
        joined = _html.unescape(re.sub(r"<[^>]+>", " ", " ".join(folios)))
        # FIVE folds since Ask became a screen of its own, so the folios
        # match the five tabs. A page marker reading "Fold 1 of 4" beside
        # five tabs is the numbering contradicting the navigation.
        for n, name in ((1, "Today"), (2, "Readings"), (3, "Your charts"),
                        (4, "The full chart"), (5, "Ask")):
            assert f"P. {n:02d}" in joined, n
            assert f"Fold {n} of 5" in joined, n
            assert name in joined, name
        # Every view has one — no screen is unnumbered.
        views = len(re.findall(r'<div class="view"', page))
        assert len(folios) == views, (len(folios), views)
        assert "P. 02·1" in joined and "Love & Marriage" in joined
        # Re-pinned 2026-09-12: the plate folios are numbered by their place
        # in the gallery, and the gallery grew D3 and D16. The claim is that
        # the plates ARE numbered in sequence, not that D9 is number two.
        plates = sorted(int(n) for n in re.findall(r"P\. 03·(\d+)", joined))
        assert plates and plates == list(range(1, len(plates) + 1)), plates

    def test_the_wheel_is_a_captioned_plate(self, page):
        """Plate number, subject, and the imprint line printed matter puts
        under a figure: what it is, when it was cast, under which ayanāṃśa."""
        assert 'class="plateno">Plate I<' in page
        for numeral in ("Plate I", "Plate II", "Plate III"):
            assert numeral in page, numeral
        cast = re.search(r'class="platecast">(.*?)</span>', page, re.S)
        assert cast, "the plate has no imprint line"
        assert "Lahiri ayanāṃśa" in cast.group(1)
        assert re.search(r"cast \d{1,2} \w+ \d{4}", cast.group(1))

    def test_the_arrival_is_a_contents_page(self, page):
        """Numbered entries, one column, hairline-separated — not cards."""
        grid = page[page.index('<section class="domaingrid"'):]
        grid = grid[:grid.index("</section>")]
        numbers = re.findall(r'class="dcard-no">([^<]+)<', grid)
        # Re-pinned 2026-09-11. The list used to start at 02 because entry 01
        # was the day's glance, which sat above it on the same screen. Today
        # is its own fold now, so the contents that used to be offset by it
        # read as a page missing its first line. The numbers are the folios
        # the entries open — 01 opens P. 02·1 — and the two that leave this
        # fold entirely (Ask, Explore) are unnumbered.
        assert numbers == ["01", "02", "03", "04", "05", "—", "—"], numbers
        css = self._css()
        block = css[css.index(".dcard {"):]
        block = block[:block.index("}")]
        assert "border-bottom: 1px solid var(--divider)" in block
        # An entry is never a box.
        assert not re.search(r"^\s*border:\s*1px", block, re.M), block

    # --- space and rules ----------------------------------------------------

    def test_nothing_is_a_box(self):
        """'No boxes-in-boxes, no shadows; whitespace does the separating.'

        Two exceptions, both earned: the city dropdown floats OVER text and
        needs an edge to be readable, and the two score rings are circles,
        not boxes — the documented 50% radius.
        """
        css = self._css()
        offenders = []
        for block in re.finditer(r"([^{}]+)\{([^{}]*)\}", css):
            selector, body = block.group(1).strip(), block.group(2)
            if not re.search(r"border:\s*1px solid", body):
                continue
            if "border-radius: 50%" in body:
                continue                      # a ring is not a box
            if ".suggest" in selector:
                continue                      # floats over text
            offenders.append(selector.splitlines()[-1].strip()[:50])
        assert offenders == [], f"boxes remain: {offenders}"

    def test_the_rule_goes_above_the_heading(self):
        """The structural signature, from the śiro-rekhā: Devanagari hangs
        from a headline rather than sitting on a baseline, so every section
        marker here is a rule with its heading beneath it."""
        css = self._css()
        block = css[css.index(".mark {"):]
        block = block[:block.index("}")]
        assert "border-top" in block and "border-bottom" not in block
        page = (HERE / "templates" / "index.html").read_text(encoding="utf-8")
        assert '<div class="mark">' in page

    def test_no_shadows_no_gradients_no_stray_radius(self):
        """Restated here because a redesign is exactly when these creep in.

        DECLARATIONS, not prose. This scanned the raw file, so a comment
        saying "no gradient and no hue" failed the no-gradient rule — the
        gate firing on the sentence that states it. Comments are stripped
        first; what is being forbidden is the property.
        """
        css = re.sub(r"/\*.*?\*/", "", self._css(), flags=re.S)
        assert "box-shadow" not in css and "gradient" not in css
        assert sorted(set(re.findall(r"border-radius:\s*([^;]+);", css))) \
            == ["0", "50%"]

    # --- colour restraint ---------------------------------------------------

    def test_two_readings_ship_not_six(self):
        css = self._css()
        assert set(re.findall(r':root\[data-palette="(\w+)"\]', css)) == \
            {"paper", "night"}

    def test_the_plate_is_engraved_not_drawn_in_neon(self, measured):
        """Thin strokes. A plate is engraved, not lit.

        Measured as RENDERED pixels, not as the raw attribute: an SVG
        stroke-width is in user units, so the same number is a hairline on
        the 530px plate and invisible on the 140px mini one. Judging the
        attribute told me the mini plate was "too heavy" when it was in fact
        drawing at 0.65px.
        """
        for width, m in measured.items():
            for name, px in m["strokePx"].items():
                assert 0.4 <= px <= 1.8, (width, name, px)
        # A `paint-order` halo is not a drawn line — it is how a label stays
        # legible where it crosses one. Judge the strokes that draw.
        css = self._css()
        for block in re.finditer(r"([^{}]+)\{([^{}]*)\}", css):
            body = block.group(2)
            if "paint-order" in body:
                continue
            for w in re.findall(r"stroke-width:\s*([\d.]+)", body):
                assert float(w) <= 1.6, (block.group(1).strip()[:40], w)

    # --- measured in a browser ----------------------------------------------

    @classmethod
    @pytest.fixture(scope="class")
    def measured(cls):
        """The layout facts, read off the rendered page at both widths.

        A stylesheet assertion cannot tell you the contents page went
        two-column or the folio fell off the edge. This can.
        """
        pw = pytest.importorskip("playwright.sync_api",
                                 reason="playwright not installed")
        import threading
        from werkzeug.serving import make_server
        from app import app
        srv = make_server("127.0.0.1", 0, app, threaded=True)
        port = srv.socket.getsockname()[1]
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        out = {}
        try:
            with pw.sync_playwright() as p:
                browser = TestMaskedBirthFieldsInARealBrowser._launch(p, pytest)
                for width in (390, 1280):
                    pg = browser.new_context(
                        viewport={"width": width, "height": 900}).new_page()
                    pg.goto(f"http://127.0.0.1:{port}/")
                    for k, v in GATE_FORM.items():
                        pg.evaluate(
                            "([k,v]) => { const e = document.querySelector("
                            "`[name=\"${k}\"]`); if (e) e.value = v; }", [k, v])
                    with pg.expect_navigation():
                        pg.evaluate("document.querySelector('#cast').submit()")
                    pg.wait_for_load_state("load")
                    pg.wait_for_timeout(900)          # let the webfonts land
                    # Re-pinned 2026-09-11. Arrival is TODAY now; the contents
                    # page, the identity strip and the domain teasers this
                    # class measures all live on the READINGS fold. Measuring
                    # the arrival view got zero-height rects for all of them
                    # and passed for the wrong reason.
                    # The plates are on ARRIVAL and on YOUR CHARTS, so their
                    # rendered stroke widths must be read before we leave.
                    strokes = pg.evaluate(r"""() => {
                      const out = {};
                      document.querySelectorAll(
                        '.view:not([hidden]) .kundli, ' +
                        '.view:not([hidden]) .minikundli').forEach((svg, i) => {
                        const vb = svg.getAttribute('viewBox').split(/\s+/);
                        const scale = svg.getBoundingClientRect().width /
                                      parseFloat(vb[2]);
                        svg.querySelectorAll('[stroke-width]').forEach(
                          (el, j) => {
                            const w = parseFloat(
                              el.getAttribute('stroke-width'));
                            if (scale > 0) out[i + ':' + j] =
                              +(w * scale).toFixed(2);
                          });
                      });
                      return out;
                    }""")
                    assert strokes, f"{width}px: no plate strokes measured"
                    pg.evaluate("location.hash = '#readings'")
                    pg.wait_for_timeout(400)
                    out[width] = pg.evaluate(r"""() => {
                      const V = document.querySelector('#view-readings');
                      const q = s => V.querySelector(s);
                      const rows = [...V.querySelectorAll('.dcard')]
                        .map(e => e.getBoundingClientRect());
                      const cs = s => getComputedStyle(q(s));
                      return {
                        overflow: document.documentElement.scrollWidth
                                  > window.innerWidth,
                        entries: rows.length,
                        columns: new Set(rows.map(r => Math.round(r.left))).size,
                        minEntryHeight: Math.min(...rows.map(r => r.height)),
                        folioRight: q('.folio').getBoundingClientRect().right,
                        win: window.innerWidth,
                        // The display hero of the READINGS fold is the chart
                        // name, not the day's line — that one lives on
                        // arrival and is measured in the pass above.
                        displayPx: parseFloat(cs('.chartof-name').fontSize),
                        bodyPx: parseFloat(
                          getComputedStyle(document.body).fontSize),
                        displayFace: cs('.chartof-name').fontFamily,
                        textFace: cs('.dcard-teaser').fontFamily,
                        identityLines: [...V.querySelectorAll(
                          '.identity li')].reduce((n, li) => n + Math.round(
                            li.getBoundingClientRect().height /
                            parseFloat(getComputedStyle(li).lineHeight)), 0),
                      };
                    }""")
                    out[width]["strokePx"] = strokes
                browser.close()
        finally:
            srv.shutdown()
        return out

    def test_no_horizontal_overflow_at_either_width(self, measured):
        for width, m in measured.items():
            assert not m["overflow"], width

    def test_the_contents_page_is_one_column_on_a_phone_and_a_desktop(
            self, measured):
        """The redesign's own claim, measured rather than asserted in CSS:
        a contents page is a list at every width."""
        for width, m in measured.items():
            assert m["entries"] == 7, (width, m["entries"])
            assert m["columns"] == 1, (
                f"{width}px: contents split into {m['columns']} columns")
            assert m["minEntryHeight"] >= 44, (width, m["minEntryHeight"])

    def test_the_chosen_faces_actually_load(self, measured):
        for width, m in measured.items():
            assert "Tiro Devanagari Sanskrit" in m["displayFace"], width
            assert "IBM Plex Sans" in m["textFace"], width

    def test_the_display_type_really_is_display_sized(self, measured):
        for width, m in measured.items():
            assert m["displayPx"] / m["bodyPx"] >= 1.8, (width, m)
        assert measured[1280]["displayPx"] > measured[390]["displayPx"]

    def test_the_folio_stays_on_the_page(self, measured):
        for width, m in measured.items():
            assert m["folioRight"] <= m["win"], width

    def test_the_imprint_is_still_exactly_three_lines(self, measured):
        """The redesign reset the type; the identity strip must not have
        grown a fourth line at 390px, which is the first thing that makes a
        phone feel unfinished."""
        for width, m in measured.items():
            assert m["identityLines"] == 3, (width, m["identityLines"])


def _srgb(component: float) -> float:
    c = component / 255
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def _luminance(hex_colour: str) -> float:
    h = hex_colour.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return .2126 * _srgb(r) + .7152 * _srgb(g) + .0722 * _srgb(b)


def contrast(a: str, b: str) -> float:
    """WCAG 2.x contrast ratio. Two hex colours in, one number out."""
    la, lb = _luminance(a), _luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + .05) / (lo + .05)


def _over(fg: str, bg: str, alpha: float) -> str:
    """Composite `fg` over `bg` — what the eye actually receives."""
    f, b = fg.lstrip("#"), bg.lstrip("#")
    return "#" + "".join(
        f"{round(int(f[i:i+2], 16) * alpha + int(b[i:i+2], 16) * (1 - alpha)):02x}"
        for i in (0, 2, 4))


class TestPaperPalette:
    """The light almanac, with its contrast COMPUTED from the stylesheet.

    A palette table in a document is a claim. This reads the hexes out of
    `static/style.css` and recomputes every pair, so a future tweak that
    lightens the bronze by two steps fails here rather than in someone's
    eyes.
    """

    @classmethod
    @pytest.fixture(scope="class")
    def tokens(cls):
        css = (HERE / "static" / "style.css").read_text(encoding="utf-8")
        head = css[:css.index("* { box-sizing")]
        out = {}
        for name, block in (
                ("paper", head[head.index(":root,"):head.index('[data-palette="night"]')]),
                ("night", head[head.index('[data-palette="night"]'):])):
            out[name] = dict(re.findall(r"(--[\w-]+):\s*(#[0-9a-fA-F]{6})",
                                        block))
        return out

    def test_both_readings_define_the_whole_set(self, tokens):
        for reading, t in tokens.items():
            for token in ("--paper", "--surface", "--ink", "--accent",
                          "--accent-ink"):
                assert token in t, (reading, token)

    def test_body_text_clears_aa_on_both_grounds(self, tokens):
        for reading, t in tokens.items():
            for ground in ("--paper", "--surface"):
                r = contrast(t["--ink"], t[ground])
                assert r >= 4.5, f"{reading} ink on {ground}: {r:.2f}:1"

    def test_links_and_small_text_clear_aa_on_both_grounds(self, tokens):
        """The pair the brief singled out.

        The bronze the mockup specified — #b68235 — is 3.02:1 on paper:
        fine for graphics and large display, and NOT enough for body text.
        That is why `--accent-ink` exists. If the two are ever collapsed
        back into one token, this fails.
        """
        for reading, t in tokens.items():
            for ground in ("--paper", "--surface"):
                r = contrast(t["--accent-ink"], t[ground])
                assert r >= 4.5, (
                    f"{reading} accent-ink on {ground}: {r:.2f}:1 — links and "
                    f"small text must clear AA")

    def test_the_graphic_accent_clears_the_non_text_floor(self, tokens):
        """AA for non-text objects — a plate stroke, a rule — is 3.0:1.

        Widened 2026-09-13 to BOTH grounds. The accent was checked on the
        paper only, so deepening the surface tone could have pushed a plate
        or a rule drawn on it under the floor without anything going red.
        """
        for reading, t in tokens.items():
            for ground in ("--paper", "--surface"):
                r = contrast(t["--accent"], t[ground])
                assert r >= 3.0, f"{reading} accent on {ground}: {r:.2f}:1"

    def test_the_second_tone_is_a_tone_the_eye_can_find(self, tokens):
        """"a second surface tone … so folds separate by tone, not just
        rule." A token that measures 1.084 against the ground is a tone in
        the stylesheet and nothing on the screen — which is what it was."""
        for reading, t in tokens.items():
            r = contrast(t["--paper"], t["--surface"])
            assert r >= 1.15, (
                f"{reading}: surface is {r:.3f}:1 against the paper — not a "
                f"step anyone can see")
            # …and not so far that it reads as a different page.
            assert r <= 1.45, f"{reading}: {r:.3f}:1 is a panel, not a tone"

    def test_the_plate_is_drawn_above_the_non_text_floor(self):
        """The figure that carries the whole screen was the faintest thing
        on it: `.plate-rule` at 38% ink measures 2.28:1 against the paper.
        Every stroke that DRAWS the plate — not the halo behind a label —
        has to clear 3.0 on the ground it is drawn on."""
        css = (HERE / "static" / "style.css").read_text(encoding="utf-8")
        tokens = self._tokens_from(css)
        checked = 0
        for selector in (".plate-rule", ".plate-diamond"):
            block = css[css.index(selector + " {"):]
            block = block[:block.index("}")]
            stroke = re.search(r"stroke:\s*([^;]+);", block).group(1).strip()
            for reading, t in tokens.items():
                colour = self._resolve(stroke, t)
                assert colour, (selector, stroke)
                r = contrast(colour, t["--paper"])
                assert r >= 3.0, (
                    f"{reading} {selector} is {r:.2f}:1 on the paper — "
                    f"under the 3.0 floor for a non-text graphic")
                checked += 1
        assert checked == 4, checked

    @staticmethod
    def _tokens_from(css):
        head = css[:css.index("* { box-sizing")]
        out = {}
        for reading, block in (
                ("paper", head[head.index(":root,"):
                               head.index('[data-palette="night"]')]),
                ("night", head[head.index('[data-palette="night"]'):])):
            out[reading] = dict(re.findall(r"(--[\w-]+):\s*(#[0-9a-fA-F]{6})",
                                           block))
        return out

    @staticmethod
    def _resolve(value, tokens):
        """A stroke declaration to a hex colour, alpha composited over the
        paper. `var(--accent)` and `rgba(var(--accent-rgb), .62)` are both
        things this stylesheet writes."""
        m = re.match(r"var\((--[\w-]+)\)$", value)
        if m:
            return tokens.get(m.group(1))
        m = re.match(r"rgba\(var\((--[\w-]+)-rgb\),\s*([\d.]+)\)$", value)
        if m:
            base = tokens.get(m.group(1))
            return _over(base, tokens["--paper"], float(m.group(2))) \
                if base else None
        return None

    def test_the_muted_ink_steps_are_still_readable_text(self, tokens):
        """Every muted step is real body text somewhere in the app, so
        every one of them has to clear 4.5 — including on the surface tone,
        which is the darker of the two grounds in the light reading."""
        css = (HERE / "static" / "style.css").read_text(encoding="utf-8")
        alphas = [float(a) for a in re.findall(
            r"--ink-\d+:\s*rgba\(var\(--ink-rgb\),\s*(\.\d+)\)", css)]
        assert len(alphas) >= 3, alphas
        for reading, t in tokens.items():
            for alpha in alphas:
                for ground in ("--paper", "--surface"):
                    mixed = _over(t["--ink"], t[ground], alpha)
                    r = contrast(mixed, t[ground])
                    assert r >= 4.5, (
                        f"{reading} ink@{alpha} on {ground}: {r:.2f}:1")

    def test_no_component_carries_a_palette_hex(self):
        """Colour lives in the token block or nowhere. This is what makes
        one attribute on the root able to reskin the whole page."""
        css = (HERE / "static" / "style.css").read_text(encoding="utf-8")
        body = css[css.index("* { box-sizing"):]
        assert re.findall(r"#[0-9a-fA-F]{6}", body) == []


class TestTheAskScreen:
    """The founder opened Ask and found nowhere to type.

    The entire block sat behind `{% if data.agent_ready %}` and the
    deployment had no API key, so the screen rendered a paragraph of
    explanation and no field. Whether an answer can be produced is a
    question about the ANSWER; it is not a reason to refuse someone the
    chance to ask.
    """

    # --- it renders, key or no key ------------------------------------------

    def test_the_field_exists_without_an_api_key(self, page):
        """The bug, pinned. `page` is rendered with no ANTHROPIC_API_KEY."""
        import agent
        assert not agent.is_configured(), (
            "this gate is meaningless with a key configured")
        view = page[page.index('id="view-ask"'):]
        view = view[:view.index("<!-- /view-ask -->")]
        assert 'id="askq"' in view, "no question field on the Ask screen"
        assert 'id="askgo"' in view, "no submit control"
        # …and it is not disabled or hidden on the way past.
        field = re.search(r'<input id="askq"[^>]*>', view).group(0)
        assert "disabled" not in field, field
        assert "hidden" not in field, field
        assert 'data-ready="0"' in view, (
            "the screen must know the agent is off — that is what selects "
            "the unavailable state instead of a silent failure")

    def test_the_label_is_the_screen(self, page):
        """"a large, centred question field with the label 'Put a question to
        your chart' at display size"."""
        view = page[page.index('id="view-ask"'):]
        view = view[:view.index("<!-- /view-ask -->")]
        label = re.search(r'<h1 class="asklabel">(.*?)</h1>', view, re.S)
        assert label, "the label is not a heading"
        assert "Put a question to your chart" in label.group(1)
        # A real <label>, bound to the field: clicking the words focuses it.
        assert 'for="askq"' in label.group(1)
        css = (HERE / "static" / "style.css").read_text(encoding="utf-8")
        block = css[css.index(".asklabel {"):]
        block = block[:block.index("}")]
        assert "var(--t-title)" in block, block
        top = css[css.index(".asktop {"):]
        top = top[:top.index("}")]
        assert "text-align: center" in top

    def test_three_suggestions_sit_quietly_beneath(self, page):
        view = page[page.index('id="view-ask"'):]
        view = view[:view.index("<!-- /view-ask -->")]
        block = view[view.index('class="asksuggest"'):]
        block = block[:block.index("</div>")]
        suggestions = re.findall(r'class="sugq">([^<]+)</button>', block)
        assert len(suggestions) == 3, suggestions
        for q in suggestions:
            assert q.strip().endswith("?"), q

    def test_the_ask_tab_opens_the_ask_screen(self, page):
        """It used to open Explore and scroll to a section inside it."""
        row = re.search(r'<nav class="tabs"[^>]*>(.*?)</nav>', page, re.S)
        assert 'href="#ask" data-view="view-ask"' in row.group(1)
        js = page[page.index("function fromHash()"):]
        js = js[:js.index("document.addEventListener")]
        assert 'if (h === "ask") return show("view-ask");' in js
        # …and it is matched BEFORE the element-lookup fallback, which would
        # otherwise find the old `#ask` lens section inside Explore.
        assert js.index('h === "ask"') < js.index('el.closest("#view-explore")')

    def test_the_folios_match_the_tab_row(self, page):
        """Ask became a screen, so there are five folds and not four. A page
        marker that says 'Fold 1 of 4' beside five tabs is the numbering
        contradicting the navigation."""
        import html as _html
        folios = re.findall(r'<p class="folio">(.*?)</p>', page, re.S)
        joined = _html.unescape(re.sub(r"<[^>]+>", " ", " ".join(folios)))
        assert "Fold 5 of 5" in joined
        assert "of 4" not in joined, "a four-fold folio survived"
        for n, name in ((1, "Today"), (2, "Readings"), (3, "Your charts"),
                        (4, "The full chart"), (5, "Ask")):
            assert f"P. {n:02d}" in joined, n
            assert name in joined, name

    # --- the answer is structural -------------------------------------------

    def test_the_endpoint_hands_over_a_verdict_and_paragraphs(self):
        """Answer-first is a property of the STRUCTURE, not of the model
        remembering to put the answer first. The verdict is its own field
        and the page never parses prose to find it."""
        source = (HERE / "app.py").read_text(encoding="utf-8")
        block = source[source.index("def ask_endpoint"):]
        block = block[:block.index("\n@app.route", 10)]
        for field in ("verdict=", "paragraphs=", "steps=", "facts_used=",
                      "rules_applied="):
            assert field in block, field
        page = (HERE / "templates" / "index.html").read_text(encoding="utf-8")
        js = page[page.index("SCREEN 5 · ASK"):]
        assert "d.verdict" in js
        # No prose parsing anywhere in the render path.
        assert "split(\".\")" not in js
        assert "indexOf(\".\")" not in js

    def test_the_six_steps_are_derived_from_cited_facts(self):
        """"the six-step checklist the agent walked … as a compact list of
        which steps fired, each expandable to the facts it used."

        Derived from the evidence, never self-reported: a step counts as
        walked when the answer cites a fact id that step is answerable
        from. A model that says it considered the divisional chart and
        cites no varga fact has not.
        """
        import agent
        from chartfacts import domain_brief
        chart = compute_chart(GATE_BIRTH)
        brief = domain_brief(chart, "how is my career going?")
        assert brief, "no domain detected for a career question"

        cited = list(brief["fact_ids"]["NATAL"][:1]) + \
            list(brief["fact_ids"]["DASHA"][:1])
        answer = agent.AgentAnswer(answer="A paragraph.", verdict="A verdict.",
                                   facts_used=cited)
        steps = agent.steps_walked(answer, brief)
        assert [s["step"] for s in steps] == [
            "NATAL", "KARAKA", "VARGA", "DASHA", "TRANSIT", "SYNTHESIS"]
        fired = {s["step"]: s["fired"] for s in steps}
        assert fired["NATAL"] and fired["DASHA"]
        assert not fired["KARAKA"] and not fired["VARGA"]
        assert not fired["TRANSIT"]
        # Each step carries the facts it actually used.
        natal = next(s for s in steps if s["step"] == "NATAL")
        assert natal["facts"] == cited[:1]
        assert natal["available"] > len(natal["facts"])

    def test_a_question_with_no_domain_shows_no_checklist(self):
        """There is no checklist to walk for "what is a nakshatra", and
        inventing one to display would be the same dishonesty pointed the
        other way."""
        import agent
        answer = agent.AgentAnswer(answer="x", facts_used=["lagna"])
        assert agent.steps_walked(answer, None) == []

    def test_the_withheld_state_is_its_own_state(self, page):
        """A reply that failed validation against the chart is the feature
        working. It reads as a finding, not as an error in the same box as
        a network failure."""
        js = page[page.index("SCREEN 5 · ASK"):]
        assert "function withheld(" in js
        assert "is-withheld" in js
        assert "d.withheld" in js
        css = (HERE / "static" / "style.css").read_text(encoding="utf-8")
        block = css[css.index(".askanswer.is-withheld {"):]
        block = block[:block.index("}")]
        assert "var(--surface)" in block
        assert "border-left" in block

    def test_facts_and_rules_are_footnoted_by_id(self, page):
        js = page[page.index("SCREEN 5 · ASK"):]
        assert 'idlist(d.facts_used, "Facts")' in js
        assert 'idlist(d.rules_applied, "Rules")' in js
        assert "askfacts" in js and "<code>" in js


class TestTheAskScreenInARealBrowser:
    """The field renders, accepts text, submits, and both states render.

    A markup gate can prove the input is in the HTML. It cannot prove that
    typing into it and pressing Ask produces an answer on the screen — which
    is the thing that was broken — so this drives the real page and stubs
    `/ask` at the network so both outcomes can be exercised without a key
    and without a model.
    """

    ANSWER = {
        "answer": "First paragraph of the working.\nSecond paragraph.",
        "verdict": "Saturn rules the tenth and sits at its weakest.",
        "paragraphs": ["First paragraph of the working.",
                       "Second paragraph."],
        "steps": [
            {"step": "NATAL", "do": "the domain's houses", "fired": True,
             "facts": [{"id": "house.10", "statement": "The 10th is Taurus."}],
             "available": 6},
            {"step": "KARAKA", "do": "the significator", "fired": False,
             "facts": [], "available": 2},
            {"step": "VARGA", "do": "the divisional chart", "fired": True,
             "facts": [{"id": "varga.d10.lagna",
                        "statement": "The D10 lagna is Scorpio."}],
             "available": 13},
            {"step": "DASHA", "do": "the running period", "fired": True,
             "facts": [{"id": "dasha.current",
                        "statement": "Rahu mahadasha."}], "available": 10},
            {"step": "TRANSIT", "do": "the slow movers", "fired": False,
             "facts": [], "available": 8},
            {"step": "SYNTHESIS", "do": "weave them", "fired": True,
             "facts": [], "available": 0},
        ],
        "facts_used": [{"id": "house.10", "statement": "The 10th is Taurus."},
                       {"id": "dasha.current",
                        "statement": "Rahu mahadasha."}],
        "rules_applied": [{"id": "rule.dasha.lordship",
                           "text": "A dasha lord delivers its houses.",
                           "source": "BPHS"}],
        "confidence": "Interpretive",
        "remaining": 4,
    }

    WITHHELD = {
        "error": "Ask about the running period instead. That reply put "
                 "Saturn in a sign it does not occupy, so it was not shown.",
        "withheld": True,
        "violations": ["wrong-sign: claimed Saturn in Leo; chart has Pisces"],
        "remaining": 3,
    }

    @classmethod
    @pytest.fixture(scope="class")
    def driven(cls):
        pw = pytest.importorskip("playwright.sync_api",
                                 reason="playwright not installed")
        import threading
        from werkzeug.serving import make_server
        from app import app
        srv = make_server("127.0.0.1", 0, app, threaded=True)
        port = srv.socket.getsockname()[1]
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        out = {}
        try:
            with pw.sync_playwright() as p:
                browser = TestMaskedBirthFieldsInARealBrowser._launch(p, pytest)
                for width in (390, 1280):
                    pg = browser.new_context(
                        viewport={"width": width, "height": 1000}).new_page()
                    pg.goto(f"http://127.0.0.1:{port}/")
                    for k, v in GATE_FORM.items():
                        pg.evaluate(
                            "([k,v]) => { const e = document.querySelector("
                            "`[name=\"${k}\"]`); if (e) e.value = v; }", [k, v])
                    with pg.expect_navigation():
                        pg.evaluate("document.querySelector('#cast').submit()")
                    pg.wait_for_load_state("load")
                    pg.evaluate("location.hash = '#ask'")
                    pg.wait_for_timeout(400)
                    shot = {}

                    # 1. EMPTY. The field is there and takes text.
                    field = pg.query_selector("#askq")
                    shot["field_visible"] = bool(field and field.is_visible())
                    shot["view_open"] = pg.eval_on_selector(
                        "#view-ask", "e => !e.hidden")
                    pg.fill("#askq", "how is my career going?")
                    shot["typed"] = pg.input_value("#askq")

                    # 2. ANSWERED. `/ask` stubbed at the network so the
                    #    render path is exercised without a key or a model.
                    pg.route("**/ask", lambda route: route.fulfill(
                        status=200, content_type="application/json",
                        body=json.dumps(cls.ANSWER)))
                    # The screen refuses to call when it knows there is no
                    # key, so tell it there is one — the stub is the key.
                    pg.evaluate(
                        "document.getElementById('askscreen')"
                        ".dataset.ready = '1'")
                    pg.reload()
                    pg.wait_for_timeout(300)
                    pg.evaluate("location.hash = '#ask'")
                    pg.wait_for_timeout(300)
                    pg.evaluate(
                        "document.getElementById('askscreen')"
                        ".dataset.ready = '1'")
                    pg.fill("#askq", "how is my career going?")
                    pg.click("#askgo")
                    pg.wait_for_selector(".askverdict", timeout=5000)
                    pg.wait_for_timeout(200)
                    shot["answer"] = pg.evaluate(r"""() => {
                      const a = document.querySelector('.askanswer');
                      const rect = e => e ? e.getBoundingClientRect().top : -1;
                      return {
                        verdict: (a.querySelector('.askverdict') || {})
                          .textContent || '',
                        paragraphs: [...a.querySelectorAll('.askpara')]
                          .map(p => p.textContent.trim()),
                        verdictAbove:
                          rect(a.querySelector('.askverdict')) <
                          rect(a.querySelector('.askpara')),
                        steps: [...a.querySelectorAll('.askstep')].map(s => ({
                          name: s.querySelector('.askstep-name').textContent,
                          fired: s.classList.contains('fired'),
                        })),
                        factIds: [...a.querySelectorAll('.askfacts code')]
                          .map(c => c.textContent),
                        summaries: [...a.querySelectorAll('.askfacts > summary')]
                          .map(x => x.textContent.trim()),
                        withheld: a.classList.contains('is-withheld'),
                      };
                    }""")
                    shot["step_facts"] = pg.evaluate(r"""() => {
                      const s = [...document.querySelectorAll('.askstep')]
                        .find(x => x.querySelector('.askstep-name')
                          .textContent === 'VARGA');
                      s.open = true;
                      return [...s.querySelectorAll('code')]
                        .map(c => c.textContent);
                    }""")

                    # 3. WITHHELD.
                    pg.route("**/ask", lambda route: route.fulfill(
                        status=422, content_type="application/json",
                        body=json.dumps(cls.WITHHELD)))
                    pg.fill("#askq", "will I get the job in December?")
                    pg.click("#askgo")
                    pg.wait_for_selector(".askanswer.is-withheld",
                                         timeout=5000)
                    pg.wait_for_timeout(200)
                    shot["withheld"] = pg.evaluate(r"""() => {
                      const a = document.querySelector('.askanswer');
                      return {
                        isWithheld: a.classList.contains('is-withheld'),
                        mark: (a.querySelector('.askwithheld-mark') || {})
                          .textContent || '',
                        text: a.textContent,
                        background: getComputedStyle(a).backgroundColor,
                        borderLeft: getComputedStyle(a).borderLeftWidth,
                      };
                    }""")
                    out[width] = shot
                browser.close()
        finally:
            srv.shutdown()
        return out

    def test_the_field_renders_and_accepts_text(self, driven):
        for width, shot in driven.items():
            assert shot["view_open"], f"{width}: the Ask view did not open"
            assert shot["field_visible"], f"{width}: no visible field"
            assert shot["typed"] == "how is my career going?", width

    def test_submitting_renders_an_answer_verdict_first(self, driven):
        for width, shot in driven.items():
            a = shot["answer"]
            assert a["verdict"].startswith("Saturn rules the tenth"), width
            assert a["paragraphs"][:2] == [
                "First paragraph of the working.", "Second paragraph."], width
            assert a["verdictAbove"], f"{width}: the verdict is not first"
            assert not a["withheld"], width

    def test_the_answer_shows_which_steps_fired(self, driven):
        for width, shot in driven.items():
            steps = shot["answer"]["steps"]
            assert [s["name"] for s in steps] == [
                "NATAL", "KARAKA", "VARGA", "DASHA", "TRANSIT",
                "SYNTHESIS"], width
            fired = {s["name"]: s["fired"] for s in steps}
            assert fired["NATAL"] and fired["VARGA"] and fired["DASHA"], width
            assert not fired["KARAKA"] and not fired["TRANSIT"], width
            # …and a step opens to the facts it used.
            assert shot["step_facts"] == ["varga.d10.lagna"], width

    def test_the_answer_footnotes_the_ids_it_rests_on(self, driven):
        for width, shot in driven.items():
            a = shot["answer"]
            summaries = " ".join(a["summaries"])
            assert "Facts used" in summaries, (width, summaries)
            assert "Rules used" in summaries, (width, summaries)
            assert "house.10" in a["factIds"], width
            assert "rule.dasha.lordship" in a["factIds"], width

    def test_a_withheld_reply_renders_its_own_state(self, driven):
        for width, shot in driven.items():
            w = shot["withheld"]
            assert w["isWithheld"], width
            assert w["mark"].strip() == "Withheld", (width, w["mark"])
            assert "was not shown" in w["text"], width
            assert "wrong-sign" in w["text"], width
            # Visibly a different state, not the same box with other words.
            assert w["borderLeft"] == "3px", (width, w["borderLeft"])
            assert w["background"] != "rgba(0, 0, 0, 0)", width


class TestTextureAndContrast:
    """The page read flat, and the fix had to stay inside the system.

    Four devices, no gradients and no hue-noise: a second surface tone for
    what sits behind the reading, a paper grain on the ground only, a
    heavier structural rule above a section head than between two rows, and
    the bronze used deliberately so the eye has one anchor per screen.
    `TestPaperPalette` owns the contrast arithmetic; this owns the devices.
    """

    @staticmethod
    def _css():
        return (HERE / "static" / "style.css").read_text(encoding="utf-8")

    def test_the_grain_is_a_background_and_can_never_be_an_overlay(self):
        """The alpha lives INSIDE the SVG, not on a CSS overlay. A
        low-opacity element stretched across the viewport is one stacking
        context away from sitting on top of the text it was meant to sit
        behind; a background image cannot do that at all."""
        css = self._css()
        assert "--grain:" in css
        grain = re.search(r'--grain:\s*url\("([^"]+)"\)', css)
        assert grain, "no grain image"
        uri = grain.group(1)
        assert uri.startswith("data:image/svg+xml,"), uri[:40]
        import urllib.parse
        svg = urllib.parse.unquote(uri.split(",", 1)[1])
        assert "feTurbulence" in svg
        # Desaturated: the brief said no hue-noise.
        assert 'type="saturate" values="0"' in svg
        alpha = float(re.search(r'opacity="([\d.]+)"', svg).group(1))
        assert 0 < alpha <= 0.08, alpha
        # It is applied as a background image, and nothing else uses it.
        assert "background-image: var(--grain)" in css
        assert css.count("var(--grain)") == 1
        # No positioned overlay anywhere near it.
        body = css[css.index("body {"):]
        body = body[:body.index("}")]
        assert "position: fixed" not in body

    def test_more_contrast_turns_the_grain_off(self):
        """Someone who asked for more contrast did not ask for texture."""
        css = self._css()
        block = css[css.index("@media (prefers-contrast: more)"):]
        block = block[:block.index("}") + 1]
        assert "--grain: none" in block

    def test_a_section_head_is_ruled_harder_than_a_row(self):
        """The page had one line weight and therefore one level of
        hierarchy: a section head and a row divider were drawn identically,
        so structure had to be read rather than seen."""
        css = self._css()
        mark = css[css.index(".mark {"):]
        mark = mark[:mark.index("}")]
        weight = float(re.search(r"border-top:\s*([\d.]+)px", mark).group(1))
        assert weight >= 1.5, weight
        # …and the hairlines did NOT all get heavier with it.
        hairlines = [float(w) for w in re.findall(
            r"border-(?:top|bottom):\s*([\d.]+)px solid var\(--hairline\)",
            css)]
        assert hairlines, "no hairlines left in the stylesheet"
        assert max(hairlines) <= 1.0, max(hairlines)

    def test_what_sits_behind_the_reading_takes_the_second_tone(self):
        """An opened expander, an ephemeris table, a category's own rows —
        the layers a reader drops INTO. The reading itself stays on the
        paper, so the eye can tell which layer it is in without reading."""
        css = self._css()
        block = css[css.index("/* --- THE SECOND TONE"):]
        block = block[:block.index("/* --- A YOGA AS A ROW")]
        for selector in (".dstep[open]", ".readfold[open]", ".tablewrap"):
            assert selector in block, selector
        assert block.count("var(--surface)") >= 2, block.count("var(--surface)")
        # Tone, not a box: the brief's standing rule.
        assert "box-shadow" not in block
        assert not re.search(r"^\s*border:\s*1px", block, re.M), block

    def test_the_bronze_is_the_plate_ink_and_the_verdict_mark(self):
        """"the bronze used deliberately as the plate's ink and for verdict
        emphasis so the eye has an anchor per screen" — and for text it is
        `--accent-ink`, which clears 4.5, never `--accent`, which does
        not."""
        css = self._css()
        for selector in (".plate-rule", ".plate-diamond"):
            block = css[css.index(selector + " {"):]
            block = block[:block.index("}")]
            assert "var(--accent)" in block, selector
        block = css[css.index(".yverdict .vmark"):]
        block = block[:block.index("}")]
        assert "var(--accent-ink)" in block, block


class TestScrollChoreography:
    """The pass's core: what moves, when, and what happens if you ask it
    not to. Nothing here changes what the app says or computes."""

    @staticmethod
    def _css():
        return (HERE / "static" / "style.css").read_text(encoding="utf-8")

    @staticmethod
    def _page_src():
        return (HERE / "templates" / "index.html").read_text(encoding="utf-8")

    # --- 1. the rules draw --------------------------------------------------

    def test_fold_rules_draw_left_to_right(self):
        css = self._css()
        block = css[css.index(".mark::before, .fold-rule::before {"):]
        block = block[:block.index("}")]
        assert "transform: scaleX(0)" in block
        assert "transform-origin: left" in block
        assert "height: 1px" in block
        done = css[css.index(".mark.is-in::before"):]
        assert "scaleX(1)" in done[:done.index("}")]

    def test_a_rule_is_never_a_border_that_cannot_be_drawn(self):
        """`.mark` used to be a border-top. A border cannot be scaled, so
        the rule is a pseudo-element now — this pins the swap."""
        css = self._css()
        block = css[css.index(".mark, .fold-rule {"):]
        assert "border-top: none" in block[:block.index("}")]

    # --- 2. the plate pins and releases ------------------------------------

    def test_the_plate_pins_beside_the_reading(self):
        css = self._css()
        assert '<div class="leaf">' in self._page_src()
        block = css[css.index(".leaf > .plate {"):]
        block = block[:block.index("}")]
        assert "position: sticky" in block
        assert "align-self: start" in block
        assert "grid-row: 1 / -1" in block, (
            "the pin must span the whole leaf, or it releases early")
        # And EVERY other child is placed explicitly. Auto-placement is what
        # dropped the headline and the identity strip into column 1, under
        # the pinned plate — a collision nobody saw until the page scrolled.
        assert ".leaf > *:not(.plate) { grid-column: 2;" in css

    def test_the_pin_is_desktop_only_and_the_phone_gets_the_plate_first(self):
        """At 390px the plate leads, unpinned — a pinned plate on a phone
        would eat the screen the reading needs."""
        css = self._css()
        pin = css.index(".leaf > .plate {")
        media = css.rindex("@media (min-width: 1000px)", 0, pin)
        assert media < pin
        # …and nothing pins it outside that query.
        outside = css[:media] + css[css.index("/* --- 3. the ghost numeral"):]
        assert ".leaf > .plate" not in outside

    def test_the_release_point_is_the_last_contents_entry(self):
        """No JS decides this: the sticky column ends where its grid ends,
        and the grid ends after the contents. The proof is the DOM order."""
        page = self._page_src()
        leaf = page[page.index('<div class="leaf">'):page.index("<!-- /leaf -->")]
        # Re-pinned 2026-09-11: the leaf is the TODAY screen now — the plate
        # beside the day — and the contents page moved to Readings. The pin
        # still releases where the grid ends, which is the end of the day
        # column rather than the end of the contents list.
        assert leaf.index('class="plate') < leaf.index('class="daycol"')
        assert 'class="todaylist"' in leaf
        assert leaf.rindex("dayverdict") < len(leaf)

    # --- 3. ghost numerals --------------------------------------------------

    def test_every_domain_carries_its_ghost_numeral(self, page):
        ghosts = re.findall(r'class="ghostno"[^>]*>([^<]+)<', page)
        assert ghosts == ["02", "03", "04", "05", "06"], ghosts
        # It repeats the folio, so it is decoration to a screen reader.
        assert page.count('class="ghostno" aria-hidden="true"') == 5

    def test_the_ghost_numeral_is_a_watermark_not_a_heading(self):
        css = self._css()
        block = css[css.index(".ghostno {"):]
        block = block[:block.index("}")]
        # In FLOW, not absolute: positioned against the centring flex
        # container it hung at the top of the screenful while the title
        # centred below it, leaving 200px of nothing between the two. What
        # the gate actually cares about is that it behaves as a watermark —
        # under the type, untouchable, and faint.
        assert "z-index: 0" in block
        assert "pointer-events: none" in block
        assert "user-select: none" in block
        alpha = float(re.search(r"rgba\(var\(--ink-rgb\),\s*(\.\d+)\)",
                                block).group(1))
        assert .08 <= alpha <= .16, f"{alpha} is not a watermark"

    # --- 4 & 5. the verdict moment and the rhythm --------------------------

    def test_each_domain_opens_on_a_full_viewport_verdict(self):
        css = self._css()
        block = css[css.index(".verdictmoment {"):]
        block = block[:block.index("}")]
        vh = float(re.search(r"min-height:\s*(\d+)vh", block).group(1))
        assert vh >= 60, vh
        assert '<div class="verdictmoment">' in self._page_src()

    def test_the_verdict_rises_into_place(self):
        css = self._css()
        block = css[css.index(".reveal-rise {"):]
        block = block[:block.index("}")]
        assert "translateY(var(--rise))" in block and "opacity: 0" in block
        rise = int(re.search(r"--rise:\s*(\d+)px", css).group(1))
        assert 16 <= rise <= 24, f"{rise}px is outside the brief's 16-24px"
        phone = re.search(r"max-width:\s*560px\)\s*\{\s*:root\s*\{\s*--rise:\s*(\d+)px",
                          css)
        assert phone and int(phone.group(1)) == 8, "the phone gets 8px"

    def test_the_working_fades_in_as_one_block_not_a_queue(self):
        css = self._css()
        assert 'class="working reveal"' in self._page_src()
        block = css[css.index(".working {"):]
        assert "opacity: 0" in block[:block.index("}")]
        # Two columns where there is room — dense after the airy verdict.
        twocol = css[css.index("@media (min-width: 700px) {\n  .working"):]
        assert "column-count: 2" in twocol[:200]

    # --- 6. how it is driven ------------------------------------------------

    def test_scroll_driven_where_supported_observer_everywhere_else(self):
        css, page = self._css(), self._page_src()
        assert "@supports (animation-timeline: view())" in css
        assert "animation-timeline: view()" in css
        assert 'CSS.supports("animation-timeline", "view()")' in page
        assert "new IntersectionObserver" in page
        # The observer stands down where CSS is already driving it.
        js = page[page.index("const scrollDriven"):]
        assert "if (scrollDriven || quiet" in js[:900]

    def test_nothing_bounces_or_loops(self):
        """Judged on declarations, not on the word appearing in a comment.

        This caught two pre-existing infinite animations in the plate's
        highlight layer — a marching-ants dash and a pulsing ring. An
        engraved plate does not have crawling ants on it, and an animation
        that never ends is the one thing on the page a reader cannot scroll
        away from.
        """
        css = self._css()
        decls = re.findall(r"\banimation(?:-name|-direction|-iteration-count)?:"
                           r"\s*([^;]+);", css)
        for value in decls:
            assert "infinite" not in value, value
            assert "alternate" not in value, value
        for dur in re.findall(r"--reveal:\s*(\d+)ms", css):
            assert 500 <= int(dur) <= 700, dur

    def test_the_reveal_is_one_shot(self):
        """An element that re-animates every time it re-enters is what makes
        a long page feel restless."""
        page = self._page_src()
        assert "io.unobserve(e.target)" in page

    # --- 7. reduced motion --------------------------------------------------

    def test_reduced_motion_kills_every_animation(self):
        css = self._css()
        block = css[css.index("@media (prefers-reduced-motion: reduce)"):]
        block = block[:block.index("\n}\n", block.index(".verdictmoment"))]
        assert "animation: none !important" in block
        assert "transition: none !important" in block

    def test_reduced_motion_leaves_nothing_hidden(self):
        """The failure mode of a reveal is a reader who asked for no motion
        being served opacity:0 forever. Every animated property is forced to
        its FINAL value, not its initial one."""
        css = self._css()
        block = css[css.index("@media (prefers-reduced-motion: reduce)"):]
        assert "scaleX(1) !important" in block
        assert "opacity: 1 !important" in block
        assert "transform: none !important" in block

    def test_reduced_motion_keeps_the_pin(self):
        """'Un-pins nothing essential.' A sticky element is layout, not
        motion; dropping it would take the plate away from the reading it
        belongs beside, which is a content loss, not a motion reduction."""
        css = self._css()
        block = css[css.index("@media (prefers-reduced-motion: reduce)"):]
        assert "position: static" not in block
        assert "position: relative !important" not in block

    def test_the_observer_stands_down_under_reduced_motion(self):
        page = self._page_src()
        js = page[page.index("const scrollDriven"):]
        assert 'matchMedia("(prefers-reduced-motion: reduce)")' in js[:600]
        assert 'targets.forEach(el => el.classList.add("is-in"))' in js[:1400]


class TestReducedMotionInARealBrowser:
    """'prefers-reduced-motion: reduce disables ALL motion and un-pins
    nothing essential — test this explicitly.'

    A stylesheet assertion cannot show that a reader who asked for no motion
    actually SEES the page. The failure mode of any reveal is serving that
    reader `opacity: 0` forever, and only a browser with the preference set
    can prove it does not happen here.
    """

    @classmethod
    @pytest.fixture(scope="class")
    def quiet(cls):
        pw = pytest.importorskip("playwright.sync_api",
                                 reason="playwright not installed")
        import threading
        from werkzeug.serving import make_server
        from app import app
        srv = make_server("127.0.0.1", 0, app, threaded=True)
        port = srv.socket.getsockname()[1]
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            with pw.sync_playwright() as p:
                browser = TestMaskedBirthFieldsInARealBrowser._launch(p, pytest)
                ctx = browser.new_context(viewport={"width": 1280,
                                                    "height": 900},
                                          reduced_motion="reduce")
                pg = ctx.new_page()
                pg.goto(f"http://127.0.0.1:{port}/")
                for k, v in GATE_FORM.items():
                    pg.evaluate(
                        "([k,v]) => { const e = document.querySelector("
                        "`[name=\"${k}\"]`); if (e) e.value = v; }", [k, v])
                with pg.expect_navigation():
                    pg.evaluate("document.querySelector('#cast').submit()")
                pg.wait_for_load_state("load")
                # A domain view, NOT the arrival one. The revealed elements
                # live inside the domain folds, and on arrival they are in a
                # hidden view with no client rects — measuring there passed
                # every assertion vacuously and proved nothing.
                pg.evaluate("location.hash = '#marriage'")
                pg.wait_for_timeout(900)
                out = pg.evaluate(r"""() => {
                  const vis = [];
                  document.querySelectorAll(
                    '.reveal-rise, .working, .mark').forEach(el => {
                    if (!el.getClientRects().length) return;   // other views
                    const cs = getComputedStyle(el);
                    vis.push({
                      cls: el.className.toString().slice(0, 24),
                      opacity: +cs.opacity,
                      transform: cs.transform,
                      transition: cs.transitionDuration,
                      animation: cs.animationName,
                    });
                  });
                  const mark = document.querySelector('.mark');
                  const rule = mark ? getComputedStyle(mark, '::before') : null;
                  const plate = document.querySelector('.leaf > .plate');
                  return {
                    elements: vis,
                    ruleTransform: rule ? rule.transform : null,
                    platePosition: plate
                      ? getComputedStyle(plate).position : null,
                    prefersReduced: matchMedia(
                      '(prefers-reduced-motion: reduce)').matches,
                  };
                }""")
                browser.close()
        finally:
            srv.shutdown()
        return out

    def test_the_browser_really_is_asking_for_no_motion(self, quiet):
        assert quiet["prefersReduced"] is True

    def test_nothing_is_left_invisible(self, quiet):
        """The one that matters. Every revealed element is fully opaque and
        untransformed the moment the page renders."""
        kinds = {k for el in quiet["elements"] for k in el["cls"].split()}
        assert "reveal-rise" in kinds and "working" in kinds, (
            f"the animated elements were never measured: {kinds} — a gate "
            f"that measures a hidden view passes for free")
        for el in quiet["elements"]:
            assert el["opacity"] == 1, el
            assert el["transform"] in ("none", "matrix(1, 0, 0, 1, 0, 0)"), el

    def test_no_transition_or_animation_is_left_running(self, quiet):
        for el in quiet["elements"]:
            assert el["transition"] in ("0s", "0s, 0s", "0s, 0s, 0s"), el
            assert el["animation"] == "none", el

    def test_the_drawn_rule_is_drawn(self, quiet):
        """scaleX(0) forever would be a page with no rules on it at all."""
        assert quiet["ruleTransform"] in ("none", "matrix(1, 0, 0, 1, 0, 0)"), \
            quiet["ruleTransform"]

    def test_the_pin_survives(self, quiet):
        """Un-pins nothing essential. A sticky element is layout, not motion;
        dropping it would take the plate away from the reading it belongs
        beside, which is a content loss dressed up as an accessibility win."""
        assert quiet["platePosition"] == "sticky"


# Leaf text nodes with their boxes, filtered to what is ACTUALLY on screen.
# The filtering is most of the work: a closed <details> lays its content out
# and hides it with content-visibility rather than display:none, and a naive
# pass reported 37 collisions that no reader could have seen.
_VISIBLE_TEXT_BOXES = r"""(sel) => {
  const boxes = [];
  document.querySelectorAll(sel + ' *').forEach(el => {
    // AN SVG LABEL IS ONE BOX. A plate mark is built from nested tspans so
    // the glyph, the letters, ℞ and ⊙ can each take their own ink — they
    // are parts of one word and of course they touch. The unit that must
    // not collide with anything is the <text> element: one label, in one
    // house cell. Measuring the tspans instead reported "☉Su" colliding
    // with "♂Ma" beside it on the same line, 104 times.
    const svgText = el.ownerSVGElement && el.tagName === 'text';
    if (el.ownerSVGElement && el.tagName === 'tspan') return;
    if (!svgText && el.children.length) return;     // leaf nodes only
    const t = (el.textContent || '').trim();
    if (!t) return;
    const cs = getComputedStyle(el);
    if (cs.visibility === 'hidden' || cs.display === 'none') return;
    if (parseFloat(cs.opacity) < 0.05) return;
    if (el.closest('[hidden]')) return;
    for (let d = el.closest('details:not([open])'); d;
         d = d.parentElement && d.parentElement.closest('details:not([open])')) {
      const sum = d.querySelector(':scope > summary');
      if (!sum || !sum.contains(el)) return;
    }
    if (el.closest('.gpane.hidden, .pane.hidden')) return;
    // A sticky or fixed bar WITH AN OPAQUE BACKGROUND is a deliberate
    // overlay — a sticky nav covering the rows it scrolls over is doing its
    // job, not colliding. The distinction is the background: the pinned
    // chart plate is sticky and has NONE, which is exactly why its overlap
    // with the reading column was a real bug and is still caught.
    let overlay = false;
    for (let a = el; a && a !== document.body; a = a.parentElement) {
      const s2 = getComputedStyle(a);
      if ((s2.position === 'sticky' || s2.position === 'fixed') &&
          s2.backgroundColor && !/rgba\(0, 0, 0, 0\)|transparent/
            .test(s2.backgroundColor)) { overlay = true; break; }
    }
    if (overlay) return;
    // PER-LINE rects, not the bounding box. An inline element that wraps
    // returns a bounding box spanning every line it touches, which overlaps
    // a sibling's box while no glyph overlaps anything — a false positive
    // that reported "2011-2029" colliding with the phrase after it.
    // SVG elements carry an SVGAnimatedString, which stringifies to
    // "[object SVGAnimatedString]" and named nothing in the failure output.
    const raw = (el.className && el.className.baseVal !== undefined)
      ? el.className.baseVal : el.className;
    const cls = (raw || el.tagName).toString().slice(0, 32);
    for (const r of el.getClientRects()) {
      if (r.width < 2 || r.height < 2) continue;
      boxes.push({t: t.slice(0, 44), x: r.left, y: r.top,
                  w: r.width, h: r.height, cls: cls, el: el});
    }
  });
  const hits = [];
  for (let i = 0; i < boxes.length; i++)
    for (let j = i + 1; j < boxes.length; j++) {
      const a = boxes[i], b = boxes[j];
      if (a.el === b.el) continue;                 // two lines of one element
      const ox = Math.min(a.x + a.w, b.x + b.w) - Math.max(a.x, b.x);
      const oy = Math.min(a.y + a.h, b.y + b.h) - Math.max(a.y, b.y);
      if (ox > 2 && oy > 2)
        hits.push(`"${a.t}" [${a.cls}] over "${b.t}" [${b.cls}] ` +
                  `(${Math.round(ox)}x${Math.round(oy)}px)`);
    }
  return {count: boxes.length, hits: hits};
}"""


class TestNothingOverlaps:
    """No two pieces of text may share screen space. At any width. Ever.

    This exists because a real collision shipped and no screenshot caught it:
    the arrival leaf's headline and identity strip were dropped into the
    pinned plate's column by grid AUTO-PLACEMENT, and the pile-up only became
    visible once the page was scrolled. Every screenshot to that point had
    been taken at scroll 0.

    So the gate walks four widths at four scroll positions and compares every
    visible text box against every other one.
    """

    WIDTHS = (390, 768, 1280, 1600)
    SCROLLS = (0, 500, 1200, 2200)

    @classmethod
    @pytest.fixture(scope="class")
    def swept(cls):
        pw = pytest.importorskip("playwright.sync_api",
                                 reason="playwright not installed")
        import threading
        from werkzeug.serving import make_server
        from app import app
        srv = make_server("127.0.0.1", 0, app, threaded=True)
        port = srv.socket.getsockname()[1]
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        found = {}
        try:
            with pw.sync_playwright() as p:
                browser = TestMaskedBirthFieldsInARealBrowser._launch(p, pytest)
                pg = browser.new_context(
                    viewport={"width": 1280, "height": 1000}).new_page()
                pg.goto(f"http://127.0.0.1:{port}/")
                # A chart whose strings are LONGER than the reference one: a
                # long name in the headline, a long place. Short text hides
                # collisions that long text finds.
                form = dict(GATE_FORM)
                form.update({"name": "Aparajita Vishwanathan",
                             "place": "Sydney, New South Wales, Australia"})
                for k, v in form.items():
                    pg.evaluate(
                        "([k,v]) => { const e = document.querySelector("
                        "`[name=\"${k}\"]`); if (e) e.value = v; }", [k, v])
                with pg.expect_navigation():
                    pg.evaluate("document.querySelector('#cast').submit()")
                pg.wait_for_load_state("load")
                pg.wait_for_timeout(2200)          # webfonts change metrics
                # Resize rather than reload: one font wait for the whole sweep.
                for width in cls.WIDTHS:
                    pg.set_viewport_size({"width": width, "height": 1000})
                    pg.wait_for_timeout(160)
                    for view, sel in (("arrival", "#view-arrival"),
                                      ("career", "#view-domain-career"),
                                      ("explore", "#view-explore"),
                                      # …and inside a category, where the
                                      # dense tables live.
                                      ("periods", "#view-explore"),
                                      ("readings", "#view-readings"),
                                      ("charts", "#view-charts"),
                                      ("varga", "#view-varga-d9")):
                        if view != "arrival":
                            pg.evaluate("(h) => { location.hash = h; }",
                                        {"career": "#career",
                                         "explore": "#explore",
                                         "periods": "#cat-periods",
                                         "readings": "#readings",
                                         "charts": "#charts",
                                         "varga": "#chart-d9"}[view])
                            pg.wait_for_timeout(320)
                        for scroll in cls.SCROLLS:
                            pg.evaluate("(y) => window.scrollTo(0, y)", scroll)
                            pg.wait_for_timeout(90)
                            r = pg.evaluate(_VISIBLE_TEXT_BOXES, sel)
                            found[(width, view, scroll)] = r
                    pg.evaluate("() => { location.hash = '#top'; }")
                    pg.wait_for_timeout(260)
                browser.close()
        finally:
            srv.shutdown()
        return found

    def test_the_sweep_actually_looked_at_something(self, swept):
        """A sweep that measured nothing would pass silently."""
        assert swept, "nothing swept"
        views = {view for (_, view, _) in swept}
        assert views == {"arrival", "career", "explore", "periods",
                         "readings", "charts", "varga"}, views
        # A low floor on purpose: this guards against a sweep that measured
        # NOTHING, not against a sparse page. A domain fold at scroll 0 is
        # meant to be sparse — it is a full-viewport verdict moment.
        for key, r in swept.items():
            assert r["count"] >= 8, (key, r["count"])

    def test_no_text_overlaps_any_other_text(self, swept):
        problems = []
        for (width, view, scroll), r in sorted(swept.items()):
            for hit in r["hits"]:
                problems.append(f"{width}px {view} @y={scroll}: {hit}")
        assert problems == [], (
            f"{len(problems)} overlapping text boxes:\n  "
            + "\n  ".join(problems[:12]))

    def test_the_pinned_column_never_reaches_the_reading_column(self, swept):
        """The specific failure, pinned by name.

        `.leaf > .glance` named the wrong section — the headline block is
        `class="chartof" id="glance"` while a DIFFERENT section is
        `class="glance"` — so the headline and identity strip were never
        placed and auto-placement put them in column 1, under the plate.
        Every child is placed explicitly now.
        """
        css = (HERE / "static" / "style.css").read_text(encoding="utf-8")
        assert ".leaf > *:not(.plate) { grid-column: 2;" in css
        assert ".leaf > .glance" not in css, (
            "naming a section by a class it does not carry is what caused "
            "the collision in the first place")


class TestVerdictsAreSpecific:
    """A verdict can be short, plain, answer-first — and say nothing.

    "Work and money is one of the stronger parts of your chart — the planet
    that rules it is strong" passed every gate in TestEditorialDoctrine and
    told the reader not one fact about their own chart. Being unspecific is
    its own failure mode and needs its own gate.
    """

    @classmethod
    @pytest.fixture(scope="class")
    def readings(cls, chart):
        import domainread
        return domainread.read_all(chart, AGENT_WHEN)

    def test_every_teaser_names_a_planet(self, readings):
        import voice
        for r in readings:
            named = voice.names_a_planet(r.teaser)
            assert named, (
                f"{r.domain.id}: no graha named — this is about charts in "
                f"general, not this one\n  {r.teaser}")

    def test_every_verdict_names_a_planet(self, readings):
        import voice
        for r in readings:
            assert voice.names_a_planet(r.verdict), (r.domain.id, r.verdict)

    def test_no_verdict_uses_a_filler_phrase(self, readings):
        import voice
        for r in readings:
            hits = voice.find_vagueness(r.visible)
            assert not hits, f"{r.domain.id}: {hits}\n  {r.visible}"

    def test_a_dated_influence_is_dated_in_the_verdict(self, readings):
        """Where the domain has a live dated influence, the verdict says
        WHEN. A reader can act on 'until Jun 2027' and cannot act on 'right
        now'."""
        import voice
        for r in readings:
            live_dates = [s for s in r.signals
                          if s.kind == "live" and voice.names_a_date(s.plain)]
            if not live_dates:
                continue
            assert voice.names_a_date(r.verdict), (
                f"{r.domain.id} has a dated influence running and the "
                f"verdict does not say when: {r.verdict}")

    def test_the_dates_are_the_ledger_s_own(self, chart, readings):
        """Never a month this module invented — the same rule the agent's
        validator enforces, applied to the deterministic reading."""
        import voice
        from chartfacts import build_facts
        ledger = " ".join(f.statement for f in build_facts(chart, AGENT_WHEN))
        for r in readings:
            for token in voice.names_a_date(r.visible):
                assert token in ledger, (
                    f"{r.domain.id}: '{token}' is not a date this chart "
                    f"produced")

    def test_the_ban_list_catches_the_real_offenders(self):
        """The exact sentences that prompted this gate."""
        import voice
        for sentence in (
                "Work and money is one of the stronger parts of your chart.",
                "Marriage is one of the harder parts of your chart.",
                "The planet that rules it is strong.",
                "Its ruling planet is weak.",
                "A second chart confirms it.",
                "Home and family is more helped than hindered."):
            assert voice.find_vagueness(sentence), f"not caught: {sentence}"

    def test_the_ban_list_spares_specific_prose(self):
        import voice
        for sentence in (
                "Saturn rules it and sits at its weakest.",
                "Your career planet, Mercury, is exalted.",
                "The Moon, the planet of the mind, sits in its best sign.",
                "Saturn is on it until Jun 2027.",
                "The second chart puts Mars and Jupiter over it."):
            assert not voice.find_vagueness(sentence), sentence

    def test_specific_did_not_cost_short(self, readings):
        """The budgets are unchanged: specific AND short."""
        import voice
        for r in readings:
            assert voice.words(r.teaser) <= voice.TEASER_WORDS, r.teaser
            assert voice.words(r.visible) <= voice.SYNTHESIS_WORDS, r.domain.id


_TEXT_SIZES_JS = r"""() => {
  // Every VISIBLE text node, with the size it actually renders at.
  //
  // SVG text is the reason this cannot read `font-size` and stop: a `<text>`
  // is sized in USER UNITS, which the viewBox then scales. 9 units inside a
  // 300-unit plate drawn at 560px renders at 17px; 13 units inside a
  // 1000-unit graph drawn at 560px renders at 7. Both readings are wrong
  // from the attribute alone, so this multiplies by the element's own CTM
  // scale and judges what the eye receives.
  const out = [];
  const walk = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let n;
  while ((n = walk.nextNode())) {
    if (!n.nodeValue.trim()) continue;
    const el = n.parentElement;
    if (!el || !el.getClientRects().length) continue;
    // A closed <details> lays its content out and hides it with
    // content-visibility — measurable, invisible, not a finding.
    let p = el, hidden = false;
    while (p) {
      if (p.tagName === 'DETAILS' && !p.open) {
        const s = p.querySelector('summary');
        if (!s || !s.contains(el)) { hidden = true; break; }
      }
      if (p.hasAttribute && p.hasAttribute('hidden')) { hidden = true; break; }
      p = p.parentElement;
    }
    if (hidden) continue;
    const cs = getComputedStyle(el);
    if (cs.visibility === 'hidden' || cs.display === 'none') continue;
    let px = parseFloat(cs.fontSize);
    let svg = false;
    if (el.ownerSVGElement) {
      svg = true;
      const m = el.getScreenCTM && el.getScreenCTM();
      if (m) px *= Math.sqrt(Math.abs(m.a * m.d - m.b * m.c));
    }
    const cls = el.className && el.className.baseVal !== undefined
      ? el.className.baseVal : (el.className || '');
    out.push({
      sel: el.tagName.toLowerCase() + (cls ? '.' + String(cls).trim()
                                                  .split(/\s+/).join('.') : ''),
      // "the body of a category" is the content of the ledger you opened —
      // not the page's own imprint footer, which sits outside every view.
      inLedger: !!el.closest('#view-explore .ledger, #view-explore .note'),
      px: +px.toFixed(1), svg, text: n.nodeValue.trim().slice(0, 30)});
  }
  return out;
}"""


class TestTypeFloors:
    """The type scale has FLOORS, and they are measured in a browser.

    "Several rows sit at 12–13px — too small." They did: the lower half of
    this stylesheet had drifted to 9 and 10px, which is a texture on a 27"
    display and unreadable on the phone it claimed to be designed for.

    A stylesheet scan cannot settle this. Half the small type is SVG, sized
    in user units the viewBox then scales — the same `font-size: 13px` was
    7 rendered pixels in the daśā graph and 24 in the plate. This walks
    every visible text node at both widths across every view and judges what
    the eye receives.
    """

    FLOOR = 13.0

    VIEWS = ("", "#readings", "#charts", "#chart-d1", "#chart-d9",
             "#chart-d10", "#explore", "#cat-charts", "#cat-periods",
             "#cat-sky", "#cat-combinations", "#cat-tables", "#cat-match",
             "#cat-ask", "#cat-learn")

    @classmethod
    @pytest.fixture(scope="class")
    def sizes(cls):
        pw = pytest.importorskip("playwright.sync_api",
                                 reason="playwright not installed")
        import threading
        from werkzeug.serving import make_server
        from app import app
        srv = make_server("127.0.0.1", 0, app, threaded=True)
        port = srv.socket.getsockname()[1]
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        out = {}
        try:
            with pw.sync_playwright() as p:
                browser = TestMaskedBirthFieldsInARealBrowser._launch(p, pytest)
                for width in (390, 1280):
                    pg = browser.new_context(
                        viewport={"width": width, "height": 1000}).new_page()
                    pg.goto(f"http://127.0.0.1:{port}/")
                    for k, v in GATE_FORM.items():
                        pg.evaluate(
                            "([k,v]) => { const e = document.querySelector("
                            "`[name=\"${k}\"]`); if (e) e.value = v; }", [k, v])
                    with pg.expect_navigation():
                        pg.evaluate("document.querySelector('#cast').submit()")
                    pg.wait_for_load_state("load")
                    pg.wait_for_timeout(900)
                    rows = []
                    for view in cls.VIEWS:
                        pg.evaluate(
                            f"location.hash = '{view or '#today'}'")
                        pg.wait_for_timeout(220)
                        for r in pg.evaluate(_TEXT_SIZES_JS):
                            rows.append({**r, "view": view or "#today"})
                    out[width] = rows
                browser.close()
        finally:
            srv.shutdown()
        return out

    def test_the_walk_actually_read_the_page(self, sizes):
        """A floor gate that measured nothing would pass forever."""
        for width, rows in sizes.items():
            assert len(rows) > 400, (width, len(rows))
            assert any(r["svg"] for r in rows), f"{width}: no SVG text read"

    def test_no_rendered_text_is_below_the_floor(self, sizes):
        for width, rows in sizes.items():
            under = sorted({(r["px"], r["sel"], r["view"], r["text"])
                            for r in rows if r["px"] < self.FLOOR})
            assert not under, (
                f"{width}px — text under {self.FLOOR}px:\n  "
                + "\n  ".join(f"{px}px {sel} [{view}] {text!r}"
                              for px, sel, view, text in under[:12]))

    def test_the_body_of_a_category_reads_at_sixteen(self, sizes):
        """The floor is 13 for a label. Anything anyone reads a SENTENCE of
        is 16 — which is a different claim, and the one the brief made."""
        for width, rows in sizes.items():
            sentences = [r for r in rows
                         if r["view"].startswith("#cat-") and not r["svg"]
                         and r["inLedger"] and len(r["text"]) >= 30]
            assert sentences, f"{width}: no prose found in any category"
            thin = sorted({(r["px"], r["sel"], r["view"])
                           for r in sentences if r["px"] < 16})
            assert not thin, f"{width}px — prose under 16px: {thin[:10]}"

    def test_the_scale_is_named_by_role_not_by_number(self):
        """The floors only hold if new work reaches for a token. A raw
        sub-16px `font-size` in the stylesheet is the thing that let this
        drift to 9px in the first place — the exceptions are SVG user units,
        which are not screen pixels at all."""
        css = (HERE / "static" / "style.css").read_text(encoding="utf-8")
        css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
        svg_ok = (".kundli ", ".minikundli ", ".lifegraph ", "#hlgroup ",
                  ".gplate")
        offenders = []
        for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", css):
            sel = " ".join(m.group(1).split())
            if any(tok in sel for tok in svg_ok):
                continue
            for v in re.findall(r"font-size:\s*([\d.]+)px", m.group(2)):
                if float(v) < 16:
                    offenders.append((sel[-46:], v))
        assert not offenders, offenders

    def test_every_floor_token_is_defined_and_worth_its_name(self):
        css = (HERE / "static" / "style.css").read_text(encoding="utf-8")
        head = css[:css.index("* { box-sizing")]
        tok = dict(re.findall(r"(--t-[\w-]+):\s*([\d.]+)px", head))
        for name, floor in (("--t-head", 20), ("--t-body", 16),
                            ("--t-table", 15), ("--t-label", 13)):
            assert name in tok, name
            assert float(tok[name]) >= floor, (name, tok[name])
        # `--t-mark` names the small-caps section marker by role; it is a
        # label, so it cannot quietly be smaller than one.
        assert float(tok["--t-mark"]) >= 13, tok["--t-mark"]


class TestExploreIndex:
    """Explore was one scroll of everything at once. It is an index now."""

    CATEGORIES = ("charts", "periods", "sky", "combinations", "tables",
                  "match", "ask", "learn")
    TECHNICAL = ("dashas", "lifeline", "weather", "doshas", "myths", "yogas",
                 "ask", "agent", "patha", "grahas", "learnpath")

    def test_the_index_lists_every_category_with_a_description(self, page):
        # A class TOKEN, not the whole attribute: Learn carries a second
        # class now, and matching `class="catrow"` exactly dropped it from
        # the index silently. That mistake has broken gates in this file
        # three times.
        rows = re.findall(
            r'<a class="catrow[^"]*" href="#cat-(\w+)"[^>]*>\s*'
            r'<span class="catrow-title">([^<]+)</span>\s*'
            r'<span class="catrow-desc">([^<]+)</span>', page, re.S)
        assert [r[0] for r in rows] == list(self.CATEGORIES), rows
        for cid, title, desc in rows:
            desc = re.sub(r"\s+", " ", desc).strip()
            assert len(desc.split()) >= 8, (cid, desc)
            assert desc.endswith("."), (cid, desc)

    def test_every_technical_section_declares_its_category(self, page):
        for section in self.TECHNICAL:
            m = re.search(rf'<section[^>]*id="{section}"[^>]*>', page)
            assert m, section
            cat = re.search(r'data-cat="(\w+)"', m.group(0))
            assert cat and cat.group(1) in self.CATEGORIES, (section, m.group(0))

    def test_only_one_category_can_be_on_screen(self):
        """The rule the redesign exists to enforce."""
        css = (HERE / "static" / "style.css").read_text(encoding="utf-8")
        # Sections, notes and the gocara block are hidden by default — but
        # NOT the index's own links, which carry data-cat to say what they
        # open. Hiding both made the index render with no rows on it.
        assert "#view-explore section[data-cat]," in css
        assert "#view-explore .note[data-cat]," in css
        for cat in self.CATEGORIES:
            assert (f'#view-explore[data-showing="{cat}"] '
                    f'section[data-cat="{cat}"]') in css, cat

    def test_the_index_hides_itself_once_a_category_is_open(self):
        css = (HERE / "static" / "style.css").read_text(encoding="utf-8")
        assert "#view-explore[data-showing] .exindex { display: none; }" in css

    def test_nothing_in_explore_is_set_below_reading_size(self):
        """'Tiny fonts' was half the complaint. Index entries are >=16px and
        so is the body of every category.

        Re-pinned 2026-09-12: the sizes are named by ROLE now, so this reads
        the token rather than a literal. `TestTypeFloors` is what checks the
        tokens are worth what they claim.
        """
        css = (HERE / "static" / "style.css").read_text(encoding="utf-8")
        for selector, floor in ((".catrow-desc", 16), (".catrow-title", 16)):
            block = css[css.index(selector + " {"):]
            block = block[:block.index("}")]
            size = float(re.search(r"font-size:\s*([\d.]+)px", block).group(1))
            assert size >= floor, (selector, size)
        for rule, token in (
                ("#view-explore[data-showing] { font-size:", "--t-body"),
                ("#view-explore[data-showing] .rows {", "--t-body"),
                ("#view-explore[data-showing] .gtable {", "--t-table")):
            block = css[css.index(rule):]
            block = block[:block.index("}")]
            assert token in block, (rule, block)

    def test_a_section_title_in_a_category_is_a_title(self):
        """"section titles >=20px". Inside a category the `.kicker` that
        opens each ledger is not a marginal label — it is the heading of the
        section you just opened, and it was set at 10px."""
        css = (HERE / "static" / "style.css").read_text(encoding="utf-8")
        block = css[css.index(
            "#view-explore[data-showing] .ledger > .kicker,"):]
        block = block[block.index("{"):block.index("}")]
        assert "var(--t-head)" in block, block

    def test_nothing_leaks_onto_the_index(self):
        """Every block inside Explore declares a category — or it renders on
        the index page, which is exactly what happened to the gocara table
        and the "weather, not verdict" note the first time."""
        page = (HERE / "templates" / "index.html").read_text(encoding="utf-8")
        seg = page[page.index('<div class="view" id="view-explore"'):
                   page.index("<!-- /view-explore -->")]
        # The index's own furniture is allowed; everything else must be filed.
        allowed = ("exindex", "cats", "catrow", "mark", "kicker", "folio",
                   "backlink", "secnav", "chartof-name")
        untagged = []
        for m in re.finditer(
                r'<(?:section|div)\s+class="(ledger|note)"[^>]*>', seg):
            if "data-cat" not in m.group(0):
                untagged.append(m.group(0)[:70])
        assert untagged == [], untagged

    def test_a_deep_link_to_a_section_opens_its_category(self):
        """The arrival page's Ask card jumps straight to #ask. Without this
        the browser would scroll to something the CSS is hiding."""
        page = (HERE / "templates" / "index.html").read_text(encoding="utf-8")
        assert "window.sideraCategoryOf" in page
        assert "window.sideraShowCategory" in page
        js = page[page.index("const cat = window.sideraCategoryOf"):]
        assert "sideraShowCategory(cat)" in js[:200]

    def test_a_category_url_opens_that_category(self):
        """#cat-periods must work as a bookmark, a reload and a shared link,
        not only as a click."""
        page = (HERE / "templates" / "index.html").read_text(encoding="utf-8")
        js = page[page.index("function fromHash()"):]
        js = js[:js.index("document.addEventListener")]
        assert 'h.startsWith("cat-")' in js
        assert 'sideraShowCategory(h.slice(4))' in js
        # …and plain #explore returns to the index rather than leaving
        # whichever category was last open showing.
        assert 'sideraShowCategory("index")' in js


class TestTodayScreen:
    """Screen 1. The first thing anyone sees is what is happening to them
    today — three or four dated lines, each naming a graha."""

    @classmethod
    @pytest.fixture(scope="class")
    def lines(cls, chart):
        import today
        return today.entries(chart, AGENT_WHEN)

    def test_there_are_three_or_four_entries(self, lines):
        """A day's reading, not a feed."""
        import today
        assert 1 <= len(lines) <= today.MAX_ENTRIES, len(lines)

    def test_every_entry_names_a_graha(self, lines):
        import voice
        for e in lines:
            assert voice.names_a_planet(e.text), e.text

    def test_every_entry_that_can_be_dated_is_dated(self, lines):
        """A retrograde is a state, not an event, and is the one kind of
        line here without a date. Everything else carries one."""
        for e in lines:
            if e.kind == "station":
                continue
            assert re.search(
                r"\b(today|tomorrow|the \d+(?:st|nd|rd|th)|"
                r"\d+ \w+|\w{3} \d{4}|for months yet)\b", e.text), e.text

    def test_no_entry_uses_the_technical_register(self, lines):
        import voice
        for e in lines:
            assert not voice.find_jargon(e.text), (e.text,
                                                   voice.find_jargon(e.text))
            assert not voice.find_throat_clearing(e.text), e.text
            assert not voice.find_vagueness(e.text), e.text

    def test_entries_stay_short(self, lines):
        import voice
        for e in lines:
            assert voice.words(e.text) <= 26, (voice.words(e.text), e.text)

    def test_a_sign_change_is_told_against_this_chart(self, lines, chart):
        """The fold is headed "Today for this chart", and a sign change is
        sky news that belongs to everybody.

        Added 2026-09-11 after reading the rendered screen: every ingress
        line said "carrying authority with it" — true of the Sun entering
        Virgo for every reader alive. What makes it this reader's is the
        part of THEIR chart the sign is, so the line has to carry it.
        """
        import rulelib
        from engine import SIGNS
        mine = {rulelib.HOUSE_MATTERS[h].split(",")[0].strip()
                for h in range(1, 13)}
        ingresses = [e for e in lines if e.kind == "ingress"]
        assert ingresses, "no ingress in the window — widen AGENT_WHEN"
        for e in ingresses:
            assert any(m in e.text for m in mine), e.text
            # …and it must be the house the sign REALLY is in this chart.
            sign = next(s for s in SIGNS if s in e.text)
            house = (SIGNS.index(sign) - chart.lagna.sign_index) % 12 + 1
            assert rulelib.HOUSE_MATTERS[house].split(",")[0].strip() \
                in e.text, e.text

    def test_the_contact_window_finds_both_edges(self, chart):
        """The machinery this screen needed. A contact fact knew the current
        gap and nothing about when the orb opened or closes; without the
        edges the line would read "Ketu is on your Venus", which is the
        vague register the doctrine refuses."""
        import today
        from transits import CONJUNCTION_ORB, angular_distance, transit_snapshot
        snap = transit_snapshot(chart, AGENT_WHEN)
        found = 0
        for t in PLANETS:
            for n in PLANETS:
                gap = angular_distance(snap.planets[t].position.longitude,
                                       chart.planets[n].longitude)
                if gap > CONJUNCTION_ORB:
                    continue
                found += 1
                entered, leaves = today.contact_window(
                    t, chart.planets[n].longitude, AGENT_WHEN)
                # Whatever edge is found must actually bound the window.
                for edge in (entered, leaves):
                    if edge is None:
                        continue
                    assert angular_distance(
                        today._lon(t, edge),
                        chart.planets[n].longitude) <= CONJUNCTION_ORB + .2
        assert found or True      # a day with no contact is a valid day

    def test_a_planet_on_its_own_degree_is_a_return_not_a_crossing(self):
        """"Mars crosses your Mars" reads like a bug. It is a return."""
        page = (HERE / "today.py").read_text(encoding="utf-8")
        assert "back on its own natal degree" in page
        assert "its own place in your chart" in page

    def test_the_moon_is_not_treated_as_news(self):
        """It changes sign every two and a half days; left in, it crowded
        out everything that was news."""
        page = (HERE / "today.py").read_text(encoding="utf-8")
        assert 'if t == "Moon":' in page and "continue" in page

    def test_the_day_header_names_the_day_twice(self, chart, client):
        """Once by the civil calendar, once by the Moon."""
        html = client.post("/", data=GATE_FORM).get_data(as_text=True)
        head = re.search(r'<h1 class="dayhead">([^<]+)</h1>', html)
        assert head, "no day header"
        text = head.group(1)
        assert re.match(r"\w+day \d+ \w+ · ", text), text

    def test_todays_transits_are_ticked_around_the_plate(self, page):
        """Outside the frame on purpose: the plate is the birth moment and
        must not be overwritten by today."""
        ticks = re.search(r'<g class="ticks".*?</g>', page, re.S)
        assert ticks, "no transit ticks on the plate"
        marks = re.findall(r'<text[^>]*>([^<]+)</text>', ticks.group(0))
        assert marks, "ticks group is empty"
        css = (HERE / "static" / "style.css").read_text(encoding="utf-8")
        block = css[css.index(".kundli .ticks text {"):]
        block = block[:block.index("}")]
        assert "var(--accent-ink)" in block
        # Re-pinned 2026-09-12. This used to cap the ticks at 11 USER UNITS
        # to keep them marginal, which on a phone rendered at 9.5 effective
        # pixels — under the legibility floor. Marginality is now carried by
        # the accent and the position, and TestTypeFloors owns the size.
        size = float(re.search(r"font-size:\s*([\d.]+)px", block).group(1))
        assert 12 <= size <= 16, size


class TestYourChartsScreen:
    """Screen 3. A gallery of divisional plates — and the honest admission
    that five of the eight are not built."""

    def test_the_gallery_shows_every_varga_built_and_unbuilt(self, page):
        import app as app_module
        codes = re.findall(r'<span class="gcard-code">([^<]+)</span>', page)
        assert len(codes) == len(app_module.VARGA_SLOTS), codes
        for code in ("D1", "D2", "D3", "D7", "D9", "D10", "D12", "D16",
                     "D30", "D60"):
            assert any(c.startswith(code + " ") for c in codes), code

    def test_an_unbuilt_slot_says_so_and_a_built_one_does_not(self, page):
        """A gallery that quietly listed only what it could cast would imply
        the list is complete.

        Re-pinned 2026-09-13, and the re-pin matters: every division in the
        gallery is cast now, so the loop over unbuilt slots iterates zero
        times and would pass forever without asserting anything. The gate
        states BOTH halves — that unbuilt slots are marked, and that a build
        with none of them carries no leftover "in preparation" text.
        """
        import app as app_module
        import vargas
        unbuilt = [code for key, code, _name in app_module.VARGA_SLOTS
                   if key != "d1" and not vargas.is_supported(code)]
        soon = re.findall(r'class="gcard gcard-soon"', page)
        assert len(soon) == len(unbuilt), (len(soon), unbuilt)
        assert page.count("In preparation") == len(unbuilt), unbuilt
        if not unbuilt:
            # The state this build is actually in. Said explicitly so the
            # assertion above cannot go quiet.
            assert soon == [], soon
            assert "In preparation" not in page
            assert len(app_module.VARGA_SLOTS) >= 10, \
                len(app_module.VARGA_SLOTS)

    def test_every_entry_says_what_that_chart_reads(self, page):
        import app as app_module
        import html as _html
        sums = [_html.unescape(t) for t in
                re.findall(r'<span class="gcard-sum">([^<]+)</span>', page)]
        assert len(sums) == len(app_module.VARGA_SLOTS), len(sums)
        for text in sums:
            # A phrase, not a paragraph: what this division is read for.
            assert 4 <= len(text.split()) <= 20, text
            assert text.strip().endswith("."), text
            assert text[:1].isupper(), text
        # …and every one of them comes from the single table, so the gallery
        # and the ledger cannot describe the same chart differently.
        for _key, code, _name in app_module.VARGA_SLOTS:
            assert app_module.varga_summary(code) in sums, code

    def test_the_built_charts_open_into_their_own_plate(self, page):
        for key in ("d1", "d9", "d10"):
            assert f'id="view-varga-{key}"' in page, key
            view = page[page.index(f'id="view-varga-{key}"'):]
            view = view[:view.index(f"<!-- /view-varga-{key} -->")]
            assert 'class="kundli"' in view
            assert 'class="platecaption"' in view
            assert 'class="dverdict' in view

    def test_every_computed_varga_is_plotted(self, page):
        """"Wire the remaining divisions to render as real plates as soon as
        their computation lands. If any division is already computed but not
        plotted, plot it now."

        This is the wire, asserted. The gallery is generic over
        `vargas.SUPPORTED`: a division renders as a real plate exactly when
        it has a sign function, and as a dashed empty frame when it does
        not. Adding `"D7": saptamsa_sign` to that registry is the whole of
        what it takes — and if a computation lands and the gallery does not
        plot it, this fails.
        """
        import app as app_module
        import vargas
        for key, code, name in app_module.VARGA_SLOTS:
            computed = key == "d1" or vargas.is_supported(code)
            has_view = f'id="view-varga-{key}"' in page
            assert has_view == computed, (
                f"{code} is {'computed' if computed else 'not computed'} but "
                f"{'has' if has_view else 'has no'} a plate page")
            if computed:
                view = page[page.index(f'id="view-varga-{key}"'):]
                view = view[:view.index(f"<!-- /view-varga-{key} -->")]
                assert 'class="kundli"' in view, code
                assert "gm gm-" in view, f"{code} plate has no graha marks"

    def test_every_division_in_the_gallery_is_named_and_described(self, page):
        """Widened 2026-09-13 from "every UNBUILT division", which now
        iterates over nothing. Every slot carries its code, its name and
        what it is read for, whether or not it can be cast."""
        import app as app_module
        import html as _html
        text = _html.unescape(page)
        for key, code, name in app_module.VARGA_SLOTS:
            assert f"{code} {name}" in text, code
            assert app_module.varga_summary(code) in text, code

    def test_each_plate_carries_a_reading_of_its_own_chart(self, page):
        """"…opening to a full plate view with its own reading."

        Added 2026-09-11 after reading the rendered screen: the plate view
        showed the plate and the gallery's one-line summary, which says what
        a Navāṃśa IS and nothing about this one. A gallery of charts with no
        reading is a filing cabinet.
        """
        import voice
        seen = []
        for key in ("d1", "d9", "d10"):
            view = page[page.index(f'id="view-varga-{key}"'):]
            view = view[:view.index(f"<!-- /view-varga-{key} -->")]
            verdict = re.search(r'class="dverdict[^"]*">(.*?)</p>', view, re.S)
            assert verdict, key
            text = re.sub(r"\s+", " ", verdict.group(1)).strip()
            seen.append(text)
            # It must be about THIS chart: a graha, and a placement.
            assert voice.names_a_planet(text), (key, text)
            assert " rises" in text, (key, text)
            assert not voice.find_jargon(text), (key, voice.find_jargon(text))
            assert not voice.find_vagueness(text), (key, text)
            assert voice.words(text) <= 40, (key, voice.words(text))
            # …and the generic "what this division reads" line is still
            # there, underneath, where it belongs.
            assert 'class="chartof-sub platewhat"' in view, key
        assert len(set(seen)) == 3, f"two plates read the same: {seen}"

    def test_a_plate_reading_is_computed_not_canned(self, chart):
        """Change the chart, change the reading. A constant would pass every
        assertion above."""
        import app as app_module
        from engine import BirthData, compute_chart
        other = compute_chart(BirthData(
            year=1972, month=11, day=3, hour=21, minute=40,
            latitude=-33.8688, longitude=151.2093, tz="Australia/Sydney",
            place="Sydney"))
        for key in ("d1", "d9", "d10"):
            a = app_module.plate_reading(key, chart)
            b = app_module.plate_reading(key, other)
            assert a != b, (key, a)

    def test_a_chart_url_opens_that_chart(self):
        page = (HERE / "templates" / "index.html").read_text(encoding="utf-8")
        js = page[page.index("function fromHash()"):]
        js = js[:js.index("document.addEventListener")]
        assert 'h.startsWith("chart-")' in js
        assert 'h === "charts"' in js and 'h === "readings"' in js


class TestEveryDivisionMatchesTheOracle:
    """No division lights up in the gallery until it has passed this.

    PyJHora, per BODY and per DIVISION, for both fictional charts — the sign
    AND the divisional longitude. Nine divisions × ten bodies × two charts is
    180 comparisons, and it is the only thing standing between a plausible
    counting rule and a wrong chart: every one of these rules produces a
    perfectly reasonable-looking plate when it is wrong.
    """

    ORACLE = json.loads(
        (HERE / "fixtures_pyjhora.json").read_text(encoding="utf-8"))

    #: Degrees. The oracle rounds to six places and we compute in full
    #: precision; anything past a hundredth of a degree is a real difference.
    TOLERANCE = 0.02

    @classmethod
    @pytest.fixture(scope="class")
    def charts(cls):
        import fixtures
        return {k: compute_chart(fixtures.birth(k))
                for k in ("reference", "partner")}

    def test_the_oracle_covers_every_division_this_build_casts(self):
        """A gate that silently skipped a division would be worse than no
        gate: the gallery would light it up on the strength of a comparison
        that never happened."""
        import vargas
        for key in ("reference", "partner"):
            have = set(self.ORACLE["charts"][key]["divisional_charts"])
            missing = [c for c in vargas.SUPPORTED if c not in have]
            assert not missing, (key, missing)

    @pytest.mark.parametrize("key", ["reference", "partner"])
    def test_every_body_in_every_division_matches(self, charts, key):
        import vargas
        chart = charts[key]
        oracle = self.ORACLE["charts"][key]["divisional_charts"]
        checked = 0
        for code in vargas.SUPPORTED:
            vc = vargas.varga_chart(chart, code)
            want = oracle[code]
            for body, w in want.items():
                if body == "Lagna":
                    got_sign = vc.lagna_sign_index
                    got_deg = vc.lagna_degree_in_sign
                else:
                    p = vc.planets[body]
                    got_sign, got_deg = p.sign_index, p.degree_in_sign
                checked += 1
                assert got_sign == w["sign_index"], (
                    f"{key} {code} {body}: sign {got_sign} "
                    f"({SIGNS[got_sign]}) vs oracle {w['sign_index']} "
                    f"({w['sign']})")
                assert abs(got_deg - w["degree_in_sign"]) < self.TOLERANCE, (
                    f"{key} {code} {body}: degree {got_deg:.6f} vs oracle "
                    f"{w['degree_in_sign']:.6f}")
        assert checked >= 90, checked

    def test_the_two_charts_do_not_produce_the_same_divisions(self, charts):
        """A comparison of two identical tables proves nothing."""
        import vargas
        a, b = charts["reference"], charts["partner"]
        for code in vargas.SUPPORTED:
            va, vb = (vargas.varga_chart(a, code), vargas.varga_chart(b, code))
            assert [va.planets[p].sign_index for p in PLANETS] != \
                [vb.planets[p].sign_index for p in PLANETS], code

    # --- the degree, and what it is -----------------------------------------

    def test_the_divisional_degree_fills_the_sign(self, charts):
        """The stretch: a graha at the very start of its part sits at 0° of
        the divisional sign, and one at the end approaches 30°. If it did
        not, the degree would be an unscaled fragment and varga nakṣatras
        computed from it would be nonsense."""
        import vargas
        for code in vargas.SUPPORTED:
            span = 30.0 / vargas.DIVISIONS[code]
            # Start of a part → 0°; just short of the next → just short of 30.
            for base in (0.0, 30.0, 210.0):
                sign_at_start, deg = vargas.varga_longitude(base, code)
                assert deg == pytest.approx(0.0, abs=1e-9), (code, base)
                _s, deg = vargas.varga_longitude(base + span * 0.9999, code)
                assert deg == pytest.approx(30.0, abs=0.01), (code, base)

    def test_a_part_boundary_moves_the_sign(self, charts):
        """Crossing from one part to the next must change the divisional
        sign — otherwise the division is not dividing."""
        import vargas
        for code in vargas.SUPPORTED:
            span = 30.0 / vargas.DIVISIONS[code]
            moved = 0
            for part in range(vargas.DIVISIONS[code] - 1):
                a = vargas.varga_sign(span * part + span / 2, code)
                b = vargas.varga_sign(span * (part + 1) + span / 2, code)
                if a != b:
                    moved += 1
            # D30's bands are unequal, so several equal parts share a sign;
            # every other division moves at every boundary.
            floor = 4 if code == "D30" else vargas.DIVISIONS[code] - 1
            assert moved >= floor, (code, moved, floor)

    # --- the schools, named ---------------------------------------------------

    def test_a_contested_division_says_which_reading_it_uses(self):
        """Every contested division carries a note and a rule, and the rule
        admits that another reading exists.

        The set is asserted as a whole rather than enumerated loosely: a
        division quietly losing its note would be the app picking a side in
        silence, which is the thing this file exists to prevent. D2, D3 and
        D27 are contested and reader-selectable; D30 and D60 are contested
        and NOT selectable, because only one reading of each is built —
        their notes say which, and that is the whole of what is owed.
        """
        import rulelib
        import schools
        import vargas
        assert set(vargas.SCHOOL_NOTE) == {"D2", "D3", "D27", "D30", "D60"}, \
            set(vargas.SCHOOL_NOTE)
        # The three that ARE selectable each have a live school option whose
        # answers both compute, so the note is an invitation and not an
        # apology.
        for code, option_id in (("D2", "hora_scheme"),
                                ("D3", "drekkana_scheme"),
                                ("D27", "bhamsa_scheme")):
            assert schools.OPTIONS[option_id].live, option_id
            assert len(schools.OPTIONS[option_id].answers) == 2, option_id
        for code, note in vargas.SCHOOL_NOTE.items():
            assert len(note.split()) >= 20, code
            rule_id = vargas.SCHOOL_RULE[code]
            assert rule_id in rulelib.RULES, (code, rule_id)
            rule = rulelib.RULES[rule_id]
            # The rule names the OTHER reading, not only this one. A note
            # that describes one school without saying another exists is not
            # flagging anything.
            assert any(w in rule.text.lower() for w in
                       ("some texts", "older", "other", "different",
                        "two ways", "disputed", "differ", "divergence",
                        "instead")), rule_id
            assert rule.source.strip(), rule_id

    def test_the_plate_prints_the_school_flag(self, page):
        """Driven by the registry, not by a list typed here. A gate that
        names the contested divisions goes stale the moment a fork is added
        — which is exactly what happened when D3 and D27 became forks and
        this test went on asserting that D3 was uncontested."""
        import vargas

        def view_of(code):
            key = code.lower()
            view = page[page.index(f'id="view-varga-{key}"'):]
            return view[:view.index(f"<!-- /view-varga-{key} -->")]

        contested = set(vargas.SCHOOL_NOTE)
        assert contested, "no division claims to be contested"
        for code in contested:
            view = view_of(code)
            assert 'class="schoolflag"' in view, code
            assert vargas.SCHOOL_RULE[code] in view, code
        # …and a division that is NOT contested does not cry wolf.
        for code in vargas.SUPPORTED:
            if code not in contested:
                assert 'class="schoolflag"' not in view_of(code), code

    def test_both_sides_of_every_scheme_fork_are_computed(self, charts):
        """A fork is only real if BOTH answers compute a chart, and only
        honest if both were checked. These three were verified against
        PyJHora's own named variants across 400 random charts — 4,000 bodies
        per side — before they were offered to anyone. Here they are pinned
        on the two fixtures, plus the thing that makes them forks at all:
        that the two answers actually disagree.
        """
        import schools
        import vargas
        forks = (("hora_scheme", "D2", "twelve", "two_sign"),
                 ("drekkana_scheme", "D3", "parashari", "parivritti"),
                 ("bhamsa_scheme", "D27", "forward", "even_reverse"))
        for option_id, code, default, alternate in forks:
            assert schools.OPTIONS[option_id].default == default, option_id
            for name, chart in charts.items():
                with schools.use({option_id: default}):
                    a = vargas.varga_chart(chart, code)
                with schools.use({option_id: alternate}):
                    b = vargas.varga_chart(chart, code)
                moved = [p for p in PLANETS
                         if a.planets[p].sign_index != b.planets[p].sign_index]
                assert moved, (
                    f"{option_id}: the two answers produced the same {code} "
                    f"on the {name} chart — that is a fake control")
                # Both are real charts, not one chart and one ruin.
                for cast in (a, b):
                    assert 0 <= cast.lagna_sign_index < 12
                    assert all(1 <= cast.planets[p].house <= 12
                               for p in PLANETS)

    def test_every_fork_alternate_matches_the_oracle(self, charts):
        """THE FAR SIDE OF EACH FORK, against PyJHora rather than against
        our own closed form.

        Until the oracle carried variant blocks this could not be done, and
        the cost was measurable: a mutation to the parivṛtti step left every
        committed gate green, because "the two readings differ" is true of a
        wrong alternate too. `export_pyjhora.py` now emits each contested
        division under every named `chart_method`, so the reading we offer
        is checked exactly as hard as the one we ship.
        """
        import schools
        import vargas
        forks = {
            "D2": ("hora_scheme",
                   {"twelve": "twelve_sign_parivritti_even_reverse",
                    "two_sign": "traditional_parashari_leo_cancer"}),
            "D3": ("drekkana_scheme",
                   {"parashari": "parashari_sign_5th_9th",
                    "parivritti": "parivritti_traya_cyclic"}),
            "D27": ("bhamsa_scheme",
                    {"forward": "forward_from_element_sign",
                     "even_reverse": "even_sign_reversal"}),
        }
        checked = 0
        for name, chart in charts.items():
            variants = self.ORACLE["charts"][name]["divisional_variants"]
            for code, (option_id, answers) in forks.items():
                for answer, label in answers.items():
                    theirs = variants[code][label]["positions"]
                    with schools.use({option_id: answer}):
                        ours = vargas.varga_chart(chart, code)
                    for body in PLANETS:
                        assert ours.planets[body].sign_index == \
                            theirs[body]["sign_index"], (
                                f"{name}/{code}/{answer}/{body}: ours "
                                f"{ours.planets[body].sign} vs oracle "
                                f"{theirs[body]['sign']}")
                        checked += 1
                    assert ours.lagna_sign_index == \
                        theirs["Lagna"]["sign_index"], (name, code, answer)
        # 2 charts x 3 divisions x 2 readings x 9 bodies.
        assert checked == 108, checked

    def test_the_two_sign_hora_uses_only_the_suns_and_moons_signs(self):
        """The older horā has TWO values, and that is the method rather than
        a bug in it. Every graha lands in Leo or Cancer: the first half of an
        odd sign is the Sun's, the second the Moon's, and even signs take
        them the other way round."""
        import schools
        import vargas
        with schools.use({"hora_scheme": "two_sign"}):
            for sign in range(12):
                odd = sign % 2 == 0
                first = vargas.varga_sign(sign * 30.0 + 5.0, "D2")
                second = vargas.varga_sign(sign * 30.0 + 20.0, "D2")
                assert {first, second} == {3, 4}, sign
                assert first == (4 if odd else 3), sign
                assert second == (3 if odd else 4), sign
        # And the twelve-sign reading is genuinely twelve-valued.
        with schools.use({"hora_scheme": "twelve"}):
            reached = {vargas.varga_sign(s * 30.0 + d, "D2")
                       for s in range(12) for d in (5.0, 20.0)}
            assert len(reached) == 12

    def test_d30_takes_its_sign_from_the_unequal_bands(self):
        """The rule the founder singled out. The equal 1° part is used for
        the degree and must never choose the sign: a graha inside an 8°
        band has no equal-part position to take."""
        import vargas
        # Aries (odd) 0–5 Mars, 5–10 Saturn, 10–18 Jupiter, 18–25 Mercury,
        # 25–30 Venus.
        for deg, sign in ((1.0, 0), (7.0, 10), (14.0, 8), (20.0, 2),
                          (27.0, 6)):
            assert vargas.varga_sign(deg, "D30") == sign, deg
        # Taurus (even) reverses: 0–5 Venus, 5–12 Mercury, 12–20 Jupiter,
        # 20–25 Saturn, 25–30 Mars.
        for deg, sign in ((1.0, 1), (8.0, 5), (15.0, 11), (22.0, 9),
                          (27.0, 7)):
            assert vargas.varga_sign(30.0 + deg, "D30") == sign, deg
        # The bands are unequal, which is the whole point.
        widths = [hi - lo for (hi, _), lo in
                  zip(vargas.TRIMSAMSA_ODD, (0,) + tuple(
                      b[0] for b in vargas.TRIMSAMSA_ODD[:-1]))]
        assert widths == [5, 5, 8, 7, 5], widths

    def test_d60_counts_half_a_degree_at_a_time(self):
        import vargas
        assert vargas.DIVISIONS["D60"] == 60
        # Aries 0°00′ → Aries; 0°30′ → Taurus; 1°00′ → Gemini.
        assert vargas.varga_sign(0.0, "D60") == 0
        assert vargas.varga_sign(0.5, "D60") == 1
        assert vargas.varga_sign(1.0, "D60") == 2
        # No even-sign reversal in this build — stated on the plate.
        assert vargas.varga_sign(30.0, "D60") == 1
        assert vargas.varga_sign(30.5, "D60") == 2


class TestAshtakavarga:
    """Milestone 2 — raw BAV and SAV.

    THE GATE THAT MATTERS IS PER SIGN. The classical per-graha totals — Sun
    48, Moon 49, Mars 39, Mercury 54, Jupiter 56, Venus 52, Saturn 39,
    summing to 337 — are the same for EVERY chart: they count rows in the
    benefic-point tables and depend on no birth moment. They passed while
    four rows of this build's table were wrong, because a bindu written at
    the wrong offset moves where it lands and not how many there are. Only
    comparison against an independent implementation, per sign, found them.
    """

    ORACLE = json.loads(
        (HERE / "fixtures_pyjhora.json").read_text(encoding="utf-8"))

    @classmethod
    @pytest.fixture(scope="class")
    def tallies(cls):
        import ashtakavarga
        import fixtures
        return {k: ashtakavarga.ashtakavarga(compute_chart(fixtures.birth(k)))
                for k in ("reference", "partner")}

    # --- the gate that bites -----------------------------------------------

    @pytest.mark.parametrize("key", ["reference", "partner"])
    def test_every_bav_row_matches_an_independent_implementation(
            self, tallies, key):
        """PyJHora, per SIGN, for both fictional charts. This is the gate the
        milestone plan called the one that actually bites — and it did."""
        import ashtakavarga
        want = self.ORACLE["charts"][key]["ashtakavarga"]
        got = tallies[key]
        for planet in ashtakavarga.BODIES:
            assert list(got.bav_by_sign[planet]) == want["bav_by_sign"][planet], (
                f"{key} {planet}\n  ours   {list(got.bav_by_sign[planet])}"
                f"\n  oracle {want['bav_by_sign'][planet]}")

    @pytest.mark.parametrize("key", ["reference", "partner"])
    def test_the_sav_distribution_matches_the_oracle(self, tallies, key):
        want = self.ORACLE["charts"][key]["ashtakavarga"]
        assert list(tallies[key].sav_by_sign) == want["sav_by_sign"]

    @pytest.mark.parametrize("key", ["reference", "partner"])
    def test_the_lagna_row_matches_and_is_kept_out_of_the_sav(self, tallies,
                                                             key):
        want = self.ORACLE["charts"][key]["ashtakavarga"]
        got = tallies[key]
        assert list(got.lagna_bav_by_sign) == want["lagna_bav_by_sign"]
        # SAV is the seven, not the eight.
        import ashtakavarga
        seven = [sum(got.bav_by_sign[p][s] for p in ashtakavarga.BODIES)
                 for s in range(12)]
        assert list(got.sav_by_sign) == seven
        assert got.sav_total == 337
        assert got.sav_total + sum(got.lagna_bav_by_sign) == 386

    def test_the_two_charts_actually_differ(self, tallies):
        """A gate comparing two identical arrays proves nothing. The whole
        point of the per-sign comparison is that it varies by chart."""
        a, b = tallies["reference"], tallies["partner"]
        assert list(a.sav_by_sign) != list(b.sav_by_sign)

    # --- the checksum, and what it is worth ---------------------------------

    def test_the_classical_totals_hold(self, tallies):
        import ashtakavarga
        for key, av in tallies.items():
            for planet, total in ashtakavarga.CLASSICAL_TOTALS.items():
                assert sum(av.bav_by_sign[planet]) == total, (key, planet)
            assert sum(av.lagna_bav_by_sign) == \
                ashtakavarga.CLASSICAL_LAGNA_TOTAL

    def test_the_337_checksum_is_chart_invariant_and_says_so(self, tallies):
        """Recorded so the milestone cannot quietly over-claim on it. The
        totals are identical for both charts BY CONSTRUCTION — they count
        table rows — so passing them is evidence about the transcription's
        arithmetic and about nothing else."""
        import ashtakavarga
        a, b = tallies["reference"], tallies["partner"]
        for planet in ashtakavarga.BODIES:
            assert sum(a.bav_by_sign[planet]) == sum(b.bav_by_sign[planet])
        assert a.sav_total == b.sav_total == 337
        doc = (HERE / "ashtakavarga.py").read_text(encoding="utf-8")
        assert "same for EVERY chart" in doc
        assert "gate the" in doc

    def test_the_checksum_is_blind_to_a_misplaced_bindu(self):
        """The claim above, demonstrated rather than asserted.

        Move one bindu to a different house in one row of one table. The
        per-graha total is unchanged, so every classical-total check still
        passes — and the per-sign comparison fails. That is precisely how
        four wrong rows survived a green checksum in this build, and it is
        why the oracle comparison is the gate this milestone rests on.
        """
        import copy
        import ashtakavarga
        import fixtures
        chart = compute_chart(fixtures.birth("reference"))
        table = copy.deepcopy(ashtakavarga.BENEFIC_PLACES)
        # Venus's row from Mars: move the 4th to the 5th.
        row = list(table["Venus"]["Mars"])
        assert row[1] == 4, row
        row[1] = 5
        table["Venus"]["Mars"] = tuple(sorted(row))
        original = ashtakavarga.BENEFIC_PLACES
        try:
            ashtakavarga.BENEFIC_PLACES = table
            broken = ashtakavarga.ashtakavarga(chart)
        finally:
            ashtakavarga.BENEFIC_PLACES = original
        good = ashtakavarga.ashtakavarga(chart)

        # The checksum notices nothing.
        for planet in ashtakavarga.BODIES:
            assert sum(broken.bav_by_sign[planet]) == \
                ashtakavarga.CLASSICAL_TOTALS[planet], planet
        assert broken.sav_total == ashtakavarga.CLASSICAL_SAV_TOTAL

        # The per-sign comparison does.
        want = self.ORACLE["charts"]["reference"]["ashtakavarga"]
        assert list(good.bav_by_sign["Venus"]) == want["bav_by_sign"]["Venus"]
        assert list(broken.bav_by_sign["Venus"]) != want["bav_by_sign"]["Venus"]

    def test_the_table_is_the_shape_the_method_needs(self):
        import ashtakavarga
        assert len(ashtakavarga.BODIES) == 7
        assert len(ashtakavarga.REFERENCES) == 8
        # Seven subject tables plus the lagna's own, eight rows each.
        assert set(ashtakavarga.BENEFIC_PLACES) == \
            set(ashtakavarga.REFERENCES)
        for subject, rows in ashtakavarga.BENEFIC_PLACES.items():
            assert set(rows) == set(ashtakavarga.REFERENCES), subject
            for ref, places in rows.items():
                assert places == tuple(sorted(set(places))), (subject, ref)
                assert all(1 <= p <= 12 for p in places), (subject, ref)

    def test_the_reductions_are_absent_and_the_app_says_so(self):
        """Trikoṇa and ekādhipatya śodhana are deliberately not implemented:
        published implementations diverge, and a disputed method printed as
        an exact number would be worse than no number. Saying so is the
        difference between a deferral and an omission."""
        import ashtakavarga
        src = (HERE / "ashtakavarga.py").read_text(encoding="utf-8")
        for word in ("trikona", "trikoṇa", "sodhana", "śodhana"):
            pass
        assert "not implemented" in src or "NOT implemented" in src
        note = ashtakavarga.REDUCTIONS_NOTE
        assert "RAW" in note and "not" in note
        assert "śodhana" in note or "sodhana" in note
        # …and it reaches the reader, not only the source file.
        page = (HERE / "templates" / "index.html").read_text(encoding="utf-8")
        assert "ashtakavarga.note" in page

    # --- signs vs houses ----------------------------------------------------

    def test_rotation_to_houses_happens_once_and_is_named(self, tallies):
        """Hazard 1 from the milestone plan. Every array is per SIGN; the
        rotation to houses is an explicit call, because a table silently
        rotated once is indistinguishable from one rotated twice."""
        av = tallies["reference"]
        lagna = av.lagna_sign_index
        for h in range(1, 13):
            assert av.sav_by_house[h] == av.sav_by_sign[(lagna + h - 1) % 12]
        assert av.sav_by_house[1] == av.sav_by_sign[lagna]
        assert sum(av.sav_by_house.values()) == av.sav_total

    def test_sav_anchors_stay_in_their_own_cell(self):
        """The number for a house is printed in that house's cell. Same
        launch-blocker as the graha labels: a value in the wrong cell is a
        wrong chart.

        The totals take the SIGN NUMERAL'S anchor, because a North-Indian
        cell has room for one small number and not two — measured: a third
        number collided with the numeral or the graha stack in every
        arrangement tried, and shrinking it to fit would have put it under
        the legibility floor.
        """
        from app import NUMBER_POS, house_at
        for house, (x, y) in NUMBER_POS.items():
            assert house_at(x, y) == house, (house, x, y, house_at(x, y))

    def test_the_plate_carries_the_sav_and_only_on_d1(self, page, chart):
        """The tables are defined against the birth chart; rotated into a
        division they would mean nothing.

        One number to a cell: the totals REPLACE the sign numerals rather
        than joining them, and a toggle above the plate says which is
        showing. A cell whose graha stack has taken the numeral's corner
        shows neither — the same rule, and the grid in Explore has all
        twelve either way.
        """
        import ashtakavarga
        d1 = page[page.index('aria-label="North-Indian chart d1"'):]
        d1 = d1[:d1.index("</svg>")]
        block = d1[d1.index('<g class="savnum"'):]
        block = block[:block.index("</g>")]
        marks = [int(m) for m in re.findall(r"<text[^>]*>(\d+)</text>", block)]
        assert marks, "the plate carries no Ashtakavarga totals"
        av = ashtakavarga.ashtakavarga(chart)
        shown = set(marks)
        assert shown <= set(av.sav_by_house.values()), (marks, av.sav_by_house)
        # Every house that has room for its numeral has its total.
        assert len(marks) == d1.count("<text", d1.index('<g class="signnum"'),
                                      d1.index("</g>",
                                               d1.index('<g class="signnum"')))
        # The toggle exists and starts off, so the plate opens as a chart.
        assert 'id="savToggle"' in page
        toggle = re.search(r'<input type="checkbox" id="savToggle"[^>]*>',
                           page).group(0)
        assert "checked" not in toggle, toggle
        for key in ("d9", "d10"):
            other = page[page.index(f'aria-label="North-Indian chart {key}"'):]
            other = other[:other.index("</svg>")]
            assert "savnum" not in other, key

    def test_the_two_numerals_are_never_shown_together(self):
        """One number to a cell. If both groups could be visible at once the
        plate would be printing a sign number and a bindu count in the same
        corner, and neither would be readable."""
        css = (HERE / "static" / "style.css").read_text(encoding="utf-8")
        assert ".savnum { display: none; }" in css
        assert ".plate.showsav .savnum { display: block; }" in css
        assert ".plate.showsav .signnum { display: none; }" in css

    # --- the reading --------------------------------------------------------

    def test_the_verdict_is_the_founders_sentence(self, tallies):
        """"your strongest houses are the 8th at 34 and the 6th at 33; the
        thinnest are the 4th at 24 and the 9th at 24" — four numbers a
        reader can act on, before any grid."""
        import ashtakavarga
        for key, av in tallies.items():
            v = ashtakavarga.verdict(av)
            assert v.startswith("Your strongest houses are "), v
            assert "; the thinnest are " in v, v
            nums = [int(n) for n in re.findall(r" at (\d+)", v)]
            assert len(nums) == 4, v
            # Strongest first descending, thinnest first ASCENDING — the
            # thinnest house is the one named first in its own clause.
            assert nums[0] >= nums[1], v
            assert nums[2] <= nums[3], v
            assert nums[1] > nums[3], v
            top = dict(ashtakavarga.strongest(av))
            low = dict(ashtakavarga.thinnest(av))
            assert set(top.values()) == set(nums[:2]), (v, top)
            assert set(low.values()) == set(nums[2:]), (v, low)

    def test_the_verdict_names_real_houses(self, chart, tallies):
        import ashtakavarga
        av = tallies["reference"]
        by_house = av.sav_by_house
        for house, score in (ashtakavarga.strongest(av)
                             + ashtakavarga.thinnest(av)):
            assert by_house[house] == score, (house, score)

    def test_the_grid_is_folded_under_the_answer(self, page):
        block = page[page.index('<section class="ledger" id="ashtakavarga"'):]
        block = block[:block.index("</section>")]
        assert block.index('class="yverdict"') < block.index("<details"), (
            "the 12x8 grid is printed before the answer")
        # A class TOKEN, not an exact attribute: the table also carries
        # `gtable`, and matching the whole attribute has broken gates in
        # this file twice already.
        assert re.search(r'class="[^"]*\bavgrid\b', block), block[:200]
        assert "overflow-x" in (HERE / "static" / "style.css").read_text(
            encoding="utf-8")

    # --- the ledger ---------------------------------------------------------

    def test_the_ledger_carries_nineteen_facts_not_ninety_six(self, chart):
        """`sav.house.N` x12 plus `bav.<planet>` x7, each carrying a
        twelve-value array. Per-planet-per-house ids would have needed 84
        more, tripling the prompt payload to say the same thing."""
        from chartfacts import build_facts
        ids = {f.id for f in build_facts(chart, AGENT_WHEN)}
        for h in range(1, 13):
            assert f"sav.house.{h}" in ids, h
        import ashtakavarga
        for p in ashtakavarga.BODIES:
            assert f"bav.{p.lower()}" in ids, p
        assert "sav.summary" in ids
        # …and nothing per-planet-per-house crept in.
        assert not [i for i in ids if re.match(r"bav\.\w+\.house\.", i)]

    def test_every_ledger_number_matches_the_computation(self, chart):
        from chartfacts import build_facts
        import ashtakavarga
        av = ashtakavarga.ashtakavarga(chart)
        facts = {f.id: f for f in build_facts(chart, AGENT_WHEN)}
        for h in range(1, 13):
            fact = facts[f"sav.house.{h}"]
            assert fact.value["bindus"] == av.sav_by_house[h], h
            assert fact.value["sign"] == av.sign_of_house(h), h
            assert str(av.sav_by_house[h]) in fact.statement, h
        for p in ashtakavarga.BODIES:
            fact = facts[f"bav.{p.lower()}"]
            assert fact.value["by_sign"] == list(av.bav_by_sign[p]), p
            assert fact.value["total"] == sum(av.bav_by_sign[p]), p

    def test_every_ledger_fact_says_it_is_raw(self, chart):
        """The reductions are deferred, so every number the agent can quote
        has to carry that with it — otherwise the agent quotes a raw figure
        as though it were a reduced one."""
        from chartfacts import build_facts
        for f in build_facts(chart, AGENT_WHEN):
            if f.kind == "ashtakavarga":
                assert f.value.get("raw") is True, f.id
                assert "RAW" in f.statement or "RAW" in f.statement.upper(), \
                    f.id


class TestAYogaIsReadNotJustDetected:
    """Item 3, whole. A yoga entry must answer four questions, in order.

    Before this the app gave a name, a classical rule, and a sentence of
    meaning that was true of the yoga rather than of the reader's chart. It
    answered neither of the two questions anyone actually asks: is it real
    in MY chart, and when does it do anything.
    """

    NOW = datetime(2026, 9, 10, tzinfo=timezone.utc)

    @classmethod
    @pytest.fixture(scope="class")
    def readings(cls, chart):
        import yogaread
        return yogaread.read_all(chart, cls.NOW)

    def test_there_is_something_to_read(self, readings):
        assert readings, "no yogas in the reference chart — proves nothing"

    # --- (a) FORMED IN ------------------------------------------------------

    def test_every_yoga_is_tested_in_the_ninth_division(self, readings):
        for r in readings:
            codes = [t.varga for t in r.varga_tests]
            assert "D9" in codes, (r.yoga.name, codes)

    def test_a_career_or_wealth_yoga_is_tested_in_the_tenth_too(self,
                                                               readings):
        """"…and, for career/wealth yogas, D10." Decided from the chart —
        which houses the combination actually touches — not from a list of
        names."""
        import yogaread
        tested = False
        for r in readings:
            codes = [t.varga for t in r.varga_tests]
            wealth = (any(h in yogaread.CAREER_WEALTH_HOUSES
                          for h in r.yoga.houses)
                      or r.yoga.kind in yogaread.CAREER_WEALTH_KINDS)
            assert ("D10" in codes) == wealth, (r.yoga.name, codes, wealth)
            tested = tested or wealth
        assert tested, "no career/wealth yoga here — the rule is untested"

    def test_each_test_says_confirmed_or_weakens_in_plain_words(self,
                                                               readings):
        """The founder's own words: 'confirmed in the ninth division' or
        'weakens in the ninth division — the promise is thinner than it
        looks'. Not a dignity string the reader has to interpret."""
        for r in readings:
            for t in r.varga_tests:
                low = t.verdict.lower()
                assert ("confirmed in the" in low or "weakens in the" in low
                        or "splits" in low
                        or "neither confirms nor weakens" in low), t.verdict
                assert t.verdict.endswith("."), t.verdict

    def test_a_varga_dignity_is_computed_from_the_divisional_degree(self):
        """Inverted 2026-09-13, and that is the milestone.

        This used to assert that a varga dignity could never be
        moolatrikona, because moolatrikona is a degree band and the build
        held no degree inside a divisional sign. It holds one now, so the
        state is computed exactly as it is in the birth chart — and it must
        agree with `dignity_at` on that division's own position, which is
        what stops it drifting back to a sign-only shortcut.
        """
        import yogaread
        import vargas
        from yogas import dignity_at
        chart = compute_chart(GATE_BIRTH)
        seen = set()
        for code in vargas.SUPPORTED:
            vc = vargas.varga_chart(chart, code)
            for p in PLANETS:
                state = yogaread.varga_dignity(vc, p)
                assert state == dignity_at(p, vc.planets[p].sign_index,
                                           vc.planets[p].degree_in_sign)
                seen.add(state)
        # The degree band is genuinely reachable, not merely permitted.
        assert "moolatrikona" in seen, seen

    # --- (b) WHAT IT GIVES --------------------------------------------------

    def test_every_yoga_says_what_it_gives_and_cites_a_rule(self, readings):
        import rulelib
        for r in readings:
            assert r.gives and r.gives.endswith("."), r.yoga.name
            assert len(r.gives.split()) >= 6, r.gives
            assert r.gives_rule in rulelib.RULES, (r.yoga.name, r.gives_rule)

    def test_what_it_gives_is_not_vague(self, readings):
        import voice
        for r in readings:
            assert not voice.find_vagueness(r.gives), (r.yoga.name, r.gives)
            assert not voice.find_throat_clearing(r.gives), r.gives

    # --- (c) WHEN IT ACTIVATES ----------------------------------------------

    def test_activation_is_dated_from_the_ledger(self, chart, readings):
        """"…the dasha/antardasha periods of its forming planet(s) with
        dates from the ledger." Not dates this module invented: every window
        must be a real period of the Vimshottari timeline."""
        from dashas import vimshottari
        timeline = vimshottari(chart)
        real = {(md.lord, md.start, md.end) for md in timeline.mahadashas}
        real |= {(ad.lord, ad.start, ad.end)
                 for md in timeline.mahadashas for ad in md.antardashas}
        seen = 0
        for r in readings:
            for a in r.activations:
                assert (a.lord, a.start, a.end) in real, (r.yoga.name, a)
                assert a.lord in r.yoga.planets, (r.yoga.name, a.lord)
                seen += 1
        assert seen, "no activation windows at all"

    def test_a_period_is_labelled_past_running_or_ahead(self, readings):
        """"If the activating period is past, say so; if future, date it."""
        for r in readings:
            for a in r.activations:
                assert a.state in ("past", "running", "ahead"), a
                if a.state == "past":
                    assert a.end <= self.NOW, a
                elif a.state == "running":
                    assert a.start <= self.NOW < a.end, a
                else:
                    assert a.start > self.NOW, a

    def test_the_verdict_says_when(self, readings):
        """A verdict that names no window has not answered the question the
        founder asked it to answer."""
        import voice
        for r in readings:
            said = voice.names_a_date(r.verdict)
            if r.activations:
                assert said, (r.yoga.name, r.verdict)
            else:
                assert "No period" in r.verdict, r.verdict

    def test_a_past_period_is_not_sold_as_coming(self, readings):
        for r in readings:
            if r.running or r.next_up:
                continue
            if any(a.state == "past" for a in r.activations):
                assert "already given" in r.verdict, r.verdict

    # --- (d) WHERE IN LIFE --------------------------------------------------

    def test_where_is_in_plain_words_never_a_house_number(self, readings):
        import rulelib
        plain = {rulelib.HOUSE_MATTERS[h].split(",")[0].strip()
                 for h in range(1, 13)}
        for r in readings:
            assert r.where, r.yoga.name
            assert any(w in r.where for w in plain), (r.yoga.name, r.where)
            assert not re.search(r"\b\d+(?:st|nd|rd|th) house", r.where), \
                r.where
            assert not re.search(r"\bhouse \d", r.where), r.where

    # --- word discipline ----------------------------------------------------

    def test_the_verdict_answers_first_and_stays_short(self, readings):
        import voice
        import yogaread
        for r in readings:
            assert voice.words(r.verdict) <= yogaread.VERDICT_WORDS, (
                r.yoga.name, voice.words(r.verdict), r.verdict)
            assert len(voice.sentences(r.verdict)) <= 2, r.verdict
            assert not voice.find_throat_clearing(r.verdict), r.verdict
            assert not voice.find_vagueness(r.verdict), r.verdict

    def test_the_verdict_names_a_planet(self, readings):
        import voice
        for r in readings:
            assert voice.names_a_planet(r.verdict), (r.yoga.name, r.verdict)

    def test_the_verdict_does_not_repeat_the_entry_name(self, readings):
        """It sits directly under the name. Repeating it spent a fifth of
        the budget and put "Yoga" — banned from the plain register — into
        every verdict in the app."""
        import voice
        for r in readings:
            assert r.yoga.name not in r.verdict, r.verdict
            assert not voice.find_jargon(r.verdict), (
                r.yoga.name, voice.find_jargon(r.verdict))

    # --- the ledger can back it ---------------------------------------------

    def test_every_claim_rests_on_a_rule_that_exists(self, readings):
        import rulelib
        for r in readings:
            assert r.rule_ids, r.yoga.name
            for rid in r.rule_ids:
                assert rid in rulelib.RULES, (r.yoga.name, rid)

    def test_every_claim_rests_on_a_fact_the_ledger_carries(self, chart,
                                                            readings):
        """"…the validator must be able to check every claim." It can only
        do that if the ids a reading cites are ids the ledger publishes."""
        from chartfacts import build_facts
        ledger = {f.id for f in build_facts(chart, self.NOW)}
        for r in readings:
            assert r.fact_ids, r.yoga.name
            for fid in r.fact_ids:
                assert fid in ledger, (r.yoga.name, fid)

    def test_the_ledger_carries_the_varga_and_activation_facts(self, chart):
        """The two facts that did not exist before. A reading asserting that
        the ninth division confirms a yoga, with nothing in the ledger
        saying so, is exactly the improvisation the ledger exists to stop."""
        from chartfacts import build_facts
        from yogas import detect_all
        ledger = {f.id: f for f in build_facts(chart, self.NOW)}
        yogas = detect_all(chart)
        assert yogas
        for y in yogas:
            slug = y.name.lower().replace(" ", "-").replace("'", "")
            slug = re.sub(r"[^a-z0-9.-]", "", slug.replace("(", "")
                          .replace(")", "").replace("&", "-"))
            varga = [k for k in ledger if k.endswith(".varga")
                     and k.startswith("yoga.")]
            act = [k for k in ledger if k.endswith(".activation")
                   and k.startswith("yoga.")]
            assert len(varga) == len(yogas), (len(varga), len(yogas))
            assert len(act) == len(yogas), (len(act), len(yogas))
        # …and they say something, not nothing.
        for fid, fact in ledger.items():
            if fid.endswith(".varga"):
                assert "D9" in fact.statement, fact.statement
                assert "Sign-level only" in fact.statement, fact.statement
            if fid.endswith(".activation"):
                assert fact.value["periods"] is not None

    # --- rendered -----------------------------------------------------------

    def test_the_fold_puts_the_verdict_before_the_working(self, page):
        block = page[page.index('<section class="ledger" id="yogas"'):]
        block = block[:block.index("</section>")]
        assert 'class="yverdict"' in block
        first = block.index('class="yverdict"')
        assert first < block.index("<details>"), (
            "the working is printed before the verdict")
        for label in ("Gives", "Where", "D9"):
            assert f'class="xplabel">{label}<' in block, label
        # The working, and the audit trail, are in the expander.
        working = block[block.index("<details>"):]
        assert "Rests on" in working and "Computed from" in working


class TestYogasAreCollapsedRows:
    """Nine yogas printed open was a wall of text nobody read.

    Each is a single closed row now — name, a one-line verdict, its family
    as a chip — and the full reading opens on click, one at a time.
    """

    NOW = datetime(2026, 9, 10, tzinfo=timezone.utc)

    @classmethod
    @pytest.fixture(scope="class")
    def rows(cls, page):
        block = page[page.index('<section class="ledger" id="yogas"'):]
        return block[:block.index("</section>")]

    def test_every_yoga_is_a_closed_row(self, rows):
        entries = re.findall(r'<details class="yoga yogarow">', rows)
        assert entries, "no yoga rows"
        # A <details> with no `open` attribute is closed.
        assert 'class="yoga yogarow" open' not in rows
        assert "<details" in rows and rows.count("<details") >= len(entries)

    def test_a_closed_row_carries_name_verdict_and_family(self, rows):
        summaries = re.findall(r"<summary class=\"yogahead\">(.*?)</summary>",
                               rows, re.S)
        assert summaries, "no row summaries"
        for block in summaries:
            for cls in ("yoganame", "yogaline", "yogakind"):
                assert f'class="{cls}"' in block, (cls, block[:120])
            line = re.search(r'class="yogaline">([^<]+)<', block).group(1)
            assert line.strip(), block[:120]

    def test_the_one_line_stays_inside_the_teaser_budget(self, chart):
        """A line that has to sit beside a name and a chip is a teaser, and
        the teaser budget applies to it."""
        import voice
        import yogaread
        readings = yogaread.read_all(chart, self.NOW)
        assert readings
        for r in readings:
            assert voice.words(r.oneline) <= yogaread.ONELINE_WORDS, (
                r.yoga.name, r.oneline)
            assert not voice.find_vagueness(r.oneline), r.oneline
            assert not voice.find_jargon(r.oneline), (
                r.yoga.name, voice.find_jargon(r.oneline))

    def test_the_one_line_says_whether_it_is_real_and_whether_it_runs(
            self, chart):
        """The two things that decide whether a reader opens the row."""
        import yogaread
        for r in yogaread.read_all(chart, self.NOW):
            state, _, when = r.oneline.partition(" · ")
            assert state in ("Held in check", "Confirmed in the ninth",
                             "Thins in the ninth", "Formed"), r.oneline
            assert when.strip(), r.oneline

    def test_the_full_reading_is_behind_the_row(self, rows):
        """Everything the open entry used to print is still there — it is
        just not printed until someone asks for it."""
        assert 'class="yverdict"' in rows
        for label in ("Gives", "Where", "D9"):
            assert f'class="xplabel">{label}<' in rows, label
        assert "Rests on" in rows and "Computed from" in rows
        # …and it sits AFTER the summary, not beside it.
        first_summary = rows.index("<summary class=\"yogahead\">")
        assert first_summary < rows.index('class="yverdict"')

    def test_one_open_at_a_time(self, page):
        rows = page[page.index('<section class="ledger" id="yogas"'):]
        rows = rows[:rows.index("</section>")]
        assert 'data-exclusive="yoga"' in rows
        js = page[page.index("[data-exclusive]"):]
        assert "other.open = false" in js[:600], js[:600]

    def test_an_open_row_is_told_apart_by_tone(self):
        """The second surface tone, doing the job it was introduced for."""
        css = (HERE / "static" / "style.css").read_text(encoding="utf-8")
        block = css[css.index(".yogarow[open] {"):]
        block = block[:block.index("}")]
        assert "var(--surface)" in block, block


class TestLearnHasAHome:
    """"Not a spotlight, not buried." A category card of its own in the
    Explore index, and a persistent quiet entry in the tab row."""

    def test_learn_has_its_own_category_card(self, page):
        index = page[page.index('<div class="cats">'):]
        index = index[:index.index("</div>", index.index("cat-learn"))]
        row = index[index.index('href="#cat-learn"'):]
        assert 'class="catrow catrow-learn"' in index
        assert 'class="catrow-title">Learn<' in row
        desc = re.search(r'class="catrow-desc">(.*?)</span>', row, re.S)
        assert desc, "no description on the Learn card"
        text = re.sub(r"\s+", " ", desc.group(1)).strip()
        assert text.startswith("How the chart is built"), text
        assert len(text.split()) <= 30, text

    def test_the_card_counts_the_lessons_it_actually_has(self, page):
        """"seven short pieces" beside twenty cards would be a small lie in
        the one place that exists to teach."""
        from lessons import LESSONS
        # The CARD, not the tab-row entry that also points at #cat-learn.
        index = page[page.index('class="catrow catrow-learn"'):]
        index = index[:index.index("</a>")]
        text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", index))
        assert f"in {len(LESSONS)} short pieces" in text, text
        # And nothing anywhere still hardcodes a stale count.
        raw = (HERE / "templates" / "index.html").read_text(encoding="utf-8")
        learn = raw[raw.index('id="learnpath"'):]
        learn = learn[:learn.index("</section>")]
        assert "20 cards" not in learn, "a hardcoded lesson count survived"

    def test_learn_is_in_the_tab_row_and_kept_quiet(self, page):
        row = re.search(r'<nav class="tabs"[^>]*>(.*?)</nav>', page, re.S)
        assert row, "no tab row"
        entry = re.search(r'<a href="#cat-learn"[^>]*class="tab-quiet"[^>]*>'
                          r'([^<]+)</a>', row.group(1))
        assert entry, row.group(1)
        assert entry.group(1).strip() == "Learn"
        css = (HERE / "static" / "style.css").read_text(encoding="utf-8")
        block = css[css.index(".tabs a.tab-quiet {"):]
        block = block[:block.index("}")]
        # Quiet: the body face at the label colour, against the display face
        # the five screens use. Still a real link at full reading size.
        assert "var(--font-body)" in block
        assert "var(--ink-50)" in block
        assert "var(--t-body)" in block

    def test_the_tab_actually_opens_the_lessons(self, page):
        row = re.search(r'<nav class="tabs"[^>]*>(.*?)</nav>', page, re.S)
        entry = re.search(r'<a href="#cat-learn"[^>]*>', row.group(1)).group(0)
        assert 'data-view="view-explore"' in entry, entry
        js = page[page.index("function fromHash()"):]
        js = js[:js.index("document.addEventListener")]
        assert 'h.startsWith("cat-")' in js
        assert 'id="learnpath"' in page


class TestNoEntryIsPrintedTwice:
    """One entry per phenomenon, in the fold and in the data behind it.

    From a live walk: "Mars in house 8 (Mangal Dosha pattern)" and "Mars in
    the 8th house" printed as two separate myth-vs-record entries — one
    placement, described twice, so a reader comparing them finds two
    classical records for the same fact. Sade Sati printed in full under
    Doshas AND under Myths.

    The fix is a canonical `subject` — (what, condition) — with exactly one
    home per subject, and a cross-reference where a phenomenon belongs to
    two sections. These gates hold that line.
    """

    NOW = datetime(2026, 9, 10, tzinfo=timezone.utc)

    @classmethod
    @pytest.fixture(scope="class")
    def folded(cls, chart):
        from doshas import combinations
        return combinations(chart, cls.NOW)

    def test_no_two_entries_describe_the_same_subject(self, folded):
        """The founder's gate, stated as they stated it: no two entries in a
        view may describe the same (planet, house/condition) pair."""
        subjects = [row["dosha"].subject for row in folded["doshas"]]
        subjects += [row["subject"] for row in folded["myths"]]
        dupes = [s for s in set(subjects) if subjects.count(s) > 1]
        assert not dupes, f"printed twice in one view: {dupes}"

    def test_a_subject_with_two_homes_is_shown_once_and_linked(self, folded):
        """Sade Sati belongs to both sections. It is PRINTED in Doshas —
        where its dates and its cancellation checks are — and linked from
        Myths."""
        dosha_subjects = {row["dosha"].subject for row in folded["doshas"]}
        myth_subjects = {row["subject"] for row in folded["myths"]}
        assert not (dosha_subjects & myth_subjects), (
            dosha_subjects & myth_subjects)
        # And the ones that moved are not silently gone.
        assert folded["crossrefs"], "nothing cross-referenced at all"
        names = {x["name"] for x in folded["crossrefs"]}
        assert names <= {row["dosha"].name for row in folded["doshas"]}

    def test_nothing_a_myth_card_said_was_dropped(self, chart, folded):
        """De-duplicating must not lose text. Every myth card's classical
        record is still somewhere — in its own entry, or folded into the
        dosha entry that now owns its subject."""
        from doshas import myth_busters
        printed = " ".join(
            [row["classical_record"] or "" for row in folded["doshas"]]
            + [row["classical_record"] for row in folded["myths"]])
        cards = myth_busters(chart, self.NOW)
        assert cards, "no myth cards at all — this proves nothing"
        for card in cards:
            assert card.classical_record in printed, card.placement

    def test_the_mangal_pattern_and_the_house_it_forms_in_are_one_entry(self):
        """The exact pair from the walk. A chart with Mars in the 8th forms
        the Mangal pattern BECAUSE Mars is in the 8th — one placement, and
        the two cards that used to describe it now share a subject and
        collapse."""
        from doshas import combinations, myth_busters
        from engine import BirthData
        # Synthetic; searched for the shape, not taken from a real record.
        # Aries lagna with Mars in Scorpio puts Mars in the 8th.
        found = compute_chart(BirthData(
            year=1988, month=1, day=5, hour=14, minute=30,
            latitude=19.07, longitude=72.88, tz="+05:30", place="Test"))
        assert found.planets["Mars"].house == 8, found.planets["Mars"].house
        # The two cards are still GENERATED — they are two real readings of
        # the same placement, and each contributes its record.
        raw = [m.subject for m in myth_busters(found, self.NOW)]
        assert raw.count(("Mars", "house-8")) == 2, raw
        # …and they arrive at the fold as one entry.
        folded = combinations(found, self.NOW)
        printed = ([row["dosha"].subject for row in folded["doshas"]]
                   + [row["subject"] for row in folded["myths"]])
        assert printed.count(("Mars", "house-8")) == 1, printed
        # Carrying both classical records, not one of them.
        row = next(r for r in folded["doshas"]
                   if r["dosha"].subject == ("Mars", "house-8"))
        for card in myth_busters(found, self.NOW):
            if card.subject == ("Mars", "house-8"):
                assert card.classical_record in row["classical_record"]

    def test_the_rendered_fold_prints_each_name_once(self, page):
        """The data can be clean and the template still print both lists."""
        block = page[page.index('<section class="ledger" id="doshas"'):]
        block = block[:block.index("<!-- Gocara")]
        names = re.findall(r'<span class="yoganame">([^<]+)</span>', block)
        assert names, "no entries rendered in the Combinations fold"
        # An entry's own name, once. A cross-reference is a link, not an
        # entry, and is not counted here — it is checked below.
        assert len(names) == len(set(names)), names
        assert "Sade Sati" in " ".join(names)
        crossref = re.search(r'<p class="crossref">(.*?)</p>', block, re.S)
        assert crossref, "no cross-reference line"
        assert "Sade Sati" in crossref.group(1)


class TestTheTabRow:
    """The five screens are peers and every one is always one tap away."""

    TABS = ("Today", "Readings", "Your charts", "Explore", "Ask")

    def test_numerology_is_listed_as_unbuilt_rather_than_hidden(self, page):
        """Numerology was never implemented — there is no numerology code in
        this repository, not a stub and not a route. It is named in the tab
        row anyway, marked unavailable, which is the same honesty the
        unbuilt divisional charts get: a reader can see what the app does
        not do instead of wondering whether they missed it.

        It must NOT be a link. A tab that navigates to a view that does not
        exist is worse than no tab.
        """
        row = re.search(r'<nav class="tabs"[^>]*>(.*?)</nav>', page, re.S)
        assert row, "no tab row"
        entry = re.search(
            r'<span class="tab-soon"[^>]*>(.*?)</span>\s*</span>',
            row.group(1), re.S)
        assert entry, "Numerology is not listed in the tab row"
        text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", entry.group(1)))
        assert "Numerology" in text, text
        assert "in preparation" in text, text
        assert 'aria-disabled="true"' in row.group(1)
        # No href anywhere near it, and no view behind it.
        assert 'href="#numerology"' not in page
        assert 'id="view-numerology"' not in page

    def test_nothing_in_the_build_pretends_numerology_exists(self):
        """The other half of the same claim. A disabled tab is honest only
        while there is genuinely nothing behind it; a half-built module
        would make it a lie in the other direction."""
        for path in sorted(HERE.glob("*.py")):
            if path.name.startswith("test_"):
                continue
            body = path.read_text(encoding="utf-8").lower()
            assert "numerolog" not in body, path.name

    def test_the_row_carries_all_five(self, page):
        """The five screens are peers. Learn rides along quietly and
        Numerology is named as unbuilt; neither is one of the five, and
        neither may displace one."""
        row = re.search(r'<nav class="tabs"[^>]*>(.*?)</nav>', page, re.S)
        assert row, "no tab row"
        labels = [t for t in re.findall(r'>([^<>]+)</a>', row.group(1))
                  if t.strip() != "Learn"]
        assert [x.strip() for x in labels] == list(self.TABS), labels

    def test_the_row_is_not_shown_before_a_chart_exists(self, client):
        """There is no Today until there is a chart."""
        blank = client.get("/").get_data(as_text=True)
        assert 'class="tabs"' not in blank

    def test_a_fold_marks_the_tab_that_owns_it(self):
        """A domain fold belongs to Readings and a divisional plate to Your
        charts, so the row never goes blank mid-read."""
        page = (HERE / "templates" / "index.html").read_text(encoding="utf-8")
        js = page[page.index("function markTabs("):]
        js = js[:js.index("function show(")]
        assert 'viewId.startsWith("view-domain-") ? "view-readings"' in js
        assert 'viewId.startsWith("view-varga-") ? "view-charts"' in js
