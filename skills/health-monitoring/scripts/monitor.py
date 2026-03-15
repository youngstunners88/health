"""
Health monitoring for post-discharge patients.
Tracks vitals, activity, sleep, and generates alerts.
"""

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path


STORAGE_DIR = Path(__file__).parent.parent / "data"
STORAGE_DIR.mkdir(exist_ok=True)


class HealthMonitor:
    """Monitors patient health metrics and generates alerts."""

    def __init__(self, storage_dir: Path | None = None):
        self.storage_dir = storage_dir or STORAGE_DIR
        self.storage_dir.mkdir(exist_ok=True)

    def record_vital(
        self,
        patient_id: str,
        metric: str,
        value: float,
        unit: str = "",
        source: str = "manual",
    ) -> dict:
        record = {
            "patient_id": patient_id,
            "metric": metric,
            "value": value,
            "unit": unit,
            "source": source,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        patient_file = self.storage_dir / f"{patient_id}_vitals.json"
        records = []
        if patient_file.exists():
            records = json.loads(patient_file.read_text())
        records.append(record)
        patient_file.write_text(json.dumps(records, indent=2))

        return record

    def get_vitals(
        self,
        patient_id: str,
        metric: str | None = None,
        hours: int = 24,
    ) -> list[dict]:
        patient_file = self.storage_dir / f"{patient_id}_vitals.json"
        if not patient_file.exists():
            return []

        records = json.loads(patient_file.read_text())
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

        filtered = []
        for r in records:
            ts = datetime.fromisoformat(r["timestamp"])
            if ts < cutoff:
                continue
            if metric and r["metric"] != metric:
                continue
            filtered.append(r)

        return filtered

    def get_monitoring_summary(
        self,
        patient_id: str,
        hours: int = 24,
    ) -> dict:
        vitals = self.get_vitals(patient_id, hours=hours)

        metrics = {}
        for v in vitals:
            m = v["metric"]
            if m not in metrics:
                metrics[m] = {"values": [], "unit": v.get("unit", ""), "readings": 0}
            metrics[m]["values"].append(v["value"])
            metrics[m]["readings"] += 1

        summary = {}
        for metric, data in metrics.items():
            vals = data["values"]
            summary[metric] = {
                "current": vals[-1] if vals else None,
                "min": min(vals) if vals else None,
                "max": max(vals) if vals else None,
                "avg": round(sum(vals) / len(vals), 1) if vals else None,
                "readings": data["readings"],
                "unit": data["unit"],
            }

        return {
            "patient_id": patient_id,
            "period_hours": hours,
            "total_readings": len(vitals),
            "metrics": summary,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def check_alerts(
        self,
        patient_id: str,
        hours: int = 1,
    ) -> list[dict]:
        from skills.anomaly_detection.scripts.detector import AnomalyDetector

        detector = AnomalyDetector()
        vitals = self.get_vitals(patient_id, hours=hours)

        alerts = []
        latest = {}
        for v in vitals:
            latest[v["metric"]] = v["value"]

        if latest:
            result = detector.check_vitals(latest)
            alerts = result.get("alerts", [])

        return alerts
