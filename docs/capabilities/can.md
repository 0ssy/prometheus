# Capability: CAN

**Status:** Implemented (Phase 2 — Capability 8)
**Owner:** Hardware Platform
**Languages:** Rust (`hal-core`), Python integration pending

CAN (Controller Area Network) provides multi-node, message-based bus access
for automotive, industrial automation, IoT, and embedded systems. The platform
supports both physical CAN and virtual CAN (`vcan`) interfaces.

## What it does today

- **Target probing** — `probe("can:<iface>")` / `probe("vcan:<iface>")` validates
  a CAN or virtual CAN interface and returns transport identity.
- **Real and virtual interfaces** — distinguishes hardware CAN (`can0`, `can1`)
  from virtual CAN (`vcan0`) used for simulation and testing.
- **Simulated fallback** — without a real backend, the transport accepts
  `can:` / `vcan:` prefixed targets so dependent code can be tested in CI.
- **Driver bridge** — `hardware.drivers.bus.CANDriver` is the legacy
  `HardwareDriver` implementation bound to a CAN interface.

## Architecture

```
CLI / Terminal / SDK / Assistant / Automation
         │
         ▼
    CANDriver (hardware.drivers.bus)
         │  probe / connect / send / receive
         ▼
hal-core (Rust)  ── CanTransport ── socketcan / netlink
         │   (fallback: simulated backend — can:/vcan: targets accepted)
         ▼
    Linux SocketCAN / MCU CAN peripheral
```

### Rust (`crates/hal-core`)

- `transports::can::CanTransport` — interface-capable transport for CAN buses.
- `transports::can::CanTransport::probe(target)` — accepts `can:` and `vcan:`
  prefixed target strings; returns `ProbeInfo` with transport identity and
  connected state.

## Usage examples

### Rust

```rust
let transport = CanTransport;
transport.probe("can0").unwrap();
transport.probe("vcan0").unwrap();
```

## Tests

- Rust: `cargo test -p hal-core --lib can`.

## Build notes

Real CAN requires a Linux kernel with SocketCAN support loaded.
Build the Rust crate with:

```bash
cargo build -p hal-core --features c-hal
```

Without the feature (default), the crate accepts `can:` / `vcan:` targets so the
platform and its tests run anywhere.
