"""Coordinator for BLNET data updates."""

from __future__ import annotations

import logging
from datetime import timedelta

from pyblnet_async import BLNETClient, BLNETData, BLNETError

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

type BLNETConfigEntry = ConfigEntry[BLNETDataUpdateCoordinator]


class BLNETDataUpdateCoordinator(DataUpdateCoordinator[BLNETData]):
    """Fetch BLNET data in one go for all entities."""

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
