import pytest
import math
from anomaly_detection import (
    zscore_anomaly_detection,
    iqr_anomaly_detection,
    check_vital,
    multivariate_anomaly_detection,
    AnomalyResult,
    VitalCheckResult,
    MultivariateAnomalyResult,
    AnomalyMethod,
)


class TestZScoreAnomalyDetection:
    @pytest.fixture
    def normal_values(self):
        return [100.0, 102.0, 98.0, 101.0, 99.0, 100.0, 103.0, 97.0]

    def test_normal_value_not_anomaly(self, normal_values):
        result = zscore_anomaly_detection(normal_values, 100.0)
        assert result.is_anomaly is False

    def test_extreme_value_is_anomaly(self, normal_values):
        result = zscore_anomaly_detection(normal_values, 200.0)
        assert result.is_anomaly is True

    def test_returns_anomaly_result(self, normal_values):
        result = zscore_anomaly_detection(normal_values, 100.0)
        assert isinstance(result, AnomalyResult)

    def test_zscore_details_included(self, normal_values):
        result = zscore_anomaly_detection(normal_values, 150.0)
        assert "Z-score" in result.details
        assert "threshold" in result.details

    def test_custom_threshold(self, normal_values):
        result_strict = zscore_anomaly_detection(normal_values, 108.0, threshold=1.0)
        result_lenient = zscore_anomaly_detection(normal_values, 108.0, threshold=5.0)
        assert result_strict.is_anomaly is True
        assert result_lenient.is_anomaly is False

    def test_expected_range_calculated(self, normal_values):
        result = zscore_anomaly_detection(normal_values, 100.0)
        assert result.expected_min < result.expected_max
        mean = sum(normal_values) / len(normal_values)
        assert abs(result.expected_min + result.expected_max - 2 * mean) < 0.01

    def test_insufficient_values_raises(self):
        with pytest.raises(ValueError, match="At least 2"):
            zscore_anomaly_detection([100.0], 101.0)

    def test_empty_values_raises(self):
        with pytest.raises(ValueError, match="At least 2"):
            zscore_anomaly_detection([], 100.0)

    def test_zero_variance_same_value(self):
        result = zscore_anomaly_detection([100.0, 100.0, 100.0], 100.0)
        assert result.is_anomaly is False

    def test_zero_variance_different_value(self):
        result = zscore_anomaly_detection([100.0, 100.0, 100.0], 105.0)
        assert result.is_anomaly is True
        assert result.method == AnomalyMethod.ZSCORE

    def test_boundary_value(self, normal_values):
        mean = sum(normal_values) / len(normal_values)
        variance = sum((x - mean) ** 2 for x in normal_values) / len(normal_values)
        std_dev = math.sqrt(variance)
        boundary = mean + 2.0 * std_dev
        result = zscore_anomaly_detection(normal_values, boundary)
        assert result.is_anomaly is False

    def test_just_above_boundary(self, normal_values):
        mean = sum(normal_values) / len(normal_values)
        variance = sum((x - mean) ** 2 for x in normal_values) / len(normal_values)
        std_dev = math.sqrt(variance)
        boundary = mean + 2.0 * std_dev + 0.01
        result = zscore_anomaly_detection(normal_values, boundary)
        assert result.is_anomaly is True


class TestIQRAnomalyDetection:
    @pytest.fixture
    def normal_values(self):
        return [95.0, 98.0, 100.0, 101.0, 102.0, 99.0, 97.0, 103.0, 100.0, 96.0]

    def test_normal_value_not_anomaly(self, normal_values):
        result = iqr_anomaly_detection(normal_values, 100.0)
        assert result.is_anomaly is False

    def test_extreme_high_value_is_anomaly(self, normal_values):
        result = iqr_anomaly_detection(normal_values, 200.0)
        assert result.is_anomaly is True

    def test_extreme_low_value_is_anomaly(self, normal_values):
        result = iqr_anomaly_detection(normal_values, 0.0)
        assert result.is_anomaly is True

    def test_returns_anomaly_result(self, normal_values):
        result = iqr_anomaly_detection(normal_values, 100.0)
        assert isinstance(result, AnomalyResult)

    def test_iqr_details_included(self, normal_values):
        result = iqr_anomaly_detection(normal_values, 100.0)
        assert "IQR" in result.details
        assert "Q1" in result.details
        assert "Q3" in result.details

    def test_custom_multiplier(self):
        values = [10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0]
        result_strict = iqr_anomaly_detection(values, 25.0, multiplier=1.0)
        result_lenient = iqr_anomaly_detection(values, 25.0, multiplier=3.0)
        assert result_strict.is_anomaly is True
        assert result_lenient.is_anomaly is False

    def test_insufficient_values_raises(self):
        with pytest.raises(ValueError, match="At least 4"):
            iqr_anomaly_detection([1.0, 2.0, 3.0], 4.0)

    def test_empty_values_raises(self):
        with pytest.raises(ValueError, match="At least 4"):
            iqr_anomaly_detection([], 100.0)

    def test_method_is_iqr(self, normal_values):
        result = iqr_anomaly_detection(normal_values, 100.0)
        assert result.method == AnomalyMethod.IQR

    def test_expected_bounds(self, normal_values):
        result = iqr_anomaly_detection(normal_values, 100.0)
        assert result.expected_min < result.expected_max


