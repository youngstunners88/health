# Healthcare Platform Architecture

## Clean Architecture Layers

```
healthcare/
├── core/                          # Framework-agnostic business rules
│   ├── domain/                    # Entities, value objects, enums
│   │   └── models.py              # Patient, Vitals, Claim, Alert, etc.
│   ├── service/                   # Abstract service base
│   │   └── base.py                # BaseService (state, events, logging)
│   ├── state/                     # Centralized state management
│   │   └── store.py               # StateStore (cache + persist + pub/sub)
│   ├── config/                    # Platform configuration
│   │   └── settings.py            # Config (env vars, service URLs)
│   └── infrastructure/            # Cross-cutting infrastructure
│       └── registry.py            # ServiceRegistry (discovery, health)
│
├── modules/                       # Domain modules (one per service)
│   ├── patient-portal/            # Patient-facing portal
│   ├── care-dashboard/            # Provider dashboard
│   ├── prior-auth/                # Prior authorization
│   ├── revenue-cycle/             # Claims & billing
│   ├── sdoh/                      # Social determinants of health
│   ├── wearables/                 # IoT device integration
│   ├── notifications/             # SMS/WhatsApp alerts
│   ├── clinical-trials/           # Trial matching
│   ├── marketplace/               # Plugin/skill registry
│   └── compliance/                # HIPAA, SOC2, FDA
│       ├── domain/                # Module-specific entities
│       ├── service/               # Module business logic (extends BaseService)
│       └── api/                   # HTTP API (FastAPI)
│
├── shared/                        # Cross-module shared code
│   ├── models.py                  # Shared request/response schemas
│   ├── utils.py                   # Common utilities
│   ├── middleware.py              # Auth, CORS, rate limiting
│   └── events/                    # Event bus
│       └── bus.py                 # EventBus (pub/sub, retry, audit)
│
├── tests/                         # Test suite
│   ├── unit/                      # Unit tests
│   └── integration/               # Integration tests
│
└── data/                          # Runtime data (gitignored)
    ├── state/                     # Centralized state store
    ├── events/                    # Event log (JSONL)
    └── logs/                      # Application logs
```

## Data Flow

```
Client → Gateway (8000) → Module API → Module Service → Domain Logic
                                    ↓
                              State Store (cache + disk)
                                    ↓
                              Event Bus → Other Services
                                    ↓
                              Infrastructure (DB, external APIs)
```

## Service Communication

Services communicate through two channels:

1. **Synchronous** — HTTP via API Gateway (request/response)
2. **Asynchronous** — Event Bus (fire-and-forget with retry)

### Standard Events

| Event | Emitted By | Consumed By |
|---|---|---|
| `patient.discharged` | Orchestration | Portal, Dashboard, Notifications |
| `vitals.recorded` | Wearables, Portal | Dashboard, Anomaly Detection |
| `vitals.alert` | Anomaly Detection | Dashboard, Notifications |
| `prior_auth.submitted` | Prior Auth | Revenue Cycle |
| `claim.submitted` | Revenue Cycle | Dashboard |
| `sdoh.screened` | SDOH | Care Coordination |
| `device.registered` | Wearables | Monitoring |
| `notification.sent` | Notifications | Audit Log |

## State Management

All state flows through the centralized `StateStore`:

```python
from healthcare.core.state.store import state_store

# Set with namespace
state_store.set("patient_123", {...}, namespace="patients", ttl=3600)

# Get
patient = state_store.get("patient_123", namespace="patients")

# Subscribe to changes
state_store.subscribe("patients", lambda k, action, v: print(f"{k} {action}"))
```

## Service Pattern

Every module service extends `BaseService`:

```python
from healthcare.core.service.base import BaseService

class PriorAuthService(BaseService):
    SERVICE_NAME = "prior_auth"
    NAMESPACE = "prior_auth"

    def submit_auth(self, data: dict) -> dict:
        try:
            # Domain logic
            auth = self._create_auth(data)
            # Persist state
            self.set_state(auth["id"], auth)
            # Emit event
            self.emit_event("submitted", {"auth_id": auth["id"]})
            return auth
        except Exception as e:
            return self.handle_error("submit_auth", e)
```

## Service Ports

| Service | Port | Purpose |
|---|---|---|
| API Gateway | 8000 | Unified entry point, proxy, aggregation |
| MCP EHR Server | 8001 | EHR data via MCP protocol |
| Patient Portal | 8080 | Patient-facing web app |
| Care Dashboard | 8081 | Provider monitoring dashboard |
| Prior Auth | 8082 | Authorization management |
| Revenue Cycle | 8083 | Claims & billing |
| SDOH | 8084 | Social determinants screening |
| Wearables | 8085 | IoT device integration |
| Notifications | 8086 | SMS/WhatsApp alerts |
| Clinical Trials | 8087 | Trial matching |
| Marketplace | 8088 | Plugin/skill registry |
| Compliance | 8089 | HIPAA/SOC2/FDA auditing |
