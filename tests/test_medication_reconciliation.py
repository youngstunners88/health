import pytest
from medication_reconciliation import (
    check_drug_interactions,
    check_allergy_conflicts,
    detect_medication_changes,
    assess_adherence_risk,
    DrugInteraction,
    AllergyConflict,
    MedicationChange,
    AdherenceRisk,
    SeverityLevel,
    ChangeType,
)


class TestCheckDrugInteractions:
    def test_detects_known_interaction(self):
        interactions = check_drug_interactions(["warfarin", "aspirin", "metoprolol"])
        assert len(interactions) == 1
        assert interactions[0].drug_a == "warfarin"
        assert interactions[0].drug_b == "aspirin"
        assert interactions[0].severity == SeverityLevel.MAJOR

    def test_detects_multiple_interactions(self):
        interactions = check_drug_interactions(
            ["warfarin", "aspirin", "lisinopril", "potassium"]
        )
        assert len(interactions) == 2

    def test_detects_contraindicated_interaction(self):
        interactions = check_drug_interactions(["metformin", "contrast_dye"])
        assert len(interactions) == 1
        assert interactions[0].severity == SeverityLevel.CONTRAINDICATED

    def test_no_interactions(self):
        interactions = check_drug_interactions(
            ["metoprolol", "amlodipine", "lisinopril"]
        )
        assert len(interactions) == 0

    def test_empty_medications_list(self):
        interactions = check_drug_interactions([])
        assert len(interactions) == 0

    def test_single_medication(self):
        interactions = check_drug_interactions(["warfarin"])
        assert len(interactions) == 0

    def test_case_insensitive(self):
        interactions = check_drug_interactions(["Warfarin", "ASPIRIN"])
        assert len(interactions) == 1

    def test_returns_drug_interaction_objects(self):
        interactions = check_drug_interactions(["simvastatin", "amiodarone"])
        assert isinstance(interactions[0], DrugInteraction)
        assert interactions[0].description == "Rhabdomyolysis risk"

    def test_ssri_maoi_contraindicated(self):
        interactions = check_drug_interactions(["ssri", "maoi"])
        assert len(interactions) == 1
        assert interactions[0].severity == SeverityLevel.CONTRAINDICATED
        assert "Serotonin syndrome" in interactions[0].description


class TestCheckAllergyConflicts:
    def test_direct_allergen_match(self):
        conflicts = check_allergy_conflicts(["penicillin"], ["penicillin"])
        assert len(conflicts) == 1
        assert conflicts[0].medication == "penicillin"
        assert conflicts[0].allergen == "penicillin"

    def test_cross_reactive_match(self):
        conflicts = check_allergy_conflicts(["amoxicillin"], ["penicillin"])
        assert len(conflicts) == 1
        assert conflicts[0].allergen == "penicillin"

    def test_no_conflicts(self):
        conflicts = check_allergy_conflicts(
            ["metoprolol", "amlodipine"], ["penicillin"]
        )
        assert len(conflicts) == 0

    def test_multiple_conflicts(self):
        conflicts = check_allergy_conflicts(
            ["amoxicillin", "ibuprofen"],
            ["penicillin", "aspirin"],
        )
        assert len(conflicts) == 2

    def test_empty_medications(self):
        conflicts = check_allergy_conflicts([], ["penicillin"])
        assert len(conflicts) == 0

    def test_empty_allergies(self):
        conflicts = check_allergy_conflicts(["penicillin"], [])
        assert len(conflicts) == 0

    def test_case_insensitive(self):
        conflicts = check_allergy_conflicts(["Penicillin"], ["PENICILLIN"])
        assert len(conflicts) == 1

    def test_sulfa_cross_reactive(self):
        conflicts = check_allergy_conflicts(["furosemide"], ["sulfa"])
        assert len(conflicts) == 1

    def test_codeine_cross_reactive(self):
        conflicts = check_allergy_conflicts(["morphine"], ["codeine"])
        assert len(conflicts) == 1

    def test_returns_allergy_conflict_objects(self):
        conflicts = check_allergy_conflicts(["penicillin"], ["penicillin"])
        assert isinstance(conflicts[0], AllergyConflict)
        assert conflicts[0].severity == SeverityLevel.MAJOR


