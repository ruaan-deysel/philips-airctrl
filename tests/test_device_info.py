"""Tests for the device_info module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml

from philips_airctrl.device_info import (
    CONTROL_FIELD_KEYS,
    DEVICE_FIELD_KEYS,
    DEVICE_FIELDS,
    FILTER_FIELD_KEYS,
    SENSOR_FIELD_KEYS,
    DeviceInfoExtractor,
    analyze_capabilities,
    generate_ha_config,
    get_field_category,
)
from philips_airctrl.models import DeviceCapabilities, DeviceReport, FieldDefinition


class TestGetFieldCategory:
    def test_device_fields(self):
        for key in DEVICE_FIELD_KEYS:
            assert get_field_category(key) == "device"

    def test_sensor_fields(self):
        for key in SENSOR_FIELD_KEYS:
            assert get_field_category(key) == "sensors"

    def test_control_fields(self):
        for key in CONTROL_FIELD_KEYS:
            assert get_field_category(key) == "controls"

    def test_filter_fields(self):
        for key in FILTER_FIELD_KEYS:
            assert get_field_category(key) == "filters"

    def test_unknown_field(self):
        assert get_field_category("unknown_key") == "system"
        assert get_field_category("Runtime") == "system"


class TestAnalyzeCapabilities:
    def test_empty_status(self):
        caps = analyze_capabilities({})
        assert caps.has_humidifier is False
        assert caps.has_purifier is False
        assert caps.has_pm25_sensor is False
        assert caps.filter_types == []

    def test_full_status(self):
        status = {
            "D0312A": True,
            "D0312B": True,
            "D03103": 25,
            "D03110": 50,
            "D03105": 10,
            "D03106": 5,
            "D03120": 3,
            "D03180": True,
            "D03182": True,
            "D01213": 1,
            "D0311F": True,
            "D03211": True,
            "D03221": 1,
            "D03240": True,
            "D03130": 80,
            "D03134": 90,
            "D03135": 70,
            "D03136": 60,
        }
        caps = analyze_capabilities(status)
        assert caps.has_humidifier is True
        assert caps.has_purifier is True
        assert caps.has_pm25_sensor is True
        assert caps.has_humidity_sensor is True
        assert caps.has_allergen_sensor is True
        assert caps.has_gas_sensor is True
        assert caps.has_display is True
        assert caps.has_timer is True
        assert caps.has_schedule is True
        assert caps.has_child_lock is True
        assert caps.has_sleep_mode is True
        assert caps.has_turbo_mode is True
        assert caps.has_allergen_mode is True
        assert caps.has_bacteria_virus_mode is True
        assert "main_filter" in caps.filter_types
        assert "pre_filter" in caps.filter_types
        assert "hepa_filter" in caps.filter_types
        assert "carbon_filter" in caps.filter_types

    def test_pm25_via_d03224(self):
        caps = analyze_capabilities({"D03224": 15})
        assert caps.has_pm25_sensor is True

    def test_display_via_d03122(self):
        caps = analyze_capabilities({"D03122": True})
        assert caps.has_display is True


class TestGenerateHAConfig:
    def test_basic(self):
        status = {"D01S05": "AC4220", "D01S03": "Living Room", "DeviceId": "abc123"}
        config = generate_ha_config("192.168.1.100", status)

        assert config.platform == "philips_airpurifier"
        assert config.host == "192.168.1.100"
        assert config.name == "Living Room"
        assert config.model == "AC4220"
        assert config.unique_id == "abc123"
        assert config.device_info.name == "Living Room"
        assert config.device_info.manufacturer == "Philips"

    def test_with_purifier(self):
        status = {"D0312B": True}
        config = generate_ha_config("192.168.1.100", status)
        assert "fan_speed" in config.supported_features
        assert "power" in config.supported_features

    def test_with_humidifier(self):
        status = {"D0312A": True}
        config = generate_ha_config("192.168.1.100", status)
        assert "humidity_target" in config.supported_features

    def test_with_display(self):
        status = {"D03120": 3}
        config = generate_ha_config("192.168.1.100", status)
        assert "display_brightness" in config.supported_features

    def test_with_pm25_sensor(self):
        status = {"D03224": 15}
        config = generate_ha_config("192.168.1.100", status)
        assert len(config.sensors) == 1
        assert config.sensors[0].name == "PM2.5"

    def test_with_humidity_sensor(self):
        status = {"D03110": 50}
        config = generate_ha_config("192.168.1.100", status)
        assert any(s.name == "Humidity" for s in config.sensors)

    def test_with_main_filter(self):
        status = {"D03130": 80}
        config = generate_ha_config("192.168.1.100", status)
        assert any(s.name == "Filter Life" for s in config.sensors)

    def test_defaults_without_info(self):
        config = generate_ha_config("192.168.1.100", {})
        assert config.name == "Air Purifier"
        assert config.model == "Unknown"
        assert config.unique_id == "philips_192_168_1_100"

    def test_sw_hw_version_defaults(self):
        config = generate_ha_config("192.168.1.100", {})
        assert config.device_info.sw_version == "Unknown"
        assert config.device_info.hw_version == "Unknown"

    def test_no_filter_sensor_for_non_main(self):
        status = {"D03134": 90}  # pre_filter only
        config = generate_ha_config("192.168.1.100", status)
        # pre_filter is in filter_types but shouldn't create sensor
        assert not any(s.name == "Filter Life" for s in config.sensors)


class TestDeviceInfoExtractor:
    def test_init(self):
        extractor = DeviceInfoExtractor("192.168.1.100", 5683)
        assert extractor.host == "192.168.1.100"
        assert extractor.port == 5683

    def test_init_default_port(self):
        extractor = DeviceInfoExtractor("192.168.1.100")
        assert extractor.port == 5683

    @pytest.mark.asyncio
    async def test_get_device_info(self):
        mock_client = AsyncMock()
        mock_client.get_status.return_value = (
            {
                "D01S03": "Living Room",
                "D01S05": "AC4220",
                "D03102": True,
                "D03103": 25,
                "D03130": 80,
                "UnknownField": "test",
            },
            120,
        )

        with patch("philips_airctrl.device_info.Client.create", return_value=mock_client):
            extractor = DeviceInfoExtractor("192.168.1.100")
            report = await extractor.get_device_info()

        assert isinstance(report, DeviceReport)
        assert report.connection.host == "192.168.1.100"
        assert report.connection.max_age == 120
        assert "device_name" in report.device
        assert "model_number" in report.device
        assert "power" in report.controls
        assert "pm25_sensor" in report.sensors
        assert "filter_life" in report.filters
        assert "UnknownField" in report.system
        assert report.system["UnknownField"].description == "Unknown field"
        mock_client.shutdown.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_device_info_shutdown_on_error(self):
        mock_client = AsyncMock()
        mock_client.get_status.side_effect = Exception("connection failed")

        with (
            patch("philips_airctrl.device_info.Client.create", return_value=mock_client),
            pytest.raises(Exception, match="connection failed"),
        ):
            extractor = DeviceInfoExtractor("192.168.1.100")
            await extractor.get_device_info()

        mock_client.shutdown.assert_called_once()

    def test_export_json_pretty(self):
        from philips_airctrl.models import ConnectionInfo

        extractor = DeviceInfoExtractor("192.168.1.100")
        report = DeviceReport(
            connection=ConnectionInfo(host="192.168.1.100", port=5683, max_age=60),
        )
        json_str = extractor.export_json(report, pretty=True)
        assert "192.168.1.100" in json_str
        assert "\n" in json_str  # Pretty printed

    def test_export_json_compact(self):
        from philips_airctrl.models import ConnectionInfo

        extractor = DeviceInfoExtractor("192.168.1.100")
        report = DeviceReport(
            connection=ConnectionInfo(host="192.168.1.100", port=5683, max_age=60),
        )
        json_str = extractor.export_json(report, pretty=False)
        assert "192.168.1.100" in json_str

    def test_export_yaml(self):
        from philips_airctrl.models import ConnectionInfo

        extractor = DeviceInfoExtractor("192.168.1.100")
        report = DeviceReport(
            connection=ConnectionInfo(host="192.168.1.100", port=5683, max_age=60),
        )
        yaml_str = extractor.export_yaml(report)
        data = yaml.safe_load(yaml_str)
        assert data["connection"]["host"] == "192.168.1.100"


class TestDeviceFieldsDefinitions:
    def test_all_fields_have_required_attributes(self):
        for key, field in DEVICE_FIELDS.items():
            assert isinstance(field, FieldDefinition)
            assert field.name
            assert field.type in ("string", "integer", "boolean")
            assert field.description

    def test_field_count(self):
        assert len(DEVICE_FIELDS) > 40
