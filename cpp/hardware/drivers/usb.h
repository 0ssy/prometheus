// P2 Hardware Platform — USB transport driver (C).
//
// Native transport primitive exposed via C++ HAL shared libraries and
// loaded from Python through the ctypes bridge.
#ifndef PROMETHEUS_HARDWARE_USB_H
#define PROMETHEUS_HARDWARE_USB_H

#ifdef __cplusplus
extern "C" {
#endif

typedef enum { USB_OK = 0, USB_ERR_NOT_FOUND = -1, USB_ERR_TIMEOUT = -2 } usb_status;

// Probe a USB device by VID/PID. Returns USB_OK on handshake.
usb_status prometheus_usb_probe(const char* target, int timeout_ms);

// Read a descriptor string (writes up to `len` bytes into `out`).
usb_status prometheus_usb_read_descriptor(const char* target, char* out, unsigned len);

#ifdef __cplusplus
}
#endif

#endif // PROMETHEUS_HARDWARE_USB_H
