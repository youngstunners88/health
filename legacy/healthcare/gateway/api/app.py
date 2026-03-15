"""
API Gateway - Unified entry point for all healthcare services.
Routes requests to the appropriate service and aggregates responses.
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pathlib import Path
import httpx
import json
import asyncio
from datetime import datetime, timezone

app = FastAPI(title="Healthcare Platform Gateway", version="1.0.0")

BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Service URLs
SERVICES = {
    "patient_portal": "http://localhost:8080",
    "care_dashboard": "http://localhost:8081",
    "prior_auth": "http://localhost:8082",
    "revenue_cycle": "http://localhost:8083",
}


class ServiceStatus(BaseModel):
    name: str
    url: str
    status: str
    response_time_ms: float = 0


async def check_service(name: str, url: str) -> dict:
    """Check if a service is healthy."""
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            start = datetime.now(timezone.utc)
            resp = await client.get(f"{url}/")
            elapsed = (datetime.now(timezone.utc) - start).total_seconds() * 1000
            return {
                "name": name,
                "url": url,
                "status": "healthy" if resp.status_code == 200 else "degraded",
                "response_time_ms": round(elapsed, 1),
                "status_code": resp.status_code,
            }
    except Exception as e:
        return {
            "name": name,
            "url": url,
            "status": "unhealthy",
            "response_time_ms": 0,
            "error": str(e),
        }


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("gateway.html", {"request": request})


@app.get("/health")
async def health():
    """Check health of all services in parallel."""
    tasks = [check_service(name, url) for name, url in SERVICES.items()]
    results = await asyncio.gather(*tasks)

    all_healthy = all(r["status"] == "healthy" for r in results)
    return {
        "status": "healthy" if all_healthy else "degraded",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "services": results,
    }


@app.get("/api/patient/{patient_id}/full-record")
async def get_full_patient_record(patient_id: str):
    """Aggregate all data for a patient across all services."""
    async with httpx.AsyncClient(timeout=10) as client:
        tasks = {
            "patient_portal": client.get(
                f"{SERVICES['patient_portal']}/api/patient/{patient_id}"
            ),
            "care_dashboard": client.get(
                f"{SERVICES['care_dashboard']}/api/patient/{patient_id}"
            ),
            "prior_auth": client.get(
                f"{SERVICES['prior_auth']}/api/auths", params={"patient_id": patient_id}
            ),
            "revenue_cycle": client.get(
                f"{SERVICES['revenue_cycle']}/api/claims",
                params={"patient_id": patient_id},
            ),
        }

        results = await asyncio.gather(*tasks.values(), return_exceptions=True)

    record = {
        "patient_id": patient_id,
        "aggregated_at": datetime.now(timezone.utc).isoformat(),
    }
    for key, result in zip(tasks.keys(), results):
        if isinstance(result, Exception):
            record[key] = {"error": str(result)}
        elif result.status_code == 200:
            record[key] = result.json()
        else:
            record[key] = {"error": f"HTTP {result.status_code}"}

    return record


@app.get("/api/overview")
async def overview():
    """Get aggregated overview from all services."""
    async with httpx.AsyncClient(timeout=10) as client:
        tasks = {
            "care_dashboard_stats": client.get(
                f"{SERVICES['care_dashboard']}/api/patients"
            ),
            "prior_auth_stats": client.get(f"{SERVICES['prior_auth']}/api/stats"),
            "revenue_cycle_stats": client.get(f"{SERVICES['revenue_cycle']}/api/stats"),
        }

        results = await asyncio.gather(*tasks.values(), return_exceptions=True)

    overview_data = {"timestamp": datetime.now(timezone.utc).isoformat()}
    for key, result in zip(tasks.keys(), results):
        if isinstance(result, Exception):
            overview_data[key] = {"error": str(result)}
        elif result.status_code == 200:
            overview_data[key] = result.json()
        else:
            overview_data[key] = {"error": f"HTTP {result.status_code}"}

    return overview_data


@app.post("/api/discharge-pipeline")
async def run_discharge_pipeline(data: dict):
    """Run the full discharge pipeline end-to-end."""
    patient_id = data.get("patient_id", "pipeline-demo")

    results = {
        "patient_id": patient_id,
        "steps": [],
        "started_at": datetime.now(timezone.utc).isoformat(),
    }

    async with httpx.AsyncClient(timeout=30) as client:
        pipeline_steps = [
            (
                "intake",
                f"{SERVICES['care_dashboard']}/api/patient/{patient_id}",
                "GET",
                None,
            ),
            (
                "risk_assessment",
                f"{SERVICES['care_dashboard']}/api/patient/{patient_id}",
                "GET",
                None,
            ),
            (
                "prior_auth_check",
                f"{SERVICES['prior_auth']}/api/payers/BlueCross BlueShield/check",
                "GET",
                {"procedure": "Home Health"},
            ),
            (
                "claims_submission",
                f"{SERVICES['revenue_cycle']}/api/claims",
                "POST",
                {
                    "patient_id": patient_id,
                    "patient_name": data.get("patient_name", "Demo Patient"),
                    "patient_dob": "1960-01-01",
                    "patient_mrn": f"MRN-{patient_id}",
                    "payer_name": "BlueCross BlueShield",
                    "payer_id": "BCBS",
                    "subscriber_id": f"SUB-{patient_id}",
                    "provider_name": "Dr. Smith",
                    "provider_npi": "1234567890",
                    "provider_tax_id": "12-3456789",
                    "place_of_service": "21",
                    "charge_amount": data.get("charge_amount", 5000.0),
                    "diagnoses": data.get("diagnoses", ["I50.9", "E11.9"]),
                    "procedures": data.get(
                        "procedures",
                        [
                            {
                                "code": "99213",
                                "modifier": "",
                                "units": 1,
                                "charge": 500.0,
                            }
                        ],
                    ),
                },
            ),
        ]

        for step_name, url, method, payload in pipeline_steps:
            try:
                if method == "GET":
                    resp = (
                        await client.get(url, params=payload)
                        if payload
                        else await client.get(url)
                    )
                else:
                    resp = await client.post(url, json=payload)

                results["steps"].append(
                    {
                        "step": step_name,
                        "status": "success" if resp.status_code < 400 else "failed",
                        "status_code": resp.status_code,
                    }
                )
            except Exception as e:
                results["steps"].append(
                    {
                        "step": step_name,
                        "status": "error",
                        "error": str(e),
                    }
                )

    results["completed_at"] = datetime.now(timezone.utc).isoformat()
    return results


# Proxy endpoints to individual services
@app.api_route("/portal/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_portal(request: Request, path: str):
    return await proxy_to_service("patient_portal", path, request)


@app.api_route("/dashboard/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_dashboard(request: Request, path: str):
    return await proxy_to_service("care_dashboard", path, request)


@app.api_route("/prior-auth/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_prior_auth(request: Request, path: str):
    return await proxy_to_service("prior_auth", path, request)


@app.api_route("/revenue/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_revenue(request: Request, path: str):
    return await proxy_to_service("revenue_cycle", path, request)


async def proxy_to_service(service_name: str, path: str, request: Request):
    """Proxy a request to a specific service."""
    service_url = SERVICES.get(service_name)
    if not service_url:
        raise HTTPException(status_code=502, detail=f"Service {service_name} not found")

    target_url = f"{service_url}/{path}"

    async with httpx.AsyncClient(timeout=30) as client:
        try:
            body = (
                await request.body()
                if request.method in ("POST", "PUT", "PATCH")
                else None
            )
            resp = await client.request(
                method=request.method,
                url=target_url,
                headers=dict(request.headers),
                content=body,
                params=request.query_params,
            )

            return JSONResponse(
                content=resp.json()
                if resp.headers.get("content-type", "").startswith("application/json")
                else resp.text,
                status_code=resp.status_code,
            )
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Service error: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
