"""Binary sensor platform for BLNET: digital inputs, plus outputs from the TA port."""

from __future__ import annotations

from pyblnet_async import DigitalInput, DirectData, DirectInput, InputKind

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import MAX_OUTPUT
from .coordinator import BLNETConfigEntry, BLNETDataUpdateCoordinator, BLNETDirectCoordinator
from .entity import BLNETDirectEntity, BLNETEntity, async_add_channels


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BLNETConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up BLNET digital inputs and outputs from a config entry."""
    web = entry.runtime_data.web
    if web is not None:
        async_add_channels(
            entry,
            web,
            async_add_entities,
            lambda data: data.digital_inputs,
            lambda channel: BLNETDigitalInput(web, entry, channel),
        )

    if (direct := entry.runtime_data.direct) is None:
        return
    names = entry.runtime_data.names

    if web is None:
        # TA-only: a UVR1611 on CAN reports digital inputs with type bits 0, like
        # unused ones, so only inputs that have a name (S<n>) become entities.
        def _direct_inputs(data: DirectData) -> list[int]:
            return [
                n
                for n, item in data.inputs.items()
                if item.kind is InputKind.DIGITAL
                or (item.kind is InputKind.UNUSED and f"S{n}" in names)
            ]

        async_add_channels(
            entry,
            direct,
            async_add_entities,
            _direct_inputs,
            lambda channel: BLNETDirectDigitalInput(direct, entry, channel),
        )

    def _direct_outputs(data: DirectData) -> list[int]:
        # With the web interface: only outputs it does not list (it shows named ones).
        shown = web.data.digital if web is not None and web.data else {}
        return [n for n in data.outputs if n <= MAX_OUTPUT and n not in shown]

    async_add_channels(
        entry,
        direct,
        async_add_entities,
        _direct_outputs,
        lambda channel: BLNETDirectOutput(direct, entry, channel),
    )


class BLNETDigitalInput(BLNETEntity, BinarySensorEntity):
    """A digital input, read only."""

    def __init__(
        self, coordinator: BLNETDataUpdateCoordinator, entry: BLNETConfigEntry, channel: int
    ) -> None:
        super().__init__(coordinator, entry, channel)
        self._attr_unique_id = f"blnet_digital_input_{channel}"

    def _item(self) -> DigitalInput | None:
        return self.coordinator.data.digital_inputs.get(self._channel)

    @property
    def is_on(self) -> bool | None:
        item = self._item()
        return item.is_on if item is not None else None


class BLNETDirectOutput(BLNETDirectEntity, BinarySensorEntity):
    """Switching state of an output, read over the TA port (read only)."""

    def __init__(
        self, coordinator: BLNETDirectCoordinator, entry: BLNETConfigEntry, channel: int
    ) -> None:
        super().__init__(
            coordinator,
            entry,
            channel,
            f"blnet_direct_output_{channel}",
            f"Ausgang A{channel}",
            f"A{channel}",
        )

    @property
    def is_on(self) -> bool | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.outputs.get(self._channel)


class BLNETDirectDigitalInput(BLNETDirectEntity, BinarySensorEntity):
    """A digital input read over the TA port (TA-only mode).

    Same unique_id as the web entity of that input, so it keeps its entity.
    """

    def __init__(
        self, coordinator: BLNETDirectCoordinator, entry: BLNETConfigEntry, channel: int
    ) -> None:
        super().__init__(
            coordinator,
            entry,
            channel,
            f"blnet_digital_input_{channel}",
            f"Digitaleingang S{channel}",
            f"S{channel}",
        )

    def _item(self) -> DirectInput | None:
        item = self.coordinator.data.inputs.get(self._channel) if self.coordinator.data else None
        if item is None or item.kind not in (InputKind.DIGITAL, InputKind.UNUSED):
            return None
        return item

    @property
    def available(self) -> bool:
        return super().available and self._item() is not None

    @property
    def is_on(self) -> bool | None:
        item = self._item()
        return item.is_on if item is not None else None
