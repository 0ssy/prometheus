# Capability: Network

**Status:** Implemented (Phase 2 — Capability 9)
**Owner:** Hardware Platform
**Languages:** C++ (`cpp/hal/`), Python integration pending

Network provides transport-layer reachability for TCP, UDP, and HTTP targets.
It is the foundation for over-the-air (OTA) updates, remote log collection, and
cloud-connected device management.

## What it does today

- **Transport-layer probing** — `probe("tcp:<host>:<port>")`,
  `probe("udp:<host>:<port>")`, and `probe("http://<host>")` validate network
  targets and return transport identity.
- **Protocol variant support** — native support for `tcp:`, `udp:`, and `http:`
  target prefixes.
- **Simulated fallback** — without a real backend, the transport accepts all
  three network target prefixes so dependent code can be tested in CI.
- **Driver bridge** — `hardware.drivers.network.NetworkDriver` is the legacy
  `HardwareDriver` implementation for network-attached devices.

## Architecture

```
CLI / Terminal / SDK / Assistant / Automation
         │
         ▼
    NetworkDriver (hardware.drivers.network)
         │  probe / connect / send / receive
         ▼
hal-core (C++)  ── NetworkTransport ── TCP/UDP sockets / reqwest
         │   (fallback: simulated backend — tcp:/udp:/http: targets accepted)
         ▼
    Ethernet / Wi-Fi / cellular interface
```

### C++ (`cpp/hal/`)

- `transports::network::NetworkTransport` — network-target transport.
- `transports::network::NetworkTransport::probe(target)` — accepts `tcp:`,
  `udp:`, and `http:` prefixed target strings; returns `ProbeInfo` with
  transport identity and connected state.

## Usage examples

### C++

```cpp
let transport = NetworkTransport;
transport.probe("tcp:192.168.1.1:23").unwrap();
transport.probe("udp:239.255.255.250:1900").unwrap();
transport.probe("http://example.com").unwrap();
```

## Tests

- C++: `ctest / CMake test -p hal-core --lib network`.

## Build notes

Real network access requires a TCP/UDP/HTTP library. Build the C++ transport with:

```bash
cargo build -p hal-core --features c-hal
```

Without the feature (default), the crate accepts network targets so the platform
and its tests run anywhere.
