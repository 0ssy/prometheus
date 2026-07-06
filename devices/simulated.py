"""
Prometheus Simulated Device (RFC 0001)
-----------------------------------------
The whole point of this class, per RFC 0001's build order: agents and
plugins get written and tested against this before any real hardware
exists. It echoes writes back as reads, and supports injecting latency
or failures so you can test how an agent handles a flaky device
*before* a real flaky device teaches you the hard way.
"""

import time
import random
from typing import Any
from .base import Device


class SimulatedDevice(Device):
    def __init__(
        self,
        device_id: str,
        ownership_declared: bool = True,
        latency_seconds: float = 0.0,
        failure_rate: float = 0.0,
    ):
        self.device_id = device_id
        self.transport = "simulated"
        self.ownership_declared = ownership_declared
        self.latency_seconds = latency_seconds
        self.failure_rate = failure_rate

        self._connected = False
        self._last_value: Any = None

    def connect(self) -> None:
        if self.latency_seconds:
            time.sleep(self.latency_seconds)
        self._connected = True

    def disconnect(self) -> None:
        self._connected = False

    def _maybe_fail(self):
        if self.failure_rate and random.random() < self.failure_rate:
            raise ConnectionError(f"Simulated failure on device {self.device_id}")

    def read(self) -> Any:
        if not self._connected:
            raise ConnectionError(f"Device {self.device_id} is not connected")
        self._maybe_fail()
        return self._last_value

    def write(self, payload: Any) -> None:
        if not self._connected:
            raise ConnectionError(f"Device {self.device_id} is not connected")
        self._maybe_fail()
        if self.latency_seconds:
            time.sleep(self.latency_seconds)
        self._last_value = payload  # echo — this is what makes it useful for testing

    def status(self) -> dict:
        return {
            "connected": self._connected,
            "last_value": self._last_value,
        }
