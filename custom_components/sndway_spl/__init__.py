"""The SNDWAY SW-525B sound level meter integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import (
    CONF_PID,
    CONF_SCAN_INTERVAL,
    CONF_VID,
    DEFAULT_PID,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_VID,
)
from .coordinator import SndwayCoordinator
from .usb_device import SndwayError, SndwaySoundLevelMeter

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]

type SndwayConfigEntry = ConfigEntry[SndwayCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: SndwayConfigEntry) -> bool:
    """Set up the meter from a config entry."""
    vid = entry.data.get(CONF_VID, DEFAULT_VID)
    pid = entry.data.get(CONF_PID, DEFAULT_PID)
    scan_interval = entry.options.get(
        CONF_SCAN_INTERVAL,
        entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
    )

    device = SndwaySoundLevelMeter(vid, pid)
    try:
        await hass.async_add_executor_job(device.open)
    except SndwayError as err:
        raise ConfigEntryNotReady(str(err)) from err

    coordinator = SndwayCoordinator(hass, entry, device, scan_interval)
    try:
        await coordinator.async_config_entry_first_refresh()
    except ConfigEntryNotReady:
        await hass.async_add_executor_job(device.close)
        raise

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: SndwayConfigEntry) -> bool:
    """Unload a config entry and free the USB device."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        await entry.runtime_data.async_shutdown()
    return unload_ok


async def _async_reload_entry(hass: HomeAssistant, entry: SndwayConfigEntry) -> None:
    """Reload the entry when its options change."""
    await hass.config_entries.async_reload(entry.entry_id)
