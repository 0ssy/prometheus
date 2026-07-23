# Capability: Recovery

**Status:** Implemented (Phase 2 — Capability 15)
**Owner:** Hardware Platform
**Languages:** C++ (`cpp/hal/`), Python (`hardware.recovery`)

Recovery provides cross-platform device recovery mode identification and
planning: Android Recovery, EDL (Qualcomm), Samsung Odin, DFU, BIOS/UEFI, TPM,
Router, IoT, Drone, Vehicle/ECU, EEPROM/NAND/NOR/SPI-Flash, and Embedded Linux
recovery contexts. The capability normalises recovery-mode targets into a stable
enumeration model and emits the metadata the rest of the platform uses to select
the correct flash/interaction toolchain.

## What it does today

- **Mode identification** — `RecoveryMode` enum covers Android Recovery, EDL,
  Odin, DFU, BIOS, UEFI, TPM, Router, IoT, Drone, Vehicle, ECU, EEPROM, NAND,
  NOR, SPI-Flash, and Embedded Linux.
- **Target probing** — `probe("recovery:<mode>:<id>")` validates a recovery-mode
  target string; mode parsing is case-insensitive with aliases
  (`android` → `AndroidRecovery`, `qualcomm` → `Edl`, etc.).
- **Device enumeration** — `RecoveryTransport::enumerate(mode)` returns
  simulated devices for each supported mode with `label`, `status`, and
  transport identity.
- **Python recovery planning** — `HardwareRecovery.assess_risk()` ranks
  diagnostics (battery, storage) as low/medium/high risk;
  `plan_recovery()` returns strategies and approval requirements;
  `recommend()`, `backup()`, `recover()`, and `reset()` provide the recovery
  workflow contract.
- **Driver bridges** — `hardware.drivers.recovery` exposes one legacy driver
  class per recovery mode: `AndroidRecoveryDriver`, `EDLDriver`, `OdinDriver`,
  `DFUDriver`, `BIOSDriver`, `UEFIDriver`, `TPMDriver`, `RouterDriver`,
  `IoTDriver`, `DroneDriver`, `VehicleDriver`, `ECUDriver`, `EEPROMDriver`,
  `NANDDriver`, `NORDriver`, `SPIFlashDriver`, `EmbeddedLinuxDriver`.

## Architecture

```
CLI / Terminal / SDK / Assistant / Automation
         │
         ▼
HardwareRecovery (hardware.recovery)
         │  assess_risk / plan_recovery / recommend / backup / recover / reset
         ▼
RecoveryTransport (hal-core)  ── mode-specific tools
         │   (fallback: simulated backend per mode)
         ▼
RecoveryDriver subclasses (hardware.drivers.recovery)
         │  AndroidRecoveryDriver / EDLDriver / OdinDriver / DFUDriver / ...
         ▼
    Device in recovery mode
```

### C++ (`cpp/hal/`)

- `transports::recovery::RecoveryMode` — enum with `as_str()`, `parse()`, and
  case-insensitive aliases for every supported recovery mode.
- `transports::recovery::RecoveryDeviceInfo` — cross-language device model with
  `mode`, `device_id`, `product`, `status`, and `transport`.
- `transports::recovery::RecoveryTransport::enumerate(mode)` — returns simulated
  device per mode.
- `transports::recovery::RecoveryTransport::probe(target)` — validates
  `recovery:` targets and extracts mode.

### Python

- `hardware/recovery.py` — `HardwareRecovery`: risk assessment, recovery
  planning, recommendation, backup, recover, reset.
- `hardware/drivers/recovery.py` — mode-specific `HardwareDriver` subclasses
  for the recovery bridge.

## Python entry points

- `hardware.recovery.HardwareRecovery` — risk assessment and recovery planning.

## C++ transport

`crates/hal-core/src/transports/recovery.rs`

## Usage examples

### C++

```cpp
let transport = RecoveryTransport;
let r = transport.probe("recovery:edl:0000").unwrap();
assert_eq!(r.mode, Some(RecoveryMode::Edl));
```

### Python

```python
from hardware.recovery import HardwareRecovery
from hardware.session import DeviceSession

recovery = HardwareRecovery()
plan = recovery.plan_recovery(session, diagnostics={"overall_status": "degraded"})
print(plan["risk"], plan["strategies"])
```

## Tests

- C++: `ctest / CMake test -p hal-core --lib recovery`.
- Python: `pytest tests/test_recovery.py tests/test_hardware_drivers.py`.

## Build notes

Recovery tooling is provided by vendor-specific CLIs (adb, fastboot, dfu-util,
UEFI tools, etc.). The C++ transport uses a simulated backend by default; enable
`c-hal` for vendor bridge integration:

```bash
cargo build -p hal-core --features c-hal
```
