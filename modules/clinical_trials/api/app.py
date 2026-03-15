"""FastAPI server for Clinical Trials Matching Service."""

import logging
import os
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from engine.matching import ClinicalTrialsEngine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"

engine = ClinicalTrialsEngine()


class PatientEHR(BaseModel):
    patient_id: str
    age: int = Field(..., ge=0, le=150)
    gender: str
    diagnoses: list[str]
    medications: list[str] = []
    comorbidities: list[str] = []
    prior_treatments: list[str] = []
    bmi: float | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Clinical Trials API starting up")
    yield
    logger.info("Clinical Trials API shutting down")


app = FastAPI(
    title="Clinical Trials Matching Service",
    description="Matches patients to clinical trials based on EHR data",
    version="1.0.0",
    lifespan=lifespan,
)

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    stats = engine.get_statistics()
    return templates.TemplateResponse(
        "trials_dashboard.html",
        {"request": request, "stats": stats},
    )


@app.post("/api/match")
async def match_patient(patient: PatientEHR):
    try:
        patient_dict = patient.model_dump()
        results = engine.match_patient_to_trials(patient_dict)
        return JSONResponse(
            status_code=200,
            content={"patient_id": patient.patient_id, "matches": results},
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Error matching patient %s", patient.patient_id)
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/trials")
async def list_trials():
    stats = engine.get_statistics()
    trials = []
    for tid in stats["trial_ids"]:
        trial = engine.get_trial_details(tid)
        if trial:
            trials.append(trial)
    return {"total": len(trials), "trials": trials}


@app.get("/api/trials/{trial_id}")
async def get_trial(trial_id: str):
    trial = engine.get_trial_details(trial_id)
    if trial is None:
        raise HTTPException(status_code=404, detail=f"Trial {trial_id} not found")
    return trial


@app.get("/api/search")
async def search_trials(
    condition: str = Query("", description="Condition name or ICD-10 code"),
    location: str = Query("", description="Location substring"),
    phase: str = Query("", description="Trial phase (e.g. Phase 2, Phase 3)"),
):
    results = engine.search_trials(condition=condition, location=location, phase=phase)
    return {"count": len(results), "trials": results}


@app.get("/api/stats")
async def get_stats():
    return engine.get_statistics()


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api.app:app", host="0.0.0.0", port=8087, reload=True)
