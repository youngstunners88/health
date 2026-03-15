import pytest
from sdoh import (
    calculate_sdoh_score,
    determine_risk_level,
    generate_auto_referrals,
    detect_critical_flags,
    SDOHScreeningResult,
    SDOHDomainScore,
    SDOHReferral,
    SDOHRiskLevel,
    SDOH_DOMAINS,
    SAFETY_CRITICAL_QUESTIONS,
)


class TestCalculateSDOHScore:
    def test_minimal_score_no_positive_responses(self):
        responses = {
            "food_security": {
                "Worried about running out of food": False,
                "Food bought didn't last and no money to get more": False,
                "Cut meal size or skipped meals due to lack of money": False,
            },
        }
        result = calculate_sdoh_score(responses)
        assert result.total_score == 0
        assert result.risk_level == SDOHRiskLevel.MINIMAL

    def test_low_risk_single_domain(self):
        responses = {
            "food_security": {
                "Worried about running out of food": True,
                "Food bought didn't last and no money to get more": False,
                "Cut meal size or skipped meals due to lack of money": False,
            },
        }
        result = calculate_sdoh_score(responses)
        assert result.total_score == 1
        assert result.risk_level == SDOHRiskLevel.LOW

    def test_moderate_risk_multiple_domains(self):
        responses = {
            "food_security": {
                "Worried about running out of food": True,
                "Food bought didn't last and no money to get more": True,
                "Cut meal size or skipped meals due to lack of money": False,
            },
            "transportation": {
                "Missed medical appointment due to transportation": True,
                "No reliable transportation": False,
                "Transportation costs are a burden": False,
            },
        }
        result = calculate_sdoh_score(responses)
        assert result.total_score >= 3

    def test_high_risk_score(self):
        responses = {
            "food_security": {
                "Worried about running out of food": True,
                "Food bought didn't last and no money to get more": True,
                "Cut meal size or skipped meals due to lack of money": True,
            },
            "housing": {
                "Not paid full rent/mortgage in past 2 months": True,
                "Moved in with others due to financial problems": True,
                "Stayed in shelter, car, or outside": False,
            },
            "utilities": {
                "Electricity/gas shut off recently": True,
                "Difficulty paying utility bills": True,
                "Home temperature unsafe": False,
            },
        }
        result = calculate_sdoh_score(responses)
        assert result.risk_level in (
            SDOHRiskLevel.MODERATE,
            SDOHRiskLevel.HIGH,
            SDOHRiskLevel.CRITICAL,
        )

    def test_critical_flags_for_safety(self):
        responses = {
            "safety": {
                "Felt unsafe at home": True,
                "Experienced physical violence": False,
                "Experienced emotional abuse": False,
            },
        }
        result = calculate_sdoh_score(responses)
        assert len(result.critical_flags) >= 1
        assert any("SAFETY" in flag for flag in result.critical_flags)

    def test_multiple_critical_flags(self):
        responses = {
            "safety": {
                "Felt unsafe at home": True,
                "Experienced physical violence": True,
                "Experienced emotional abuse": False,
            },
        }
        result = calculate_sdoh_score(responses)
        assert len(result.critical_flags) >= 2

    def test_weighted_scoring(self):
        food_responses = {
            "Worried about running out of food": True,
            "Food bought didn't last and no money to get more": True,
            "Cut meal size or skipped meals due to lack of money": True,
        }
        safety_responses = {
            "Felt unsafe at home": True,
            "Experienced physical violence": True,
            "Experienced emotional abuse": True,
        }
        responses = {
            "food_security": food_responses,
            "safety": safety_responses,
        }
        result = calculate_sdoh_score(responses)
        safety_domain = next(d for d in result.domain_scores if d.domain == "safety")
        food_domain = next(
            d for d in result.domain_scores if d.domain == "food_security"
        )
        assert safety_domain.score > food_domain.score

    def test_returns_screening_result(self):
        responses = {
            "food_security": {
                "Worried about running out of food": False,
                "Food bought didn't last and no money to get more": False,
                "Cut meal size or skipped meals due to lack of money": False,
            },
        }
        result = calculate_sdoh_score(responses)
        assert isinstance(result, SDOHScreeningResult)

    def test_domain_scores_populated(self):
        responses = {
            "food_security": {
                "Worried about running out of food": True,
                "Food bought didn't last and no money to get more": False,
                "Cut meal size or skipped meals due to lack of money": False,
            },
            "housing": {
                "Not paid full rent/mortgage in past 2 months": False,
                "Moved in with others due to financial problems": False,
                "Stayed in shelter, car, or outside": False,
            },
        }
        result = calculate_sdoh_score(responses)
        assert len(result.domain_scores) == 2

    def test_max_possible_score_calculated(self):
        responses = {
            "food_security": {
                "Worried about running out of food": False,
                "Food bought didn't last and no money to get more": False,
                "Cut meal size or skipped meals due to lack of money": False,
            },
        }
        result = calculate_sdoh_score(responses)
        assert result.max_possible_score > 0

    def test_empty_responses(self):
        result = calculate_sdoh_score({})
        assert result.total_score == 0
        assert result.risk_level == SDOHRiskLevel.MINIMAL
        assert len(result.domain_scores) == 0

    def test_partial_domains(self):
        responses = {
            "housing": {
                "Not paid full rent/mortgage in past 2 months": True,
                "Moved in with others due to financial problems": True,
                "Stayed in shelter, car, or outside": True,
            },
        }
        result = calculate_sdoh_score(responses)
        assert len(result.domain_scores) == 1


