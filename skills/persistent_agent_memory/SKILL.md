# Persistent Agent Memory

## Description
File-based JSON key-value store for agent state persistence. Used by `StateSchema.save()` and `StateSchema.load_latest()` in the healthcare orchestration layer.

## When to Use
- Persisting orchestration state between sessions
- Storing agent memory that survives restarts
- Caching patient data for quick retrieval

## How to Run

```python
from skills.persistent_agent_memory.scripts.memory_store import save_memory, load_memory, clear_memory

# Save state
save_memory("patient:12345:latest", {"risk_score": 0.72, "status": "discharged"})

# Load state
state = load_memory("patient:12345:latest")

# Clear all
clear_memory()
```

## Limitations
- Single JSON file (no concurrency safety)
- No encryption (upgrade to HIPAA-compliant store for production)
- No TTL/expiration
- Not suitable for high-throughput scenarios

## Production Upgrade Path
- Replace with Redis for low-latency access
- Replace with PostgreSQL for durability and querying
- Add AES-256 encryption for PHI data
- Add file locking for concurrent access
