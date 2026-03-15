```mermaid
sequenceDiagram
    participant Supervisor as Orchestrator (LangGraph)
    participant Intake as Intake Agent
    participant Risk as Risk Agent
    participant Payer as Payer Agent
    participant Followup as Follow‑up Agent
    participant Monitor as Monitor Agent
    participant MCP as Local MCP Server (stdio/http)

    Supervisor->>Intake: invoke(state)
    Intake->>MCP: call get_patient_ehr(patient_id)
    MCP-->>Intake: return EHR JSON
    Intake->>Supervisor: return state with EHR + log
    Supervisor->>Risk: invoke(state)
    Risk->>Supervisor: compute risk_score + log
    alt risk_score > 0.7
        Supervisor->>Payer: invoke(state)
        Payer->>MCP: call check_payer_rules(patient_id, procedure)
        MCP-->>Payer: return decision JSON
        Payer->>Supervisor: return state + log
    else
        Supervisor->>Followup: invoke(state)
    end
    Supervisor->>Followup: invoke(state)
    Followup->>Supervisor: return follow‑up plan + log
    Supervisor->>Monitor: invoke(state)
    Monitor->>Supervisor: return vitals + log
    Supervisor->>End: return final state
```