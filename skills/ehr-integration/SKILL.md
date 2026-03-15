# EHR Integration Skill

## Description
Connects to Electronic Health Record systems via FHIR/HL7 APIs. Retrieves patient demographics, conditions, medications, allergies, encounters, and observations. Used by the `intake_agent` node in the discharge orchestration graph.

## When to Use
- Patient intake to pull clinical history
- Medication reconciliation before discharge
- Retrieving lab results and vital signs
- Checking allergy information

## How to Run

```python
from skills.ehr_integration.scripts.fhir_client import FHIRClient

client = FHIRClient(base_url="https://hapi.fhir.org/baseR4")

# Get full patient record
record = client.get_patient_record("patient-123")

# Get specific resources
conditions = client.get_conditions("patient-123")
medications = client.get_medications("patient-123")
allergies = client.get_allergies("patient-123")
observations = client.get_observations("patient-123", code="8867-4")  # Heart rate
encounters = client.get_encounters("patient-123")
```

## Supported FHIR Resources
- Patient (demographics)
- Condition (diagnoses, problems)
- MedicationRequest (prescriptions)
- AllergyIntolerance (allergies)
- Observation (vitals, labs)
- Encounter (visits, admissions)
- CarePlan (care plans)
- Procedure (procedures performed)

## Configuration
Set `FHIR_SERVER_URL` environment variable or pass `base_url` to the client.
For Epic/Cerner, configure OAuth2 credentials via `FHIR_CLIENT_ID` and `FHIR_CLIENT_SECRET`.
