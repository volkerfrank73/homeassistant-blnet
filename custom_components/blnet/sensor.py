"""Sensor platform for BLNET: analog inputs."""

from __future__ import annotations

from pyblnet_async import AnalogValue

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import BLNETConfigEntry, BLNETDataUpdateCoordinator
from .entity import BLNETEntity, async_add_channels


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BLNETConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up BLNET sensors from a config entry."""
    coordinator = entry.runtime_data
    async_add_channels(
        entry,
        async_add_entities,
        lambda data: data.analog,
        lambda channel: BLNETSensor(coordinator, entry, channel),
    )


class BLNETSensor(BLNETEntity, SensorEntity):
    """An analog input (temperature etc.)."""

    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self, coordinator: BLNETDataUpdateCoordinator, entry: BLNETConfigEntry, channel: int
    ) -> None:
        super().__init__(coordinator, entry, channel)
        # Same unique_id as the legacy YAML integration, so registry settings survive.
        self._attr_unique_id = f"blnet_sensor_blnet analog {channel}"

    def _item(self) -> AnalogValue | None:
        return self.coordinator.data.analog.get(self._channel)

    @property
    def native_value(self) -> float | None:
        item = self._item()
        return item.value if item is not None else None

    @property
    def native_unit_of_measurement(self) -> str | None:
        item = self._item()
        return item.unit if item is not None else None

    @property
    def device_class(self) -> SensorDeviceClass | None:
        item = self._item()
        if item is not None and item.unit == UnitOfTemperature.CELSIUS:
            return SensorDeviceClass.TEMPERATURE
        return None