class TestDetermineRiskLevel:
    @pytest.mark.parametrize(
        "score,expected",
        [
            (0, SDOHRiskLevel.MINIMAL),
            (1, SDOHRiskLevel.LOW),
            (2, SDOHRiskLevel.LOW),
            (3, SDOHRiskLevel.MODERATE),
            (5, SDOHRiskLevel.MODERATE),
            (6, SDOHRiskLevel.HIGH),
            (8, SDOHRiskLevel.HIGH),
            (9, SDOHRiskLevel.CRITICAL),
            (20, SDOHRiskLevel.CRITICAL),
        ],
    )
    def test_risk_level_classification(self, score, expected):
        assert determine_risk_level(score) == expected

    def test_negative_score_raises(self):
        with pytest.raises(ValueError, match="non-negative"):
            determine_risk_level(-1)


class TestGenerateAutoReferrals:
    def test_referral_for_positive_food_security(self):
        responses = {
            "food_security": {
                "Worried about running out of food": True,
                "Food bought didn't last and no money to get more": False,
                "Cut meal size or skipped meals due to lack of money": False,
            },
        }
        screening = calculate_sdoh_score(responses)
        referrals = generate_auto_referrals("P001", screening)
        assert len(referrals) == 1
        assert referrals[0].service_type == "food_bank"

    def test_referral_for_positive_housing(self):
        responses = {
            "housing": {
                "Not paid full rent/mortgage in past 2 months": True,
                "Moved in with others due to financial problems": False,
                "Stayed in shelter, car, or outside": False,
            },
        }
        screening = calculate_sdoh_score(responses)
        referrals = generate_auto_referrals("P001", screening)
        assert len(referrals) == 1
        assert referrals[0].service_type == "housing_assistance"

    def test_no_referrals_for_no_positive_responses(self):
        responses = {
            "food_security": {
                "Worried about running out of food": False,
                "Food bought didn't last and no money to get more": False,
                "Cut meal size or skipped meals due to lack of money": False,
            },
        }
        screening = calculate_sdoh_score(responses)
        referrals = generate_auto_referrals("P001", screening)
        assert len(referrals) == 0

    def test_safety_referral_is_urgent(self):
        responses = {
            "safety": {
                "Felt unsafe at home": True,
                "Experienced physical violence": False,
                "Experienced emotional abuse": False,
            },
        }
        screening = calculate_sdoh_score(responses)
        referrals = generate_auto_referrals("P001", screening)
        assert len(referrals) == 1
        assert referrals[0].priority == "urgent"

    def test_non_safety_referral_is_standard(self):
        responses = {
            "food_security": {
                "Worried about running out of food": True,
                "Food bought didn't last and no money to get more": False,
                "Cut meal size or skipped meals due to lack of money": False,
            },
        }
        screening = calculate_sdoh_score(responses)
        referrals = generate_auto_referrals("P001", screening)
        assert referrals[0].priority == "standard"

    def test_multiple_referrals(self):
        responses = {
            "food_security": {
                "Worried about running out of food": True,
                "Food bought didn't last and no money to get more": False,
                "Cut meal size or skipped meals due to lack of money": False,
            },
            "transportation": {
                "Missed medical appointment due to transportation": True,
                "No reliable transportation": False,
                "Transportation costs are a burden": False,
            },
        }
        screening = calculate_sdoh_score(responses)
        referrals = generate_auto_referrals("P001", screening)
        assert len(referrals) == 2

    def test_referral_id_format(self):
        responses = {
            "food_security": {
                "Worried about running out of food": True,
                "Food bought didn't last and no money to get more": False,
                "Cut meal size or skipped meals due to lack of money": False,
            },
        }
        screening = calculate_sdoh_score(responses)
        referrals = generate_auto_referrals("P001", screening)
        assert referrals[0].referral_id.startswith("SDOH-P001-")

    def test_referral_status_pending(self):
        responses = {
            "food_security": {
                "Worried about running out of food": True,
                "Food bought didn't last and no money to get more": False,
                "Cut meal size or skipped meals due to lack of money": False,
            },
        }
        screening = calculate_sdoh_score(responses)
        referrals = generate_auto_referrals("P001", screening)
        assert referrals[0].status == "pending"

    def test_returns_sdoh_referral_objects(self):
        responses = {
            "food_security": {
                "Worried about running out of food": True,
                "Food bought didn't last and no money to get more": False,
                "Cut meal size or skipped meals due to lack of money": False,
            },
        }
        screening = calculate_sdoh_score(responses)
        referrals = generate_auto_referrals("P001", screening)
        assert isinstance(referrals[0], SDOHReferral)

    def test_referral_has_reason(self):
        responses = {
            "food_security": {
                "Worried about running out of food": True,
                "Food bought didn't last and no money to get more": False,
                "Cut meal size or skipped meals due to lack of money": False,
            },
        }
        screening = calculate_sdoh_score(responses)
        referrals = generate_auto_referrals("P001", screening)
        assert "food security" in referrals[0].reason.lower()


