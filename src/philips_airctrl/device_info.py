"""Device information extraction and formatting for Home Assistant integration."""

from __future__ import annotations

import logging
from typing import Any

import yaml

from philips_airctrl.coap.client import Client
from philips_airctrl.models import (
    ConnectionInfo,
    DeviceCapabilities,
    DeviceReport,
    FieldDefinition,
    FieldValue,
    HAConfig,
    HADeviceInfo,
    SensorConfig,
)

logger = logging.getLogger(__name__)


# Known device status fields and their meanings
DEVICE_FIELDS: dict[str, FieldDefinition] = {
    # Device identification
    "D01S03": FieldDefinition(name="device_name", type="string", description="Device name"),
    "D01S04": FieldDefinition(name="device_nickname", type="string", description="Device nickname"),
    "D01S05": FieldDefinition(name="model_number", type="string", description="Model number"),
    "D01S0D": FieldDefinition(name="serial_number", type="string", description="Serial number"),
    "D01S12": FieldDefinition(
        name="firmware_version", type="string", description="Firmware version"
    ),
    "DeviceId": FieldDefinition(name="device_id", type="string", description="Unique device ID"),
    "ProductId": FieldDefinition(name="product_id", type="string", description="Product ID"),
    "WifiVersion": FieldDefinition(
        name="wifi_version", type="string", description="WiFi module version"
    ),
    # Device status
    "D01102": FieldDefinition(name="error_code", type="integer", description="Error code"),
    "D01107": FieldDefinition(name="warning_code", type="integer", description="Warning code"),
    "D01108": FieldDefinition(name="device_status", type="integer", description="Device status"),
    "D01109": FieldDefinition(
        name="connection_status", type="integer", description="Connection status"
    ),
    "D0110A": FieldDefinition(
        name="update_available", type="integer", description="Update available"
    ),
    "D0110C": FieldDefinition(
        name="temperature", type="integer", description="Temperature (\u00b0C)"
    ),
    "D0110F": FieldDefinition(name="language", type="integer", description="Language setting"),
    "D01213": FieldDefinition(name="child_lock", type="integer", description="Child lock status"),
    # Air quality and sensors
    "D03102": FieldDefinition(name="power", type="boolean", description="Power on/off"),
    "D03103": FieldDefinition(name="pm25_sensor", type="integer", description="PM2.5 sensor value"),
    "D03105": FieldDefinition(
        name="allergen_sensor", type="integer", description="Allergen sensor value"
    ),
    "D03106": FieldDefinition(name="gas_sensor", type="integer", description="Gas sensor value"),
    "D0310A": FieldDefinition(name="fan_speed", type="integer", description="Fan speed setting"),
    "D0310C": FieldDefinition(
        name="target_humidity", type="integer", description="Target humidity (%)"
    ),
    "D0310D": FieldDefinition(name="water_level", type="integer", description="Water level"),
    "D03110": FieldDefinition(
        name="humidity_sensor", type="integer", description="Humidity sensor value (%)"
    ),
    "D03115": FieldDefinition(name="auto_mode", type="boolean", description="Auto mode enabled"),
    "D0311F": FieldDefinition(name="sleep_mode", type="boolean", description="Sleep mode enabled"),
    "D03120": FieldDefinition(
        name="display_brightness", type="integer", description="Display brightness"
    ),
    "D03122": FieldDefinition(
        name="display_enabled", type="boolean", description="Display enabled"
    ),
    "D03125": FieldDefinition(
        name="current_humidity", type="integer", description="Current humidity (%)"
    ),
    "D0312A": FieldDefinition(
        name="humidifier_enabled", type="boolean", description="Humidifier enabled"
    ),
    "D0312B": FieldDefinition(
        name="purifier_enabled", type="boolean", description="Purifier enabled"
    ),
    "D0312C": FieldDefinition(
        name="air_quality_index", type="integer", description="Air quality index"
    ),
    "D03112": FieldDefinition(
        name="function_mode", type="integer", description="Function mode setting"
    ),
    "D03130": FieldDefinition(
        name="filter_life", type="integer", description="Filter life remaining (%)"
    ),
    "D03134": FieldDefinition(
        name="pre_filter_life", type="integer", description="Pre-filter life remaining (%)"
    ),
    "D03135": FieldDefinition(
        name="hepa_filter_life", type="integer", description="HEPA filter life remaining (%)"
    ),
    "D03136": FieldDefinition(
        name="carbon_filter_life", type="integer", description="Carbon filter life remaining (%)"
    ),
    "D03137": FieldDefinition(
        name="wick_filter_life",
        type="integer",
        description="Wick/humidifier filter life remaining (%)",
    ),
    "D03180": FieldDefinition(name="timer_enabled", type="boolean", description="Timer enabled"),
    "D03182": FieldDefinition(
        name="schedule_enabled", type="boolean", description="Schedule enabled"
    ),
    "D0313B": FieldDefinition(
        name="timer_remaining", type="integer", description="Timer remaining (minutes)"
    ),
    # Advanced features
    "D03211": FieldDefinition(name="turbo_mode", type="boolean", description="Turbo mode enabled"),
    "D03221": FieldDefinition(
        name="allergen_mode", type="integer", description="Allergen mode setting"
    ),
    "D03224": FieldDefinition(
        name="pm25_value", type="integer", description="PM2.5 value (\u03bcg/m\u00b3)"
    ),
    "D03240": FieldDefinition(
        name="bacteria_virus_mode", type="boolean", description="Bacteria/virus mode"
    ),
    "D03R81": FieldDefinition(
        name="schedule_data", type="string", description="Schedule/mode data (base64)"
    ),
    # System information
    "Runtime": FieldDefinition(
        name="runtime", type="integer", description="Device runtime (seconds)"
    ),
    "rssi": FieldDefinition(
        name="wifi_signal", type="integer", description="WiFi signal strength (dBm)"
    ),
    "free_memory": FieldDefinition(
        name="free_memory", type="integer", description="Free memory (bytes)"
    ),
    "StatusType": FieldDefinition(
        name="status_type", type="string", description="Status message type"
    ),
    "ConnectType": FieldDefinition(
        name="connect_type", type="string", description="Connection type"
    ),
    # Filter and maintenance
    "D05102": FieldDefinition(name="filter_type", type="integer", description="Filter type"),
    "D05207": FieldDefinition(
        name="filter_usage_hours", type="integer", description="Filter usage (hours)"
    ),
    "D05408": FieldDefinition(
        name="filter_total_hours", type="integer", description="Filter total hours"
    ),
    "D0520D": FieldDefinition(
        name="pre_filter_usage", type="integer", description="Pre-filter usage (hours)"
    ),
    "D0540E": FieldDefinition(
        name="pre_filter_total", type="integer", description="Pre-filter total hours"
    ),
}

