import pytest
from datetime import datetime, timedelta
from revenue_cycle import (
    create_claim_line_item,
    submit_claim,
    process_era,
    create_appeal,
    calculate_statistics,
    ClaimLineItem,
    Claim,
    ERAResult,
    Appeal,
    RevenueStatistics,
    ClaimStatus,
    DenialReason,
    claims_db,
    appeals_db,
)


@pytest.fixture(autouse=True)
def clear_databases():
    claims_db.clear()
    appeals_db.clear()
    yield


class TestCreateClaimLineItem:
    def test_creates_line_item(self):
        item = create_claim_line_item("99213", "M06.9", 150.0, 1, "Office visit")
        assert isinstance(item, ClaimLineItem)
        assert item.procedure_code == "99213"
        assert item.diagnosis_code == "M06.9"
        assert item.charge_amount == 150.0
        assert item.units == 1
        assert item.description == "Office visit"

    def test_negative_charge_raises(self):
        with pytest.raises(ValueError, match="non-negative"):
            create_claim_line_item("99213", "M06.9", -50.0, 1, "Office visit")

    def test_zero_units_raises(self):
        with pytest.raises(ValueError, match="at least 1"):
            create_claim_line_item("99213", "M06.9", 150.0, 0, "Office visit")

    def test_negative_units_raises(self):
        with pytest.raises(ValueError, match="at least 1"):
            create_claim_line_item("99213", "M06.9", 150.0, -1, "Office visit")

    def test_multiple_units(self):
        item = create_claim_line_item("J0123", "C50.011", 500.0, 3, "Chemotherapy")
        assert item.units == 3
        assert item.charge_amount == 500.0


class TestSubmitClaim:
    def test_submits_claim_successfully(self):
        line_items = [
            create_claim_line_item("99213", "M06.9", 150.0, 1, "Office visit"),
        ]
        claim = submit_claim("P001", "DR001", "BCBS", line_items)
        assert isinstance(claim, Claim)
        assert claim.status == ClaimStatus.SUBMITTED
        assert claim.patient_id == "P001"
        assert claim.provider_id == "DR001"
        assert claim.payer_id == "BCBS"

    def test_claim_id_format(self):
        line_items = [
            create_claim_line_item("99213", "M06.9", 150.0, 1, "Office visit")
        ]
        claim = submit_claim("P001", "DR001", "BCBS", line_items)
        assert claim.claim_id.startswith("CLM-P001-")

    def test_total_charge_calculated_single_item(self):
        line_items = [
            create_claim_line_item("99213", "M06.9", 150.0, 1, "Office visit")
        ]
        claim = submit_claim("P001", "DR001", "BCBS", line_items)
        assert claim.total_charge == 150.0

    def test_total_charge_calculated_multiple_items(self):
        line_items = [
            create_claim_line_item("99213", "M06.9", 150.0, 1, "Office visit"),
            create_claim_line_item("J0123", "C50.011", 500.0, 2, "Chemotherapy"),
        ]
        claim = submit_claim("P001", "DR001", "BCBS", line_items)
        assert claim.total_charge == 150.0 + 1000.0

    def test_line_items_stored(self):
        line_items = [
            create_claim_line_item("99213", "M06.9", 150.0, 1, "Office visit")
        ]
        claim = submit_claim("P001", "DR001", "BCBS", line_items)
        assert len(claim.line_items) == 1

    def test_submission_date_set(self):
        line_items = [
            create_claim_line_item("99213", "M06.9", 150.0, 1, "Office visit")
        ]
        claim = submit_claim("P001", "DR001", "BCBS", line_items)
        assert isinstance(claim.submission_date, datetime)

    def test_paid_amount_initially_zero(self):
        line_items = [
            create_claim_line_item("99213", "M06.9", 150.0, 1, "Office visit")
        ]
        claim = submit_claim("P001", "DR001", "BCBS", line_items)
        assert claim.paid_amount == 0.0

    def test_denial_reason_initially_none(self):
        line_items = [
            create_claim_line_item("99213", "M06.9", 150.0, 1, "Office visit")
        ]
        claim = submit_claim("P001", "DR001", "BCBS", line_items)
        assert claim.denial_reason is None

    def test_empty_line_items_raises(self):
        with pytest.raises(ValueError, match="at least one"):
            submit_claim("P001", "DR001", "BCBS", [])

    def test_claim_stored_in_db(self):
        line_items = [
            create_claim_line_item("99213", "M06.9", 150.0, 1, "Office visit")
        ]
        claim = submit_claim("P001", "DR001", "BCBS", line_items)
        assert claim.claim_id in claims_db


