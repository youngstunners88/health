"""
SDOH (Social Determinants of Health) Engine
Screening, risk stratification, automated community resource referrals,
and integration with discharge planning.
"""

import json
import uuid
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Optional


DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

SCREENINGS_FILE = DATA_DIR / "screenings.json"
REFERRALS_FILE = DATA_DIR / "referrals.json"
RESOURCES_FILE = Path(__file__).parent.parent / "resources" / "community_resources.json"


SDOH_DOMAINS = {
    "housing": {
        "label": "Housing Stability",
        "questions": [
            {
                "id": "h1",
                "text": "Do you have a stable place to live?",
                "type": "yes_no",
            },
            {
                "id": "h2",
                "text": "Are you worried about losing your housing in the next 30 days?",
                "type": "yes_no",
            },
            {
                "id": "h3",
                "text": "Do you currently live with family/friends temporarily?",
                "type": "yes_no",
            },
            {
                "id": "h4",
                "text": "Is your current housing safe and in good condition?",
                "type": "yes_no",
            },
        ],
        "risk_threshold": 2,
    },
    "food": {
        "label": "Food Security",
        "questions": [
            {
                "id": "f1",
                "text": "Within the past 12 months, did you worry that food would run out before you got money to buy more?",
                "type": "yes_no",
            },
            {
                "id": "f2",
                "text": "Within the past 12 months, did the food you bought not last and you didn't have money to get more?",
                "type": "yes_no",
            },
            {
                "id": "f3",
                "text": "In the past week, did you ever skip meals because you couldn't afford food?",
                "type": "yes_no",
            },
        ],
        "risk_threshold": 1,
    },
    "transportation": {
        "label": "Transportation Access",
        "questions": [
            {
                "id": "t1",
                "text": "Do you have reliable transportation to get to medical appointments?",
                "type": "yes_no",
            },
            {
                "id": "t2",
                "text": "Has lack of transportation ever caused you to miss a medical appointment?",
                "type": "yes_no",
            },
            {
                "id": "t3",
                "text": "Do you have a valid driver's license?",
                "type": "yes_no",
            },
        ],
        "risk_threshold": 1,
    },
    "utilities": {
        "label": "Utilities Access",
        "questions": [
            {
                "id": "u1",
                "text": "Have you had your electricity, gas, or water shut off in the past 12 months?",
                "type": "yes_no",
            },
            {
                "id": "u2",
                "text": "Are you currently behind on utility bills?",
                "type": "yes_no",
            },
            {
                "id": "u3",
                "text": "Do you have air conditioning that works during hot weather?",
                "type": "yes_no",
            },
            {
                "id": "u4",
                "text": "Do you have reliable heating during cold weather?",
                "type": "yes_no",
            },
        ],
        "risk_threshold": 2,
    },
    "safety": {
        "label": "Personal Safety",
        "questions": [
            {"id": "s1", "text": "Do you feel safe in your home?", "type": "yes_no"},
            {"id": "s2", "text": "Are you afraid of anyone at home?", "type": "yes_no"},
            {
                "id": "s3",
                "text": "Has anyone hit, kicked, or hurt you in the past year?",
                "type": "yes_no",
            },
        ],
        "risk_threshold": 1,
        "critical": True,
    },
    "social": {
        "label": "Social Support",
        "questions": [
            {
                "id": "so1",
                "text": "If you needed help with daily activities, is there someone who could help?",
                "type": "yes_no",
            },
            {"id": "so2", "text": "Do you live alone?", "type": "yes_no"},
            {
                "id": "so3",
                "text": "How often do you feel lonely or isolated?",
                "type": "scale_0_10",
            },
            {
                "id": "so4",
                "text": "Do you have someone you can talk to about personal problems?",
                "type": "yes_no",
            },
        ],
        "risk_threshold": 2,
    },
    "financial": {
        "label": "Financial Strain",
        "questions": [
            {
                "id": "fi1",
                "text": "How difficult is it to pay for basic necessities (food, housing, healthcare)?",
                "type": "scale_1_5",
            },
            {"id": "fi2", "text": "Are you currently employed?", "type": "yes_no"},
            {
                "id": "fi3",
                "text": "Have you had to choose between paying for medication and other necessities?",
                "type": "yes_no",
            },
        ],
        "risk_threshold": 2,
    },
    "health_literacy": {
        "label": "Health Literacy",
        "questions": [
            {
                "id": "hl1",
                "text": "How confident are you filling out medical forms on your own?",
                "type": "scale_1_5",
            },
            {
                "id": "hl2",
                "text": "Do you have difficulty understanding medical instructions?",
                "type": "yes_no",
            },
            {
                "id": "hl3",
                "text": "Do you need an interpreter for medical visits?",
                "type": "yes_no",
            },
        ],
        "risk_threshold": 1,
    },
}


