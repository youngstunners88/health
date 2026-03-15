from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from skills.persistent_agent_memory.scripts.memory_store import (
    save_memory,
    load_memory,
    clear_memory,
)
import json


class StateSchema(BaseModel):
    patient_id: str
    run_id: str = Field(
        default_factory=lambda: (
            __import__("uuid")
            .uuid5(
                __import__("uuid").UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8"),
                f"{__import__('datetime').datetime.now(timezone.utc).date().isoformat()}|{__import__('uuid').uuid4()}",
            )
            .hex
        )
    )
    risk_score: Optional[float] = None
    risk_details: Optional[Dict[str, Any]] = None
    handoff_log: List[Dict[str, Any]] = Field(default_factory=list)
    patient_ehr: Optional[Dict[str, Any]] = None
    payer_decision: Optional[Dict[str, Any]] = None
    follow_up_plan: Optional[Dict[str, Any]] = None
    care_team: Optional[Dict[str, Any]] = None
    patient_instructions: Optional[Dict[str, Any]] = None
    vitals: Optional[Dict[str, Any]] = None
    vitals_alerts: Optional[List[Dict[str, Any]]] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    # Payment related fields
    amount: Optional[float] = 0.0
    currency: Optional[str] = "usd"
    method: Optional[str] = "card"
    insurance_eligibility: Optional[Dict[str, Any]] = None
    adherence_days: Optional[int] = None
    staking_purpose: Optional[str] = None
    payment_result: Optional[Dict[str, Any]] = None
    prior_auths: Optional[List[Dict[str, Any]]] = None
    sdoh_screening: Optional[Dict[str, Any]] = None
    sdoh_referrals: Optional[List[Dict[str, Any]]] = None
    wearable_devices: Optional[List[Dict[str, Any]]] = None

    def save(self):
        save_memory(f"state:{self.patient_id}:{self.run_id}", self.model_dump_json())

    @staticmethod
    def load_latest(patient_id: str) -> Optional["StateSchema"]:
        from skills.persistent_agent_memory.scripts.memory_store import _read_store

        data = _read_store() or {}
        pref = f"state:{patient_id}:"
        matching = [k for k in data.keys() if k.startswith(pref)]
        if not matching:
            return None
        latest_key = max(matching)
        try:
            return StateSchema.model_validate_json(data[latest_key])
        except Exception:
            return None
