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
    # The out-of-range daśā defect. An invariant of the model, not of any
    # chart: the Vimśottarī spans 120 years and a reading outside it has
    # nothing to read, so it must go silent rather than raise.
    "TestAskOutsideTheDashaRange": (
        "invariant", "product rule: a chart outside the 120-year cycle "
                     "renders, and a lens with nothing to say is silent "
                     "rather than dissenting"),
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
    # Rule precedence. Mostly product rules about which classical rule is
    # allowed to be reported as the verdict — enforced in the validator, so
    # they hold regardless of what any model does on the day.
    "TestContactPrecedence": (
        "invariant", "product rule: a specific transit-to-natal contact "
                     "governs the generic gocara-from-Moon verdict, and a "
                     "conflict between rules must be named, not flattened"),
    # PyJHora — a second, independently written implementation that this app
    # does not link or import (test_hygiene.py enforces it). Same standing as
    # the ERFA cross-check: a source outside this build. If one goes red, the
    # presumption is that Sidera is wrong.
    "TestOracleCrossCheck": (
        "external", "PyJHora (AGPL) via fixtures_pyjhora.json — a second "
                    "implementation, sharing no interpretation code with "
                    "this build (see tools/oracle/README.md)"),
    # These assert the SHAPE of the oracle file, not Sidera's behaviour —
    # nothing they describe is implemented yet. They are invariants of the
    # fixture format, so that regenerating the oracle into something the
    # planned gates cannot rest on fails now rather than mid-feature.
    "TestOracleGatesTheNextMilestones": (
        "invariant", "the fixture shape milestones 2 and 3 are gated "
                     "against, asserted before the features exist"),
    # Layman-first computation options. Product rules about how a choice is
    # PRESENTED (plain English, one recommended default, an explanation per
    # answer) plus the two that give the feature its integrity: no live
    # option may be a control that changes nothing, and every school-
    # dependent statement carries its school.
    # /ask as a method rather than a lookup. Product rules about the reading
    # procedure — every checklist step must be answerable from the ledger,
    # the prompt must require the steps in order, and the new class of claim
    # (transit drishti) must be as checkable as the old ones.
    # The domains-not-techniques restructure. Product rules from
    # ui-design/RESTRUCTURE.md — the load-bearing one is that nothing was
    # lost in the move: every technical section that existed before must
    # still exist, re-homed under "Explore the full chart".
    "TestDomainRestructure::test_the_contents_list_is_one_column_at_every_width":
        ("invariant", "product rule from ui-design/DOSSIER.md: the contents "
                      "page is one column at every width"),
    "TestDomainRestructure": (
        "invariant", "product rules from ui-design/RESTRUCTURE.md: nothing "
                     "deleted, arrival reads wheel → identity → verdict → "
                     "domains, a domain view is verdict-first, every step "
                     "row cites real fact ids, and the reading reports "
                     "condition rather than outcome"),
    # The bug was a browser behaviour — a native picker following the
    # viewer's SYSTEM locale — so the guard has to be a browser. Markup
    # assertions cannot show that Safari rejects a typed "13".
    # Order and economy of speech, from the founder's live walk-through.
    # These are product rules, not observations: the app over-explained and
    # buried the answer, and the budgets and banned phrases are the decision
    # about how it speaks. They constrain ORDER only — every honesty gate is
    # tested unchanged elsewhere.
    # The visual layer, from the founder's editorial-dossier brief. Product
    # rules about SETTING — type scale, pagination, rules, restraint — none
    # of which touch what the app computes or says.
    # The light paper almanac and its scroll choreography, from the approved
    # Claude Design mockup. Product rules about the visual layer; the AA
    # gates recompute contrast from the stylesheet rather than trusting a
    # table in a document.
    "TestReducedMotionInARealBrowser": (
        "invariant", "product rule: a reader who asks for no motion is served "
                     "the finished page — every reveal at its final value, "
                     "nothing left invisible, and the pin kept"),
    "TestTodayScreen": (
        "invariant", "product rule: the first screen is today — three or "
                     "four dated lines, each naming a graha"),
    "TestYourChartsScreen": (
        "invariant", "product rule: every divisional chart is listed, built "
                     "or not, with what it reads"),
    "TestTheTabRow": (
        "invariant", "product rule: five peer screens, always one tap away"),
    "TestTheAskScreen": (
        "invariant", "product rule: the question field renders whether or "
                     "not an answer can be produced; answers are "
                     "verdict-first and footnote the ids they rest on"),
    "TestTheAskScreenInARealBrowser": (
        "invariant", "product rule: the field renders, accepts text, "
                     "submits, and both the answered and the withheld state "
                     "render — driven in a browser"),
    "TestYogasAreCollapsedRows": (
        "invariant", "product rule: a yoga is a closed row carrying name, "
                     "one-line verdict and family; one open at a time"),
    "TestLearnHasAHome": (
        "invariant", "product rule: Learn has a category card and a quiet "
                     "tab entry — not a spotlight, not buried"),
    "TestTextureAndContrast": (
        "invariant", "product rule: a second surface tone, a grain on the "
                     "ground only, a heavier structural rule than a row "
                     "divider, and the bronze as the plate's ink"),
    "TestEveryDivisionMatchesTheOracle": (
        "external", "PyJHora — an independent implementation, compared per "
                    "body and per division for both fictional charts, sign "
                    "AND divisional longitude"),
    "TestAshtakavarga": (
        "external", "PyJHora — an independent implementation, compared per "
                    "SIGN for both fictional charts; plus the classical "
                    "per-graha totals, which gate the table and not the "
                    "computation"),
    "TestTypeFloors": (
        "invariant", "product rule: no rendered text below 13px, prose at "
                     "16 — measured in a browser, SVG scaled by its viewBox"),
    "TestAYogaIsReadNotJustDetected": (
        "invariant", "product rule: a yoga entry says whether the divisional "
                     "charts confirm it, what it gives, when its planets' "
                     "periods run, and where in life"),
    "TestNoEntryIsPrintedTwice": (
        "invariant", "product rule: one entry per phenomenon; a subject with "
                     "two homes is printed once and cross-referenced"),
    "TestVerdictsAreSpecific": (
        "invariant", "product rule: a verdict names at least one graha and, "
                     "where a dated influence runs, says when — specific "
                     "AND short"),
    "TestExploreIndex": (
        "invariant", "product rule: Explore is a grouped index, one category "
                     "on screen at a time, nothing below reading size"),
    "TestNothingOverlaps": (
        "invariant", "product rule: no two pieces of text may share screen "
                     "space at any width or scroll position"),
    "TestPaperPalette": (
        "invariant", "product rule: two readings, one bronze split by role, "
                     "and every text pair recomputed to WCAG AA from "
                     "static/style.css"),
    "TestScrollChoreography": (
        "invariant", "product rules from the approved mockup: rules draw, "
                     "the plate pins and releases, ghost numerals carry it "
                     "down-leaf, verdicts open full-viewport, and "
                     "prefers-reduced-motion serves the finished page"),
    "TestEditorialDossier": (
        "invariant", "product rules from ui-design/DOSSIER.md: a typography-"
                     "led almanac — real type jumps, a folio on every fold, "
                     "the wheel as a captioned plate, a one-column contents "
                     "page, rules above headings, and nothing boxed"),
    "TestEditorialDoctrine": (
        "invariant", "product rules from voice.py: answer first in one "
                     "breath, hard word budgets, no throat-clearing, one "
                     "caveat at the end, and no Sanskrit or house numbers "
                     "in the layer a stranger reads"),
    "TestMaskedBirthFieldsInARealBrowser": (
        "invariant", "product rule: the birth date and time are entered "
                     "identically on every browser and every system locale, "
                     "and digits alone suffice on a numeric keypad"),
    "TestDueDiligenceReading": (
        "invariant", "product rule: a domain question is read across all "
                     "five frames, every step is answerable from the "
                     "ledger, and a transit-aspect claim is checked "
                     "against the table the selected school produced"),
    "TestComputationOptions": (
        "invariant", "product rules: the question must be answerable "
                     "without the vocabulary, every live option must move a "
                     "real computed value, and the chosen school prints on "
                     "each verdict that depended on it"),
    "TestDifferentialHarness": (
        "invariant", "properties of the random-record generator: seeded and "
                     "reproducible, spread over dates and places, never a "
                     "committed fixture, and its output never committed"),
    "TestVimshottariAgainstTheOracle": (
        "external", "PyJHora's Vimshottari MD/AD boundaries for the "
                    "fictional charts — pins the sidereal-year fix the "
                    "300-chart differential run found"),
    # MIXED, deliberately, and the class docstring says which half is which:
    # the Parāśarī padas are gated against PyJHora body by body, while the
    # Jaimini co-lord hierarchy is written from the tradition rather than
    # transcribed, so its structural properties are invariants and its
    # agreement with the oracle is measured rather than asserted.
    "TestArudhas": (
        "external", "PyJHora's A1–A12 under both co-lord schools for the "
                    "fictional charts; the strength hierarchy's structure "
                    "is checked as an invariant, not against them"),
    # MIXED for a different reason than TestArudhas. The eight-karaka half
    # is a true external check — PyJHora computes that scheme itself. The
    # seven-karaka half is not: the oracle's block was derived by the
    # exporter from the same longitudes by dropping Rahu, so agreeing with
    # it is corroboration, not independent confirmation. The class says so
    # and asserts that the oracle keeps admitting it.
    # MIXED again, and the class docstring is explicit about the split:
    # the undisputed subset is checked against PyJHora exactly, while the
    # Scorpio/Aquarius dispositor disagreement is recorded as a finding
    # rather than chased. Only 8 of 56 fixture cases fall in the checked
    # subset, which the gate asserts rather than glosses.
    # INVARIANT, and unusually so for a chart computation: PyJHora
    # implements no avastha, so there is no external anchor here at all.
    # The class docstring says so. Bālādi's partition is asserted directly
    # and jāgradādi's inputs come from the oracle-gated `dignity_at`.
    "TestAvasthas": (
        "invariant", "the bālādi partition and a total mapping over the "
                     "dignity vocabulary — NO oracle exists for avasthās"),
    "TestVimsopaka": (
        "external", "PyJHora's vimsopaka scores for the fictional charts, "
                    "on the subset where the dispositor is not disputed; "
                    "the divergence itself is pinned as an invariant"),
    "TestCharaKarakas": (
        "external", "PyJHora's eight-karaka ordering for the fictional "
                    "charts; the seven-karaka comparison is against a "
                    "derivation and is labelled as one"),
    # A second derivation of the plate, by someone else. TestPlateGeometry
    # proves our two layers agree with each other, which a wholesale rotation
    # of the mapping would survive; this cannot be satisfied by any rotation.
    "TestPlateGeometryAgainstAnIndependentRenderer": (
        "external", "react-native-kundli-chart (MIT) constants/geometry.ts "
                    "HOUSE_POLYGONS — an independently authored "
                    "North-Indian plate; evaluated and NOT adopted, see "
                    "ui-design/RENDERER-EVALUATION.md"),
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
    "TestPhase6FlaskUI::test_birth_date_and_time_are_masked_text_not_native_pickers":
        ("invariant", "product rule: identical entry on every browser "
                      "regardless of system locale — regression from a live "
                      "Render report, macOS Safari 12-hour clock"),
    "TestPhase6FlaskUI::test_the_field_hints_state_the_order_and_the_clock":
        ("invariant", "product rule: a masked field must state its order, "
                      "or the visitor cannot know which chart they cast"),
    "TestPhase6FlaskUI::test_date_parsing_is_day_first_and_never_ambiguous":
        ("invariant", "calendar arithmetic and one stated date order"),
    "TestPhase6FlaskUI::test_month_first_is_refused_with_the_order_spelled_out":
        ("invariant", "product rule: the one wrong entry that would "
                      "otherwise cast a plausible chart must be refused"),
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
    "TestUIRevisionWalkthrough::test_design_handoff_paper_tokens":
        ("external", "DESIGN-HANDOFF.md token table"),
    "TestUIRevisionWalkthrough::test_framework_palettes_by_root_attribute":
        ("external", "Sidera Framework · SIX · TOKENS + the superseding token table in DESIGN-HANDOFF.md"),
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

    # The classical precedence itself (the specific displaces the general;
    # a node on a natal graha eclipses it) is not this build's invention.
    "TestContactPrecedence::test_precedence_rules_are_in_the_library_with_sources":
        ("external", "visesa-over-samanya priority; nodal eclipse reading in "
                     "the nodal-transit literature — each rule names its "
                     "source in rulelib.py"),
    # This one pins where transit Ketu actually is on a fixed date, which any
    # ephemeris can check; the natal half is constructed around it.
    "TestContactPrecedence::test_the_fixture_is_the_configuration_under_test":
        ("external", "transit Ketu at Leo 14°03′58″ on 2026-03-15 — "
                     "checkable in any ephemeris"),

    # The 337 checksum is a classical figure the oracle reproduces, not a
    # property of our file format like the rest of its class.
    "TestOracleGatesTheNextMilestones::test_ashtakavarga_is_raw_per_sign_and_sums_to_337":
        ("external", "BPHS per-planet bindu totals 48/49/39/54/56/52/39 "
                     "summing to 337, reproduced by PyJHora"),

    # This one asserts that restoring the OLD constant breaks the gate — a
    # property of the test, not of any outside source.
    "TestVimshottariAgainstTheOracle::test_the_julian_year_would_fail_this":
        ("invariant", "a gate that cannot go red is decoration"),

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
