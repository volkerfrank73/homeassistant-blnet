"""Config flow for BLNET integration."""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlparse

import voluptuous as vol
from pyblnet_async import BLNETAuthError, BLNETClient, BLNETConnectionError

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_SCAN_INTERVAL
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_NODE,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MIN_SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

_SCAN_INTERVAL = vol.All(vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL))


class BLNETConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for BLNET."""

    VERSION = 1

    async def _async_test(self, data: dict[str, Any]) -> str | None:
        """Try to connect; return an error key or None."""
        client = BLNETClient(
            data[CONF_HOST],
            async_get_clientsession(self.hass),
            password=data.get(CONF_PASSWORD) or None,
            port=data[CONF_PORT],
            node=data.get(CONF_NODE),
        )
        try:
            await client.async_test_connection()
        except BLNETConnectionError as err:
            _LOGGER.debug("BL-NET connection test failed: %s", err)
            return "cannot_connect"
        except BLNETAuthError as err:
            _LOGGER.debug("BL-NET login failed: %s", err)
            return "invalid_auth"
        except Exception:
            _LOGGER.exception("Unexpected error while testing the BL-NET connection")
            return "unknown"
        return None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            data = {k: v for k, v in user_input.items() if k != CONF_SCAN_INTERVAL}
            data[CONF_HOST] = data[CONF_HOST].strip()
            await self.async_set_unique_id(f"{data[CONF_HOST]}:{data[CONF_PORT]}")
            self._abort_if_unique_id_configured()

            if (error := await self._async_test(data)) is None:
                return self.async_create_entry(
                    title=f"BL-NET ({data[CONF_HOST]})",
                    data=data,
                    options={CONF_SCAN_INTERVAL: user_input[CONF_SCAN_INTERVAL]},
                )
            errors["base"] = error

        defaults = user_input or {}
        schema = vol.Schema(
            {
                vol.Required(CONF_HOST, default=defaults.get(CONF_HOST, vol.UNDEFINED)): str,
                vol.Optional(CONF_PASSWORD, default=defaults.get(CONF_PASSWORD, vol.UNDEFINED)): str,
                vol.Required(CONF_PORT, default=defaults.get(CONF_PORT, DEFAULT_PORT)): int,
                vol.Optional(CONF_NODE, default=defaults.get(CONF_NODE, vol.UNDEFINED)): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=62)
                ),
                vol.Required(
                    CONF_SCAN_INTERVAL,
                    default=defaults.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                ): _SCAN_INTERVAL,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_import(self, import_data: dict[str, Any]) -> ConfigFlowResult:
        """Import the legacy YAML configuration (`blnet:`)."""
        host = urlparse(import_data["resource"]).hostname or import_data["resource"]
        data: dict[str, Any] = {
            CONF_HOST: host,
            CONF_PORT: import_data.get("web_port", DEFAULT_PORT),
        }
        if import_data.get(CONF_PASSWORD):
            data[CONF_PASSWORD] = import_data[CONF_PASSWORD]
        if import_data.get("can_node") is not None:
            data[CONF_NODE] = import_data["can_node"]

        await self.async_set_unique_id(f"{host}:{data[CONF_PORT]}")
        self._abort_if_unique_id_configured()

        if (error := await self._async_test(data)) is not None:
            _LOGGER.warning(
                "Import of the YAML configuration for %s failed (%s). "
                "Add the integration in the UI instead",
                host,
                error,
            )
            return self.async_abort(reason=error)

        scan_interval = max(
            import_data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL), MIN_SCAN_INTERVAL
        )
        return self.async_create_entry(
            title=f"BL-NET ({host})",
            data=data,
            options={CONF_SCAN_INTERVAL: scan_interval},
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry) -> BLNETOptionsFlow:
        """Get options flow for this handler."""
        return BLNETOptionsFlow()


class BLNETOptionsFlow(OptionsFlow):
    """Handle BLNET options."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options step."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        current = self.config_entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        schema = vol.Schema({vol.Required(CONF_SCAN_INTERVAL, default=current): _SCAN_INTERVAL})
        return self.async_show_form(step_id="init", data_schema=schema)
