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
