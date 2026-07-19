# Capability: ADB (Android Debug Bridge)

**Status:** Implemented (Phase 2 — Capability 3)
**Owner:** Hardware Platform
**Languages:** Rust (`hal-core`), Python (Hardware API, SDK, CLI, Assistant, Automation)

ADB makes Android support real. It reuses the same primitives as USB and
Serial (discovery, hot-plug, permission policy, events, driver bridge) and
adds the Android-specific operations: shell, logcat, push, pull, install,
reboot, recovery, sideload.

## What it does today

- **Device discovery** — `adb devices -l` when the `adb` CLI is present,
  otherwise a deterministic simulated device, so the platform runs anywhere.
- **Device information** — serial, state, model, product, device, Android
  version, SDK, and USB VID/PID via one `AdbDevice` model.
- **Hot-plug detection** — `ADBManager.poll_once()` / `start_monitor()` emit
  `DeviceConnectedEvent` / `DeviceDisconnectedEvent`.
- **shell** — run commands on a device (permission-gated).
- **logcat** — capture device logs.
- **push / pull** — file transfer to/from a device.
- **install apk** — install an application package.
- **reboot** — normal / recovery / bootloader.
- **recovery / sideload** — OTA sideload while in recovery (distinct
  permission from a normal reboot).
- **Permission system** — `AdbPermissionPolicy` gates by serial/VID/PID and
  capability; defaults to **deny-unknown**.
- **Driver abstraction** — `ADBDriver` bridges to the capability's
  `ADBManager`.
- **Stable Hardware API** — `hardware.adb.ADBManager`.
- **SDK / Assistant / Automation / CLI / Terminal** integration.

## Architecture

```
CLI / Terminal        SDK (sdk.adb.ADB)
Assistant tools        Automation actions (adb:*)
        │                        │
        ▼                        ▼
ADBManager (hardware.adb)   AdbPermissionPolicy
        │  enumerate / poll_once / shell / logcat / push / pull / install / reboot / sideload
        ▼
adb CLI (real)  ──  hal-core AdbTransport (simulated fallback)
```

### Rust (`crates/hal-core`)

- `transports::adb::AdbDeviceInfo` — cross-language device model.
- `transports::adb::AdbTransport::enumerate()` — real discovery via the `adb`
  CLI when built with `--features adb-real`, otherwise a simulated device.
- `transports::adb::AdbMonitor` — poll-based hot-plug detector emitting
  `AdbChange::Connected` / `AdbChange::Disconnected`.
- `parse_adb_devices()` — parser for `adb devices -l` output (tested under
  `adb-real`).

### Python (`hardware/adb`)

- `manager.py` — `ADBManager`, `AdbDevice`, `get_adb_manager()`: discovery,
  `poll_once`/`start_monitor`, permission-gated operations, event publishing.
- `permissions.py` — `AdbPermissionPolicy`, `AdbAllowRule`, `AdbDenyRule`,
  `AdbCapability` (discover/read_info/shell/logcat/push/pull/install/reboot/
  recovery/sideload).

## Permission model

Evaluation order: **explicit deny → explicit allow (any matching rule that
grants the capability) → default**. With `default_allow=False` (the safe
default) a device cannot be touched unless a matching allow rule exists. Note
that RECOVERY/sideload are separate capabilities from REBOOT, so a device can
be allowed to reboot but not to enter recovery.

```python
from sdk.adb import ADB
client = ADB()
client.allow(serial="ABCD1234", capabilities={"shell", "logcat", "push", "pull"})
ok, why = client.can_access("shell", "ABCD1234")
```

## Usage

### SDK

```python
from sdk.adb import ADB

adb = ADB()
for d in adb.enumerate():
    print(d["serial"], d["model"], d["state"])

adb.allow(serial="ABCD1234", capabilities={"shell", "logcat"})
print(adb.shell("ABCD1234", "getprop ro.build.version.release"))
print(adb.logcat("ABCD1234", lines=200))
```

### CLI

```bash
prometheus adb list
prometheus adb shell ABCD1234 "getprop"
prometheus adb logcat ABCD1234 200
prometheus adb push ABCD1234 ./app.apk /data/local/tmp/app.apk
prometheus adb pull ABCD1234 /sdcard/log.txt ./log.txt
prometheus adb install ABCD1234 ./app.apk
prometheus adb reboot ABCD1234 recovery
prometheus adb sideload ABCD1234 ./ota.zip
prometheus adb monitor 10
prometheus adb allow --serial ABCD1234 --capability shell
prometheus adb deny  --serial ABCD1234
```

### Terminal

```
prometheus> adb list
prometheus> adb shell ABCD1234 getprop
prometheus> adb reboot ABCD1234 recovery
prometheus> adb monitor
```

## Tests

- Rust: `cargo test -p hal-core --lib adb` (default + `--features adb-real`).
- Python: `pytest tests/test_adb_capability.py tests/test_hardware_drivers.py`.

## Build notes

Real ADB discovery requires the `adb` executable on `PATH`. Build the Rust
crate with:

```bash
cargo build -p hal-core --features adb-real
```

Without the feature (default), the crate uses a simulated device so the
platform and its tests run anywhere.
