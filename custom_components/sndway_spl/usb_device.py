"""Low-level USB access to the SNDWAY SW-525B sound level meter.

This is a straight port of the reverse-engineered C++ reference in ``main.cpp``:
write a one-byte ``0xB3`` query to the interrupt OUT endpoint, wait briefly, then
read an interrupt IN packet whose first two bytes are a big-endian value in tenths
of a decibel.

Everything in this module is blocking and must be run in an executor thread.
"""

from __future__ import annotations

import errno
import logging
import threading

import usb.core
import usb.util

from .const import (
    CMD_QUERY,
    EP_IN,
    EP_OUT,
    PACKET_SIZE,
    USB_INTERFACE,
)

_LOGGER = logging.getLogger(__name__)

_READ_RETRIES = 3
_WRITE_TIMEOUT_MS = 200
_READ_TIMEOUT_MS = 300


class SndwayError(Exception):
    """Raised when communication with the meter fails."""


class SndwayDeviceNotFound(SndwayError):
    """Raised when no matching USB device is present."""


class _TransferTimeout(SndwayError):
    """Internal: a single interrupt transfer timed out."""


class SndwaySoundLevelMeter:
    """Persistent handle to one SW-525B over USB."""

    def __init__(
        self,
        vid: int,
        pid: int,
        *,
        interface: int = USB_INTERFACE,
        ep_out: int = EP_OUT,
        ep_in: int = EP_IN,
    ) -> None:
        """Store the addressing info; no I/O happens here."""
        self._vid = vid
        self._pid = pid
        self._interface = interface
        self._ep_out = ep_out
        self._ep_in = ep_in
        self._dev: usb.core.Device | None = None
        self._lock = threading.Lock()

    @property
    def address(self) -> str:
        """Human readable ``vvvv:pppp`` USB id."""
        return f"{self._vid:04x}:{self._pid:04x}"

    def open(self) -> None:
        """Find, configure and claim the device."""
        with self._lock:
            self._open_locked()

    def close(self) -> None:
        """Release the interface and drop the handle."""
        with self._lock:
            self._close_locked()

    def read_db(self) -> float:
        """Return the current sound pressure level in dB.

        Opens the device on first use and reopens it after a fatal USB error.
        Transient timeouts are retried a few times before giving up.
        """
        with self._lock:
            if self._dev is None:
                self._open_locked()

            last_error: Exception | None = None
            for attempt in range(_READ_RETRIES):
                try:
                    return self._read_once_locked()
                except _TransferTimeout as err:
                    last_error = err
                    _LOGGER.debug(
                        "Timeout reading from %s (attempt %d/%d)",
                        self.address,
                        attempt + 1,
                        _READ_RETRIES,
                    )
                except SndwayError:
                    self._close_locked()
                    raise

            self._close_locked()
            raise SndwayError(f"No response from {self.address}: {last_error}")

    # -- internals (call with the lock held) --------------------------------

    def _open_locked(self) -> None:
        dev = usb.core.find(idVendor=self._vid, idProduct=self._pid)
        if dev is None:
            raise SndwayDeviceNotFound(
                f"USB device {self.address} not found - is it plugged in?"
            )

        try:
            if dev.is_kernel_driver_active(self._interface):
                dev.detach_kernel_driver(self._interface)
        except NotImplementedError:
            # Backend without kernel-driver support (e.g. Windows/libusbK).
            pass
        except usb.core.USBError as err:
            raise SndwayError(
                f"Could not detach kernel driver from {self.address}: {err}"
            ) from err

        try:
            if dev.get_active_configuration() is None:
                dev.set_configuration()
        except usb.core.USBError:
            try:
                dev.set_configuration()
            except usb.core.USBError as err:
                raise SndwayError(
                    f"Could not configure {self.address}: {err}"
                ) from err

        try:
            usb.util.claim_interface(dev, self._interface)
        except usb.core.USBError as err:
            raise SndwayError(
                f"Could not claim interface {self._interface} on {self.address}: {err}"
            ) from err

        self._dev = dev
        _LOGGER.debug("Opened SNDWAY meter %s", self.address)

    def _close_locked(self) -> None:
        dev, self._dev = self._dev, None
        if dev is None:
            return
        try:
            usb.util.release_interface(dev, self._interface)
        except usb.core.USBError:
            pass
        try:
            dev.attach_kernel_driver(self._interface)
        except (NotImplementedError, usb.core.USBError):
            pass
        usb.util.dispose_resources(dev)
        _LOGGER.debug("Closed SNDWAY meter %s", self.address)

    def _read_once_locked(self) -> float:
        assert self._dev is not None
        payload = bytes([CMD_QUERY]) + bytes(PACKET_SIZE - 1)
        try:
            self._dev.write(self._ep_out, payload, timeout=_WRITE_TIMEOUT_MS)
            data = self._dev.read(self._ep_in, PACKET_SIZE, timeout=_READ_TIMEOUT_MS)
        except usb.core.USBError as err:
            if _is_timeout(err):
                raise _TransferTimeout(str(err)) from err
            raise SndwayError(f"USB transfer to {self.address} failed: {err}") from err

        if len(data) < 2:
            raise _TransferTimeout(f"short packet ({len(data)} bytes)")

        return round((data[0] * 256 + data[1]) * 0.1, 1)


def _is_timeout(err: usb.core.USBError) -> bool:
    """Best-effort detection of a libusb timeout across backends."""
    if err.errno == errno.ETIMEDOUT:
        return True
    text = str(err).lower()
    return "timeout" in text or "timed out" in text
