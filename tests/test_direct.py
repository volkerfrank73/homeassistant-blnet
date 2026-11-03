"""TA port (direct port): additional source, TA-only mode, names, memory reset."""

from dataclasses import replace
from datetime import timedelta

import pytest
from pyblnet_async import BLNETConnectionError

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_SCAN_INTERVAL, STATE_OFF, STATE_ON, STATE_UNAVAILABLE
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.blnet.names import format_names, parse_names

from .conftest import DIRECT

WEB_TA = {CONF_SCAN_INTERVAL: 60, "source": "web_ta", "ta_port": 40000, "ta_reset": False}


async def _setup(hass, entry):
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


def _eid(hass, domain, unique_id):
    return er.async_get(hass).async_get_entity_id(domain, "blnet", unique_id)


def _state(hass, domain, unique_id):
    return hass.states.get(_eid(hass, domain, unique_id))


# --- web interface only -------------------------------------------------------


async def test_web_only_has_no_direct_client(hass, client, direct, entry):
    await _setup(hass, entry)
    direct.cls.assert_not_called()
    assert _eid(hass, "sensor", "blnet_sensor_blnet analog 16") is None


# --- web interface and TA port ------------------------------------------------


async def test_web_ta_entities(hass, client, direct, entry_ta):
    await _setup(hass, entry_ta)
    direct.cls.assert_called_once_with("192.168.0.250", port=40000, reset=False)

    # S16 is missing in the web interface: comes from the TA port, legacy unique_id scheme
    flow = _state(hass, "sensor", "blnet_sensor_blnet analog 16")
    assert flow.state == "112.0"
    assert flow.attributes["unit_of_measurement"] == "L/h"
    assert flow.attributes["device_class"] == "volume_flow_rate"
    assert flow.name == "BL-NET Durchfluss S16"
    # S1 still comes from the web interface
    assert _state(hass, "sensor", "blnet_sensor_blnet analog 1").name == "BL-NET TKollektor"

    energy = _state(hass, "sensor", "blnet_direct_heat_meter_1_energy")
    assert energy.state == "86750.1"
    assert energy.attributes["device_class"] == "energy"
    assert energy.attributes["state_class"] == "total_increasing"
    assert energy.attributes["unit_of_measurement"] == "kWh"
    power = _state(hass, "sensor", "blnet_direct_heat_meter_1_power")
    assert power.attributes["unit_of_measurement"] == "kW"
    assert _eid(hass, "sensor", "blnet_direct_heat_meter_2_energy") is None  # inactive

    # outputs 1 and 6 are switches from the web interface, 8 is not listed there
    assert _eid(hass, "binary_sensor", "blnet_direct_output_1") is None
    assert _eid(hass, "binary_sensor", "blnet_direct_output_6") is None
    out8 = _state(hass, "binary_sensor", "blnet_direct_output_8")
    assert out8.state == STATE_ON
    assert out8.name == "BL-NET Ausgang A8"
    assert _state(hass, "binary_sensor", "blnet_direct_output_3").state == STATE_OFF
    assert _eid(hass, "binary_sensor", "blnet_direct_output_14") is None
    assert _state(hass, "switch", "blnet_switch_6").state == STATE_ON


async def test_ta_failure_keeps_web_entities(hass, client, direct, entry_ta):
    direct.async_fetch.side_effect = BLNETConnectionError("down")
    await _setup(hass, entry_ta)
    assert entry_ta.state is ConfigEntryState.LOADED
    assert _state(hass, "sensor", "blnet_sensor_blnet analog 1").state == "24.8"

    direct.async_fetch.side_effect = None
    await entry_ta.runtime_data.direct.async_refresh()
    await hass.async_block_till_done()
    assert _state(hass, "sensor", "blnet_sensor_blnet analog 16").state == "112.0"


async def test_ta_failure_later_makes_only_direct_unavailable(
    hass, client, direct, entry_ta, freezer
):
    await _setup(hass, entry_ta)
    direct.async_fetch.side_effect = BLNETConnectionError("down")
    freezer.tick(timedelta(seconds=61))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert _state(hass, "sensor", "blnet_sensor_blnet analog 16").state == STATE_UNAVAILABLE
    assert _state(hass, "sensor", "blnet_sensor_blnet analog 1").state == "24.8"


async def test_heat_meter_turns_active_later(hass, client, direct, entry_ta, freezer):
    await _setup(hass, entry_ta)
    meters = dict(DIRECT.heat_meters)
    meters[2] = replace(meters[2], active=True, energy=47182.8)
    direct.async_fetch.return_value = replace(DIRECT, heat_meters=meters)
    freezer.tick(timedelta(seconds=61))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert _state(hass, "sensor", "blnet_direct_heat_meter_2_energy").state == "47182.8"


# --- TA port only -------------------------------------------------------------


