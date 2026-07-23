#include "hal_bindings.h"
#include <stdio.h>
#include <string.h>

int hal_usb_probe(const char *target, char *out, size_t out_len) {
    if (target && (strncmp(target, "usb:", 4) == 0 || strncmp(target, "dev-", 4) == 0)) {
        snprintf(out, out_len, "usb:%s:connected", target);
        return 0;
    }
    snprintf(out, out_len, "usb:%s:unsupported", target);
    return -1;
}

int hal_serial_probe(const char *target, char *out, size_t out_len) {
    if (target && (strncmp(target, "serial:", 7) == 0 || strncmp(target, "COM", 3) == 0 || strncmp(target, "/dev/tty", 8) == 0)) {
        snprintf(out, out_len, "serial:%s:connected", target);
        return 0;
    }
    snprintf(out, out_len, "serial:%s:unsupported", target);
    return -1;
}

int hal_jtag_probe(const char *target, char *out, size_t out_len) {
    if (target && (strncmp(target, "jtag:", 5) == 0 || strncmp(target, "swd:", 4) == 0)) {
        snprintf(out, out_len, "jtag:%s:connected", target);
        return 0;
    }
    snprintf(out, out_len, "jtag:%s:unsupported", target);
    return -1;
}
