from mcp.server.fastmcp import FastMCP
from typing import Dict, Any
import uvicorn
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("mcp_ehr_server")

mcp = FastMCP("healthcare-ehr", json_response=True)

@mcp.tool()
def get_patient_ehr(patient_id: str) -> Dict[str, Any]:
    """MCP tool: secure read-only EHR fetch (mock)"""
    try:
        if not patient_id or not isinstance(patient_id, str):
            raise ValueError("Invalid patient_id")
        logger.info(f"EHR requested for patient_id={patient_id}")
        result = {
            "patient_id": patient_id,
            "name": "John Doe",
            "admission_date": "2026-03-15",
            "diagnoses": ["CHF", "T2DM"],
            "vitals": {"bp": "148/92", "hr": 88},
            "audit": f"logged_at_{datetime.utcnow().date()}"
        }
        logger.info(f"EHR returned for patient_id={patient_id}")
        return result
    except Exception as e:
        logger.error(f"Error in get_patient_ehr: {e}")
        # Return a structured error so agent can handle
        return {"error": str(e), "patient_id": patient_id}

@mcp.tool()
def check_payer_rules(patient_id: str, procedure: str) -> Dict[str, Any]:
    """MCP tool: payer claims check (mock)"""
    try:
        if not patient_id or not procedure:
            raise ValueError("Missing patient_id or procedure")
        logger.info(f"Payer rules checked for patient_id={patient_id}, procedure={procedure}")
        result = {
            "covered": True,
            "copay": 45,
            "prior_auth": False,
            "notes": "BlueCross approved 90 days post-discharge",
            "audit": f"checked_at_{datetime.utcnow().date()}"
        }
        logger.info(f"Payer check completed for patient_id={patient_id}")
        return result
    except Exception as e:
        logger.error(f"Error in check_payer_rules: {e}")
        return {"error": str(e), "patient_id": patient_id}

if __name__ == "__main__":
    print("🚀 Healthcare MCP server running on http://localhost:8001 + stdio")
    # OpenClaw can connect via MCP client or stdio transport
    uvicorn.run("mcp_ehr_server:mcp", host="0.0.0.0", port=8001, log_level="info")