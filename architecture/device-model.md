# Device Model

## The contract

`devices/base.py`'s `Device` class. Every transport — `SimulatedDevice`,
`SerialDevice`, and `engineering/device_simulator.py`'s
`SimulatedFirmwareDevice` — implements the same shape:

```python
class Device(ABC):
    device_id: str
    transport: str
    ownership_declared: bool = False

    def connect() -> None
    def disconnect() -> None
    def read() -> Any
    def write(payload) -> None
    def status() -> dict

    # Wider contract, added per external review — concrete methods
    # with honest "not supported" defaults, NOT @abstractmethod:
    def identify() -> dict
    def diagnose() -> dict
    def verify() -> dict
    def simulate(scenario=None) -> dict
    def recover() -> dict
```

## Why the wider methods are concrete, not abstract

An external architecture review suggested every device should
implement `identify/diagnose/verify/simulate/recover` directly. That's
the right long-term shape, but making them `@abstractmethod` today
would have broken every existing subclass — none of them implement
real diagnose/verify/recover logic yet, because that logic currently
lives in `engineering/` (Firmware Inspector, Boot Chain Analyzer,
Recovery Planner), operating on file paths and twin data, not on live
`Device` instances.

So the base class provides honest defaults —
`{"supported": False, "detail": "..."}` — rather than either breaking
existing code or pretending capability exists where it doesn't. As
each `engineering/` module gets wired to call directly against a
connected `Device` (rather than a file path handed to it separately),
override the relevant method on that transport. Don't leave the
default in place and let it quietly mean something it doesn't.

## Registry

`devices/registry.py`'s `DeviceRegistry` — in-memory, no persistence
across restarts (RFC 0001, deliberate for v0.1). A live device's
`hardware` field in a Delta twin comes from asking the registry
directly; an offline device's twin falls back to knowledge-graph
history only.

## Real-hardware status

`SerialDevice` (pyserial-backed) exists and its error paths (bad port,
disconnect) are tested. It has never exchanged real bytes with a real
microcontroller — see `docs/CAPABILITY_BACKLOG.md`. Don't treat
"error handling is tested" as equivalent to "works against real
hardware."
