import json
import subprocess
from typing import Dict, Any

def call_mcp_tool(tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """Call a local MCP tool via stdio (FastMCP)"""
    # Assumes MCP server is running and accessible via stdio
    # For simplicity, we simulate by importing the server functions directly.
    # In production, use MCP client library.
    if tool_name == "get_patient_ehr":
        from ..protocols.mcp_ehr_server import mcp
        # FastMCP doesn't expose a direct call; we'll mock.
        return {
            "patient_id": args["patient_id"],
            "name": "John Doe",
            "admission_date": "2026-03-15",
            "diagnoses": ["CHF", "T2DM"],
            "vitals": {"bp": "148/92", "hr": 88},
            "audit": "logged_at_2026-03-17"
        }
    elif tool_name == "check_payer_rules":
        return {
            "covered": True,
            "copay": 45,
            "prior_auth": False,
            "notes": "BlueCross approved 90 days post-discharge"
        }
    else:
        raise ValueError(f"Unknown MCP tool: {tool_name}")