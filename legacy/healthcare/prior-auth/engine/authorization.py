"""
Prior Authorization Engine
Automates prior auth requests with clinical justification, payer rules checking,
document assembly, denial management, and appeal generation.
"""

import json
import uuid
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Optional


DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

RULES_FILE = DATA_DIR / "payer_rules.json"
AUTHS_FILE = DATA_DIR / "authorizations.json"


class PayerRulesDB:
    """Database of payer-specific prior authorization rules."""

    def __init__(self):
        self.rules = self._load_rules()

    def _load_rules(self) -> dict:
        if RULES_FILE.exists():
            try:
                return json.loads(RULES_FILE.read_text())
            except json.JSONDecodeError:
                pass
        return self._default_rules()

    def save_rules(self):
        RULES_FILE.write_text(json.dumps(self.rules, indent=2, default=str))

    def _default_rules(self) -> dict:
        return {
            "BlueCross BlueShield": {
                "payer_id": "BCBS",
                "requires_prior_auth": [
                    "MRI",
                    "CT Scan",
                    "PET Scan",
                    "Echocardiogram",
                    "Cardiac Catheterization",
                    "Sleep Study",
                    "Physical Therapy",
                    "Home Health",
                    "Durable Medical Equipment",
                    "Specialty Drugs",
                ],
                "auth_methods": ["portal", "fax", "phone"],
                "portal_url": "https://provider.bcbs.com/auth",
                "fax_number": "1-800-555-0100",
                "phone_number": "1-800-555-0200",
                "turnaround_hours": 72,
                "expedited_hours": 24,
                "requires_clinical_notes": True,
                "requires_peer_review": False,
                "requires_fail_first": True,
                "fail_first_duration_days": 30,
            },
            "Aetna": {
                "payer_id": "AETNA",
                "requires_prior_auth": [
                    "MRI",
                    "CT Scan",
                    "PET Scan",
                    "Advanced Imaging",
                    "Inpatient Admission",
                    "Skilled Nursing",
                    "Home Infusion",
                    "Specialty Drugs",
                    "Genetic Testing",
                ],
                "auth_methods": ["portal", "phone"],
                "portal_url": "https://provider.aetna.com/auth",
                "phone_number": "1-800-555-0300",
                "turnaround_hours": 48,
                "expedited_hours": 12,
                "requires_clinical_notes": True,
                "requires_peer_review": True,
                "requires_fail_first": False,
            },
            "UnitedHealthcare": {
                "payer_id": "UHC",
                "requires_prior_auth": [
                    "MRI",
                    "CT Scan",
                    "PET Scan",
                    "Cardiac Procedures",
                    "Bariatric Surgery",
                    "Spine Surgery",
                    "Specialty Drugs",
                    "Durable Medical Equipment",
                    "Home Health",
                    "Physical Therapy",
                ],
                "auth_methods": ["portal", "fax"],
                "portal_url": "https://provider.uhc.com/auth",
                "fax_number": "1-800-555-0400",
                "turnaround_hours": 96,
                "expedited_hours": 48,
                "requires_clinical_notes": True,
                "requires_peer_review": True,
                "requires_fail_first": True,
                "fail_first_duration_days": 60,
            },
            "Medicare": {
                "payer_id": "MEDICARE",
                "requires_prior_auth": [
                    "Durable Medical Equipment",
                    "Home Health",
                    "Skilled Nursing Facility",
                    "Inpatient Rehabilitation",
                    "Hyperbaric Oxygen",
                    "Chiropractic",
                ],
                "auth_methods": ["portal", "fax", "phone"],
                "portal_url": "https://www.medicare.gov/prior-auth",
                "fax_number": "1-800-555-0500",
                "turnaround_hours": 120,
                "expedited_hours": 48,
                "requires_clinical_notes": True,
                "requires_peer_review": False,
                "requires_fail_first": False,
            },
            "Medicaid": {
                "payer_id": "MEDICAID",
                "requires_prior_auth": [
                    "MRI",
                    "CT Scan",
                    "Specialty Drugs",
                    "Durable Medical Equipment",
                    "Home Health",
                    "Non-Emergency Transport",
                    "Behavioral Health",
                ],
                "auth_methods": ["portal", "fax"],
                "portal_url": "https://medicaid.gov/prior-auth",
                "fax_number": "1-800-555-0600",
                "turnaround_hours": 168,
                "expedited_hours": 72,
                "requires_clinical_notes": True,
                "requires_peer_review": False,
                "requires_fail_first": True,
                "fail_first_duration_days": 30,
            },
        }

    def get_payer_rules(self, payer_name: str) -> dict | None:
        for name, rules in self.rules.items():
            if name.lower() == payer_name.lower():
                return rules
        return None

    def needs_prior_auth(self, payer_name: str, procedure: str) -> bool:
        rules = self.get_payer_rules(payer_name)
        if not rules:
            return True
        return procedure in rules.get("requires_prior_auth", [])

    def get_all_payers(self) -> list[dict]:
        return [{"name": name, **rules} for name, rules in self.rules.items()]


