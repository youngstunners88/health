"""
Notification Service API - FastAPI server with endpoints for sending,
scheduling, history, statistics, and Twilio webhooks.
"""

import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from engine.messaging import NotificationEngine, DeliveryStatus

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"

engine: Optional[NotificationEngine] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global engine
    engine = NotificationEngine(
        account_sid=os.getenv("TWILIO_ACCOUNT_SID"),
        auth_token=os.getenv("TWILIO_AUTH_TOKEN"),
        from_phone=os.getenv("TWILIO_FROM_PHONE"),
        from_whatsapp=os.getenv("TWILIO_WHATSAPP_PHONE"),
        mock_mode=os.getenv("NOTIFICATION_MOCK_MODE", "true").lower() == "true",
        max_retries=int(os.getenv("NOTIFICATION_MAX_RETRIES", "3")),
        retry_delay_seconds=int(os.getenv("NOTIFICATION_RETRY_DELAY", "30")),
        app_name=os.getenv("APP_NAME", "HealthCare Portal"),
    )
    logger.info("Notification engine started")
    yield
    if engine:
        engine.shutdown()
        logger.info("Notification engine stopped")


app = FastAPI(
    title="Notification Service",
    description="SMS/WhatsApp notification service for healthcare",
    version="1.0.0",
    lifespan=lifespan,
)

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


# --- Request Models ---


class SendRequest(BaseModel):
    patient_id: str = Field(..., min_length=1)
    phone: str = Field(..., min_length=7)
    message: str = Field(..., min_length=1, max_length=1600)
    channel: str = Field(default="sms", pattern="^(sms|whatsapp)$")
    msg_type: str = Field(default="manual", max_length=50)


class ScheduleRequest(BaseModel):
    patient_id: str = Field(..., min_length=1)
    reminder_type: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)
    phone: str = Field(..., min_length=7)
    cron: str = Field(..., min_length=1)
    channel: str = Field(default="sms", pattern="^(sms|whatsapp)$")
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    patient_name: Optional[str] = None


class MedicationReminderRequest(BaseModel):
    patient_id: str = Field(..., min_length=1)
    phone: str = Field(..., min_length=7)
    patient_name: Optional[str] = None
    medications: list[dict] = Field(..., min_length=1)
    cron: str = Field(..., min_length=1)
    channel: str = Field(default="sms", pattern="^(sms|whatsapp)$")
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class AppointmentReminderRequest(BaseModel):
    patient_id: str = Field(..., min_length=1)
    phone: str = Field(..., min_length=7)
    patient_name: Optional[str] = None
    date: str
    time: str
    provider: str
    hours_before: int = Field(default=24, ge=1, le=168)
    channel: str = Field(default="sms", pattern="^(sms|whatsapp)$")


class SymptomCheckinRequest(BaseModel):
    patient_id: str = Field(..., min_length=1)
    phone: str = Field(..., min_length=7)
    patient_name: Optional[str] = None
    cron: str = Field(..., min_length=1)
    channel: str = Field(default="sms", pattern="^(sms|whatsapp)$")
    start_date: Optional[str] = None
    end_date: Optional[str] = None


# --- Endpoints ---


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse(
        "notifications_dashboard.html", {"request": request}
    )


@app.get("/schedule", response_class=HTMLResponse)
async def schedule_page(request: Request):
    return templates.TemplateResponse(
        "notification_schedule.html", {"request": request}
    )


@app.post("/api/send")
async def send_notification(req: SendRequest):
    if engine is None:
        raise HTTPException(
            status_code=503, detail="Notification engine not initialized"
        )

    try:
        if req.channel == "whatsapp":
            result = engine.send_whatsapp(
                phone=req.phone,
                message=req.message,
                patient_id=req.patient_id,
                msg_type=req.msg_type,
            )
        else:
            result = engine.send_sms(
                phone=req.phone,
                message=req.message,
                patient_id=req.patient_id,
                msg_type=req.msg_type,
            )

        if result["success"]:
            return JSONResponse(
                status_code=200,
                content={
                    "status": "success",
                    "notification_id": result["notification_id"],
                    "channel": result["channel"],
                    "message_sid": result.get("message_sid"),
                },
            )
        else:
            return JSONResponse(
                status_code=502,
                content={
                    "status": "failed",
                    "error": result.get("error", "unknown error"),
                },
            )
    except Exception as e:
        logger.error("Send notification failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/schedule")
async def schedule_notification(req: ScheduleRequest):
    if engine is None:
        raise HTTPException(
            status_code=503, detail="Notification engine not initialized"
        )

    try:
        schedule = {
            "cron": req.cron,
            "phone": req.phone,
            "patient_name": req.patient_name or "",
        }
        if req.start_date:
            schedule["start_date"] = req.start_date
        if req.end_date:
            schedule["end_date"] = req.end_date

        result = engine.schedule_reminder(
            patient_id=req.patient_id,
            reminder_type=req.reminder_type,
            message=req.message,
            schedule=schedule,
            channel=req.channel,
        )

        return JSONResponse(status_code=201, content={"status": "scheduled", **result})
    except Exception as e:
        logger.error("Schedule notification failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/schedule/medication")