DEVICE_FIELD_KEYS = frozenset(
    [
        "D01S03",
        "D01S04",
        "D01S05",
        "D01S0D",
        "D01S12",
        "DeviceId",
        "ProductId",
        "WifiVersion",
    ]
)
SENSOR_FIELD_KEYS = frozenset(
    ["D03103", "D03105", "D03106", "D03110", "D03125", "D0312C", "D03224", "rssi"]
)
CONTROL_FIELD_KEYS = frozenset(
    [
        "D03102",
        "D0310A",
        "D0310C",
        "D03112",
        "D03115",
        "D0311F",
        "D03120",
        "D03122",
        "D0312A",
        "D0312B",
        "D03180",
        "D03182",
        "D0313B",
        "D03211",
        "D03221",
        "D03240",
    ]
)
FILTER_FIELD_KEYS = frozenset(
    [
        "D03130",
        "D03134",
        "D03135",
        "D03136",
        "D03137",
        "D05102",
        "D05207",
        "D05408",
        "D0520D",
        "D0540E",
    ]
)


def get_field_category(key: str) -> str:
    """Determine the category for a field."""
    if key in DEVICE_FIELD_KEYS:
        return "device"
    if key in SENSOR_FIELD_KEYS:
        return "sensors"
    if key in CONTROL_FIELD_KEYS:
        return "controls"
    if key in FILTER_FIELD_KEYS:
        return "filters"
    return "system"


