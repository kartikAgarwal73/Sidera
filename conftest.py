"""Test provenance registry — memory hygiene for a multi-session build.

WHY THIS EXISTS
A green suite proves "the code still does what it did", not "the code does
what it should". Those are different guarantees, and after enough sessions
nobody remembers which tests carry which. When a test goes red the honest
question is: *is this a regression, or was my expectation wrong?* — and the
answer depends entirely on where the expected value came from.

So every test declares its provenance, in one of three classes:

  external        Anchored to a source OUTSIDE this build — a classical rule,
                  independently checkable astronomy, a second ephemeris, a
                  design or framework document. If one of these goes red,
                  THE CODE IS WRONG. Do not edit the expectation without
                  going back to the named source.

  invariant       Must hold by definition, mathematics, or an explicit product
                  rule, regardless of any reference. Ketu is Rahu+180°;
                  antardaśās partition their mahādaśā; no dosha renders
                  without its cancellation checks. If one goes red, THE CODE
                  IS WRONG.

  characterization  Froze observed output. Protects continuity, not
                  correctness — if the value was wrong when it was written,
                  this test now defends the error. A red one MAY legitimately
                  be re-baselined, but say so in the commit message.

Adding a test without registering it here fails `test_hygiene.py`. That is
deliberate: the declaration is the point.

THE 2026-08-26 RECLASSIFICATION — READ THIS BEFORE TRUSTING AN 'external' TAG
Phases 1–5 were originally anchored to a real birth record the commissioner
supplied and had independently verified. That made them genuinely external:
the expected values came from outside this build, from a person who could
check them.

That record has been removed from the repository, and the committed chart is
now fictional. A fictional chart cannot carry the same anchor — its expected
values would have to be computed BY THIS BUILD, which makes asserting them
circular. So those declarations were downgraded to `characterization`. They
were NOT relabelled to keep the counts looking strong; the loss is the point
of recording it.

Two things were added to recover real anchoring, and only these carry
`external` for chart values now:

  * `TestIndependentEphemerisCrossCheck` — every position in the reference
    chart, recomputed with ERFA (IAU SOFA), agreeing to under an arcminute.
    A second ephemeris is a real outside source; our own is not.
  * `TestAstronomicalAnchors` — published, person-free facts (Spica at 180°,
    the epoch ayanamsa, a catalogued eclipse) that involve no birth record
    at all.

Everything downstream of the fictional chart — which yogas fire, which
dashas run, what the page renders — is characterization, and is declared so.
"""
from __future__ import annotations

import pytest

PROVENANCE_CLASSES = ("external", "invariant", "characterization")

