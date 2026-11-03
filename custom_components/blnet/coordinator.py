"""Coordinators for BLNET data updates."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import timedelta

from pyblnet_async import BLNETClient, BLNETData, BLNETDirectClient, BLNETError, DirectData

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


@dataclass
class BLNETRuntimeData:
    """Coordinators and channel names of one config entry.

    `web` is None in TA-only mode, `direct` is None in web-only mode.
    `names` maps "S1", "A6", ... to the configured names.
    """

    web: BLNETDataUpdateCoordinator | None
    direct: BLNETDirectCoordinator | None = None
    names: dict[str, str] = field(default_factory=dict)


type BLNETConfigEntry = ConfigEntry[BLNETRuntimeData]


class BLNETDataUpdateCoordinator(DataUpdateCoordinator[BLNETData]):
    """Fetch the web interface data in one go for all entities."""

    config_entry: BLNETConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: BLNETConfigEntry,
        client: BLNETClient,
        scan_interval: int,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self.client = client

    async def _async_update_data(self) -> BLNETData:
        try:
            return await self.client.async_fetch()
        except BLNETError as err:
            # The BL-NET allows one session at a time, so a login failure can be
            # temporary (e.g. someone has the web interface open): do not start reauth.
            raise UpdateFailed(f"Error talking to BL-NET: {err}") from err


class BLNETDirectCoordinator(DataUpdateCoordinator[DirectData]):
    """Fetch the current dataset over the TA port (direct port).

    Separate from the web coordinator, so a failing TA port leaves the web
    entities alone.
    """

    config_entry: BLNETConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: BLNETConfigEntry,
        client: BLNETDirectClient,
        scan_interval: int,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN}_direct",
            update_interval=timedelta(seconds=scan_interval),
        )
        self.client = client

    async def _async_update_data(self) -> DirectData:
        try:
            return await self.client.async_fetch()
        except BLNETError as err:
            raise UpdateFailed(f"Error reading the BL-NET TA port: {err}") from err
