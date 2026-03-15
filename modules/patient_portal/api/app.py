"""
Patient Portal API
FastAPI backend serving the patient-facing interface.
Connects to healthcare orchestration for discharge plans, medications, vitals, and care team.
"""

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timezone
from pathlib import Path
import uuid
import json
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

app = FastAPI(title="Patient Portal", version="1.0.0")

BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

PATIENT_STORE = BASE_DIR / "data" / "patients"
PATIENT_STORE.mkdir(parents=True, exist_ok=True)


class PatientLogin(BaseModel):
    patient_id: str
    access_code: str


class VitalsReading(BaseModel):
    patient_id: str
    metric: str
    value: float
    unit: str = ""
    notes: str = ""


class SymptomCheckIn(BaseModel):
    patient_id: str
    symptoms: list[str] = []
    severity: int = Field(ge=1, le=10, default=5)
    notes: str = ""


class PatientPortal:
    """Manages patient portal sessions and data."""

    def __init__(self):
        self._sessions = {}

    def create_session(self, patient_id: str, access_code: str) -> dict | None:
        patient_file = PATIENT_STORE / f"{patient_id}.json"
        if not patient_file.exists():
            patient_data = self._create_patient_record(patient_id)
        else:
            patient_data = json.loads(patient_file.read_text())

        if patient_data.get("access_code") != access_code:
            return None

        session_id = str(uuid.uuid4())
        self._sessions[session_id] = {
            "patient_id": patient_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": (
                datetime.now(timezone.utc).replace(hour=23, minute=59, second=59)
            ).isoformat(),
        }

        return {
            "session_id": session_id,
            "patient_id": patient_id,
            "patient_name": patient_data.get("name", "Patient"),
            "discharge_date": patient_data.get("discharge_date"),
        }

    def _create_patient_record(self, patient_id: str) -> dict:
        """Create a new patient record with default access code."""
        data = {
            "patient_id": patient_id,
            "access_code": "1234",
            "name": f"Patient {patient_id}",
            "discharge_date": datetime.now(timezone.utc).date().isoformat(),
            "diagnoses": [],
            "medications": [],
            "discharge_plan": {},
            "care_team": {"members": []},
            "vitals": [],
            "symptom_log": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        patient_file = PATIENT_STORE / f"{patient_id}.json"
        patient_file.write_text(json.dumps(data, indent=2))
        return data

    def get_patient_data(self, patient_id: str) -> dict:
        patient_file = PATIENT_STORE / f"{patient_id}.json"
        if not patient_file.exists():
            raise HTTPException(status_code=404, detail="Patient not found")
        return json.loads(patient_file.read_text())

    def save_patient_data(self, patient_id: str, data: dict):
        patient_file = PATIENT_STORE / f"{patient_id}.json"
        data["updated_at"] = datetime.now(timezone.utc).isoformat()
        patient_file.write_text(json.dumps(data, indent=2))

    def record_vitals(self, patient_id: str, vitals: dict):
        data = self.get_patient_data(patient_id)
        if "vitals" not in data:
            data["vitals"] = []
        data["vitals"].append(
            {
                **vitals,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        self.save_patient_data(patient_id, data)

    def record_symptom(self, patient_id: str, symptom: dict):
        data = self.get_patient_data(patient_id)
        if "symptom_log" not in data:
            data["symptom_log"] = []
        data["symptom_log"].append(
            {
                **symptom,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        self.save_patient_data(patient_id, data)


portal = PatientPortal()


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/dashboard")
async def dashboard(request: Request, session_id: str = ""):
    if not session_id or session_id not in portal._sessions:
        return templates.TemplateResponse(
            "login.html", {"request": request, "error": "Please log in"}
        )

    session = portal._sessions[session_id]
    patient = portal.get_patient_data(session["patient_id"])

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "patient": patient,
            "session": session,
        },
    )


@app.post("/api/login")
async def api_login(login: PatientLogin):
    result = portal.create_session(login.patient_id, login.access_code)
    if not result:
        raise HTTPException(status_code=401, detail="Invalid patient ID or access code")
    return result


@app.get("/api/patient/{patient_id}")
async def get_patient(patient_id: str):
    return portal.get_patient_data(patient_id)


@app.post("/api/vitals")
async def submit_vitals(vitals: VitalsReading):
    portal.record_vitals(vitals.patient_id, vitals.model_dump())
    return {"status": "recorded", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.post("/api/symptoms")
async def submit_symptoms(checkin: SymptomCheckIn):
    portal.record_symptom(checkin.patient_id, checkin.model_dump())
    return {"status": "recorded", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.get("/api/medications/{patient_id}")
async def get_medications(patient_id: str):
    data = portal.get_patient_data(patient_id)
    return {"medications": data.get("medications", [])}


@app.get("/api/discharge-plan/{patient_id}")
async def get_discharge_plan(patient_id: str):
    data = portal.get_patient_data(patient_id)
    return data.get("discharge_plan", {})


@app.get("/api/care-team/{patient_id}")
async def get_care_team(patient_id: str):
    data = portal.get_patient_data(patient_id)
    return data.get("care_team", {"members": []})


@app.get("/api/vitals-history/{patient_id}")
async def get_vitals_history(patient_id: str):
    data = portal.get_patient_data(patient_id)
    return {"vitals": data.get("vitals", [])}


@app.get("/api/symptom-history/{patient_id}")
async def get_symptom_history(patient_id: str):
    data = portal.get_patient_data(patient_id)
    return {"symptoms": data.get("symptom_log", [])}


@app.post("/api/sync-orchestration/{patient_id}")
async def sync_from_orchestration(patient_id: str):
    """Pull latest data from the healthcare orchestration system."""
    try:
        from workspaces.healthcare.orchestration.state import StateSchema
        from workspaces.healthcare.protocols.mcp_client import call_mcp_tool

        state = StateSchema.load_latest(patient_id)
        if not state:
            return {"status": "no_orchestration_data", "patient_id": patient_id}

        patient_data = portal.get_patient_data(patient_id)

        if state.patient_ehr:
            patient_data["diagnoses"] = state.patient_ehr.get("diagnoses", [])
            patient_data["name"] = state.patient_ehr.get(
                "name", patient_data.get("name", "Patient")
            )

        if state.follow_up_plan:
            patient_data["discharge_plan"] = state.follow_up_plan

        if state.care_team:
            patient_data["care_team"] = state.care_team

        if state.patient_instructions:
            patient_data["patient_instructions"] = state.patient_instructions

        portal.save_patient_data(patient_id, patient_data)

        return {"status": "synced", "patient_id": patient_id}
    except Exception as e:
        return {"status": "sync_failed", "error": str(e)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
