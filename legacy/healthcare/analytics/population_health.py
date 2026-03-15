"""
Population Health Analytics
Aggregate analytics across all patients for quality reporting and value-based care.
"""

import json
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Optional


PATIENT_STORE = (
    Path(__file__).parent.parent / "patient-portal" / "api" / "data" / "patients"
)
PRIOR_AUTH_DATA = (
    Path(__file__).parent.parent / "prior-auth" / "data" / "authorizations.json"
)
CARE_DASHBOARD_ALERTS = (
    Path(__file__).parent.parent
    / "care-dashboard"
    / "api"
    / "data"
    / "alerts"
    / "alerts.json"
)


class PopulationHealthAnalytics:
    """Aggregate analytics for population health management."""

    def get_overview(self) -> dict:
        """High-level population health overview."""
        patients = self._load_all_patients()
        auths = self._load_prior_auths()
        alerts = self._load_alerts()

        total = len(patients)
        if total == 0:
            return {"total_patients": 0, "message": "No patient data available"}

        risk_distribution = {"low": 0, "moderate": 0, "high": 0, "very_high": 0}
        diagnoses_count = {}
        days_since_discharge = []

        for p in patients:
            plan = p.get("discharge_plan", {})
            risk = plan.get("risk_level", "moderate")
            risk_distribution[risk] = risk_distribution.get(risk, 0) + 1

            for dx in p.get("diagnoses", []):
                diagnoses_count[dx] = diagnoses_count.get(dx, 0) + 1

            try:
                discharge_date = datetime.fromisoformat(p.get("discharge_date", ""))
                days = (datetime.now(timezone.utc) - discharge_date).days
                days_since_discharge.append(days)
            except (ValueError, TypeError):
                pass

        avg_days = (
            sum(days_since_discharge) / len(days_since_discharge)
            if days_since_discharge
            else 0
        )

        top_diagnoses = sorted(
            diagnoses_count.items(), key=lambda x: x[1], reverse=True
        )[:10]

        return {
            "total_patients": total,
            "risk_distribution": risk_distribution,
            "high_risk_percentage": round(
                (
                    risk_distribution.get("high", 0)
                    + risk_distribution.get("very_high", 0)
                )
                / total
                * 100,
                1,
            ),
            "avg_days_since_discharge": round(avg_days, 1),
            "top_diagnoses": [
                {"diagnosis": dx, "count": count} for dx, count in top_diagnoses
            ],
            "total_prior_auths": len(auths),
            "total_alerts": len([a for a in alerts if a.get("status") == "active"]),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def get_quality_metrics(self) -> dict:
        """Quality metrics for MIPS/HEDIS reporting."""
        patients = self._load_all_patients()
        auths = self._load_prior_auths()

        total = len(patients)
        if total == 0:
            return {"message": "No data available"}

        patients_with_followup = sum(
            1
            for p in patients
            if p.get("discharge_plan", {}).get("follow_up_appointments")
        )

        patients_with_meds = sum(1 for p in patients if p.get("medications"))

        patients_with_care_team = sum(
            1 for p in patients if p.get("care_team", {}).get("members")
        )

        patients_with_vitals = sum(1 for p in patients if p.get("vitals"))

        auth_approval_rate = 0
        if auths:
            approved = len([a for a in auths if a.get("status") == "approved"])
            decided = len(
                [a for a in auths if a.get("status") in ("approved", "denied")]
            )
            if decided > 0:
                auth_approval_rate = round(approved / decided * 100, 1)

        return {
            "care_transition_measures": {
                "patients_with_followup_scheduled": patients_with_followup,
                "followup_rate": round(patients_with_followup / total * 100, 1),
                "patients_with_medication_reconciliation": patients_with_meds,
                "med_reconciliation_rate": round(patients_with_meds / total * 100, 1),
                "patients_with_care_team_assigned": patients_with_care_team,
                "care_team_rate": round(patients_with_care_team / total * 100, 1),
            },
            "prior_auth_metrics": {
                "total_requests": len(auths),
                "approval_rate": auth_approval_rate,
            },
            "patient_engagement": {
                "patients_with_vitals_logged": patients_with_vitals,
                "engagement_rate": round(patients_with_vitals / total * 100, 1),
            },
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def get_readmission_risk_report(self) -> dict:
        """Readmission risk analysis across the population."""
        patients = self._load_all_patients()

        risk_groups = {"low": [], "moderate": [], "high": [], "very_high": []}
        for p in patients:
            risk = p.get("discharge_plan", {}).get("risk_level", "moderate")
            risk_groups[risk].append(
                {
                    "patient_id": p["patient_id"],
                    "name": p.get("name", "Unknown"),
                    "diagnoses": p.get("diagnoses", []),
                    "days_since_discharge": self._days_since(p),
                }
            )

        return {
            "risk_groups": {
                k: {"count": len(v), "patients": v} for k, v in risk_groups.items()
            },
            "total_at_risk": len(risk_groups.get("high", []))
            + len(risk_groups.get("very_high", [])),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def _load_all_patients(self) -> list[dict]:
        if not PATIENT_STORE.exists():
            return []
        patients = []
        for f in PATIENT_STORE.glob("*.json"):
            try:
                patients.append(json.loads(f.read_text()))
            except (json.JSONDecodeError, KeyError):
                pass
        return patients

    def _load_prior_auths(self) -> list[dict]:
        if not PRIOR_AUTH_DATA.exists():
            return []
        try:
            return json.loads(PRIOR_AUTH_DATA.read_text())
        except (json.JSONDecodeError, KeyError):
            return []

    def _load_alerts(self) -> list[dict]:
        if not CARE_DASHBOARD_ALERTS.exists():
            return []
        try:
            return json.loads(CARE_DASHBOARD_ALERTS.read_text())
        except (json.JSONDecodeError, KeyError):
            return []

    def _days_since(self, patient: dict) -> int:
        try:
            discharge_date = datetime.fromisoformat(patient.get("discharge_date", ""))
            return (datetime.now(timezone.utc) - discharge_date).days
        except (ValueError, TypeError):
            return -1
