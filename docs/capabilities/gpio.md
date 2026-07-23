# Capability: GPIO

**Status:** Implemented (Phase 2 — Capability 5)
**Owner:** Hardware Platform
**Languages:** Rust (`hal-core`), Python integration pending

GPIO provides foundational pin-level access for embedded and SBC targets. It
covers GPIO chip enumeration and target probing; higher-level pin read/write
operations are exposed through the driver abstraction layer.

## What it does today

- **Chip enumeration** — list GPIO chips with chip ID and label, either from
  the `c-hal` C backend or a single simulated `gpio0`.
- **Target probing** — `probe("gpio:<target>")` validates a GPIO target string
  and returns transport identity plus pin count metadata.
- **Simulated fallback** — without `c-hal`, enumeration returns one chip so the
  platform and tests run anywhere.
- **Driver bridge** — `hardware.drivers.bus.GPIODriver` is the legacy
  `HardwareDriver` implementation bound to a GPIO target via the manager.

## Architecture

```
CLI / Terminal / SDK / Assistant / Automation
         │
         ▼
    GPIODriver (hardware.drivers.bus)
         │  probe / connect / read / write
         ▼
hal-core (Rust)  ── GpioTransport ── c-hal (libgpiod-like C ABI)
         │   (fallback: simulated backend)
         ▼
    Linux GPIO sysfs / character devices
```

### Rust (`crates/hal-core`)

- `transports::gpio::ProbeInfo` — target identity, connected state, pin count.
- `transports::gpio::GpioTransport::enumerate_chips()` — real enumeration via
  `c-prom`/`c-hal` when the `c-hal` feature is enabled; otherwise returns the
  simulated `gpio0`.
- `transports::gpio::GpioTransport::probe(target)` — validates `gpio:` targets.

## Usage examples

### Rust

```rust
let transport = GpioTransport::new();
for (id, label) in transport.enumerate_chips() {
    println!("chip {}: {}", id, label);
}
transport.probe("gpio:0").unwrap();
```

## Tests

- Rust: `cargo test -p hal-core --lib gpio` (default + `--features c-hal`).

## Build notes

Real GPIO requires the `c-hal` feature. Build the Rust crate with:

```bash
cargo build -p hal-core --features c-hal
```

Without the feature (default), the crate uses the simulated backend so the
platform and its tests run anywhere.
