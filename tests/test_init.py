from dataclasses import replace
from datetime import timedelta

import pytest
from pyblnet_async import BLNETConnectionError, DigitalCommand

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import STATE_OFF, STATE_ON, STATE_UNAVAILABLE
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

from pytest_homeassistant_custom_component.common import async_fire_time_changed

from .conftest import DATA


async def _setup(hass, entry):
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


def _eid(hass, domain, unique_id):
    return er.async_get(hass).async_get_entity_id(domain, "blnet", unique_id)


async def test_entities_keep_legacy_unique_ids(hass, client, entry):
    await _setup(hass, entry)
    assert entry.state is ConfigEntryState.LOADED

    sensor = _eid(hass, "sensor", "blnet_sensor_blnet analog 1")
    assert hass.states.get(sensor).state == "24.8"
    assert hass.states.get(sensor).attributes["device_class"] == "temperature"
    assert hass.states.get(sensor).attributes["unit_of_measurement"] == "°C"

    pressure = _eid(hass, "sensor", "blnet_sensor_blnet analog 3")
    assert "device_class" not in hass.states.get(pressure).attributes
    assert hass.states.get(pressure).attributes["unit_of_measurement"] == "bar"

    assert hass.states.get(_eid(hass, "switch", "blnet_switch_1")).state == STATE_OFF
    assert hass.states.get(_eid(hass, "switch", "blnet_switch_6")).state == STATE_ON
    assert hass.states.get(_eid(hass, "switch", "blnet_mode_switch_1")).state == STATE_ON
    assert hass.states.get(_eid(hass, "switch", "blnet_mode_switch_6")).state == STATE_OFF
    assert (
        hass.states.get(_eid(hass, "binary_sensor", "blnet_digital_input_2")).state
        == STATE_OFF
    )


async def test_setup_retries_when_unreachable(hass, client, entry):
    client.async_fetch.side_effect = BLNETConnectionError("down")
    entry.add_to_hass(hass)
    assert not await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_unload(hass, client, entry):
    await _setup(hass, entry)
    assert await hass.config_entries.async_unload(entry.entry_id)
    assert entry.state is ConfigEntryState.NOT_LOADED


async def test_missing_channel_becomes_unavailable_and_new_one_is_added(
    hass, client, entry, freezer
):
    await _setup(hass, entry)
    sensor = _eid(hass, "sensor", "blnet_sensor_blnet analog 1")

    analog = {k: v for k, v in DATA.analog.items() if k != 1}
    analog[9] = replace(DATA.analog[1], id=9, name="Neu")
    client.async_fetch.return_value = replace(DATA, analog=analog)
    freezer.tick(timedelta(seconds=61))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    assert hass.states.get(sensor).state == STATE_UNAVAILABLE
    assert _eid(hass, "sensor", "blnet_sensor_blnet analog 9") is not None


async def test_output_switch_commands(hass, client, entry):
    await _setup(hass, entry)
    switch = _eid(hass, "switch", "blnet_switch_1")
    await hass.services.async_call("switch", "turn_on", {"entity_id": switch}, blocking=True)
    client.async_set_digital.assert_awaited_with(1, DigitalCommand.ON)
    await hass.services.async_call("switch", "turn_off", {"entity_id": switch}, blocking=True)
    client.async_set_digital.assert_awaited_with(1, DigitalCommand.OFF)


async def test_auto_switch_commands(hass, client, entry):
    await _setup(hass, entry)
    # output 6 is in HAND mode and currently on
    auto6 = _eid(hass, "switch", "blnet_mode_switch_6")
    await hass.services.async_call("switch", "turn_on", {"entity_id": auto6}, blocking=True)
    client.async_set_digital.assert_awaited_with(6, DigitalCommand.AUTO)
    # output 1 is AUTO and off: leaving AUTO keeps it off
    auto1 = _eid(hass, "switch", "blnet_mode_switch_1")
    await hass.services.async_call("switch", "turn_off", {"entity_id": auto1}, blocking=True)
    client.async_set_digital.assert_awaited_with(1, DigitalCommand.OFF)


async def test_command_error_is_reported(hass, client, entry):
    await _setup(hass, entry)
    client.async_set_digital.side_effect = BLNETConnectionError("down")
    switch = _eid(hass, "switch", "blnet_switch_1")
    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            "switch", "turn_on", {"entity_id": switch}, blocking=True
        )
