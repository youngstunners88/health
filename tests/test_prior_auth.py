import pytest
from datetime import datetime
from prior_auth import (
    create_prior_auth_request,
    check_payer_rules,
    generate_clinical_justification,
    generate_appeal_letter,
    process_auth_decision,
    PriorAuthRequest,
    PayerRule,
    AppealLetter,
    AuthDecision,
    AuthStatus,
    PAYER_RULES,
)


class TestCreatePriorAuthRequest:
    def test_creates_request_with_pending_status(self):
        request = create_prior_auth_request(
            patient_id="P001",
            provider_id="DR001",
            service_code="J0123",
            diagnosis_code="C50.011",
            payer="medicare",
            clinical_notes="Patient requires chemotherapy",
        )
        assert isinstance(request, PriorAuthRequest)
        assert request.status == AuthStatus.PENDING
        assert request.patient_id == "P001"
        assert request.provider_id == "DR001"

    def test_request_id_format(self):
        request = create_prior_auth_request(
            patient_id="P001",
            provider_id="DR001",
            service_code="J0123",
            diagnosis_code="C50.011",
            payer="medicare",
            clinical_notes="Test",
        )
        assert request.request_id.startswith("PA-P001-J0123-")

    def test_default_urgency_is_routine(self):
        request = create_prior_auth_request(
            patient_id="P001",
            provider_id="DR001",
            service_code="J0123",
            diagnosis_code="C50.011",
            payer="medicare",
            clinical_notes="Test",
        )
        assert request.urgency == "routine"

    def test_urgent_urgency(self):
        request = create_prior_auth_request(
            patient_id="P001",
            provider_id="DR001",
            service_code="J0123",
            diagnosis_code="C50.011",
            payer="medicare",
            clinical_notes="Test",
            urgency="urgent",
        )
        assert request.urgency == "urgent"

    def test_expedited_urgency(self):
        request = create_prior_auth_request(
            patient_id="P001",
            provider_id="DR001",
            service_code="J0123",
            diagnosis_code="C50.011",
            payer="medicare",
            clinical_notes="Test",
            urgency="expedited",
        )
        assert request.urgency == "expedited"

    def test_invalid_urgency_raises(self):
        with pytest.raises(ValueError, match="routine, urgent, or expedited"):
            create_prior_auth_request(
                patient_id="P001",
                provider_id="DR001",
                service_code="J0123",
                diagnosis_code="C50.011",
                payer="medicare",
                clinical_notes="Test",
                urgency="emergency",
            )

    def test_submitted_date_set(self):
        request = create_prior_auth_request(
            patient_id="P001",
            provider_id="DR001",
            service_code="J0123",
            diagnosis_code="C50.011",
            payer="medicare",
            clinical_notes="Test",
        )
        assert isinstance(request.submitted_date, datetime)

    def test_clinical_notes_stored(self):
        request = create_prior_auth_request(
            patient_id="P001",
            provider_id="DR001",
            service_code="J0123",
            diagnosis_code="C50.011",
            payer="medicare",
            clinical_notes="Detailed clinical notes here",
        )
        assert request.clinical_notes == "Detailed clinical notes here"


class TestCheckPayerRules:
    def test_medicare_requires_prior_auth(self):
        rule = check_payer_rules("medicare", "J0123", "C50.011")
        assert rule.requires_prior_auth is True
        assert rule.turnaround_days == 14

    def test_commercial_no_prior_auth_needed(self):
        rule = check_payer_rules("commercial", "99213", "M06.9")
        assert rule.requires_prior_auth is False

    def test_commercial_requires_prior_auth(self):
        rule = check_payer_rules("commercial", "J3420", "M06.9")
        assert rule.requires_prior_auth is True
        assert rule.turnaround_days == 7

    def test_valid_diagnosis_accepted(self):
        rule = check_payer_rules("medicare", "J0123", "C34.10")
        assert rule.requires_prior_auth is True

    def test_invalid_diagnosis_raises(self):
        with pytest.raises(ValueError, match="not valid"):
            check_payer_rules("medicare", "J0123", "INVALID")

    def test_unknown_service_returns_no_auth_required(self):
        rule = check_payer_rules("medicare", "UNKNOWN", "C50.011")
        assert rule.requires_prior_auth is False

    def test_documentation_requirements(self):
        rule = check_payer_rules("medicare", "J0123", "C50.011")
        assert "medical_necessity" in rule.documentation_requirements
        assert "failed_conservative_treatment" in rule.documentation_requirements

    def test_medicaid_stronger_requirements(self):
        rule = check_payer_rules("medicaid", "J0123", "C50.011")
        assert rule.turnaround_days == 21
        assert "imaging" in rule.documentation_requirements

    def test_case_insensitive_payer(self):
        rule = check_payer_rules("MEDICARE", "J0123", "C50.011")
        assert rule.requires_prior_auth is True

    def test_case_insensitive_service_code(self):
        rule = check_payer_rules("medicare", "j0123", "C50.011")
        assert rule.requires_prior_auth is True

    def test_returns_payer_rule_object(self):
        rule = check_payer_rules("medicare", "J0123", "C50.011")
        assert isinstance(rule, PayerRule)


