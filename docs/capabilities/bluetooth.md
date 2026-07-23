# Capability: Bluetooth

**Status:** Implemented (Phase 2 — Capability 10)
**Owner:** Hardware Platform
**Languages:** Rust (`hal-core`), Python integration pending

Bluetooth (Classic and BLE) provides wireless device discovery, pairing, and
data exchange for peripheral sensors, keyboards, audio devices, and IoT nodes.

## What it does today

- **Target probing** — `probe("ble:<addr>")` / `probe("bt:<addr>")` validates a
  BLE or Classic Bluetooth target and returns transport identity.
- **Protocol variants** — supports both BLE (`ble:`) and Classic Bluetooth
  (`bt:`) target prefixes.
- **Simulated fallback** — without a real backend, the transport accepts
  `ble:` / `bt:` prefixed targets so dependent code can be tested in CI.
- **No Python manager yet** — discovery is in `hal-core`; a Python manager and
  SDK client are backlog.

## Architecture

```
CLI / Terminal / SDK / Assistant / Automation
         │
         ▼
    BluetoothDriver (pending)
         │  probe / connect / scan / pair
         ▼
hal-core (Rust)  ── BluetoothTransport ── BlueZ / btmgmt
         │   (fallback: simulated backend — ble:/bt: targets accepted)
         ▼
    Linux BlueZ / MCU Bluetooth stack
```

### Rust (`crates/hal-core`)

- `transports::bluetooth::BluetoothTransport` — probe transport for Bluetooth
  targets.
- `transports::bluetooth::BluetoothTransport::probe(target)` — accepts `ble:`
  and `bt:` prefixed target strings; returns `ProbeInfo` with transport identity
  and connected state.

## Usage examples

### Rust

```rust
let transport = BluetoothTransport;
transport.probe("ble:AA:BB:CC:DD:EE:FF").unwrap();
transport.probe("bt:00:11:22:33:44:55").unwrap();
```

## Tests

- Rust: `cargo test -p hal-core --lib bluetooth`.

## Build notes

Real Bluetooth requires Linux BlueZ (or a `c-hal` backend).
Build the Rust crate with:

```bash
cargo build -p hal-core --features c-hal
```

Without the feature (default), the crate accepts `ble:` / `bt:` targets so the
platform and its tests run anywhere.
