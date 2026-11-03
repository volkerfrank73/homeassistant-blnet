"""Sensor platform for BLNET: analog inputs, plus flows and heat meters from the TA port."""

from __future__ import annotations

from pyblnet_async import AnalogValue, DirectData, DirectInput, HeatMeter, InputKind

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import (
    UnitOfEnergy,
    UnitOfIrradiance,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfVolumeFlowRate,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import BLNETConfigEntry, BLNETDataUpdateCoordinator, BLNETDirectCoordinator
from .entity import BLNETDirectEntity, BLNETEntity, async_add_channels

# Input kind -> (name prefix, device class, HA unit)
_DIRECT_KINDS: dict[InputKind, tuple[str, SensorDeviceClass, str]] = {
    InputKind.FLOW: (
        "Durchfluss", SensorDeviceClass.VOLUME_FLOW_RATE, UnitOfVolumeFlowRate.LITERS_PER_HOUR
    ),
    InputKind.TEMPERATURE: ("Temperatur", SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS),
    InputKind.ROOM_TEMPERATURE: ("Raumtemperatur", SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS),
    InputKind.RADIATION: (
        "Einstrahlung", SensorDeviceClass.IRRADIANCE, UnitOfIrradiance.WATTS_PER_SQUARE_METER
    ),
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BLNETConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up BLNET sensors from a config entry."""
    web = entry.runtime_data.web
    if web is not None:
        async_add_channels(
            entry,
            web,
            async_add_entities,
            lambda data: data.analog,
            lambda channel: BLNETSensor(web, entry, channel),
        )

    if (direct := entry.runtime_data.direct) is None:
        return

    def _direct_inputs(data: DirectData) -> list[int]:
        # With the web interface: only what it does not show already (e.g. flows).
        shown = web.data.analog if web is not None and web.data else {}
        return [
            n
            for n, item in data.inputs.items()
            if item.kind in _DIRECT_KINDS and item.value is not None and n not in shown
        ]

    async_add_channels(
        entry,
        direct,
        async_add_entities,
        _direct_inputs,
        lambda channel: BLNETDirectInputSensor(direct, entry, channel),
    )
    async_add_channels(
        entry,
        direct,
        async_add_entities,
        lambda data: [
            (n, part) for n, m in data.heat_meters.items() if m.active for part in ("power", "energy")
        ],
        lambda key: BLNETHeatMeterSensor(direct, entry, *key),
    )


class BLNETSensor(BLNETEntity, SensorEntity):
    """An analog input (temperature etc.)."""

    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self, coordinator: BLNETDataUpdateCoordinator, entry: BLNETConfigEntry, channel: int
    ) -> None:
        super().__init__(coordinator, entry, channel)
        # Same unique_id as the legacy YAML integration, so registry settings survive.
        self._attr_unique_id = f"blnet_sensor_blnet analog {channel}"

    def _item(self) -> AnalogValue | None:
        return self.coordinator.data.analog.get(self._channel)

    @property
    def native_value(self) -> float | None:
        item = self._item()
        return item.value if item is not None else None

    @property
    def native_unit_of_measurement(self) -> str | None:
        item = self._item()
        return item.unit if item is not None else None

    @property
    def device_class(self) -> SensorDeviceClass | None:
        item = self._item()
        if item is not None and item.unit == UnitOfTemperature.CELSIUS:
            return SensorDeviceClass.TEMPERATURE
        return None


class BLNETDirectInputSensor(BLNETDirectEntity, SensorEntity):
    """A measured input read over the TA port.

    Same unique_id as the web sensor of that input, so an input keeps its entity
    when switching between web and TA port.
    """

    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self, coordinator: BLNETDirectCoordinator, entry: BLNETConfigEntry, channel: int
    ) -> None:
        kind = coordinator.data.inputs[channel].kind
        prefix, device_class, unit = _DIRECT_KINDS[kind]
        super().__init__(
            coordinator,
            entry,
            channel,
            f"blnet_sensor_blnet analog {channel}",
            f"{prefix} S{channel}",
            f"S{channel}",
        )
        self._kind = kind
        self._attr_device_class = device_class
        self._attr_native_unit_of_measurement = unit

    def _item(self) -> DirectInput | None:
        item = self.coordinator.data.inputs.get(self._channel) if self.coordinator.data else None
        return item if item is not None and item.kind is self._kind else None

    @property
    def available(self) -> bool:
        return super().available and self._item() is not None

    @property
    def native_value(self) -> float | None:
        item = self._item()
        return item.value if item is not None else None


class BLNETHeatMeterSensor(BLNETDirectEntity, SensorEntity):
    """Power or energy of a heat meter (Wärmemengenzähler), TA port only."""

    def __init__(
        self, coordinator: BLNETDirectCoordinator, entry: BLNETConfigEntry, meter: int, part: str
    ) -> None:
        label = "Leistung" if part == "power" else "Wärmemenge"
        super().__init__(
            coordinator,
            entry,
            meter,
            f"blnet_direct_heat_meter_{meter}_{part}",
            f"Wärmemengenzähler {meter} {label}",
        )
        self._part = part
        if part == "power":
            self._attr_device_class = SensorDeviceClass.POWER
            self._attr_state_class = SensorStateClass.MEASUREMENT
            self._attr_native_unit_of_measurement = UnitOfPower.KILO_WATT
        else:
            self._attr_device_class = SensorDeviceClass.ENERGY
            self._attr_state_class = SensorStateClass.TOTAL_INCREASING
            self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR

    def _item(self) -> HeatMeter | None:
        meter = self.coordinator.data.heat_meters.get(self._channel) if self.coordinator.data else None
        return meter if meter is not None and meter.active else None

    @property
    def available(self) -> bool:
        return super().available and self._item() is not None

    @property
    def native_value(self) -> float | None:
        meter = self._item()
        if meter is None:
            return None
        return meter.power if self._part == "power" else meter.energy
