"""Sound pressure level sensor for the SNDWAY SW-525B."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import UnitOfSoundPressure
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_info import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import SndwayConfigEntry
from .const import DEFAULT_NAME, DOMAIN, MANUFACTURER, MODEL
from .coordinator import SndwayCoordinator

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SndwayConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor for a config entry."""
    async_add_entities([SndwaySoundPressureSensor(entry.runtime_data, entry)])


class SndwaySoundPressureSensor(CoordinatorEntity[SndwayCoordinator], SensorEntity):
    """Reports the meter's current reading in decibels."""

    _attr_has_entity_name = True
    _attr_translation_key = "sound_pressure_level"
    _attr_device_class = SensorDeviceClass.SOUND_PRESSURE
    _attr_native_unit_of_measurement = UnitOfSoundPressure.DECIBEL
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 1

    def __init__(
        self, coordinator: SndwayCoordinator, entry: SndwayConfigEntry
    ) -> None:
        """Initialise the entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.unique_id}_sound_pressure_level"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=DEFAULT_NAME,
            manufacturer=MANUFACTURER,
            model=MODEL,
        )

    @property
    def native_value(self) -> float | None:
        """Return the latest decibel reading."""
        return self.coordinator.data
