# Capability: USB

**Status:** Implemented (Phase 2 — Capability 1)
**Owner:** Hardware Platform
**Languages:** C++ (`cpp/hal/`), Python (Hardware API, SDK, CLI, Assistant, Automation)

USB is the foundation capability. Every other hardware capability (Serial,
ADB, Fastboot, …) builds on the same enumeration, hot-plug, permission, and
event primitives introduced here.

## What it does today

- **USB enumeration** — list every attached device with vendor/product id,
  manufacturer, product, serial, bus/port, USB spec, device class.
- **Device information** — stable `device_id`, `vid:pid`, and rich metadata
  exposed through a single `UsbDevice` model.
- **Hot-plug detection** — a `USBManager` monitor (and a single-shot
  `poll_once`) detects connect/disconnect and emits `DeviceConnectedEvent` /
  `DeviceDisconnectedEvent`.
- **Permission system** — `UsbPermissionPolicy` gates access by
  vendor/product id, serial, and capability; defaults to **deny-unknown**.
- **Driver abstraction** — the Hardware API hides the backend; real
  enumeration runs through the `hal-core` C++ transport (`rusb`), with a
  deterministic simulated backend for CI/hosts without libusb.
- **Stable Hardware API** — `hardware.usb.USBManager` is the single entry
  point for the rest of the platform.
- **SDK API** — `sdk.usb.Usb` is the supported client for applications,
  plugins, and automation.
- **Assistant integration** — `assistant.tools.usb` exposes discoverable
  tools (`usb.enumerate`, `usb.info`, `usb.allow`, `usb.deny`).
- **Automation integration** — `automation.actions.usb` registers
  `usb:*` actions for the workflow engine.
- **Terminal / CLI** — `prometheus usb list|info|monitor|allow|deny` and the
  `usb` terminal command.
- **Driver bridge** — `hardware.drivers.usb.USBDriver` is the legacy
  `HardwareDriver` implementation, now bound to a real device via
  `USBManager`. `USBDriver.for_device(device_id)` exposes the same driver
  contract as the other simulated drivers but reads live device metadata and
  enforces the permission policy on `connect()`.

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│  CLI / Terminal         SDK (sdk.usb.Usb)                     │
│  Assistant tools         Automation actions (usb:*)          │
└───────────────┬───────────────────────┬──────────────────────┘
                │                        │
                ▼                        ▼
        USBManager (hardware.usb)   UsbPermissionPolicy
                │  enumerate / poll_once / events
                ▼
        hal-core (C++)  ── UsbTransport ── rusb (libusb)
                │   (fallback: simulated backend)
                ▼
        OS USB stack
```

### C++ (`cpp/hal/`)

- `transports::usb::UsbDeviceInfo` — cross-language device model.
- `transports::usb::UsbTransport::enumerate()` — real enumeration via
  `rusb` when built with `--features usb-real`, otherwise a deterministic
  simulated list.
- `transports::usb::UsbMonitor` — poll-based hot-plug detector that emits
  `UsbChange::Connected` / `UsbChange::Disconnected` deltas.
- `transports::usb::device_id()` — stable device identity across
  re-enumerations (bus+port path preferred, serial as fallback).

### Python (`hardware/usb`)

- `manager.py` — `USBManager`: enumeration, `poll_once`/`start_monitor`
  hot-plug, permission checks, event publishing.
- `permissions.py` — `UsbPermissionPolicy`, `UsbAllowRule`, `UsbDenyRule`,
  `UsbCapability` (enumerate/read_info/connect/read/write/flash/reboot).

## Permission model

Evaluation order: **explicit deny → explicit allow → default**. With
`default_allow=False` (the safe default) no device may be accessed unless a
matching allow rule exists.

```python
from sdk.usb import Usb
client = Usb()
client.allow(vendor_id=0x18D1, product_id=0x4EE7, capabilities={"read_info", "connect"})
ok, why = client.can_access("read_info", 0x18D1, 0x4EE7)
```

## Usage

### SDK

```python
from sdk.usb import Usb

usb = Usb()
for dev in usb.enumerate():
    print(dev["vid_pid"], dev["manufacturer"], dev["product"])

usb.start_monitor(interval=1.0)
```

### CLI

```bash
prometheus usb list
prometheus usb info simulated-usb-0
prometheus usb monitor 10
prometheus usb allow --vid 0x18d1 --pid 0x4ee7 --capability enumerate
prometheus usb deny  --vid 0x1234
```

### Terminal

```
prometheus> usb list
prometheus> usb info simulated-usb-0
prometheus> usb monitor
```

## Tests

- C++: `ctest / CMake test -p hal-core --lib usb` (default + `--features usb-real`).
- Python: `pytest tests/test_usb_capability.py` — permission policy, Hardware
  API enumeration/hot-plug events, SDK client, automation actions, assistant
  tools.

## Build notes

Real USB requires libusb. Build the C++ transport with:

```bash
cargo build -p hal-core --features usb-real
```

Without the feature (default), the crate uses the simulated backend so the
platform and its tests run anywhere.
