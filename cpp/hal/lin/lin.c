#include "lin.h"
#include <string.h>
#include <stdio.h>

prom_lin_device_list_t prom_lin_enumerate(void) {
    prom_lin_device_list_t list;
    memset(&list, 0, sizeof(list));
    list.error = PROM_LIN_OK;

    snprintf(list.devices[0].interface, sizeof(list.devices[0].interface), "LIN1");
    list.devices[0].vendor_id = 0x16D0;
    list.devices[0].product_id = 0x1166;
    list.devices[0].baud_rate = 19200;
    snprintf(list.devices[0].manufacturer, sizeof(list.devices[0].manufacturer), "NXP");
    snprintf(list.devices[0].product, sizeof(list.devices[0].product), "LIN Transceiver");
    list.count = 1;

    return list;
}

void prom_lin_free_device_list(prom_lin_device_list_t *list) {
    (void)list;
}

prom_lin_err_t prom_lin_probe(const char *target) {
    (void)target;
    return PROM_LIN_OK;
}
