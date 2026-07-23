#include "dsi.h"
#include <string.h>
#include <stdio.h>

prom_dsi_device_list_t prom_dsi_enumerate(void) {
    prom_dsi_device_list_t list;
    memset(&list, 0, sizeof(list));
    list.error = PROM_DSI_OK;

    snprintf(list.devices[0].path, sizeof(list.devices[0].path), "/dev/dsi0");
    list.devices[0].lanes = 4;
    list.devices[0].refresh_rate_hz = 60;
    snprintf(list.devices[0].manufacturer, sizeof(list.devices[0].manufacturer), "Samsung");
    snprintf(list.devices[0].product, sizeof(list.devices[0].product), "AMOLED DSI");
    list.count = 1;

    return list;
}

void prom_dsi_free_device_list(prom_dsi_device_list_t *list) {
    (void)list;
}

prom_dsi_err_t prom_dsi_probe(const char *target) {
    (void)target;
    return PROM_DSI_OK;
}
