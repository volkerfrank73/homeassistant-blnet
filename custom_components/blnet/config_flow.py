"""Config flow for BLNET integration."""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlparse

import voluptuous as vol
from pyblnet_async import (
    BLNETAuthError,
    BLNETClient,
    BLNETConnectionError,
    BLNETDirectClient,
    BLNETError,
)

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_SCAN_INTERVAL
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    BooleanSelector,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
)

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
    MIN_SCAN_INTERVAL,
    SOURCE_WEB,
    SOURCES,
)
from .names import format_names, names_from_web, parse_names

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
    """Handle BLNET options: interval, data source, TA port, names."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options step."""
        errors: dict[str, str] = {}
        placeholders = {"line": ""}
        if user_input is not None:
            try:
                parse_names(user_input.get(CONF_NAMES))
            except ValueError as err:
                errors[CONF_NAMES] = "names_invalid"
                placeholders["line"] = str(err)
            if not errors and user_input[CONF_SOURCE] != SOURCE_WEB:
                if error := await self._async_test_ta_port(user_input[CONF_TA_PORT]):
                    errors[CONF_TA_PORT] = error
            if not errors:
                data = dict(user_input)
                if not (data.get(CONF_NAMES) or "").strip():
                    data.pop(CONF_NAMES, None)
                return self.async_create_entry(data=data)

        values = user_input or self.config_entry.options
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_SCAN_INTERVAL,
                    default=values.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                ): _SCAN_INTERVAL,
                vol.Required(
                    CONF_SOURCE, default=values.get(CONF_SOURCE, SOURCE_WEB)
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=SOURCES,
                        translation_key=CONF_SOURCE,
                        mode=SelectSelectorMode.LIST,
                    )
                ),
                vol.Required(
                    CONF_TA_PORT, default=values.get(CONF_TA_PORT, DEFAULT_TA_PORT)
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=65535)),
                vol.Required(
                    CONF_TA_RESET, default=values.get(CONF_TA_RESET, False)
                ): BooleanSelector(),
                vol.Optional(
                    CONF_NAMES,
                    description={"suggested_value": self._names_text(values)},
                ): TextSelector(TextSelectorConfig(multiline=True)),
            }
        )
        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            errors=errors,
            description_placeholders=placeholders,
        )

    def _names_text(self, values: Any) -> str:
        """Configured names, or the names of the web interface as a starting point."""
        if values.get(CONF_NAMES):
            return values[CONF_NAMES]
        runtime = getattr(self.config_entry, "runtime_data", None)
        web = runtime.web if runtime is not None else None
        if web is not None and web.data is not None:
            return format_names(names_from_web(web.data))
        return ""

    async def _async_test_ta_port(self, port: int) -> str | None:
        """Check the TA port; return an error key or None."""
        client = BLNETDirectClient(self.config_entry.data[CONF_HOST], port=port)
        try:
            mode = await client.async_test_connection()
        except BLNETError as err:
            _LOGGER.debug("BL-NET TA port test failed: %s", err)
            return "ta_cannot_connect"
        except Exception:
            _LOGGER.exception("Unexpected error while testing the BL-NET TA port")
            return "unknown"
        return None if mode == "CAN" else "ta_unsupported"
