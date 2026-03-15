"""
Seed script to create sample patient data connected to orchestration output.
Run after the orchestration graph processes a patient.
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

PATIENT_STORE = Path(__file__).parent.parent / "api" / "data" / "patients"
PATIENT_STORE.mkdir(parents=True, exist_ok=True)


def seed_patient(patient_id: str = "12345"):
    """Create a sample patient with realistic discharge data."""

    patient_data = {
        "patient_id": patient_id,
        "access_code": "1234",
        "name": "John Doe",
        "discharge_date": datetime.now(timezone.utc).date().isoformat(),
        "diagnoses": ["CHF", "Type 2 Diabetes"],
        "medications": [
            {
                "name": "lisinopril",
                "dose": "20mg",
                "frequency": "daily",
                "instructions": "Take in the morning with water",
            },
            {
                "name": "metformin",
                "dose": "500mg",
                "frequency": "twice daily",
                "instructions": "Take with meals",
            },
            {
                "name": "furosemide",
                "dose": "40mg",
                "frequency": "daily",
                "instructions": "Take in the morning. Avoid nighttime dosing.",
            },
        ],
        "discharge_plan": {
            "risk_level": "high",
            "follow_up_appointments": [
                {
                    "specialist": "PCP",
                    "condition": "General follow-up",
                    "days_from_discharge": 7,
                    "priority": "high",
                },
                {
                    "specialist": "Cardiology",
                    "condition": "CHF",
                    "days_from_discharge": 7,
                    "priority": "high",
                },
                {
                    "specialist": "Endocrinology",
                    "condition": "Type 2 Diabetes",
                    "days_from_discharge": 14,
                    "priority": "moderate",
                },
            ],
            "warning_signs": [
                "Sudden weight gain (more than 2-3 lbs in a day or 5 lbs in a week)",
                "Increased shortness of breath, especially when lying flat",
                "Swelling in legs, ankles, or abdomen",
                "Blood sugar consistently above 250 or below 70",
                "Fever above 101F (38.3C)",
                "Chest pain or pressure",
                "Difficulty breathing",
            ],
            "home_care_instructions": [
                "Take all medications as prescribed",
                "Keep all follow-up appointments",
                "Weigh yourself daily at the same time each morning",
                "Follow a low-sodium diet (less than 2g per day)",
                "Limit fluid intake to 2 liters per day unless otherwise directed",
                "Monitor blood sugar as directed",
                "Check feet daily for cuts, blisters, or sores",
                "Monitor blood pressure (current: 130/80)",
            ],
        },
        "care_team": {
            "members": [
                {
                    "role": "primary_care",
                    "title": "Primary Care Provider",
                    "name": "Dr. Smith",
                    "responsibilities": [
                        "Overall care management",
                        "Follow-up coordination",
                        "Medication management",
                    ],
                },
                {
                    "role": "cardiology",
                    "title": "Cardiologist",
                    "name": "Cardiology Team",
                    "responsibilities": [
                        "Heart failure management",
                        "Echocardiogram scheduling",
                        "Medication titration",
                    ],
                },
                {
                    "role": "pharmacy",
                    "title": "Clinical Pharmacist",
                    "name": "Clinical Pharmacy",
                    "responsibilities": [
                        "Medication reconciliation",
                        "Drug interaction review",
                        "Patient education",
                    ],
                },
            ]
        },
        "vitals": [],
        "symptom_log": [],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    patient_file = PATIENT_STORE / f"{patient_id}.json"
    patient_file.write_text(json.dumps(patient_data, indent=2))
    print(f"Seeded patient {patient_id} -> {patient_file}")
    return patient_data


if __name__ == "__main__":
    pid = sys.argv[1] if len(sys.argv) > 1 else "12345"
    seed_patient(pid)
