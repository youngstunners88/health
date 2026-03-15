# Care Coordination Skill

## Description
Coordinates care between multiple providers, specialists, home health agencies, and social services. Manages care team communication and ensures smooth care transitions.

## When to Use
- When multiple specialists are involved in a patient's care
- During care transitions (hospital to home, SNF, rehab)
- When coordinating home health services
- When updating the care team on patient status

## How to Run

```python
from skills.care_coordination.scripts.coordinator import CareCoordinator

coordinator = CareCoordinator()

# Assemble care team
team = coordinator.assemble_care_team(
    patient_id="patient_123",
    primary_care_provider="Dr. Smith",
    specialists=["Cardiology", "Endocrinology"],
    home_health=True,
    social_work=True,
)

# Send care transition notification
notification = coordinator.notify_care_transition(
    patient_id="patient_123",
    from_location="hospital",
    to_location="home",
    discharge_summary="Patient discharged with CHF exacerbation...",
    care_team=team,
)
```
