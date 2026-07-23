# Capability: SWD

**Status:** Implemented (Phase 2 — Capability 14)
**Owner:** Hardware Platform
**Languages:** C++ (`cpp/hal/`), Python integration pending

SWD (Serial Wire Debug) is ARM's low-pin-count debug interface, used to
program, debug, and trace Cortex-M and Cortex-R targets. The platform supports
device enumeration, hot-plug detection, and authenticated access probes.

## What it does today

- **Device enumeration** — list reachable SWD targets with target ID, DP
  IDCODE, decoded ARM core (e.g. `Cortex-M33`), debug port version, and serial.
- **Hot-plug detection** — `SwdMonitor` polls for target connect/disconnect and
  emits `SwdChange::Connected` / `SwdChange::Disconnected` deltas.
- **Target probing** — `probe("swd:<target>")` returns connection state and APB
  access latency.
- **Real OpenOCD backend** — when built with `--features swd-real`, shells out
  to OpenOCD's CMSIS-DAP interface; parses `target` / `IDCODE` / `Cortex-*`
  output into `SwdDeviceInfo`.
- **Simulated fallback** — without `swd-real`, a deterministic two-target
  simulated set (Cortex-M33 + Cortex-M0+) is returned so tests/CI stay
  portable.
- **Driver bridge** — `hardware.drivers.bus.SWDDriver` is the legacy
  `HardwareDriver` implementation bound to an SWD target.

## Architecture

```
CLI / Terminal / SDK / Assistant / Automation
         │
         ▼
    SWDDriver (hardware.drivers.bus)
         │  probe / connect / read / write / halt / resume
         ▼
hal-core (C++)  ── SwdTransport / SwdMonitor ── OpenOCD / pyOCD
         │   (fallback: simulated backend)
         ▼
    CMSIS-DAP / JTAG-SWD probe
```

### C++ (`cpp/hal/`)

- `transports::swd::SwdDeviceInfo` — cross-language device model with target
  ID, IDCODE, core, DP version, and serial.
- `transports::swd::SwdTransport::enumerate()` — real enumeration via OpenOCD
  when built with `--features swd-real`; otherwise a deterministic simulated
  list.
- `transports::swd::SwdMonitor` — poll-based hot-plug detector emitting
  `SwdChange::Connected` / `SwdChange::Disconnected`.
- `transports::swd::SwdTransport::probe(target)` — validates `swd:` / `swd-*`
  target strings.

## Usage examples

### C++

```cpp
let transport = SwdTransport;
for dev in SwdTransport::enumerate() {
    println!("{} {:?} id=0x{:08X}", dev.target_id, dev.core, dev.idcode.unwrap());
}

let mut monitor = SwdMonitor::new();
monitor.prime();
for change in monitor.poll() {
    println!("SWD change: {:?}", change);
}
```

## Tests

- C++: `ctest / CMake test -p hal-core --lib swd` (default + `--features swd-real`).

## Build notes

Real SWD requires OpenOCD with a CMSIS-DAP interface.
Build the C++ transport with:

```bash
cargo build -p hal-core --features swd-real
```

Without the feature (default), the crate uses the simulated backend so the
platform and its tests run anywhere.
