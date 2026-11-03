"""Shared entity code for BLNET."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import BLNETConfigEntry, BLNETDataUpdateCoordinator, BLNETDirectCoordinator


class BLNETEntity(CoordinatorEntity[BLNETDataUpdateCoordinator]):
    """Base class for entities that mirror one channel of the web interface.

    Names come from the name list in the options (key "S<n>" or "A<n>"), otherwise
    straight from the BL-NET (no device name prefix), so entities keep the names and
    entity ids they had with the old YAML integration.
    """

    _attr_has_entity_name = False
    _name_prefix = "S"

    def __init__(
        self, coordinator: BLNETDataUpdateCoordinator, entry: BLNETConfigEntry, channel: int
    ) -> None:
        super().__init__(coordinator)
        self._channel = channel
        self._configured_name = entry.runtime_data.names.get(f"{self._name_prefix}{channel}")
        self._attr_device_info = _device_info(entry)

    def _item(self):
        """Return this channel's current data or None if the device stopped reporting it."""
        raise NotImplementedError

    @property
    def available(self) -> bool:
        return super().available and self._item() is not None

    @property
    def name(self) -> str | None:
        if self._configured_name:
            return self._configured_name
        item = self._item()
        return item.name if item is not None else None


def _device_info(entry: BLNETConfigEntry) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name="BL-NET",
        manufacturer="Technische Alternative",
        model="BL-NET",
    )


class BLNETDirectEntity(CoordinatorEntity[BLNETDirectCoordinator]):
    """Base class for entities read over the TA port.

    The TA port carries no names: the name list in the options wins, otherwise a
    fixed German default name.
    """

    _attr_has_entity_name = False

    def __init__(
        self,
        coordinator: BLNETDirectCoordinator,
        entry: BLNETConfigEntry,
        channel: int,
        unique_id: str,
        default_name: str,
        name_key: str | None = None,
    ) -> None:
        super().__init__(coordinator)
        self._channel = channel
        self._attr_unique_id = unique_id
        names = entry.runtime_data.names
        self._attr_name = (names.get(name_key) if name_key else None) or default_name
        self._attr_device_info = _device_info(entry)

    @property
    def available(self) -> bool:
        return super().available and self.coordinator.data is not None


@callback
def async_add_channels(
    entry: BLNETConfigEntry,
    coordinator: BLNETDataUpdateCoordinator | BLNETDirectCoordinator,
    async_add_entities: AddEntitiesCallback,
    channels: Callable[[Any], Iterable[Any]],
    factory: Callable[[Any], Entity],
) -> None:
    """Add entities for all current channels and for channels that appear later.

    Channels are any hashable keys; nothing is added while the coordinator has no data.
    """
    known: set[Any] = set()

    @callback
    def _add_new() -> None:
        if coordinator.data is None:
            return
        new = [c for c in channels(coordinator.data) if c not in known]
        if new:
            known.update(new)
            async_add_entities(factory(c) for c in new)

    _add_new()
    entry.async_on_unload(coordinator.async_add_listener(_add_new))
