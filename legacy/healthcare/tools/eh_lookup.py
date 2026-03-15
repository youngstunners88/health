def lookup_ehr(patient_id: str):
    """Wrapper for MCP EHR lookup"""
    # In production, this would call an MCP client
    # For now, return mock data
    return {
        "patient_id": patient_id,
        "name": "John Doe",
        "diagnoses": ["CHF", "T2DM"],
        "vitals": {"bp": "148/92", "hr": 88}
    }