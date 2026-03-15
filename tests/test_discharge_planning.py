import pytest
from datetime import datetime, timedelta
from discharge_planning import (
    generate_discharge_plan,
    schedule_follow_up,
    compile_warning_signs,
    generate_social_referrals,
    DischargePlan,
    FollowUpAppointment,
    WarningSign,
    SocialServicesReferral,
)


class TestGenerateDischargePlan:
    @pytest.fixture
    def discharge_date(self):
        return datetime(2025, 1, 15)

    def test_generates_plan_for_heart_failure(self, discharge_date):
        plan = generate_discharge_plan(
            patient_id="P001",
            discharge_date=discharge_date,
            diagnosis="heart failure",
            medications=["lisinopril", "furosemide", "metoprolol"],
        )
        assert isinstance(plan, DischargePlan)
        assert plan.patient_id == "P001"
        assert plan.diagnosis == "heart failure"
        assert len(plan.medications) == 3

    def test_heart_failure_follow_ups(self, discharge_date):
        plan = generate_discharge_plan(
            patient_id="P001",
            discharge_date=discharge_date,
            diagnosis="heart failure",
            medications=[],
        )
        assert len(plan.follow_ups) == 2
        assert plan.follow_ups[0].provider_type == "cardiologist"
        assert plan.follow_ups[0].days_from_discharge == 7
        assert plan.follow_ups[1].provider_type == "primary_care"
        assert plan.follow_ups[1].days_from_discharge == 14

    def test_copd_follow_ups(self, discharge_date):
        plan = generate_discharge_plan(
            patient_id="P001",
            discharge_date=discharge_date,
            diagnosis="copd",
            medications=[],
        )
        assert len(plan.follow_ups) == 2
        assert plan.follow_ups[0].provider_type == "pulmonologist"

    def test_pneumonia_follow_ups(self, discharge_date):
        plan = generate_discharge_plan(
            patient_id="P001",
            discharge_date=discharge_date,
            diagnosis="pneumonia",
            medications=[],
        )
        assert len(plan.follow_ups) == 1
        assert plan.follow_ups[0].days_from_discharge == 7

    def test_follow_up_dates_calculated(self, discharge_date):
        plan = generate_discharge_plan(
            patient_id="P001",
            discharge_date=discharge_date,
            diagnosis="heart failure",
            medications=[],
        )
        assert plan.follow_ups[0].scheduled_date == discharge_date + timedelta(days=7)
        assert plan.follow_ups[1].scheduled_date == discharge_date + timedelta(days=14)

    def test_warning_signs_for_heart_failure(self, discharge_date):
        plan = generate_discharge_plan(
            patient_id="P001",
            discharge_date=discharge_date,
            diagnosis="heart failure",
            medications=[],
        )
        assert len(plan.warning_signs) >= 3
        symptoms = [ws.symptom for ws in plan.warning_signs]
        assert any("weight gain" in s.lower() for s in symptoms)
        assert any("shortness of breath" in s.lower() for s in symptoms)

    def test_warning_signs_for_copd(self, discharge_date):
        plan = generate_discharge_plan(
            patient_id="P001",
            discharge_date=discharge_date,
            diagnosis="copd",
            medications=[],
        )
        assert len(plan.warning_signs) >= 2

    def test_default_warning_signs_for_unknown_diagnosis(self, discharge_date):
        plan = generate_discharge_plan(
            patient_id="P001",
            discharge_date=discharge_date,
            diagnosis="appendicitis",
            medications=[],
        )
        assert len(plan.warning_signs) >= 2

    def test_home_health_referral(self, discharge_date):
        plan = generate_discharge_plan(
            patient_id="P001",
            discharge_date=discharge_date,
            diagnosis="heart failure",
            medications=[],
            needs_home_health=True,
        )
        assert len(plan.social_referrals) == 1
        assert plan.social_referrals[0].referral_type == "home_health"

    def test_transportation_referral(self, discharge_date):
        plan = generate_discharge_plan(
            patient_id="P001",
            discharge_date=discharge_date,
            diagnosis="heart failure",
            medications=[],
            needs_transportation=True,
        )
        assert len(plan.social_referrals) == 1
        assert plan.social_referrals[0].referral_type == "transportation"

    def test_financial_assistance_referral(self, discharge_date):
        plan = generate_discharge_plan(
            patient_id="P001",
            discharge_date=discharge_date,
            diagnosis="heart failure",
            medications=[],
            needs_financial_assistance=True,
        )
        assert len(plan.social_referrals) == 1
        assert plan.social_referrals[0].referral_type == "financial_assistance"
        assert plan.social_referrals[0].priority == "urgent"

    def test_multiple_referrals(self, discharge_date):
        plan = generate_discharge_plan(
            patient_id="P001",
            discharge_date=discharge_date,
            diagnosis="heart failure",
            medications=[],
            needs_home_health=True,
            needs_transportation=True,
            needs_financial_assistance=True,
        )
        assert len(plan.social_referrals) == 3

    def test_no_referrals_when_not_needed(self, discharge_date):
        plan = generate_discharge_plan(
            patient_id="P001",
            discharge_date=discharge_date,
            diagnosis="heart failure",
            medications=[],
        )
        assert len(plan.social_referrals) == 0

    def test_instructions_generated(self, discharge_date):
        plan = generate_discharge_plan(
            patient_id="P001",
            discharge_date=discharge_date,
            diagnosis="heart failure",
            medications=["lisinopril"],
        )
        assert "heart failure" in plan.instructions
        assert "medications" in plan.instructions.lower()

    def test_diabetes_follow_ups(self, discharge_date):
        plan = generate_discharge_plan(
            patient_id="P001",
            discharge_date=discharge_date,
            diagnosis="diabetes",
            medications=[],
        )
        assert len(plan.follow_ups) == 2
        assert plan.follow_ups[0].provider_type == "endocrinologist"


