# Anomaly Detection Skill

## Description
Detects anomalies in patient vital signs and health metrics using statistical methods (Z-score, IQR) and ML-based approaches (Isolation Forest). Used by the `monitor_agent` node in the discharge orchestration graph.

## When to Use
- Real-time vital sign monitoring post-discharge
- Detecting deterioration before it becomes critical
- Alerting care team to concerning trends

## How to Run

```python
from skills.anomaly_detection.scripts.detector import AnomalyDetector

detector = AnomalyDetector()

# Z-score detection
result = detector.detect_zscore(
    value=110,
    metric="heart_rate",
    mean=72,
    std=10,
    threshold=2.0,
)

# IQR detection
result = detector.detect_iqr(
    values=[120, 125, 118, 130, 195, 122],
    metric="systolic_bp",
)

# Batch detection with Isolation Forest
result = detector.detect_isolation_forest(
    data=[
        {"heart_rate": 72, "spo2": 98, "temperature": 98.6},
        {"heart_rate": 75, "spo2": 97, "temperature": 98.8},
        {"heart_rate": 110, "spo2": 92, "temperature": 101.2},
    ],
    contamination=0.1,
)
```
