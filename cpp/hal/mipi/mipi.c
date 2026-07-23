#include "mipi.h"
#include <string.h>
#include <stdio.h>

prom_mipi_device_list_t prom_mipi_enumerate(void) {
    prom_mipi_device_list_t list;
    memset(&list, 0, sizeof(list));
    list.error = PROM_MIPI_OK;

    snprintf(list.devices[0].path, sizeof(list.devices[0].path), "/dev/video0");
    list.devices[0].lanes = 4;
    list.devices[0].refresh_rate_hz = 60;
    snprintf(list.devices[0].manufacturer, sizeof(list.devices[0].manufacturer), "Sony");
    snprintf(list.devices[0].product, sizeof(list.devices[0].product), "IMX500 MIPI");
    list.count = 1;

    return list;
}

void prom_mipi_free_device_list(prom_mipi_device_list_t *list) {
    (void)list;
}

prom_mipi_err_t prom_mipi_probe(const char *target) {
    (void)target;
    return PROM_MIPI_OK;
}
