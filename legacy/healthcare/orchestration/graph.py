import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from langgraph.graph import StateGraph, END
from workspaces.healthcare.orchestration.state import StateSchema
from workspaces.healthcare.protocols.mcp_client import call_mcp_tool
from workspaces.healthcare.protocols.a2a import send_a2a_message
from skills.humanizer.scripts.humanize import humanize_json
from skills.payment_agent.scripts.process import pay
from skills.risk_scoring.scripts.risk_calculator import calculate_risk
from skills.ehr_integration.scripts.fhir_client import FHIRClient
from skills.medication_reconciliation.scripts.med_checker import MedicationChecker
from skills.discharge_planning.scripts.planner import DischargePlanner
from skills.care_coordination.scripts.coordinator import CareCoordinator
from skills.patient_education.scripts.educator import PatientEducator
from skills.anomaly_detection.scripts.detector import AnomalyDetector
from skills.health_monitoring.scripts.monitor import HealthMonitor
import logging
from functools import wraps


def time_node(name: str):
    """Simple timing decorator for node execution (no-op for testing)."""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        return wrapper

    return decorator


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("healthcare_graph")


# Node functions
def intake_agent(state: StateSchema):
    """Pull EHR via MCP with FHIR fallback"""
    try:
        ehr = call_mcp_tool("get_patient_ehr", {"patient_id": state.patient_id})
        if "error" in ehr:
            logger.warning(
                f"Intake agent MCP error, falling back to FHIR: {ehr['error']}"
            )
            try:
                fhir = FHIRClient()
                ehr = fhir.get_patient_record(state.patient_id)
            except Exception as fhir_err:
                logger.error(f"FHIR fallback also failed: {fhir_err}")
                ehr = {}
        state.patient_ehr = ehr
        state.handoff_log.append({"agent": "intake", "output": ehr})
    except Exception as ex:
        logger.exception(f"Intake agent exception: {ex}")
        state.patient_ehr = {}
        state.handoff_log.append({"agent": "intake", "error": str(ex)})
    return state


def risk_agent(state: StateSchema):
    """Score readmission risk using LACE index"""
    try:
        diagnoses = state.patient_ehr.get("diagnoses", [])
        risk_result = calculate_risk(
            patient_id=state.patient_id,
            method="lace",
            params={
                "length_of_stay_days": state.patient_ehr.get("length_of_stay", 3),
                "admission_acuity": state.patient_ehr.get("admission_acuity", "urgent"),
                "comorbidities": diagnoses,
                "ed_visits_last_6mo": state.patient_ehr.get("ed_visits", 1),
            },
        )
        state.risk_score = risk_result["risk"]
        state.risk_details = risk_result
        state.handoff_log.append(
            {
                "agent": "risk",
                "risk_score": risk_result["risk"],
                "level": risk_result["level"],
            }
        )
    except Exception as ex:
        logger.exception(f"Risk agent exception: {ex}")
        risk = 0.8 if "CHF" in state.patient_ehr.get("diagnoses", []) else 0.3
        state.risk_score = risk
        state.handoff_log.append(
            {"agent": "risk", "risk_score": risk, "error": str(ex)}
        )
    return state


def payer_agent(state: StateSchema):
    """Check coverage and auto-generate prior auth if needed"""
    try:
        from workspaces.healthcare.prior_auth.engine.authorization import (
            PriorAuthEngine,
            PayerRulesDB,
        )

        payer_rules_db = PayerRulesDB()
        auth_engine = PriorAuthEngine()

        payer_name = state.patient_ehr.get("payer_name", "BlueCross BlueShield")
        diagnoses = state.patient_ehr.get("diagnoses", [])
        procedures = state.patient_ehr.get("procedures", ["discharge_planning"])

        payer_decision = call_mcp_tool(
            "check_payer_rules",
            {"patient_id": state.patient_id, "procedure": "discharge_planning"},
        )

        prior_auths = []
        for procedure in procedures:
            if payer_rules_db.needs_prior_auth(payer_name, procedure):
                auth = auth_engine.create_auth_request(
                    patient_id=state.patient_id,
                    patient_name=state.patient_ehr.get("name", "Patient"),
                    payer_name=payer_name,
                    procedure=procedure,
                    diagnosis_codes=diagnoses,
                    provider_name=state.patient_ehr.get("provider", "Dr. Smith"),
                    provider_npi=state.patient_ehr.get("provider_npi", "1234567890"),
                    clinical_notes=f"Prior auth for {procedure} during discharge planning. Diagnoses: {', '.join(diagnoses)}.",
                    urgency="standard",
                )
                prior_auths.append(auth)
                logger.info(
                    f"Auto-created prior auth {auth['auth_id']} for {procedure}"
                )

        if "error" in payer_decision:
            logger.error(f"Payer agent MCP error: {payer_decision['error']}")
            payer_decision = {}

        state.payer_decision = payer_decision
        state.prior_auths = prior_auths
        state.handoff_log.append(
            {
                "agent": "payer",
                "output": payer_decision,
                "prior_auths_created": len(prior_auths),
                "prior_auth_ids": [a["auth_id"] for a in prior_auths],
            }
        )
    except Exception as ex:
        logger.exception(f"Payer agent exception: {ex}")
        state.payer_decision = {}
        state.handoff_log.append({"agent": "payer", "error": str(ex)})
    return state


