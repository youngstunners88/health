# Healthcare Platform

AI-native healthcare orchestration system with 12 domain modules, clean architecture, and autonomous skill execution.

## What It Is

A modular healthcare platform built with Python that orchestrates patient care, clinical trials, compliance, revenue cycle management, and more through a unified API gateway.

## Quick Start

```bash
cd healthcare-platform
pip install -r requirements.txt
python seed.py
python start.py
```

## Architecture

```
healthcare-platform/
├── core/              # Framework-agnostic business rules
│   ├── domain/        # Patient, Vitals, Claim, Alert models
│   ├── service/       # BaseService with state, events, logging
│   ├── state/         # Centralized StateStore
│   ├── config/        # Platform configuration
│   ├── router.py      # Command routing engine
│   └── autosave.py    # Auto-save to vault
├── modules/           # 10 domain microservices
│   ├── patient_portal/      # Patient web app (:8080)
│   ├── care_dashboard/      # Provider dashboard (:8081)
│   ├── prior_auth/          # Prior authorization (:8082)
│   ├── revenue_cycle/       # Claims & billing (:8083)
│   ├── sdoh/                # Social determinants (:8084)
│   ├── wearables/           # IoT devices (:8085)
│   ├── notifications/       # SMS/WhatsApp alerts (:8086)
│   ├── clinical_trials/     # Trial matching (:8087)
│   ├── marketplace/         # Skill registry (:8088)
│   └── compliance/          # HIPAA/SOC2/FDA (:8089)
├── skills/            # 16 healthcare skills
├── tests/             # Test suite
├── deployments/       # Docker, docker-compose
├── shared/            # Cross-module event bus
└── docs/              # Architecture docs
```

## Services

| Service | Port | Purpose |
|---------|------|---------|
| API Gateway | 8000 | Unified entry point |
| MCP EHR Server | 8001 | EHR data via MCP |
| Patient Portal | 8080 | Patient web app |
| Care Dashboard | 8081 | Provider dashboard |
| Prior Auth | 8082 | Authorization automation |
| Revenue Cycle | 8083 | Claims & billing |
| SDOH | 8084 | Social determinants |
| Wearables | 8085 | IoT devices |
| Notifications | 8086 | SMS/WhatsApp alerts |
| Clinical Trials | 8087 | Trial matching |
| Marketplace | 8088 | Skill registry |
| Compliance | 8089 | HIPAA/SOC2/FDA |

## Data

Seeded with 3 patients, 6 prior auths, 2 claims ($25K), 2 SDOH screenings, 6 wearable devices, 13 auto-referrals.

## License

MIT
