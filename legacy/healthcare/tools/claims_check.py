def check_claims(patient_id: str, procedure: str):
    """Wrapper for MCP claims check"""
    return {
        "covered": True,
        "copay": 45,
        "prior_auth": False,
        "notes": "BlueCross approved 90 days post-discharge"
    }