class TestProcessERA:
    @pytest.fixture
    def claim(self):
        line_items = [
            create_claim_line_item("99213", "M06.9", 150.0, 1, "Office visit")
        ]
        return submit_claim("P001", "DR001", "BCBS", line_items)

    def test_process_paid_era(self, claim):
        era = process_era(claim.claim_id, "paid", 120.0, 30.0, 0.0)
        assert isinstance(era, ERAResult)
        assert era.paid_amount == 120.0
        assert era.adjustment_amount == 30.0

    def test_claim_status_updated_to_paid(self, claim):
        process_era(claim.claim_id, "paid", 120.0)
        assert claims_db[claim.claim_id].status == ClaimStatus.PAID
        assert claims_db[claim.claim_id].paid_amount == 120.0

    def test_process_denied_era(self, claim):
        era = process_era(
            claim.claim_id,
            "denied",
            0.0,
            denial_code="CO-197",
            denial_reason="prior_auth_required",
        )
        assert era.status == "denied"
        assert era.denial_code == "CO-197"
        assert era.denial_reason == "prior_auth_required"

    def test_claim_status_updated_to_denied(self, claim):
        process_era(claim.claim_id, "denied", 0.0, denial_reason="prior_auth_required")
        assert claims_db[claim.claim_id].status == ClaimStatus.DENIED

    def test_denial_reason_mapped(self, claim):
        process_era(
            claim.claim_id, "denied", 0.0, denial_reason="not_medically_necessary"
        )
        assert (
            claims_db[claim.claim_id].denial_reason
            == DenialReason.NOT_MEDICALLY_NECESSARY
        )

    def test_patient_responsibility(self, claim):
        era = process_era(claim.claim_id, "paid", 100.0, 20.0, 30.0)
        assert era.patient_responsibility == 30.0

    def test_unknown_claim_raises(self):
        with pytest.raises(ValueError, match="not found"):
            process_era("UNKNOWN", "paid", 100.0)

    def test_payer_response_date_set(self, claim):
        process_era(claim.claim_id, "paid", 120.0)
        assert claims_db[claim.claim_id].payer_response_date is not None

    def test_era_has_payer_id(self, claim):
        era = process_era(claim.claim_id, "paid", 120.0)
        assert era.payer_id == "BCBS"

    def test_era_processed_date_set(self, claim):
        era = process_era(claim.claim_id, "paid", 120.0)
        assert isinstance(era.processed_date, datetime)

    def test_all_denial_reason_mappings(self, claim):
        denial_reasons = [
            "prior_auth_required",
            "not_medically_necessary",
            "duplicate_claim",
            "coordination_of_benefits",
            "coding_error",
            "timely_filing",
        ]
        expected = [
            DenialReason.PRIOR_AUTH_REQUIRED,
            DenialReason.NOT_MEDICALLY_NECESSARY,
            DenialReason.DUPLICATE_CLAIM,
            DenialReason.COORDINATION_OF_BENEFITS,
            DenialReason.CODING_ERROR,
            DenialReason.TIMELY_FILING,
        ]
        for reason, exp in zip(denial_reasons, expected):
            line_items = [create_claim_line_item("99213", "M06.9", 150.0, 1, "Test")]
            c = submit_claim(f"P-{reason}", "DR001", "BCBS", line_items)
            process_era(c.claim_id, "denied", 0.0, denial_reason=reason)
            assert claims_db[c.claim_id].denial_reason == exp


class TestCreateAppeal:
    @pytest.fixture
    def denied_claim(self):
        line_items = [
            create_claim_line_item("99213", "M06.9", 150.0, 1, "Office visit")
        ]
        claim = submit_claim("P001", "DR001", "BCBS", line_items)
        process_era(claim.claim_id, "denied", 0.0, denial_reason="prior_auth_required")
        return claim

    def test_creates_appeal(self, denied_claim):
        appeal = create_appeal(
            denied_claim.claim_id,
            "Prior auth was obtained",
            ["prior_auth_doc.pdf"],
        )
        assert isinstance(appeal, Appeal)
        assert appeal.claim_id == denied_claim.claim_id
        assert appeal.reason == "Prior auth was obtained"

    def test_appeal_id_format(self, denied_claim):
        appeal = create_appeal(denied_claim.claim_id, "Test", [])
        assert appeal.appeal_id.startswith(f"APL-{denied_claim.claim_id}-")

    def test_supporting_documents_stored(self, denied_claim):
        appeal = create_appeal(
            denied_claim.claim_id,
            "Test",
            ["doc1.pdf", "doc2.pdf"],
        )
        assert appeal.supporting_documents == ["doc1.pdf", "doc2.pdf"]

    def test_claim_status_updated_to_appealed(self, denied_claim):
        create_appeal(denied_claim.claim_id, "Test", [])
        assert claims_db[denied_claim.claim_id].status == ClaimStatus.APPEALED

    def test_submission_date_set(self, denied_claim):
        appeal = create_appeal(denied_claim.claim_id, "Test", [])
        assert isinstance(appeal.submission_date, datetime)

    def test_appeal_status_submitted(self, denied_claim):
        appeal = create_appeal(denied_claim.claim_id, "Test", [])
        assert appeal.status == "submitted"

    def test_appeal_stored_in_db(self, denied_claim):
        appeal = create_appeal(denied_claim.claim_id, "Test", [])
        assert appeal.appeal_id in appeals_db

    def test_unknown_claim_raises(self):
        with pytest.raises(ValueError, match="not found"):
            create_appeal("UNKNOWN", "Test", [])


