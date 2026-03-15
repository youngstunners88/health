# Health Monitoring Skill

## Description
Comprehensive health monitoring for post-discharge patients. Tracks vital signs, activity, sleep, and medication adherence. Integrates with wearable devices and home monitoring equipment.

## When to Use
- Post-discharge patient monitoring
- Chronic disease management
- Remote patient monitoring programs

## How to Run

```python
from skills.health_monitoring.scripts.monitor import HealthMonitor

monitor = HealthMonitor()

# Record a vital reading
monitor.record_vital(
    patient_id="patient_123",
    metric="heart_rate",
    value=78,
    unit="bpm",
    source="wearable",
)

# Get monitoring summary
summary = monitor.get_monitoring_summary(
    patient_id="patient_123",
    hours=24,
)

# Check for alerts
alerts = monitor.check_alerts(
    patient_id="patient_123",
)
```
