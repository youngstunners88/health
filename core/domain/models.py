"""
Healthcare Platform - Core Domain Models
Clean architecture: domain entities are pure, framework-agnostic.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timezone
from enum import Enum
import uuid


class RiskLevel(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    VERY_HIGH = "very_high"


class AlertSeverity(str, Enum):
    NORMAL = "normal"
    WARNING = "warning"
    CRITICAL = "critical"


class AuthStatus(str, Enum):
    SUBMITTED = "submitted"
    APPROVED = "approved"
    DENIED = "denied"
    APPEAL_SUBMITTED = "appeal_submitted"
    NOT_REQUIRED = "not_required"


class ClaimStatus(str, Enum):
    SUBMITTED = "submitted"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    PAID = "paid"
    DENIED = "denied"
    APPEAL_SUBMITTED = "appeal_submitted"


class SDOHRiskLevel(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class DeviceStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"


class Patient(BaseModel):
    id: str
    name: str
    mrn: str = ""
    dob: str = ""
    phone: str = ""
    email: str = ""
    payer_name: str = ""
    subscriber_id: str = ""
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class Diagnosis(BaseModel):
    code: str
    description: str
    type: str = "primary"


class Medication(BaseModel):
    name: str
    dose: str
    frequency: str
    instructions: str = ""
    start_date: str = ""
    end_date: str = ""


class VitalsReading(BaseModel):
    patient_id: str
    heart_rate: Optional[int] = None
    systolic_bp: Optional[int] = None
    diastolic_bp: Optional[int] = None
    spo2: Optional[int] = None
    temperature: Optional[float] = None
    weight: Optional[float] = None
    respiratory_rate: Optional[int] = None
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class DischargePlan(BaseModel):
    patient_id: str
    risk_level: RiskLevel = RiskLevel.MODERATE
    follow_up_appointments: list[dict] = []
    warning_signs: list[str] = []
    home_care_instructions: list[str] = []
    medication_schedule: list[dict] = []
    social_services_referrals: list[dict] = []
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class CareTeamMember(BaseModel):
    role: str
    title: str
    name: str
    responsibilities: list[str] = []


class CareTeam(BaseModel):
    patient_id: str
    members: list[CareTeamMember] = []


class PriorAuthRequest(BaseModel):
    id: str = Field(default_factory=lambda: f"PA-{uuid.uuid4().hex[:8].upper()}")
    patient_id: str
    patient_name: str
    payer_name: str
    procedure: str
    diagnosis_codes: list[str] = []
    provider_name: str
    provider_npi: str
    status: AuthStatus = AuthStatus.SUBMITTED
    submitted_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    decision: Optional[str] = None
    auth_number: Optional[str] = None


class Claim(BaseModel):
    id: str = Field(default_factory=lambda: f"CLM-{uuid.uuid4().hex[:8].upper()}")
    patient_id: str
    payer_name: str
    provider_name: str
    provider_npi: str
    charge_amount: float = 0.0
    status: ClaimStatus = ClaimStatus.SUBMITTED
    submitted_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class Alert(BaseModel):
    id: str = Field(default_factory=lambda: f"ALT-{uuid.uuid4().hex[:8].upper()}")
    patient_id: str
    type: str
    severity: AlertSeverity = AlertSeverity.WARNING
    message: str
    data: dict = {}
    status: str = "active"
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class SDOHScreening(BaseModel):
    id: str = Field(default_factory=lambda: f"SDOH-{uuid.uuid4().hex[:8].upper()}")
    patient_id: str
    patient_name: str
    responses: dict = {}
    overall_risk_level: SDOHRiskLevel = SDOHRiskLevel.LOW
    positive_domains: list[str] = []
    critical_flags: list[str] = []
    completed_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class WearableDevice(BaseModel):
    id: str = Field(default_factory=lambda: f"DEV-{uuid.uuid4().hex[:8].upper()}")
    patient_id: str
    device_type: str
    device_name: str
    status: DeviceStatus = DeviceStatus.ACTIVE
    metrics: list[str] = []
    last_sync_at: Optional[str] = None
    registered_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class Notification(BaseModel):
    id: str = Field(default_factory=lambda: f"NOT-{uuid.uuid4().hex[:8].upper()}")
    patient_id: str
    type: str
    channel: str
    message: str
    status: str = "pending"
    scheduled_at: Optional[str] = None
    sent_at: Optional[str] = None
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
