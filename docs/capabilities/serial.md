# Capability: Serial Communication

**Status:** Implemented (Phase 2 — Capability 2)
**Owner:** Hardware Platform
**Languages:** C++ (`cpp/hal/`), Python (Hardware API, SDK, CLI, Assistant, Automation)

Serial is the second foundation capability, built on the same primitives
introduced by USB: enumeration, hot-plug, a permission system, a stable
Hardware API, and the same integration surfaces (SDK / CLI / Assistant /
Automation / driver bridge).

## What it does today

- **Enumeration** — list every serial port: `UART`, `COM`, `ttyUSB`, `ttyACM`,
  with USB VID/PID, manufacturer, product, serial, and supported baud rates.
- **Device information** — stable `port` identity and rich metadata via one
  `SerialPort` model.
- **Hot-plug detection** — `SerialManager.poll_once()` / `start_monitor()`
  detect ports appearing/disappearing and emit `DeviceConnectedEvent` /
  `DeviceDisconnectedEvent`.
- **Read / write** — `read()` / `write()` with automatic logging of traffic.
- **Baud configuration** — `configure()` / `connect(port, baud_rate=...)`.
- **Live console / logging** — every read/write is recorded in `manager.log()`.
- **Permission system** — `SerialPermissionPolicy` gates access by port,
  VID/PID, serial, and capability; defaults to **deny-unknown**.
- **Driver abstraction** — `SerialDriver` bridges to the capability's
  `SerialManager` (real enumeration via `hal-core`/`serialport`, simulated
  fallback), with optional pyserial for live byte I/O.
- **Stable Hardware API** — `hardware.serial.SerialManager`.
- **SDK API** — `sdk.serial.Serial`.
- **Assistant / Automation / CLI / Terminal** integration.

## Architecture

Mirrors the USB capability exactly:

```
CLI / Terminal        SDK (sdk.serial.Serial)
Assistant tools        Automation actions (serial:*)
        │                        │
        ▼                        ▼
SerialManager (hardware.serial)   SerialPermissionPolicy
        │  enumerate / poll_once / read / write / events
        ▼
hal-core (C++)  ── SerialTransport ── serialport (libserialport)
        │   (fallback: simulated backend)
```

### C++ (`cpp/hal/`)

- `transports::serial::SerialPortInfo` — cross-language port model.
- `transports::serial::SerialTransport::enumerate()` — real enumeration via
  `serialport` when built with `--features serial-real`, otherwise a
  deterministic simulated list.
- `transports::serial::SerialMonitor` — poll-based hot-plug detector emitting
  `SerialChange::Connected` / `SerialChange::Disconnected` deltas.

### Python (`hardware/serial`)

- `manager.py` — `SerialManager`, `SerialPort`, `get_serial_manager()`:
  enumeration, `poll_once`/`start_monitor`, permission checks, read/write/log,
  event publishing.
- `permissions.py` — `SerialPermissionPolicy`, `SerialAllowRule`,
  `SerialDenyRule`, `SerialCapability` (enumerate/read_info/connect/read/write/
  configure/log).

## Permission model

Evaluation order: **explicit deny → explicit allow → default**. With
`default_allow=False` (the safe default) no port may be opened unless a
matching allow rule exists.

```python
from sdk.serial import Serial
client = Serial()
client.allow(port="COM3", capabilities={"connect", "read", "write"})
ok, why = client.can_access("connect", "COM3")
```

## Usage

### SDK

```python
from sdk.serial import Serial

ser = Serial()
for p in ser.enumerate():
    print(p["port"], p.get("vid_pid"), p["baud_rates"])

client.allow(port="/dev/ttyUSB0", capabilities={"connect", "write"})
ser.connect("/dev/ttyUSB0", baud_rate=115200)
ser.write("/dev/ttyUSB0", b"AT\r\n")
print(ser.log())
```

### CLI

```bash
prometheus serial list
prometheus serial info /dev/ttyUSB0
prometheus serial connect /dev/ttyUSB0 115200
prometheus serial disconnect /dev/ttyUSB0
prometheus serial monitor 10
prometheus serial allow --port COM3 --capability connect
prometheus serial deny  --port COM3
```

### Terminal

```
prometheus> serial list
prometheus> serial info /dev/ttyUSB0
prometheus> serial connect /dev/ttyUSB0 115200
prometheus> serial monitor
```

## Tests

- C++: `ctest / CMake test -p hal-core --lib serial` (default + `--features serial-real`).
- Python: `pytest tests/test_serial_capability.py tests/test_hardware_drivers.py`.

## Build notes

Real serial requires libserialport. Build the C++ transport with:

```bash
cargo build -p hal-core --features serial-real
```

Without the feature (default), the crate uses the simulated backend so the
platform and its tests run anywhere.
