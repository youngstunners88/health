import pytest
from datetime import datetime
from wearables import (
    register_device,
    ingest_reading,
    check_threshold_alerts,
    sync_device,
    get_device_readings,
    get_patient_devices,
    WearableDevice,
    DeviceReading,
    ThresholdAlert,
    DeviceType,
    DeviceStatus,
    DEVICE_THRESHOLDS,
    registered_devices,
    device_readings,
)


@pytest.fixture(autouse=True)
def clear_device_state():
    registered_devices.clear()
    device_readings.clear()
    yield


class TestRegisterDevice:
    def test_registers_device_successfully(self):
        device = register_device("DEV001", "P001", DeviceType.GLUCOMETER)
        assert isinstance(device, WearableDevice)
        assert device.device_id == "DEV001"
        assert device.patient_id == "P001"
        assert device.device_type == DeviceType.GLUCOMETER

    def test_device_status_active(self):
        device = register_device("DEV001", "P001", DeviceType.GLUCOMETER)
        assert device.status == DeviceStatus.ACTIVE

    def test_device_registered_date_set(self):
        device = register_device("DEV001", "P001", DeviceType.GLUCOMETER)
        assert isinstance(device.registered_date, datetime)

    def test_last_sync_initially_none(self):
        device = register_device("DEV001", "P001", DeviceType.GLUCOMETER)
        assert device.last_sync is None

    def test_battery_level_set(self):
        device = register_device(
            "DEV001", "P001", DeviceType.GLUCOMETER, battery_level=85
        )
        assert device.battery_level == 85

    def test_battery_level_none(self):
        device = register_device("DEV001", "P001", DeviceType.GLUCOMETER)
        assert device.battery_level is None

    def test_invalid_battery_level_low(self):
        with pytest.raises(ValueError, match="between 0 and 100"):
            register_device("DEV001", "P001", DeviceType.GLUCOMETER, battery_level=-1)

    def test_invalid_battery_level_high(self):
        with pytest.raises(ValueError, match="between 0 and 100"):
            register_device("DEV001", "P001", DeviceType.GLUCOMETER, battery_level=101)

    def test_valid_battery_boundaries(self):
        device_0 = register_device(
            "DEV001", "P001", DeviceType.GLUCOMETER, battery_level=0
        )
        assert device_0.battery_level == 0
        device_100 = register_device(
            "DEV002", "P001", DeviceType.GLUCOMETER, battery_level=100
        )
        assert device_100.battery_level == 100

    def test_all_device_types(self):
        for dtype in DeviceType:
            device = register_device(f"DEV-{dtype.value}", "P001", dtype)
            assert device.device_type == dtype
            assert device.status == DeviceStatus.ACTIVE

    def test_device_stored_in_registry(self):
        register_device("DEV001", "P001", DeviceType.GLUCOMETER)
        assert "DEV001" in registered_devices

    def test_readings_list_initialized(self):
        register_device("DEV001", "P001", DeviceType.GLUCOMETER)
        assert "DEV001" in device_readings
        assert device_readings["DEV001"] == []