class PriorAuthEngine:
    """Manages prior authorization lifecycle."""

    def __init__(self):
        self.payer_rules = PayerRulesDB()
        self.authorizations = self._load_auths()

    def _load_auths(self) -> list[dict]:
        if AUTHS_FILE.exists():
            try:
                return json.loads(AUTHS_FILE.read_text())
            except json.JSONDecodeError:
                pass
        return []

    def _save_auths(self):
        AUTHS_FILE.write_text(
            json.dumps(self.authorizations[-500:], indent=2, default=str)
        )

    def create_auth_request(
        self,
        patient_id: str,
        patient_name: str,
        payer_name: str,
        procedure: str,
        diagnosis_codes: list[str],
        provider_name: str,
        provider_npi: str,
        clinical_notes: str = "",
        urgency: str = "standard",
        requested_start_date: str = "",
    ) -> dict:
        """Create a new prior authorization request."""
        rules = self.payer_rules.get_payer_rules(payer_name)
        needs_auth = self.payer_rules.needs_prior_auth(payer_name, procedure)

        auth_id = f"PA-{uuid.uuid4().hex[:8].upper()}"
        now = datetime.now(timezone.utc)

        turnaround = rules.get("turnaround_hours", 72) if rules else 72
        if urgency == "expedited":
            turnaround = rules.get("expedited_hours", 24) if rules else 24

        expected_decision = now + timedelta(hours=turnaround)

        clinical_justification = self._generate_justification(
            procedure, diagnosis_codes, clinical_notes, rules
        )

        auth = {
            "auth_id": auth_id,
            "patient_id": patient_id,
            "patient_name": patient_name,
            "payer_name": payer_name,
            "payer_id": rules.get("payer_id", "UNKNOWN") if rules else "UNKNOWN",
            "procedure": procedure,
            "diagnosis_codes": diagnosis_codes,
            "provider_name": provider_name,
            "provider_npi": provider_npi,
            "clinical_notes": clinical_notes,
            "clinical_justification": clinical_justification,
            "urgency": urgency,
            "requested_start_date": requested_start_date
            or (now + timedelta(days=7)).date().isoformat(),
            "status": "submitted" if needs_auth else "not_required",
            "needs_prior_auth": needs_auth,
            "submission_method": rules.get("auth_methods", ["portal"])[0]
            if rules
            else "portal",
            "submitted_at": now.isoformat(),
            "expected_decision_by": expected_decision.isoformat(),
            "decision_at": None,
            "decision": None,
            "decision_reason": None,
            "auth_number": None,
            "denial_reason": None,
            "appeals": [],
            "documents": self._assemble_documents(
                auth_id, procedure, diagnosis_codes, clinical_justification
            ),
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }

        self.authorizations.append(auth)
        self._save_auths()
        return auth

    def _generate_justification(
        self,
        procedure: str,
        diagnosis_codes: list[str],
        clinical_notes: str,
        rules: dict | None,
    ) -> dict:
        """Generate clinical justification for the prior auth request."""
        justification = {
            "medical_necessity": self._determine_medical_necessity(
                procedure, diagnosis_codes
            ),
            "diagnosis_support": self._map_diagnoses_to_procedure(
                procedure, diagnosis_codes
            ),
            "conservative_treatment_history": self._suggest_conservative_treatments(
                procedure, rules
            ),
            "clinical_notes": clinical_notes,
            "evidence_based_guidelines": self._reference_guidelines(procedure),
        }
        return justification

    def _determine_medical_necessity(self, procedure: str, diagnoses: list[str]) -> str:
        """Determine medical necessity statement."""
        necessity_map = {
            "MRI": "Advanced imaging is medically necessary to evaluate the extent of pathology and guide treatment planning for the diagnosed condition.",
            "CT Scan": "CT imaging is medically necessary for detailed anatomical evaluation and treatment planning.",
            "PET Scan": "PET imaging is medically necessary for staging, restaging, or treatment response assessment of the diagnosed condition.",
            "Echocardiogram": "Echocardiography is medically necessary to assess cardiac structure and function in the setting of the diagnosed cardiac condition.",
            "Cardiac Catheterization": "Cardiac catheterization is medically necessary for definitive diagnosis and potential intervention for suspected coronary artery disease.",
            "Home Health": "Home health services are medically necessary to provide skilled nursing and therapy in the home setting for a homebound patient.",
            "Physical Therapy": "Physical therapy is medically necessary to restore functional mobility and independence following the diagnosed condition or procedure.",
            "Durable Medical Equipment": "DME is medically necessary to support activities of daily living and maintain safety in the home setting.",
            "Specialty Drugs": "Specialty medication is medically necessary as first-line or alternative therapy for the diagnosed condition per clinical guidelines.",
        }
        return necessity_map.get(
            procedure,
            f"The requested procedure/service is medically necessary for the evaluation and treatment of the patient's diagnosed condition(s): {', '.join(diagnoses)}.",
        )

    def _map_diagnoses_to_procedure(
        self, procedure: str, diagnoses: list[str]
    ) -> list[dict]:
        """Map diagnosis codes to the requested procedure."""
        return [
            {
                "code": code,
                "procedure": procedure,
                "relevance": "primary" if i == 0 else "secondary",
            }
            for i, code in enumerate(diagnoses)
        ]

    def _suggest_conservative_treatments(
        self, procedure: str, rules: dict | None
    ) -> list[str]:
        """Suggest conservative treatments tried before the requested procedure."""
        treatments_map = {
            "MRI": [
                "Physical therapy (6+ weeks)",
                "NSAIDs trial",
                "Rest and activity modification",
            ],
            "CT Scan": [
                "Basic imaging (X-ray)",
                "Clinical evaluation",
                "Laboratory studies",
            ],
            "Echocardiogram": ["ECG", "Stress test", "Cardiac biomarkers"],
            "Physical Therapy": [
                "Home exercise program",
                "Activity modification",
                "OTC analgesics",
            ],
            "Home Health": [
                "Outpatient therapy",
                "Family caregiver support",
                "Telehealth monitoring",
            ],
            "Durable Medical Equipment": [
                "Assistive device trial",
                "Home safety assessment",
                "Caregiver training",
            ],
        }
        return treatments_map.get(
            procedure, ["Clinical evaluation", "Conservative management trial"]
        )

    def _reference_guidelines(self, procedure: str) -> list[str]:
        """Reference evidence-based guidelines supporting the procedure."""
        guidelines_map = {
            "MRI": [
                "ACR Appropriateness Criteria",
                "Milliman Care Guidelines (MCG)",
                "InterQual Criteria",
            ],
            "CT Scan": [
                "ACR Appropriateness Criteria",
                "American College of Radiology Guidelines",
            ],
            "Echocardiogram": [
                "ACC/AHA Guidelines for Echocardiography",
                "ASE Guidelines",
            ],
            "Cardiac Catheterization": [
                "ACC/AHA Guidelines for Coronary Angiography",
                "SCAI Appropriate Use Criteria",
            ],
            "Home Health": [
                "CMS Home Health Coverage Guidelines",
                "Medicare Benefit Policy Manual Chapter 7",
            ],
            "Physical Therapy": [
                "APTA Clinical Practice Guidelines",
                "MCG Rehabilitation Guidelines",
            ],
        }
        return guidelines_map.get(
            procedure, ["Clinical practice guidelines for the indicated condition"]
        )

    def _assemble_documents(
        self, auth_id: str, procedure: str, diagnoses: list[str], justification: dict
    ) -> list[dict]:
        """Assemble required documents for submission."""
        return [
            {
                "document_type": "prior_auth_request_form",
                "description": f"Prior Authorization Request for {procedure}",
                "status": "generated",
                "content": {
                    "auth_id": auth_id,
                    "procedure": procedure,
                    "diagnoses": diagnoses,
                    "justification": justification,
                },
            },
            {
                "document_type": "clinical_summary",
                "description": "Clinical Summary and Medical History",
                "status": "template",
            },
            {
                "document_type": "provider_attestation",
                "description": "Provider Attestation of Medical Necessity",
                "status": "template",
            },
        ]

    def process_decision(
        self,
        auth_id: str,
        decision: str,
        decision_reason: str = "",
        auth_number: str = "",
        denial_reason: str = "",
    ) -> dict:
        """Process a payer decision on a prior auth request."""
        for auth in self.authorizations:
            if auth["auth_id"] == auth_id:
                now = datetime.now(timezone.utc).isoformat()
                auth["decision"] = decision
                auth["decision_reason"] = decision_reason
                auth["decision_at"] = now
                auth["updated_at"] = now

                if decision == "approved":
                    auth["status"] = "approved"
                    auth["auth_number"] = (
                        auth_number or f"AUTH-{uuid.uuid4().hex[:6].upper()}"
                    )
                elif decision == "denied":
                    auth["status"] = "denied"
                    auth["denial_reason"] = denial_reason
                    auth["appeal_eligible"] = True
                    auth["appeal_deadline"] = (
                        datetime.now(timezone.utc) + timedelta(days=180)
                    ).isoformat()
                    auth["auto_appeal_generated"] = self._generate_appeal(auth)

                self._save_auths()
                return auth

        raise ValueError(f"Authorization {auth_id} not found")

    def _generate_appeal(self, auth: dict) -> dict:
        """Generate an appeal letter for a denied prior auth request."""
        return {
            "appeal_letter": f"""
PRIOR AUTHORIZATION APPEAL

Date: {datetime.now(timezone.utc).strftime("%B %d, %Y")}
Auth ID: {auth["auth_id"]}
Patient: {auth["patient_name"]} (ID: {auth["patient_id"]})
Provider: {auth["provider_name"]} (NPI: {auth["provider_npi"]})
Payer: {auth["payer_name"]}

RE: Appeal of Denial for {auth["procedure"]}

Dear {auth["payer_name"]} Appeals Department,

I am writing to formally appeal the denial of prior authorization for {auth["procedure"]}
for patient {auth["patient_name"]}.

Medical Necessity:
{auth["clinical_justification"].get("medical_necessity", "N/A")}

Supporting Diagnoses:
{", ".join(auth["diagnosis_codes"])}

Clinical Guidelines Supporting This Request:
{chr(10).join("- " + g for g in auth["clinical_justification"].get("evidence_based_guidelines", []))}

Conservative Treatments Attempted:
{chr(10).join("- " + t for t in auth["clinical_justification"].get("conservative_treatment_history", []))}

Denial Reason Provided: {auth.get("denial_reason", "Not specified")}

This service is medically necessary and meets all coverage criteria. I respectfully request
a peer-to-peer review and reconsideration of this denial.

Sincerely,
{auth["provider_name"]}
            """,
            "peer_review_requested": True,
            "external_review_eligible": True,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def submit_appeal(self, auth_id: str, appeal_notes: str = "") -> dict:
        """Submit an appeal for a denied authorization."""
        for auth in self.authorizations:
            if auth["auth_id"] == auth_id and auth.get("status") == "denied":
                appeal = {
                    "appeal_number": f"APPEAL-{uuid.uuid4().hex[:6].upper()}",
                    "submitted_at": datetime.now(timezone.utc).isoformat(),
                    "status": "submitted",
                    "notes": appeal_notes,
                    "expected_decision_by": (
                        datetime.now(timezone.utc) + timedelta(days=30)
                    ).isoformat(),
                }
                auth["appeals"].append(appeal)
                auth["status"] = "appeal_submitted"
                auth["updated_at"] = datetime.now(timezone.utc).isoformat()
                self._save_auths()
                return auth
        raise ValueError(
            f"Authorization {auth_id} not found or not eligible for appeal"
        )

    def get_authorizations(
        self,
        patient_id: str | None = None,
        status: str | None = None,
        payer_name: str | None = None,
    ) -> list[dict]:
        """Get authorizations with optional filtering."""
        auths = self.authorizations
        if patient_id:
            auths = [a for a in auths if a["patient_id"] == patient_id]
        if status:
            auths = [a for a in auths if a["status"] == status]
        if payer_name:
            auths = [a for a in auths if a["payer_name"].lower() == payer_name.lower()]
        return sorted(auths, key=lambda a: a.get("created_at", ""), reverse=True)

    def get_auth_by_id(self, auth_id: str) -> dict | None:
        for auth in self.authorizations:
            if auth["auth_id"] == auth_id:
                return auth
        return None

    def get_pending_auths(self) -> list[dict]:
        """Get all pending/expiring authorizations."""
        now = datetime.now(timezone.utc)
        pending = []
        for auth in self.authorizations:
            if auth["status"] in ("submitted", "pending_review"):
                try:
                    deadline = datetime.fromisoformat(auth["expected_decision_by"])
                    hours_remaining = (deadline - now).total_seconds() / 3600
                    auth["hours_until_deadline"] = round(hours_remaining, 1)
                    auth["is_expiring_soon"] = hours_remaining < 24
                    pending.append(auth)
                except (ValueError, KeyError):
                    pending.append(auth)
        return sorted(pending, key=lambda a: a.get("hours_until_deadline", 999))

    def get_statistics(self) -> dict:
        """Get prior auth statistics."""
        total = len(self.authorizations)
        if total == 0:
            return {"total": 0, "approval_rate": 0, "denial_rate": 0, "pending": 0}

        approved = len([a for a in self.authorizations if a["status"] == "approved"])
        denied = len([a for a in self.authorizations if a["status"] == "denied"])
        pending = len(
            [
                a
                for a in self.authorizations
                if a["status"] in ("submitted", "pending_review")
            ]
        )

        return {
            "total": total,
            "approved": approved,
            "denied": denied,
            "pending": pending,
            "approval_rate": round(approved / (approved + denied) * 100, 1)
            if (approved + denied) > 0
            else 0,
            "denial_rate": round(denied / (approved + denied) * 100, 1)
            if (approved + denied) > 0
            else 0,
            "not_required": len(
                [a for a in self.authorizations if a["status"] == "not_required"]
            ),
            "in_appeal": len(
                [a for a in self.authorizations if a["status"] == "appeal_submitted"]
            ),
        }
