# Medication Reconciliation Skill

## Description
Performs medication reconciliation during discharge. Checks for drug-drug interactions, allergy conflicts, duplicate therapies, and adherence risks. Generates a clean medication list for the patient.

## When to Use
- Before discharge to reconcile home vs inpatient medications
- When new prescriptions are added
- When checking for drug interactions or allergy conflicts

## How to Run

```python
from skills.medication_reconciliation.scripts.med_checker import MedicationChecker

checker = MedicationChecker()

# Check a medication list
result = checker.reconcile(
    patient_id="patient_123",
    home_medications=[
        {"name": "lisinopril", "dose": "10mg", "frequency": "daily"},
        {"name": "metformin", "dose": "500mg", "frequency": "twice daily"},
    ],
    hospital_medications=[
        {"name": "lisinopril", "dose": "20mg", "frequency": "daily"},
        {"name": "metformin", "dose": "500mg", "frequency": "twice daily"},
        {"name": "furosemide", "dose": "40mg", "frequency": "daily"},
    ],
    allergies=["penicillin", "sulfa"],
)
```

## Output Schema
```json
{
  "patient_id": "string",
  "changes": [
    {"medication": "lisinopril", "change": "dose_increase", "from": "10mg", "to": "20mg"}
  ],
  "new_medications": [{"name": "furosemide", "dose": "40mg", "frequency": "daily"}],
  "discontinued": [],
  "interactions": [],
  "allergy_conflicts": [],
  "adherence_risk": "low|moderate|high",
  "discharge_medList": [...]
}
```
