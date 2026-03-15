"""
Anomaly detection for patient vital signs and health metrics.
Supports Z-score, IQR, and Isolation Forest methods.
"""

from datetime import datetime, timezone
import math


VITAL_NORMALS = {
    "heart_rate": {"mean": 72, "std": 10, "unit": "bpm"},
    "systolic_bp": {"mean": 120, "std": 15, "unit": "mmHg"},
    "diastolic_bp": {"mean": 80, "std": 10, "unit": "mmHg"},
    "spo2": {"mean": 97, "std": 1.5, "unit": "%"},
    "temperature": {"mean": 98.6, "std": 0.5, "unit": "F"},
    "respiratory_rate": {"mean": 16, "std": 2, "unit": "breaths/min"},
    "weight": {"mean": 80, "std": 5, "unit": "kg"},
}


class AnomalyDetector:
    """Detects anomalies in patient health data."""

    def detect_zscore(
        self,
        value: float,
        metric: str,
        mean: float | None = None,
        std: float | None = None,
        threshold: float = 2.0,
    ) -> dict:
        normals = VITAL_NORMALS.get(metric, {})
        used_mean = mean if mean is not None else normals.get("mean", 0)
        used_std = std if std is not None else normals.get("std", 1)

        if used_std == 0:
            used_std = 1

        zscore = (value - used_mean) / used_std
        is_anomaly = abs(zscore) > threshold

        severity = "normal"
        if is_anomaly:
            abs_z = abs(zscore)
            if abs_z > 4:
                severity = "critical"
            elif abs_z > 3:
                severity = "high"
            else:
                severity = "moderate"

        direction = "above" if zscore > 0 else "below"

        return {
            "metric": metric,
            "value": value,
            "expected_mean": used_mean,
            "expected_std": used_std,
            "zscore": round(zscore, 2),
            "is_anomaly": is_anomaly,
            "severity": severity,
            "direction": direction,
            "unit": normals.get("unit", ""),
            "detected_at": datetime.now(timezone.utc).isoformat(),
        }

    def detect_iqr(
        self,
        values: list[float],
        metric: str,
        iqr_multiplier: float = 1.5,
    ) -> dict:
        if len(values) < 4:
            return {
                "metric": metric,
                "is_anomaly": False,
                "message": "Need at least 4 values for IQR detection",
                "detected_at": datetime.now(timezone.utc).isoformat(),
            }

        sorted_vals = sorted(values)
        n = len(sorted_vals)
        q1 = sorted_vals[n // 4]
        q3 = sorted_vals[(3 * n) // 4]
        iqr = q3 - q1

        lower_bound = q1 - (iqr_multiplier * iqr)
        upper_bound = q3 + (iqr_multiplier * iqr)

        anomalies = []
        for i, v in enumerate(values):
            if v < lower_bound or v > upper_bound:
                anomalies.append(
                    {
                        "index": i,
                        "value": v,
                        "bound": "lower" if v < lower_bound else "upper",
                    }
                )

        normals = VITAL_NORMALS.get(metric, {})

        return {
            "metric": metric,
            "q1": q1,
            "q3": q3,
            "iqr": round(iqr, 2),
            "lower_bound": round(lower_bound, 2),
            "upper_bound": round(upper_bound, 2),
            "anomalies": anomalies,
            "is_anomaly": len(anomalies) > 0,
            "unit": normals.get("unit", ""),
            "detected_at": datetime.now(timezone.utc).isoformat(),
        }

    def detect_isolation_forest(
        self,
        data: list[dict],
        contamination: float = 0.1,
    ) -> dict:
        """
        Simplified isolation forest implementation.
        For production, use sklearn.ensemble.IsolationForest.
        """
        if len(data) < 5:
            return {
                "is_anomaly": False,
                "message": "Need at least 5 data points for isolation forest",
                "detected_at": datetime.now(timezone.utc).isoformat(),
            }

        features = list(data[0].keys())
        n = len(data)
        scores = []

        for point in data:
            score = 0.0
            for feature in features:
                values = [d[feature] for d in data if feature in d]
                if not values:
                    continue
                mean = sum(values) / len(values)
                std = (sum((v - mean) ** 2 for v in values) / len(values)) ** 0.5
                if std == 0:
                    continue
                z = abs((point.get(feature, mean) - mean) / std)
                score += z
            scores.append(score / len(features))

        threshold = sorted(scores)[int(n * (1 - contamination))]
        anomalies = []
        for i, (point, score) in enumerate(zip(data, scores)):
            is_anomaly = score > threshold
            if is_anomaly:
                anomalies.append(
                    {
                        "index": i,
                        "score": round(score, 2),
                        "data": point,
                    }
                )

        return {
            "anomalies": anomalies,
            "is_anomaly": len(anomalies) > 0,
            "total_points": n,
            "anomaly_count": len(anomalies),
            "contamination": contamination,
            "detected_at": datetime.now(timezone.utc).isoformat(),
        }

    def check_vitals(
        self,
        vitals: dict,
        custom_thresholds: dict | None = None,
    ) -> dict:
        """Check a set of vitals against normal ranges."""
        thresholds = custom_thresholds or {}
        alerts = []

        for metric, value in vitals.items():
            if metric in VITAL_NORMALS:
                normals = VITAL_NORMALS[metric]
                th = thresholds.get(metric, {})
                result = self.detect_zscore(
                    value=value,
                    metric=metric,
                    mean=th.get("mean", normals["mean"]),
                    std=th.get("std", normals["std"]),
                    threshold=th.get("zscore_threshold", 2.0),
                )
                if result["is_anomaly"]:
                    alerts.append(result)

        return {
            "vitals_checked": len(vitals),
            "alerts": alerts,
            "alert_count": len(alerts),
            "overall_status": "critical"
            if any(a["severity"] == "critical" for a in alerts)
            else "warning"
            if alerts
            else "normal",
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
