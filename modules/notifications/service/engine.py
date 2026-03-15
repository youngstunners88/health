"""
Notification Engine - Core messaging service with Twilio integration,
mock fallback, scheduling, delivery tracking, and retry logic.
"""

import json
import logging
import os
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from threading import Lock, Thread
from typing import Any, Optional

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

HISTORY_FILE = DATA_DIR / "notification_history.json"
STATS_FILE = DATA_DIR / "notification_stats.json"
SCHEDULES_FILE = DATA_DIR / "schedules.json"
DELIVERY_LOG_FILE = DATA_DIR / "delivery_log.json"

TEMPLATES = {
    "medication_reminder": "Hi {name}, time to take your medication: {medications}. "
    "Reply OK when done. - {app_name}",
    "appointment_reminder": "Hi {name}, reminder: you have an appointment on {date} at {time} "
    "with {provider}. Reply C to confirm. - {app_name}",
    "symptom_checkin": "Hi {name}, please reply with your current symptoms or type 'all clear' "
    "if you're feeling well. - {app_name}",
    "alert": "ALERT: {message}. Please contact your care team if needed. - {app_name}",
    "welcome": "Welcome to {app_name}, {name}! You'll receive medication reminders, "
    "appointment alerts, and symptom check-ins. Reply STOP to opt out.",
}


class DeliveryStatus:
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRYING = "retrying"