COMMUNITY_RESOURCES = {
    "housing": [
        {
            "name": "211 Housing Assistance",
            "phone": "2-1-1",
            "description": "Connects to local housing resources, emergency shelter, rental assistance",
            "eligibility": "Income-based",
            "referral_method": "phone",
        },
        {
            "name": "HUD Housing Counseling",
            "phone": "1-800-569-4287",
            "description": "Free housing counseling services",
            "eligibility": "All",
            "referral_method": "phone",
        },
        {
            "name": "Local Emergency Shelter",
            "phone": "Contact 211",
            "description": "Emergency shelter and transitional housing",
            "eligibility": "Immediate need",
            "referral_method": "warm_handoff",
        },
    ],
    "food": [
        {
            "name": "SNAP (Food Stamps)",
            "phone": "Contact local DSS",
            "description": "Monthly food assistance benefits",
            "eligibility": "Income-based",
            "referral_method": "application_assist",
        },
        {
            "name": "Feeding America Food Banks",
            "phone": "1-800-771-2303",
            "description": "Local food banks and pantries",
            "eligibility": "All",
            "referral_method": "referral",
        },
        {
            "name": "Meals on Wheels",
            "phone": "1-888-998-6325",
            "description": "Home-delivered meals for seniors and homebound individuals",
            "eligibility": "Age 60+ or homebound",
            "referral_method": "referral",
        },
        {
            "name": "WIC Program",
            "phone": "Contact local health dept",
            "description": "Nutrition assistance for women, infants, and children",
            "eligibility": "Pregnant/postpartum women, children under 5",
            "referral_method": "referral",
        },
    ],
    "transportation": [
        {
            "name": "Non-Emergency Medical Transportation (NEMT)",
            "phone": "Contact Medicaid plan",
            "description": "Free transportation to medical appointments for Medicaid members",
            "eligibility": "Medicaid",
            "referral_method": "prior_auth",
        },
        {
            "name": "Local Transit Paratransit",
            "phone": "Contact local transit",
            "description": "Door-to-door transportation for individuals with disabilities",
            "eligibility": "Disability certification",
            "referral_method": "application_assist",
        },
        {
            "name": "Volunteer Driver Programs",
            "phone": "Contact 211",
            "description": "Volunteer drivers for medical appointments",
            "eligibility": "All",
            "referral_method": "referral",
        },
    ],
    "utilities": [
        {
            "name": "LIHEAP (Energy Assistance)",
            "phone": "1-866-674-6327",
            "description": "Help with heating and cooling costs",
            "eligibility": "Income-based",
            "referral_method": "application_assist",
        },
        {
            "name": "Utility Company Assistance Programs",
            "phone": "Contact utility provider",
            "description": "Payment plans and emergency assistance",
            "eligibility": "Varies by provider",
            "referral_method": "referral",
        },
    ],
    "safety": [
        {
            "name": "National Domestic Violence Hotline",
            "phone": "1-800-799-7233",
            "description": "24/7 crisis support, safety planning, shelter referrals",
            "eligibility": "All",
            "referral_method": "warm_handoff",
            "confidential": True,
        },
        {
            "name": "National Elder Abuse Hotline",
            "phone": "1-800-677-1116",
            "description": "Elder abuse reporting and support",
            "eligibility": "Age 60+",
            "referral_method": "warm_handoff",
            "confidential": True,
        },
        {
            "name": "Adult Protective Services",
            "phone": "Contact local APS",
            "description": "Investigation and intervention for vulnerable adults",
            "eligibility": "Vulnerable adults",
            "referral_method": "mandatory_report",
        },
    ],
    "social": [
        {
            "name": "Area Agency on Aging",
            "phone": "1-800-677-1116",
            "description": "Senior services, social activities, caregiver support",
            "eligibility": "Age 60+",
            "referral_method": "referral",
        },
        {
            "name": "NAMI Support Groups",
            "phone": "1-800-950-6264",
            "description": "Mental health support groups and education",
            "eligibility": "All",
            "referral_method": "referral",
        },
        {
            "name": "Local Senior Centers",
            "phone": "Contact 211",
            "description": "Social activities, meals, health programs",
            "eligibility": "Age 60+",
            "referral_method": "referral",
        },
    ],
    "financial": [
        {
            "name": "Medicaid/CHIP Enrollment",
            "phone": "1-800-318-2596",
            "description": "Health insurance for low-income individuals and families",
            "eligibility": "Income-based",
            "referral_method": "application_assist",
        },
        {
            "name": "Prescription Assistance Programs",
            "phone": "Contact pharmacy",
            "description": "Discount programs and manufacturer assistance for medications",
            "eligibility": "Income-based",
            "referral_method": "referral",
        },
        {
            "name": "Financial Counseling",
            "phone": "Contact hospital social work",
            "description": "Free financial counseling and bill assistance",
            "eligibility": "All",
            "referral_method": "referral",
        },
    ],
    "health_literacy": [
        {
            "name": "Medical Interpreter Services",
            "phone": "Contact hospital",
            "description": "Free interpreter services for medical appointments",
            "eligibility": "All",
            "referral_method": "referral",
        },
        {
            "name": "Health Literacy Programs",
            "phone": "Contact local library",
            "description": "Free health literacy education",
            "eligibility": "All",
            "referral_method": "referral",
        },
    ],
}