class TestDetectMedicationChanges:
    def test_new_medication_detected(self):
        current = {"lisinopril": {"dose": 10.0}}
        previous = {}
        changes = detect_medication_changes(current, previous)
        assert len(changes) == 1
        assert changes[0].change_type == ChangeType.NEW_MEDICATION
        assert changes[0].medication_name == "lisinopril"

    def test_discontinued_medication_detected(self):
        current = {}
        previous = {"metoprolol": {"dose": 50.0}}
        changes = detect_medication_changes(current, previous)
        assert len(changes) == 1
        assert changes[0].change_type == ChangeType.DISCONTINUED

    def test_dose_increase_detected(self):
        current = {"lisinopril": {"dose": 20.0}}
        previous = {"lisinopril": {"dose": 10.0}}
        changes = detect_medication_changes(current, previous)
        assert len(changes) == 1
        assert changes[0].change_type == ChangeType.DOSE_INCREASE
        assert changes[0].old_dose == 10.0
        assert changes[0].new_dose == 20.0

    def test_dose_decrease_detected(self):
        current = {"lisinopril": {"dose": 5.0}}
        previous = {"lisinopril": {"dose": 10.0}}
        changes = detect_medication_changes(current, previous)
        assert len(changes) == 1
        assert changes[0].change_type == ChangeType.DOSE_DECREASE

    def test_no_changes(self):
        current = {"lisinopril": {"dose": 10.0}}
        previous = {"lisinopril": {"dose": 10.0}}
        changes = detect_medication_changes(current, previous)
        assert len(changes) == 0

    def test_mixed_changes(self):
        current = {
            "lisinopril": {"dose": 20.0},
            "amlodipine": {"dose": 5.0},
        }
        previous = {
            "lisinopril": {"dose": 10.0},
            "metoprolol": {"dose": 50.0},
        }
        changes = detect_medication_changes(current, previous)
        assert len(changes) == 3
        change_types = {c.change_type for c in changes}
        assert ChangeType.DOSE_INCREASE in change_types
        assert ChangeType.NEW_MEDICATION in change_types
        assert ChangeType.DISCONTINUED in change_types

    def test_empty_both(self):
        changes = detect_medication_changes({}, {})
        assert len(changes) == 0

    def test_returns_medication_change_objects(self):
        current = {"new_med": {"dose": 5.0}}
        previous = {}
        changes = detect_medication_changes(current, previous)
        assert isinstance(changes[0], MedicationChange)

    def test_dose_change_from_none(self):
        current = {"med": {"dose": 10.0}}
        previous = {"med": {}}
        changes = detect_medication_changes(current, previous)
        assert len(changes) == 1
        assert changes[0].change_type == ChangeType.DOSE_INCREASE


class TestAssessAdherenceRisk:
    def test_low_risk_patient(self):
        result = assess_adherence_risk("P001", 5.0, 2, False, False, False)
        assert result.risk_score == 0.0
        assert len(result.risk_factors) == 0
        assert "Standard follow-up" in result.recommendation

    def test_high_missed_doses(self):
        result = assess_adherence_risk("P001", 25.0, 2, False, False, False)
        assert result.risk_score >= 0.3
        assert "High missed dose rate" in result.risk_factors

    def test_polypharmacy(self):
        result = assess_adherence_risk("P001", 5.0, 8, False, False, False)
        assert "Polypharmacy" in result.risk_factors

    def test_cognitive_impairment(self):
        result = assess_adherence_risk("P001", 5.0, 2, True, False, False)
        assert result.risk_score >= 0.25
        assert "Cognitive impairment" in result.risk_factors

    def test_multiple_risk_factors(self):
        result = assess_adherence_risk("P001", 25.0, 8, True, True, True)
        assert result.risk_score >= 0.6
        assert len(result.risk_factors) >= 4
        assert "Immediate intervention" in result.recommendation

    def test_risk_score_capped_at_1(self):
        result = assess_adherence_risk("P001", 50.0, 20, True, True, True)
        assert result.risk_score <= 1.0

    def test_moderate_risk_recommendation(self):
        result = assess_adherence_risk("P001", 15.0, 4, False, False, False)
        assert "Monitor closely" in result.recommendation

    def test_returns_adherence_risk_object(self):
        result = assess_adherence_risk("P001", 5.0, 2, False, False, False)
        assert isinstance(result, AdherenceRisk)
        assert result.patient_id == "P001"

    def test_social_barriers_factor(self):
        result = assess_adherence_risk("P001", 5.0, 2, False, True, False)
        assert "Social barriers" in result.risk_factors

    def test_cost_concern_factor(self):
        result = assess_adherence_risk("P001", 5.0, 2, False, False, True)
        assert "Cost concerns" in result.risk_factors

    def test_boundary_moderate_missed_doses(self):
        result = assess_adherence_risk("P001", 11.0, 2, False, False, False)
        assert "Moderate missed dose rate" in result.risk_factors

    def test_boundary_high_missed_doses(self):
        result = assess_adherence_risk("P001", 21.0, 2, False, False, False)
        assert "High missed dose rate" in result.risk_factors
