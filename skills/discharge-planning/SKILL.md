# Discharge Planning Skill

## Description
Generates comprehensive discharge plans including follow-up appointments, home care instructions, warning signs, and care transition coordination. Used by the `followup_agent` node in the discharge orchestration graph.

## When to Use
- After risk assessment and payment processing
- When creating a patient-specific discharge plan
- When coordinating post-discharge care

## How to Run

```python
from skills.discharge_planning.scripts.planner import DischargePlanner

planner = DischargePlanner()

plan = planner.generate_plan(
    patient_id="patient_123",
    risk_level="high",
    conditions=["CHF", "Type 2 Diabetes"],
    medications=[
        {"name": "lisinopril", "dose": "20mg", "frequency": "daily"},
        {"name": "metformin", "dose": "500mg", "frequency": "twice daily"},
        {"name": "furosemide", "dose": "40mg", "frequency": "daily"},
    ],
    vitals={"bp": "130/80", "hr": 75, "spo2": 98, "weight": "85kg"},
    social_factors={"living_alone": True, "transportation": False},
)
```

## Output
Returns a structured discharge plan with:
- Follow-up appointment schedule
- Home care instructions
- Warning signs to watch for
- Medication schedule
- Social services referrals
- Emergency contact information
