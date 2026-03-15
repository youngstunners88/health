"""
Prior Authorization API
FastAPI backend for prior auth management.
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from pathlib import Path
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from healthcare.modules.prior_auth.service.engine import (
    PriorAuthEngine,
    PayerRulesDB,
)

app = FastAPI(title="Prior Authorization System", version="1.0.0")

BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

engine = PriorAuthEngine()
payer_rules = PayerRulesDB()


class AuthRequest(BaseModel):
    patient_id: str
    patient_name: str
    payer_name: str
    procedure: str
    diagnosis_codes: list[str]
    provider_name: str
    provider_npi: str
    clinical_notes: str = ""
    urgency: str = "standard"
    requested_start_date: str = ""


class DecisionRequest(BaseModel):
    auth_id: str
    decision: str
    decision_reason: str = ""
    auth_number: str = ""
    denial_reason: str = ""


class AppealRequest(BaseModel):
    auth_id: str
    appeal_notes: str = ""


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    auths = engine.get_authorizations()
    stats = engine.get_statistics()
    pending = engine.get_pending_auths()
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "auths": auths[:20],
            "stats": stats,
            "pending": pending,
            "payers": payer_rules.get_all_payers(),
        },
    )


@app.get("/new")
async def new_auth_form(request: Request):
    return templates.TemplateResponse(
        "new_auth.html",
        {
            "request": request,
            "payers": payer_rules.get_all_payers(),
        },
    )


@app.get("/auth/{auth_id}")
async def auth_detail(request: Request, auth_id: str):
    auth = engine.get_auth_by_id(auth_id)
    if not auth:
        raise HTTPException(status_code=404, detail="Authorization not found")
    return templates.TemplateResponse(
        "auth_detail.html",
        {
            "request": request,
            "auth": auth,
        },
    )


@app.post("/api/auth")
async def create_auth(req: AuthRequest):
    auth = engine.create_auth_request(**req.model_dump())
    return auth


@app.post("/api/auth/decision")
async def process_decision(req: DecisionRequest):
    auth = engine.process_decision(**req.model_dump())
    return auth


@app.post("/api/auth/appeal")
async def submit_appeal(req: AppealRequest):
    auth = engine.submit_appeal(**req.model_dump())
    return auth


@app.get("/api/auths")
async def api_auths(patient_id: str = None, status: str = None, payer_name: str = None):
    return engine.get_authorizations(
        patient_id=patient_id, status=status, payer_name=payer_name
    )


@app.get("/api/auths/pending")
async def api_pending():
    return engine.get_pending_auths()


@app.get("/api/stats")
async def api_stats():
    return engine.get_statistics()


@app.get("/api/payers")
async def api_payers():
    return payer_rules.get_all_payers()


@app.get("/api/payers/{payer_name}/check")
async def check_payer_auth(payer_name: str, procedure: str):
    needs = payer_rules.needs_prior_auth(payer_name, procedure)
    rules = payer_rules.get_payer_rules(payer_name)
    return {
        "payer": payer_name,
        "procedure": procedure,
        "needs_prior_auth": needs,
        "rules": rules,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8082)
