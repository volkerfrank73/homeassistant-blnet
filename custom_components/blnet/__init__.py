"""The BLNET integration."""

from __future__ import annotations

from pyblnet_async import BLNETClient, BLNETDirectClient

from homeassistant.config_entries import SOURCE_IMPORT
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    Platform,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType

from .const import (
    CONF_NAMES,
    CONF_NODE,
    CONF_SOURCE,
    CONF_TA_PORT,
    CONF_TA_RESET,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TA_PORT,
    DOMAIN,
    SOURCE_TA,
    SOURCE_WEB,
)
from .coordinator import (
    BLNETConfigEntry,
    BLNETDataUpdateCoordinator,
    BLNETDirectCoordinator,
    BLNETRuntimeData,
)
from .names import parse_names

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.SENSOR, Platform.SWITCH]

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Import a legacy YAML configuration (`blnet:`) into a config entry."""
    if (conf := config.get(DOMAIN)) is not None:
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN, context={"source": SOURCE_IMPORT}, data=dict(conf)
            )
        )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: BLNETConfigEntry) -> bool:
    """Set up BLNET from a config entry."""
    options = entry.options
    source = options.get(CONF_SOURCE, SOURCE_WEB)
    scan_interval = options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    try:
        names = parse_names(options.get(CONF_NAMES))
    except ValueError:
        names = {}  # validated in the options flow; never block the setup over a name

    web = None
    if source != SOURCE_TA:
        client = BLNETClient(
            entry.data[CONF_HOST],
            async_get_clientsession(hass),
            password=entry.data.get(CONF_PASSWORD) or None,
            port=entry.data.get(CONF_PORT, DEFAULT_PORT),
            node=entry.data.get(CONF_NODE),
        )
        web = BLNETDataUpdateCoordinator(hass, entry, client, scan_interval)
        await web.async_config_entry_first_refresh()

    direct = None
    if source != SOURCE_WEB:
        direct = BLNETDirectCoordinator(
            hass,
            entry,
            BLNETDirectClient(
                entry.data[CONF_HOST],
                port=options.get(CONF_TA_PORT, DEFAULT_TA_PORT),
                reset=options.get(CONF_TA_RESET, False),
            ),
            scan_interval,
        )
        if web is None:
            await direct.async_config_entry_first_refresh()
        else:
            # Additional source: a failure must not block the web entities, so no
            # first_refresh; its entities appear once the TA port answers.
            await direct.async_refresh()

    entry.runtime_data = BLNETRuntimeData(web=web, direct=direct, names=names)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload))
    return True


async def _async_reload(hass: HomeAssistant, entry: BLNETConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: BLNETConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