class TestCalculateStatistics:
    def test_empty_statistics(self):
        stats = calculate_statistics()
        assert isinstance(stats, RevenueStatistics)
        assert stats.total_claims == 0
        assert stats.total_charges == 0.0
        assert stats.total_paid == 0.0
        assert stats.denial_rate == 0.0
        assert stats.collection_rate == 0.0

    def test_single_paid_claim(self):
        line_items = [
            create_claim_line_item("99213", "M06.9", 150.0, 1, "Office visit")
        ]
        claim = submit_claim("P001", "DR001", "BCBS", line_items)
        process_era(claim.claim_id, "paid", 120.0, 30.0)

        stats = calculate_statistics()
        assert stats.total_claims == 1
        assert stats.total_charges == 150.0
        assert stats.total_paid == 120.0
        assert stats.total_denied == 0.0

    def test_mixed_claims(self):
        items1 = [create_claim_line_item("99213", "M06.9", 150.0, 1, "Visit")]
        claim1 = submit_claim("P001", "DR001", "BCBS", items1)
        process_era(claim1.claim_id, "paid", 120.0)

        items2 = [create_claim_line_item("J0123", "C50.011", 500.0, 1, "Chemo")]
        claim2 = submit_claim("P002", "DR001", "BCBS", items2)
        process_era(claim2.claim_id, "denied", 0.0, denial_reason="prior_auth_required")

        stats = calculate_statistics()
        assert stats.total_claims == 2
        assert stats.total_charges == 650.0
        assert stats.total_paid == 120.0
        assert stats.total_denied == 500.0

    def test_denial_rate(self):
        for i in range(4):
            items = [create_claim_line_item("99213", "M06.9", 100.0, 1, "Visit")]
            c = submit_claim(f"P{i}", "DR001", "BCBS", items)
            if i < 1:
                process_era(c.claim_id, "paid", 80.0)
            else:
                process_era(c.claim_id, "denied", 0.0, denial_reason="coding_error")

        stats = calculate_statistics()
        assert stats.denial_rate == 75.0

    def test_collection_rate(self):
        items = [create_claim_line_item("99213", "M06.9", 1000.0, 1, "Visit")]
        claim = submit_claim("P001", "DR001", "BCBS", items)
        process_era(claim.claim_id, "paid", 800.0)

        stats = calculate_statistics()
        assert stats.collection_rate == 80.0

    def test_average_payment_days(self):
        items = [create_claim_line_item("99213", "M06.9", 100.0, 1, "Visit")]
        claim = submit_claim("P001", "DR001", "BCBS", items)
        claims_db[claim.claim_id].payer_response_date = (
            claim.submission_date + timedelta(days=15)
        )
        claims_db[claim.claim_id].status = ClaimStatus.PAID
        claims_db[claim.claim_id].paid_amount = 80.0

        stats = calculate_statistics()
        assert stats.average_payment_days == 15.0

    def test_no_paid_claims_avg_days_zero(self):
        items = [create_claim_line_item("99213", "M06.9", 100.0, 1, "Visit")]
        claim = submit_claim("P001", "DR001", "BCBS", items)
        process_era(claim.claim_id, "denied", 0.0, denial_reason="coding_error")

        stats = calculate_statistics()
        assert stats.average_payment_days == 0.0

    def test_rounding(self):
        items = [create_claim_line_item("99213", "M06.9", 100.333, 1, "Visit")]
        claim = submit_claim("P001", "DR001", "BCBS", items)
        process_era(claim.claim_id, "paid", 80.111)

        stats = calculate_statistics()
        assert stats.total_charges == round(100.333, 2)
        assert stats.total_paid == round(80.111, 2)
