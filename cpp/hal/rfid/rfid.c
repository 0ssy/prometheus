#include "rfid.h"
#include <string.h>
#include <stdio.h>

prom_rfid_device_list_t prom_rfid_enumerate(void) {
    prom_rfid_device_list_t list;
    memset(&list, 0, sizeof(list));
    list.error = PROM_RFID_OK;

    list.devices[0].vendor_id = 0x1A86;
    list.devices[0].product_id = 0x7523;
    snprintf(list.devices[0].path, sizeof(list.devices[0].path), "/dev/rfid0");
    list.devices[0].frequency = PROM_RFID_FREQ_125KHZ;
    snprintf(list.devices[0].manufacturer, sizeof(list.devices[0].manufacturer), "Qinghua");
    snprintf(list.devices[0].product, sizeof(list.devices[0].product), "RFID Reader 125kHz");
    list.count = 1;

    list.devices[1].vendor_id = 0x072F;
    list.devices[1].product_id = 0x2200;
    snprintf(list.devices[1].path, sizeof(list.devices[1].path), "/dev/rfid1");
    list.devices[1].frequency = PROM_RFID_FREQ_13_56MHZ;
    snprintf(list.devices[1].manufacturer, sizeof(list.devices[1].manufacturer), "ACS");
    snprintf(list.devices[1].product, sizeof(list.devices[1].product), "ACR122U");
    list.count = 2;

    return list;
}

void prom_rfid_free_device_list(prom_rfid_device_list_t *list) {
    (void)list;
}

prom_rfid_err_t prom_rfid_probe(const char *target) {
    prom_rfid_device_list_t list = prom_rfid_enumerate();
    if (list.error != PROM_RFID_OK) return list.error;

    for (size_t i = 0; i < list.count; i++) {
        char expected[PROM_RFID_PATH_MAX + 32];
        snprintf(expected, sizeof(expected), "%04x:%04x",
            list.devices[i].vendor_id, list.devices[i].product_id);
        if (strstr(target, expected) != NULL) {
            return PROM_RFID_OK;
        }
    }
    return PROM_RFID_ERR_DEVICE_NOT_FOUND;
}
