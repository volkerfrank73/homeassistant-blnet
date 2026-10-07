"""Coordinator for BLNET data updates."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import BLNetApiClient
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class BLNetDataUpdateCoordinator(DataUpdateCoordinator[dict[str, object]]):
    """Coordinate BLNET data fetching."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: BLNetApiClient,
        scan_interval_seconds: int,
    ) -> None:
        super().__init__(
            hass,
            logger=_LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval_seconds),
        )
        self.api = api

    async def _async_update_data(self) -> dict[str, object]:
        """Fetch data from BLNET and map it to coordinator data."""
        try:
            return await self.api.async_get_status()
        except Exception as err:  # pragma: no cover - safeguard for bootstrap
            raise UpdateFailed(f"Failed to update BLNET data: {err}") from err