async def test_ta_only(hass, client, direct, entry_ta_only):
    await _setup(hass, entry_ta_only)
    client.async_fetch.assert_not_called()
    direct.cls.assert_called_once_with("192.168.0.250", port=40000, reset=True)

    # inputs keep the unique_ids of the web entities, names from the option
    s1 = _state(hass, "sensor", "blnet_sensor_blnet analog 1")
    assert s1.state == "24.8"
    assert s1.name == "BL-NET Kollektor"
    assert s1.attributes["device_class"] == "temperature"
    assert _state(hass, "sensor", "blnet_sensor_blnet analog 16").name == "BL-NET Durchfluss S16"

    # S2 (type bits 0, raw 1) is named, so it is a digital input; it is on
    s2 = _state(hass, "binary_sensor", "blnet_digital_input_2")
    assert s2.state == STATE_ON
    assert s2.name == "BL-NET Heizp.Freig."

    # all outputs A1..A13 as read-only binary sensors, no switches
    assert _state(hass, "binary_sensor", "blnet_direct_output_6").name == "BL-NET Heizkreis Pumpe"
    assert _state(hass, "binary_sensor", "blnet_direct_output_6").state == STATE_ON
    assert _state(hass, "binary_sensor", "blnet_direct_output_1").state == STATE_OFF
    assert _eid(hass, "switch", "blnet_switch_6") is None


async def test_ta_only_unnamed_unused_input_is_skipped(hass, client, direct, entry_ta_only):
    entry_ta_only.add_to_hass(hass)
    hass.config_entries.async_update_entry(
        entry_ta_only, options={**entry_ta_only.options, "names": "S1 = Kollektor"}
    )
    assert await hass.config_entries.async_setup(entry_ta_only.entry_id)
    await hass.async_block_till_done()
    assert _eid(hass, "binary_sensor", "blnet_digital_input_2") is None


async def test_ta_only_setup_retries_when_unreachable(hass, client, direct, entry_ta_only):
    direct.async_fetch.side_effect = BLNETConnectionError("down")
    entry_ta_only.add_to_hass(hass)
    assert not await hass.config_entries.async_setup(entry_ta_only.entry_id)
    assert entry_ta_only.state is ConfigEntryState.SETUP_RETRY


# --- names on web entities ----------------------------------------------------


async def test_names_override_web_names(hass, client, direct, entry):
    entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(
        entry, options={**entry.options, "names": "S1 = Kollektor\nA6 = Heizkreis Pumpe"}
    )
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert _state(hass, "sensor", "blnet_sensor_blnet analog 1").name == "BL-NET Kollektor"
    assert _state(hass, "sensor", "blnet_sensor_blnet analog 3").name == "BL-NET Druck"
    assert _state(hass, "switch", "blnet_switch_6").name == "BL-NET Heizkreis Pumpe"


def test_parse_and_format_names():
    names = parse_names("s1 = Kollektor\n\n# Kommentar\nA6: Heizkreis Pumpe\nS10=WW")
    assert names == {"S1": "Kollektor", "A6": "Heizkreis Pumpe", "S10": "WW"}
    assert format_names(names) == "S1 = Kollektor\nS10 = WW\nA6 = Heizkreis Pumpe"
    for bad in ("Kollektor", "S17 = x", "A14 = x", "S1 ="):
        with pytest.raises(ValueError):
            parse_names(bad)


# --- options flow -------------------------------------------------------------


async def _options(hass, entry, user_input):
    result = await hass.config_entries.options.async_init(entry.entry_id)
    return result, await hass.config_entries.options.async_configure(result["flow_id"], user_input)


async def test_options_prefill_names_from_web(hass, client, direct, entry):
    await _setup(hass, entry)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    schema = result["data_schema"].schema
    key = next(k for k in schema if k == "names")
    assert key.description["suggested_value"] == (
        "S1 = TKollektor\nS2 = Digitaleing.2\nS3 = Druck\nA1 = Pumpe-Solar\nA6 = Pumpe-Hzkr"
    )


async def test_options_enable_ta_port(hass, client, direct, entry):
    await _setup(hass, entry)
    _, result = await _options(hass, entry, WEB_TA)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options == WEB_TA
    await hass.async_block_till_done()
    assert _eid(hass, "sensor", "blnet_sensor_blnet analog 16") is not None


async def test_options_ta_port_errors(hass, client, direct, entry):
    await _setup(hass, entry)
    result = await hass.config_entries.options.async_init(entry.entry_id)

    direct.async_test_connection.side_effect = BLNETConnectionError("x")
    result = await hass.config_entries.options.async_configure(result["flow_id"], WEB_TA)
    assert result["errors"] == {"ta_port": "ta_cannot_connect"}

    direct.async_test_connection.side_effect = None
    direct.async_test_connection.return_value = "DL"
    result = await hass.config_entries.options.async_configure(result["flow_id"], WEB_TA)
    assert result["errors"] == {"ta_port": "ta_unsupported"}


async def test_options_invalid_names(hass, client, direct, entry):
    await _setup(hass, entry)
    _, result = await _options(hass, entry, {**WEB_TA, "names": "S1 = ok\nquatsch"})
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"names": "names_invalid"}
    assert result["description_placeholders"]["line"] == "quatsch"


async def test_options_web_only_does_not_test_ta_port(hass, client, direct, entry_ta):
    await _setup(hass, entry_ta)
    direct.async_test_connection.side_effect = BLNETConnectionError("x")
    _, result = await _options(hass, entry_ta, {**WEB_TA, "source": "web"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert entry_ta.runtime_data.direct is None