class SDOHEngine:
    """Manages SDOH screening, scoring, and referrals."""

    def __init__(self):
        self.screenings = self._load_screenings()
        self.referrals = self._load_referrals()

    def _load_screenings(self) -> list[dict]:
        if SCREENINGS_FILE.exists():
            try:
                return json.loads(SCREENINGS_FILE.read_text())
            except json.JSONDecodeError:
                pass
        return []

    def _save_screenings(self):
        SCREENINGS_FILE.write_text(
            json.dumps(self.screenings[-500:], indent=2, default=str)
        )

    def _load_referrals(self) -> list[dict]:
        if REFERRALS_FILE.exists():
            try:
                return json.loads(REFERRALS_FILE.read_text())
            except json.JSONDecodeError:
                pass
        return []

    def _save_referrals(self):
        REFERRALS_FILE.write_text(
            json.dumps(self.referrals[-500:], indent=2, default=str)
        )

    def create_screening(
        self,
        patient_id: str,
        patient_name: str,
        responses: dict,
        screened_by: str = "self",
        screening_context: str = "discharge",
    ) -> dict:
        """Create an SDOH screening with responses."""
        screening_id = f"SDOH-{uuid.uuid4().hex[:8].upper()}"
        now = datetime.now(timezone.utc)

        scores = self._score_screening(responses)
        risk_level = self._determine_risk_level(scores)
        auto_referrals = self._generate_referrals(patient_id, patient_name, scores)

        screening = {
            "screening_id": screening_id,
            "patient_id": patient_id,
            "patient_name": patient_name,
            "screened_by": screened_by,
            "screening_context": screening_context,
            "responses": responses,
            "domain_scores": scores,
            "overall_risk_level": risk_level,
            "positive_domains": [
                d for d, s in scores.items() if s["positive_count"] > 0
            ],
            "critical_flags": [d for d, s in scores.items() if s.get("critical")],
            "auto_referrals": auto_referrals,
            "completed_at": now.isoformat(),
            "created_at": now.isoformat(),
        }

        self.screenings.append(screening)
        self._save_screenings()

        for ref in auto_referrals:
            self.referrals.append(ref)
        self._save_referrals()

        return screening

    def _score_screening(self, responses: dict) -> dict:
        """Score each SDOH domain based on responses."""
        scores = {}

        for domain_key, domain in SDOH_DOMAINS.items():
            positive_count = 0
            domain_responses = []

            for q in domain["questions"]:
                response = responses.get(q["id"])
                if response is None:
                    continue

                is_positive = False
                if q["type"] == "yes_no":
                    if q["id"] in ("h1", "t1", "so1", "so4"):
                        is_positive = response == "no"
                    elif q["id"] in ("hl1",):
                        is_positive = response in ("not_at_all", "a_little")
                    else:
                        is_positive = response == "yes"
                elif q["type"] == "scale_0_10":
                    is_positive = response >= 7
                elif q["type"] == "scale_1_5":
                    if q["id"] == "fi1":
                        is_positive = response >= 4
                    elif q["id"] == "hl1":
                        is_positive = response <= 2
                    else:
                        is_positive = response >= 4

                if is_positive:
                    positive_count += 1

                domain_responses.append(
                    {
                        "question_id": q["id"],
                        "question_text": q["text"],
                        "response": response,
                        "positive": is_positive,
                    }
                )

            scores[domain_key] = {
                "domain": domain["label"],
                "positive_count": positive_count,
                "total_questions": len(domain["questions"]),
                "risk_threshold": domain["risk_threshold"],
                "at_risk": positive_count >= domain["risk_threshold"],
                "critical": domain.get("critical", False) and positive_count > 0,
                "responses": domain_responses,
            }

        return scores

    def _determine_risk_level(self, scores: dict) -> str:
        """Determine overall SDOH risk level."""
        critical_count = sum(1 for s in scores.values() if s.get("critical"))
        at_risk_count = sum(1 for s in scores.values() if s["at_risk"])

        if critical_count > 0:
            return "critical"
        elif at_risk_count >= 3:
            return "high"
        elif at_risk_count >= 1:
            return "moderate"
        return "low"

    def _generate_referrals(
        self, patient_id: str, patient_name: str, scores: dict
    ) -> list[dict]:
        """Auto-generate referrals for at-risk domains."""
        referrals = []

        for domain_key, score in scores.items():
            if not score["at_risk"]:
                continue

            resources = COMMUNITY_RESOURCES.get(domain_key, [])
            for resource in resources:
                referral = {
                    "referral_id": f"REF-{uuid.uuid4().hex[:8].upper()}",
                    "screening_id": None,
                    "patient_id": patient_id,
                    "patient_name": patient_name,
                    "domain": domain_key,
                    "resource_name": resource["name"],
                    "resource_phone": resource["phone"],
                    "resource_description": resource["description"],
                    "eligibility": resource["eligibility"],
                    "referral_method": resource["referral_method"],
                    "confidential": resource.get("confidential", False),
                    "status": "pending",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "completed_at": None,
                    "follow_up_date": (
                        datetime.now(timezone.utc) + timedelta(days=14)
                    ).isoformat(),
                    "outcome": None,
                }
                referrals.append(referral)

        return referrals

    def update_referral_status(
        self, referral_id: str, status: str, outcome: str = ""
    ) -> dict:
        """Update the status of a referral."""
        for ref in self.referrals:
            if ref["referral_id"] == referral_id:
                ref["status"] = status
                ref["outcome"] = outcome
                if status in ("completed", "closed"):
                    ref["completed_at"] = datetime.now(timezone.utc).isoformat()
                self._save_referrals()
                return ref
        raise ValueError(f"Referral {referral_id} not found")

    def get_screenings(self, patient_id: str | None = None) -> list[dict]:
        screenings = self.screenings
        if patient_id:
            screenings = [s for s in screenings if s["patient_id"] == patient_id]
        return sorted(screenings, key=lambda s: s.get("completed_at", ""), reverse=True)

    def get_referrals(
        self,
        patient_id: str | None = None,
        status: str | None = None,
        domain: str | None = None,
    ) -> list[dict]:
        referrals = self.referrals
        if patient_id:
            referrals = [r for r in referrals if r["patient_id"] == patient_id]
        if status:
            referrals = [r for r in referrals if r["status"] == status]
        if domain:
            referrals = [r for r in referrals if r["domain"] == domain]
        return sorted(referrals, key=lambda r: r.get("created_at", ""), reverse=True)

    def get_statistics(self) -> dict:
        total_screenings = len(self.screenings)
        total_referrals = len(self.referrals)

        risk_distribution = {"low": 0, "moderate": 0, "high": 0, "critical": 0}
        for s in self.screenings:
            risk = s.get("overall_risk_level", "low")
            risk_distribution[risk] = risk_distribution.get(risk, 0) + 1

        referral_status = {}
        for r in self.referrals:
            status = r.get("status", "unknown")
            referral_status[status] = referral_status.get(status, 0) + 1

        domain_counts = {}
        for r in self.referrals:
            domain = r.get("domain", "unknown")
            domain_counts[domain] = domain_counts.get(domain, 0) + 1

        return {
            "total_screenings": total_screenings,
            "total_referrals": total_referrals,
            "risk_distribution": risk_distribution,
            "referral_status": referral_status,
            "top_domains": sorted(
                domain_counts.items(), key=lambda x: x[1], reverse=True
            )[:5],
            "completion_rate": round(
                referral_status.get("completed", 0) / total_referrals * 100, 1
            )
            if total_referrals > 0
            else 0,
        }

    def get_screening_questions(self) -> dict:
        """Return all SDOH screening questions organized by domain."""
        return {
            key: {
                "label": domain["label"],
                "questions": domain["questions"],
            }
            for key, domain in SDOH_DOMAINS.items()
        }
