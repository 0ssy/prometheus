# Capability: I2C

**Status:** Implemented (Phase 2 — Capability 7)
**Owner:** Hardware Platform
**Languages:** Rust (`hal-core`), Python integration pending

I2C (Inter-Integrated Circuit) provides multi-device, two-wire bus access for
sensors, EEPROMs, PMICs, and other addressable peripherals on embedded and SBC
targets.

## What it does today

- **Target probing** — `probe("i2c:<bus>:<addr>")` validates an I2C bus/address
  target and returns transport identity.
- **Multi-drop addressing** — supports 7-bit and 10-bit I2C addresses on a
  given bus controller.
- **Simulated fallback** — without a real backend, the transport accepts
  `i2c:` prefixed targets so dependent code can be tested in CI.
- **Driver bridge** — `hardware.drivers.bus.I2CDriver` is the legacy
  `HardwareDriver` implementation bound to an I2C bus/address.

## Architecture

```
CLI / Terminal / SDK / Assistant / Automation
         │
         ▼
    I2CDriver (hardware.drivers.bus)
         │  probe / connect / read / write / scan
         ▼
hal-core (Rust)  ── I2cTransport ── i2c-dev / sysfs
         │   (fallback: simulated backend — any i2c: target accepted)
         ▼
    Linux I2C adapter / MCU I2C peripheral
```

### Rust (`crates/hal-core`)

- `transports::i2c::I2cTransport` — bus-capable transport for I2C targets.
- `transports::i2c::I2cTransport::probe(target)` — accepts `i2c:` prefixed
  target strings; returns `ProbeInfo` with transport identity and connected
  state.

## Usage examples

### Rust

```rust
let transport = I2cTransport;
transport.probe("i2c:1:0x50").unwrap();  // bus 1, addr 0x50
```

## Tests

- Rust: `cargo test -p hal-core --lib i2c`.

## Build notes

Real I2C requires a Linux kernel with `i2c-dev` exposed (or a `c-hal` backend).
Build the Rust crate with:

```bash
cargo build -p hal-core --features c-hal
```

Without the feature (default), the crate accepts `i2c:` targets so the platform
and its tests run anywhere.