class TestGenerateClinicalJustification:
    def test_j0123_template(self):
        justification = generate_clinical_justification(
            service_code="J0123",
            diagnosis="C50.011",
            failed_treatments=["radiation", "surgery"],
        )
        assert "C50.011" in justification
        assert "radiation" in justification
        assert "surgery" in justification
        assert "Laboratory results" in justification

    def test_j3420_template(self):
        justification = generate_clinical_justification(
            service_code="J3420",
            diagnosis="M06.9",
            failed_treatments=["methotrexate"],
        )
        assert "M06.9" in justification
        assert "step therapy" in justification.lower()
        assert "methotrexate" in justification

    def test_empty_treatments(self):
        justification = generate_clinical_justification(
            service_code="J0123",
            diagnosis="C50.011",
            failed_treatments=[],
        )
        assert "none documented" in justification

    def test_unknown_service_uses_default_template(self):
        justification = generate_clinical_justification(
            service_code="UNKNOWN",
            diagnosis="M06.9",
            failed_treatments=["physical therapy"],
        )
        assert "M06.9" in justification
        assert "physical therapy" in justification

    def test_additional_notes_included(self):
        justification = generate_clinical_justification(
            service_code="J0123",
            diagnosis="C50.011",
            failed_treatments=["radiation"],
            additional_notes="Patient has comorbidities",
        )
        assert "Patient has comorbidities" in justification

    def test_returns_string(self):
        justification = generate_clinical_justification(
            service_code="J0123",
            diagnosis="C50.011",
            failed_treatments=["radiation"],
        )
        assert isinstance(justification, str)
        assert len(justification) > 0


class TestGenerateAppealLetter:
    def test_generates_appeal_letter(self):
        letter = generate_appeal_letter(
            request_id="PA-001",
            patient_id="P001",
            payer="medicare",
            denial_reason="Not medically necessary",
            clinical_justification="Patient requires treatment",
            supporting_documents=["lab_results.pdf", "progress_notes.pdf"],
        )
        assert isinstance(letter, AppealLetter)
        assert letter.request_id == "PA-001"
        assert letter.patient_id == "P001"
        assert letter.payer == "medicare"

    def test_letter_content_includes_denial_reason(self):
        letter = generate_appeal_letter(
            request_id="PA-001",
            patient_id="P001",
            payer="medicare",
            denial_reason="Prior auth required",
            clinical_justification="Justification text",
            supporting_documents=[],
        )
        assert "Prior auth required" in letter.letter_content

    def test_letter_content_includes_justification(self):
        letter = generate_appeal_letter(
            request_id="PA-001",
            patient_id="P001",
            payer="medicare",
            denial_reason="Test",
            clinical_justification="Clinical justification here",
            supporting_documents=[],
        )
        assert "Clinical justification here" in letter.letter_content

    def test_letter_content_includes_documents(self):
        letter = generate_appeal_letter(
            request_id="PA-001",
            patient_id="P001",
            payer="medicare",
            denial_reason="Test",
            clinical_justification="Test",
            supporting_documents=["doc1.pdf", "doc2.pdf"],
        )
        assert "doc1.pdf" in letter.letter_content
        assert "doc2.pdf" in letter.letter_content

    def test_letter_has_formal_structure(self):
        letter = generate_appeal_letter(
            request_id="PA-001",
            patient_id="P001",
            payer="medicare",
            denial_reason="Test",
            clinical_justification="Test",
            supporting_documents=[],
        )
        assert "APPEAL FOR PRIOR AUTHORIZATION DENIAL" in letter.letter_content
        assert "Dear Appeals Department" in letter.letter_content
        assert "Sincerely" in letter.letter_content

    def test_supporting_documents_stored(self):
        letter = generate_appeal_letter(
            request_id="PA-001",
            patient_id="P001",
            payer="medicare",
            denial_reason="Test",
            clinical_justification="Test",
            supporting_documents=["lab.pdf"],
        )
        assert letter.supporting_documents == ["lab.pdf"]

    def test_submission_date_set(self):
        letter = generate_appeal_letter(
            request_id="PA-001",
            patient_id="P001",
            payer="medicare",
            denial_reason="Test",
            clinical_justification="Test",
            supporting_documents=[],
        )
        assert isinstance(letter.submission_date, datetime)


class TestProcessAuthDecision:
    def test_approved_decision(self):
        decision = process_auth_decision(
            request_id="PA-001",
            approved=True,
            reason="Medical necessity confirmed",
            authorized_units=10,
            authorized_period_days=90,
        )
        assert decision.status == AuthStatus.APPROVED
        assert decision.authorized_units == 10
        assert decision.authorized_period_days == 90
        assert decision.denial_reason is None

    def test_denied_decision(self):
        decision = process_auth_decision(
            request_id="PA-001",
            approved=False,
            reason="Does not meet criteria",
            denial_reason="Not medically necessary",
        )
        assert decision.status == AuthStatus.DENIED
        assert decision.denial_reason == "Not medically necessary"
        assert decision.authorized_units is None

    def test_decision_date_set(self):
        decision = process_auth_decision(
            request_id="PA-001",
            approved=True,
            reason="Approved",
        )
        assert isinstance(decision.decision_date, datetime)

    def test_returns_auth_decision(self):
        decision = process_auth_decision(
            request_id="PA-001",
            approved=True,
            reason="Approved",
        )
        assert isinstance(decision, AuthDecision)

    def test_denied_without_reason(self):
        decision = process_auth_decision(
            request_id="PA-001",
            approved=False,
            reason="Denied",
        )
        assert decision.status == AuthStatus.DENIED
        assert decision.denial_reason is None
