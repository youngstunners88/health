"""
Discharge plan generation.
Creates patient-specific discharge plans based on clinical and social factors.
"""

from datetime import datetime, timedelta, timezone


CONDITION_FOLLOWUP = {
    "chf": {"specialist": "Cardiology", "days": 7, "priority": "high"},
    "copd": {"specialist": "Pulmonology", "days": 7, "priority": "high"},
    "diabetes": {"specialist": "Endocrinology", "days": 14, "priority": "moderate"},
    "pneumonia": {"specialist": "PCP", "days": 7, "priority": "moderate"},
    "uti": {"specialist": "PCP", "days": 10, "priority": "low"},
    "hip replacement": {"specialist": "Orthopedics", "days": 14, "priority": "high"},
}

WARNING_SIGNS = {
    "chf": [
        "Sudden weight gain (more than 2-3 lbs in a day or 5 lbs in a week)",
        "Increased shortness of breath, especially when lying flat",
        "Swelling in legs, ankles, or abdomen",
        "Persistent cough or wheezing",
        "Feeling dizzy or faint",
    ],
    "copd": [
        "Increased difficulty breathing",
        "Change in mucus color or amount",
        "Fever above 101F",
        "Chest pain",
        "Confusion or drowsiness",
    ],
    "diabetes": [
        "Blood sugar consistently above 250 or below 70",
        "Signs of infection (fever, redness, swelling)",
        "Numbness or tingling in feet",
        "Excessive thirst or urination",
        "Blurred vision",
    ],
}

GENERIC_WARNING_SIGNS = [
    "Fever above 101F (38.3C)",
    "Chest pain or pressure",
    "Difficulty breathing",
    "Severe pain not relieved by medication",
    "Confusion or sudden change in mental state",
    "Uncontrolled bleeding",
    "Signs of infection at incision sites (redness, swelling, drainage)",
]


class DischargePlanner:
    """Generates comprehensive discharge plans."""

    def generate_plan(
        self,
        patient_id: str,
        risk_level: str = "moderate",
        conditions: list[str] | None = None,
        medications: list[dict] | None = None,
        vitals: dict | None = None,
        social_factors: dict | None = None,
    ) -> dict:
        conditions = conditions or []
        medications = medications or []
        vitals = vitals or {}
        social_factors = social_factors or {}

        followups = self._schedule_followups(conditions)
        warnings = self._compile_warnings(conditions)
        home_care = self._generate_home_care(conditions, vitals)
        social_referrals = self._identify_social_needs(social_factors)
        med_schedule = self._create_medication_schedule(medications)

        return {
            "patient_id": patient_id,
            "risk_level": risk_level,
            "follow_up_appointments": followups,
            "warning_signs": warnings,
            "home_care_instructions": home_care,
            "medication_schedule": med_schedule,
            "social_services_referrals": social_referrals,
            "emergency_instructions": "Call 911 for life-threatening emergencies. Call your care team at 1-800-XXX-XXXX for urgent concerns.",
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def _schedule_followups(self, conditions: list[str]) -> list[dict]:
        followups = []
        seen_specialists = set()
        base_date = datetime.now(timezone.utc)

        for condition in conditions:
            key = condition.lower()
            if key in CONDITION_FOLLOWUP:
                info = CONDITION_FOLLOWUP[key]
                if info["specialist"] not in seen_specialists:
                    followups.append(
                        {
                            "specialist": info["specialist"],
                            "condition": condition,
                            "days_from_discharge": info["days"],
                            "priority": info["priority"],
                            "scheduled_date": (
                                base_date + timedelta(days=info["days"])
                            ).isoformat(),
                        }
                    )
                    seen_specialists.add(info["specialist"])

        if "PCP" not in seen_specialists:
            followups.append(
                {
                    "specialist": "PCP",
                    "condition": "General follow-up",
                    "days_from_discharge": 7,
                    "priority": "high",
                    "scheduled_date": (base_date + timedelta(days=7)).isoformat(),
                }
            )

        return sorted(followups, key=lambda x: x["days_from_discharge"])

    def _compile_warnings(self, conditions: list[str]) -> list[str]:
        warnings = list(GENERIC_WARNING_SIGNS)
        for condition in conditions:
            key = condition.lower()
            if key in WARNING_SIGNS:
                warnings.extend(WARNING_SIGNS[key])
        return list(dict.fromkeys(warnings))

    def _generate_home_care(self, conditions: list[str], vitals: dict) -> list[str]:
        instructions = [
            "Take all medications as prescribed",
            "Keep all follow-up appointments",
            "Get adequate rest and gradually increase activity",
        ]

        if any(c.lower() == "chf" for c in conditions):
            instructions.extend(
                [
                    "Weigh yourself daily at the same time each morning",
                    "Follow a low-sodium diet (less than 2g per day)",
                    "Limit fluid intake to 2 liters per day unless otherwise directed",
                ]
            )

        if any(c.lower() == "diabetes" for c in conditions):
            instructions.extend(
                [
                    "Monitor blood sugar as directed",
                    "Follow your diabetic meal plan",
                    "Check feet daily for cuts, blisters, or sores",
                ]
            )

        if vitals.get("bp"):
            instructions.append(f"Monitor blood pressure (current: {vitals['bp']})")
        if vitals.get("weight"):
            instructions.append(f"Track weight (current: {vitals['weight']})")

        return instructions

    def _identify_social_needs(self, social_factors: dict) -> list[dict]:
        referrals = []
        if social_factors.get("living_alone"):
            referrals.append(
                {
                    "service": "Home health aide",
                    "reason": "Patient lives alone and may need assistance",
                    "urgency": "moderate",
                }
            )
        if not social_factors.get("transportation"):
            referrals.append(
                {
                    "service": "Medical transportation",
                    "reason": "Patient lacks transportation to follow-up appointments",
                    "urgency": "high",
                }
            )
        if social_factors.get("food_insecurity"):
            referrals.append(
                {
                    "service": "Meals on delivery / food assistance",
                    "reason": "Patient may have difficulty obtaining nutritious meals",
                    "urgency": "moderate",
                }
            )
        if social_factors.get("financial_hardship"):
            referrals.append(
                {
                    "service": "Social work / financial counseling",
                    "reason": "Patient may need assistance with medication costs",
                    "urgency": "moderate",
                }
            )
        return referrals

    def _create_medication_schedule(self, medications: list[dict]) -> list[dict]:
        schedule = []
        for med in medications:
            freq = med.get("frequency", "daily").lower()
            times = []
            if freq in ("daily", "once daily"):
                times = ["08:00"]
            elif freq in ("twice daily", "two times daily"):
                times = ["08:00", "20:00"]
            elif freq in ("three times daily", "three times a day"):
                times = ["08:00", "14:00", "20:00"]
            elif freq in ("four times daily", "every 6 hours"):
                times = ["06:00", "12:00", "18:00", "00:00"]
            elif freq in ("every 8 hours", "three times daily"):
                times = ["06:00", "14:00", "22:00"]
            elif freq in ("every 12 hours"):
                times = ["08:00", "20:00"]
            else:
                times = ["08:00"]

            schedule.append(
                {
                    "medication": med["name"],
                    "dose": med.get("dose", ""),
                    "times": times,
                    "instructions": med.get("instructions", "Take with water"),
                }
            )
        return schedule
