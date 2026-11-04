"""Sensor platform for Con Edison integration."""
from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, PRIMARY_ACCOUNT, SENSORS
from .coordinator import ConEdisonDataUpdateCoordinator

# Usage sensors whose unit follows the meter (kWh for electric, therms/CCF for gas)
_USAGE_SENSORS = {"last_bill_kwh", "current_cycle_usage", "forecasted_usage"}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Con Edison sensors from a config entry."""
    coordinators: dict[str, ConEdisonDataUpdateCoordinator] = hass.data[DOMAIN][entry.entry_id]
    
    entities = [
        ConEdisonSensor(coordinator, entry, sensor_type)
        for coordinator in coordinators.values()
        for sensor_type in SENSORS
    ]
    
    async_add_entities(entities)


class ConEdisonSensor(CoordinatorEntity[ConEdisonDataUpdateCoordinator], SensorEntity):
    """Representation of a Con Edison sensor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ConEdisonDataUpdateCoordinator,
        entry: ConfigEntry,
        sensor_type: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        
        self._sensor_type = sensor_type
        self._sensor_config = SENSORS[sensor_type]
        
        account_key = coordinator.account_key
        # The primary account keeps the IDs it had before multi-account support
        if account_key == PRIMARY_ACCOUNT:
            self._attr_unique_id = f"{entry.entry_id}_{sensor_type}"
            device_id = entry.entry_id
        else:
            self._attr_unique_id = f"{entry.entry_id}_{account_key}_{sensor_type}"
            device_id = f"{entry.entry_id}_{account_key}"
        self._attr_name = self._sensor_config["name"]
        self._attr_native_unit_of_measurement = self._sensor_config.get("unit")
        self._attr_icon = self._sensor_config.get("icon")
        
        device_class = self._sensor_config.get("device_class")
        if device_class == "monetary":
            self._attr_device_class = SensorDeviceClass.MONETARY
        elif device_class == "energy":
            self._attr_device_class = SensorDeviceClass.ENERGY
        else:
            self._attr_device_class = None
        
        state_class = self._sensor_config.get("state_class")
        if state_class == "total_increasing":
            self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        elif state_class == "total":
            self._attr_state_class = SensorStateClass.TOTAL
        elif state_class == "measurement":
            self._attr_state_class = SensorStateClass.MEASUREMENT
        else:
            self._attr_state_class = None
        
        label = coordinator.account_label
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            name=f"ConEd Connect {label}" if label else "ConEd Connect",
            manufacturer="HA-ConEd",
            model="ConEd Connect Account",
        )

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Usage sensors show the meter's unit; gas accounts report therms or CCF."""
        if self._sensor_type in _USAGE_SENSORS and self.coordinator.data:
            return self.coordinator.data.get("usage_unit") or self._attr_native_unit_of_measurement
        return self._attr_native_unit_of_measurement

    @property
    def device_class(self) -> SensorDeviceClass | None:
        """Energy device class only fits kWh; gas usage has no matching class here."""
        if self._sensor_type in _USAGE_SENSORS and self.native_unit_of_measurement != "kWh":
            return None
        return self._attr_device_class

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        if self.coordinator.data is None:
            return None
        
        value = self.coordinator.data.get(self._sensor_type)
        
        if value is None:
            return None
        
        if isinstance(value, (int, float)):
            if self._sensor_config.get("device_class") == "monetary":
                return round(value, 2)
            elif self._sensor_config.get("device_class") == "energy":
                return round(value, 2)
            elif self._sensor_type == "kwh_cost":
                return round(value, 4)
            return value
        
        return value

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra state attributes."""
        if self.coordinator.data is None:
            return None
        
        data_key = f"{self._sensor_type}_data"
        extra_data = self.coordinator.data.get(data_key)
        
        if extra_data and isinstance(extra_data, dict):
            return extra_data
        
        return None
