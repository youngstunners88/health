"""
Wearable/IoT API
FastAPI backend for device management and data ingestion.
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from pathlib import Path
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from healthcare.modules.wearables.service.engine import WearableEngine, DEVICE_TYPES

app = FastAPI(title="Wearable/IoT Integration", version="1.0.0")

BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

engine = WearableEngine()


class DeviceRegistration(BaseModel):
    patient_id: str
    patient_name: str
    device_type: str
    device_name: str = ""
    device_id: str = ""
    connection_config: dict = {}


class ReadingIngestion(BaseModel):
    device_id: str
    patient_id: str
    readings: list[dict]
    source: str = "device"


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    stats = engine.get_statistics()
    return templates.TemplateResponse(
        "wearables_dashboard.html",
        {
            "request": request,
            "stats": stats,
            "device_types": DEVICE_TYPES,
        },
    )


@app.get("/device/{device_id}")
async def device_detail(request: Request, device_id: str):
    try:
        status = engine.get_device_status(device_id)
        readings = engine.get_readings(
            patient_id=status["patient_id"], device_id=device_id, hours=24
        )
        return templates.TemplateResponse(
            "device_detail.html",
            {
                "request": request,
                "device": status,
                "readings": readings[-50:],
            },
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/api/devices")
async def register_device(req: DeviceRegistration):
    device = engine.register_device(**req.model_dump())
    return device


@app.post("/api/readings")
async def ingest_readings(req: ReadingIngestion):
    result = engine.ingest_readings(**req.model_dump())
    return result


@app.post("/api/devices/{device_id}/sync")
async def sync_device(device_id: str, data: dict = None):
    try:
        result = engine.sync_device(device_id, data)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/api/devices")
async def api_devices(patient_id: str = None):
    if patient_id:
        return engine.get_patient_devices(patient_id)
    return engine.devices


@app.get("/api/devices/{device_id}")
async def api_device_status(device_id: str):
    try:
        return engine.get_device_status(device_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/api/readings")
async def api_readings(
    patient_id: str, metric: str = None, device_id: str = None, hours: int = 24
):
    return engine.get_readings(
        patient_id=patient_id, metric=metric, device_id=device_id, hours=hours
    )


@app.get("/api/stats")
async def api_stats():
    return engine.get_statistics()


@app.get("/api/device-types")
async def api_device_types():
    return DEVICE_TYPES


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8085)
