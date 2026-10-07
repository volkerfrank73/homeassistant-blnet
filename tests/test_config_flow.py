import pytest
from pyblnet_async import BLNETAuthError, BLNETConnectionError

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_SCAN_INTERVAL
from homeassistant.data_entry_flow import FlowResultType

from custom_components.blnet.const import DOMAIN

USER_INPUT = {
    CONF_HOST: "192.168.0.250",
    CONF_PASSWORD: "secret",
    CONF_PORT: 80,
    CONF_SCAN_INTERVAL: 60,
}


async def _start(hass, user_input):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    return await hass.config_entries.flow.async_configure(result["flow_id"], user_input)


async def test_user_flow_creates_entry(hass, client):
    result = await _start(hass, USER_INPUT)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {
        CONF_HOST: "192.168.0.250",
        CONF_PASSWORD: "secret",
        CONF_PORT: 80,
    }
    assert result["options"] == {CONF_SCAN_INTERVAL: 60}


@pytest.mark.parametrize(
    ("exc", "error"),
    [
        (BLNETConnectionError("x"), "cannot_connect"),
        (BLNETAuthError("x"), "invalid_auth"),
        (RuntimeError("x"), "unknown"),
    ],
)
async def test_user_flow_errors_and_recovery(hass, client, exc, error):
    client.async_test_connection.side_effect = exc
    result = await _start(hass, USER_INPUT)
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": error}

    client.async_test_connection.side_effect = None
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_duplicate_aborts(hass, client, entry):
    entry.add_to_hass(hass)
    result = await _start(hass, USER_INPUT)
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_import_from_yaml(hass, client):
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_IMPORT},
        data={
            "resource": "http://192.168.0.250",
            "password": "secret",
            "scan_interval": 360,
            "web_port": 80,
            "can_node": 2,
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {
        CONF_HOST: "192.168.0.250",
        CONF_PORT: 80,
        CONF_PASSWORD: "secret",
        "can_node": 2,
    }
    assert result["options"] == {CONF_SCAN_INTERVAL: 360}


async def test_import_unreachable_aborts(hass, client):
    client.async_test_connection.side_effect = BLNETConnectionError("x")
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_IMPORT},
        data={"resource": "http://192.168.0.250"},
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "cannot_connect"


async def test_options_flow(hass, client, entry):
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_SCAN_INTERVAL: 120}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options[CONF_SCAN_INTERVAL] == 120
