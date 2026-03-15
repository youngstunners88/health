"""
Revenue Cycle API
FastAPI backend for claims, charges, and ERA management.
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from pathlib import Path
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from healthcare.modules.revenue_cycle.service.engine import ClaimsEngine

app = FastAPI(title="Revenue Cycle Management", version="1.0.0")

BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

engine = ClaimsEngine()


class ClaimSubmission(BaseModel):
    patient_id: str
    patient_name: str
    patient_dob: str
    patient_mrn: str
    payer_name: str
    payer_id: str
    subscriber_id: str
    provider_name: str
    provider_npi: str
    provider_tax_id: str
    place_of_service: str
    claim_type: str = "professional"
    diagnoses: list[str] = []
    procedures: list[dict] = []
    charge_amount: float = 0.0
    prior_auth_id: str = ""
    notes: str = ""


class EraProcessing(BaseModel):
    claim_id: str
    allowed_amount: float
    paid_amount: float
    patient_responsibility: float
    adjustment_codes: list[dict] = []
    denial_reason: str = ""
    denial_codes: list[str] = []


class AppealSubmission(BaseModel):
    claim_id: str
    appeal_notes: str = ""


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    claims = engine.get_claims()
    stats = engine.get_statistics()
    denials = engine.get_denial_analysis()
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "claims": claims[:20],
            "stats": stats,
            "denials": denials,
        },
    )


@app.get("/new")
async def new_claim_form(request: Request):
    return templates.TemplateResponse("new_claim.html", {"request": request})


@app.get("/claim/{claim_id}")
async def claim_detail(request: Request, claim_id: str):
    claim = engine.get_claim_by_id(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    return templates.TemplateResponse(
        "claim_detail.html",
        {
            "request": request,
            "claim": claim,
        },
    )


@app.post("/api/claims")
async def submit_claim(req: ClaimSubmission):
    claim = engine.submit_claim(**req.model_dump())
    return claim


@app.post("/api/claims/era")
async def process_era(req: EraProcessing):
    claim = engine.process_era(**req.model_dump())
    return claim


@app.post("/api/claims/appeal")
async def submit_appeal(req: AppealSubmission):
    claim = engine.submit_claim_appeal(**req.model_dump())
    return claim


@app.get("/api/claims")
async def api_claims(
    patient_id: str = None, status: str = None, payer_name: str = None
):
    return engine.get_claims(
        patient_id=patient_id, status=status, payer_name=payer_name
    )


@app.get("/api/stats")
async def api_stats():
    return engine.get_statistics()


@app.get("/api/denials")
async def api_denials():
    return engine.get_denial_analysis()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8083)
