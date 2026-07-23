# Capability: DFU

**Status:** Implemented (Phase 2 — Capability 13)
**Owner:** Hardware Platform
**Languages:** Rust (`hal-core`), Python integration pending

DFU (Device Firmware Upgrade) provides device discovery and state monitoring
for devices that expose an official USB DFU runtime or bootloader. The platform
supports detach-capable and non-detachable DFU devices across multiple vendors.

## What it does today

- **Device enumeration** — list DFU-capable devices with platform path, VID/PID,
  DFU state (`appIDLE`, `dfuDNLOAD-IDLE`, etc.), firmware version, and detach
  capability.
- **Hot-plug detection** — `DfuMonitor` polls for device connect/disconnect and
  emits `DfuChange::Connected` / `DfuChange::Disconnected` deltas keyed by
  `path`.
- **Real dfu-util backend** — when built with `--features dfu-real`, shells out
  to `dfu-util -l` and parses `manufacturer=`, `idVendor=`, `idProduct=`,
  `bcdDevice=`, `State=` into `DfuDeviceInfo`.
- **Simulated fallback** — without `dfu-real`, a deterministic pair of DFU
  devices (Apple `05AC:1227` in `appIDLE` + ST `0483:DF11` in `dfuIDLE`) is
  returned so tests/CI stay portable.
- **Label generation** — `DFU (<vid>:<pid>)` fallback for human-readable device
  labels.
- **Driver bridge** — `hardware.drivers.recovery.DFUDriver` is the legacy
  `HardwareDriver` implementation for DFU-mode devices.

## Architecture

```
CLI / Terminal / SDK / Assistant / Automation
         │
         ▼
    DFUDriver (hardware.drivers.recovery)
         │  enumerate / probe / detach / download / upload
         ▼
hal-core (Rust)  ── DfuTransport / DfuMonitor ── dfu-util
         │   (fallback: simulated backend — two deterministic DFU devices)
         ▼
    USB DFU bootloader / runtime
```

### Rust (`crates/hal-core`)

- `transports::dfu::DfuDeviceInfo` — cross-language device model with `path`,
  `vendor_id`, `product_id`, `state`, `firmware_version`, `can_detach`.
- `transports::dfu::DfuTransport::enumerate()` — real enumeration via `dfu-util`
  when built with `--features dfu-real`; otherwise a deterministic simulated
  list.
- `transports::dfu::DfuMonitor` — poll-based hot-plug detector emitting
  `DfuChange::Connected` / `DfuChange::Disconnected`.
- `transports::dfu::DfuTransport::probe(target)` — validates `dfu:` prefixed
  target strings.

## Usage examples

### Rust

```rust
let transport = DfuTransport;
for dev in DfuTransport::enumerate() {
    println!("{} state={}", dev.vid_pid(), dev.state);
}

let mut monitor = DfuMonitor::new();
monitor.prime();
for change in monitor.poll() {
    println!("DFU change: {:?}", change);
}
```

## Tests

- Rust: `cargo test -p hal-core --lib dfu` (default + `--features dfu-real`).

## Build notes

Real DFU requires the `dfu-util` executable on `PATH`.
Build the Rust crate with:

```bash
cargo build -p hal-core --features dfu-real
```

Without the feature (default), the crate uses the simulated backend so the
platform and its tests run anywhere.