async def schedule_medication(req: MedicationReminderRequest):
    if engine is None:
        raise HTTPException(
            status_code=503, detail="Notification engine not initialized"
        )

    try:
        schedule = {
            "cron": req.cron,
            "phone": req.phone,
            "patient_name": req.patient_name or "Patient",
        }
        if req.start_date:
            schedule["start_date"] = req.start_date
        if req.end_date:
            schedule["end_date"] = req.end_date

        result = engine.medication_reminder(
            patient_id=req.patient_id,
            medications=req.medications,
            schedule=schedule,
            channel=req.channel,
        )

        return JSONResponse(status_code=201, content={"status": "scheduled", **result})
    except Exception as e:
        logger.error("Schedule medication reminder failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/schedule/appointment")
async def schedule_appointment(req: AppointmentReminderRequest):
    if engine is None:
        raise HTTPException(
            status_code=503, detail="Notification engine not initialized"
        )

    try:
        appointment = {
            "date": req.date,
            "time": req.time,
            "provider": req.provider,
            "phone": req.phone,
            "patient_name": req.patient_name or "Patient",
        }

        result = engine.appointment_reminder(
            patient_id=req.patient_id,
            appointment=appointment,
            hours_before=req.hours_before,
            channel=req.channel,
        )

        return JSONResponse(status_code=201, content={"status": "scheduled", **result})
    except Exception as e:
        logger.error("Schedule appointment reminder failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/schedule/symptom-checkin")
async def schedule_symptom_checkin(req: SymptomCheckinRequest):
    if engine is None:
        raise HTTPException(
            status_code=503, detail="Notification engine not initialized"
        )

    try:
        schedule = {
            "cron": req.cron,
            "phone": req.phone,
            "patient_name": req.patient_name or "Patient",
        }
        if req.start_date:
            schedule["start_date"] = req.start_date
        if req.end_date:
            schedule["end_date"] = req.end_date

        result = engine.symptom_checkin_prompt(
            patient_id=req.patient_id,
            schedule=schedule,
            channel=req.channel,
        )

        return JSONResponse(status_code=201, content={"status": "scheduled", **result})
    except Exception as e:
        logger.error("Schedule symptom checkin failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/history")
async def get_history(patient_id: Optional[str] = None, limit: int = 50):
    if engine is None:
        raise HTTPException(
            status_code=503, detail="Notification engine not initialized"
        )

    if patient_id:
        history = engine.get_notification_history(patient_id, limit)
    else:
        history = engine._history[-limit:]

    return JSONResponse(content={"history": history, "count": len(history)})


@app.get("/api/stats")
async def get_stats():
    if engine is None:
        raise HTTPException(
            status_code=503, detail="Notification engine not initialized"
        )

    return JSONResponse(content=engine.get_statistics())


@app.get("/api/schedules")
async def get_schedules(patient_id: Optional[str] = None):
    if engine is None:
        raise HTTPException(
            status_code=503, detail="Notification engine not initialized"
        )

    schedules = engine.get_schedules(patient_id)
    return JSONResponse(content={"schedules": schedules, "count": len(schedules)})


@app.delete("/api/schedules/{schedule_id}")
async def cancel_schedule(schedule_id: str):
    if engine is None:
        raise HTTPException(
            status_code=503, detail="Notification engine not initialized"
        )

    if engine.cancel_schedule(schedule_id):
        return JSONResponse(content={"status": "cancelled", "schedule_id": schedule_id})
    raise HTTPException(status_code=404, detail="Schedule not found")


@app.post("/webhook/twilio")
async def twilio_webhook(request: Request):
    """Handle delivery status callbacks from Twilio."""
    try:
        form_data = await request.form()
        message_sid = form_data.get("MessageSid", "")
        status = form_data.get("MessageStatus", "")
        error_code = form_data.get("ErrorCode", "")

        logger.info(
            "Twilio webhook: sid=%s status=%s error_code=%s",
            message_sid,
            status,
            error_code,
        )

        if engine:
            with engine._lock:
                for h in engine._history:
                    if h.get("message_sid") == message_sid:
                        if status in ("delivered", "read"):
                            h["status"] = DeliveryStatus.DELIVERED
                            h["delivered_at"] = datetime.utcnow().isoformat()
                        elif status in ("failed", "undelivered"):
                            h["status"] = DeliveryStatus.FAILED
                        engine._persist_history()
                        break

        return JSONResponse(content={"status": "ok"})
    except Exception as e:
        logger.error("Twilio webhook error: %s", e)
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/health")
async def health_check():
    return JSONResponse(
        content={
            "status": "healthy",
            "mock_mode": engine.mock_mode if engine else None,
            "timestamp": datetime.utcnow().isoformat(),
        }
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api.app:app",
        host="0.0.0.0",
        port=8086,
        reload=True,
        log_level="info",
    )
