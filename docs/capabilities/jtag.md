# Capability: JTAG

**Status:** Implemented (Phase 2 — Capability 11)
**Owner:** Hardware Platform
**Languages:** C++ (`cpp/hal/`), Python integration pending

JTAG (IEEE 1149.1) provides boundary-scan and debug access for board-level
testing, silicon validation, and firmware debugging across ARM, RISC-V, and
other SoC families.

## What it does today

- **Target probing** — `probe("jtag:<target>")` validates a JTAG target string
  and returns transport identity; `swd:` targets are also accepted for
  backward compatibility.
- **Backward compatibility with SWD** — the same probe recognises `swd:` prefix
  strings, aliasing them to JTAG until SWD gets its own manager layer.
- **Simulated fallback** — without a real probe backend, the transport accepts
  `jtag:` / `swd:` prefixed targets so dependent code can be tested in CI.
- **Driver bridge** — `hardware.drivers.bus.JTAGDriver` is the legacy
  `HardwareDriver` implementation bound to a JTAG target.

## Architecture

```
CLI / Terminal / SDK / Assistant / Automation
         │
         ▼
    JTAGDriver (hardware.drivers.bus)
         │  probe / connect / scan / halt / resume / read / write
         ▼
hal-core (C++)  ── JtagTransport ── OpenOCD / J-Link / CMSIS-DAP
         │   (fallback: simulated backend — jtag:/swd: targets accepted)
         ▼
    Physical JTAG probe / embedded debugger
```

### C++ (`cpp/hal/`)

- `transports::jtag::JtagTransport` — probe transport for JTAG targets.
- `transports::jtag::JtagTransport::probe(target)` — accepts `jtag:` and `swd:`
  prefixed target strings; returns `ProbeInfo` with transport identity and
  connected state.

## Usage examples

### C++

```cpp
let transport = JtagTransport;
transport.probe("jtag:cortex-m33").unwrap();
transport.probe("swd:0").unwrap();
```

## Tests

- C++: `ctest / CMake test -p hal-core --lib jtag`.

## Build notes

Real JTAG requires OpenOCD, J-Link, or a CMSIS-DAP probe.
Build the C++ transport with:

```bash
cargo build -p hal-core --features c-hal
```

Without the feature (default), the crate accepts `jtag:` / `swd:` targets so the
platform and its tests run anywhere.
