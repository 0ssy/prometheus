# Capability: HID

**Status:** Implemented (Phase 2 — Capability 12)
**Owner:** Hardware Platform
**Languages:** C++ (`cpp/hal/`), Python integration pending

HID (Human Interface Device) provides enumeration and hot-plug detection for
keyboards, mice, game controllers, barcode scanners, and other USB-based or
standalone HID peripherals exposed via `hidraw` paths.

## What it does today

- **Device enumeration** — list every attached HID device with platform path,
  VID/PID, manufacturer, product, serial, usage page, usage ID, and interface
  number.
- **Hot-plug detection** — `HidMonitor` polls for device connect/disconnect and
  emits `HidChange::Connected` / `HidChange::Disconnected` deltas keyed by
  `path`.
- **Real hidapi backend** — when built with `--features hid-real`, uses the
  `hidapi` crate to enumerate real devices on Linux/macOS/Windows; otherwise a
  deterministic set of two simulated HID devices (Logitech Unifying Receiver +
  Microdia USB Keyboard) is returned.
- **Simulated fallback** — without `hid-real`, tests and CI run anywhere with
  no hidapi dependency.
- **Label generation** — `manufacturer product` / `product` / `manufacturer` /
  `vid_pid` fallback chain for human-readable device labels.

## Architecture

```
CLI / Terminal / SDK / Assistant / Automation
         │
         ▼
    HIDManager (pending)
         │  enumerate / poll_once / read / write
         ▼
hal-core (C++)  ── HidTransport / HidMonitor ── hidapi (libusb/HIDAPI)
         │   (fallback: simulated backend — two deterministic HID devices)
         ▼
    OS hidraw device nodes (e.g. /dev/hidraw0)
```

### C++ (`cpp/hal/`)

- `transports::hid::HidDeviceInfo` — cross-language device model with `path`,
  `vendor_id`, `product_id`, `manufacturer`, `product`, `serial_number`,
  `usage_page`, `usage_id`, `interface_number`.
- `transports::hid::HidTransport::enumerate()` — real enumeration via `hidapi`
  when built with `--features hid-real`; otherwise a deterministic simulated
  list.
- `transports::hid::HidMonitor` — poll-based hot-plug detector emitting
  `HidChange::Connected` / `HidChange::Disconnected`.
- `transports::hid::HidTransport::probe(target)` — validates `hid:` and
  `/dev/hidraw*` target strings.

## Usage examples

### C++

```cpp
let transport = HidTransport;
for dev in HidTransport::enumerate() {
    println!("{} {} {}", dev.path, dev.vid_pid(), dev.label());
}

let mut monitor = HidMonitor::new();
monitor.prime();
for change in monitor.poll() {
    println!("HID change: {:?}", change);
}
```

## Tests

- C++: `ctest / CMake test -p hal-core --lib hid` (default + `--features hid-real`).

## Build notes

Real HID requires the `hidapi` system library.
Build the C++ transport with:

```bash
cargo build -p hal-core --features hid-real
```

Without the feature (default), the crate uses the simulated backend so the
platform and its tests run anywhere.
