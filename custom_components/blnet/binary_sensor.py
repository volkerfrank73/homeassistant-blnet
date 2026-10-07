"""Binary sensor platform for BLNET: digital inputs."""

from __future__ import annotations

from pyblnet_async import DigitalInput

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import BLNETConfigEntry, BLNETDataUpdateCoordinator
from .entity import BLNETEntity, async_add_channels


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BLNETConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up BLNET digital inputs from a config entry."""
    coordinator = entry.runtime_data
    async_add_channels(
        entry,
        async_add_entities,
        lambda data: data.digital_inputs,
        lambda channel: BLNETDigitalInput(coordinator, entry, channel),
    )


class BLNETDigitalInput(BLNETEntity, BinarySensorEntity):
    """A digital input, read only."""

    def __init__(
        self, coordinator: BLNETDataUpdateCoordinator, entry: BLNETConfigEntry, channel: int
    ) -> None:
        super().__init__(coordinator, entry, channel)
        self._attr_unique_id = f"blnet_digital_input_{channel}"

    def _item(self) -> DigitalInput | None:
        return self.coordinator.data.digital_inputs.get(self._channel)

    @property
    def is_on(self) -> bool | None:
        item = self._item()
        return item.is_on if item is not None else None
