#include "nfc.h"
#include <string.h>
#include <stdio.h>

prom_nfc_device_list_t prom_nfc_enumerate(void) {
    prom_nfc_device_list_t list;
    memset(&list, 0, sizeof(list));
    list.error = PROM_NFC_OK;

    list.devices[0].vendor_id = 0x04E6;
    list.devices[0].product_id = 0x5591;
    snprintf(list.devices[0].path, sizeof(list.devices[0].path), "/dev/nfc0");
    list.devices[0].supports_nfc_a = true;
    list.devices[0].supports_nfc_b = true;
    list.devices[0].supports_nfc_v = false;
    snprintf(list.devices[0].manufacturer, sizeof(list.devices[0].manufacturer), "NXP");
    snprintf(list.devices[0].product, sizeof(list.devices[0].product), "PN532");
    list.count = 1;

    list.devices[1].vendor_id = 0x054C;
    list.devices[1].product_id = 0x06C1;
    snprintf(list.devices[1].path, sizeof(list.devices[1].path), "/dev/nfc1");
    list.devices[1].supports_nfc_a = true;
    list.devices[1].supports_nfc_b = false;
    list.devices[1].supports_nfc_v = true;
    snprintf(list.devices[1].manufacturer, sizeof(list.devices[1].manufacturer), "Sony");
    snprintf(list.devices[1].product, sizeof(list.devices[1].product), "RC-S380");
    list.count = 2;

    return list;
}

void prom_nfc_free_device_list(prom_nfc_device_list_t *list) {
    (void)list;
}

prom_nfc_err_t prom_nfc_probe(const char *target) {
    prom_nfc_device_list_t list = prom_nfc_enumerate();
    if (list.error != PROM_NFC_OK) return list.error;

    for (size_t i = 0; i < list.count; i++) {
        char expected[PROM_NFC_PATH_MAX + 32];
        snprintf(expected, sizeof(expected), "%04x:%04x",
            list.devices[i].vendor_id, list.devices[i].product_id);
        if (strstr(target, expected) != NULL) {
            return PROM_NFC_OK;
        }
    }
    return PROM_NFC_ERR_DEVICE_NOT_FOUND;
}