class TestDetectCriticalFlags:
    def test_detects_safety_flag(self):
        responses = {
            "safety": {
                "Felt unsafe at home": True,
                "Experienced physical violence": False,
                "Experienced emotional abuse": False,
            },
        }
        flags = detect_critical_flags(responses)
        assert len(flags) == 1
        assert "Felt unsafe at home" in flags[0]

    def test_detects_multiple_safety_flags(self):
        responses = {
            "safety": {
                "Felt unsafe at home": True,
                "Experienced physical violence": True,
                "Experienced emotional abuse": True,
            },
        }
        flags = detect_critical_flags(responses)
        assert len(flags) == 3

    def test_no_flags_when_no_safety_issues(self):
        responses = {
            "food_security": {
                "Worried about running out of food": True,
                "Food bought didn't last and no money to get more": False,
                "Cut meal size or skipped meals due to lack of money": False,
            },
        }
        flags = detect_critical_flags(responses)
        assert len(flags) == 0

    def test_empty_responses(self):
        flags = detect_critical_flags({})
        assert len(flags) == 0

    def test_safety_domain_all_false(self):
        responses = {
            "safety": {
                "Felt unsafe at home": False,
                "Experienced physical violence": False,
                "Experienced emotional abuse": False,
            },
        }
        flags = detect_critical_flags(responses)
        assert len(flags) == 0

    def test_flag_format_includes_safety_prefix(self):
        responses = {
            "safety": {
                "Experienced physical violence": True,
                "Felt unsafe at home": False,
                "Experienced emotional abuse": False,
            },
        }
        flags = detect_critical_flags(responses)
        assert all(flag.startswith("SAFETY:") for flag in flags)
