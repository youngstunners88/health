"""
Wearable/IoT Integration Engine
Connects real devices (Apple Health, Fitbit, Bluetooth medical devices)
to the monitoring and alert systems.
"""

import json
import uuid
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Optional
import logging

logger = logging.getLogger("wearables")


DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DEVICES_FILE = DATA_DIR / "devices.json"
READINGS_FILE = DATA_DIR / "readings.json"
SYNC_LOG_FILE = DATA_DIR / "sync_log.json"


DEVICE_TYPES = {
    "apple_health": {
        "name": "Apple Health",
        "category": "platform",
        "metrics": [
            "heart_rate",
            "steps",
            "sleep",
            "blood_oxygen",
            "body_temperature",
            "weight",
            "blood_pressure",
        ],
        "connection_type": "oauth",
        "sync_interval_minutes": 15,
    },
    "fitbit": {
        "name": "Fitbit",
        "category": "platform",
        "metrics": [
            "heart_rate",
            "steps",
            "sleep",
            "blood_oxygen",
            "weight",
            "resting_heart_rate",
        ],
        "connection_type": "oauth",
        "sync_interval_minutes": 15,
    },
    "bluetooth_bp_cuff": {
        "name": "Bluetooth Blood Pressure Cuff",
        "category": "medical_device",
        "metrics": ["systolic_bp", "diastolic_bp", "heart_rate"],
        "connection_type": "bluetooth",
        "sync_interval_minutes": 0,
    },
    "bluetooth_glucose_meter": {
        "name": "Bluetooth Glucose Meter",
        "category": "medical_device",
        "metrics": ["blood_glucose"],
        "connection_type": "bluetooth",
        "sync_interval_minutes": 0,
    },
    "bluetooth_pulse_oximeter": {
        "name": "Bluetooth Pulse Oximeter",
        "category": "medical_device",
        "metrics": ["spo2", "heart_rate"],
        "connection_type": "bluetooth",
        "sync_interval_minutes": 0,
    },
    "bluetooth_scale": {
        "name": "Bluetooth Smart Scale",
        "category": "medical_device",
        "metrics": ["weight", "bmi"],
        "connection_type": "bluetooth",
        "sync_interval_minutes": 0,
    },
    "continuous_glucose_monitor": {
        "name": "Continuous Glucose Monitor (CGM)",
        "category": "medical_device",
        "metrics": ["blood_glucose"],
        "connection_type": "bluetooth",
        "sync_interval_minutes": 5,
    },
    "smartwatch": {
        "name": "Smartwatch (Generic)",
        "category": "platform",
        "metrics": ["heart_rate", "steps", "sleep", "activity"],
        "connection_type": "bluetooth",
        "sync_interval_minutes": 30,
    },
}


