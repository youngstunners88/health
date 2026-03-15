"""
Medication reconciliation and interaction checking.
Compares home vs hospital medications, checks for interactions and allergy conflicts.
"""

from datetime import datetime, timezone


# Simplified drug interaction database
DRUG_INTERACTIONS = {
    ("lisinopril", "potassium"): {
        "severity": "moderate",
        "description": "Increased risk of hyperkalemia",
    },
    ("lisinopril", "spironolactone"): {
        "severity": "moderate",
        "description": "Increased risk of hyperkalemia",
    },
    ("warfarin", "aspirin"): {
        "severity": "high",
        "description": "Increased bleeding risk",
    },
    ("warfarin", "ibuprofen"): {
        "severity": "high",
        "description": "Increased bleeding risk",
    },
    ("metformin", "contrast_dye"): {
        "severity": "high",
        "description": "Risk of lactic acidosis",
    },
    ("furosemide", "lisinopril"): {
        "severity": "moderate",
        "description": "Increased risk of hypotension and renal impairment",
    },
    ("furosemide", "digoxin"): {
        "severity": "high",
        "description": "Hypokalemia increases digoxin toxicity risk",
    },
    ("simvastatin", "amiodarone"): {
        "severity": "high",
        "description": "Increased risk of rhabdomyolysis",
    },
    ("metoprolol", "verapamil"): {
        "severity": "high",
        "description": "Risk of severe bradycardia and heart block",
    },
    ("ciprofloxacin", "warfarin"): {
        "severity": "moderate",
        "description": "Increased anticoagulant effect",
    },
}

HIGH_RISK_CLASSES = [
    "anticoagulant",
    "opioid",
    "insulin",
    "chemotherapy",
    "antiarrhythmic",
]


class MedicationChecker:
    """Medication reconciliation and safety checking."""

    def reconcile(
        self,
        patient_id: str,
        home_medications: list[dict],
        hospital_medications: list[dict],
        allergies: list[str] | None = None,
    ) -> dict:
        home_names = {m["name"].lower() for m in home_medications}
        hospital_names = {m["name"].lower() for m in hospital_medications}

        changes = []
        for med in hospital_medications:
            name = med["name"].lower()
            if name in home_names:
                home_med = next(
                    m for m in home_medications if m["name"].lower() == name
                )
                if med.get("dose") != home_med.get("dose"):
                    changes.append(
                        {
                            "medication": med["name"],
                            "change": "dose_change",
                            "from": home_med.get("dose"),
                            "to": med.get("dose"),
                        }
                    )
                if med.get("frequency") != home_med.get("frequency"):
                    changes.append(
                        {
                            "medication": med["name"],
                            "change": "frequency_change",
                            "from": home_med.get("frequency"),
                            "to": med.get("frequency"),
                        }
                    )

        new_medications = [
            m for m in hospital_medications if m["name"].lower() not in home_names
        ]
        discontinued = [
            m for m in home_medications if m["name"].lower() not in hospital_names
        ]

        interactions = self._check_interactions(hospital_medications)
        allergy_conflicts = self._check_allergies(hospital_medications, allergies or [])
        adherence_risk = self._assess_adherence_risk(hospital_medications)

        return {
            "patient_id": patient_id,
            "changes": changes,
            "new_medications": new_medications,
            "discontinued": discontinued,
            "interactions": interactions,
            "allergy_conflicts": allergy_conflicts,
            "adherence_risk": adherence_risk,
            "discharge_med_list": hospital_medications,
            "reconciled_at": datetime.now(timezone.utc).isoformat(),
        }

    def _check_interactions(self, medications: list[dict]) -> list[dict]:
        interactions = []
        names = [m["name"].lower() for m in medications]
        checked = set()
        for i, name_a in enumerate(names):
            for name_b in names[i + 1 :]:
                pair = tuple(sorted([name_a, name_b]))
                if pair in checked:
                    continue
                checked.add(pair)
                if pair in DRUG_INTERACTIONS:
                    info = DRUG_INTERACTIONS[pair]
                    interactions.append(
                        {
                            "drug_a": name_a,
                            "drug_b": name_b,
                            "severity": info["severity"],
                            "description": info["description"],
                        }
                    )
        return interactions

    def _check_allergies(
        self, medications: list[dict], allergies: list[str]
    ) -> list[dict]:
        allergy_map = {
            "penicillin": ["amoxicillin", "ampicillin", "penicillin", "piperacillin"],
            "sulfa": [
                "sulfamethoxazole",
                "sulfasalazine",
                "furosemide",
                "hydrochlorothiazide",
            ],
            "aspirin": ["aspirin", "ibuprofen", "naproxen"],
        }
        conflicts = []
        for med in medications:
            name = med["name"].lower()
            for allergy in allergies:
                allergy_lower = allergy.lower()
                cross_reactive = allergy_map.get(allergy_lower, [allergy_lower])
                if name in cross_reactive:
                    conflicts.append(
                        {
                            "medication": med["name"],
                            "allergy": allergy,
                            "type": "direct"
                            if name == allergy_lower
                            else "cross-reactive",
                        }
                    )
        return conflicts

    def _assess_adherence_risk(self, medications: list[dict]) -> str:
        count = len(medications)
        high_risk_count = sum(
            1
            for m in medications
            if any(cls in m.get("name", "").lower() for cls in HIGH_RISK_CLASSES)
        )
        complex_dosing = sum(
            1
            for m in medications
            if m.get("frequency", "").lower()
            in (
                "three times daily",
                "four times daily",
                "every 6 hours",
                "every 8 hours",
            )
        )

        score = count + (high_risk_count * 2) + complex_dosing
        if score <= 3:
            return "low"
        elif score <= 6:
            return "moderate"
        return "high"
