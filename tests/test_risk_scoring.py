import pytest
from risk_scoring import (
    calculate_lace_index,
    calculate_hospital_score,
    classify_risk_level,
    RiskLevel,
    LaceScoreResult,
)


class TestCalculateLaceIndex:
    def test_low_risk_score(self):
        result = calculate_lace_index(1, 1, 1, 1)
        assert result.total == 4
        assert result.risk_level == RiskLevel.LOW

    def test_moderate_risk_score(self):
        result = calculate_lace_index(2, 2, 2, 2)
        assert result.total == 8
        assert result.risk_level == RiskLevel.MODERATE

    def test_high_risk_score(self):
        result = calculate_lace_index(3, 3, 3, 3)
        assert result.total == 12
        assert result.risk_level == RiskLevel.HIGH

    def test_very_high_risk_score(self):
        result = calculate_lace_index(5, 5, 5, 5)
        assert result.total == 20
        assert result.risk_level == RiskLevel.VERY_HIGH

    def test_known_lace_values(self):
        result = calculate_lace_index(3, 2, 4, 1)
        assert result.length_of_stay == 3
        assert result.acuity == 2
        assert result.comorbidity == 4
        assert result.emergency_visits == 1
        assert result.total == 10
        assert result.risk_level == RiskLevel.HIGH

    def test_minimum_score(self):
        result = calculate_lace_index(0, 0, 0, 0)
        assert result.total == 0
        assert result.risk_level == RiskLevel.LOW

    def test_boundary_low_to_moderate(self):
        result_at_4 = calculate_lace_index(1, 1, 1, 1)
        assert result_at_4.risk_level == RiskLevel.LOW
        result_at_5 = calculate_lace_index(2, 1, 1, 1)
        assert result_at_5.risk_level == RiskLevel.MODERATE

    def test_boundary_moderate_to_high(self):
        result_at_8 = calculate_lace_index(2, 2, 2, 2)
        assert result_at_8.risk_level == RiskLevel.MODERATE
        result_at_9 = calculate_lace_index(3, 2, 2, 2)
        assert result_at_9.risk_level == RiskLevel.HIGH

    def test_boundary_high_to_very_high(self):
        result_at_12 = calculate_lace_index(3, 3, 3, 3)
        assert result_at_12.risk_level == RiskLevel.HIGH
        result_at_13 = calculate_lace_index(4, 3, 3, 3)
        assert result_at_13.risk_level == RiskLevel.VERY_HIGH

    def test_returns_lace_score_result(self):
        result = calculate_lace_index(2, 3, 1, 2)
        assert isinstance(result, LaceScoreResult)

    def test_negative_length_of_stay_raises(self):
        with pytest.raises(ValueError, match="non-negative"):
            calculate_lace_index(-1, 1, 1, 1)

    def test_negative_acuity_raises(self):
        with pytest.raises(ValueError, match="non-negative"):
            calculate_lace_index(1, -1, 1, 1)

    def test_negative_comorbidity_raises(self):
        with pytest.raises(ValueError, match="non-negative"):
            calculate_lace_index(1, 1, -1, 1)

    def test_negative_emergency_visits_raises(self):
        with pytest.raises(ValueError, match="non-negative"):
            calculate_lace_index(1, 1, 1, -1)

    def test_extreme_values(self):
        result = calculate_lace_index(100, 100, 100, 100)
        assert result.total == 400
        assert result.risk_level == RiskLevel.VERY_HIGH


class TestCalculateHospitalScore:
    def test_elective_admission_low_risk(self):
        result = calculate_hospital_score(40, "elective", 0, 0)
        assert result.acuity == 1
        assert result.risk_level == RiskLevel.LOW

    def test_emergency_admission(self):
        result = calculate_hospital_score(50, "emergency", 2, 1)
        assert result.acuity == 3
        assert result.total == 5 + 3 + 2 + 2

    def test_trauma_admission(self):
        result = calculate_hospital_score(60, "trauma", 3, 2)
        assert result.acuity == 4
        assert result.length_of_stay == 5

    def test_urgent_admission(self):
        result = calculate_hospital_score(30, "urgent", 1, 0)
        assert result.acuity == 2
        assert result.risk_level == RiskLevel.LOW

    def test_high_risk_elderly_patient(self):
        result = calculate_hospital_score(85, "emergency", 5, 4)
        assert result.length_of_stay == 5
        assert result.acuity == 3
        assert result.comorbidity == 5
        assert result.emergency_visits == 6
        assert result.total == 19
        assert result.risk_level == RiskLevel.VERY_HIGH

    def test_age_component_capped_at_5(self):
        result = calculate_hospital_score(100, "elective", 0, 0)
        assert result.length_of_stay == 5

    def test_comorbidity_component_capped_at_5(self):
        result = calculate_hospital_score(30, "elective", 10, 0)
        assert result.comorbidity == 5

    def test_emergency_component_capped_at_6(self):
        result = calculate_hospital_score(30, "elective", 0, 10)
        assert result.emergency_visits == 6

    def test_boundary_moderate_risk(self):
        result = calculate_hospital_score(50, "urgent", 2, 1)
        assert result.total == 5 + 2 + 2 + 2
        assert result.risk_level == RiskLevel.MODERATE

    def test_negative_age_raises(self):
        with pytest.raises(ValueError, match="non-negative"):
            calculate_hospital_score(-1, "elective", 0, 0)

    def test_invalid_admission_type_raises(self):
        with pytest.raises(ValueError, match="Invalid admission type"):
            calculate_hospital_score(50, "outpatient", 0, 0)

    def test_negative_comorbidities_raises(self):
        with pytest.raises(ValueError, match="non-negative"):
            calculate_hospital_score(50, "elective", -1, 0)

    def test_negative_prior_admissions_raises(self):
        with pytest.raises(ValueError, match="non-negative"):
            calculate_hospital_score(50, "elective", 0, -1)


class TestClassifyRiskLevel:
    @pytest.mark.parametrize(
        "score,expected",
        [
            (0, RiskLevel.LOW),
            (1, RiskLevel.LOW),
            (4, RiskLevel.LOW),
            (5, RiskLevel.MODERATE),
            (8, RiskLevel.MODERATE),
            (9, RiskLevel.HIGH),
            (12, RiskLevel.HIGH),
            (13, RiskLevel.VERY_HIGH),
            (20, RiskLevel.VERY_HIGH),
            (100, RiskLevel.VERY_HIGH),
        ],
    )
    def test_risk_classification(self, score, expected):
        assert classify_risk_level(score) == expected

    def test_negative_score_raises(self):
        with pytest.raises(ValueError, match="non-negative"):
            classify_risk_level(-1)
