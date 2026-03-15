import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from workspaces.healthcare.orchestration.graph import app
from workspaces.healthcare.orchestration.state import StateSchema

def test_handoff_flow():
    initial = {"patient_id": "test-001"}
    final = app.invoke(initial)
    assert final["patient_id"] == "test-001"
    assert "risk_score" in final
    assert len(final["handoff_log"]) >= 4