def analyze_capabilities(status: dict[str, Any]) -> DeviceCapabilities:
    """Analyze device capabilities based on available status fields."""
    filter_types: list[str] = []
    if "D03130" in status:
        filter_types.append("main_filter")
    if "D03134" in status:
        filter_types.append("pre_filter")
    if "D03135" in status:
        filter_types.append("hepa_filter")
    if "D03136" in status:
        filter_types.append("carbon_filter")

    return DeviceCapabilities(
        has_humidifier="D0312A" in status,
        has_purifier="D0312B" in status,
        has_pm25_sensor="D03103" in status or "D03224" in status,
        has_humidity_sensor="D03110" in status,
        has_allergen_sensor="D03105" in status,
        has_gas_sensor="D03106" in status,
        has_display="D03120" in status or "D03122" in status,
        has_timer="D03180" in status,
        has_schedule="D03182" in status,
        has_child_lock="D01213" in status,
        has_sleep_mode="D0311F" in status,
        has_turbo_mode="D03211" in status,
        has_allergen_mode="D03221" in status,
        has_bacteria_virus_mode="D03240" in status,
        filter_types=filter_types,
    )


def generate_ha_config(host: str, status: dict[str, Any]) -> HAConfig:
    """Generate Home Assistant configuration suggestions."""
    model = status.get("D01S05", "Unknown")
    name = status.get("D01S03", "Air Purifier")
    capabilities = analyze_capabilities(status)

    supported_features: list[str] = []
    if capabilities.has_purifier:
        supported_features.extend(["fan_speed", "power"])
    if capabilities.has_humidifier:
        supported_features.append("humidity_target")
    if capabilities.has_display:
        supported_features.append("display_brightness")

    sensors: list[SensorConfig] = []
    if capabilities.has_pm25_sensor:
        sensors.append(
            SensorConfig(name="PM2.5", key="D03224", unit="\u03bcg/m\u00b3", device_class="pm25")
        )
    if capabilities.has_humidity_sensor:
        sensors.append(
            SensorConfig(name="Humidity", key="D03110", unit="%", device_class="humidity")
        )
    for filter_type in capabilities.filter_types:
        if filter_type == "main_filter":
            sensors.append(
                SensorConfig(name="Filter Life", key="D03130", unit="%", device_class="battery")
            )

    return HAConfig(
        host=host,
        name=name,
        model=model,
        unique_id=status.get("DeviceId", f"philips_{host.replace('.', '_')}"),
        device_info=HADeviceInfo(
            identifiers=[status.get("DeviceId", f"philips_{host}")],
            name=name,
            model=model,
            sw_version=status.get("D01S12", "Unknown"),
            hw_version=status.get("WifiVersion", "Unknown"),
        ),
        supported_features=supported_features,
        sensors=sensors,
    )


class DeviceInfoExtractor:
    """Extract comprehensive device information for Home Assistant integration."""

    def __init__(self, host: str, port: int = 5683) -> None:
        self.host = host
        self.port = port

    async def get_device_info(self) -> DeviceReport:
        """Get comprehensive device information."""
        client = await Client.create(host=self.host, port=self.port)

        try:
            status, max_age = await client.get_status()

            report = DeviceReport(
                connection=ConnectionInfo(
                    host=self.host,
                    port=self.port,
                    max_age=max_age,
                ),
                raw_status=status,
                capabilities=analyze_capabilities(status),
                home_assistant=generate_ha_config(self.host, status),
            )

            for key, value in status.items():
                if key in DEVICE_FIELDS:
                    field_def = DEVICE_FIELDS[key]
                    category = get_field_category(key)
                    field_value = FieldValue(
                        value=value,
                        type=field_def.type,
                        description=field_def.description,
                        raw_key=key,
                    )
                    getattr(report, category)[field_def.name] = field_value
                else:
                    field_value = FieldValue(
                        value=value,
                        type=type(value).__name__,
                        description="Unknown field",
                        raw_key=key,
                    )
                    report.system[key] = field_value

            return report

        finally:
            await client.shutdown()

    def export_json(self, device_info: DeviceReport, pretty: bool = True) -> str:
        """Export device info as JSON."""
        if pretty:
            return device_info.model_dump_json(indent=2)
        return device_info.model_dump_json()

    def export_yaml(self, device_info: DeviceReport) -> str:
        """Export device info as YAML."""
        return yaml.dump(
            device_info.model_dump(mode="json"), default_flow_style=False, sort_keys=False
        )
