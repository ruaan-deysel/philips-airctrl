"""Pydantic models for Philips air purifier data structures."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class DeviceInfo(BaseModel):
    """Information about a discovered device."""

    ip: str
    port: int = 5683
    model: str | None = None
    name: str | None = None
    device_id: str | None = None
    product_id: str | None = None
    firmware_version: str | None = None
    wifi_version: str | None = None
    serial_number: str | None = None
    status: dict[str, Any] | None = None
    reachable: bool = False


class FieldDefinition(BaseModel):
    """Definition of a device status field."""

    name: str
    type: str
    description: str


class FieldValue(BaseModel):
    """A resolved device field with its value."""

    value: Any
    type: str
    description: str
    raw_key: str


class DeviceCapabilities(BaseModel):
    """Analyzed device capabilities based on available status fields."""

    has_humidifier: bool = False
    has_purifier: bool = False
    has_pm25_sensor: bool = False
    has_humidity_sensor: bool = False
    has_allergen_sensor: bool = False
    has_gas_sensor: bool = False
    has_display: bool = False
    has_timer: bool = False
    has_schedule: bool = False
    has_child_lock: bool = False
    has_sleep_mode: bool = False
    has_turbo_mode: bool = False
    has_allergen_mode: bool = False
    has_bacteria_virus_mode: bool = False
    filter_types: list[str] = Field(default_factory=list)


class SensorConfig(BaseModel):
    """Home Assistant sensor configuration."""

    name: str
    key: str
    unit: str
    device_class: str


class HADeviceInfo(BaseModel):
    """Home Assistant device info block."""

    identifiers: list[str]
    name: str
    manufacturer: str = "Philips"
    model: str
    sw_version: str
    hw_version: str


class HAConfig(BaseModel):
    """Home Assistant configuration suggestion."""

    platform: str = "philips_airpurifier"
    host: str
    name: str
    model: str
    unique_id: str
    device_info: HADeviceInfo
    supported_features: list[str] = Field(default_factory=list)
    sensors: list[SensorConfig] = Field(default_factory=list)
    binary_sensors: list[dict[str, str]] = Field(default_factory=list)
    switches: list[dict[str, str]] = Field(default_factory=list)


class ConnectionInfo(BaseModel):
    """Device connection information."""

    host: str
    port: int
    max_age: int
    protocol: str = "CoAP"
    encryption: str = "AES-CBC"


class DeviceReport(BaseModel):
    """Comprehensive device information report."""

    connection: ConnectionInfo
    device: dict[str, FieldValue] = Field(default_factory=dict)
    sensors: dict[str, FieldValue] = Field(default_factory=dict)
    controls: dict[str, FieldValue] = Field(default_factory=dict)
    filters: dict[str, FieldValue] = Field(default_factory=dict)
    system: dict[str, FieldValue] = Field(default_factory=dict)
    raw_status: dict[str, Any] = Field(default_factory=dict)
    capabilities: DeviceCapabilities = Field(default_factory=DeviceCapabilities)
    home_assistant: HAConfig | None = None
