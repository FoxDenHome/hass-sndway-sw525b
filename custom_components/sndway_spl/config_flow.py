"""Config flow for the SNDWAY SW-525B integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback

from .const import (
    CONF_PID,
    CONF_SCAN_INTERVAL,
    CONF_VID,
    DEFAULT_NAME,
    DEFAULT_PID,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_VID,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)
from .usb_device import SndwayError, SndwaySoundLevelMeter

_SCAN_INTERVAL_SELECTOR = vol.All(
    vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL)
)


def _parse_hex(value: Any) -> int:
    """Parse a hex string like ``0483`` / ``0x0483`` (or a plain int) into an int."""
    if isinstance(value, int):
        return value
    return int(str(value).strip(), 16)


class SndwayConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the UI setup flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for the USB ids and verify the device can be opened."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                vid = _parse_hex(user_input[CONF_VID])
                pid = _parse_hex(user_input[CONF_PID])
            except ValueError:
                errors["base"] = "invalid_id"
            else:
                await self.async_set_unique_id(f"{vid:04x}:{pid:04x}")
                self._abort_if_unique_id_configured()

                device = SndwaySoundLevelMeter(vid, pid)
                try:
                    await self.hass.async_add_executor_job(device.open)
                except SndwayError:
                    errors["base"] = "cannot_connect"
                except Exception:  # noqa: BLE001 - surface anything else to the user
                    errors["base"] = "unknown"
                else:
                    await self.hass.async_add_executor_job(device.close)
                    return self.async_create_entry(
                        title=DEFAULT_NAME,
                        data={
                            CONF_VID: vid,
                            CONF_PID: pid,
                            CONF_SCAN_INTERVAL: user_input[CONF_SCAN_INTERVAL],
                        },
                    )

        defaults = user_input or {
            CONF_VID: f"{DEFAULT_VID:04x}",
            CONF_PID: f"{DEFAULT_PID:04x}",
            CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
        }
        schema = vol.Schema(
            {
                vol.Required(CONF_VID, default=defaults[CONF_VID]): str,
                vol.Required(CONF_PID, default=defaults[CONF_PID]): str,
                vol.Required(
                    CONF_SCAN_INTERVAL, default=defaults[CONF_SCAN_INTERVAL]
                ): _SCAN_INTERVAL_SELECTOR,
            }
        )
        return self.async_show_form(
            step_id="user", data_schema=schema, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> SndwayOptionsFlow:
        """Return the options flow."""
        return SndwayOptionsFlow()


class SndwayOptionsFlow(OptionsFlow):
    """Let the user tune the polling interval after setup."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        current = self.config_entry.options.get(
            CONF_SCAN_INTERVAL,
            self.config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        )
        schema = vol.Schema(
            {
                vol.Required(CONF_SCAN_INTERVAL, default=current): _SCAN_INTERVAL_SELECTOR,
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