@time_node("payment")
def payment_agent(state: StateSchema) -> StateSchema:
    """
    Processes a payment after the insurance check.
    Expects state to contain:
      - patient_id
      - amount (float)   – e.g., copay amount
      - currency (str)   – "usd" or "celo-usd"
      - method (str)     – "celo", "card", etc.
      - risk_score (float, optional) – 0‑1
      - adherence_days (int, optional) – claim‑free streak
      - purpose (str, optional) – one of the three sub‑pools
    """
    # Provide defaults for missing fields to avoid AttributeError
    amount = state.amount if state.amount is not None else 0.0
    currency = state.currency if state.currency is not None else "usd"
    method = state.method if state.method is not None else "card"
    try:
        result = pay(
            amount=amount,
            currency=currency,
            method=method,
            metadata={
                "patient_id": state.patient_id,
                "procedure": state.insurance_eligibility.get("procedure")
                if state.insurance_eligibility
                else None,
                "description": "Copay for discharge planning",
            },
            risk_score=getattr(state, "risk_score", None),
            adherence_days=getattr(state, "adherence_days", None),
            purpose=getattr(state, "staking_purpose", "follow_up_bonus"),
        )
        state.payment_result = result
        state.handoff_log.append({"agent": "payment", "result": result})
    except Exception as ex:
        logger.exception(f"Payment agent exception: {ex}")
        state.payment_result = {"error": str(ex)}
        state.handoff_log.append({"agent": "payment", "error": str(ex)})
    return state


def followup_agent(state: StateSchema):
    """Generate discharge plan with real scheduling and humanization"""
    try:
        planner = DischargePlanner()
        diagnoses = state.patient_ehr.get("diagnoses", [])
        plan = planner.generate_plan(
            patient_id=state.patient_id,
            risk_level=state.risk_details.get("level", "moderate")
            if state.risk_details
            else "moderate",
            conditions=diagnoses,
            medications=state.patient_ehr.get("medications", []),
            vitals=state.patient_ehr.get("vitals", {}),
            social_factors=state.patient_ehr.get("social_factors", {}),
        )

        coordinator = CareCoordinator()
        care_team = coordinator.assemble_care_team(
            patient_id=state.patient_id,
            primary_care_provider="Dr. Smith",
            specialists=diagnoses,
            home_health=state.risk_score > 0.5,
            social_work=True,
            pharmacy=True,
        )

        educator = PatientEducator()
        discharge_instructions = educator.generate_discharge_instructions(
            patient_name=state.patient_ehr.get("name", "Patient"),
            conditions=diagnoses,
            medications=state.patient_ehr.get("medications", []),
            followups=plan.get("follow_up_appointments", []),
            warning_signs=plan.get("warning_signs", []),
        )

        humanized_plan = humanize_json(plan)
        state.follow_up_plan = plan
        state.care_team = care_team
        state.patient_instructions = discharge_instructions
        state.handoff_log.append(
            {
                "agent": "followup",
                "plan": plan,
                "humanized_plan": humanized_plan,
                "care_team_members": len(care_team.get("members", [])),
            }
        )
    except Exception as ex:
        logger.exception(f"Followup agent exception: {ex}")
        state.follow_up_plan = {}
        state.handoff_log.append({"agent": "followup", "error": str(ex)})
    return state


def monitor_agent(state: StateSchema):
    """Monitor home vitals with anomaly detection"""
    try:
        monitor = HealthMonitor()
        detector = AnomalyDetector()

        vitals = state.patient_ehr.get("vitals", {"bp": "130/80", "hr": 75, "spo2": 98})
        parsed_vitals = {}
        if "bp" in vitals:
            parts = vitals["bp"].split("/")
            if len(parts) == 2:
                parsed_vitals["systolic_bp"] = int(parts[0])
                parsed_vitals["diastolic_bp"] = int(parts[1])
        if "hr" in vitals:
            parsed_vitals["heart_rate"] = int(vitals["hr"])
        if "spo2" in vitals:
            parsed_vitals["spo2"] = int(vitals["spo2"])

        state.vitals = vitals
        vitals_check = detector.check_vitals(parsed_vitals)
        state.vitals_alerts = vitals_check.get("alerts", [])

        coordinator = CareCoordinator()
        if vitals_check.get("overall_status") != "normal":
            transition_note = coordinator.notify_care_transition(
                patient_id=state.patient_id,
                from_location="home",
                to_location="care_team_alert",
                discharge_summary=f"Vitals alert: {vitals_check['overall_status']}. Alerts: {vitals_check['alert_count']}",
                care_team=state.care_team if state.care_team else {"members": []},
            )
            state.handoff_log.append(
                {
                    "agent": "monitor",
                    "vitals": vitals,
                    "alert_status": vitals_check["overall_status"],
                    "alerts": vitals_check["alerts"],
                    "care_team_notified": transition_note.get("notifications_sent", 0),
                }
            )
        else:
            state.handoff_log.append(
                {
                    "agent": "monitor",
                    "vitals": vitals,
                    "alert_status": "normal",
                }
            )
    except Exception as ex:
        logger.exception(f"Monitor agent exception: {ex}")
        state.vitals = {}
        state.handoff_log.append({"agent": "monitor", "error": str(ex)})
    return state


