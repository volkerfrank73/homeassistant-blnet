"""Fixtures for the BLNET integration tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from pyblnet_async import (
    AnalogValue,
    BLNETData,
    DigitalInput,
    DigitalMode,
    DigitalValue,
    DirectData,
    DirectInput,
    HeatMeter,
    InputKind,
)

from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_SCAN_INTERVAL
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.blnet.const import DOMAIN


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Allow loading custom_components in every test."""


DATA = BLNETData(
    analog={
        1: AnalogValue(1, "TKollektor", 24.8, "°C"),
        3: AnalogValue(3, "Druck", 1.5, "bar"),
    },
    digital_inputs={2: DigitalInput(2, "Digitaleing.2", False)},
    digital={
        1: DigitalValue(1, "Pumpe-Solar", DigitalMode.AUTO, False),
        6: DigitalValue(6, "Pumpe-Hzkr", DigitalMode.HAND, True),
    },
)


DIRECT = DirectData(
    inputs={
        1: DirectInput(1, InputKind.TEMPERATURE, 24.8, "°C", 0x20F8),
        2: DirectInput(2, InputKind.UNUSED, None, None, 0x0001),
        15: DirectInput(15, InputKind.FLOW, 0.0, "l/h", 0x3000),
        16: DirectInput(16, InputKind.FLOW, 112.0, "l/h", 0x301C),
    },
    outputs={n: n in (6, 8) for n in range(1, 17)},
    heat_meters={
        1: HeatMeter(1, True, 0.0, 86750.1),
        2: HeatMeter(2, False, 0.0, 0.0),
    },
)


@pytest.fixture
def direct():
    """Patch BLNETDirectClient everywhere it is used."""
    with (
        patch("custom_components.blnet.BLNETDirectClient", autospec=True) as init_cls,
        patch("custom_components.blnet.config_flow.BLNETDirectClient", init_cls),
    ):
        instance = init_cls.return_value
        instance.async_fetch = AsyncMock(return_value=DIRECT)
        instance.async_test_connection = AsyncMock(return_value="CAN")
        instance.cls = init_cls
        yield instance


@pytest.fixture
def client():
    """Patch BLNETClient everywhere it is used."""
    with (
        patch("custom_components.blnet.BLNETClient", autospec=True) as init_cls,
        patch("custom_components.blnet.config_flow.BLNETClient", init_cls),
    ):
        instance = init_cls.return_value
        instance.async_fetch = AsyncMock(return_value=DATA)
        instance.async_test_connection = AsyncMock()
        instance.async_set_digital = AsyncMock()
        yield instance


@pytest.fixture
def entry():
    return MockConfigEntry(
        domain=DOMAIN,
        unique_id="192.168.0.250:80",
        data={CONF_HOST: "192.168.0.250", CONF_PORT: 80, CONF_PASSWORD: "secret"},
        options={CONF_SCAN_INTERVAL: 60},
    )


def _entry(**options):
    return MockConfigEntry(
        domain=DOMAIN,
        unique_id="192.168.0.250:80",
        data={CONF_HOST: "192.168.0.250", CONF_PORT: 80, CONF_PASSWORD: "secret"},
        options={CONF_SCAN_INTERVAL: 60, **options},
    )


@pytest.fixture
def entry_ta():
    """Web interface and TA port."""
    return _entry(source="web_ta", ta_port=40000, ta_reset=False)


@pytest.fixture
def entry_ta_only():
    """TA port only, with names."""
    return _entry(
        source="ta",
        ta_port=40000,
        ta_reset=True,
        names="S1 = Kollektor\nS2 = Heizp.Freig.\nA6 = Heizkreis Pumpe",
    )
