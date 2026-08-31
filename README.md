# SNDWAY SW-525B — Home Assistant integration

Home Assistant custom integration for the **SNDWAY SW-525B** digital sound level
meter, connected over USB. It exposes a single **Sound pressure level** sensor
(`dB`, `measurement` state class) that you can use in history, statistics,
automations and dashboards.

Repo: <https://github.com/FoxDenHome/hass-sndway-sw525b>

## How it works

The meter enumerates as a USB device `0483:5750`. The integration speaks the same
interrupt protocol as the [reverse-engineered C++ reference by neon-izm / izm][ref]:
write a one-byte `0xB3` query to interrupt OUT endpoint `0x01`, then read an
interrupt IN packet from `0x81` whose first two bytes are a big-endian value in
tenths of a decibel (`value = (buf[0] * 256 + buf[1]) / 10`).

Communication uses [pyusb] (pulled in automatically as a requirement) on top of
`libusb`. It is `local_polling` — no cloud, no network.

[ref]: https://github.com/neon-izm/SNDWAY_SW525B_USB
[pyusb]: https://github.com/pyusb/pyusb

## Installation

### HACS (custom repository)

1. HACS → ⋮ (top right) → **Custom repositories**.
2. Repository: `https://github.com/FoxDenHome/hass-sndway-sw525b`, type: **Integration**. Add.
3. Search for **"SNDWAY SW-525B Sound Level Meter"**, install it, and restart Home Assistant.

### Manual

```sh
cd /config            # your Home Assistant configuration directory
git clone https://github.com/FoxDenHome/hass-sndway-sw525b.git
mkdir -p custom_components
cp -r hass-sndway-sw525b/custom_components/sndway_spl custom_components/
```

Restart Home Assistant afterwards.

## Setup

**Settings → Devices & Services → Add Integration → SNDWAY SW-525B**.

| Field | Default | Notes |
| --- | --- | --- |
| USB vendor ID (hex) | `0483` | Change only if `lsusb` shows something else |
| USB product ID (hex) | `5750` | |
| Update interval (seconds) | `2` | Editable later via the integration's **Configure** button |

The integration verifies it can open the device before creating the entry.

## Host requirements

* The meter must be plugged into the machine running Home Assistant, and `libusb`
  must be available (it already is on Home Assistant OS and the official container
  image).
* **Container / Supervised:** pass the USB device through to the container
  (`--device=/dev/bus/usb`, or a privileged container). Home Assistant OS does this
  automatically.
* **Core in a venv:** the account running Home Assistant needs access to the USB
  node. Add a udev rule at `/etc/udev/rules.d/99-sndway.rules`:

  ```
  SUBSYSTEM=="usb", ATTRS{idVendor}=="0483", ATTRS{idProduct}=="5750", MODE="0660", TAG+="uaccess"
  ```

  then `sudo udevadm control --reload && sudo udevadm trigger` and replug the meter.

While loaded, the integration claims USB interface 0 and detaches the kernel
driver; it re-attaches the driver again when the config entry is unloaded.

## Notes & limitations

* The value is reported as plain `dB`. The SW-525B applies A/C weighting on the
  device and the packet does not indicate which, so no `dBA` distinction is made.
* A single poll timeout is retried a few times before the sensor goes
  `unavailable`; a fatal USB error drops the handle and it is reopened on the next
  poll.
* Only one meter per host is supported (entries are keyed by USB vendor/product ID).

## Credits

USB protocol reverse engineering: [neon-izm/SNDWAY_SW525B_USB](https://github.com/neon-izm/SNDWAY_SW525B_USB)
(MIT, © 2022 izm). Home Assistant integration: © 2026 Doridian. MIT licensed.
