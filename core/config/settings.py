"""
Platform Configuration
Single config source for all services.
"""

import os
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


class Config:
    """Centralized configuration with environment variable overrides."""

    # Platform
    PLATFORM_NAME = "Healthcare Platform"
    VERSION = "1.0.0"
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"

    # Database
    DB_URL = os.getenv("DATABASE_URL", "sqlite:///data/platform.db")
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # Services
    SERVICES = {
        "patient_portal": {"port": 8080, "host": "0.0.0.0"},
        "care_dashboard": {"port": 8081, "host": "0.0.0.0"},
        "prior_auth": {"port": 8082, "host": "0.0.0.0"},
        "revenue_cycle": {"port": 8083, "host": "0.0.0.0"},
        "sdoh": {"port": 8084, "host": "0.0.0.0"},
        "wearables": {"port": 8085, "host": "0.0.0.0"},
        "notifications": {"port": 8086, "host": "0.0.0.0"},
        "clinical_trials": {"port": 8087, "host": "0.0.0.0"},
        "marketplace": {"port": 8088, "host": "0.0.0.0"},
        "compliance": {"port": 8089, "host": "0.0.0.0"},
        "gateway": {"port": 8000, "host": "0.0.0.0"},
        "mcp_ehr": {"port": 8001, "host": "0.0.0.0"},
    }

    # FHIR
    FHIR_SERVER_URL = os.getenv("FHIR_SERVER_URL", "https://hapi.fhir.org/baseR4")
    FHIR_CLIENT_ID = os.getenv("FHIR_CLIENT_ID", "")
    FHIR_CLIENT_SECRET = os.getenv("FHIR_CLIENT_SECRET", "")

    # Notifications
    TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
    TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER", "")
    NOTIFICATION_MOCK_MODE = (
        os.getenv("NOTIFICATION_MOCK_MODE", "true").lower() == "true"
    )

    # Security
    PHI_ENCRYPTION_KEY = os.getenv("PHI_ENCRYPTION_KEY", "dev-key-change-in-production")
    JWT_SECRET = os.getenv("JWT_SECRET", "dev-jwt-secret-change-in-production")

    # Paths
    DATA_DIR = DATA_DIR
    STATE_DIR = DATA_DIR / "state"
    EVENTS_DIR = DATA_DIR / "events"
    LOGS_DIR = DATA_DIR / "logs"

    @classmethod
    def init_dirs(cls):
        """Create all required directories."""
        for d in [cls.DATA_DIR, cls.STATE_DIR, cls.EVENTS_DIR, cls.LOGS_DIR]:
            d.mkdir(parents=True, exist_ok=True)

    @classmethod
    def get_service_url(cls, service_name: str) -> str:
        """Get the full URL for a service."""
        svc = cls.SERVICES.get(service_name, {})
        return f"http://{svc.get('host', 'localhost')}:{svc.get('port', 0)}"

    @classmethod
    def to_dict(cls) -> dict[str, Any]:
        """Export config as dict (without secrets)."""
        return {
            "platform": cls.PLATFORM_NAME,
            "version": cls.VERSION,
            "debug": cls.DEBUG,
            "services": {k: {"port": v["port"]} for k, v in cls.SERVICES.items()},
            "fhir_server": cls.FHIR_SERVER_URL,
            "notification_mock": cls.NOTIFICATION_MOCK_MODE,
        }


config = Config()
config.init_dirs()
