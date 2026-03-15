"""
Revenue Cycle Engine
Claims submission (837P/837I), denial management, charge capture, and reconciliation.
"""

import json
import uuid
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Optional


DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

CLAIMS_FILE = DATA_DIR / "claims.json"
CHARGES_FILE = DATA_DIR / "charges.json"
ERA_FILE = DATA_DIR / "eras.json"


class ClaimsEngine:
    """Manages the full claims lifecycle."""

    def __init__(self):
        self.claims = self._load_claims()
        self.charges = self._load_charges()
        self.eras = self._load_eras()

    def _load_claims(self) -> list[dict]:
        if CLAIMS_FILE.exists():
            try:
                return json.loads(CLAIMS_FILE.read_text())
            except json.JSONDecodeError:
                pass
        return []

    def _save_claims(self):
        CLAIMS_FILE.write_text(json.dumps(self.claims[-1000:], indent=2, default=str))

    def _load_charges(self) -> list[dict]:
        if CHARGES_FILE.exists():
            try:
                return json.loads(CHARGES_FILE.read_text())
            except json.JSONDecodeError:
                pass
        return []

    def _save_charges(self):
        CHARGES_FILE.write_text(json.dumps(self.charges[-1000:], indent=2, default=str))

    def _load_eras(self) -> list[dict]:
        if ERA_FILE.exists():
            try:
                return json.loads(ERA_FILE.read_text())
            except json.JSONDecodeError:
                pass
        return []

    def _save_eras(self):
        ERA_FILE.write_text(json.dumps(self.eras[-500:], indent=2, default=str))

    def submit_claim(
        self,
        patient_id: str,
        patient_name: str,
        patient_dob: str,
        patient_mrn: str,
        payer_name: str,
        payer_id: str,
        subscriber_id: str,
        provider_name: str,
        provider_npi: str,
        provider_tax_id: str,
        place_of_service: str,
        claim_type: str = "professional",
        diagnoses: list[str] | None = None,
        procedures: list[dict] | None = None,
        charge_amount: float = 0.0,
        prior_auth_id: str = "",
        notes: str = "",
    ) -> dict:
        """Submit a new claim (837P for professional, 837I for institutional)."""
        claim_id = f"CLM-{uuid.uuid4().hex[:8].upper()}"
        now = datetime.now(timezone.utc)

        claim = {
            "claim_id": claim_id,
            "claim_type": claim_type,
            "form_type": "837P" if claim_type == "professional" else "837I",
            "patient": {
                "patient_id": patient_id,
                "name": patient_name,
                "dob": patient_dob,
                "mrn": patient_mrn,
            },
            "payer": {
                "name": payer_name,
                "payer_id": payer_id,
                "subscriber_id": subscriber_id,
            },
            "provider": {
                "name": provider_name,
                "npi": provider_npi,
                "tax_id": provider_tax_id,
                "place_of_service": place_of_service,
            },
            "diagnoses": diagnoses or [],
            "procedures": procedures or [],
            "charge_amount": charge_amount,
            "prior_auth_id": prior_auth_id,
            "notes": notes,
            "status": "submitted",
            "submitted_at": now.isoformat(),
            "submitted_to_clearinghouse": True,
            "clearinghouse_trace": f"TRC-{uuid.uuid4().hex[:10].upper()}",
            "acknowledgment": None,
            "accepted_at": None,
            "rejected_at": None,
            "rejection_reason": None,
            "adjudicated_at": None,
            "allowed_amount": 0.0,
            "paid_amount": 0.0,
            "patient_responsibility": 0.0,
            "denial_reason": None,
            "denial_codes": [],
            "appeals": [],
            "era_id": None,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }

        self.claims.append(claim)
        self._save_claims()

        if charge_amount > 0:
            self._record_charge(patient_id, claim_id, charge_amount, procedures or [])

        return claim

    def _record_charge(
        self, patient_id: str, claim_id: str, amount: float, procedures: list[dict]
    ):
        """Record a charge for reconciliation."""
        charge = {
            "charge_id": f"CHG-{uuid.uuid4().hex[:8].upper()}",
            "patient_id": patient_id,
            "claim_id": claim_id,
            "amount": amount,
            "procedures": [
                {
                    "code": p.get("code", ""),
                    "modifier": p.get("modifier", ""),
                    "units": p.get("units", 1),
                    "charge": p.get("charge", 0),
                }
                for p in procedures
            ],
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.charges.append(charge)
        self._save_charges()

    def process_acknowledgment(
        self, claim_id: str, accepted: bool, reason: str = ""
    ) -> dict:
        """Process a 999/277CA acknowledgment from the clearinghouse."""
        for claim in self.claims:
            if claim["claim_id"] == claim_id:
                now = datetime.now(timezone.utc).isoformat()
                claim["acknowledgment"] = "accepted" if accepted else "rejected"
                if accepted:
                    claim["status"] = "accepted"
                    claim["accepted_at"] = now
                else:
                    claim["status"] = "rejected"
                    claim["rejected_at"] = now
                    claim["rejection_reason"] = reason
                claim["updated_at"] = now
                self._save_claims()
                return claim
        raise ValueError(f"Claim {claim_id} not found")

    def process_era(
        self,
        claim_id: str,
        allowed_amount: float,
        paid_amount: float,
        patient_responsibility: float,
        adjustment_codes: list[dict] | None = None,
        denial_reason: str = "",
        denial_codes: list[str] | None = None,
    ) -> dict:
        """Process an 835 ERA (Electronic Remittance Advice)."""
        for claim in self.claims:
            if claim["claim_id"] == claim_id:
                now = datetime.now(timezone.utc).isoformat()
                claim["adjudicated_at"] = now
                claim["allowed_amount"] = allowed_amount
                claim["paid_amount"] = paid_amount
                claim["patient_responsibility"] = patient_responsibility
                claim["updated_at"] = now

                if paid_amount > 0:
                    claim["status"] = "paid"
                elif denial_reason:
                    claim["status"] = "denied"
                    claim["denial_reason"] = denial_reason
                    claim["denial_codes"] = denial_codes or []
                    claim["appeal_eligible"] = True
                    claim["auto_appeal"] = self._generate_claim_appeal(claim)
                else:
                    claim["status"] = "pending_review"

                era = {
                    "era_id": f"ERA-{uuid.uuid4().hex[:8].upper()}",
                    "claim_id": claim_id,
                    "allowed_amount": allowed_amount,
                    "paid_amount": paid_amount,
                    "patient_responsibility": patient_responsibility,
                    "adjustment_codes": adjustment_codes or [],
                    "processed_at": now,
                }
                self.eras.append(era)
                claim["era_id"] = era["era_id"]
                self._save_eras()
                self._save_claims()

                self._update_charge_status(claim_id, claim["status"])
                return claim
        raise ValueError(f"Claim {claim_id} not found")

    def _generate_claim_appeal(self, claim: dict) -> dict:
        """Generate an appeal for a denied claim."""
        return {
            "appeal_letter": f"""
CLAIMS APPEAL

Date: {datetime.now(timezone.utc).strftime("%B %d, %Y")}
Claim ID: {claim["claim_id"]}
Patient: {claim["patient"]["name"]} (MRN: {claim["patient"]["mrn"]})
Provider: {claim["provider"]["name"]} (NPI: {claim["provider"]["npi"]})
Payer: {claim["payer"]["name"]}

RE: Appeal of Denied Claim {claim["claim_id"]}

Dear {claim["payer"]["name"]} Appeals Department,

I am writing to formally appeal the denial of claim {claim["claim_id"]}
for services rendered to {claim["patient"]["name"]} on {claim.get("submitted_at", "N/A")[:10]}.

Diagnoses: {", ".join(claim.get("diagnoses", []))}
Procedures: {", ".join(p.get("code", "") for p in claim.get("procedures", []))}
Billed Amount: ${claim["charge_amount"]:,.2f}

Denial Reason: {claim.get("denial_reason", "Not specified")}
Denial Codes: {", ".join(claim.get("denial_codes", []))}

This claim was submitted with all required documentation and meets all coverage criteria.
I respectfully request a review and reconsideration of this denial.

Sincerely,
{claim["provider"]["name"]}
            """,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def submit_claim_appeal(self, claim_id: str, appeal_notes: str = "") -> dict:
        """Submit an appeal for a denied claim."""
        for claim in self.claims:
            if claim["claim_id"] == claim_id and claim.get("status") == "denied":
                appeal = {
                    "appeal_id": f"APPEAL-{uuid.uuid4().hex[:6].upper()}",
                    "submitted_at": datetime.now(timezone.utc).isoformat(),
                    "status": "submitted",
                    "notes": appeal_notes,
                    "expected_decision_by": (
                        datetime.now(timezone.utc) + timedelta(days=60)
                    ).isoformat(),
                }
                claim["appeals"].append(appeal)
                claim["status"] = "appeal_submitted"
                claim["updated_at"] = datetime.now(timezone.utc).isoformat()
                self._save_claims()
                return claim
        raise ValueError(f"Claim {claim_id} not found or not eligible for appeal")

    def _update_charge_status(self, claim_id: str, status: str):
        for charge in self.charges:
            if charge["claim_id"] == claim_id:
                charge["status"] = status
                self._save_charges()

    def get_claims(
        self,
        patient_id: str | None = None,
        status: str | None = None,
        payer_name: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> list[dict]:
        claims = self.claims
        if patient_id:
            claims = [c for c in claims if c["patient"]["patient_id"] == patient_id]
        if status:
            claims = [c for c in claims if c["status"] == status]
        if payer_name:
            claims = [
                c for c in claims if c["payer"]["name"].lower() == payer_name.lower()
            ]
        if date_from:
            claims = [c for c in claims if c.get("submitted_at", "")[:10] >= date_from]
        if date_to:
            claims = [c for c in claims if c.get("submitted_at", "")[:10] <= date_to]
        return sorted(claims, key=lambda c: c.get("submitted_at", ""), reverse=True)

    def get_claim_by_id(self, claim_id: str) -> dict | None:
        for claim in self.claims:
            if claim["claim_id"] == claim_id:
                return claim
        return None

    def get_statistics(self) -> dict:
        total = len(self.claims)
        if total == 0:
            return {
                "total_claims": 0,
                "total_charges": 0,
                "total_paid": 0,
                "denial_rate": 0,
            }

        status_counts = {}
        total_charges = sum(c.get("charge_amount", 0) for c in self.claims)
        total_paid = sum(c.get("paid_amount", 0) for c in self.claims)
        total_allowed = sum(c.get("allowed_amount", 0) for c in self.claims)
        total_patient_resp = sum(
            c.get("patient_responsibility", 0) for c in self.claims
        )

        for c in self.claims:
            s = c.get("status", "unknown")
            status_counts[s] = status_counts.get(s, 0) + 1

        denied = status_counts.get("denied", 0)
        decided = status_counts.get("paid", 0) + denied

        return {
            "total_claims": total,
            "status_breakdown": status_counts,
            "total_charges": round(total_charges, 2),
            "total_allowed": round(total_allowed, 2),
            "total_paid": round(total_paid, 2),
            "total_patient_responsibility": round(total_patient_resp, 2),
            "total_pending": round(total_charges - total_paid - total_patient_resp, 2),
            "denial_rate": round(denied / decided * 100, 1) if decided > 0 else 0,
            "clean_claim_rate": round(status_counts.get("paid", 0) / total * 100, 1)
            if total > 0
            else 0,
            "avg_days_to_payment": self._calc_avg_days_to_payment(),
        }

    def _calc_avg_days_to_payment(self) -> float:
        paid_claims = [
            c
            for c in self.claims
            if c.get("status") == "paid" and c.get("adjudicated_at")
        ]
        if not paid_claims:
            return 0
        total_days = 0
        count = 0
        for c in paid_claims:
            try:
                submitted = datetime.fromisoformat(c["submitted_at"])
                adjudicated = datetime.fromisoformat(c["adjudicated_at"])
                total_days += (adjudicated - submitted).days
                count += 1
            except (ValueError, KeyError):
                pass
        return round(total_days / count, 1) if count > 0 else 0

    def get_denial_analysis(self) -> dict:
        denied_claims = [c for c in self.claims if c.get("status") == "denied"]
        denial_reasons = {}
        payer_denials = {}

        for c in denied_claims:
            reason = c.get("denial_reason", "Unknown")
            denial_reasons[reason] = denial_reasons.get(reason, 0) + 1

            payer = c["payer"]["name"]
            if payer not in payer_denials:
                payer_denials[payer] = {"total": 0, "denied": 0}
            payer_denials[payer]["denied"] += 1

        for c in self.claims:
            payer = c["payer"]["name"]
            if payer not in payer_denials:
                payer_denials[payer] = {"total": 0, "denied": 0}
            payer_denials[payer]["total"] += 1

        for payer in payer_denials:
            total = payer_denials[payer]["total"]
            denied = payer_denials[payer]["denied"]
            payer_denials[payer]["denial_rate"] = (
                round(denied / total * 100, 1) if total > 0 else 0
            )

        return {
            "total_denied": len(denied_claims),
            "denial_reasons": sorted(
                denial_reasons.items(), key=lambda x: x[1], reverse=True
            ),
            "payer_denial_rates": payer_denials,
            "appeals_submitted": len(
                [c for c in self.claims if c.get("status") == "appeal_submitted"]
            ),
        }