# Per-class default provenance: (class, source-note).
CLASS_DEFAULT: dict[str, tuple[str, str]] = {
    "TestAstronomicalAnchors": (
        "external", "published person-free astronomy — Lahiri's definition, "
                    "the epoch ayanāṃśa, a catalogued eclipse"),
    "TestIndependentEphemerisCrossCheck": (
        "external", "ERFA / IAU SOFA — a second ephemeris, no shared code "
                    "with swisseph (see tools/erfa_cross_check.py)"),
    # Downgraded 2026-08-26: the reference chart is now fictional, so its
    # positions are this build's own output. The cross-check class above
    # is what actually anchors them.
    "TestPhase1CoreEngine": (
        "characterization", "positions of the fictional reference chart"),
    "TestPhase2NakshatrasVimshottari": (
        "characterization", "daśā dates derived from the fictional chart"),
    "TestPhase3DivisionalCharts": (
        "characterization", "vargas of the fictional chart"),
    "TestPhase4TransitsAspects": (
        "characterization", "aspect table of the fictional chart"),
    "TestPhase5Yogas": (
        "characterization", "which yogas the fictional chart forms"),
    "TestPhase6FlaskUI": ("characterization", "rendered output frozen"),
    "TestPhase7ExplanationEngine": ("characterization", "composed strings frozen"),
    "TestPhase8ShowYourWorking": ("invariant", "derived from gate + drishti spec"),
    "TestPhase9LifeTimeline": ("characterization", "computed timeline frozen"),
    "TestPhase10AntiAnxiety": ("characterization", "rendered output frozen"),
    "TestPhase11LearnAsYouGo": ("invariant", "authored-content product rules"),
    "TestUIRevisionWalkthrough": ("invariant", "product rules from the walkthrough"),
    "TestPancanga": ("external", "independently checkable astronomy"),
    "TestFrameworkFixturePersona": (
        "external", "Sidera Framework PDF · stated fixture values"),
    "TestGunaMilan": ("invariant", "aṣṭakūṭa structural rules"),
    "TestMatchUI": ("characterization", "rendered output frozen"),
    "TestAskYourChart": ("characterization", "engine output frozen"),
    "TestReadingEngine": ("invariant", "pipeline structure and determinism"),
    "TestDeployability": ("invariant", "production-readiness product rules"),
    # v1.1 agent. The whole point of these is that they are product rules,
    # not frozen output: an LLM's behaviour is not reproducible, so the
    # guarantee lives in the validator and the validator is what is tested.
    "TestChartFactLedger": (
        "invariant", "the ledger must describe the chart it came from"),
    "TestPlateGeometry": (
        "invariant", "product rule: a graha is drawn in the cell of the "
                     "house it is computed in, and both layers share one "
                     "geometry table"),
    "TestFixtureHygiene": (
        "invariant", "standing rule: no real birth record is ever a fixture"),
    "TestRuleLibrary": (
        "external", "classical dasha-phala and gochara rules, each with its "
                    "named source"),
    "TestGroundedAgent": (
        "invariant", "product rule: an answer may assert only what the "
                     "computed ledger contains"),
    "TestAgentLimitsAndLog": (
        "invariant", "rate-limit arithmetic and append-only logging"),
    "TestAgentEndpoint": (
        "invariant", "product rules for the /ask surface"),
}