class TestIngestReading:
    @pytest.fixture
    def device(self):
        return register_device("DEV001", "P001", DeviceType.GLUCOMETER)

    def test_ingest_valid_reading(self, device):
        reading = ingest_reading("DEV001", 100.0)
        assert isinstance(reading, DeviceReading)
        assert reading.value == 100.0
        assert reading.device_id == "DEV001"
        assert reading.patient_id == "P001"

    def test_reading_id_format(self, device):
        reading = ingest_reading("DEV001", 100.0)
        assert reading.reading_id.startswith("R-DEV001-")

    def test_reading_timestamp_set(self, device):
        reading = ingest_reading("DEV001", 100.0)
        assert isinstance(reading.timestamp, datetime)

    def test_custom_timestamp(self, device):
        custom_ts = datetime(2025, 1, 1, 12, 0, 0)
        reading = ingest_reading("DEV001", 100.0, timestamp=custom_ts)
        assert reading.timestamp == custom_ts

    def test_reading_metadata(self, device):
        reading = ingest_reading("DEV001", 100.0, metadata={"source": "manual"})
        assert reading.metadata == {"source": "manual"}

    def test_metadata_defaults_to_empty_dict(self, device):
        reading = ingest_reading("DEV001", 100.0)
        assert reading.metadata == {}

    def test_unit_set_from_thresholds(self, device):
        reading = ingest_reading("DEV001", 100.0)
        assert reading.unit == "mg/dL"

    def test_reading_stored_in_device_readings(self, device):
        ingest_reading("DEV001", 100.0)
        readings = get_device_readings("DEV001")
        assert len(readings) == 1

    def test_multiple_readings(self, device):
        ingest_reading("DEV001", 100.0)
        ingest_reading("DEV001", 105.0)
        ingest_reading("DEV001", 98.0)
        readings = get_device_readings("DEV001")
        assert len(readings) == 3

    def test_unregistered_device_raises(self):
        with pytest.raises(ValueError, match="not registered"):
            ingest_reading("UNKNOWN", 100.0)

    def test_inactive_device_raises(self):
        register_device("DEV001", "P001", DeviceType.GLUCOMETER)
        registered_devices["DEV001"].status = DeviceStatus.INACTIVE
        with pytest.raises(ValueError, match="not active"):
            ingest_reading("DEV001", 100.0)

    def test_value_below_range_raises(self, device):
        with pytest.raises(ValueError, match="out of range"):
            ingest_reading("DEV001", 10.0)

    def test_value_above_range_raises(self, device):
        with pytest.raises(ValueError, match="out of range"):
            ingest_reading("DEV001", 500.0)

    def test_blood_pressure_reading(self):
        register_device("DEV002", "P001", DeviceType.BLOOD_PRESSURE)
        reading = ingest_reading("DEV002", 120.0)
        assert reading.value == 120.0
        assert "mmHg" in reading.unit

    def test_heart_rate_reading(self):
        register_device("DEV003", "P001", DeviceType.HEART_RATE)
        reading = ingest_reading("DEV003", 72.0)
        assert reading.value == 72.0
        assert reading.unit == "bpm"

    def test_pulse_oximeter_reading(self):
        register_device("DEV004", "P001", DeviceType.PULSE_OXIMETER)
        reading = ingest_reading("DEV004", 98.0)
        assert reading.value == 98.0
        assert reading.unit == "%"

    def test_updates_last_sync(self, device):
        assert device.last_sync is None
        ingest_reading("DEV001", 100.0)
        assert device.last_sync is not None


