# Capability: SPI

**Status:** Implemented (Phase 2 — Capability 6)
**Owner:** Hardware Platform
**Languages:** C++ (`cpp/hal/`), Python integration pending

SPI (Serial Peripheral Interface) provides high-speed, full-duplex bus access
for sensors, displays, flash memory, and other peripherals attached to embedded
hosts.

## What it does today

- **Target probing** — `probe("spi:<target>")` validates an SPI bus target and
  returns transport identity.
- **Bus controller identification** — supports host-side SPI bus numbers and
  chip-select targets.
- **Simulated fallback** — without a real backend, the transport accepts
  `spi:` prefixed targets so dependent code can be tested in CI.
- **Driver bridge** — `hardware.drivers.bus.SPIDriver` is the legacy
  `HardwareDriver` implementation bound to an SPI target.

## Architecture

```
CLI / Terminal / SDK / Assistant / Automation
         │
         ▼
    SPIDriver (hardware.drivers.bus)
         │  probe / connect / transfer
         ▼
hal-core (C++)  ── SpiTransport ── spidev / sysfs
         │   (fallback: simulated backend — any spi: target accepted)
         ▼
    Linux SPI controller / MCU SPI peripheral
```

### C++ (`cpp/hal/`)

- `transports::spi::SpiTransport` — bus-capable transport for SPI targets.
- `transports::spi::SpiTransport::probe(target)` — accepts `spi:` prefixed
  target strings; returns `ProbeInfo` with transport identity and connected
  state.

## Usage examples

### C++

```cpp
let transport = SpiTransport;
transport.probe("spi:0.0").unwrap();  // bus 0, CS 0
```

## Tests

- C++: `ctest / CMake test -p hal-core --lib spi`.

## Build notes

Real SPI requires a Linux kernel with `spidev` exposed (or a `c-hal` backend).
Build the C++ transport with:

```bash
cargo build -p hal-core --features c-hal
```

Without the feature (default), the crate accepts `spi:` targets so the platform
and its tests run anywhere.
