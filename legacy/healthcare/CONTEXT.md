# Healthcare Workspace

**Goal**: Build agentic healthcare infrastructure—multi-agent orchestration, secure tool access via MCP, and agent‑to‑agent communication for care coordination, discharge orchestration, and related workflows.

**Tone**: Technical, precise, security‑ and compliance‑focused; emphasize reproducibility, auditability, and HIPAA‑like safeguards.

**Typical Stack**:
- Language: Python (≥3.9)
- Orchestration: LangGraph (StateGraph) for dynamic agent graphs
- Context Bridge: MCP (Model Context Protocol) server(s) for secure tool/drug/claims lookups
- Agent Comm: A2A (agent‑to‑agent) protocol with signed messages
- State Layer: Pydantic models (StateSchema) persisted via Redis or Postgres
- Security: Least‑privilege via MCP access controls, AES‑256 payload encryption, JWT per agent, immutable audit logs (e.g., append‑only store or blockchain‑lite)
- Infrastructure: Docker containers, Kubernetes (or Docker‑Compose for dev), AWS/GCP VPC, Secrets Manager, LangSmith + Prometheus monitoring
- CI/CD: GitHub Actions → Helm/ArgoCD
- Testing: Pytest, property‑based testing, chaos tests
- Docs: Markdown, Mermaid diagrams

**Routing Keywords**: healthcare, agentic, EHR, electronic health record, discharge, care coordination, patient intake, risk scoring, payer, claims, follow‑up, monitoring, LangGraph, MCP, A2A, multi‑agent, swarm, orchestration, supervisor, HIPAA, PHI, audit, encryption, JWT, Redis, Postgres, Docker, Kubernetes, Helm, ArgoCD, GitHub Actions, LangSmith, Prometheus, pytest, StateSchema, Pydantic, tool wrapper, ehr_lookup, claims_check, vitals monitoring.

When a task mentions any of the above, place instructions/files in this workspace and reference the path.