class TestScheduleFollowUp:
    @pytest.fixture
    def discharge_date(self):
        return datetime(2025, 6, 1)

    def test_schedules_correct_date(self, discharge_date):
        appt = schedule_follow_up(
            discharge_date, "cardiologist", 7, "Check volume status"
        )
        assert appt.scheduled_date == discharge_date + timedelta(days=7)
        assert appt.provider_type == "cardiologist"
        assert appt.days_from_discharge == 7

    def test_returns_follow_up_appointment(self, discharge_date):
        appt = schedule_follow_up(discharge_date, "pcp", 14)
        assert isinstance(appt, FollowUpAppointment)

    def test_negative_days_raises(self, discharge_date):
        with pytest.raises(ValueError, match="non-negative"):
            schedule_follow_up(discharge_date, "pcp", -1)

    def test_zero_days(self, discharge_date):
        appt = schedule_follow_up(discharge_date, "pcp", 0)
        assert appt.scheduled_date == discharge_date


class TestCompileWarningSigns:
    def test_heart_failure_warning_signs(self):
        signs = compile_warning_signs("heart failure")
        assert len(signs) >= 3
        assert all(isinstance(s, WarningSign) for s in signs)

    def test_copd_warning_signs(self):
        signs = compile_warning_signs("copd")
        assert len(signs) >= 2

    def test_diabetes_warning_signs(self):
        signs = compile_warning_signs("diabetes")
        assert len(signs) >= 2
        symptoms = [s.symptom for s in signs]
        assert any(
            "blood sugar" in s.lower() or "hypoglycemia" in s.lower() for s in symptoms
        )

    def test_unknown_diagnosis_defaults(self):
        signs = compile_warning_signs("unknown_condition")
        assert len(signs) >= 2

    def test_warning_sign_has_required_fields(self):
        signs = compile_warning_signs("pneumonia")
        sign = signs[0]
        assert sign.symptom
        assert sign.severity in ("low", "moderate", "high")
        assert sign.action
        assert sign.when_to_seek_care


class TestGenerateSocialReferrals:
    def test_single_referral(self):
        referrals = generate_social_referrals(["home_health"])
        assert len(referrals) == 1
        assert referrals[0].referral_type == "home_health"
        assert referrals[0].status == "pending"

    def test_multiple_referrals(self):
        referrals = generate_social_referrals(
            ["home_health", "transportation", "meal_delivery"]
        )
        assert len(referrals) == 3

    def test_urgent_priority_for_financial(self):
        referrals = generate_social_referrals(["financial_assistance"])
        assert referrals[0].priority == "urgent"

    def test_urgent_priority_for_mental_health(self):
        referrals = generate_social_referrals(["mental_health"])
        assert referrals[0].priority == "urgent"

    def test_standard_priority(self):
        referrals = generate_social_referrals(["home_health"])
        assert referrals[0].priority == "standard"

    def test_empty_needs(self):
        referrals = generate_social_referrals([])
        assert len(referrals) == 0

    def test_unknown_need_ignored(self):
        referrals = generate_social_referrals(["home_health", "unknown_service"])
        assert len(referrals) == 1

    def test_case_insensitive(self):
        referrals = generate_social_referrals(["Home_Health"])
        assert len(referrals) == 1

    def test_returns_social_services_referral_objects(self):
        referrals = generate_social_referrals(["transportation"])
        assert isinstance(referrals[0], SocialServicesReferral)
        assert referrals[0].contact_info
