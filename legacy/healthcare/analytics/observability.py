"""
Observability layer for healthcare platform.
Prometheus metrics, structured logging, and health checks.
"""

from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    generate_latest,
    CONTENT_TYPE_LATEST,
)
from datetime import datetime, timezone
import logging
import json
import time
from functools import wraps


logger = logging.getLogger("healthcare.observability")


# Metrics
METRIC_REQUESTS = Counter(
    "healthcare_requests_total",
    "Total HTTP requests",
    ["service", "method", "endpoint", "status"],
)

METRIC_REQUEST_DURATION = Histogram(
    "healthcare_request_duration_seconds",
    "Request duration in seconds",
    ["service", "endpoint"],
)

METRIC_PATIENTS_ACTIVE = Gauge(
    "healthcare_patients_active",
    "Number of actively monitored patients",
)

METRIC_RISK_SCORE = Gauge(
    "healthcare_patient_risk_score",
    "Patient readmission risk score",
    ["patient_id", "risk_level"],
)

METRIC_PRIOR_AUTH = Counter(
    "healthcare_prior_auth_total",
    "Prior authorization requests",
    ["payer", "procedure", "status"],
)

METRIC_ALERTS = Gauge(
    "healthcare_active_alerts",
    "Number of active clinical alerts",
    ["severity"],
)

METRIC_VITALS_READINGS = Counter(
    "healthcare_vitals_readings_total",
    "Total vitals readings submitted",
    ["metric"],
)

METRIC_DISCHARGE_PLAN = Counter(
    "healthcare_discharge_plans_total",
    "Discharge plans generated",
    ["risk_level"],
)


def metrics_endpoint():
    """Return Prometheus metrics."""
    return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}


def health_check(services: dict[str, str] | None = None):
    """Return health check response."""
    services = services or {
        "patient_portal": "http://localhost:8080",
        "care_dashboard": "http://localhost:8081",
        "prior_auth": "http://localhost:8082",
    }

    status = "healthy"
    checks = {}
    for name, url in services.items():
        checks[name] = {
            "status": "unknown",
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }

    return {
        "status": status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "services": checks,
    }


def timed(service: str, endpoint: str):
    """Decorator to time endpoint execution and record metrics."""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start
                METRIC_REQUEST_DURATION.labels(
                    service=service, endpoint=endpoint
                ).observe(duration)
                return result
            except Exception as e:
                duration = time.time() - start
                METRIC_REQUEST_DURATION.labels(
                    service=service, endpoint=endpoint
                ).observe(duration)
                raise

        return wrapper

    return decorator


class AuditLogger:
    """HIPAA-compliant audit logger."""

    def __init__(self, log_file: str | None = None):
        self.log_file = log_file
        self.logger = logging.getLogger("healthcare.audit")
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter(
                json.dumps(
                    {
                        "timestamp": "%(timestamp)s",
                        "event": "%(event)s",
                        "user": "%(user)s",
                        "patient_id": "%(patient_id)s",
                        "action": "%(action)s",
                        "details": "%(details)s",
                        "ip": "%(ip)s",
                    }
                )
            )
        )
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def log(
        self,
        event: str,
        user: str,
        patient_id: str,
        action: str,
        details: dict | None = None,
        ip: str | None = None,
    ):
        self.logger.info(
            "",
            extra={
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event": event,
                "user": user,
                "patient_id": patient_id,
                "action": action,
                "details": json.dumps(details or {}),
                "ip": ip or "unknown",
            },
        )