class NotificationEngine:
    """Core notification engine with Twilio integration, mock fallback,
    scheduling, delivery tracking, and retry logic."""

    def __init__(
        self,
        account_sid: Optional[str] = None,
        auth_token: Optional[str] = None,
        from_phone: Optional[str] = None,
        from_whatsapp: Optional[str] = None,
        mock_mode: bool = False,
        max_retries: int = 3,
        retry_delay_seconds: int = 30,
        app_name: str = "HealthCare Portal",
    ):
        self.account_sid = account_sid or os.getenv("TWILIO_ACCOUNT_SID", "")
        self.auth_token = auth_token or os.getenv("TWILIO_AUTH_TOKEN", "")
        self.from_phone = from_phone or os.getenv("TWILIO_FROM_PHONE", "+15551234567")
        self.from_whatsapp = from_whatsapp or os.getenv(
            "TWILIO_WHATSAPP_PHONE", "whatsapp:+15551234567"
        )
        self.mock_mode = mock_mode or not (self.account_sid and self.auth_token)
        self.max_retries = max_retries
        self.retry_delay_seconds = retry_delay_seconds
        self.app_name = app_name

        self._twilio_client = None
        self._lock = Lock()
        self._scheduler_thread = None
        self._running = False

        self._init_twilio()
        self._load_data()
        self._start_scheduler()

        logger.info(
            "NotificationEngine initialized (mode=%s)",
            "mock" if self.mock_mode else "twilio",
        )

    def _init_twilio(self):
        if not self.mock_mode:
            try:
                from twilio.rest import Client

                self._twilio_client = Client(self.account_sid, self.auth_token)
                logger.info("Twilio client initialized successfully")
            except ImportError:
                logger.warning(
                    "twilio package not installed, falling back to mock mode"
                )
                self.mock_mode = True
            except Exception as e:
                logger.error("Failed to initialize Twilio client: %s", e)
                self.mock_mode = True

    def _load_data(self):
        with self._lock:
            self._history = self._load_json(HISTORY_FILE, [])
            self._stats = self._load_json(
                STATS_FILE,
                {
                    "total_sent": 0,
                    "total_delivered": 0,
                    "total_failed": 0,
                    "total_retries": 0,
                    "by_type": {},
                    "by_channel": {"sms": 0, "whatsapp": 0},
                },
            )
            self._schedules = self._load_json(SCHEDULES_FILE, [])
            self._delivery_log = self._load_json(DELIVERY_LOG_FILE, [])

    def _load_json(self, path: Path, default: Any) -> Any:
        try:
            if path.exists():
                with open(path, "r") as f:
                    return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error("Failed to load %s: %s", path, e)
        return default

    def _save_json(self, path: Path, data: Any):
        try:
            tmp_path = path.with_suffix(".tmp")
            with open(tmp_path, "w") as f:
                json.dump(data, f, indent=2, default=str)
            tmp_path.replace(path)
        except IOError as e:
            logger.error("Failed to save %s: %s", path, e)

    def _persist_history(self):
        self._save_json(HISTORY_FILE, self._history[-10000:])

    def _persist_stats(self):
        self._save_json(STATS_FILE, self._stats)

    def _persist_schedules(self):
        self._save_json(SCHEDULES_FILE, self._schedules)

    def _persist_delivery_log(self):
        self._save_json(DELIVERY_LOG_FILE, self._delivery_log[-5000:])

    def _update_stats(self, channel: str, msg_type: str, status: str):
        self._stats["total_sent"] += 1
        if status == DeliveryStatus.DELIVERED:
            self._stats["total_delivered"] += 1
        elif status == DeliveryStatus.FAILED:
            self._stats["total_failed"] += 1
        self._stats["by_channel"][channel] = (
            self._stats["by_channel"].get(channel, 0) + 1
        )
        if msg_type not in self._stats["by_type"]:
            self._stats["by_type"][msg_type] = {
                "sent": 0,
                "delivered": 0,
                "failed": 0,
            }
        self._stats["by_type"][msg_type]["sent"] += 1
        if status == DeliveryStatus.DELIVERED:
            self._stats["by_type"][msg_type]["delivered"] += 1
        elif status == DeliveryStatus.FAILED:
            self._stats["by_type"][msg_type]["failed"] += 1
        self._persist_stats()

    def _record_delivery(self, notification_id: str, status: str, details: str = ""):
        entry = {
            "notification_id": notification_id,
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
            "details": details,
        }
        self._delivery_log.append(entry)
        self._persist_delivery_log()

    def _send_via_twilio(self, to_phone: str, message: str, channel: str) -> dict:
        if self.mock_mode or self._twilio_client is None:
            return self._send_mock(to_phone, message, channel)

        try:
            from_number = (
                self.from_whatsapp if channel == "whatsapp" else self.from_phone
            )
            if channel == "whatsapp" and not to_phone.startswith("whatsapp:"):
                to_phone = f"whatsapp:{to_phone}"

            msg = self._twilio_client.messages.create(
                body=message,
                from_=from_number,
                to=to_phone,
            )
            return {
                "success": True,
                "message_sid": msg.sid,
                "status": msg.status,
                "channel": channel,
            }
        except Exception as e:
            logger.error("Twilio send failed (%s): %s", channel, e)
            return {
                "success": False,
                "error": str(e),
                "channel": channel,
            }

    def _send_mock(self, to_phone: str, message: str, channel: str) -> dict:
        sid = f"SM{uuid.uuid4().hex[:32]}"
        logger.info(
            "[MOCK %s] To: %s | Message: %s",
            channel.upper(),
            to_phone,
            message[:100],
        )
        return {
            "success": True,
            "message_sid": sid,
            "status": "sent",
            "channel": channel,
            "mock": True,
        }

    def _send_with_retry(
        self, to_phone: str, message: str, channel: str, notification_id: str
    ) -> dict:
        for attempt in range(1, self.max_retries + 1):
            result = self._send_via_twilio(to_phone, message, channel)
            if result["success"]:
                self._record_delivery(
                    notification_id,
                    DeliveryStatus.SENT,
                    f"sid={result.get('message_sid')}",
                )
                return result
            else:
                self._record_delivery(
                    notification_id,
                    DeliveryStatus.RETRYING
                    if attempt < self.max_retries
                    else DeliveryStatus.FAILED,
                    f"attempt={attempt}/{self.max_retries} error={result.get('error')}",
                )
                self._stats["total_retries"] += 1
                if attempt < self.max_retries:
                    logger.warning(
                        "Retry %d/%d for notification %s",
                        attempt,
                        self.max_retries,
                        notification_id,
                    )
                    time.sleep(self.retry_delay_seconds)

        self._record_delivery(
            notification_id, DeliveryStatus.FAILED, "max retries exceeded"
        )
        return {"success": False, "error": "max retries exceeded", "channel": channel}

    def send_sms(
        self,
        phone: str,
        message: str,
        patient_id: str,
        msg_type: str = "manual",
    ) -> dict:
        notification_id = str(uuid.uuid4())
        record = {
            "id": notification_id,
            "patient_id": patient_id,
            "channel": "sms",
            "phone": phone,
            "message": message,
            "type": msg_type,
            "status": DeliveryStatus.PENDING,
            "created_at": datetime.utcnow().isoformat(),
            "delivered_at": None,
            "retries": 0,
        }

        with self._lock:
            self._history.append(record)
            self._persist_history()

        result = self._send_with_retry(phone, message, "sms", notification_id)
        status = (
            DeliveryStatus.DELIVERED if result["success"] else DeliveryStatus.FAILED
        )

        with self._lock:
            for h in self._history:
                if h["id"] == notification_id:
                    h["status"] = status
                    h["delivered_at"] = (
                        datetime.utcnow().isoformat() if result["success"] else None
                    )
                    h["message_sid"] = result.get("message_sid")
                    h["retries"] = self.max_retries - 1 if not result["success"] else 0
                    break
            self._persist_history()
            self._update_stats("sms", msg_type, status)

        return {
            "notification_id": notification_id,
            "success": result["success"],
            "status": status,
            "channel": "sms",
            "message_sid": result.get("message_sid"),
        }

    def send_whatsapp(
        self,
        phone: str,
        message: str,
        patient_id: str,
        msg_type: str = "manual",
    ) -> dict:
        notification_id = str(uuid.uuid4())
        record = {
            "id": notification_id,
            "patient_id": patient_id,
            "channel": "whatsapp",
            "phone": phone,
            "message": message,
            "type": msg_type,
            "status": DeliveryStatus.PENDING,
            "created_at": datetime.utcnow().isoformat(),
            "delivered_at": None,
            "retries": 0,
        }

        with self._lock:
            self._history.append(record)
            self._persist_history()

        result = self._send_with_retry(phone, message, "whatsapp", notification_id)
        status = (
            DeliveryStatus.DELIVERED if result["success"] else DeliveryStatus.FAILED
        )

        with self._lock:
            for h in self._history:
                if h["id"] == notification_id:
                    h["status"] = status
                    h["delivered_at"] = (
                        datetime.utcnow().isoformat() if result["success"] else None
                    )
                    h["message_sid"] = result.get("message_sid")
                    h["retries"] = self.max_retries - 1 if not result["success"] else 0
                    break
            self._persist_history()
            self._update_stats("whatsapp", msg_type, status)

        return {
            "notification_id": notification_id,
            "success": result["success"],
            "status": status,
            "channel": "whatsapp",
            "message_sid": result.get("message_sid"),
        }

    def schedule_reminder(
        self,
        patient_id: str,
        reminder_type: str,
        message: str,
        schedule: dict,
        channel: str = "sms",
    ) -> dict:
        """
        Schedule a recurring notification.
        schedule: {
            "cron": "0 8 * * *",        # cron expression (minute hour day month weekday)
            "start_date": "2024-01-01",  # optional
            "end_date": "2024-12-31",    # optional
            "phone": "+15559876543",     # required
            "enabled": true
        }
        """
        schedule_id = str(uuid.uuid4())
        entry = {
            "id": schedule_id,
            "patient_id": patient_id,
            "type": reminder_type,
            "message": message,
            "channel": channel,
            "schedule": schedule,
            "enabled": schedule.get("enabled", True),
            "created_at": datetime.utcnow().isoformat(),
            "last_triggered": None,
            "next_trigger": None,
        }

        with self._lock:
            self._schedules.append(entry)
            self._persist_schedules()

        logger.info(
            "Scheduled reminder %s for patient %s (type=%s, cron=%s)",
            schedule_id,
            patient_id,
            reminder_type,
            schedule.get("cron"),
        )

        return {
            "schedule_id": schedule_id,
            "patient_id": patient_id,
            "type": reminder_type,
            "channel": channel,
            "cron": schedule.get("cron"),
            "enabled": True,
        }

    def medication_reminder(
        self,
        patient_id: str,
        medications: list[dict],
        schedule: dict,
        channel: str = "sms",
    ) -> dict:
        """
        Schedule medication reminders.
        medications: [{"name": "Metformin", "dose": "500mg"}, ...]
        """
        med_list = ", ".join(f"{m['name']} ({m['dose']})" for m in medications)
        phone = schedule.get("phone", "")
        name = schedule.get("patient_name", "Patient")

        message = TEMPLATES["medication_reminder"].format(
            name=name,
            medications=med_list,
            app_name=self.app_name,
        )

        return self.schedule_reminder(
            patient_id=patient_id,
            reminder_type="medication_reminder",
            message=message,
            schedule=schedule,
            channel=channel,
        )

    def appointment_reminder(
        self,
        patient_id: str,
        appointment: dict,
        hours_before: int = 24,
        channel: str = "sms",
    ) -> dict:
        """
        Schedule an appointment reminder.
        appointment: {
            "date": "2024-06-15",
            "time": "10:00",
            "provider": "Dr. Smith",
            "phone": "+15559876543",
            "patient_name": "John"
        }
        """
        name = appointment.get("patient_name", "Patient")
        phone = appointment.get("phone", "")
        appt_date = appointment.get("date", "TBD")
        appt_time = appointment.get("time", "TBD")
        provider = appointment.get("provider", "your provider")

        message = TEMPLATES["appointment_reminder"].format(
            name=name,
            date=appt_date,
            time=appt_time,
            provider=provider,
            app_name=self.app_name,
        )

        try:
            appt_dt = datetime.strptime(f"{appt_date} {appt_time}", "%Y-%m-%d %H:%M")
            reminder_dt = appt_dt - timedelta(hours=hours_before)
            cron_expr = f"{reminder_dt.minute} {reminder_dt.hour} {reminder_dt.day} {reminder_dt.month} *"
        except (ValueError, TypeError):
            cron_expr = "0 8 * * *"
            logger.warning("Invalid appointment datetime, using default cron")

        schedule = {
            "cron": cron_expr,
            "phone": phone,
            "patient_name": name,
            "start_date": datetime.utcnow().strftime("%Y-%m-%d"),
            "end_date": appt_date,
            "one_time": True,
        }

        return self.schedule_reminder(
            patient_id=patient_id,
            reminder_type="appointment_reminder",
            message=message,
            schedule=schedule,
            channel=channel,
        )

    def symptom_checkin_prompt(
        self,
        patient_id: str,
        schedule: dict,
        channel: str = "sms",
    ) -> dict:
        """Schedule recurring symptom check-in prompts."""
        name = schedule.get("patient_name", "Patient")
        phone = schedule.get("phone", "")

        message = TEMPLATES["symptom_checkin"].format(
            name=name,
            app_name=self.app_name,
        )

        return self.schedule_reminder(
            patient_id=patient_id,
            reminder_type="symptom_checkin",
            message=message,
            schedule=schedule,
            channel=channel,
        )

    def get_notification_history(self, patient_id: str, limit: int = 50) -> list[dict]:
        with self._lock:
            patient_history = [
                h for h in reversed(self._history) if h["patient_id"] == patient_id
            ]
        return patient_history[:limit]

    def get_statistics(self) -> dict:
        with self._lock:
            total = self._stats["total_sent"]
            delivered = self._stats["total_delivered"]
            failed = self._stats["total_failed"]
            return {
                "total_sent": total,
                "total_delivered": delivered,
                "total_failed": failed,
                "total_retries": self._stats["total_retries"],
                "delivery_rate": round(delivered / total * 100, 2) if total > 0 else 0,
                "by_channel": dict(self._stats["by_channel"]),
                "by_type": dict(self._stats["by_type"]),
                "active_schedules": sum(1 for s in self._schedules if s.get("enabled")),
                "total_schedules": len(self._schedules),
            }

    def cancel_schedule(self, schedule_id: str) -> bool:
        with self._lock:
            for s in self._schedules:
                if s["id"] == schedule_id:
                    s["enabled"] = False
                    self._persist_schedules()
                    logger.info("Cancelled schedule %s", schedule_id)
                    return True
        return False

    def get_schedules(self, patient_id: Optional[str] = None) -> list[dict]:
        with self._lock:
            if patient_id:
                return [s for s in self._schedules if s["patient_id"] == patient_id]
            return list(self._schedules)

    def _parse_cron(self, cron_expr: str, now: datetime) -> bool:
        """Minimal cron parser: 'minute hour day month weekday'."""
        try:
            parts = cron_expr.strip().split()
            if len(parts) != 5:
                return False
            c_min, c_hour, c_day, c_month, c_dow = parts

            def match(field: str, value: int) -> bool:
                if field == "*":
                    return True
                if "," in field:
                    return str(value) in field.split(",")
                if "-" in field:
                    start, end = field.split("-")
                    return int(start) <= value <= int(end)
                if "/" in field:
                    base, step = field.split("/")
                    if base == "*":
                        return value % int(step) == 0
                    return value >= int(base) and (value - int(base)) % int(step) == 0
                return int(field) == value

            return (
                match(c_min, now.minute)
                and match(c_hour, now.hour)
                and match(c_day, now.day)
                and match(c_month, now.month)
                and match(c_dow, now.weekday())
            )
        except Exception:
            return False

    def _check_schedules(self):
        now = datetime.utcnow()
        triggered = []

        with self._lock:
            for s in self._schedules:
                if not s.get("enabled"):
                    continue
                cron_expr = s.get("schedule", {}).get("cron")
                if not cron_expr:
                    continue

                start_date = s.get("schedule", {}).get("start_date")
                end_date = s.get("schedule", {}).get("end_date")
                if start_date and now.strftime("%Y-%m-%d") < start_date:
                    continue
                if end_date and now.strftime("%Y-%m-%d") > end_date:
                    continue

                if self._parse_cron(cron_expr, now):
                    last = s.get("last_triggered")
                    if last:
                        last_dt = datetime.fromisoformat(last)
                        if (now - last_dt).total_seconds() < 55:
                            continue

                    triggered.append(s)

        for s in triggered:
            self._execute_schedule(s)

    def _execute_schedule(self, schedule: dict):
        try:
            phone = schedule["schedule"].get("phone", "")
            if not phone:
                logger.warning("No phone number for schedule %s", schedule["id"])
                return

            if schedule["channel"] == "whatsapp":
                result = self.send_whatsapp(
                    phone=phone,
                    message=schedule["message"],
                    patient_id=schedule["patient_id"],
                    msg_type=schedule["type"],
                )
            else:
                result = self.send_sms(
                    phone=phone,
                    message=schedule["message"],
                    patient_id=schedule["patient_id"],
                    msg_type=schedule["type"],
                )

            with self._lock:
                for s in self._schedules:
                    if s["id"] == schedule["id"]:
                        s["last_triggered"] = datetime.utcnow().isoformat()
                        if schedule.get("schedule", {}).get("one_time"):
                            s["enabled"] = False
                        break
                self._persist_schedules()

        except Exception as e:
            logger.error("Failed to execute schedule %s: %s", schedule["id"], e)

    def _scheduler_loop(self):
        logger.info("Scheduler thread started")
        while self._running:
            try:
                self._check_schedules()
            except Exception as e:
                logger.error("Scheduler error: %s", e)
            time.sleep(10)
        logger.info("Scheduler thread stopped")

    def _start_scheduler(self):
        self._running = True
        self._scheduler_thread = Thread(target=self._scheduler_loop, daemon=True)
        self._scheduler_thread.start()

    def shutdown(self):
        self._running = False
        if self._scheduler_thread:
            self._scheduler_thread.join(timeout=5)
        with self._lock:
            self._persist_history()
            self._persist_stats()
            self._persist_schedules()
            self._persist_delivery_log()
        logger.info("NotificationEngine shut down")
