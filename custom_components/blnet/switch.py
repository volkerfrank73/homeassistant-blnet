"""Switch platform for BLNET: digital outputs."""

from __future__ import annotations

from typing import Any

from pyblnet_async import BLNETError, DigitalCommand, DigitalMode, DigitalValue

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import BLNETConfigEntry, BLNETDataUpdateCoordinator
from .entity import BLNETEntity, async_add_channels


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BLNETConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up BLNET switches from a config entry."""
    coordinator = entry.runtime_data
    for switch_class in (BLNETOutputSwitch, BLNETAutoSwitch):
        async_add_channels(
            entry,
            async_add_entities,
            lambda data: data.digital,
            lambda channel, cls=switch_class: cls(coordinator, entry, channel),
        )


class _BLNETOutput(BLNETEntity, SwitchEntity):
    """Common code for the two switches of a digital output."""

    def _item(self) -> DigitalValue | None:
        return self.coordinator.data.digital.get(self._channel)

    async def _async_command(self, command: DigitalCommand) -> None:
        try:
            await self.coordinator.client.async_set_digital(self._channel, command)
        except BLNETError as err:
            raise HomeAssistantError(
                f"Could not set BL-NET output {self._channel} to {command.name}: {err}"
            ) from err
        await self.coordinator.async_request_refresh()


class BLNETOutputSwitch(_BLNETOutput):
    """Switch the output itself on or off (puts it into manual mode)."""

    def __init__(
        self, coordinator: BLNETDataUpdateCoordinator, entry: BLNETConfigEntry, channel: int
    ) -> None:
        super().__init__(coordinator, entry, channel)
        self._attr_unique_id = f"blnet_switch_{channel}"

    @property
    def is_on(self) -> bool | None:
        item = self._item()
        return item.is_on if item is not None else None

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._async_command(DigitalCommand.ON)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._async_command(DigitalCommand.OFF)


class BLNETAutoSwitch(_BLNETOutput):
    """On: the controller decides (AUTO). Off: manual mode, keeping the current state."""

    def __init__(
        self, coordinator: BLNETDataUpdateCoordinator, entry: BLNETConfigEntry, channel: int
    ) -> None:
        super().__init__(coordinator, entry, channel)
        self._attr_unique_id = f"blnet_mode_switch_{channel}"

    @property
    def is_on(self) -> bool | None:
        item = self._item()
        return item.mode is DigitalMode.AUTO if item is not None else None

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._async_command(DigitalCommand.AUTO)

    async def async_turn_off(self, **kwargs: Any) -> None:
        item = self._item()
        await self._async_command(
            DigitalCommand.ON if item is not None and item.is_on else DigitalCommand.OFF
        )
