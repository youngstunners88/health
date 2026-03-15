"""Compliance API - FastAPI server for Healthcare Compliance Layer."""

import logging
import os
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, PlainTextResponse
from pydantic import BaseModel

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from engine.auditor import ComplianceAuditor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("compliance-api")

app = FastAPI(title="Healthcare Compliance API", version="1.0.0")

auditor = ComplianceAuditor()

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "..", "templates")


def _read_template(name):
    path = os.path.join(TEMPLATE_DIR, name)
    with open(path, "r") as f:
        return f.read()


class AuditRequest(BaseModel):
    overrides: dict[str, str] = {}


class AccessLogRequest(BaseModel):
    user: str
    patient_id: str
    action: str
    resource: str
    ip_address: str


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return HTMLResponse(content=_read_template("compliance_dashboard.html"))


@app.post("/api/audit")
async def run_audit(req: AuditRequest = None):
    try:
        overrides = req.overrides if req else {}
        result = auditor.run_audit(overrides=overrides)
        return result
    except Exception as e:
        logger.exception("Failed to run audit")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/score")
async def get_score():
    try:
        return auditor.get_compliance_score()
    except Exception as e:
        logger.exception("Failed to get compliance score")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/gaps")
async def get_gaps():
    try:
        return auditor.get_gap_report()
    except Exception as e:
        logger.exception("Failed to get gap report")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/access-log", status_code=201)
async def log_access(entry: AccessLogRequest):
    try:
        result = auditor.log_access_event(
            user=entry.user,
            patient_id=entry.patient_id,
            action=entry.action,
            resource=entry.resource,
            ip_address=entry.ip_address,
        )
        return result
    except Exception as e:
        logger.exception("Failed to log access event")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/access-log")
async def get_access_log(patient_id: str = "", user: str = "", limit: int = 100):
    try:
        results = auditor.get_access_log(
            patient_id=patient_id or None,
            user=user or None,
            limit=limit,
        )
        return {"entries": results, "total": len(results)}
    except Exception as e:
        logger.exception("Failed to get access log")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/baa-template", response_class=PlainTextResponse)
async def get_baa_template():
    try:
        return auditor.generate_baa_template()
    except Exception as e:
        logger.exception("Failed to get BAA template")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/soc2-checklist")
async def get_soc2_checklist():
    try:
        return auditor.get_soc2_checklist()
    except Exception as e:
        logger.exception("Failed to get SOC 2 checklist")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/fda-guidance")
async def get_fda_guidance():
    try:
        return auditor.get_fda_samd_classification()
    except Exception as e:
        logger.exception("Failed to get FDA guidance")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/hipaa-checks")
async def get_hipaa_checks():
    try:
        from engine.auditor import HIPAA_CHECKS

        return {"total": len(HIPAA_CHECKS), "checks": HIPAA_CHECKS}
    except Exception as e:
        logger.exception("Failed to get HIPAA checks")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8089, log_level="info")
