"""Shared entity code for BLNET."""

from __future__ import annotations

from collections.abc import Callable, Iterable

from pyblnet_async import BLNETData

from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import BLNETConfigEntry, BLNETDataUpdateCoordinator


class BLNETEntity(CoordinatorEntity[BLNETDataUpdateCoordinator]):
    """Base class for entities that mirror one BL-NET channel.

    Names come straight from the BL-NET (no device name prefix), so entities
    keep the names and entity ids they had with the old YAML integration.
    """

    _attr_has_entity_name = False

    def __init__(
        self, coordinator: BLNETDataUpdateCoordinator, entry: BLNETConfigEntry, channel: int
    ) -> None:
        super().__init__(coordinator)
        self._channel = channel
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="BL-NET",
            manufacturer="Technische Alternative",
            model="BL-NET",
        )

    def _item(self):
        """Return this channel's current data or None if the device stopped reporting it."""
        raise NotImplementedError

    @property
    def available(self) -> bool:
        return super().available and self._item() is not None

    @property
    def name(self) -> str | None:
        item = self._item()
        return item.name if item is not None else None


@callback
def async_add_channels(
    entry: BLNETConfigEntry,
    async_add_entities: AddEntitiesCallback,
    channels: Callable[[BLNETData], Iterable[int]],
    factory: Callable[[int], Entity],
) -> None:
    """Add entities for all current channels and for channels that appear later."""
    coordinator = entry.runtime_data
    known: set[int] = set()

    @callback
    def _add_new() -> None:
        new = [c for c in channels(coordinator.data) if c not in known]
        if new:
            known.update(new)
            async_add_entities(factory(c) for c in new)

    _add_new()
    entry.async_on_unload(coordinator.async_add_listener(_add_new))
