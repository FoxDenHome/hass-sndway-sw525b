"""Polling coordinator for the SNDWAY SW-525B."""

from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN
from .usb_device import SndwayError, SndwaySoundLevelMeter

_LOGGER = logging.getLogger(__name__)


class SndwayCoordinator(DataUpdateCoordinator[float]):
    """Query the meter on a fixed interval and hand out the latest dBA reading."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        device: SndwaySoundLevelMeter,
        scan_interval: int,
    ) -> None:
        """Set up the coordinator for one config entry."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self.config_entry = entry
        self.device = device

    async def _async_update_data(self) -> float:
        try:
            return await self.hass.async_add_executor_job(self.device.read_db)
        except SndwayError as err:
            raise UpdateFailed(str(err)) from err

    async def async_shutdown(self) -> None:
        """Stop polling and release the USB handle."""
        await super().async_shutdown()
        await self.hass.async_add_executor_job(self.device.close)
