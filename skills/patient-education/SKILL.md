# Patient Education Skill

## Description
Generates patient-friendly educational materials about conditions, medications, procedures, and self-care. Adapts reading level and language to the patient's needs.

## When to Use
- Creating discharge instructions
- Explaining conditions to patients
- Generating medication guides
- Creating self-care instruction sheets

## How to Run

```python
from skills.patient_education.scripts.educator import PatientEducator

educator = PatientEducator()

# Generate condition education
material = educator.generate_condition_material(
    condition="CHF",
    reading_level="6th_grade",  # 6th_grade, 8th_grade, high_school
    language="en",
)

# Generate medication guide
guide = educator.generate_medication_guide(
    medication="furosemide",
    dose="40mg",
    frequency="daily",
    reading_level="6th_grade",
)
```
