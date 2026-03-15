# Trend Analysis Skill

## Description
Analyzes trends in patient vitals, lab values, and health metrics over time. Identifies improving, worsening, or stable trends to support clinical decision-making.

## When to Use
- Post-discharge monitoring to detect deterioration
- Evaluating treatment effectiveness
- Generating reports for care team review

## How to Run

```python
from skills.trend_analysis.scripts.trend_analyzer import TrendAnalyzer

analyzer = TrendAnalyzer()

# Analyze a time series of vitals
result = analyzer.analyze_trend(
    patient_id="patient_123",
    metric="weight",
    data_points=[
        {"value": 85.0, "timestamp": "2026-04-01T08:00:00Z"},
        {"value": 85.5, "timestamp": "2026-04-02T08:00:00Z"},
        {"value": 86.2, "timestamp": "2026-04-03T08:00:00Z"},
        {"value": 87.0, "timestamp": "2026-04-04T08:00:00Z"},
    ],
    metric_name="Weight (kg)",
)
```
