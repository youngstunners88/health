"""
Care Team Dashboard API
Provider-facing dashboard for monitoring discharged patients.
Shows risk scores, vitals trends, alerts, and patient status at a glance.
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone, timedelta
from pathlib import Path
import json
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

app = FastAPI(title="Care Team Dashboard", version="1.0.0")

BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

PATIENT_STORE = (
    Path(__file__).parent.parent / "patient-portal" / "api" / "data" / "patients"
)
ALERT_STORE = BASE_DIR / "data" / "alerts"
ALERT_STORE.mkdir(parents=True, exist_ok=True)


class AlertAction(BaseModel):
    alert_id: str
    action: str  # acknowledge, escalate, resolve, dismiss
    notes: str = ""


class CareDashboard:
    """Manages care team dashboard data."""

    def __init__(self):
        self._load_alerts()

    def _load_alerts(self):
        alerts_file = ALERT_STORE / "alerts.json"
        if alerts_file.exists():
            try:
                self.alerts = json.loads(alerts_file.read_text())
            except json.JSONDecodeError:
                self.alerts = []
        else:
            self.alerts = []

    def _save_alerts(self):
        alerts_file = ALERT_STORE / "alerts.json"
        alerts_file.write_text(json.dumps(self.alerts[-200:], indent=2, default=str))

    def get_all_patients(self) -> list[dict]:
        """Get all patients with summary data."""
        if not PATIENT_STORE.exists():
            return []

        patients = []
        for patient_file in PATIENT_STORE.glob("*.json"):
            try:
                data = json.loads(patient_file.read_text())
                patients.append(self._build_patient_summary(data))
            except (json.JSONDecodeError, KeyError):
                continue

        patients.sort(key=lambda p: p.get("alert_count", 0), reverse=True)
        return patients

    def _build_patient_summary(self, data: dict) -> dict:
        """Build a summary view of a patient for the dashboard."""
        vitals = data.get("vitals", [])
        symptoms = data.get("symptom_log", [])
        alerts = [
            a
            for a in self.alerts
            if a.get("patient_id") == data["patient_id"] and a.get("status") == "active"
        ]

        latest_vitals = {}
        if vitals:
            try:
                latest = json.loads(vitals[-1].get("notes", "{}"))
                latest_vitals = latest
            except (json.JSONDecodeError, IndexError):
                pass

        latest_symptom = symptoms[-1] if symptoms else None

        risk_level = "moderate"
        discharge_plan = data.get("discharge_plan", {})
        if discharge_plan:
            risk_level = discharge_plan.get("risk_level", "moderate")

        days_since_discharge = 0
        try:
            discharge_date = datetime.fromisoformat(data.get("discharge_date", ""))
            days_since_discharge = (datetime.now(timezone.utc) - discharge_date).days
        except (ValueError, TypeError):
            pass

        return {
            "patient_id": data["patient_id"],
            "name": data.get("name", "Unknown"),
            "discharge_date": data.get("discharge_date"),
            "days_since_discharge": days_since_discharge,
            "diagnoses": data.get("diagnoses", []),
            "medication_count": len(data.get("medications", [])),
            "risk_level": risk_level,
            "latest_vitals": latest_vitals,
            "latest_symptom": latest_symptom,
            "alert_count": len(alerts),
            "alerts": alerts,
            "vital_readings_count": len(vitals),
            "symptom_checkins_count": len(symptoms),
            "follow_up_count": len(discharge_plan.get("follow_up_appointments", [])),
        }

    def get_patient_detail(self, patient_id: str) -> dict:
        """Get detailed view of a single patient."""
        patient_file = PATIENT_STORE / f"{patient_id}.json"
        if not patient_file.exists():
            raise HTTPException(status_code=404, detail="Patient not found")

        data = json.loads(patient_file.read_text())
        summary = self._build_patient_summary(data)

        vitals_history = []
        for v in data.get("vitals", []):
            try:
                vitals_data = json.loads(v.get("notes", "{}"))
                vitals_history.append(
                    {
                        "timestamp": v.get("timestamp"),
                        **vitals_data,
                    }
                )
            except (json.JSONDecodeError, TypeError):
                pass

        return {
            **summary,
            "full_data": data,
            "vitals_history": vitals_history,
            "medications": data.get("medications", []),
            "care_team": data.get("care_team", {"members": []}),
            "discharge_plan": data.get("discharge_plan", {}),
        }

    def create_alert(
        self,
        patient_id: str,
        alert_type: str,
        severity: str,
        message: str,
        data: dict | None = None,
    ):
        """Create a new alert."""
        alert = {
            "alert_id": f"alert_{len(self.alerts) + 1}_{int(datetime.now(timezone.utc).timestamp())}",
            "patient_id": patient_id,
            "type": alert_type,
            "severity": severity,
            "message": message,
            "data": data or {},
            "status": "active",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "acknowledged_at": None,
            "resolved_at": None,
            "acknowledged_by": None,
            "resolved_by": None,
            "notes": "",
        }
        self.alerts.append(alert)
        self._save_alerts()
        return alert

    def process_alert_action(self, action: AlertAction, user: str = "provider") -> dict:
        """Process an alert action (acknowledge, escalate, resolve, dismiss)."""
        for alert in self.alerts:
            if alert.get("alert_id") == action.alert_id:
                now = datetime.now(timezone.utc).isoformat()
                alert["action_taken"] = action.action
                alert["action_by"] = user
                alert["action_notes"] = action.notes
                alert["action_at"] = now

                if action.action == "acknowledge":
                    alert["status"] = "acknowledged"
                    alert["acknowledged_at"] = now
                    alert["acknowledged_by"] = user
                elif action.action == "resolve":
                    alert["status"] = "resolved"
                    alert["resolved_at"] = now
                    alert["resolved_by"] = user
                elif action.action == "dismiss":
                    alert["status"] = "dismissed"
                    alert["resolved_at"] = now
                elif action.action == "escalate":
                    alert["status"] = "escalated"
                    alert["severity"] = "critical"

                self._save_alerts()
                return alert

        raise HTTPException(status_code=404, detail="Alert not found")

    def get_alerts(
        self, status: str | None = None, severity: str | None = None
    ) -> list[dict]:
        """Get alerts with optional filtering."""
        alerts = self.alerts
        if status:
            alerts = [a for a in alerts if a.get("status") == status]
        if severity:
            alerts = [a for a in alerts if a.get("severity") == severity]
        return sorted(alerts, key=lambda a: a.get("created_at", ""), reverse=True)

    def check_patient_alerts(self, patient_id: str) -> list[dict]:
        """Auto-generate alerts based on patient data."""
        patient_file = PATIENT_STORE / f"{patient_id}.json"
        if not patient_file.exists():
            return []

        data = json.loads(patient_file.read_text())
        new_alerts = []

        vitals = data.get("vitals", [])
        if vitals:
            try:
                latest = json.loads(vitals[-1].get("notes", "{}"))
                hr = latest.get("heart_rate")
                if hr and (hr > 100 or hr < 60):
                    new_alerts.append(
                        self.create_alert(
                            patient_id=patient_id,
                            alert_type="vitals",
                            severity="warning" if 60 <= hr <= 120 else "critical",
                            message=f"Abnormal heart rate: {hr} bpm",
                            data={"heart_rate": hr},
                        )
                    )

                spo2 = latest.get("spo2")
                if spo2 and spo2 < 92:
                    new_alerts.append(
                        self.create_alert(
                            patient_id=patient_id,
                            alert_type="vitals",
                            severity="critical",
                            message=f"Low oxygen saturation: {spo2}%",
                            data={"spo2": spo2},
                        )
                    )

                temp = latest.get("temperature")
                if temp and temp > 100.4:
                    new_alerts.append(
                        self.create_alert(
                            patient_id=patient_id,
                            alert_type="vitals",
                            severity="warning",
                            message=f"Elevated temperature: {temp}°F",
                            data={"temperature": temp},
                        )
                    )

                bp_sys = latest.get("systolic")
                bp_dia = latest.get("diastolic")
                if bp_sys and bp_sys > 160:
                    new_alerts.append(
                        self.create_alert(
                            patient_id=patient_id,
                            alert_type="vitals",
                            severity="warning",
                            message=f"High blood pressure: {bp_sys}/{bp_dia}",
                            data={"systolic": bp_sys, "diastolic": bp_dia},
                        )
                    )
            except (json.JSONDecodeError, IndexError):
                pass

        symptoms = data.get("symptom_log", [])
        if symptoms:
            latest = symptoms[-1]
            if latest.get("severity", 0) >= 8:
                new_alerts.append(
                    self.create_alert(
                        patient_id=patient_id,
                        alert_type="symptom",
                        severity="warning",
                        message=f"High severity symptom check-in: {latest.get('severity')}/10",
                        data={
                            "symptoms": latest.get("symptoms", []),
                            "severity": latest.get("severity"),
                        },
                    )
                )
            if "chest_pain" in latest.get("symptoms", []):
                new_alerts.append(
                    self.create_alert(
                        patient_id=patient_id,
                        alert_type="symptom",
                        severity="critical",
                        message="Patient reported chest pain",
                        data={"symptoms": latest.get("symptoms", [])},
                    )
                )
            if "shortness_of_breath" in latest.get("symptoms", []):
                new_alerts.append(
                    self.create_alert(
                        patient_id=patient_id,
                        alert_type="symptom",
                        severity="warning",
                        message="Patient reported shortness of breath",
                        data={"symptoms": latest.get("symptoms", [])},
                    )
                )

        return new_alerts


dashboard = CareDashboard()


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    patients = dashboard.get_all_patients()
    alerts = dashboard.get_alerts(status="active")
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "patients": patients,
            "alerts": alerts,
            "total_patients": len(patients),
            "active_alerts": len(
                [a for a in alerts if a.get("severity") in ("critical", "warning")]
            ),
        },
    )


@app.get("/patient/{patient_id}")
async def patient_detail(request: Request, patient_id: str):
    try:
        patient = dashboard.get_patient_detail(patient_id)
        new_alerts = dashboard.check_patient_alerts(patient_id)
        all_alerts = dashboard.get_alerts()
        patient_alerts = [a for a in all_alerts if a.get("patient_id") == patient_id]
        return templates.TemplateResponse(
            "patient_detail.html",
            {
                "request": request,
                "patient": patient,
                "alerts": patient_alerts,
                "new_alerts": new_alerts,
            },
        )
    except HTTPException:
        raise


@app.get("/alerts")
async def alerts_page(request: Request, status: str = "active"):
    alerts = dashboard.get_alerts(status=status if status != "all" else None)
    return templates.TemplateResponse(
        "alerts.html",
        {
            "request": request,
            "alerts": alerts,
            "current_filter": status,
        },
    )


@app.post("/api/alerts/action")
async def alert_action(action: AlertAction):
    return dashboard.process_alert_action(action)


@app.get("/api/patients")
async def api_patients():
    return dashboard.get_all_patients()


@app.get("/api/patient/{patient_id}")
async def api_patient_detail(patient_id: str):
    return dashboard.get_patient_detail(patient_id)


@app.get("/api/alerts")
async def api_alerts(status: str = "active", severity: str = None):
    return dashboard.get_alerts(
        status=status if status != "all" else None, severity=severity
    )


@app.post("/api/patient/{patient_id}/check-alerts")
async def check_alerts(patient_id: str):
    new_alerts = dashboard.check_patient_alerts(patient_id)
    return {"new_alerts": len(new_alerts), "alerts": new_alerts}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8081)