class TestCheckVital:
    def test_normal_heart_rate(self):
        result = check_vital("heart_rate", 72)
        assert result.is_critical is False
        assert result.is_anomalous is False
        assert "normal range" in result.message

    def test_critical_high_heart_rate(self):
        result = check_vital("heart_rate", 150)
        assert result.is_critical is True
        assert result.is_anomalous is True
        assert "CRITICAL" in result.message
        assert "high" in result.message.lower()

    def test_critical_low_heart_rate(self):
        result = check_vital("heart_rate", 35)
        assert result.is_critical is True
        assert result.is_anomalous is True
        assert "CRITICAL" in result.message
        assert "low" in result.message.lower()

    def test_warning_high_blood_pressure(self):
        result = check_vital("blood_pressure_systolic", 150)
        assert result.is_critical is False
        assert result.is_anomalous is True
        assert "Warning" in result.message

    def test_critical_high_blood_pressure(self):
        result = check_vital("blood_pressure_systolic", 185)
        assert result.is_critical is True

    def test_normal_temperature(self):
        result = check_vital("temperature", 37.0)
        assert result.is_critical is False
        assert result.is_anomalous is False

    def test_fever_temperature(self):
        result = check_vital("temperature", 39.0)
        assert result.is_anomalous is True
        assert result.is_critical is False

    def test_critical_temperature(self):
        result = check_vital("temperature", 41.0)
        assert result.is_critical is True

    def test_low_oxygen_saturation(self):
        result = check_vital("oxygen_saturation", 90)
        assert result.is_anomalous is True
        assert result.is_critical is True

    def test_high_blood_glucose(self):
        result = check_vital("blood_glucose", 350)
        assert result.is_anomalous is True
        assert result.is_critical is False

    def test_critical_blood_glucose(self):
        result = check_vital("blood_glucose", 450)
        assert result.is_critical is True

    def test_unknown_vital_raises(self):
        with pytest.raises(ValueError, match="Unknown vital sign"):
            check_vital("unknown_vital", 100)

    def test_returns_vital_check_result(self):
        result = check_vital("heart_rate", 72)
        assert isinstance(result, VitalCheckResult)
        assert result.vital_name == "heart_rate"
        assert result.value == 72
        assert result.unit == "bpm"

    def test_respiratory_rate_critical_low(self):
        result = check_vital("respiratory_rate", 6)
        assert result.is_critical is True

    def test_respiratory_rate_critical_high(self):
        result = check_vital("respiratory_rate", 35)
        assert result.is_critical is True

    def test_diastolic_bp_normal(self):
        result = check_vital("blood_pressure_diastolic", 80)
        assert result.is_critical is False
        assert result.is_anomalous is False


class TestMultivariateAnomalyDetection:
    @pytest.fixture
    def baselines(self):
        return {
            "heart_rate": {"mean": 72, "std_dev": 5},
            "blood_pressure_systolic": {"mean": 120, "std_dev": 10},
            "temperature": {"mean": 37.0, "std_dev": 0.3},
            "oxygen_saturation": {"mean": 98, "std_dev": 1},
        }

    def test_normal_readings_not_anomaly(self, baselines):
        readings = {
            "heart_rate": 74,
            "blood_pressure_systolic": 118,
            "temperature": 37.1,
            "oxygen_saturation": 97,
        }
        result = multivariate_anomaly_detection(readings, baselines)
        assert result.is_anomaly is False

    def test_abnormal_readings_anomaly(self, baselines):
        readings = {
            "heart_rate": 130,
            "blood_pressure_systolic": 180,
            "temperature": 40.0,
            "oxygen_saturation": 88,
        }
        result = multivariate_anomaly_detection(readings, baselines)
        assert result.is_anomaly is True

    def test_returns_multivariate_result(self, baselines):
        readings = {"heart_rate": 72}
        result = multivariate_anomaly_detection(readings, baselines)
        assert isinstance(result, MultivariateAnomalyResult)

    def test_contributing_factors_identified(self, baselines):
        readings = {
            "heart_rate": 130,
            "blood_pressure_systolic": 120,
        }
        result = multivariate_anomaly_detection(readings, baselines)
        assert any("heart_rate" in f for f in result.contributing_factors)

    def test_anomaly_score_between_0_and_1(self, baselines):
        readings = {"heart_rate": 72, "temperature": 37.0}
        result = multivariate_anomaly_detection(readings, baselines)
        assert 0.0 <= result.anomaly_score <= 1.0

    def test_custom_threshold(self, baselines):
        readings = {
            "heart_rate": 100,
            "blood_pressure_systolic": 150,
        }
        result_strict = multivariate_anomaly_detection(
            readings, baselines, threshold=0.3
        )
        result_lenient = multivariate_anomaly_detection(
            readings, baselines, threshold=0.9
        )
        assert result_strict.is_anomaly is True
        assert result_lenient.is_anomaly is False

    def test_unknown_vitals_ignored(self, baselines):
        readings = {
            "heart_rate": 72,
            "unknown_metric": 999,
        }
        result = multivariate_anomaly_detection(readings, baselines)
        assert result.anomaly_score >= 0

    def test_empty_readings(self, baselines):
        result = multivariate_anomaly_detection({}, baselines)
        assert result.anomaly_score == 0.0
        assert result.is_anomaly is False

    def test_zero_std_dev_same_value(self):
        baselines = {"heart_rate": {"mean": 72, "std_dev": 0}}
        result = multivariate_anomaly_detection({"heart_rate": 72}, baselines)
        assert result.anomaly_score == 0.0

    def test_zero_std_dev_different_value(self):
        baselines = {"heart_rate": {"mean": 72, "std_dev": 0}}
        result = multivariate_anomaly_detection({"heart_rate": 80}, baselines)
        assert result.anomaly_score > 0

    def test_has_timestamp(self, baselines):
        readings = {"heart_rate": 72}
        result = multivariate_anomaly_detection(readings, baselines)
        assert isinstance(result.timestamp, type(result.timestamp))
