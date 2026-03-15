#!/usr/bin/env python3
"""
Seed Script - Creates realistic patient data across all services.
Run this before starting the platform to have demo data ready.
"""

import sys
from pathlib import Path
import json
from datetime import datetime, timezone, timedelta

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

SEED_DIR = ROOT / "data" / "seed"
SEED_DIR.mkdir(parents=True, exist_ok=True)


def seed_patient_data():
    """Create patient portal data."""
    patient_store = ROOT / "workspaces/healthcare/patient-portal/api/data/patients"
    patient_store.mkdir(parents=True, exist_ok=True)

    patients = [
        {
            "patient_id": "PT-001",
            "access_code": "1234",
            "name": "John Doe",
            "discharge_date": (datetime.now(timezone.utc) - timedelta(days=3))
            .date()
            .isoformat(),
            "diagnoses": ["CHF", "Type 2 Diabetes"],
            "medications": [
                {
                    "name": "lisinopril",
                    "dose": "20mg",
                    "frequency": "daily",
                    "instructions": "Take in the morning",
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
                    "instructions": "Take in the morning",
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
                    "Sudden weight gain (more than 2-3 lbs in a day)",
                    "Increased shortness of breath",
                    "Swelling in legs, ankles, or abdomen",
                    "Blood sugar consistently above 250 or below 70",
                    "Fever above 101F",
                ],
                "home_care_instructions": [
                    "Take all medications as prescribed",
                    "Weigh yourself daily at the same time",
                    "Follow a low-sodium diet (less than 2g per day)",
                    "Limit fluid intake to 2 liters per day",
                    "Monitor blood sugar as directed",
                    "Check feet daily for cuts or sores",
                ],
                "social_services_referrals": [
                    {
                        "service": "Home health aide",
                        "reason": "Patient lives alone",
                        "urgency": "moderate",
                    },
                    {
                        "service": "Medical transportation",
                        "reason": "No transportation to appointments",
                        "urgency": "high",
                    },
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
                        ],
                    },
                    {
                        "role": "cardiology",
                        "title": "Cardiologist",
                        "name": "Dr. Johnson",
                        "responsibilities": [
                            "Heart failure management",
                            "Medication titration",
                        ],
                    },
                    {
                        "role": "pharmacy",
                        "title": "Clinical Pharmacist",
                        "name": "Pharmacy Team",
                        "responsibilities": [
                            "Medication reconciliation",
                            "Drug interaction review",
                        ],
                    },
                ]
            },
            "vitals": [
                {
                    "patient_id": "PT-001",
                    "metric": "vitals_checkin",
                    "value": 1,
                    "unit": "checkin",
                    "notes": json.dumps(
                        {
                            "heart_rate": 88,
                            "systolic": 148,
                            "diastolic": 92,
                            "spo2": 96,
                            "temperature": 98.8,
                            "weight": 185.2,
                        }
                    ),
                    "timestamp": (
                        datetime.now(timezone.utc) - timedelta(hours=2)
                    ).isoformat(),
                },
                {
                    "patient_id": "PT-001",
                    "metric": "vitals_checkin",
                    "value": 1,
                    "unit": "checkin",
                    "notes": json.dumps(
                        {
                            "heart_rate": 82,
                            "systolic": 142,
                            "diastolic": 88,
                            "spo2": 97,
                            "temperature": 98.6,
                            "weight": 184.8,
                        }
                    ),
                    "timestamp": (
                        datetime.now(timezone.utc) - timedelta(hours=26)
                    ).isoformat(),
                },
            ],
            "symptom_log": [
                {
                    "patient_id": "PT-001",
                    "symptoms": ["fatigue", "swelling"],
                    "severity": 4,
                    "notes": "Feeling tired, some ankle swelling",
                    "timestamp": (
                        datetime.now(timezone.utc) - timedelta(hours=4)
                    ).isoformat(),
                },
            ],
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
        {
            "patient_id": "PT-002",
            "access_code": "5678",
            "name": "Jane Smith",
            "discharge_date": (datetime.now(timezone.utc) - timedelta(days=1))
            .date()
            .isoformat(),
            "diagnoses": ["COPD", "Hypertension"],
            "medications": [
                {
                    "name": "albuterol",
                    "dose": "90mcg",
                    "frequency": "as needed",
                    "instructions": "2 puffs every 4-6 hours as needed",
                },
                {
                    "name": "amlodipine",
                    "dose": "5mg",
                    "frequency": "daily",
                    "instructions": "Take in the morning",
                },
            ],
            "discharge_plan": {
                "risk_level": "moderate",
                "follow_up_appointments": [
                    {
                        "specialist": "PCP",
                        "condition": "General follow-up",
                        "days_from_discharge": 7,
                        "priority": "high",
                    },
                    {
                        "specialist": "Pulmonology",
                        "condition": "COPD",
                        "days_from_discharge": 14,
                        "priority": "moderate",
                    },
                ],
                "warning_signs": [
                    "Increased difficulty breathing",
                    "Change in mucus color or amount",
                    "Fever above 101F",
                    "Chest pain",
                ],
                "home_care_instructions": [
                    "Take medications as prescribed",
                    "Use inhaler as directed",
                    "Avoid smoke and respiratory irritants",
                    "Practice breathing exercises daily",
                ],
                "social_services_referrals": [],
            },
            "care_team": {
                "members": [
                    {
                        "role": "primary_care",
                        "title": "Primary Care Provider",
                        "name": "Dr. Williams",
                        "responsibilities": ["Overall care management"],
                    },
                    {
                        "role": "pulmonology",
                        "title": "Pulmonologist",
                        "name": "Dr. Chen",
                        "responsibilities": [
                            "COPD management",
                            "Pulmonary function testing",
                        ],
                    },
                ]
            },
            "vitals": [
                {
                    "patient_id": "PT-002",
                    "metric": "vitals_checkin",
                    "value": 1,
                    "unit": "checkin",
                    "notes": json.dumps(
                        {
                            "heart_rate": 76,
                            "systolic": 135,
                            "diastolic": 85,
                            "spo2": 95,
                            "temperature": 98.4,
                        }
                    ),
                    "timestamp": (
                        datetime.now(timezone.utc) - timedelta(hours=6)
                    ).isoformat(),
                },
            ],
            "symptom_log": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
        {
            "patient_id": "PT-003",
            "access_code": "9012",
            "name": "Robert Johnson",
            "discharge_date": (datetime.now(timezone.utc) - timedelta(days=5))
            .date()
            .isoformat(),
            "diagnoses": ["Pneumonia", "Type 2 Diabetes"],
            "medications": [
                {
                    "name": "amoxicillin",
                    "dose": "500mg",
                    "frequency": "three times daily",
                    "instructions": "Complete full 10-day course",
                },
                {
                    "name": "metformin",
                    "dose": "1000mg",
                    "frequency": "twice daily",
                    "instructions": "Take with meals",
                },
            ],
            "discharge_plan": {
                "risk_level": "moderate",
                "follow_up_appointments": [
                    {
                        "specialist": "PCP",
                        "condition": "General follow-up",
                        "days_from_discharge": 7,
                        "priority": "high",
                    },
                    {
                        "specialist": "Endocrinology",
                        "condition": "Type 2 Diabetes",
                        "days_from_discharge": 30,
                        "priority": "low",
                    },
                ],
                "warning_signs": [
                    "Fever returns",
                    "Difficulty breathing",
                    "Chest pain",
                    "Blood sugar above 250",
                ],
                "home_care_instructions": [
                    "Complete full antibiotic course",
                    "Monitor blood sugar regularly",
                    "Get adequate rest",
                    "Drink plenty of fluids",
                ],
                "social_services_referrals": [],
            },
            "care_team": {
                "members": [
                    {
                        "role": "primary_care",
                        "title": "Primary Care Provider",
                        "name": "Dr. Martinez",
                        "responsibilities": [
                            "Overall care management",
                            "Antibiotic monitoring",
                        ],
                    },
                ]
            },
            "vitals": [],
            "symptom_log": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    ]

    for patient in patients:
        patient_file = patient_store / f"{patient['patient_id']}.json"
        patient_file.write_text(json.dumps(patient, indent=2))
        print(f"  ✓ Patient: {patient['name']} ({patient['patient_id']})")

    return patients


def seed_prior_auth():
    """Create prior authorization data."""
    from healthcare.modules.prior_auth.service.engine import PriorAuthEngine

    engine = PriorAuthEngine()

    # Create auths for PT-001
    procs = ["Home Health", "Physical Therapy", "Durable Medical Equipment"]
    for proc in procs:
        auth = engine.create_auth_request(
            patient_id="PT-001",
            patient_name="John Doe",
            payer_name="BlueCross BlueShield",
            procedure=proc,
            diagnosis_codes=["I50.9", "E11.9"],
            provider_name="Dr. Smith",
            provider_npi="1234567890",
            clinical_notes=f"Patient discharged with CHF exacerbation. {proc} medically necessary.",
        )
        print(f"  ✓ Prior Auth: {auth['auth_id']} - {proc}")

    # Simulate a decision
    if engine.authorizations:
        engine.process_decision(
            auth_id=engine.authorizations[0]["auth_id"],
            decision="approved",
            auth_number="AUTH-BCBS-2026-001",
            decision_reason="Meets medical necessity criteria",
        )
        print(f"  ✓ Decision: {engine.authorizations[0]['auth_id']} approved")

    return engine


def seed_claims():
    """Create claims data."""
    from healthcare.modules.revenue_cycle.service.engine import ClaimsEngine

    engine = ClaimsEngine()

    claim = engine.submit_claim(
        patient_id="PT-001",
        patient_name="John Doe",
        patient_dob="1960-03-15",
        patient_mrn="MRN-001",
        payer_name="BlueCross BlueShield",
        payer_id="BCBS",
        subscriber_id="SUB-001",
        provider_name="Dr. Smith",
        provider_npi="1234567890",
        provider_tax_id="12-3456789",
        place_of_service="21",
        charge_amount=12500.00,
        diagnoses=["I50.9", "E11.9"],
        procedures=[
            {"code": "99223", "modifier": "", "units": 1, "charge": 5000.0},
            {"code": "93306", "modifier": "", "units": 1, "charge": 3500.0},
            {"code": "99238", "modifier": "", "units": 1, "charge": 4000.0},
        ],
    )
    print(f"  ✓ Claim: {claim['claim_id']} - ${claim['charge_amount']:,.2f}")

    return engine


def seed_sdoh():
    """Create SDOH screening data."""
    from healthcare.modules.sdoh.service.engine import SDOHEngine

    engine = SDOHEngine()

    screening = engine.create_screening(
        patient_id="PT-001",
        patient_name="John Doe",
        responses={
            "so2": "yes",
            "so1": "no",
            "t1": "no",
            "t2": "yes",
            "f1": "yes",
            "f2": "yes",
            "fi1": 4,
            "fi3": "yes",
        },
        screened_by="auto_discharge",
        screening_context="discharge",
    )
    print(
        f"  ✓ SDOH Screening: {screening['screening_id']} - Risk: {screening['overall_risk_level']}"
    )
    print(f"    → {len(screening['auto_referrals'])} auto-referrals generated")

    return engine


def seed_wearables():
    """Create wearable device registrations."""
    from healthcare.modules.wearables.service.engine import WearableEngine

    engine = WearableEngine()

    devices = [
        ("bluetooth_bp_cuff", "Home BP Monitor"),
        ("bluetooth_glucose_meter", "Home Glucose Meter"),
        ("bluetooth_pulse_oximeter", "Home Pulse Oximeter"),
    ]
    for dtype, dname in devices:
        device = engine.register_device(
            patient_id="PT-001",
            patient_name="John Doe",
            device_type=dtype,
            device_name=dname,
        )
        print(f"  ✓ Device: {dname} ({device['device_id']})")

    return engine


def main():
    print("=" * 60)
    print("HEALTHCARE PLATFORM - SEEDING DATA")
    print("=" * 60)
    print()

    print("Patients:")
    patients = seed_patient_data()
    print()

    print("Prior Authorizations:")
    seed_prior_auth()
    print()

    print("Claims:")
    seed_claims()
    print()

    print("SDOH Screenings:")
    seed_sdoh()
    print()

    print("Wearable Devices:")
    seed_wearables()
    print()

    print("=" * 60)
    print("SEEDING COMPLETE")
    print("=" * 60)
    print()
    print("Patient Portal:   http://localhost:8080 (ID: PT-001, Code: 1234)")
    print("Care Dashboard:   http://localhost:8081")
    print("Prior Auth:       http://localhost:8082")
    print("Revenue Cycle:    http://localhost:8083")
    print("SDOH:             http://localhost:8084")
    print("Wearables:        http://localhost:8085")
    print("Notifications:    http://localhost:8086")
    print("Clinical Trials:  http://localhost:8087")
    print("Marketplace:      http://localhost:8088")
    print("Compliance:       http://localhost:8089")


if __name__ == "__main__":
    main()
