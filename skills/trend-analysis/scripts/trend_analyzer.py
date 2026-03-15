"""
Trend analysis for patient vitals and health metrics.
Detects improving, worsening, or stable trends using linear regression and statistical methods.
"""

from datetime import datetime, timezone


class TrendAnalyzer:
    """Analyzes trends in patient health metrics over time."""

    def analyze_trend(
        self,
        patient_id: str,
        metric: str,
        data_points: list[dict],
        metric_name: str | None = None,
        warning_threshold: float | None = None,
        critical_threshold: float | None = None,
    ) -> dict:
        if len(data_points) < 2:
            return {
                "patient_id": patient_id,
                "metric": metric,
                "trend": "insufficient_data",
                "message": "Need at least 2 data points for trend analysis",
                "data_points": len(data_points),
                "analyzed_at": datetime.now(timezone.utc).isoformat(),
            }

        values = [dp["value"] for dp in data_points]
        timestamps = [dp.get("timestamp", "") for dp in data_points]

        slope = self._linear_regression_slope(values)
        direction = self._classify_direction(slope, values)
        volatility = self._calculate_volatility(values)
        alert_level = self._determine_alert_level(
            values[-1], warning_threshold, critical_threshold, direction
        )

        return {
            "patient_id": patient_id,
            "metric": metric,
            "metric_name": metric_name or metric,
            "trend": direction,
            "slope_per_reading": round(slope, 4),
            "current_value": values[-1],
            "previous_value": values[-2],
            "change": round(values[-1] - values[0], 2),
            "percent_change": round(((values[-1] - values[0]) / values[0]) * 100, 1)
            if values[0] != 0
            else 0,
            "volatility": round(volatility, 4),
            "alert_level": alert_level,
            "data_points": len(data_points),
            "range": {"min": min(values), "max": max(values)},
            "timestamps": timestamps,
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        }

    def _linear_regression_slope(self, values: list[float]) -> float:
        n = len(values)
        if n < 2:
            return 0.0
        x_mean = (n - 1) / 2
        y_mean = sum(values) / n
        numerator = sum((i - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((i - x_mean) ** 2 for i in range(n))
        if denominator == 0:
            return 0.0
        return numerator / denominator

    def _classify_direction(self, slope: float, values: list[float]) -> str:
        if len(values) < 2:
            return "stable"
        mean_val = sum(values) / len(values)
        normalized_slope = slope / mean_val if mean_val != 0 else 0

        if abs(normalized_slope) < 0.01:
            return "stable"
        elif normalized_slope > 0:
            return "increasing"
        else:
            return "decreasing"

    def _calculate_volatility(self, values: list[float]) -> float:
        if len(values) < 2:
            return 0.0
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        return variance**0.5

    def _determine_alert_level(
        self,
        current_value: float,
        warning_threshold: float | None,
        critical_threshold: float | None,
        direction: str,
    ) -> str:
        if critical_threshold is not None and current_value >= critical_threshold:
            return "critical"
        if warning_threshold is not None and current_value >= warning_threshold:
            return "warning"
        if direction in ("increasing", "decreasing"):
            return "monitor"
        return "normal"

    def analyze_multiple_metrics(
        self,
        patient_id: str,
        metrics: dict[str, list[dict]],
        thresholds: dict[str, dict] | None = None,
    ) -> dict:
        """Analyze trends for multiple metrics at once."""
        thresholds = thresholds or {}
        results = {}
        overall_alert = "normal"

        for metric, data_points in metrics.items():
            metric_thresholds = thresholds.get(metric, {})
            result = self.analyze_trend(
                patient_id=patient_id,
                metric=metric,
                data_points=data_points,
                **metric_thresholds,
            )
            results[metric] = result

            alert_priority = {
                "critical": 4,
                "warning": 3,
                "monitor": 2,
                "normal": 1,
                "insufficient_data": 0,
            }
            if alert_priority.get(result["alert_level"], 0) > alert_priority.get(
                overall_alert, 0
            ):
                overall_alert = result["alert_level"]

        return {
            "patient_id": patient_id,
            "metrics": results,
            "overall_alert": overall_alert,
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        }
