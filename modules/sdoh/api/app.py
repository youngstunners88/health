"""
SDOH API
FastAPI backend for SDOH screening and referrals.
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from pathlib import Path
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from healthcare.modules.sdoh.service.engine import SDOHEngine

app = FastAPI(title="SDOH Screening & Referrals", version="1.0.0")

BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

engine = SDOHEngine()


class ScreeningRequest(BaseModel):
    patient_id: str
    patient_name: str
    responses: dict
    screened_by: str = "self"
    screening_context: str = "discharge"


class ReferralUpdate(BaseModel):
    referral_id: str
    status: str
    outcome: str = ""


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    stats = engine.get_statistics()
    screenings = engine.get_screenings()
    referrals = engine.get_referrals(status="pending")
    return templates.TemplateResponse(
        "sdoh_dashboard.html",
        {
            "request": request,
            "stats": stats,
            "screenings": screenings[:10],
            "pending_referrals": referrals,
        },
    )


@app.get("/screening/new")
async def new_screening(request: Request):
    questions = engine.get_screening_questions()
    return templates.TemplateResponse(
        "new_screening.html",
        {
            "request": request,
            "questions": questions,
        },
    )


@app.post("/api/screenings")
async def create_screening(req: ScreeningRequest):
    screening = engine.create_screening(**req.model_dump())
    return screening


@app.post("/api/referrals/update")
async def update_referral(req: ReferralUpdate):
    referral = engine.update_referral_status(**req.model_dump())
    return referral


@app.get("/api/screenings")
async def api_screenings(patient_id: str = None):
    return engine.get_screenings(patient_id=patient_id)


@app.get("/api/referrals")
async def api_referrals(patient_id: str = None, status: str = None, domain: str = None):
    return engine.get_referrals(patient_id=patient_id, status=status, domain=domain)


@app.get("/api/stats")
async def api_stats():
    return engine.get_statistics()


@app.get("/api/questions")
async def api_questions():
    return engine.get_screening_questions()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8084)
