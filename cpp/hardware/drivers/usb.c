// P2 Hardware Platform — USB transport driver implementation (C).
//
// Real driver would open libusb; here we implement a deterministic probe
// so the HAL conformance suite runs without hardware. The Rust `hal-core`
// crate compiles and calls this via `cc`/`bindgen`.
#include "usb.h"
#include <string.h>

usb_status prometheus_usb_probe(const char* target, int timeout_ms) {
    (void)timeout_ms;
    if (target && strncmp(target, "dev-", 4) == 0) {
        return USB_OK;
    }
    return USB_ERR_NOT_FOUND;
}

usb_status prometheus_usb_read_descriptor(const char* target, char* out, unsigned len) {
    if (prometheus_usb_probe(target, 0) != USB_OK) return USB_ERR_NOT_FOUND;
    const char* desc = "prometheus-usb-device";
    unsigned n = (unsigned)strlen(desc);
    if (n >= len) n = len - 1;
    memcpy(out, desc, n);
    out[n] = '\0';
    return USB_OK;
}