def supervisor_router(state: StateSchema):
    """Route based on risk score"""
    try:
        if state.risk_score is not None and state.risk_score > 0.7:
            return "payer"
        else:
            return "followup"
    except Exception as ex:
        logger.exception(f"Supervisor router exception: {ex}")
        return "followup"


def sdoh_agent(state: StateSchema):
    """Run SDOH screening and auto-generate referrals"""
    try:
        from workspaces.healthcare.sdoh.engine.screening import SDOHEngine

        sdoh_engine = SDOHEngine()
        social_factors = state.patient_ehr.get("social_factors", {})

        responses = {}
        if social_factors.get("living_alone"):
            responses["so2"] = "yes"
            responses["so1"] = "no"
        if social_factors.get("transportation") is False:
            responses["t1"] = "no"
            responses["t2"] = "yes"
        if social_factors.get("food_insecurity"):
            responses["f1"] = "yes"
            responses["f2"] = "yes"
        if social_factors.get("financial_hardship"):
            responses["fi1"] = 4
            responses["fi3"] = "yes"

        if responses:
            screening = sdoh_engine.create_screening(
                patient_id=state.patient_id,
                patient_name=state.patient_ehr.get("name", "Patient"),
                responses=responses,
                screened_by="auto_discharge",
                screening_context="discharge",
            )
            state.sdoh_screening = screening
            state.sdoh_referrals = screening.get("auto_referrals", [])
            state.handoff_log.append(
                {
                    "agent": "sdoh",
                    "screening_id": screening["screening_id"],
                    "risk_level": screening["overall_risk_level"],
                    "referrals_generated": len(screening.get("auto_referrals", [])),
                }
            )
        else:
            state.handoff_log.append(
                {"agent": "sdoh", "status": "no_social_factors_detected"}
            )
    except Exception as ex:
        logger.exception(f"SDOH agent exception: {ex}")
        state.handoff_log.append({"agent": "sdoh", "error": str(ex)})
    return state


def wearable_agent(state: StateSchema):
    """Register wearable devices for post-discharge monitoring"""
    try:
        from workspaces.healthcare.wearables.engine.devices import WearableEngine

        wearable_engine = WearableEngine()
        patient_name = state.patient_ehr.get("name", "Patient")
        devices = []

        diagnoses = state.patient_ehr.get("diagnoses", [])
        if any(
            d.lower() in ["chf", "heart failure", "hypertension"] for d in diagnoses
        ):
            device = wearable_engine.register_device(
                patient_id=state.patient_id,
                patient_name=patient_name,
                device_type="bluetooth_bp_cuff",
                device_name="Home BP Monitor",
            )
            devices.append(device)

        if any(d.lower() in ["diabetes", "t2dm", "t1dm"] for d in diagnoses):
            device = wearable_engine.register_device(
                patient_id=state.patient_id,
                patient_name=patient_name,
                device_type="bluetooth_glucose_meter",
                device_name="Home Glucose Meter",
            )
            devices.append(device)

        device = wearable_engine.register_device(
            patient_id=state.patient_id,
            patient_name=patient_name,
            device_type="bluetooth_pulse_oximeter",
            device_name="Home Pulse Oximeter",
        )
        devices.append(device)

        state.wearable_devices = devices
        state.handoff_log.append(
            {
                "agent": "wearable",
                "devices_registered": len(devices),
                "device_types": [d["device_type"] for d in devices],
            }
        )
    except Exception as ex:
        logger.exception(f"Wearable agent exception: {ex}")
        state.handoff_log.append({"agent": "wearable", "error": str(ex)})
    return state


# Build graph
workflow = StateGraph(StateSchema)
workflow.add_node("intake", intake_agent)
workflow.add_node("risk", risk_agent)
workflow.add_node("payer", payer_agent)
workflow.add_node("payment", payment_agent)
workflow.add_node("followup", followup_agent)
workflow.add_node("sdoh", sdoh_agent)
workflow.add_node("wearable", wearable_agent)
workflow.add_node("monitor", monitor_agent)

workflow.set_entry_point("intake")
workflow.add_edge("intake", "risk")
workflow.add_conditional_edges(
    "risk", supervisor_router, {"payer": "payer", "followup": "followup"}
)
workflow.add_edge("payer", "payment")
workflow.add_edge("payment", "followup")
workflow.add_edge("followup", "sdoh")
workflow.add_edge("sdoh", "wearable")
workflow.add_edge("wearable", "monitor")
workflow.add_edge("monitor", END)

app = workflow.compile()

if __name__ == "__main__":
    result = app.invoke({"patient_id": "12345"})
    print(result)
