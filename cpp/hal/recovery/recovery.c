#include "recovery.h"
#include <string.h>
#include <stdio.h>

static const char *recovery_mode_names[] = {
    "android_recovery", "edl", "odin", "dfu", "bios", "uefi", "tpm",
    "router", "iot", "drone", "vehicle", "ecu", "eeprom", "nand", "nor",
    "spi_flash", "embedded_linux"
};

prom_recovery_device_list_t prom_recovery_enumerate(prom_recovery_mode_t mode) {
    prom_recovery_device_list_t list;
    memset(&list, 0, sizeof(list));
    list.error = 0;

    if (mode >= PROM_RECOVERY_MODE_COUNT) {
        list.error = -1;
        return list;
    }

    snprintf(list.devices[0].device_id, sizeof(list.devices[0].device_id),
        "recovery-%s", recovery_mode_names[mode]);
    snprintf(list.devices[0].product, sizeof(list.devices[0].product),
        "Simulated %s", recovery_mode_names[mode]);
    snprintf(list.devices[0].status, sizeof(list.devices[0].status), "idle");
    list.devices[0].mode = mode;
    list.count = 1;

    return list;
}

void prom_recovery_free_device_list(prom_recovery_device_list_t *list) {
    (void)list;
}

int prom_recovery_probe(const char *target, prom_recovery_mode_t *out_mode) {
    const char *rest = strstr(target, "recovery:") != NULL ? target + 9 : target;
    char mode_str[64] = {0};
    const char *colon = strchr(rest, ':');
    size_t len = colon != NULL ? (size_t)(colon - rest) : strlen(rest);
    if (len >= sizeof(mode_str)) len = sizeof(mode_str) - 1;
    memcpy(mode_str, rest, len);
    mode_str[len] = '\0';

    for (int i = 0; i < PROM_RECOVERY_MODE_COUNT; i++) {
        if (strcasecmp(mode_str, recovery_mode_names[i]) == 0) {
            if (out_mode) *out_mode = (prom_recovery_mode_t)i;
            return 0;
        }
    }
    return -1;
}
