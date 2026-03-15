import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from workspaces.healthcare.orchestration.graph import app
from workspaces.healthcare.orchestration.state import StateSchema

def test_intake_mcp_error(monkeypatch):
    """Simulate MCP error in intake agent"""
    def mock_call_mcp_tool(tool_name, args):
        if tool_name == "get_patient_ehr":
            return {"error": "MCP connection failed"}
        return {}
    monkeypatch.setattr("workspaces.healthcare.orchestration.graph.call_mcp_tool", mock_call_mcp_tool)
    
    initial = {"patient_id": "err-001"}
    final = app.invoke(initial)
    # Should still return a state, with empty patient_ehr
    assert final["patient_id"] == "err-001"
    assert final["patient_ehr"] == {}
    # The handoff log should contain an intake entry (even if output empty)
    assert any(entry.get("agent") == "intake" for entry in final["handoff_log"])

def test_payer_mcp_error(monkeypatch):
    """Simulate MCP error in payer agent"""
    def mock_call_mcp_tool(tool_name, args):
        if tool_name == "check_payer_rules":
            return {"error": "Payer service down"}
        # For get_patient_ehr return normal
        if tool_name == "get_patient_ehr":
            return {
                "patient_id": args["patient_id"],
                "name": "John Doe",
                "admission_date": "2026-03-15",
                "diagnoses": ["CHF", "T2DM"],
                "vitals": {"bp": "148/92", "hr": 88},
                "audit": "logged_at_2026-03-17"
            }
        return {}
    monkeypatch.setattr("workspaces.healthcare.orchestration.graph.call_mcp_tool", mock_call_mcp_tool)
    
    initial = {"patient_id": "err-002"}
    final = app.invoke(initial)
    assert final["patient_id"] == "err-002"
    assert final["payer_decision"] == {}
    assert any(entry.get("agent") == "payer" for entry in final["handoff_log"])