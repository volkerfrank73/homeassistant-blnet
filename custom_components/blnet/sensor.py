"""Sensor platform for BLNET."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import BLNetDataUpdateCoordinator


@dataclass(frozen=True, kw_only=True)
class BLNetSensorEntityDescription(SensorEntityDescription):
    """Describe a BLNET sensor entity."""


SENSOR_TYPES: tuple[BLNetSensorEntityDescription, ...] = (
    BLNetSensorEntityDescription(
        key="available",
        name="BLNET Available",
        icon="mdi:lan-connect",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up BLNET sensors from config entry."""
    coordinator: BLNetDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        BLNetSensor(coordinator=coordinator, entry=entry, description=description)
        for description in SENSOR_TYPES
    )


class BLNetSensor(CoordinatorEntity[BLNetDataUpdateCoordinator], SensorEntity):
    """Represent a BLNET sensor."""

    entity_description: BLNetSensorEntityDescription

    def __init__(
        self,
        coordinator: BLNetDataUpdateCoordinator,
        entry: ConfigEntry,
        description: BLNetSensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"

    @property
    def native_value(self) -> bool | None:
        """Return sensor value from coordinator data."""
        value = self.coordinator.data.get(self.entity_description.key)
        if isinstance(value, bool):
            return value
        return None