# Per-test overrides, keyed "Class::test_name" (parametrisation stripped).
OVERRIDE: dict[str, tuple[str, str]] = {
    # --- Phase 1: definitional truths sitting among the chart values
    "TestPhase1CoreEngine::test_ketu_opposite_rahu":
        ("invariant", "Ketu is Rāhu + 180° by definition"),
    "TestPhase1CoreEngine::test_all_planets_present":
        ("invariant", "the nine grahas are a closed set"),
    "TestPhase1CoreEngine::test_iana_timezone_matches_fixed_offset":
        ("invariant", "Asia/Kolkata was +05:30 in 1998"),
    "TestPhase1CoreEngine::test_ayanamsa_is_lahiri_range":
        ("external", "published Lahiri value for the late 1990s"),

    # --- Phase 2
    "TestPhase2NakshatrasVimshottari::test_nakshatra_boundaries":
        ("invariant", "27 × 13°20′ arithmetic"),
    "TestPhase2NakshatrasVimshottari::test_dasha_sequence_totals_120_years":
        ("invariant", "the nine daśā spans sum to 120 by definition"),
    "TestPhase2NakshatrasVimshottari::test_antardashas_partition_each_md":
        ("invariant", "ADs tile their MD exactly, proportional to lord years"),
    "TestPhase2NakshatrasVimshottari::test_timeline_spans_120_years":
        ("invariant", "cycle length is definitional"),

    # --- Phase 3
    "TestPhase3DivisionalCharts::test_navamsa_counting_rules":
        ("external", "Parāśarī navāṃśa counting — movable/fixed/dual"),
    "TestPhase3DivisionalCharts::test_dasamsa_counting_rules":
        ("external", "Parāśarī daśāṃśa counting — odd from itself, even "
                     "from the 9th"),
    "TestPhase3DivisionalCharts::test_d9_houses_from_divisional_lagna":
        ("invariant", "whole-sign counting from the computed D9 lagna"),

    # --- Phase 4
    "TestPhase4TransitsAspects::test_drishti_offsets_per_spec":
        ("external", "master prompt · drishti specification"),
    "TestPhase4TransitsAspects::test_aspected_signs_counting":
        ("external", "graha drishti offsets applied to bare sign indices"),
    "TestPhase4TransitsAspects::test_angular_distance_wraparound":
        ("invariant", "modular arithmetic on a circle"),
    "TestPhase4TransitsAspects::test_aspect_completeness_every_graha":
        ("invariant", "every graha casts at least its 7th, in any chart"),

    # --- Phase 5
    "TestPhase5Yogas::test_natural_relations":
        ("external", "naisargika maitrī table, incl. its asymmetry"),
    "TestPhase5Yogas::test_dignity_states_bphs_segmentation":
        ("external", "BPHS degree segmentation — the synthetic cases pin "
                     "the band edges independently of any chart"),
    "TestPhase5Yogas::test_pancha_mahapurusha_fires_on_a_kendra":
        ("invariant", "constructed chart exercises the Kendra half of the "
                      "rule directly"),
    "TestPhase5Yogas::test_dhana_friction_tag_on_enemy_lords":
        ("invariant", "constructed chart exercises the friction tag"),
    "TestPhase5Yogas::test_kemadruma_formed_and_effective_synthetic":
        ("invariant", "constructed chart exercises the rule directly"),
    "TestPhase5Yogas::test_kemadruma_formed_but_cancelled_synthetic":
        ("invariant", "constructed chart exercises the exception directly"),

    # --- Phase 6
    "TestPhase6FlaskUI::test_birth_form_renders_blank_and_universal":
        ("invariant", "product rule: no fixture may leak into the UI"),
    "TestPhase6FlaskUI::test_time_parsing_24h_and_12h":
        ("invariant", "clock arithmetic"),
    "TestPhase6FlaskUI::test_twelve_hour_input_casts_identical_chart":
        ("invariant", "06:57 and 6:57 AM are the same instant"),
    "TestPhase6FlaskUI::test_birth_time_field_is_a_native_time_input":
        ("invariant", "product rule: a birth time must be enterable on a "
                      "phone — regression from a live Render smoke-test"),
    "TestPhase6FlaskUI::test_no_birth_field_traps_a_mobile_keyboard":
        ("invariant", "product rule: no field may demand characters its "
                      "declared keyboard cannot produce"),
    "TestPhase6FlaskUI::test_coordinate_parsing_shapes_and_refusals":
        ("invariant", "decimal-degree arithmetic and hemisphere convention"),
    "TestPhase6FlaskUI::test_native_time_value_casts_the_same_chart":
        ("invariant", "every accepted spelling of one instant is the same "
                      "instant, so the chart must be identical"),
    "TestPhase6FlaskUI::test_missing_timezone_is_never_guessed":
        ("invariant", "product rule: a guessed timezone corrupts the chart"),
    "TestPhase6FlaskUI::test_cities_api_offline_lookup":
        ("external", "GeoNames cities15000"),
    "TestPhase6FlaskUI::test_non_reference_chart_renders":
        ("invariant", "product rule: the app serves arbitrary birth data"),
    # Downgraded 2026-08-26 with the rest of the chart-derived expectations.
    "TestPhase6FlaskUI::test_dashboard_identity_line":
        ("characterization", "fictional chart's values, surfaced in the UI"),
    "TestPhase6FlaskUI::test_chart_degree_labels":
        ("characterization", "fictional chart's degrees, surfaced in the UI"),
    "TestPhase6FlaskUI::test_dashboard_has_three_chart_tabs":
        ("characterization", "fictional chart's vargas, surfaced in the UI"),

    # --- Phase 7
    "TestPhase7ExplanationEngine::test_confidence_is_mandatory_and_validated":
        ("invariant", "product rule: no interpretation without a tag"),
    "TestPhase7ExplanationEngine::test_every_explanation_has_three_layers_and_tag":
        ("invariant", "product rule: fact / mechanism / meaning, always"),

    # --- Phase 8
    "TestPhase8ShowYourWorking::test_page_has_explorer_ui":
        ("characterization", "rendered output frozen"),

    # --- Phase 9
    "TestPhase9LifeTimeline::test_ingress_finder_known_events":
        ("external", "real sign ingresses, checkable in any ephemeris"),
    "TestPhase9LifeTimeline::test_upcoming_ingresses_sorted_and_bounded":
        ("invariant", "ordering and horizon are structural"),

    # --- Phase 10
    "TestPhase10AntiAnxiety::test_kaal_sarpa_not_formed_when_a_graha_crosses":
        ("invariant", "moving a graha across the axis must dissolve the "
                      "pattern — the rule, not the chart"),
    "TestPhase10AntiAnxiety::test_transit_weather_always_dated":
        ("invariant", "product rule: every difficult season carries an end date"),
    "TestPhase10AntiAnxiety::test_no_fear_language_anywhere":
        ("invariant", "product rule: banned vocabulary"),
    "TestPhase10AntiAnxiety::test_myth_buster_claims_are_read_off_the_chart":
        ("invariant", "product rule: every chart-specific claim in a card "
                      "must be computed from that chart, never hardcoded"),
    "TestPhase10AntiAnxiety::test_kaal_sarpa_card_names_its_late_provenance":
        ("external", "Kaal Sarpa is absent from BPHS, Phaladeepika and "
                     "Saravali — a documented fact about the literature"),

    # --- Phase 11
    "TestPhase11LearnAsYouGo::test_page_renders_learn_ui":
        ("characterization", "rendered output frozen"),

    # --- walkthrough revision
    # The classical claim (Jupiter is exalted in Cancer) and the transit
    # itself are external, but the assertions also read Moon-relative values
    # off the fictional chart — so the tests as written are characterization.
    "TestUIRevisionWalkthrough::test_b_exalted_jupiter_line":
        ("characterization", "dignity is classical, but from_moon/quality "
                             "come from the fictional chart"),
    "TestUIRevisionWalkthrough::test_b_jupiter_on_natal_venus_contact":
        ("characterization", "orb against the fictional chart's Venus"),
    "TestUIRevisionWalkthrough::test_b_nodal_return_surfaces_on_both_nodes":
        ("characterization", "orbs against the fictional chart's nodes"),
    "TestUIRevisionWalkthrough::test_c_ketu_has_its_own_row":
        ("invariant", "product rule: Ketu gets its own slow-mover row"),
    "TestUIRevisionWalkthrough::test_d_no_broken_ordinals":
        ("invariant", "product rule: the ordinal filter is always applied"),
    "TestUIRevisionWalkthrough::test_e_marker_labels_decollided":
        ("invariant", "product rule: timeline labels never overlap"),
    "TestUIRevisionWalkthrough::test_f_favicon_served":
        ("invariant", "product rule: the icon routes resolve"),
    "TestUIRevisionWalkthrough::test_design_handoff_pastel_tokens":
        ("external", "DESIGN-HANDOFF.md token table"),
    "TestUIRevisionWalkthrough::test_framework_six_palettes_by_root_attribute":
        ("external", "Sidera Framework · SIX · TOKENS"),
    "TestUIRevisionWalkthrough::test_framework_non_negotiable_tokens":
        ("external", "Sidera Framework · SIX · TOKENS non-negotiables"),
    "TestUIRevisionWalkthrough::test_design_handoff_glance_pattern":
        ("characterization", "rendered output frozen"),
    "TestUIRevisionWalkthrough::test_a_navigation_and_disclosure":
        ("characterization", "rendered output frozen"),

    # --- pañcāṅga
    "TestPancanga::test_five_limbs_present":
        ("invariant", "the contract requires all five"),
    "TestPancanga::test_nakshatra_agrees_with_dasha_module":
        ("invariant", "one source of truth: longitude only"),
    "TestPancanga::test_angas_carry_end_times":
        ("invariant", "every limb gives way; karaṇa ≤ tithi"),
    "TestPancanga::test_deterministic":
        ("invariant", "pure function of moment and place"),

    # --- guṇa milan
    "TestGunaMilan::test_kuta_names_and_maxima":
        ("external", "classical 1+2+3+4+5+6+7+8 = 36"),
    "TestGunaMilan::test_gana_matrix_is_asymmetric":
        ("external", "Raman's gaṇa table"),
    "TestGunaMilan::test_yoni_sworn_enemies_only_zero":
        ("external", "the seven classical sworn-enemy pairs"),
    "TestGunaMilan::test_reference_pairing_scores":
        ("characterization", "this pairing's totals frozen from own run"),
    "TestGunaMilan::test_pairing_order_changes_the_reckoning":
        ("characterization", "reversed totals frozen from own run"),
    "TestGunaMilan::test_mangal_mutual_cancellation":
        ("characterization", "frozen from own run"),
    "TestGunaMilan::test_fraction_rendering":
        ("external", "Sidera Framework · numeral rule (vulgar fractions)"),
    "TestGunaMilan::test_shape_matches_framework_contract":
        ("invariant", "the aṣṭakūṭa contract: 8 rows summing to 36"),
    "TestGunaMilan::test_deterministic":
        ("invariant", "pure function of the two charts"),

    # --- match UI
    "TestMatchUI::test_no_partner_leaves_dasha_chip":
        ("invariant", "product rule: no partner, no match section"),
    "TestMatchUI::test_partner_place_without_coords_is_refused":
        ("invariant", "product rule: coordinates are never guessed"),

    # --- ask engine
    "TestAskYourChart::test_registry_structure":
        ("invariant", "weights sum to 1; every lens carries a rule"),
    "TestAskYourChart::test_verdict_carries_all_five_outputs":
        ("invariant", "product rule: the five required outputs"),
    "TestAskYourChart::test_answers_deterministic_no_free_text":
        ("invariant", "product rule: no free-text generation"),
    "TestAskYourChart::test_disagreement_is_never_averaged_into_one_answer":
        ("invariant", "core product principle: a split is displayed, never "
                      "resolved — asserted across the whole registry"),
    "TestAskYourChart::test_lenses_disagree_label_exists_for_low_convergence":
        ("invariant", "the convergence thresholds are part of the contract"),

    # --- reading engine (framework FOUR · READING ENGINE)
    "TestReadingEngine::test_condition_weights_match_the_framework_table":
        ("external", "Sidera Framework · CONDITION WEIGHTS table"),
    "TestReadingEngine::test_ties_break_by_natural_graha_order":
        ("external", "framework tie-break rule + classical graha order"),
    "TestReadingEngine::test_voice_word_limits_hold_all_year":
        ("external", "framework VOICE: <15 statement, 25-40 long"),
    "TestReadingEngine::test_voice_forbids_predictions_about_money_health_death":
        ("external", "framework VOICE: no predictions about money/health/death"),
    "TestReadingEngine::test_pancanga_floor_always_yields":
        ("external", "framework: the pañcāṅga set always yields something"),
    "TestReadingEngine::test_ui_renders_the_reading":
        ("characterization", "rendered output frozen"),

    # --- deployability
    "TestDeployability::test_ephemeris_backend_is_explicit":
        ("characterization", "pins the backend swisseph actually serves; a "
                             "change of source invalidates every gate value"),
}


