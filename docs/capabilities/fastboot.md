# Capability: Fastboot

**Status:** Implemented (Phase 2 — Capability 4)
**Owner:** Hardware Platform
**Languages:** Rust (`hal-core`), Python (Hardware API, SDK, CLI, Assistant, Automation)

Fastboot is the Android bootloader flashing and diagnostic protocol. It reuses
the same discovery, hot-plug, and permission primitives as USB and Serial and
adds the bootloader-specific operations: getvar, unlock, lock, flash, erase,
boot, reboot, oem, and update-super.

## What it does today

- **Device discovery** — `fastboot devices` when the `fastboot` CLI is present;
  otherwise a deterministic simulated device so the platform runs anywhere.
- **Device information** — serial, state, product, model, USB VID/PID, and
  unlock status via one `FastbootDevice` model.
- **Hot-plug detection** — `FastbootManager.poll_once()` / `start_monitor()`
  detect bootloader connect/disconnect and emit `DeviceConnectedEvent` /
  `DeviceDisconnectedEvent`.
- **getvar** — query bootloader variables (permission-gated).
- **unlock / lock** — control bootloader lock state.
- **flash / erase** — write or erase a partition by name.
- **boot / reboot** — boot kernel or reboot to different stages.
- **oem** — vendor-specific OEM commands.
- **update-super** — merge a super image into the current super partition.
- **Permission system** — `FastbootPermissionPolicy` gates by serial/VID/PID
  and capability; defaults to **deny-unknown**.
- **Driver abstraction** — `FastbootDriver` bridges to the capability's
  `FastbootManager`.
- **Stable Hardware API** — `hardware.fastboot.FastbootManager`.
- **SDK API** — `sdk.fastboot.Fastboot`.
- **Assistant / Automation / CLI / Terminal** integration.

## Architecture

```
CLI / Terminal        SDK (sdk.fastboot.Fastboot)
Assistant tools        Automation actions (fastboot:*)
         │                        │
         ▼                        ▼
FastbootManager (hardware.fastboot)   FastbootPermissionPolicy
         │  enumerate / poll_once / getvar / unlock / lock / flash / erase / boot / reboot / oem
         ▼
fastboot CLI (real)  ──  hal-core FastbootTransport (simulated fallback)
```

### Rust (`crates/hal-core`)

- `transports::fastboot::FastbootDeviceInfo` — cross-language device model with
  serial, state, product, model, VID/PID, and unlock status.
- `transports::fastboot::FastbootTransport::enumerate()` — real discovery via
  `fastboot devices` when built with `--features fastboot-real`; otherwise a
  deterministic simulated device.
- `transports::fastboot::FastbootMonitor` — poll-based hot-plug detector
  emitting `FastbootChange::Connected` / `FastbootChange::Disconnected`.
- `parse_fastboot_devices()` — parser for `fastboot devices` output (tested
  under `fastboot-real`).

### Python (`hardware/fastboot`)

- `manager.py` — `FastbootManager`, `FastbootDevice`, `get_fastboot_manager()`:
  discovery, `poll_once`/`start_monitor`, permission-gated operations, event
  publishing.
- `permissions.py` — `FastbootPermissionPolicy`, `FastbootAllowRule`,
  `FastbootDenyRule`, `FastbootCapability` (discover/read_info/flash/erase/
  reboot/unlock/oem/update_super).

## Permission model

Evaluation order: **explicit deny → explicit allow (any matching rule that
grants the capability) → default**. With `default_allow=False` (the safe
default) a bootloader cannot be touched unless a matching allow rule exists.

```python
from sdk.fastboot import Fastboot
client = Fastboot()
client.allow(serial="ABCD1234", capabilities={"getvar", "flash", "reboot"})
ok, why = client.can_access("flash", "ABCD1234")
```

## Usage

### SDK

```python
from sdk.fastboot import Fastboot

fb = Fastboot()
for d in fb.enumerate():
    print(d["serial"], d["model"], d["unlocked"])

fb.allow(serial="fastboot-abcdef123456", capabilities={"flash", "reboot"})
print(fb.getvar("fastboot-abcdef123456", "product"))
fb.flash("fastboot-abcdef123456", "boot", "boot.img")
fb.reboot("fastboot-abcdef123456")
```

### CLI

```bash
prometheus fastboot list
prometheus fastboot info fastboot-abcdef123456
prometheus fastboot getvar fastboot-abcdef123456 product
prometheus fastboot flash   fastboot-abcdef123456 boot boot.img
prometheus fastboot unlock  fastboot-abcdef123456
prometheus fastboot reboot  fastboot-abcdef123456
prometheus fastboot monitor 10
prometheus fastboot allow --serial fastboot-abcdef123456 --capability flash
prometheus fastboot deny  --serial fastboot-abcdef123456
```

### Terminal

```
prometheus> fastboot list
prometheus> fastboot info fastboot-abcdef123456
prometheus> fastboot flash boot boot.img
prometheus> fastboot monitor
```

## Tests

- Rust: `cargo test -p hal-core --lib fastboot` (default + `--features fastboot-real`).
- Python: `pytest tests/test_fastboot_capability.py tests/test_hardware_drivers.py`.

## Build notes

Real Fastboot discovery requires the `fastboot` executable on `PATH`. Build the
Rust crate with:

```bash
cargo build -p hal-core --features fastboot-real
```

Without the feature (default), the crate uses a simulated device so the platform
and its tests run anywhere.