class WearableEngine:
    """Manages wearable device connections, data ingestion, and alerting."""

    def __init__(self):
        self.devices = self._load_devices()
        self.readings = self._load_readings()
        self.sync_log = self._load_sync_log()

    def _load_devices(self) -> list[dict]:
        if DEVICES_FILE.exists():
            try:
                return json.loads(DEVICES_FILE.read_text())
            except json.JSONDecodeError:
                pass
        return []

    def _save_devices(self):
        DEVICES_FILE.write_text(json.dumps(self.devices, indent=2, default=str))

    def _load_readings(self) -> list[dict]:
        if READINGS_FILE.exists():
            try:
                return json.loads(READINGS_FILE.read_text())
            except json.JSONDecodeError:
                pass
        return []

    def _save_readings(self):
        READINGS_FILE.write_text(
            json.dumps(self.readings[-5000:], indent=2, default=str)
        )

    def _load_sync_log(self) -> list[dict]:
        if SYNC_LOG_FILE.exists():
            try:
                return json.loads(SYNC_LOG_FILE.read_text())
            except json.JSONDecodeError:
                pass
        return []

    def _save_sync_log(self):
        SYNC_LOG_FILE.write_text(
            json.dumps(self.sync_log[-200:], indent=2, default=str)
        )

    def register_device(
        self,
        patient_id: str,
        patient_name: str,
        device_type: str,
        device_name: str = "",
        device_id: str = "",
        connection_config: dict | None = None,
    ) -> dict:
        """Register a new wearable device for a patient."""
        if device_type not in DEVICE_TYPES:
            raise ValueError(
                f"Unknown device type: {device_type}. Available: {list(DEVICE_TYPES.keys())}"
            )

        device_info = DEVICE_TYPES[device_type]
        registered_device = {
            "device_id": device_id or f"DEV-{uuid.uuid4().hex[:8].upper()}",
            "patient_id": patient_id,
            "patient_name": patient_name,
            "device_type": device_type,
            "device_name": device_name or device_info["name"],
            "category": device_info["category"],
            "metrics": device_info["metrics"],
            "connection_type": device_info["connection_type"],
            "connection_config": connection_config or {},
            "status": "active",
            "registered_at": datetime.now(timezone.utc).isoformat(),
            "last_sync_at": None,
            "last_reading_at": None,
            "total_readings": 0,
        }

        self.devices.append(registered_device)
        self._save_devices()
        return registered_device

    def ingest_readings(
        self,
        device_id: str,
        patient_id: str,
        readings: list[dict],
        source: str = "device",
    ) -> dict:
        """Ingest a batch of readings from a device."""
        device = self._find_device(device_id)
        if not device:
            raise ValueError(f"Device {device_id} not found")

        ingested = []
        alerts = []

        for reading in readings:
            metric = reading.get("metric", "")
            value = reading.get("value")
            timestamp = reading.get("timestamp", datetime.now(timezone.utc).isoformat())

            if value is None:
                continue

            record = {
                "reading_id": f"RDG-{uuid.uuid4().hex[:8].upper()}",
                "device_id": device_id,
                "patient_id": patient_id,
                "metric": metric,
                "value": value,
                "unit": reading.get("unit", ""),
                "source": source,
                "timestamp": timestamp,
                "ingested_at": datetime.now(timezone.utc).isoformat(),
            }
            self.readings.append(record)
            ingested.append(record)

            alert = self._check_threshold(patient_id, metric, value)
            if alert:
                alerts.append(alert)

        device["last_reading_at"] = datetime.now(timezone.utc).isoformat()
        device["total_readings"] += len(ingested)
        self._save_devices()
        self._save_readings()

        return {
            "device_id": device_id,
            "readings_ingested": len(ingested),
            "alerts_generated": len(alerts),
            "alerts": alerts,
        }

    def sync_device(self, device_id: str, data: dict | None = None) -> dict:
        """Simulate or perform a device sync."""
        device = self._find_device(device_id)
        if not device:
            raise ValueError(f"Device {device_id} not found")

        sync_entry = {
            "device_id": device_id,
            "patient_id": device["patient_id"],
            "synced_at": datetime.now(timezone.utc).isoformat(),
            "status": "success",
            "readings_received": 0,
        }

        if data and "readings" in data:
            result = self.ingest_readings(
                device_id=device_id,
                patient_id=device["patient_id"],
                readings=data["readings"],
                source=device["device_type"],
            )
            sync_entry["readings_received"] = result["readings_ingested"]
            sync_entry["alerts"] = result["alerts"]

        device["last_sync_at"] = sync_entry["synced_at"]
        self._save_devices()

        self.sync_log.append(sync_entry)
        self._save_sync_log()

        return sync_entry

    def _check_threshold(
        self, patient_id: str, metric: str, value: float
    ) -> dict | None:
        """Check if a reading exceeds clinical thresholds."""
        thresholds = {
            "heart_rate": {
                "low": 50,
                "high": 120,
                "critical_low": 40,
                "critical_high": 150,
            },
            "systolic_bp": {
                "low": 90,
                "high": 160,
                "critical_low": 80,
                "critical_high": 180,
            },
            "diastolic_bp": {
                "low": 60,
                "high": 100,
                "critical_low": 50,
                "critical_high": 120,
            },
            "spo2": {"low": 92, "high": 100, "critical_low": 88, "critical_high": 100},
            "blood_glucose": {
                "low": 70,
                "high": 250,
                "critical_low": 50,
                "critical_high": 400,
            },
            "body_temperature": {
                "low": 96.0,
                "high": 100.4,
                "critical_low": 95.0,
                "critical_high": 103.0,
            },
            "weight": {"low": 0, "high": 999, "critical_low": 0, "critical_high": 999},
        }

        th = thresholds.get(metric)
        if not th:
            return None

        severity = None
        if value <= th["critical_low"] or value >= th["critical_high"]:
            severity = "critical"
        elif value <= th["low"] or value >= th["high"]:
            severity = "warning"

        if severity:
            return {
                "alert_id": f"WA-{uuid.uuid4().hex[:8].upper()}",
                "patient_id": patient_id,
                "metric": metric,
                "value": value,
                "threshold": th,
                "severity": severity,
                "message": f"{metric}: {value} ({severity})",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        return None

    def _find_device(self, device_id: str) -> dict | None:
        for device in self.devices:
            if device["device_id"] == device_id:
                return device
        return None

    def get_patient_devices(self, patient_id: str) -> list[dict]:
        return [d for d in self.devices if d["patient_id"] == patient_id]

    def get_readings(
        self,
        patient_id: str,
        metric: str | None = None,
        device_id: str | None = None,
        hours: int = 24,
    ) -> list[dict]:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        readings = []
        for r in self.readings:
            if r["patient_id"] != patient_id:
                continue
            if metric and r["metric"] != metric:
                continue
            if device_id and r["device_id"] != device_id:
                continue
            try:
                ts = datetime.fromisoformat(r["timestamp"])
                if ts < cutoff:
                    continue
            except (ValueError, TypeError):
                continue
            readings.append(r)
        return sorted(readings, key=lambda r: r.get("timestamp", ""))

    def get_device_status(self, device_id: str) -> dict:
        device = self._find_device(device_id)
        if not device:
            raise ValueError(f"Device {device_id} not found")

        last_sync = device.get("last_sync_at")
        needs_sync = False
        if last_sync:
            try:
                sync_time = datetime.fromisoformat(last_sync)
                interval = DEVICE_TYPES.get(device["device_type"], {}).get(
                    "sync_interval_minutes", 30
                )
                if interval > 0:
                    needs_sync = (
                        datetime.now(timezone.utc) - sync_time
                    ).total_seconds() > interval * 60
            except (ValueError, TypeError):
                pass

        recent_readings = self.get_readings(
            patient_id=device["patient_id"],
            device_id=device_id,
            hours=24,
        )

        return {
            **device,
            "needs_sync": needs_sync,
            "readings_last_24h": len(recent_readings),
            "metrics_available": device["metrics"],
        }

    def get_statistics(self) -> dict:
        total_devices = len(self.devices)
        active_devices = len([d for d in self.devices if d["status"] == "active"])
        total_readings = len(self.readings)

        device_types = {}
        for d in self.devices:
            dt = d["device_type"]
            device_types[dt] = device_types.get(dt, 0) + 1

        metric_counts = {}
        for r in self.readings:
            m = r["metric"]
            metric_counts[m] = metric_counts.get(m, 0) + 1

        return {
            "total_devices": total_devices,
            "active_devices": active_devices,
            "total_readings": total_readings,
            "device_types": device_types,
            "top_metrics": sorted(
                metric_counts.items(), key=lambda x: x[1], reverse=True
            )[:10],
        }
