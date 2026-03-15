"""
End-to-end demo script.
Runs a full discharge pipeline: intake → risk → payer/prior-auth → payment → followup → monitor.
Then seeds patient portal and care dashboard data.
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from workspaces.healthcare.orchestration.state import StateSchema
from workspaces.healthcare.orchestration.graph import app as graph_app
from workspaces.healthcare.prior_auth.engine.authorization import (
    PriorAuthEngine,
    PayerRulesDB,
)


def run_demo(patient_id: str = "demo-001"):
    print("=" * 60)
    print("HEALTHCARE DISCHARGE ORCHESTRATION - END-TO-END DEMO")
    print("=" * 60)

    print(f"\n[1/6] INTAKE — Pulling EHR for patient {patient_id}...")
    print(f"  Patient: John Doe")
    print(f"  Diagnoses: CHF, Type 2 Diabetes")
    print(f"  Admission: 2026-03-15")

    print(f"\n[2/6] RISK ASSESSMENT — Calculating readmission risk...")
    from skills.risk_scoring.scripts.risk_calculator import calculate_risk

    risk = calculate_risk(
        patient_id=patient_id,
        method="lace",
        params={
            "length_of_stay_days": 5,
            "admission_acuity": "emergency",
            "comorbidities": ["CHF", "diabetes"],
            "ed_visits_last_6mo": 2,
        },
    )
    print(f"  LACE Score: {risk['score']}")
    print(f"  Readmission Risk: {risk['risk'] * 100:.0f}%")
    print(f"  Risk Level: {risk['level'].upper()}")
    for factor in risk["factors"]:
        print(f"  → {factor}")

    print(f"\n[3/6] PAYER CHECK + PRIOR AUTH — Checking coverage...")
    payer_rules = PayerRulesDB()
    auth_engine = PriorAuthEngine()

    payer = "BlueCross BlueShield"
    procedures = ["Home Health", "Physical Therapy", "Durable Medical Equipment"]
    for proc in procedures:
        needs = payer_rules.needs_prior_auth(payer, proc)
        status = "REQUIRES AUTH" if needs else "NO AUTH NEEDED"
        print(f"  {proc}: {status}")

        if needs:
            auth = auth_engine.create_auth_request(
                patient_id=patient_id,
                patient_name="John Doe",
                payer_name=payer,
                procedure=proc,
                diagnosis_codes=["I50.9", "E11.9"],
                provider_name="Dr. Smith",
                provider_npi="1234567890",
                clinical_notes=f"Patient discharged with CHF exacerbation. {proc} medically necessary for recovery.",
            )
            print(f"    → Auto-created: {auth['auth_id']}")
            print(
                f"    → Justification: {auth['clinical_justification']['medical_necessity'][:80]}..."
            )

    print(f"\n[4/6] DISCHARGE PLANNING — Generating plan...")
    from skills.discharge_planning.scripts.planner import DischargePlanner

    planner = DischargePlanner()
    plan = planner.generate_plan(
        patient_id=patient_id,
        risk_level=risk["level"],
        conditions=["CHF", "Type 2 Diabetes"],
        medications=[
            {"name": "lisinopril", "dose": "20mg", "frequency": "daily"},
            {"name": "metformin", "dose": "500mg", "frequency": "twice daily"},
            {"name": "furosemide", "dose": "40mg", "frequency": "daily"},
        ],
        social_factors={"living_alone": True, "transportation": False},
    )
    print(f"  Follow-ups: {len(plan['follow_up_appointments'])}")
    for appt in plan["follow_up_appointments"][:3]:
        print(
            f"    → {appt['specialist']} in {appt['days_from_discharge']} days ({appt['priority']})"
        )
    print(f"  Social Referrals: {len(plan['social_services_referrals'])}")
    for ref in plan["social_services_referrals"]:
        print(f"    → {ref['service']} ({ref['urgency']})")

    print(f"\n[5/6] MEDICATION RECONCILIATION — Checking safety...")
    from skills.medication_reconciliation.scripts.med_checker import MedicationChecker

    checker = MedicationChecker()
    med_result = checker.reconcile(
        patient_id=patient_id,
        home_medications=[
            {"name": "lisinopril", "dose": "10mg", "frequency": "daily"},
            {"name": "metformin", "dose": "500mg", "frequency": "twice daily"},
        ],
        hospital_medications=[
            {"name": "lisinopril", "dose": "20mg", "frequency": "daily"},
            {"name": "metformin", "dose": "500mg", "frequency": "twice daily"},
            {"name": "furosemide", "dose": "40mg", "frequency": "daily"},
        ],
        allergies=["penicillin"],
    )
    print(f"  Changes: {len(med_result['changes'])}")
    for change in med_result["changes"]:
        print(
            f"    → {change['medication']}: {change['change']} ({change['from']} → {change['to']})"
        )
    print(f"  New Medications: {len(med_result['new_medications'])}")
    for med in med_result["new_medications"]:
        print(f"    → {med['name']} {med['dose']}")
    print(f"  Interactions: {len(med_result['interactions'])}")
    for ix in med_result["interactions"]:
        print(
            f"    → {ix['drug_a']} + {ix['drug_b']}: {ix['severity']} — {ix['description']}"
        )

    print(f"\n[6/8] MONITORING SETUP — Anomaly detection configured...")
    from skills.anomaly_detection.scripts.detector import AnomalyDetector

    detector = AnomalyDetector()
    vitals_check = detector.check_vitals(
        {
            "heart_rate": 88,
            "systolic_bp": 148,
            "diastolic_bp": 92,
            "spo2": 96,
        }
    )
    print(f"  Vitals Status: {vitals_check['overall_status']}")
    if vitals_check["alerts"]:
        for alert in vitals_check["alerts"]:
            print(f"    ⚠️ {alert['metric']}: {alert['value']} (z={alert['zscore']})")
    else:
        print(f"  All vitals within normal range")

    print(f"\n[7/8] SDOH SCREENING — Social determinants assessment...")
    from workspaces.healthcare.sdoh.engine.screening import SDOHEngine

    sdoh_engine = SDOHEngine()
    screening = sdoh_engine.create_screening(
        patient_id=patient_id,
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
    print(f"  Screening ID: {screening['screening_id']}")
    print(f"  Overall Risk: {screening['overall_risk_level'].upper()}")
    print(f"  At-Risk Domains: {', '.join(screening['positive_domains'])}")
    print(f"  Auto-Referrals Generated: {len(screening['auto_referrals'])}")
    for ref in screening["auto_referrals"][:5]:
        print(f"    → {ref['resource_name']} ({ref['domain']})")

    print(f"\n[8/8] WEARABLE/IoT SETUP — Registering monitoring devices...")
    from workspaces.healthcare.wearables.engine.devices import WearableEngine

    wearable_engine = WearableEngine()
    devices = [
        ("bluetooth_bp_cuff", "Home BP Monitor"),
        ("bluetooth_glucose_meter", "Home Glucose Meter"),
        ("bluetooth_pulse_oximeter", "Home Pulse Oximeter"),
        ("bluetooth_scale", "Home Smart Scale"),
    ]
    registered = []
    for dtype, dname in devices:
        device = wearable_engine.register_device(
            patient_id=patient_id,
            patient_name="John Doe",
            device_type=dtype,
            device_name=dname,
        )
        registered.append(device)
        print(f"  → {dname} ({dtype}): {device['device_id']}")

    print(f"\n{'=' * 60}")
    print(f"DEMO COMPLETE — Patient {patient_id} discharged successfully")
    print(f"{'=' * 60}")

    stats = auth_engine.get_statistics()
    print(f"\nPrior Auth Summary:")
    print(f"  Total Requests: {stats['total']}")
    print(f"  Pending: {stats['pending']}")
    print(f"  Approval Rate: {stats['approval_rate']}%")

    print(f"\nNext Steps:")
    print(
        f"  1. Patient Portal:  python -m uvicorn workspaces.healthcare.patient-portal.api.app:app --port 8080"
    )
    print(
        f"  2. Care Dashboard:  python -m uvicorn workspaces.healthcare.care-dashboard.api.app:app --port 8081"
    )
    print(
        f"  3. Prior Auth:      python -m uvicorn workspaces.healthcare.prior-auth.api.app:app --port 8082"
    )

    return {
        "patient_id": patient_id,
        "risk": risk,
        "plan": plan,
        "medications": med_result,
        "vitals": vitals_check,
        "prior_auth_stats": stats,
    }


if __name__ == "__main__":
    pid = sys.argv[1] if len(sys.argv) > 1 else "demo-001"
    run_demo(pid)
