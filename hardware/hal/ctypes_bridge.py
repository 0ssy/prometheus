"""ctypes bridge from Python to the C++ HAL transports.

Replaces ``import hal_core`` for Platform code paths that need real
device enumeration or Ed25519 verification. Each transport DLL is loaded
on demand from the CMake build output directory.
"""

from __future__ import annotations

import ctypes
import os
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]


def _find_hal_dir() -> Path:
    if sys.platform == "win32":
        candidates = [
            REPO_ROOT / "cpp" / "build" / "hal" / "Release",
            REPO_ROOT / "build" / "hal" / "Release",
        ]
    else:
        candidates = [
            REPO_ROOT / "cpp" / "build" / "hal",
            REPO_ROOT / "build" / "hal",
        ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def _load_dll(name: str) -> ctypes.CDLL:
    base = _find_hal_dir()
    if sys.platform == "win32":
        candidates = [base / f"{name}.dll"]
    elif sys.platform == "darwin":
        candidates = [base / f"lib{name}.dylib"]
    else:
        candidates = [base / f"lib{name}.so"]
    for path in candidates:
        if path.exists():
            return ctypes.CDLL(str(path))
    raise OSError(f"HAL transport library not found: {name} (searched {candidates})")


# ---------------------------------------------------------------------------
# USB transport
# ---------------------------------------------------------------------------

class _PromUsbDeviceInfo(ctypes.Structure):
    _fields_ = [
        ("vendor_id", ctypes.c_uint16),
        ("product_id", ctypes.c_uint16),
        ("bus_number", ctypes.c_uint8),
        ("device_address", ctypes.c_uint8),
        ("serial_number", ctypes.c_char * 64),
        ("manufacturer", ctypes.c_char * 64),
        ("product", ctypes.c_char * 64),
        ("class_code", ctypes.c_uint8),
        ("subclass_code", ctypes.c_uint8),
        ("protocol_code", ctypes.c_uint8),
        ("max_packet_size", ctypes.c_uint16),
    ]


class _PromUsbDeviceList(ctypes.Structure):
    _fields_ = [
        ("devices", _PromUsbDeviceInfo * 128),
        ("count", ctypes.c_size_t),
        ("error", ctypes.c_int),
    ]


_lib_usb = _load_dll("prom_hal_usb")
_lib_usb.prom_usb_enumerate.restype = _PromUsbDeviceList
_lib_usb.prom_usb_enumerate.argtypes = []
_lib_usb.prom_usb_strerror.restype = ctypes.c_char_p
_lib_usb.prom_usb_strerror.argtypes = [ctypes.c_int]


class UsbTransport:
    """Drop-in replacement for ``hal_core.UsbTransport`` using ctypes."""

    @staticmethod
    def enumerate() -> list[dict[str, Any]]:
        result = _lib_usb.prom_usb_enumerate()
        devices: list[dict[str, Any]] = []
        for i in range(result.count):
            d = result.devices[i]
            vid = d.vendor_id
            pid = d.product_id
            devices.append({
                "device_id": f"{vid:04x}:{pid:04x}",
                "vendor_id": vid,
                "product_id": pid,
                "manufacturer": _decode(d.manufacturer),
                "product": _decode(d.product),
                "serial_number": _decode(d.serial_number),
                "bus_number": d.bus_number,
                "port_number": d.device_address,
                "usb_spec": 0,
                "device_class": d.class_code,
                "max_packet_size": d.max_packet_size,
            })
        return devices


# ---------------------------------------------------------------------------
# Serial transport
# ---------------------------------------------------------------------------

class _PromSerialPortInfo(ctypes.Structure):
    _fields_ = [
        ("path", ctypes.c_char * 256),
        ("description", ctypes.c_char * 128),
        ("baud_rate", ctypes.c_uint32),
        ("data_bits", ctypes.c_uint8),
        ("parity", ctypes.c_int),
        ("stop_bits", ctypes.c_int),
        ("flow_control", ctypes.c_int),
        ("is_open", ctypes.c_bool),
    ]


class _PromSerialPortList(ctypes.Structure):
    _fields_ = [
        ("ports", _PromSerialPortInfo * 64),
        ("count", ctypes.c_size_t),
        ("error", ctypes.c_int),
    ]


_lib_serial = _load_dll("prom_hal_serial")
_lib_serial.prom_serial_list_ports.restype = _PromSerialPortList
_lib_serial.prom_serial_list_ports.argtypes = []
_lib_serial.prom_serial_strerror.restype = ctypes.c_char_p
_lib_serial.prom_serial_strerror.argtypes = [ctypes.c_int]


DEFAULT_BAUD_RATES = [9600, 19200, 38400, 57600, 115200, 230400, 460800, 921600]


class SerialTransport:
    """Drop-in replacement for ``hal_core.SerialTransport`` using ctypes."""

    @staticmethod
    def enumerate() -> list[dict[str, Any]]:
        result = _lib_serial.prom_serial_list_ports()
        ports: list[dict[str, Any]] = []
        for i in range(result.count):
            p = result.ports[i]
            ports.append({
                "port": _decode(p.path),
                "vendor_id": None,
                "product_id": None,
                "manufacturer": None,
                "product": _decode(p.description),
                "serial_number": None,
                "baud_rates": list(DEFAULT_BAUD_RATES),
            })
        return ports


# ---------------------------------------------------------------------------
# Ed25519 / verify_signature
# ---------------------------------------------------------------------------

def verify_signature(public_key_pem: bytes, payload: bytes, signature: bytes) -> bool:
    """Verify an Ed25519 signature.

    Uses the C++ HAL when a ``prom_ed25519_verify`` symbol is available;
    otherwise falls back to the ``cryptography`` Python package.
    """
    _load_ed25519()
    try:
        pk_hex = public_key_pem.hex().encode("utf-8")
        payload_buf = ctypes.c_char_p(payload)
        sig_buf = ctypes.c_char_p(signature)
        result = _lib_ed25519.prom_ed25519_verify(pk_hex, len(pk_hex), payload_buf, len(payload), sig_buf, len(signature))
        return bool(result)
    except (AttributeError, OSError):
        pass

    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        from cryptography.hazmat.primitives import serialization
        key = serialization.load_pem_public_key(public_key_pem)
        if not isinstance(key, Ed25519PublicKey):
            return False
        key.verify(signature, payload)
        return True
    except Exception:
        return False


_lib_ed25519: ctypes.CDLL | None = None


def _load_ed25519() -> None:
    global _lib_ed25519
    if _lib_ed25519 is not None:
        return
    for candidate in ("prom_hal_ed25519",):
        try:
            _lib_ed25519 = _load_dll(candidate)
            _lib_ed25519.prom_ed25519_verify.restype = ctypes.c_int
            _lib_ed25519.prom_ed25519_verify.argtypes = [
                ctypes.POINTER(ctypes.c_char), ctypes.c_size_t,
                ctypes.POINTER(ctypes.c_char), ctypes.c_size_t,
                ctypes.POINTER(ctypes.c_char), ctypes.c_size_t,
            ]
            return
        except OSError:
            continue
    _lib_ed25519 = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _decode(raw: bytes | None) -> str | None:
    if not raw:
        return None
    text = raw.split(b"\x00", 1)[0].decode("utf-8", errors="replace")
    return text or None
