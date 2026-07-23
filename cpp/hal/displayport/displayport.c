#include "displayport.h"
#include <string.h>
#include <stdio.h>

prom_dp_device_list_t prom_dp_enumerate(void) {
    prom_dp_device_list_t list;
    memset(&list, 0, sizeof(list));
    list.error = PROM_DP_OK;

    snprintf(list.devices[0].path, sizeof(list.devices[0].path), "/dev/dp0");
    list.devices[0].width = 2560;
    list.devices[0].height = 1440;
    list.devices[0].refresh_rate_hz = 144;
    snprintf(list.devices[0].manufacturer, sizeof(list.devices[0].manufacturer), "LG");
    snprintf(list.devices[0].product, sizeof(list.devices[0].product), "27GN850-B");
    list.count = 1;

    return list;
}

void prom_dp_free_device_list(prom_dp_device_list_t *list) {
    (void)list;
}

prom_dp_err_t prom_dp_probe(const char *target) {
    (void)target;
    return PROM_DP_OK;
}
