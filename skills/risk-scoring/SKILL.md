# Risk Scoring Skill

## Description
Calculates patient readmission risk using validated clinical scoring models. Supports LACE index, HOSPITAL score, and custom ML-based risk assessment. Used by the `risk_agent` node in the discharge orchestration graph.

## When to Use
- After patient intake, before routing to payer or followup
- Any time you need a readmission probability score
- When evaluating discharge readiness

## How to Run

```python
from skills.risk_scoring.scripts.risk_calculator import calculate_risk

# LACE Index (Length of stay, Acuity, Comorbidities, ED visits)
result = calculate_risk(
    patient_id="patient_123",
    method="lace",
    params={
        "length_of_stay_days": 4,
        "admission_acuity": "urgent",  # elective, urgent, emergency
        "comorbidities": ["CHF", "diabetes"],  # Charlson comorbidity list
        "ed_visits_last_6mo": 2
    }
)
# Returns: {"score": 12, "risk": 0.72, "level": "high", "factors": [...]}

# HOSPITAL Score
result = calculate_risk(
    patient_id="patient_123",
    method="hospital",
    params={
        "h": "high",  # H: Hct at discharge (low=3, high=0)
        "o": True,    # O: Oncology active treatment (yes=3, no=0)
        "s": 75,      # S: Score on readmission risk scale (0-75)
        "p": 1,       # P: Number of procedures (0, 1, 2+)
        "i": "none",  # I: Index type of admission (none=0, medical=1, emergency=2)
        "t": 5,       # T: Type of admission (0=elective, 5=emergency)
        "a": 1,       # A: Admissions in last 12 months
        "l": 4        # L: Length of stay (days)
    }
)
```

## Scoring Models

### LACE Index
| Component | Points |
|---|---|
| Length of stay | 1 point per day (max 5) |
| Acuity | Elective=0, Urgent=1, Emergency=3 |
| Comorbidities | Charlson score (0-6) |
| ED visits | 1 point per visit in last 6mo (max 4) |

**Risk Levels:** 0-4 = Low (5%), 5-9 = Moderate (15%), 10-14 = High (25%), 15+ = Very High (40%)

### HOSPITAL Score
Range: 0-30. Risk: 0-4 = Low (5%), 5-8 = Moderate (12%), 9+ = High (25%)

## Output Schema
```json
{
  "patient_id": "string",
  "method": "lace|hospital|ml",
  "score": "number",
  "risk": "float (0.0-1.0)",
  "level": "low|moderate|high|very_high",
  "factors": ["list of contributing factors"],
  "recommendations": ["list of clinical recommendations"],
  "timestamp": "ISO 8601"
}
```