def provenance_for(class_name: str, test_name: str):
    """(class, source) for a test, or None when undeclared."""
    key = f"{class_name}::{test_name}"
    if key in OVERRIDE:
        return OVERRIDE[key]
    return CLASS_DEFAULT.get(class_name)


def pytest_configure(config):
    for name in PROVENANCE_CLASSES:
        config.addinivalue_line(
            "markers", f"{name}: provenance class — see conftest.py")
    config.addinivalue_line("markers", "hygiene: meta-test guarding the suite")


def pytest_collection_modifyitems(items):
    """Attach the declared provenance marker to every collected test.

    Also skip the gate suite wholesale when the reference chart has been
    substituted via SIDERA_FIXTURES: those expectations are anchored to one
    specific birth record, and running them against another chart would
    report failures that are not defects. The hygiene suite still runs.
    """
    import fixtures
    substituted = not fixtures.is_built_in("reference")
    skip_anchored = pytest.mark.skip(
        reason="SIDERA_FIXTURES substitutes the reference chart; the gate "
               "expectations are anchored to the built-in record and have "
               "no known values for another one")
    for item in items:
        if substituted and item.fspath.basename == "test_gates.py":
            item.add_marker(skip_anchored)
        cls = item.cls.__name__ if item.cls else ""
        func = item.originalname or item.name.split("[")[0]
        declared = provenance_for(cls, func)
        if declared:
            item.add_marker(getattr(pytest.mark, declared[0]))
            item.user_properties.append(("provenance", declared[0]))
            item.user_properties.append(("provenance_source", declared[1]))