class TestCheckThresholdAlerts:
    @pytest.fixture
    def device(self):
        return register_device("DEV001", "P001", DeviceType.GLUCOMETER)

    def test_no_alert_for_normal_value(self, device):
        alert = check_threshold_alerts("DEV001", 100.0)
        assert alert is None

    def test_warning_for_above_normal(self, device):
        alert = check_threshold_alerts("DEV001", 190.0)
        assert alert is not None
        assert alert.severity == "warning"
        assert "above normal" in alert.message.lower()

    def test_warning_for_below_normal(self, device):
        alert = check_threshold_alerts("DEV001", 65.0)
        assert alert is not None
        assert alert.severity == "warning"
        assert "below normal" in alert.message.lower()

    def test_critical_for_dangerously_high(self, device):
        alert = check_threshold_alerts("DEV001", 450.0)
        assert alert is not None
        assert alert.severity == "critical"
        assert "dangerously high" in alert.message.lower()

    def test_critical_for_dangerously_low(self, device):
        alert = check_threshold_alerts("DEV001", 40.0)
        assert alert is not None
        assert alert.severity == "critical"
        assert "dangerously low" in alert.message.lower()

    def test_returns_threshold_alert(self, device):
        alert = check_threshold_alerts("DEV001", 200.0)
        assert isinstance(alert, ThresholdAlert)

    def test_alert_has_patient_id(self, device):
        alert = check_threshold_alerts("DEV001", 200.0)
        assert alert.patient_id == "P001"

    def test_alert_has_device_type(self, device):
        alert = check_threshold_alerts("DEV001", 200.0)
        assert alert.device_type == DeviceType.GLUCOMETER

    def test_alert_has_thresholds(self, device):
        alert = check_threshold_alerts("DEV001", 200.0)
        assert alert.threshold_min == 70
        assert alert.threshold_max == 180

    def test_alert_has_created_at(self, device):
        alert = check_threshold_alerts("DEV001", 200.0)
        assert isinstance(alert.created_at, datetime)

    def test_unregistered_device_returns_none(self):
        alert = check_threshold_alerts("UNKNOWN", 100.0)
        assert alert is None

    def test_blood_pressure_alert(self):
        register_device("DEV002", "P001", DeviceType.BLOOD_PRESSURE)
        alert = check_threshold_alerts("DEV002", 190.0)
        assert alert is not None
        assert alert.severity == "critical"

    def test_heart_rate_alert(self):
        register_device("DEV003", "P001", DeviceType.HEART_RATE)
        alert = check_threshold_alerts("DEV003", 150.0)
        assert alert is not None
        assert alert.severity == "critical"

    def test_boundary_normal_value(self, device):
        alert = check_threshold_alerts("DEV001", 180.0)
        assert alert is None

    def test_boundary_warning_value(self, device):
        alert = check_threshold_alerts("DEV001", 181.0)
        assert alert is not None
        assert alert.severity == "warning"


class TestSyncDevice:
    @pytest.fixture
    def device(self):
        return register_device("DEV001", "P001", DeviceType.GLUCOMETER)

    def test_syncs_device(self, device):
        assert device.last_sync is None
        synced = sync_device("DEV001")
        assert synced.last_sync is not None

    def test_status_remains_active(self, device):
        synced = sync_device("DEV001")
        assert synced.status == DeviceStatus.ACTIVE

    def test_reactivates_sync_error_device(self, device):
        device.status = DeviceStatus.SYNC_ERROR
        synced = sync_device("DEV001")
        assert synced.status == DeviceStatus.ACTIVE

    def test_returns_wearable_device(self, device):
        synced = sync_device("DEV001")
        assert isinstance(synced, WearableDevice)

    def test_unregistered_device_raises(self):
        with pytest.raises(ValueError, match="not registered"):
            sync_device("UNKNOWN")


class TestGetDeviceReadings:
    @pytest.fixture
    def device(self):
        return register_device("DEV001", "P001", DeviceType.GLUCOMETER)

    def test_empty_initially(self, device):
        readings = get_device_readings("DEV001")
        assert readings == []

    def test_returns_readings_after_ingest(self, device):
        ingest_reading("DEV001", 100.0)
        ingest_reading("DEV001", 105.0)
        readings = get_device_readings("DEV001")
        assert len(readings) == 2

    def test_unregistered_device_raises(self):
        with pytest.raises(ValueError, match="not registered"):
            get_device_readings("UNKNOWN")


class TestGetPatientDevices:
    def test_returns_devices_for_patient(self):
        register_device("DEV001", "P001", DeviceType.GLUCOMETER)
        register_device("DEV002", "P001", DeviceType.HEART_RATE)
        register_device("DEV003", "P002", DeviceType.BLOOD_PRESSURE)

        devices = get_patient_devices("P001")
        assert len(devices) == 2

    def test_returns_empty_for_unknown_patient(self):
        devices = get_patient_devices("UNKNOWN")
        assert len(devices) == 0

    def test_returns_wearable_device_list(self):
        register_device("DEV001", "P001", DeviceType.GLUCOMETER)
        devices = get_patient_devices("P001")
        assert all(isinstance(d, WearableDevice) for d in devices)
