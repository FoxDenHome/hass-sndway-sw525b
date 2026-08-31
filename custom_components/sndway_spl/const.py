"""Constants for the SNDWAY SW-525B sound level meter integration."""

from __future__ import annotations

DOMAIN = "sndway_spl"

DEFAULT_NAME = "SNDWAY SW-525B"
MANUFACTURER = "SNDWAY"
MODEL = "SW-525B"

# USB identifiers of the SW-525B (STMicroelectronics VID, custom PID).
DEFAULT_VID = 0x0483
DEFAULT_PID = 0x5750

# USB endpoints / protocol, taken from the reverse-engineered C++ reference.
USB_INTERFACE = 0
EP_OUT = 0x01
EP_IN = 0x81
PACKET_SIZE = 64
CMD_QUERY = 0xB3

CONF_VID = "vid"
CONF_PID = "pid"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_SCAN_INTERVAL = 2
MIN_SCAN_INTERVAL = 1
MAX_SCAN_INTERVAL = 3600
